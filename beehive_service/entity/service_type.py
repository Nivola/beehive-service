# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import json
from six.moves.urllib.parse import urlencode
from time import sleep
from beecell.remote import NotFoundException
from beecell.simple import str2bool, truncate, dict_get, format_date
from beehive.common.apimanager import ApiObject, ApiManagerError
from beehive.common.data import trace, operation
from beehive.common.task_v2 import prepare_or_run_task
from beehive_service.entity import ServiceApiObject
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.entity.service_instance import ApiServiceInstance, ApiServiceInstanceConfig
from beehive_service.model import SrvStatusType, ServiceInstance
from beehive_service.service_util import __SRV_MODULE_BASE_PREFIX__
from typing import List, Type, Tuple, Any, Union, Dict
from logging import getLogger

logger = getLogger(__name__)


class ApiServiceType(ServiceApiObject):
    objdef = 'ServiceType'
    objuri = 'servicetype'
    objname = 'servicetype'
    objdesc = 'ServiceType'

    INVALID_PROCESS_KEY = 'invalid_key'

    PROCESS_KEY_CREATION = 'instanceCreate'
    PROCESS_KEY_DELETE = 'instanceDelete'
    PROCESS_KEY_UPDATE = 'instanceUpdate'
    PROCESS_ADD_RULE = 'addRule'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.status = None
        self.objclass = None
        self.flag_container = False
        self.plugintype = None
        self.template_cfg = None

        # use this attribute in plugin to point service instance
        self.instance = None

        if self.model is not None:
            self.status = self.model.status
            self.objclass = self.model.objclass
            self.flag_container = bool(self.model.flag_container)
            self.plugintype = self.model.plugintype.name_type
            self.template_cfg = self.model.template_cfg

        # child classes
        self.child_classes = [
            # ApiServiceCostParam,
            ApiServiceDefinition,
            ApiServiceProcess
        ]

        self.update_object = self.manager.update_service_type
        self.delete_object = self.manager.delete
        self.flag_async = False

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'status': self.status,
            'objclass': self.objclass,
            'plugintype': self.plugintype,
            'flag_container': str2bool(self.flag_container),
            'template_cfg': self.template_cfg
        })
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def update_name(self, name):
        if self.update_object is not None:
            self.update_object(oid=self.oid, name=name)
            self.logger.debug('Update name of %s to %s' % (self.uuid, name))

    def update_desc(self, desc):
        if self.update_object is not None:
            self.update_object(oid=self.oid, desc=desc)
            self.logger.debug('Update desc of %s to %s' % (self.uuid, desc))

    def update_status(self, status):
        if self.update_object is not None:
            self.update_object(oid=self.oid, status=status)
            self.logger.debug('Update status of %s to %s' % (self.uuid, status))

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method. Extend this function to execute action after
        object was deleted.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: True
        :raise ApiManagerError:
        """
        self.update_status(SrvStatusType.DELETED)
        return True

    def acquire_metric(self, resource_uuid: str) -> List[dict]:
        """Call resource method to generate metric consume for a single instance

        :param resource_uuid: resource uuid
        :rtype dict
        :raise ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        # metric_type_nums = [1, 2, 3, 7]
        # metric_type = random.randint(1, 8)
        # if metric_type in metric_type_nums:
        #     value = (random.randint(1, 100))
        # else:
        #     value = (random.randint(0, 1))
        #
        # metrics = [{'metric_type': '%s' % metric_type,
        #             'metric_value': '%s' % value,
        #             'resource_type': '%s' % self.__class__.__name__}]

        metrics = []
        return metrics

    # def validateParams(self, oid):
    #     """Validation params pre-create instance
    #
    #     :return: Dictionary with object detail.
    #     :rtype: dict
    #     :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
    #     """
    #     self.logger.info('validateParams oid=%s' % oid)

    # def transformParamResource(self, oid):
    #     """Transformation params post-create instance
    #
    #     :return: Dictionary with normalized params.
    #     :rtype: dict
    #     :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
    #     """
    #     self.logger.info('transformParamResource oid=%s' % oid)

    # def createResourceInstance(self, instance):
    #     """ Make resource :
    #
    #         :return: uuid resource if it is a sync plugin, None otherwise
    #         :return: process_id: if it is an asynchronous plugin invoque Camunda process and return id, None otherwise
    #         :rtype: string, string
    #         :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
    #     """
    #     # finta per ora
    #     uuid = None
    #     process_id = None
    #     return uuid, process_id

    # def base_prepare_process_variables(self, instance, template, **kvargs):
    #     """
    #     Agnostic prepare of process variables  only extract base info from instance
    #     :param instance:  (ServiceInstance) the instance for which we want to launch process
    #     :param template: (string) the jinja2 template for get the json representation of the process variables
    #     :param kvargs:  arbitrary context
    #     :return: dictionary containig process variables
    #     """
    #     # current environment
    #     data_context = {
    #         'instance_uuid': instance.uuid,
    #         'resource_uuid': instance.resource_uuid,
    #         'srvinstance_account_id': instance.account_id,
    #         'srvinstance_status': instance.status,
    #         'obj_instance': instance,
    #     }
    #
    #     if instance.model:
    #         data_context['srvinstance_account_id'] = instance.model.account_id
    #         data_context['srvinstance_status'] = instance.model.status
    #         data_context['name'] = instance.model.name
    #         data_context['desc'] = instance.model.desc
    #         data_context['resource_uuid'] = instance.model.resource_uuid
    #
    #     # merge kvarrgs into rendering context
    #     data_context.update(kvargs)
    #
    #     # render template
    #     jtmpl = Template(template)
    #     out_rep = jtmpl.render(**data_context)
    #
    #     self.logger.debug('TEMPLATE CONTEXT: <<<%s>>>' % str(data_context))
    #     self.logger.debug('TEMPLATE RENDERED: <<<%s>>>' % out_rep)
    #
    #     data = json.loads(out_rep)
    #
    #     return data

    # def prepare_create_process_variables(self, instance, template, **kvargs):
    #     """
    #     Prepare process variables prepare process variables using template for crate resource operation
    #     :param instance:  (ServiceInstance) the instance for which we want to launch process
    #     :param template: (string) the jinja2 template for get the json representation of the process variables
    #     :param kvargs:  arbitrary context
    #     :return: dictionary
    #     """
    #
    #     # current environment
    #     data_context = {}
    #     # ggg preparo  il contesto di rendering del template cfg + ambiente
    #     # ggg recupero la configurazione attiva
    #     active_cfg = instance.getActiveCFG()
    #     cfg_data = {}
    #
    #     if active_cfg is not None and active_cfg.json_cfg is not None:
    #         cfg_data = active_cfg.json_cfg
    #
    #     # merge cfg + environment
    #     data_context.update(cfg_data)
    #     data_context.update(kvargs)
    #     return self.base_prepare_process_variables(instance, template, **data_context)

    # def createResourceInstanceAsync(self, instance, process_key, template="{}"):
    #     """ Make resource :
    #
    #         :return: uuid resource if it is a sync plugin, None otherwise
    #         :return: process_id: if it is an asynchronous plugin invoque Camunda process and return id, None otherwise
    #         :rtype: string, string
    #         :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
    #     """
    #     data = self.prepare_create_process_variables(instance, template)
    #
    #     try:
    #         res = self.camunda_engine.process_instance_start_processkey(process_key, variables=data)
    #         self.logger.debug('Call Camunda call: %s' % res)
    #         process_id = res.get('id')
    #
    #         upd_data = {'bpmn_process_id': process_id}
    #
    #         instance.update(**upd_data)
    #
    #         self.logger.debug('Resource ApiDummySTChild asynchronous...! %s' % process_id)
    #     except RemoteException as ex:
    #         self.logger.warn('Resource ApiDummySTChild asynchronous...! %s' % str(ex))
    #         raise ApiManagerWarning(ex)
    #
    #     return None, process_id

    def get_bpmn_process_key(self, instance, method_key):
        """
        get bpmn process info key for method.
        Returns process key and variable template.
        :param instance:  ServiceInstance for which we are  getting process infos
        :param method_key: the method name we are looking for
        :return: tuple process_key , template
        :rtype: basestring, basestring
        """
        if instance.model.service_definition.service_type.serviceProcesses is None:
            return None, None

        for p in instance.model.service_definition.service_type.serviceProcesses:
            self.logger.warn(instance.model.service_definition.service_type.serviceProcesses)
            if p.method_key == method_key:
                # ggg restituisco ance il template
                return p.process_key, p.template
        return None, None


class ApiServiceTypePlugin(ApiServiceType):
    INVALID_PROCESS_KEY = 'invalid_key'

    PROCESS_KEY_CREATION = 'instanceCreate'
    PROCESS_KEY_DELETE = 'instanceDelete'
    PROCESS_KEY_UPDATE = 'instanceUpdate'
    PROCESS_ADD_RULE = 'addRule'

    create_task = None
    update_task = None
    patch_task = None
    delete_task = None
    action_task = None

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceType.__init__(self, *args, **kvargs)

        # use this attribute in plugin to point service instance
        self.instance: ApiServiceInstance = None
        self.active_task = None
        self.resource = {}
        self.parent = None
        self.account = None
        self.definition_name = None

    @property
    def resource_uuid(self):
        if self.instance is not None:
            return self.instance.resource_uuid
        else:
            return None

    @property
    def tags(self):
        if self.instance is not None:
            return [t.name for t in self.instance.get_tags()]
            #
            # if self.instance.model.inst_tags is not None:
            #     return self.instance.model.inst_tags.split(',')
            # else:
            #     return []
        else:
            return []

    @property
    def config(self) -> ApiServiceInstanceConfig:
        """Get property from config

        :return:
        """
        if self.instance is not None:
            if self.instance.config_object is None:
                self.instance.get_main_config()
            if self.instance.config_object is not None:
                return self.instance.config_object
            else:
                self.logger.error(f"No config found for instance objid: {self.instance.objid}")
                return None
        return None

    def get_parent(self):
        """Get parent service type plugin instance

        :return: ServiceInstance
        """
        plugin = None
        if self.instance is not None:
            parent = self.instance.get_parent()
            if parent is not None:
                plugin = parent.get_service_type_plugin()
        return plugin

    def get_account(self):
        """Get account

        :return: Account instance
        """
        if self.instance is not None:
            account = self.instance.get_account()
            return account
        return None

    @staticmethod
    def customize_list(controller, entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation
        after entity was created. Used only for synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        return entities

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)

        self.parent = self.instance.get_parent()
        if self.parent is not None:
            parent = {'uuid': self.parent.uuid, 'name': self.parent.name}
        else:
            parent = {}

        info.update({
            '__meta__': {
                'objid': self.instance.objid,
                'type': self.instance.objtype,
                'definition': self.instance.objdef,
                'uri': self.instance.objuri,
            },
            'id': self.instance.oid,
            'uuid': self.instance.uuid,
            'name': self.instance.name,
            # 'account_id': str(self.instance.account_id),
            'account': self.instance.account.small_info(),
            'definition_id': str(self.instance.service_definition_id),
            'definition_name': self.definition_name,
            'bpmn_process_id': self.instance.bpmn_process_id,
            'resource_uuid': self.instance.resource_uuid,
            'status': self.get_status(),
            'parent': parent,
            'is_container': str2bool(self.instance.is_container()),
            'config': self.instance.config,
            'last_error': self.instance.model.last_error,
            'plugintype': self.plugintype,
            'tags': self.tags,
            'date': {
                'creation': format_date(self.instance.model.creation_date),
                'modified': format_date(self.instance.model.modification_date),
                'expiry': format_date(self.instance.model.expiry_date),
            }
        })

        # if self.account is not None:
        #     info['account'] = self.account.small_info()
        #
        # if self.definition is not None:
        #     info['definition'] = self.definition.small_info()

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        pass

    def get_status(self):
        """Get service instance status"""
        return self.instance.status

    def check_status(self):
        """Check service instance status"""
        # check status
        accepted_state = [SrvStatusType.ACTIVE, SrvStatusType.ERROR]
        if self.get_status() not in accepted_state:
            raise ApiManagerError('Service is not in a correct status')

    def is_active(self):
        """Check if object has status ACTIVE

        :return: True if active
        """
        if self.get_status() == 'ACTIVE':
            return True
        return False

    def update_status(self, status, error=None):
        """Update connected service instance status

        :param status: status
        :param error: error [optional]
        """
        if self.instance is not None:
            self.instance.update_status(status, error=error)

    def set_resource(self, resource):
        """Update service instance resource

        :param resource: resource uuid
        :param error: error [optional]
        """
        if self.instance is not None:
            self.instance.set_resource(resource)

    def get_child_type_plugin_instances(self, plugin_class=None):
        """Get instance children of a specific plugintype

        TODO: query must be optimized. Make too much db query

        :param plugin_class: ServiceType extended class
        :return: list of type plugins instance
        """
        plugins = []
        plugintype = None
        if plugin_class is not None:
            plugintype = plugin_class.plugintype
        childs = self.manager.get_service_instance_children(start_service_id=self.instance.oid, plugintype=plugintype)
        for child in childs:
            instance = ApiServiceInstance(self.controller, oid=child.id, objid=child.objid, name=child.name,
                                          desc=child.desc, active=child.active, model=child)
            instance.get_main_config()
            plugin = instance.get_service_type_plugin()
            plugins.append(plugin)
        self.logger.debug('Get type plugin instance %s childs: %s' % (self.uuid, truncate(plugins)))
        return plugins

    def is_availability_zone_active(self, compute_zone, availability_zone_name):
        """Return true if compute service availability zone status is ACTIVE

        :return compute_zone: compute zone uuid or name
        :param availability_zone_name: availability zone name
        :return: True or False
        """
        if self.get_resource_availability_zone_status(compute_zone, availability_zone_name) == 'ACTIVE':
            return True
        return False

    #
    # config
    #
    def get_config(self, attr_key: str):
        """Get property from config

        :param attr_key: property name
        :return:
        """
        if self.instance is not None:
            if self.instance.config_object is None:
                self.instance.get_main_config()
            if self.instance.config_object is not None:
                return self.instance.config_object.get_json_property(attr_key)
            else:
                self.logger.error(f"No config found for instance objid: {self.instance.objid}")
                return None
        return None

    def set_config(self, attr_key, attr_value):
        """Set property in config

        :param attr_key: property name
        :param attr_value: property value
        :return:
        """
        if self.instance is not None:
            if self.instance.config_object is None:
                self.instance.get_main_config()
            self.instance.config_object.set_json_property(attr_key, attr_value)

    #
    # pre, post function
    #
    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :param params.id: inst.oid,
        :param params.uuid: inst.uuid,
        :param params.objid: inst.objid,
        :param params.name: name,
        :param params.desc: desc,
        :param params.attribute: None,
        :param params.tags: None,
        :param params.resource_id: resource_id
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    def post_create(self, **params):
        """Post create function. Use this after service creation
        Extend this function to execute some operation after entity was created.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_import(self, **params):
        """Check input params before resource import. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        Service instance config is populated with: owner_id, service_definition_id, computeZone

        :param params: input params
        :param params.id: inst.oid,
        :param params.uuid: inst.uuid,
        :param params.objid: inst.objid,
        :param params.name: name,
        :param params.desc: desc,
        :param params.attribute: None,
        :param params.tags: None,
        :param params.resource_id: resource_id
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    def post_import(self, **params):
        """Post import function. Use this after service creation.
        Extend this function to execute some operation after entity was created.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_update(self, **params):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    def post_update(self, **params):
        """Post update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_patch(self, **params):
        """Pre patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    def post_patch(self, **params):
        """Post patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_action(self, **params):
        """Pre action function. This function is used in update method. Extend this function to manipulate and
        validate input params.
        The method may add to params the key action_task the name of task to be executed that can override
        self.action_task. If not present self.action_task wil be used

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    def post_action(self, **params):
        """Post action function. This function is used in update method. Extend this function to manipulate and
        validate action input params.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        return params

    def post_delete(self, **params):
        """Post delete function. This function is used in delete method. Extend this function to execute action after
        object was deleted.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    #
    # update
    #
    @trace(op='update')
    def update(self, **params):
        """Update service using a celery task or the synchronous function update_internal.

        :param params: custom params required by task
        :param params.parent_id: id of the parent service instance [optional]
        :param params.sync: if True run sync task, if False run async task
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.instance.verify_permisssions('update')

        # check status
        self.check_status()
        # if self.get_status() not in [SrvStatusType.ACTIVE]:
        #     raise ApiManagerError('Service is not in a correct status')

        # run an optional pre update function
        params = self.pre_update(**params)
        self.logger.debug('params after pre update: %s' % params)

        # change resource state
        self.update_status(SrvStatusType.BUILDING)

        # get sync status of the task
        sync = params.pop('sync', False)
        self.logger.debug('task sync: %s' % sync)

        # force update with internal update
        force = params.pop('force', False)
        self.logger.debug('Force update: %s' % force)

        # get param to update in the service instance record
        parent_id = params.pop('parent_id', None)
        resource_uuid = params.pop('resource_uuid', None)
        tags = params.pop('tags', None)

        # update model
        update_model_params = {'oid': self.instance.oid}
        if resource_uuid is not None:
            update_model_params['resource_uuid'] = resource_uuid

        self.instance.update_object(**update_model_params)

        # update parent
        if parent_id is not None:
            parent_plugin = self.controller.get_service_type_plugin(parent_id)
            # link instance to parent instance
            link_name = 'lnk_%s_%s' % (parent_plugin.instance.oid, self.instance.oid)
            self.controller.add_service_instlink(link_name, parent_plugin.instance.oid, self.instance.oid)
            self.logger.info('Link service instance %s to parent instance %s' %
                             (self.instance.uuid, parent_plugin.instance.uuid))

        # update tags
        if tags is not None:
            cmd = tags.get('cmd')
            values = tags.get('values')
            try:
                # add tag
                if cmd == 'add':
                    for value in values:
                        self.instance.add_tag(value)
                        # controller.create_service_tag(srv_inst, srv_inst.account_id, value)
                        self.logger.debug('Add tag %s to service instance %s' % (value, self.instance.uuid))
                elif cmd == 'delete':
                    for value in values:
                        # controller.delete_service_tag(srv_inst, srv_inst.account_id, value)
                        self.instance.remove_tag(value)
                        self.logger.debug('Remove tag %s from service instance %s' % (value, self.instance.uuid))
            except Exception as e:
                self.logger.debug(e)
        try:
            # update resource using asynchronous celery task
            if self.update_task is not None and force is False:
                base_params = {
                    'alias': self.plugintype + '.update',
                    'id': self.instance.oid,
                    'uuid': self.instance.uuid,
                    'objid': self.instance.objid,
                    'resource_uuid': self.check_resource(),
                    'resource_params': {},
                    'name': self.instance.name
                }
                base_params.update(**params)
                params = base_params

                params.update(self.get_user())
                res = prepare_or_run_task(self.instance, self.update_task, params, sync=sync)
                self.logger.info('run update task: %s' % res[0])

                if sync is False:
                    self.active_task = res[0]['taskid']
                if sync is True:
                    self.active_task = res[0]

                # post update function
                self.post_update(**params)

            # update service using sync method
            else:
                self.active_task = None

                # post create function
                self.post_update(**params)

                self.update_status(SrvStatusType.ACTIVE)
                self.logger.info('Update service %s' % self.instance.uuid)

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return self

    #
    # patch
    #
    @trace(op='update')
    def patch(self, **params):
        """Update service using a celery task or the synchronous function patch_internal.

        :param params: custom params required by task
        :param params.sync: if True run sync task, if False run async task
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.instance.verify_permisssions('update')

        # check status
        self.check_status()
        # if self.get_status() not in [SrvStatusType.ACTIVE]:
        #     raise ApiManagerError('Service is not in a correct status')

        # run an optional pre patch function
        params = self.pre_patch(**params)
        self.logger.debug('params after pre udpate: %s' % params)

        # change resource state
        self.update_status(SrvStatusType.BUILDING)

        # get sync status of the task
        sync = params.pop('sync', False)
        self.logger.debug('task sync: %s' % sync)

        try:
            # patch resource using asynchronous celery task
            if self.patch_task is not None:
                base_params = {
                    'alias': self.plugintype + '.patch',
                    'id': self.instance.oid,
                    'uuid': self.instance.uuid,
                    'objid': self.instance.objid,
                    'resource_uuid': self.check_resource(),
                    'name': self.instance
                }
                base_params.update(**params)
                params = base_params

                params.update(self.get_user())
                res = prepare_or_run_task(self.instance, self.patch_task, params, sync=sync)
                self.logger.info('run patch task: %s' % res[0])

                if sync is False:
                    self.active_task = res[0]['taskid']
                if sync is True:
                    self.active_task = res[0]

                # post update function
                self.post_patch(**params)

            # patch service using sync method
            else:
                self.active_task = None

                # post create function
                self.post_patch(**params)

                self.update_status(SrvStatusType.ACTIVE)
                self.logger.info('Update service %s' % self.instance.uuid)

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return self

    #
    # action
    #
    @trace(op='update')
    def action(self, **params):
        """Send action to service using a celery task.
        Call pre_action in order to customize parameter and post_action in order to finalize the action

        pre_action may add to params the keys
        action_task the name of task to be executed which override self.action_task. If not present self.action_task
        will be used

        :param params: custom params required by task
        :param params.sync: if True run sync task, if False run async task
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.instance.verify_permisssions('update')

        # check status
        # if self.get_status() not in [SrvStatusType.ACTIVE]:
        #     raise ApiManagerError('Service is not in a correct status')

        # run an optional pre update function
        params = self.pre_action(**params)
        self.logger.debug('params after pre action: %s' % params)

        # change resource state
        # self.update_status(SrvStatusType.BUILDING)

        # get sync status of the task
        sync = params.pop('sync', False)
        self.logger.debug('task sync: %s' % sync)

        action_task = params.pop('action_task', self.action_task)
        # action_task_workflow = params.pop('action_task_workflow', self.action_task_workflow)

        try:
            # update resource using asynchronous celery task
            # if self.action_task is not None:
            if action_task is not None:
                base_params = {
                    'alias': self.plugintype + '.action',
                    'id': self.instance.oid,
                    'uuid': self.instance.uuid,
                    'objid': self.instance.objid,
                    'resource_uuid': self.check_resource(),
                    'name': self.instance.name
                }
                base_params.update(**params)
                params = base_params

                if params.get('steps', None) is None:
                    step = 'beehive_service.task_v2.servicetypeplugin.TypePluginInstanceActionTask.action_resource_step'
                    params['steps'] = [step]

                params.update(self.get_user())
                res = prepare_or_run_task(self.instance, self.action_task, params, sync=sync)
                self.logger.info('run action task: %s' % res[0])

                if sync is False:
                    self.active_task = res[0]['taskid']
                if sync is True:
                    self.active_task = res[0]

                # post update function
                self.post_action(**params)

            # update service using sync method
            else:
                self.active_task = None

                # post create function
                self.post_action(**params)

                # self.update_status(SrvStatusType.ACTIVE)
                # self.logger.info('Update service %s' % self.instance.uuid)

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return self

    #
    # delete
    #
    def delete_instance(self):
        """Delete soft service instance"""
        self.instance = self.controller.get_entity(ApiServiceInstance, ServiceInstance, self.instance.oid)

        config = self.instance.get_main_config()
        if config is not None:
            config.delete(soft=True)
        self.instance.delete(soft=True)

    def expunge_instance(self):
        """Delete hard service instance"""
        self.instance = self.controller.get_entity(ApiServiceInstance, ServiceInstance, self.instance.oid)

        # delete config
        config = self.instance.get_main_config()
        if config is not None:
            config.expunge()

        # delete all links
        links, tot = self.controller.get_links(service=self.instance.oid)
        for link in links:
            self.logger.debug('expunge link %s' % link.uuid)
            link.expunge()

        # delete instance
        self.instance.expunge()

    @trace(op='delete')
    def delete(self, **params):
        """Delete service using a celery task or the synchronous function delete_resource.

        :param params: custom params required by task
        :param params.force: force delete for any states
        :param params.propagate: if True propagate delete to all cmp modules
        :param params.sync: if True run sync task, if False run async task
        :return: celery task instance
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.instance.verify_permisssions('delete')

        force = params.get('force', False)
        propagate = params.get('propagate', True)
        sync = params.pop('sync', False)

        # check status
        # if self.get_status() not in [SrvStatusType.ACTIVE, SrvStatusType.DRAFT, SrvStatusType.PENDING,
        #                              SrvStatusType.ERROR]:
        if force is False:
            if self.get_status() not in [SrvStatusType.ACTIVE, SrvStatusType.ERROR]:
                raise ApiManagerError('Service is not in a correct status')

        # verify service has no childs TODO:
        # params['child_num'] = self.manager.count_resource(parent_id=self.oid)

        if propagate is False:
            self.logger.info('Stop service %s delete propagation' % self.instance.uuid)

            # change resource state
            self.update_status(SrvStatusType.DELETING)

            self.delete_instance()
            self.logger.info('Delete service %s' % self.instance.uuid)
            return True

        # run an optional pre delete function
        params = self.pre_delete(**params)
        self.logger.debug('params after pre delete: %s' % params)

        # if params['child_num'] > 0:
        #     raise ApiManagerError('Resource %s has %s childs. It can not be expunged' %
        #                           (self.oid, params['child_num']))

        # change resource state
        self.update_status(SrvStatusType.DELETING)

        try:
            # delete resource using asynchronous celery task
            if self.delete_task is not None:
                # setup task params
                data = {
                    'alias': self.plugintype + '.delete',
                    'id': self.instance.oid,
                    'uuid': self.instance.uuid,
                    'objid': self.instance.objid,
                    'resource_uuid': self.check_resource(),
                    'name': self.instance.name
                }
                params.update(data)

                params.update(self.get_user())
                res = prepare_or_run_task(self.instance, self.delete_task, params, sync=sync)
                self.logger.info('run delete task: %s' % res[0])

                if sync is False:
                    self.active_task = res[0]['taskid']
                if sync is True:
                    self.active_task = res[0]

                # post delete function
                self.post_delete(**params)

            # delete resource using sync method
            else:
                self.active_task = None

                # post delete function
                self.post_delete(**params)
                self.delete_instance()
                self.logger.info('Delete service %s' % self.instance.uuid)

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return True

    #
    # tags
    #
    @trace(op='update')
    def add_tag(self, value):
        """Add tag

        :param str value: tag value
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        self.instance.add_tag(value)
        if self.check_resource() is not None:
            self.create_resource_tag(value)

    @trace(op='update')
    def remove_tag(self, value):
        """Remove tag

        :param str value: tag value
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        self.instance.remove_tag(value)
        if self.check_resource() is not None:
            self.delete_resource_tag(value)

    #
    # links
    #
    @trace(op='view')
    def get_linked_services(self, link_type=None, link_type_filter=None, *args, **kvargs):
        """Get linked services

        todo: return plugin type

        :param link_type: link type [optional]
        :param link_type_filter: link type filter
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param details: if True execute customize_list()
        :return: :py:class:`list` of :py:class:`ResourceLink`
        :raise ApiManagerError:
        """
        def get_entities(*args, **kvargs):
            res, total = self.manager.get_linked_services(service=self.instance.oid, link_type=link_type,
                                                          link_type_filter=link_type_filter, *args, **kvargs)
            return res, total

        def customize(entities, *args, **kvargs):
            return entities

        res, total = self.controller.get_paginated_entities(ApiServiceInstance, get_entities,
                                                            customize=customize, *args, **kvargs)
        self.logger.debug('Get linked service instances: %s' % res)
        return res, total

    @trace(op='insert')
    def add_link(self, name: str=None, type:str =None, end_service: int=None, attributes=None):
        """Add resource links

        :param name: link name
        :param type: link type
        :param end_service: end service reference id, uuid
        :param attributes: link attributes [optional]
        :return: link uuid
        :raise ApiManagerError:
        """
        link_uuid = self.controller.add_link(name=name, type=type, account=self.instance.account_id,
                                             start_service=self.instance.oid, end_service=end_service,
                                             attributes=attributes)
        link = self.controller.get_link(link_uuid)
        return link

    @trace(op='delete')
    def del_link(self, end_service, type):
        """Delete a link that terminate on the end_service

        :param end_service: end resource name or id
        :return: link id
        """
        links, tot = self.controller.get_links(start_service=self.instance.oid, end_service=end_service, type=type)
        if tot > 0:
            links[0].expunge()
        return links[0]

    #
    # check
    #
    def check(self):
        """Check service plugin instance

        :return: dict with check result. {'check': True, 'msg': None}
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        operation.cache = False
        resource = self.check_resource()

        if resource is None:
            check = False
            msg = 'resource does not exist'
        else:
            check = True
            msg = None
        res = {'check': check, 'msg': msg}
        self.logger.debug2('Check service %s: %s' % (self.uuid, res))
        return res

    #
    # resource methods
    #
    def __get_task_status(self, taskid, module):
        """Query api to get task status

        :param taskid: task id to query
        :param module: module where task is executed
        :return:
        """
        msg = ''
        if module == 'resource':
            uri = '/v2.0/nrs/worker/tasks/%s/status' % taskid
        elif module == 'service':
            uri = '/v2.0/nws/worker/tasks/%s/status' % taskid
        else:
            uri = '/v2.0/nws/worker/tasks/%s/status' % taskid
        try:
            res = self.api_client.admin_request('resource', uri, 'get', silent=True)
            task = res.get('task_instance')
            state = task.get('status')
            self.logger.info('Get task %s state: %s' % (taskid, state))
            if state == 'FAILURE':
                msg = self.__get_task_error(taskid, module)
            return state, msg
        except (NotFoundException, Exception) as ex:
            self.logger.error(ex)
            msg = ex
            return 'FAILURE', msg

    def __get_task_error(self, taskid, module):
        """Query api to get task trace

        :param taskid: task id to query
        :param module: module where task is executed
        :return: task error
        """
        if module == 'resource':
            uri = '/v2.0/nrs/worker/tasks/%s/trace' % taskid
        elif module == 'service':
            uri = '/v2.0/nws/worker/tasks/%s/trace' % taskid
        else:
            uri = '/v2.0/nws/worker/tasks/%s/trace' % taskid
        try:
            res = self.api_client.admin_request('resource', uri, 'get', silent=True)
            trace = res.get('task_trace')[-1]['message']
            self.logger.error('Get task %s trace: %s' % (taskid, trace))
            return trace
        except Exception:
            return None

    def get_task_result(self, taskid, module='resource'):
        """Query api to get task result

        :param taskid: task id to query
        :param module: module where task is executed [default=resource]
        :return: task result
        """
        if module == 'resource':
            uri = '/v2.0/nrs/worker/tasks/%s' % taskid
        elif module == 'service':
            uri = '/v2.0/nws/worker/tasks/%s' % taskid
        else:
            uri = '/v2.0/nws/worker/tasks/%s' % taskid
        try:
            res = self.api_client.admin_request('resource', uri, 'get', silent=True)
            task = res.get('task_instance')
            state = task.get('status')
            result = None
            if state == 'SUCCESS':
                result = task.get('result')
                self.logger.info('Get task %s result: %s' % (taskid, result))
            return result
        except (NotFoundException, Exception) as ex:
            self.logger.error(ex)
            return None

    # FF: ex maxtime=1200
    def wait_for_task(self, taskid, delta=2, maxtime=3600, task=None, module='resource'):
        """Wait for task

        :param taskid: task id
        :param delta: sample time
        :param maxtime: max time to wait
        :param task: task instance
        :param module: module where task is executed. [default=resource]
        :return:
        """

        try:
            self.logger.info('Wait for task: %s' % taskid)
            state, statemsg = self.__get_task_status(taskid, module)
            elapsed = 0
            while state not in ['SUCCESS', 'FAILURE', 'TIMEOUT']:
                sleep(delta)
                state, statemsg = self.__get_task_status(taskid, module)
                if task is not None:
                    task.progress(msg='Get %s task %s status: %s' % (module, taskid, state))
                elapsed += delta
                if elapsed > maxtime:
                    state = 'TIMEOUT'

            if state == 'TIMEOUT':
                msg = '%s task %s timeout' % (module, taskid)
                self.logger.error(msg)
                if task is not None:
                    task.progress(msg='error - %s' % msg)
                raise ApiManagerError('%s action timeout' % module)
            elif state == 'FAILURE':
                # err = self.__get_task_error(taskid, module)
                msg = '%s task %s error: %s' % (module, taskid, statemsg)
                self.logger.error(msg)
                if task is not None:
                    task.progress(msg='error - %s' % msg)
                raise ApiManagerError('%s action error: %s' % (module, statemsg))

            if task is not None:
                task.progress(msg='%s task %s SUCCESS' % (module, taskid))
            self.logger.info('%s task %s SUCCESS' % (module, taskid))

            return state
        except ApiManagerError as ex:
            self.logger.error(ex.value, exc_info=1)
            if task is not None:
                task.progress(msg='error - %s' % ex)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise Exception(ex)

    def check_resource(self, *args, **kvargs):
        """Check resource exists

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            if self.instance.resource_uuid is not None:
                uri = '/v1.0/nrs/entities/%s' % self.instance.resource_uuid
                self.controller.api_client.admin_request('resource', uri, 'get', data='')
                return self.instance.resource_uuid
            else:
                return None
        except ApiManagerError as ex:
            return None

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return None

    def update_resource(self, task, *args, **kvargs):
        """Update resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return None

    def patch_resource(self, task, *args, **kvargs):
        """Patch resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return None

    def action_resource(self, task, *args, **kvargs):
        """Send action to resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return None

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.check_resource() is None:
            return True

        try:
            uri = '/v1.0/nrs/entities/%s?force=true' % self.instance.resource_uuid
            res = self.controller.api_client.admin_request('resource', uri, 'delete', data='')
            taskid = res.get('taskid', None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug('Delete compute instance resources: %s' % res)

        return True

    def create_resource_tag(self, tag_name):
        """Create resource tag

        :param tag_name: tag name
        :return: resource tag uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        name = '%s$%s' % (__SRV_MODULE_BASE_PREFIX__, tag_name)

        try:
            tag_resource = self.api_client.admin_request('resource', '/v1.0/nrs/tags/%s' % name, 'get')
            self.logger.debug('Resource tag %s was found' % name)
        except ApiManagerError as ex:
            self.logger.warn('Resource tag %s was not found. Create a new one' % name)
            uri = '/v1.0/nrs/tags'
            data = {'resourcetag': {'value': name}}
            tag_resource = self.controller.api_client.admin_request('resource', uri, 'post', data=data)

        data = {'resource': {'tags': {'cmd': 'add', 'values': [name]}, 'force': True}}
        uri = '/v1.0/nrs/entities/%s' % self.instance.resource_uuid
        self.api_client.admin_request('resource', uri, 'put', data=data)
        self.logger.debug('Add resource tag %s to resource %s' % (name, self.instance.resource_uuid))

        return tag_resource.get('uuid')

    def delete_resource_tag(self, tag_name):
        """Remove resource tag

        :param tag_name: tag name
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # deassign tag
        name = '%s$%s' % (__SRV_MODULE_BASE_PREFIX__, tag_name)
        data = {'resource': {'tags': {'cmd': 'remove', 'values': [name]}, 'force': True}}
        uri = '/v1.0/nrs/entities/%s' % self.instance.resource_uuid
        self.api_client.admin_request('resource', uri, 'put', data=data)
        self.logger.debug('Remove resource tag %s from resource %s' % (name, self.instance.resource_uuid))

        # remove tag
        name = '%s$%s' % (__SRV_MODULE_BASE_PREFIX__, tag_name)
        uri = '/v1.0/nrs/tags/%s' % name
        self.controller.api_client.admin_request('resource', uri, 'delete', data=data)
        self.logger.debug('Remove resource tag %s ' % name)

        return True

    def get_resource_availability_zones(self, compute_zone):
        """Get compute service availability zones

        :return compute_zone: compute zone uuid or name
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = '/v1.0/nrs/provider/compute_zones/%s/availability_zones' % compute_zone
        res = self.controller.api_client.admin_request('resource', uri, 'get', data='').get('availability_zones', [])
        self.controller.logger.debug('Get compute service %s availability zones: %s' % (compute_zone, truncate(res)))
        return res

    def get_resource_main_availability_zone(self):
        """Get service instance main availability zone

        :return: avz id or None
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            if self.instance.resource_uuid is not None:
                uri = '/v1.0/nrs/entities/%s' % self.instance.resource_uuid
                res = self.controller.api_client.admin_request('resource', uri, 'get', data='')
                return dict_get(res, 'resource.attributes.availability_zone', default=None)
            else:
                return None
        except ApiManagerError as ex:
            return None

    def get_resource_availability_zone_status(self, compute_zone, availability_zone_name):
        """Get compute service availability zone

        :param compute_zone: compute zone uuid or name
        :param availability_zone_name: availability zone name
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        avzs = self.get_resource_availability_zones(compute_zone)
        res = None
        for avz in avzs:
            if dict_get(avz, 'site.name') == availability_zone_name:
                res = dict_get(avz, 'state')
        if res is None:
            raise ApiManagerError('Availability zone %s was not found' % availability_zone_name)
        return res

    def check_quotas(self, compute_zone, quotas):
        """Check compute zone quotas are respected

        :param compute_zone: compute zone uuid or name
        :param quotas: quotas to check. Dict like {"compute.instances":500}
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {'quotas': quotas}
        uri = '/v1.0/nrs/provider/compute_zones/%s/quotas/check' % compute_zone
        self.controller.api_client.admin_request('resource', uri, 'put', data=data, timeout=180)
        return True

    def get_flavor(self, flavor_resource_uuid):
        """Get flavor resource info

        :param flavor_resource_uuid: flavor resource uuid
        :return: Dictionary with resource info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = '/v1.0/nrs/provider/flavors/%s' % flavor_resource_uuid
        flavor = self.controller.api_client.admin_request('resource', uri, 'get').get('flavor')
        self.logger.debug('Get resource flavor: %s' % flavor)

        return flavor

    def get_image(self, image_resource_uuid):
        """Get image resource info

        :param image_resource_uuid: image resource uuid
        :return: Dictionary with resource info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = '/v1.0/nrs/provider/images/%s' % image_resource_uuid
        image = self.controller.api_client.admin_request('resource', uri, 'get').get('image')
        self.logger.debug('Get resource image: %s' % image)

        return image


class AsyncApiServiceTypePlugin(ApiServiceTypePlugin):
    """Basic async resource
    """
    task_path = 'beehive_service.task_v2.servicetypeplugin.AbstractServiceTypePluginTask.'

    create_task = 'beehive_service.task_v2.servicetypeplugin.service_type_plugin_inst_task'
    update_task = 'beehive_service.task_v2.servicetypeplugin.service_type_plugin_inst_update_task'
    patch_task = 'beehive_service.task_v2.servicetypeplugin.service_type_plugin_inst_patch_task'
    delete_task = 'beehive_service.task_v2.servicetypeplugin.service_type_plugin_inst_delete_task'
    action_task = 'beehive_service.task_v2.servicetypeplugin.service_type_plugin_inst_action_task'


class ApiServiceTypeContainer(AsyncApiServiceTypePlugin):
    objuri = 'stcontainer'
    objname = 'stcontainer'
    objdesc = 'ServiceTypeContainer'

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

    @trace(op='view')
    def get_resource(self):
        """Get resource info

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = '/v1.0/nrs/provider/compute_zones/%s' % self.instance.resource_uuid
        instances = self.controller.api_client.admin_request('resource', uri, 'get', data='').get('compute_zone')
        self.logger.debug('Get compute service resource: %s' % truncate(instances))
        return instances

    @trace(op='view')
    def list_resources(self, uuids=None, tags=None, page=0, size=100):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if uuids is None:
            uuids = []
        if tags is None:
            tags = []

        data = {
            'size': size,
            'page': page
        }
        if len(uuids) > 0:
            data['uuids'] = ','.join(uuids)
        if len(tags) > 0:
            data['tags'] = ','.join(tags)
        instances = self.controller.api_client.admin_request('resource', '/v1.0/nrs/provider/compute_zones', 'get',
                                                             data=urlencode(data)).get('compute_zones', [])
        self.logger.debug('Get compute service resources: %s' % truncate(instances))
        return instances

    def get_resource_quotas(self):
        """Get compute service quotas

        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = '/v1.0/nrs/provider/compute_zones/%s/quotas' % self.instance.resource_uuid
        res = self.controller.api_client.admin_request('resource', uri, 'get', data='').get('quotas', [])
        self.controller.logger.debug('Get compute service %s quotas: %s' % (self.instance.resource_uuid, truncate(res)))
        return res

    def set_resource_quotas(self, task, quotas):
        """Set compute service quotas

        :param quotas: dict with quotas to set
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            data = {'quotas': quotas}
            uri = '/v1.0/nrs/provider/compute_zones/%s/quotas' % self.instance.resource_uuid
            res = self.controller.api_client.admin_request('resource', uri, 'put', data=data)
            taskid = res.get('taskid', None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.controller.logger.debug('Set compute service %s quotas: %s' % (self.instance.resource_uuid, truncate(res)))

        return res

    def get_resource_availability_zones(self):
        """Get compute service availability zones

        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = ApiServiceTypePlugin.get_resource_availability_zones(self, self.instance.resource_uuid)
        return res

    def get_attributes(self, prefix=None):
        """Get plugin attributes quota

        :return:
        """
        if self.resource is None:
            self.resource = {}

        attributes = []

        quote = self.get_resource_quotas()
        for quota in quote:
            name = quota.get('quota')
            if name.find(prefix) == 0:
                name = name.replace(prefix+'.', '')
                quota['quota'] = name
                attributes.append(quota)

        return attributes

    def get_container_attributes(self, prefix):
        """Get plugin attributes quota

        :return:
        """
        if self.resource is None:
            self.resource = {}

        attributes = []

        quote = self.get_resource_quotas()
        for quota in quote:
            name = quota.get('quota')
            if name.find(prefix) == 0:
                name = name.replace(prefix+'.', '')
                quota['quota'] = name
                attributes.append(quota)

        return attributes


# class ApiServiceCostParam(ServiceApiObject):
#     objdef = ApiObject.join_typedef(ApiServiceType.objdef, 'ServiceCostParam')
#     objuri = 'servicecostparam'
#     objname = 'servicecostparam'
#     objdesc = 'ServiceCostParam'
#
#     def __init__(self, *args, **kvargs):
#         """ """
#         ServiceApiObject.__init__(self, *args, **kvargs)
#
#         if self.model is not None:
#             self.service_type_id = self.model.service_type_id
#             self.param_unit = self.model.param_unit
#             self.param_definition = self.model.param_definition
#
#             # child classes
#         self.child_classes = []
#
#         self.update_object = self.manager.update_service_cost_param
#
#         # Hard delete
#         self.delete_object = self.manager.purge
#
#     def info(self):
#         """Get object info
#
#         :return: Dictionary with object info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         info = ServiceApiObject.info(self)
#         info.update({
#             'service_type_id': str(self.service_type_id),
#             'param_unit': self.param_unit,
#             'param_definition': self.param_definition
#         })
#         return info
#
#     def detail(self):
#         """Get object extended info
#
#         :return: Dictionary with object detail.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         info = self.info()
#         return info


class ApiServiceProcess(ServiceApiObject):
    objdef = ApiObject.join_typedef(ApiServiceType.objdef, 'ServiceProcess')
    objuri = 'serviceprocess'
    objname = 'serviceprocess'
    objdesc = 'serviceprocess'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.service_type_id = None
        self.method_key = None
        self.process_key = None
        self.template = None

        if self.model is not None:
            self.service_type_id = self.model.service_type_id
            self.method_key = self.model.method_key
            self.process_key = self.model.process_key
            self.template = self.model.template

        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_process

        # Hard delete
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'service_type_id': str(self.service_type_id),
            'method_key': self.method_key,
            'process_key': self.process_key,
            'template': self.template
        })
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info
