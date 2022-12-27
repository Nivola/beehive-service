# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from copy import deepcopy
from urllib.parse import urlencode

from marshmallow.fields import String
from sqlalchemy.sql.functions import array_agg
from beecell.simple import format_date, obscure_data, dict_get
from beecell.types.type_string import truncate
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import ApiServiceTypePlugin, ApiServiceTypeContainer, AsyncApiServiceTypePlugin
from beehive_service.model.account import Account
from beehive_service.model.base import SrvStatusType
from beehive.common.apimanager import ApiClient, ApiManagerWarning, ApiManagerError
from beehive_service.model import Division, Organization
from beehive.common.assert_util import AssertUtil
from beehive_service.plugins.computeservice.controller import ApiComputeInstance, ApiComputeSubnet
from pprint import pprint
from uuid import uuid4
from beecell.types.type_id import id_gen


# class LoggingParamsNames(object):
#     # TODO da capire quali sono i  params!
#     # Nvl_FileSystem_Size = 'Nvl_FileSystem_Size'
#     # Nvl_FileSystem_Type = 'Nvl_FileSystem_Type'
#     # Nvl_shareProto = 'Nvl_shareProto'
#     # Nvl_FileSystemId = 'Nvl_FileSystemId'
#     # SubnetId = 'SubnetId'
#     # owner_id = 'owner_id'
#     CreationToken = 'CreationToken'


class ApiLoggingService(ApiServiceTypeContainer):
    objuri = 'loggingservice'
    objname = 'loggingservice'
    objdesc = 'LoggingService'
    plugintype = 'LoggingService'

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypeContainer.__init__(self, *args, **kvargs)
        self.flag_async = True

        self.child_classes = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypeContainer.info(self)
        info.update({})
        return info

    @staticmethod
    def customize_list(controller, entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        instance_type_idx = controller.get_service_definition_idx(ApiLoggingService.plugintype)

        # get resources
        # zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiLoggingService(controller).list_resources(uuids=resources)
        resources_idx = {r['uuid']: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        self.logger.debug('pre_create - begin - params: %s' % obscure_data(deepcopy(params)))
        compute_services, tot = self.controller.get_paginated_service_instances(plugintype='ComputeService',
                                                                                account_id=self.instance.account_id,
                                                                                filter_expired=False)
        self.logger.debug('pre_create - tot: %s' % tot)
        if tot == 0:
            raise ApiManagerError('Some service dependency does not exist')

        compute_service = compute_services[0]
        if compute_service.is_active() is False:
            raise ApiManagerError('Some service dependency are not in the correct status')

        # set resource uuid
        self.set_resource(compute_service.resource_uuid)

        params['resource_params'] = {}
        self.logger.debug('pre_create - end - params: %s' % obscure_data(deepcopy(params)))

        return params

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: 'pending',
            SrvStatusType.ACTIVE: 'available',
            SrvStatusType.DELETED: 'deregistered',
            SrvStatusType.DRAFT: 'trasient',
            SrvStatusType.ERROR: 'error'
        }
        return mapping.get(state, 'unknown')

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        # instance_type_idx = self.controller.get_service_definition_idx(ApiLoggingService.plugintype)

        instance_item = {}
        instance_item['id'] = self.instance.uuid
        instance_item['name'] = self.instance.name
        instance_item['creationDate'] = format_date(self.instance.model.creation_date)
        instance_item['description'] = self.instance.desc
        instance_item['state'] = self.state_mapping(self.instance.status)
        instance_item['owner'] = self.account.uuid
        instance_item['owner_name'] = self.account.name
        instance_item['template'] = self.instance_type.uuid
        instance_item['template_name'] = self.instance_type.name
        instance_item['stateReason'] = {'code': None, 'message': None}
        # reason = self.resource.get('reason', None)
        if self.instance.status == 'ERROR':
            instance_item['stateReason'] = {'code': 400, 'message': self.instance.last_error}
        instance_item['resource_uuid'] = self.instance.resource_uuid

        return instance_item

    def aws_get_attributes(self):
        """Get account attributes like quotas

        :return:
        """
        if self.resource is None:
            self.resource = {}
        attributes = []

        for quota in self.get_resource_quotas():
            name = quota.get('quota')
            if name.find('logging') == 0:
                name = name.replace('logging.', '')
                attributes_item = {
                    'attributeName': '%s [%s]' % (name, quota.get('unit')),
                    'attributeValueSet': [{
                        'item': {
                            'attributeValue': quota.get('value'),
                            'nvl-attributeUsed': quota.get('allocated')
                        }
                    }]
                }
                attributes.append(attributes_item)

        return attributes

    def set_attributes(self, quotas):
        """Set service quotas

        :param quotas: dict with quotas to set
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {}
        for quota, value in quotas.items():
            # TODO fv da capire!
            # data['share.%s' % quota] = value
            data['logging.%s' % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix='logging'):
        return self.get_container_attributes(prefix=prefix)

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: the running task which is calling the method
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug('create_resource begin')
        self.update_status(SrvStatusType.PENDING)
        quotas = self.get_config('quota')
        self.logger.debug('create_resource quotas: {}'.format(quotas))
        self.set_resource_quotas(task, quotas)

        # update service status
        self.update_status(SrvStatusType.CREATED)
        self.logger.debug('create_resource - Update instance resources: %s' % self.instance.resource_uuid)

        return self.instance.resource_uuid

    def delete_resource(self, *args, **kvargs):
        """Delete resource do nothing. Compute zone is owned by ComputeService

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug('delete_resource begin')
        return True


class ApiLoggingSpace(AsyncApiServiceTypePlugin):
    plugintype = 'LoggingSpace'
    task_path = 'beehive_service.plugins.loggingservice.tasks_v2.'

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        if self.instance is not None:
            self.account = self.controller.get_account(self.instance.account_id)
            # get parent account
            account = self.controller.get_account(self.instance.account_id)
            # get parent division
            div = self.controller.manager.get_entity(Division, account.division_id)
            # get parent organization
            org = self.controller.manager.get_entity(Organization, div.organization_id)

            if self.resource_uuid is not None:
                try:
                    self.resource = self.get_resource()
                except:
                    self.resource = None

            resource_desc = '%s.%s.%s' % (org.name, div.name, account.name)
            self.logger.debug('post_get - resource_desc: %s' % resource_desc)

    @staticmethod
    def customize_list(controller, entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        compute_service_idx = controller.get_service_instance_idx(ApiLoggingSpace.plugintype, index_key='account_id')
        instance_type_idx = controller.get_service_definition_idx(ApiLoggingSpace.plugintype)

        # get resources
        zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.compute_service = compute_service_idx.get(account_id)
            entity.instance_type_idx = instance_type_idx
            if entity.compute_service.resource_uuid not in zones:
                zones.append(entity.compute_service.resource_uuid)
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        if len(resources) == 0:
            resources_idx = {}
        else:
            if len(resources) > 3:
                resources = None
            else:
                zones = []
            if len(zones) > 40:
                zones = None
            elif len(zones) == 0:
                zones = None
            resources_list = ApiLoggingSpace(controller).list_resources(zones=zones, uuids=resources)
            resources_idx = {r['uuid']: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def logging_state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: 'creating',
            SrvStatusType.PENDING: 'creating',
            SrvStatusType.CREATED: 'creating',
            SrvStatusType.BUILDING: 'creating',
            SrvStatusType.ACTIVE: 'available',
            SrvStatusType.DELETING: 'deleting',
            SrvStatusType.DELETED: 'delete',
            SrvStatusType.ERROR: 'error',
        }
        return mapping.get(state, 'unknown')

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        self.logger.debug('aws_info - begin')
        self.logger.debug('aws_info - config: %s' % self.instance.config)

        if self.resource is None:
            self.resource = {}

        instance_type = self.instance_type_idx.get(str(self.instance.service_definition_id))

        instance_item = {}
        instance_item['id'] = self.instance.uuid
        instance_item['name'] = self.instance.name
        instance_item['creationDate'] = format_date(self.instance.model.creation_date)
        instance_item['description'] = self.instance.desc
        instance_item['state'] = self.logging_state_mapping(self.instance.status)
        instance_item['ownerId'] = self.account.uuid
        instance_item['ownerAlias'] = self.account.name
        instance_item['templateId'] = instance_type.uuid
        instance_item['templateName'] = instance_type.name
        instance_item['stateReason'] = {'nvl-code': 0, 'nvl-message': ''}
        if self.instance.status == 'ERROR':
            instance_item['stateReason'] = {'nvl-code': 400, 'nvl-message': self.instance.last_error}
        # instance_item['resource_uuid'] = self.instance.resource_uuid

        # kibana_space_name = self.instance.config.get('kibana_space_name')
        # instance_item['kibanaSpaceName'] = kibana_space_name

        # endpoints
        base_endpoint = self.get_config('dashboard_endpoint')
        kibana_space_name = self.instance.config.get('kibana_space_name')
        instance_item['endpoints'] = {
            'home': '%s/s/%s/app/home#/' % (base_endpoint, kibana_space_name),
            'discover': '%s/s/%s/app/discover#/' % (base_endpoint, kibana_space_name)
        }

        # dashboard
        instance_item['dashboards'] = []
        if 'dashboards' in self.resource:
            for d in self.resource.get('dashboards'):
                instance_item['dashboards'].append({
                    'dashboardId': d.get('id'),
                    'dashboardName': d.get('desc'),
                    'dashboardVersion': d.get('version'),
                    'dashboardScore': d.get('score'),
                    'modificationDate': d.get('updated_at'),
                    'endpoint': '%s/s/%s/app/dashboards#/view/%s' % (base_endpoint, kibana_space_name, d.get('id'))
                })

        return instance_item

    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # self.logger.debug('pre_create - begin')
        # self.logger.debug('pre_create - params {}'.format(params))

        # # params = self.get_config()
        # json_cfg = self.instance.config_object.json_cfg
        # self.logger.debug('pre_create - dopo get_config - json_cfg {}'.format(json_cfg))
        # # inner_data = json_cfg['space']

        container_id = self.get_config('container')
        compute_zone = self.get_config('computeZone')
        dashboard_space_from = self.get_config('dashboard_space_from')
        dashboard = self.get_config('dashboard')
        # name = '%s-%s' % (self.instance.name, id_gen(length=8))

        # # creazione triplet
        account_id = self.instance.account_id
        # # account_id = inner_data.get('owner_id')
        # self.logger.debug('pre_create - account_id: %s' % account_id)
        # # get parent account
        account: ApiAccount = self.controller.get_account(account_id)
        # # get parent division
        # div: Division = self.controller.manager.get_entity(Division, account.division_id)
        # # get parent organization
        # org: Organization = self.controller.manager.get_entity(Organization, div.organization_id)
        # triplet = '%s.%s.%s' % (org.name, div.name, account.name)
        # self.logger.debug('pre_create - triplet: %s' % triplet)

        users: list = account.get_users()
        users_to_add = []
        for user in users:
            # self.logger.debug('pre_create - user: {}'.format(user))
            if user['role'] == 'master' or user['role'] == 'viewer':
                email = user['email']
                # to avoid duplicates
                if email not in users_to_add:
                    users_to_add.append(user['email'])
                
        str_users: str = ''
        for email in users_to_add:
            str_users = str_users + email + ','
        self.logger.debug('pre_create - str_users: %s' % str_users)
        if str_users.endswith(','):
            str_users = str_users[:-1]

        name = '%s-%s' % (params['name'], id_gen())
        desc = params['desc']
        triplet = self.get_config('triplet').lower()

        space = self.get_config('space')
        if 'norescreate' in space:
            norescreate = space['norescreate']
        else:
            norescreate = False

        # if name == 'SpaceDefault':
        #     name = triplet
        #     desc = 'desc %s' % triplet
        #
        #     # update service instance name
        #     self.update_name(name)
        #     self.update_desc(desc)

        # name = name.lower()
        # desc = desc.lower()

        data = {
            'compute_zone': compute_zone,
            'container': container_id,
            'desc': desc,
            'name': name,
            'dashboard_space_from': dashboard_space_from,
            'dashboard': dashboard,
            'str_users': str_users,
            'norescreate': norescreate,
            'elk_space': {
                'space_id': triplet.replace('.', '-'),
                'name': triplet,
                'desc': desc,
                'triplet': triplet,
            }
        }
        params['resource_params'] = data
        self.logger.debug('pre_create - resource_params: %s' % obscure_data(deepcopy(params)))

        params['id'] = self.instance.oid

        self.logger.debug('pre_create - end')
        return params

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.logger.debug('pre_delete - begin')
        self.logger.debug('pre_delete - params {}'.format(params))

        if self.check_resource() is not None:
            # raise ApiManagerError('Logging %s has an active space. It can not be deleted' % self.instance.uuid)
            container_id = self.get_config('container')
            compute_zone = self.get_config('computeZone')

            data = {
                'container': container_id,
                'compute_zone': compute_zone,
            }
            params['resource_params'] = data
            self.logger.debug('pre_delete params: %s' % params)

            return params

        self.logger.debug('pre_delete - end')
        return params

    def sync_users(self):
        """Synchronize users in a space

        :return:
        """
        try:
            # creazione triplet
            account_id = self.instance.account_id
            # account_id = inner_data.get('owner_id')
            self.logger.debug('sync_users - account_id: %s' % account_id)
            # get parent account
            account: ApiAccount = self.controller.get_account(account_id)
            # get parent division
            div: Division = self.controller.manager.get_entity(Division, account.division_id)
            # get parent organization
            org: Organization = self.controller.manager.get_entity(Organization, div.organization_id)
            triplet = '%s.%s.%s' % (org.name, div.name, account.name)
            self.logger.debug('sync_users - triplet: %s' % triplet)

            users: list = account.get_users()
            # str_users: str = 'xxx@csi.it,' # per test
            
            users_to_add = []
            for user in users:
                # self.logger.debug('sync_users - user: {}'.format(user))
                if user['role'] == 'master' or user['role'] == 'viewer':
                    email = user['email']
                    # to avoid duplicates
                    if email not in users_to_add:
                        users_to_add.append(user['email'])
                    
            str_users: str = ''
            for email in users_to_add:
                str_users = str_users + email + ','
            self.logger.debug('sync_users - str_users: %s' % str_users)
            if str_users.endswith(','):
                str_users = str_users[:-1]

            resource_space_id = self.instance.resource_uuid
            self.logger.debug('sync_users - resource_space_id: %s' % resource_space_id)

            role_name = self.__get_role_name(triplet)
            self.logger.debug('sync_users - role_name: %s' % role_name)

            # task creation
            params = {
                'resource_params': {
                    # 'action': 'sync-users',
                    'action': {
                        'name': 'sync-users',
                        'args': {
                            'triplet': triplet,
                            'str_users': str_users,
                            'resource_space_id': resource_space_id,
                            'role_name': role_name
                        }
                    }
                }
            }
            self.logger.debug('sync_users - params {}'.format(params))
            self.action(**params)
        except Exception:
            self.logger.error('sync_users', exc_info=2)
            raise ApiManagerError('Error sync_users for space %s' % self.instance.uuid)

        return True

    #
    # resource
    #
    def __get_role_name(self, triplet):
        name = 'role_%s' % triplet
        name = name.lower()
        return name

    def get_resource(self, uuid=None):
        """Get resource info

        :param uuid: resource uuid [optional]
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        space = None
        if uuid is None:
            uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = '/v1.0/nrs/provider/logging_spaces/%s' % uuid
            space = self.controller.api_client.admin_request('resource', uri, 'get', data='').get('logging_space')
        self.logger.debug('Get logging space resource: %s' % truncate(space))
        return space

    def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            'size': size,
            'page': page
        }
        if zones is not None:
            data['parent_list'] = ','.join(zones)
        if uuids is not None:
            data['uuids'] = ','.join(uuids)
        if tags is not None:
            data['tags'] = ','.join(tags)
        uri = '/v1.0/nrs/provider/logging_spaces'
        data = urlencode(data)
        spaces = self.controller.api_client.admin_request('resource', uri, 'get', data=data).get('logging_spaces', [])
        self.logger.debug('Get logging space resources: %s' % truncate(spaces))
        return spaces

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # self.logger.debug('create_resource - begin')
        # data = {'logging_space': args[0]}
        # self.logger.debug('create_resource - data: {}'.format(data))

        compute_zone = args[0].get('compute_zone')
        container = args[0].get('container')

        # params for dashboard copy
        dashboard_space_from = args[0].pop('dashboard_space_from')
        dashboard = args[0].pop('dashboard')

        # params for role mapping
        str_users = args[0].pop('str_users')

        elk_space = args[0].get('elk_space')
        space_id = elk_space.get('space_id')
        space_name = elk_space.get('name')

        triplet = elk_space.pop('triplet')

        norescreate = args[0].pop('norescreate')

        space_data = {
            'logging_space': {
                'container': container,
                'compute_zone': compute_zone,
                'name': space_name,
                'desc': space_name,
                'norescreate': norescreate,
                'elk_space': elk_space
            }
        }

        # create space
        try:
            uri = '/v1.0/nrs/provider/logging_spaces'
            # data = {'logging_space': args[0]}
            res = self.controller.api_client.admin_request('resource', uri, 'post', data=space_data)
            uuid = res.get('uuid', None)
            taskid = res.get('taskid', None)
            self.logger.debug('Create resource: %s' % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug('Update space resource: %s' % uuid)

            # create roles
            resource_space_id = uuid
            # role_name = self.create_resource_role(task, compute_zone, container, name, triplet, resource_space_id, 
            #                                       space_id)
            role_name = self.__create_resource_role(task, container, triplet, resource_space_id, space_id, norescreate)

            # create role mapping
            # self.__create_resource_role_mapping(task, compute_zone, container, triplet, resource_space_id, role_name,
            #                                  str_users)
            self.__create_resource_role_mapping(task, container, triplet, resource_space_id, role_name, str_users, norescreate)

            if norescreate is False:
                # copy dashboard to folder (don't execute just after creation, the resource sometimes isn't already active)
                self.__create_resource_dashboard(task, resource_space_id, dashboard_space_from, dashboard, triplet)

        kibana_space_name = space_id
        self.logger.debug('create_resource - kibana_space_name: %s' % kibana_space_name)
        self.instance.set_config('kibana_space_name', kibana_space_name)

        self.logger.debug('create_resource - end')

        return uuid

    def __create_resource_role(self, task, container, triplet, resource_space_id, space_id, norescreate):
        """Create role

        :param task: task instance
        :param container:
        :param triplet:
        :param resource_space_id:
        :param space_id:
        :return:
        """
        name = self.__get_role_name(triplet)

        indice = '*-%s' % triplet
        indice = indice.lower()

        role_data = {
            'logging_role': {
                'container': container,
                'name': name,
                'desc': name,
                'logging_space': resource_space_id,
                'norescreate': norescreate,
                'elk_role': {
                    'name': name,
                    'desc': name,
                    'indice': indice,
                    'space_id': space_id
                }
            }
        }
        self.logger.debug('create_resource_role - role data: %s' % role_data)

        # create role
        try:
            res = self.controller.api_client.admin_request('resource', '/v1.0/nrs/provider/logging_roles', 'post',
                                                           data=role_data, other_headers=None)
            taskid = res.get('taskid', None)
            uuid = res.get('uuid', None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # wait job
        if taskid is not None:
            self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
        else:
            raise ApiManagerError('role job does not started')

        self.logger.debug('create_resource_role - role resource %s' % uuid)
        return name

    def __create_resource_dashboard(self, task, resource_space_id, dashboard_space_from, dashboard, triplet):
        """Create dashboard

        :param task: celery task reference
        :param resource_space_id: resource space id
        :param dashboard_space_from: dashboard space from
        :param dashboard:
        :param triplet:
        :rtype: bool
        """
        self.logger.debug('create_resource_dashboard - begin')
        self.logger.debug('create_resource_dashboard - dashboard_space_from: %s' % dashboard_space_from)

        for dashboard_item in dashboard:
            title = dashboard_item['title']
            logtype = dashboard_item['logtype']

            # filebeat-*-logtype-*-account_name
            index_pattern = 'filebeat-*-' + logtype + '-*-' + triplet.lower()

            dashboard_data = {
                'action': {
                    'add_dashboard': {
                        'space_id_from': dashboard_space_from,
                        'dashboard': title,
                        'index_pattern': index_pattern
                    }
                }
            }
            self.logger.debug('create_resource_dashboard - dashboard_data: %s' % dashboard_data)

            # create dashboard_data
            try:
                url_action = '/v1.0/nrs/provider/logging_spaces/%s/actions' % resource_space_id
                self.logger.debug('create_resource_dashboard - url_action: %s' % url_action)
                res = self.controller.api_client.admin_request('resource', url_action, 'put',
                                                               data=dashboard_data, other_headers=None)
                taskid = res.get('taskid', None)
                uuid = res.get('uuid', None)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # wait job
            if taskid is not None:
                self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
            else:
                raise ApiManagerError('dashboard_data job does not started')

        self.logger.debug('create_resource_dashboard - resource %s' % uuid)
        return True

    def __create_resource_role_mapping(self, task, container, triplet, resource_space_id, role_name, users_email, norescreate=None):
        """Create role mapping
        
        :param task: 
        :param container: 
        :param triplet: 
        :param resource_space_id: 
        :param role_name: 
        :param users_email: 
        :return: 
        """
        name = 'mapping_%s' % triplet
        name = name.lower()
        
        role_mapping_data = {
            'logging_role_mapping': {
                'container': container,
                'name': name,
                'desc': name,
                'logging_space': resource_space_id,
                'norescreate': norescreate,
                'elk_role_mapping': {
                    'name': name,
                    'desc': name,
                    'role_name': role_name,
                    'users_email': users_email,
                    'realm_name': 'ldap-internal'
                }
            }
        }
        self.logger.debug('create_resource_role_mapping - role_mapping_data: %s' % role_mapping_data)

        # create role mapping
        try:
            uri = '/v1.0/nrs/provider/logging_role_mappings'
            res = self.controller.api_client.admin_request('resource', uri, 'post', data=role_mapping_data,
                                                           other_headers=None)
            taskid = res.get('taskid', None)
            uuid = res.get('uuid', None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)
        
        # wait job
        if taskid is not None:
            self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
        else:
            raise ApiManagerError('role mapping job does not started')

        self.logger.debug('create_resource_role_mapping - resource %s' % uuid)
        return True
        
    def update_resource(self, task, **kvargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """
        self.logger.debug('update_resource - begin')

        try:
            # single action
            action = kvargs.pop('action', None)
            if action is not None:
                data = {
                    'action': {
                        action.get('name'): action.get('args')
                    }
                }
                uri = '/v1.0/nrs/provider/logging_spaces/%s/actions' % self.instance.resource_uuid
                res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
                taskid = res.get('taskid', None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug('update_resource - Update space action resources: %s' % res)

            # base update
            elif len(kvargs.keys()) > 0:
                data = {
                    'logging_space': kvargs
                }
                self.controller.api_client
                api_client: ApiClient = self.controller.api_client
                res = api_client.admin_request(
                    'resource', '/v1.0/nrs/provider/logging_spaces/%s' % self.instance.resource_uuid, 'put', data=data)
                taskid = res.get('taskid')
                if taskid is not None:
                    self.wait_for_task(taskid, delta=2, maxtime=180, task=task)

                self.logger.debug('update_resource - Update logging space action resources: %s' % res)

                self.logger.debug('update_resource - end')
                return taskid
            
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))
        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug('delete_resource - begin')
        self.logger.debug('delete_resource - args {}'.format(args))
        self.logger.debug('delete_resource - kvargs {}'.format(kvargs))

        self.__delete_role(task)
        self.__delete_role_mapping(task)

        # delete current resource entities - space
        res_space = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)
        self.logger.debug('delete_resource - res_space {}'.format(res_space))

        self.logger.debug('delete_resource - end')
        return

    def __delete_role(self, task):
        # find role child of space
        role_data = {
            'parent': self.instance.resource_uuid
        }
        res_role = self.controller.api_client.admin_request('resource', '/v1.0/nrs/provider/logging_roles', 'get',
                                                            data=role_data, other_headers=None)
        self.logger.debug('delete_role - res_role {}'.format(res_role))
        logging_roles: list = res_role.get('logging_roles')
        if len(logging_roles) > 0:
            logging_role = logging_roles.pop(0)
            uuid_role = logging_role.get('uuid')

            # delete role
            self.logger.debug('delete_role - delete uuid_role %s' % uuid_role)
            role_delete_data = {}
            uri = '/v1.0/nrs/provider/logging_roles/' + uuid_role
            res_role_delete = self.controller.api_client.admin_request('resource', uri, 'delete',
                                                                       data=role_delete_data, other_headers=None)
            self.logger.debug('delete_role - res_role_delete {}'.format(res_role_delete))
            uuid = res_role_delete.get('uuid')
            taskid = res_role_delete.get('taskid')
            if uuid is not None and taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                self.logger.debug('delete_role - ok - deleted uuid_role %s' % uuid_role)
        else:
            self.logger.debug('delete_role - no role to delete')

    def __delete_role_mapping(self, task):
        # find role mapping child of space
        role_mapping_data = {
            'parent': self.instance.resource_uuid
        }
        uri = '/v1.0/nrs/provider/logging_role_mappings'
        res_role_mapping = self.controller.api_client.admin_request('resource', uri, 'get',
                                                                    data=role_mapping_data, other_headers=None)
        self.logger.debug('delete_role_mapping - res_role_mapping {}'.format(res_role_mapping))
        logging_role_mappings: list = res_role_mapping.get('logging_role_mappings')
        if len(logging_role_mappings) > 0:
            logging_role_mapping = logging_role_mappings.pop(0)
            uuid_role_mapping = logging_role_mapping.get('uuid')

            # delete role_mapping
            self.logger.debug('delete_role_mapping - delete uuid_role_mapping %s' % uuid_role_mapping)
            role_mapping_delete_data = {}
            uri = '/v1.0/nrs/provider/logging_role_mappings/' + uuid_role_mapping
            res_role_mapping_delete = self.controller.api_client.admin_request('resource', uri, 'delete',
                                                                               data=role_mapping_delete_data,
                                                                               other_headers=None)
            self.logger.debug('delete_role_mapping - res_role_mapping_delete {}'.format(res_role_mapping_delete))
            uuid = res_role_mapping_delete.get('uuid')
            taskid = res_role_mapping_delete.get('taskid')
            if uuid is not None and taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                self.logger.debug('delete_role_mapping - ok - deleted uuid_role_mapping %s' % uuid_role_mapping)
        else:
            self.logger.debug('delete_role_mapping - no role_mapping to delete')

    def action_resource(self, task, *args, **kvargs):
        """Send action to resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug('action_resource - begin')
        self.logger.debug('action_resource - kvargs {}'.format(kvargs))

        compute_zone = self.get_config('computeZone')
        container = self.get_config('container')

        # create new rules
        action = kvargs.get('action', None)
        if action is not None:
            name = action.get('name')
            args = action.get('args')
            self.logger.debug('action_resource - action name: %s' % name)
            
            if name == 'sync-users':
                # self.instance.sync_users_action()
                triplet = args.get('triplet')
                resource_space_id = args.get('resource_space_id')
                role_name = args.get('role_name')
                str_users = args.get('str_users')

                self.__delete_role_mapping(task)
                self.__create_resource_role_mapping(task, container, triplet, resource_space_id, role_name, str_users)

        self.logger.debug('action_resource - end')
        return True


class ApiLoggingInstance(AsyncApiServiceTypePlugin):
    plugintype = 'LoggingInstance'
    task_path = 'beehive_service.plugins.loggingservice.tasks_v2.'

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        pass
        # if self.instance is not None:
        #     self.account = self.controller.get_account(self.instance.account_id)
        #     # get parent account
        #     account = self.controller.get_account(self.instance.account_id)
        #     # get parent division
        #     div = self.controller.manager.get_entity(Division, account.division_id)
        #     # get parent organization
        #     org = self.controller.manager.get_entity(Organization, div.organization_id)
        #
        #     resource_desc = '%s.%s.%s' % (org.name, div.name, account.name)
        #     self.logger.debug('post_get - resource_desc: %s' % resource_desc)

    @staticmethod
    def customize_list(controller, entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        return entities

    def logging_state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: 'creating',
            SrvStatusType.PENDING: 'creating',
            SrvStatusType.BUILDING: 'creating',
            SrvStatusType.ACTIVE: 'available',
            SrvStatusType.DELETING: 'deleting',
            SrvStatusType.DELETED: 'delete',
            SrvStatusType.ERROR: 'error',
        }
        return mapping.get(state, 'unknown')

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        inner_data = self.instance.config.get('instance')
        compute_instance = None
        if inner_data is not None and 'ComputeInstanceId' in inner_data:
            compute_instance = inner_data.get('ComputeInstanceId')
        
        modules = self.instance.config.get('modules')

        instance_item = {}
        instance_item['id'] = self.instance.uuid
        instance_item['name'] = self.instance.name
        instance_item['creationDate'] = format_date(self.instance.model.creation_date)
        instance_item['description'] = self.instance.desc
        instance_item['state'] = self.logging_state_mapping(self.instance.status)
        instance_item['ownerId'] = str(self.instance.account_id)
        # instance_item['template'] = self.instance_type.uuid
        # instance_item['template_name'] = self.instance_type.name
        instance_item['stateReason'] = {'nvl-code': 0, 'nvl-message': ''}
        if self.instance.status == 'ERROR':
            instance_item['stateReason'] = {'nvl-code': 400, 'nvl-message': self.instance.last_error}

        instance_item['computeInstanceId'] = compute_instance
        instance_item['modules'] = modules

        return instance_item

    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        compute_zone = self.get_config('computeZone')

        # base quotas
        quotas = {
            'logging.instances': 1
        }

        # check quotas
        # commentare in fase di add
        self.check_quotas(compute_zone, quotas)

        # read config
        config = self.get_config('instance')
        compute_instance_id = config.get('ComputeInstanceId')

        # get compute instance service instance
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

        params['resource_params'] = {
            'compute_instance_resource_uuid': compute_service_instance.resource_uuid,
            'compute_instance_id': compute_service_instance.oid
        }

        self.logger.debug('pre_create - end')
        return params

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        return params

    def enable_log_config(self, module_params):
        """enable logging config in a compute instance

        :param module_params: module params
        :return:
        """
        try:
            config = self.get_config('instance')
            compute_instance_id = config.get('ComputeInstanceId')

            # get compute instance service instance
            compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

            # task creation
            params = {
                'resource_uuid': compute_service_instance.resource_uuid,
                'resource_params': {
                    'action': 'enable-log-config',
                    'module_params': module_params
                }
            }
            self.logger.debug('enable log config - params {}'.format(params))
            self.action(**params)
        except Exception:
            self.logger.error('enable log config', exc_info=2)
            raise ApiManagerError('Error enabling log config for instance %s' % self.instance.uuid)

        return True

    def disable_log_config(self, module_params):
        """disable logging config in a compute instance

        :param module_params: module params
        :return:
        """
        try:
            config = self.get_config('instance')
            compute_instance_id = config.get('ComputeInstanceId')

            # get compute instance service instance
            compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

            # task creation
            params = {
                'resource_uuid': compute_service_instance.resource_uuid,
                'resource_params': {
                    'action': 'disable-log-config',
                    'module_params': module_params
                }
            }
            self.logger.debug('disable log config - params {}'.format(params))
            self.action(**params)
        except Exception:
            self.logger.error('disable log config', exc_info=2)
            raise ApiManagerError('Error disabling log config for instance %s' % self.instance.uuid)

        return True

    #
    # resource
    #
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        compute_instance_id = args[0].pop('compute_instance_id', None)
        compute_instance_resource_uuid = args[0].pop('compute_instance_resource_uuid', None)
        files = None
        pipeline = 5051
        data = {
            'action': {'enable_logging': {'files': files, 'logstash_port': pipeline}}
        }
        uri = '/v1.0/nrs/provider/instances/%s/actions' % compute_instance_resource_uuid
        res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
        taskid = res.get('taskid', None)
        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug('Update compute instance %s action resources: %s' % (compute_instance_resource_uuid, res))

        # create link between instance and compute instance
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)
        self.add_link(name='logging-%s' % id_gen(), type='logging', end_service=compute_service_instance.oid,
                      attributes={})

        return self.instance.resource_uuid

    def update_resource(self, task, **kwargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """
        self.logger.debug('update_resource - begin')
        self.logger.debug('update_resource - end')
        return

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        config = self.get_config('instance')
        compute_instance_id = config.get('ComputeInstanceId')

        # get compute instance service instance
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)
        compute_instance_resource_uuid = compute_service_instance.resource_uuid

        data = {
            'action': {'disable_logging': {}}
        }
        uri = '/v1.0/nrs/provider/instances/%s/actions' % compute_instance_resource_uuid
        res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
        taskid = res.get('taskid', None)
        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug('Update compute instance %s action resources: %s' % (compute_instance_resource_uuid, res))

        return True

    def check_resource(self, *args, **kvargs):
        """Check resource exists

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        config = self.get_config('instance')
        self.logger.debug('+++++ config: {}'.format(config))

        compute_instance_id = None
        if config is not None and 'ComputeInstanceId' in config:
            compute_instance_id = config.get('ComputeInstanceId')

        # get compute instance service instance
        self.logger.debug('+++++ compute_instance_id: %s' % (compute_instance_id))
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

        return compute_service_instance.resource_uuid

    def action_resource(self, task, *args, **kvargs):
        """Send action to resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        config = self.get_config('instance')
        compute_instance_id = config.get('ComputeInstanceId')

        # get compute instance service instance
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)
        compute_instance_resource_uuid = compute_service_instance.resource_uuid

        # create new rules
        action = kvargs.get('action', None)
        module_params = kvargs.get('module_params', None)
        self.logger.warn('action_resource - action: %s' % action)
        self.logger.warn('action_resource - module_params: %s' % module_params)
        
        if action == 'enable-log-config':
            # get module name
            module = module_params.get('name')

            # run action on compute instance
            data = {
                'action': {'enable_log_module': {'module': module, 'module_params': module_params}}
            }
            uri = '/v1.0/nrs/provider/instances/%s/actions' % compute_instance_resource_uuid
            res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
            taskid = res.get('taskid', None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug('Update compute instance %s action resources: %s' % (compute_instance_resource_uuid, res))

            # update service instance config
            # modules = json_cfg.get('modules')
            modules = self.instance.get_config('modules')
            if modules is None:
                modules = {}
            modules.update({module: module_params})
            self.logger.debug('action_resource - modules: {}'.format(modules))
            self.instance.set_config('modules', modules)

        elif action == 'disable-log-config':
            # get module name
            module = module_params.get('name')

            # run action on compute instance
            data = {
                'action': {'disable_log_module': {'module': module, 'module_params': module_params}}
            }
            uri = '/v1.0/nrs/provider/instances/%s/actions' % compute_instance_resource_uuid
            res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
            taskid = res.get('taskid', None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug('Update compute instance %s action resources: %s' % (compute_instance_resource_uuid, res))

            # update service instance config
            # modules = json_cfg.get('modules')
            modules = self.instance.get_config('modules')
            if modules is not None:
                modules.pop(module)
            self.logger.debug('action_resource - modules: {}'.format(modules))
            self.instance.set_config('modules', modules)

        self.logger.debug('action_resource - end')
        return True
