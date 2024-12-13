# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from copy import deepcopy
from beehive.common.apimanager import ApiManagerError
from beehive_service.entity.service_type import ApiServiceTypeContainer
from beehive_service.model.base import SrvStatusType
from beecell.simple import format_date, obscure_data
from beehive_service.plugins.databaseservice.entity.instance_v2 import (
    ApiDatabaseServiceInstanceV2,
)


class ApiDatabaseService(ApiServiceTypeContainer):
    objuri = "databaseservice"
    objname = "databaseservice"
    objdesc = "DatabaseService"
    plugintype = "DatabaseService"

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
        return ApiServiceTypeContainer.info(self)

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
        account_ids = {e.instance.account_id for e in entities}
        account_idx = controller.get_account_idx(id_list=account_ids)
        instance_type_idx = controller.get_service_definition_idx(ApiDatabaseService.plugintype)

        # get resources
        resources = set()
        for entity in entities:
            entity_instance = entity.instance
            entity.account = account_idx.get("%s" % entity_instance.account_id)
            entity.instance_type = instance_type_idx.get("%s" % entity_instance.service_definition_id)
            if entity_instance.resource_uuid is not None:
                resources.add(entity_instance.resource_uuid)

        resources_idx = {}
        if len(resources) > 0:
            resources_list = ApiDatabaseService(controller).list_resources(uuids=resources)
            resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        compute_services, tot = self.controller.get_paginated_service_instances(
            plugintype="ComputeService",
            account_id=self.instance.account_id,
            filter_expired=False,
        )
        if tot == 0:
            raise ApiManagerError("Some service dependency does not exist")

        compute_service = compute_services[0]

        if compute_service.is_active() is False:
            raise ApiManagerError("Some service dependency are not in the correct status")

        # set resource uuid
        self.set_resource(compute_service.resource_uuid)

        params["resource_params"] = {}
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: "pending",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETED: "deregistered",
            SrvStatusType.DRAFT: "trasient",
            SrvStatusType.ERROR: "error",
        }
        return mapping.get(state, "error")

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        instance_item = {}
        instance_item["id"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["creationDate"] = format_date(self.instance.model.creation_date)
        instance_item["description"] = self.instance.desc
        instance_item["state"] = self.state_mapping(self.instance.status)
        instance_item["owner"] = self.account.uuid
        instance_item["owner_name"] = self.account.name
        instance_item["template"] = self.instance_type.uuid
        instance_item["template_name"] = self.instance_type.name
        instance_item["stateReason"] = {"code": None, "message": None}
        # reason = self.resource.get('reason', None)
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "code": 400,
                "message": self.instance.last_error,
            }
        instance_item["resource_uuid"] = self.instance.resource_uuid

        return instance_item

    def aws_get_attributes(self):
        """Get account attributes like quotas

        :return:
        """
        if self.resource is None:
            self.resource = {}
        attributes = []

        for quota in self.get_resource_quotas():
            name = quota.get("quota")
            if name.find("database") == 0:
                name = name.replace("database.", "")
                attributes_item = {
                    "attributeName": "%s [%s]" % (name, quota.get("unit")),
                    "attributeValueSet": [
                        {
                            "item": {
                                "attributeValue": quota.get("value"),
                                "nvl-attributeUsed": quota.get("allocated"),
                            }
                        }
                    ],
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
            data["database.%s" % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix="database"):
        return self.get_container_attributes(prefix=prefix)

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.update_status(SrvStatusType.PENDING)
        quotas = self.get_config("quota")
        self.set_resource_quotas(task, quotas)

        # update service status
        self.update_status(SrvStatusType.CREATED)
        self.logger.debug("Update database instance resources: %s" % self.instance.resource_uuid)

        return self.instance.resource_uuid

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource do nothing. Compute zone is owned by ComputeService

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return True


class ApiDatabaseServiceInstance(ApiDatabaseServiceInstanceV2):
    pass


# class ApiDatabaseServiceInstance(AsyncApiServiceTypePlugin):
#     plugintype = 'DatabaseInstance'
#     objname = 'dbinstance'
#
#     def __init__(self, *args, **kvargs):
#         """ """
#         ApiServiceTypePlugin.__init__(self, *args, **kvargs)
#
#         self.child_classes = []
#
#     def info(self):
#         """Get object info
#         :return: Dictionary with object info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         info = ApiServiceTypePlugin.info(self)
#         info.update({})
#         return info
#
#     @staticmethod
#     def customize_list(controller, entities, *args, **kvargs):
#         """Post list function. Extend this function to execute some operation after entity was created. Used only for
#         synchronous creation.
#
#         :param controller: controller instance
#         :param entities: list of entities
#         :param args: custom params
#         :param kvargs: custom params
#         :return: None
#         :raise ApiManagerError:
#         """
#         account_idx = controller.get_account_idx()
#         subnet_idx = controller.get_service_instance_idx(ApiComputeSubnet.plugintype)
#         vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)
#         security_group_idx = controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)
#         instance_type_idx = controller.get_service_definition_idx(ApiDatabaseServiceInstance.plugintype)
#         compute_service_idx = controller.get_service_instance_idx(ApiComputeService.plugintype, index_key='account_id')
#
#         # get resources
#         zones = []
#         resources = []
#         for entity in entities:
#             entity.account = account_idx.get(str(entity.instance.account_id))
#             entity.compute_service = compute_service_idx.get(str(entity.instance.account_id))
#             entity.subnet = subnet_idx.get(str(entity.get_config('dbinstance.DBSubnetGroupName')))
#             if entity.subnet is not None:
#                 entity.subnet_vpc = vpc_idx.get(entity.subnet.get_parent_id())
#                 entity.avzone = entity.subnet.get_config('site')
#             else:
#                 entity.subnet_vpc = None
#                 entity.avzone = None
#
#             # get security groups
#             entity.security_groups = []
#             sgs = entity.get_config('dbinstance.VpcSecurityGroupIds.VpcSecurityGroupId')
#             if sgs is not None:
#                 for sg in sgs:
#                     entity.security_groups.append(security_group_idx.get(str(sg)))
#
#             # get instance type
#             entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
#
#             if entity.compute_service.resource_uuid not in zones:
#                 zones.append(entity.compute_service.resource_uuid)
#             if entity.instance.resource_uuid is not None:
#                 resources.append(entity.instance.resource_uuid)
#
#         if len(resources) == 0:
#             resources_idx = {}
#         else:
#             if len(resources) > 3:
#                 resources = []
#             else:
#                 zones = []
#             if len(zones) > 40:
#                 zones = []
#             resources_list = ApiDatabaseServiceInstance(controller).list_resources(zones=zones, uuids=resources)
#             resources_idx = {r['uuid']: r for r in resources_list}
#
#         # assign resources
#         for entity in entities:
#             entity.resource = resources_idx.get(entity.instance.resource_uuid)
#
#         return entities
#
#     def post_get(self):
#         """Post get function. This function is used in get_entity method. Extend this function to extend description
#         info returned after query.
#
#         :raise ApiManagerError:
#         """
#         self.account = self.controller.get_account(str(self.instance.account_id))
#         if self.get_config('dbinstance.DBSubnetGroupName') is not None:
#             self.subnet = self.controller.get_service_instance(self.get_config('dbinstance.DBSubnetGroupName'))
#             self.subnet_vpc = self.controller.get_service_instance(self.subnet.get_parent_id())
#             self.avzone = self.subnet.get_config('site')
#         else:
#             self.subnet = None
#             self.subnet_vpc = None
#             self.avzone = None
#
#         # get security groups
#         self.security_groups = []
#         if self.get_config('dbinstance.VpcSecurityGroupIds.VpcSecurityGroupId') is not None:
#             for sg in self.get_config('dbinstance.VpcSecurityGroupIds.VpcSecurityGroupId'):
#                 self.security_groups.append(self.controller.get_service_instance(sg))
#
#         # get instance type
#         self.instance_type = self.controller.get_service_def(self.instance.service_definition_id)
#
#         # assign resources
#         if self.instance.resource_uuid is not None:
#             resources_list = self.list_resources(uuids=[self.instance.resource_uuid])
#             if len(resources_list) > 0:
#                 self.resource = resources_list[0]
#
#     def state_mapping(self, state):
#         mapping = {
#             SrvStatusType.PENDING: 'pending',
#             SrvStatusType.BUILDING: 'building',
#             SrvStatusType.CREATED: 'building',
#             SrvStatusType.ACTIVE: 'available',
#             SrvStatusType.DELETED: 'deregistered',
#             SrvStatusType.DRAFT: 'transient',
#             SrvStatusType.ERROR: 'error'
#         }
#         return mapping.get(state, 'error')
#
#     def aws_info(self):
#         """Get info as required by aws api
#
#         :param inst_service:
#         :param resource:
#         :param account_idx:
#         :param instance_type_idx:
#         :return:
#         """
#         instance_item = {}
#
#         # get config
#         config = self.get_config('dbinstance')
#         if config is None:
#             config = {}
#
#         # get subnet
#         subnet = self.subnet
#         subnet_vpc = self.subnet_vpc
#         subnet_vpc_id = getattr(subnet_vpc, 'uuid', None)
#         subnet_vpc_name = getattr(subnet_vpc, 'name', None)
#         avzone = self.avzone
#
#         # resInst = resource.get('stack', {})
#         if self.resource is None:
#             self.resource = {}
#
#         # resource attributes
#         attributes = self.resource.get('attributes', {})
#
#         # resource stack ref
#         stacks = self.resource.get('stacks', [])
#         avz_main_stack = {}
#         if len(stacks) > 0:
#             avz_main_stack = stacks[0]
#         address, port = None, None
#         if avz_main_stack.get('listener', ':') is not None:
#             address, port = avz_main_stack.get('listener', ':').split(':')
#
#         instance_item['AllocatedStorage'] = int(config.get('AllocatedStorage', -1))
#         instance_item['AutoMinorVersionUpgrade'] = None
#         instance_item['AvailabilityZone'] = avzone
#         if config.get('BackupRetentionPeriod', None) is not None:
#             instance_item['BackupRetentionPeriod'] = int(config.get('BackupRetentionPeriod', -1))
#         instance_item['CACertificateIdentifier'] = ''
#         instance_item['CharacterSetName'] = config.get('CharacterSetName')
#         instance_item['DBInstanceClass'] = self.instance_type.name
#         instance_item['DBInstanceIdentifier'] = self.instance.uuid
#         instance_item['DbInstancePort'] = port
#         instance_item['DBInstanceStatus'] = self.state_mapping(self.instance.status)
#         instance_item['DbiResourceId'] = ''
#         instance_item['DBName'] = config.get('DBName')
#
#         instance_item['nvl-stateReason'] = {'nvl-code': None, 'nvl-message': None}
#         if self.instance.status == 'ERROR':
#             instance_item['nvl-stateReason'] = {'nvl-code': '400', 'nvl-message': self.instance.last_error}
#
#         # reason = self.resource.get('reason', None)
#         # if reason is not None:
#         #     instance_item['nvl-stateReason'] = {'nvl-code': '400', 'nvl-message': reason.get('error')}
#
#         dbSubnetGroupItem = {}
#         dbSubnetGroupItem['DBSubnetGroupArn'] = ''
#         dbSubnetGroupItem['DBSubnetGroupDescription'] = getattr(subnet, 'desc', '')
#         dbSubnetGroupItem['DBSubnetGroupName'] = getattr(subnet, 'name', '')
#         dbSubnetGroupItem['SubnetGroupStatus'] = getattr(subnet, 'status', '')
#         dbSubnetGroupItem['Subnets'] = [
#             {
#                 'SubnetAvailabilityZone': {'AvailabilityZone': {'Name': avzone}},
#                 'SubnetIdentifier': getattr(subnet, 'uuid', ''),
#                 'SubnetStatus': getattr(subnet, 'status', '')
#             }
#         ]
#         dbSubnetGroupItem['VpcId'] = subnet_vpc_id
#         instance_item['DBSubnetGroup'] = dbSubnetGroupItem
#
#         instance_item['Endpoint'] = {'Address': address, 'Port': port}
#         instance_item['Engine'] = attributes.get('engine', None)
#         instance_item['EngineVersion'] = attributes.get('version', None)
#         instance_item['InstanceCreateTime'] = format_date(self.instance.model.creation_date)
#         instance_item['LatestRestorableTime'] = format_date(self.instance.model.modification_date)
#         instance_item['LicenseModel'] = ''
#         instance_item['MasterUsername'] = config.get('MasterUsername')
#         instance_item['MultiAZ'] = config.get('MultiAZ')
#
#         instance_item['PendingModifiedValues'] = {}
#
#         instance_item['PreferredBackupWindow'] = config.get('PreferredBackupWindow')
#         instance_item['PreferredMaintenanceWindow'] = config.get('PreferredMaintenanceWindow')
#         instance_item['PubliclyAccessible'] = config.get('PubliclyAccessible')
#         instance_item['ReadReplicaDBClusterIdentifiers'] = []
#         instance_item['ReadReplicaDBInstanceIdentifiers'] = []
#         instance_item['ReadReplicaSourceDBInstanceIdentifier'] = ''
#         instance_item['SecondaryAvailabilityZone'] = ''
#         instance_item['StatusInfos'] = [{'Status': self.state_mapping(self.instance.status)}]
#         instance_item['StorageEncrypted'] = config.get('StorageEncrypted')
#         instance_item['StorageType'] = config.get('StorageType')
#
#         instance_item['VpcSecurityGroups'] = [
#             {
#                 'VpcSecurityGroupMembership': {
#                     'VpcSecurityGroupId': sg.uuid,
#                     'Status': None,
#                     'nvl-vpcSecurityGroupName': sg.name
#                 }
#             } for sg in self.security_groups]
#
#         # custom params
#         instance_item['nvl-name'] = self.instance.name
#         instance_item['nvl-ownerAlias'] = self.account.name
#         instance_item['nvl-ownerId'] = self.account.uuid
#         instance_item['nvl-resourceId'] = self.instance.resource_uuid
#
#         return instance_item
#
#     def pre_create(self, **params)-> dict:> dict:
#         """Check input params before resource creation. Use this to format parameters for service creation
#         Extend this function to manipulate and validate create input params.
#
#         :param params: input params
#         :return: resource input params
#         :raise ApiManagerError:
#         """
#         account_id = self.instance.account_id
#
#         # base quotas
#         quotas = {
#             'database.cores': 0,
#             'database.instances': 1,
#             'database.ram': 0,
#         }
#
#         # get container
#         container_id = self.get_config('container')
#         flavor_resource_uuid = self.get_config('flavor')
#         image_resource_uuid = self.get_config('image')
#         compute_zone = self.get_config('computeZone')
#         data_instance = self.get_config('dbinstance')
#
#         # get Flavor resource Info
#         flavor_resource = self.get_flavor(flavor_resource_uuid)
#         # try to get main volume size from flavor
#         flavor_configs = flavor_resource.get('attributes', None).get('configs', None)
#         quotas['database.cores'] = flavor_configs.get('vcpus', 0)
#         quotas['database.ram'] = flavor_configs.get('memory', 0)
#         if quotas['database.ram'] > 0:
#             quotas['database.ram'] = quotas['database.ram'] / 1024
#
#         # db_appuser_name = self.get_config('db_appuser_name')
#         # db_appuser_password = self.get_config('db_appuser_password')
#
#         # get availability zone from request parameters
#         av_zone = data_instance.get('AvailabilityZone', None)
#
#         # check subnet
#         subnet_id = data_instance.get('DBSubnetGroupName', None)
#         if subnet_id is None:
#             raise ApiManagerError('Subnet is not defined')
#
#         subnet_inst = self.controller.check_service_instance(subnet_id, ApiComputeSubnet, account=account_id)
#         if av_zone is None:
#             subnet_inst.get_main_config()
#             av_zone = subnet_inst.get_config('site')
#
#         # check availability zone status
#         if self.is_availability_zone_active(compute_zone, av_zone) is False:
#             raise ApiManagerError('Availability zone %s is not in available status' % av_zone)
#
#         # get key name
#         key_name = data_instance.get('Nvl_KeyName', None)
#         # get key name from database definition
#         if key_name is None:
#             key_name = self.get_config('key_name').get(av_zone, None)
#         else:
#             ApiComputeKeyPairsHelper(self.controller).check_service_instance(key_name, account_id)
#
#         # get and check the id SecurityGroupId
#         security_group_ress = []
#         for security_group in data_instance.get('VpcSecurityGroupIds', {}).get('VpcSecurityGroupId', []):
#             sg_inst = self.controller.check_service_instance(security_group, ApiComputeSecurityGroup,
#                                                              account=account_id)
#             if sg_inst.resource_uuid is None:
#                 raise ApiManagerError('SecurityGroup id %s is invalid' % security_group)
#             security_group_ress.append(sg_inst.resource_uuid)
#
#             # link security group to db instance
#             self.instance.add_link(name='link-%s-%s' % (self.instance.oid, sg_inst.oid), type='sg',
#                                    end_service=sg_inst.oid, attributes={})
#
#         if len(security_group_ress) == 0:
#             raise ApiManagerError('VpcSecurityGroupId is not correct')
#
#         # get vpc
#         vpc_resource_uuid = self.controller.get_service_instance(
#             subnet_inst.model.linkParent[0].start_service_id).resource_uuid
#
#         # get engine
#         engine = data_instance.get('Engine')
#         engineVersion = data_instance.get('EngineVersion')
#         multiAZ = data_instance.get('MultiAZ')
#         if multiAZ:
#             av_zone = None
#
#         # data_instance.get('AllocatedStorage',0)
#         # data_instance.get('AvailabilityZone', None)
#         # data_instance.get('BackupRetentionPeriod', 1)
#         # data_instance.get('CharacterSetName', None)
#         # data_instance.get('LicenseModel')
#         # data_instance('Port')
#         # data_instance('PreferredBackupWindow', '2018-01-22T20:54Z')
#         # data_instance('PreferredMaintenanceWindow', '2018-01-22T20:54Z')
#         # data_instance('PubliclyAccessible', False)
#         # data_instance('StorageEncrypted', False)
#         # data_instance('StorageType', None)
#         # data_instance('Tag_N', [])
#
#         # check quotas
#         self.check_quotas(compute_zone, quotas)
#
#         # name = '%s-%s' % (self.instance.name, id_gen(length=8))
#         name = self.instance.name
#
#         dbname = data_instance.get('DBName', 'test')
#         if dbname is not None:
#             dbname = dbname.lower()
#
#         data = {
#             'container': container_id,
#             'compute_zone': compute_zone,
#             'availability_zone': av_zone,
#             'flavor': flavor_resource_uuid,
#             'image': image_resource_uuid,
#             'vpc': vpc_resource_uuid,
#             'subnet': subnet_inst.get_config('cidr'),
#             'security_group': security_group_ress[0],
#             'db_name': dbname,
#             # 'db_appuser_name': db_appuser_name,
#             # 'db_appuser_password': db_appuser_password,
#             'engine': engine,
#             'version': engineVersion,
#             'name': name,
#             'desc': name,
#             'root_disk_size': 40,
#             'data_disk_size': data_instance.get('AllocatedStorage'),
#             # 'db_root_name': data_instance.get('MasterUsername', 'default'),
#             'db_root_password': data_instance.get('MasterUserPassword', None),
#             'key_name': key_name
#         }
#         params['resource_params'] = data
#         self.logger.debug('Pre create params: %s' % obscure_data(deepcopy(params)))
#         return params
#
#     #
#     # resource client method
#     #
#     @trace(op='view')
#     def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=-1):
#         """Get resource info
#
#         :return: Dictionary with resources info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         if zones is None:
#             zones = []
#         if uuids is None:
#             uuids = []
#         if tags is None:
#             tags = []
#         data = {
#             'size': size,
#             'page': page
#         }
#         if len(zones) > 0:
#             data['parent_list'] = ','.join(zones)
#         if len(uuids) > 0:
#             data['uuids'] = ','.join(uuids)
#         if len(tags) > 0:
#             data['tags'] = ','.join(tags)
#
#         instances = self.controller.api_client.admin_request('resource', '/v1.0/nrs/provider/sql_stacks', 'get',
#                                                              data=urlencode(data)).get('sql_stacks', [])
#         self.controller.logger.debug('Get sql stack resources: %s' % truncate(instances))
#         return instances
#
#     @trace(op='insert')
#     def create_resource(self, task, *args, **kvargs):
#         """Create resource
#
#         :param args: custom positional args
#         :param kvargs: custom key=value args
#         :return: True
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         data = {'sql_stack': args[0]}
#         try:
#             uri = '/v1.0/nrs/provider/sql_stacks'
#             res = self.controller.api_client.admin_request('resource', uri, 'post', data=data)
#             uuid = res.get('uuid', None)
#             taskid = res.get('taskid', None)
#             self.logger.debug('Create sql stack resource: %s' % uuid)
#         except ApiManagerError as ex:
#             self.logger.error(ex, exc_info=1)
#             self.update_status(SrvStatusType.ERROR, error=ex.value)
#             raise
#         except Exception as ex:
#             self.logger.error(ex, exc_info=1)
#             self.update_status(SrvStatusType.ERROR, error=str(ex))
#             raise ApiManagerError(str(ex))
#
#         # set resource uuid
#         if uuid is not None and taskid is not None:
#             self.set_resource(uuid)
#             self.update_status(SrvStatusType.PENDING)
#             self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
#             self.update_status(SrvStatusType.CREATED)
#             self.controller.logger.debug('Update sql stack resource: %s' % uuid)
#
#         return uuid
#
#
#     @trace(op='view')
#     def list_engines(self):
#         """List database engine type and version
#
#         :return: Dictionary with resources info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#
#         engines = self.controller.api_client.admin_request('resource', '/v1.0/nrs/provider/sql_stacks/engines', 'get')
#         self.controller.logger.debug('Get sql stack resource engines: %s' % truncate(engines))
#         return engines

# class ApiDatabaseServiceSchema(ApiServiceTypePlugin):
#     """"""
#     objuri = 'databaseserviceschema'
#     objname = 'databaseserviceschema'
#     objdesc = 'Databaseserviceschema'
#
#     def __init__(self, *args, **kvargs):
#         """ """
#         ApiServiceTypePlugin.__init__(self, *args, **kvargs)
#         self.resourceInfo = None
#
#         self.child_classes = []
#
#     def info(self):
#         """Get object info
#         :return: Dictionary with object info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         info = ApiServiceTypePlugin.info(self)
#         info.update({
#              })
#         return info
#
#     def getResourceInfo(self, resource_uuid):
#         """Get resource info
#         :return: Dictionary with resource info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         path = 'ApiDatabaseSchema:getResourceInfo:'
#         self.logger.debug('%s START' % path)
#         AssertUtil.assert_is_not_none(resource_uuid)
#         info = self.controller.api_client.admin_request('resource',
#                         '/v1.0/XXXXX/%s' % resource_uuid,
#                         'get')
#         self.logger.debug('%s END info=%s' % (path, info))
#         return info
#
#     def validateParams(self, oid):
#         """Validation params pre-create instance
#
#         :return: Dictionary with object detail.
#         :rtype: dict
#         :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
#         """
#         self.logger.debug('validateParams oid=%s' %oid)
#
#     def transformParamResource(self, oid):
#         """Transformation params post-create instance
#
#         :return: Dictionary with normalized params.
#         :rtype: dict
#         :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
#         """
#         self.logger.debug('transformParamResource oid=%s' %oid)
#
#     def createResourceInstance(self, instance):
#         """
#         """
#         pass
#
#     def updateResource(self, instance, *args, **kwargs):
#         """
#         """
#         pass
#
#     def deleteResource(self, instance, *args, **kwargs):
#         """
#         """
#         pass


# class ApiDatabaseServiceBackup(ApiServiceTypePlugin):
#     pass
#
#
# class ApiDatabaseServiceLog(ApiServiceTypePlugin):
#     pass
#
#
# class ApiDatabaseServiceSnapshot(ApiServiceTypePlugin):
#     pass
#
#
# class ApiDatabaseServiceTag(ApiServiceTypePlugin):
#     pass
#
#
# class ApiDatabaseServiceUser(ApiServiceTypePlugin):
#     pass
