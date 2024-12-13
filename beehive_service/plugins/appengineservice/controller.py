# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from copy import deepcopy

from beecell.simple import merge_dicts, format_date, obscure_data, truncate, id_gen
from beehive.common.assert_util import AssertUtil
from beehive.common.data import trace
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import (
    ApiServiceTypeContainer,
    ApiServiceTypePlugin,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model import SrvStatusType
from beehive_service.controller import ApiServiceType
from beehive.common.apimanager import ApiManagerWarning, ApiManagerError
from six.moves.urllib.parse import urlencode
from beehive_service.plugins.computeservice.controller import (
    ApiComputeSubnet,
    ApiComputeSecurityGroup,
    ApiComputeVPC,
    ApiComputeKeyPairsHelper,
)
from beehive_service.plugins.storageservice.controller import ApiStorageService


class ApiAppEngineServiceResourceHelper(object):
    def __init__(self, controller):
        self.controller = controller

    def list_instance_resources(self, zones=None, uuids=None, page=0, size=20):
        """List resources
        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if zones is None:
            zones = []
        if uuids is None:
            uuids = []
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        self.controller.logger.debug("ListResource %s" % data)

        path = "ApiDatabaseService:listResource:"
        self.controller.logger.warning("%s START" % path)
        res = self.controller.api_client.admin_request(
            "resource", "/v1.0/nrs/provider/app_stacks", "get", data=urlencode(data)
        ).get("app_stacks", [])
        self.controller.logger.debug("%s END res=%s" % (path, res))
        return res

    def index_resources(self, resources):
        """Index resources by uuid

        :param resources: resource list
        :return: resource indexed by uuid
        """
        return {r["uuid"]: r for r in resources}


class ApiAppEngineService(ApiServiceTypeContainer):
    objuri = "appengineservice"
    objname = "appengineservice"
    objdesc = "AppEngineService"
    plugintype = "AppEngineService"

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
        instance_type_idx = controller.get_service_definition_idx(ApiAppEngineService.plugintype)

        # get resources
        zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiAppEngineService(controller).list_resources(uuids=resources)
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
        return mapping.get(state, "unknown")

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
            if name.find("appengine") == 0:
                name = name.replace("appengine.", "")
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
            data["appengine.%s" % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix="appengine"):
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

    def delete_resource(self, *args, **kvargs):
        """Delete resource do nothing. Compute zone is owned by ComputeService

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return True

    @staticmethod
    def import_instance(controller, resource_id, inst_def):
        """Create service from existing resource

        :param controller:
        :param resource_id:
        :param inst_def:
        :return:
        """
        res = ApiAppEngineServiceResourceHelper(controller).list_instance_resources(uuids=[resource_id])
        if len(res) == 0:
            raise ApiManagerError("Resource %s does not exist" % resource_id)
        res = res[0]
        if res.get("state") == 0:
            raise ApiManagerError("Resource %s does not have a correct state" % resource_id)

        compute_zone = res.get("parent").get("uuid")
        container = res.get("container").get("uuid")
        name = res.get("name")
        desc = res.get("desc")
        engine_configs = res.get("attributes").get("engine_configs")
        vpc_resource_uuid = res.get("vpc").get("uuid")
        security_group_resource_uuid = res.get("security_group").get("uuid")

        # check if the compute zone has an associated AppEngineService
        res, total = controller.get_paginated_service_instances(
            resource_uuid=compute_zone,
            plugintype=ApiAppEngineService.plugintype,
            filter_expired=False,
            active=True,
        )

        if total == 0:
            raise ApiManagerWarning("Resource %s can not be associated to an active App Engine Service" % resource_id)
        inst_compute_service = res[0]

        # get account id
        account_id = inst_compute_service.account_id

        # check account oid
        account = controller.get_account(account_id)
        #  checks authorization user on account and instance to create
        controller.check_authorization(
            ApiServiceInstance.objtype,
            ApiServiceInstance.objdef,
            account.objid,
            "insert",
        )

        # checks authorization user on compute service instance
        if inst_compute_service.verify_permisssions("update") is False:
            raise ApiManagerWarning("User does not have permission to update instance id %s" % inst_compute_service.oid)

        # create service
        instance = controller.createInstanceHierachy(
            None,
            None,
            name=name,
            desc=desc,
            instance_parent_id=inst_compute_service.oid,
            service_def=inst_def,
            account=account,
        )
        plugin_root = ApiServiceInstance(
            controller,
            oid=instance.id,
            objid=instance.objid,
            name=instance.name,
            desc=instance.desc,
            active=instance.active,
            model=instance,
        )

        # get vpc
        vpcs, total = controller.get_paginated_service_instances(
            resource_uuid=vpc_resource_uuid,
            plugintype=ApiComputeVPC.plugintype,
            filter_expired=False,
            active=True,
        )
        vpc_id = None
        subnet_id = None
        if total == 1:
            vpc_id = vpcs[0].uuid

            # get subnet
            subnets = vpcs[0].getInstanceChildren(plugintype=ApiComputeSubnet.plugintype)
            if len(subnets) > 0:
                subnet_id = subnets[0].uuid

        # get security group
        sgs, total = controller.get_paginated_service_instances(
            resource_uuid=vpc_resource_uuid,
            plugintype=ApiComputeSecurityGroup.plugintype,
            filter_expired=False,
            active=True,
        )
        sg_ids = []
        if total == 1:
            sg_ids = [sgs[0].uuid]

        # update instance config with request data
        inst_cfgs, total = controller.get_service_instance_cfgs(service_instance_id=instance.id)
        for inst_cfg in inst_cfgs:
            data = {
                "resource_id": resource_id,
                "EngineConfigs": engine_configs,
                "SubnetId": subnet_id,
                "VpcId": vpc_id,
                "SecurityGroupId_N": sg_ids,
            }
            json_cfg_merged = merge_dicts(
                inst_cfg.json_cfg,
                {"computeZone": inst_compute_service.resource_uuid},
                data,
            )
            inst_cfg.update(json_cfg=json_cfg_merged)

        # sync creation
        model_data = {"resource_uuid": resource_id, "status": SrvStatusType.ACTIVE}
        plugin_root.update(**model_data)

        controller.logger.info("Create app engine from existing resource %s" % resource_id)

        return instance


class ApiAppEngineInstance(AsyncApiServiceTypePlugin):
    objuri = "appengineservice/instance"
    objname = "appengine"
    objdesc = "AppEngine Instance"
    plugintype = "AppEngineInstance"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.resourceInfo = None

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
        subnet_idx = controller.get_service_instance_idx(ApiComputeSubnet.plugintype)
        vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)
        security_group_idx = controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)
        instance_type_idx = controller.get_service_definition_idx(ApiAppEngineInstance.plugintype)

        # get resources
        zones = []
        resources = []
        for entity in entities:
            entity.account = account_idx.get(str(entity.instance.account_id))
            entity.subnet = subnet_idx.get(str(entity.get_config("instance.SubnetId")))
            entity.subnet_vpc = vpc_idx.get(entity.subnet.get_parent_id())
            entity.avzone = entity.subnet.get_config("site")

            # get security groups
            entity.security_groups = []
            for sg in entity.get_config("instance.SecurityGroupId_N"):
                entity.security_groups.append(security_group_idx.get(str(sg)))

            # get instance type
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))

            # get resource
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        if len(resources) > 3:
            resources = []
        else:
            zones = []
        resources_list = ApiAppEngineInstance(controller).list_resources(zones=zones, uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        self.account = self.controller.get_account(str(self.instance.account_id))
        self.subnet = self.controller.get_service_instance(self.get_config("instance.SubnetId"))
        self.subnet_vpc = self.controller.get_service_instance(self.subnet.get_parent_id())
        self.avzone = self.subnet.get_config("site")

        # get security groups
        self.security_groups = []
        for sg in self.get_config("instance.SecurityGroupId_N"):
            self.security_groups.append(self.controller.get_service_instance(sg))

        # get instance type
        self.instance_type = self.controller.get_service_def(self.instance.service_definition_id)

        # assign resources
        if self.instance.resource_uuid is not None:
            resources_list = self.list_resources(uuids=[self.instance.resource_uuid])
            if len(resources_list) > 0:
                self.resource = resources_list[0]

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: "pending",
            SrvStatusType.PENDING: "pending",
            SrvStatusType.BUILDING: "building",
            SrvStatusType.CREATED: "building",
            SrvStatusType.ACTIVE: "running",
            SrvStatusType.ERROR: "error",
            SrvStatusType.ERROR_CREATION: "error",
            SrvStatusType.STOPPING: "stopping",
            SrvStatusType.STOPPED: "stopped",
            SrvStatusType.SHUTTINGDOWN: "shutting-down",
            SrvStatusType.TERMINATED: "terminated",
            SrvStatusType.UNKNOWN: "error",
        }
        return mapping.get(state, "unknown")

    def aws_info(self):
        """Get info as required by aws api

        :param inst_service:
        :param resource:
        :param account_idx:
        :param instance_type_idx:
        :return:
        """
        instance_item = {}
        data_instance = self.get_config("instance")

        # get subnet
        subnet = self.subnet
        subnet_vpc = self.subnet_vpc
        avzone = self.avzone
        subnet_vpc_id = subnet_vpc.uuid
        subnet_vpc_name = subnet_vpc.name

        # resInst = resource.get('stack', {})
        if self.resource is None:
            self.resource = {}

        instance_item["instanceId"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["additionalInfo"] = self.instance.desc
        instance_item["instanceType"] = self.instance_type.name
        instance_item["launchTime"] = format_date(self.instance.model.creation_date)
        instance_item["monitoring"] = False
        instance_item["instanceState"] = {"name": self.state_mapping(self.instance.status)}
        # instance_item['stateReason'] = {'code': None, 'message': None}
        # reason = self.resource.get('reason', None)
        # if reason is not None:
        #     instance_item['stateReason'] = {'code': 400, 'message': reason.get('error')}

        instance_item["stateReason"] = {"code": None, "message": None}
        # reason = self.resource.get('reason', None)
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "code": 400,
                "message": self.instance.last_error,
            }

        # account
        instance_item["OwnerAlias"] = self.account.name
        instance_item["OwnerId"] = self.account.uuid

        instance_item["subnetId"] = subnet.uuid
        instance_item["subnetName"] = subnet.name
        instance_item["vpcId"] = subnet_vpc_id
        instance_item["vpcName"] = subnet_vpc_name
        instance_item["placement"] = {"availabilityZone": avzone}

        # security groups
        instance_item["groupSet"] = []
        for sg in self.security_groups:
            instance_item["groupSet"].append({"groupId": sg.uuid, "groupName": sg.name})

        # internal resource info
        stack_idx = {i["availability_zone"]: i for i in self.resource.get("stacks", [])}
        main_stack = stack_idx.get(avzone, {})
        instance_item["privateIpAddress"] = main_stack.get("servers", [])
        instance_item["uris"] = main_stack.get("uris", [])

        # keys
        key_name = self.get_config("KeyName")
        if key_name is None and avzone is not None:
            key_name = self.get_config("key_name").get(avzone)
        instance_item["keyName"] = key_name

        # tags
        instance_item["tagSet"] = [{"key": None, "value": None}]

        # engine
        instance_item["engine"] = self.get_config("engine")
        instance_item["version"] = self.get_config("version")
        instance_item["engineConfigs"] = data_instance.get("EngineConfigs", {})

        # custom params
        instance_item["nvl-resourceId"] = self.instance.resource_uuid

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id

        # base quotas
        quotas = {
            "appengine.cores": 0,
            "appengine.instances": 1,
            "appengine.ram": 0,
        }

        # get container
        container_id = self.get_config("container")
        flavor_resource_uuid = self.get_config("flavor")
        image_resource_uuid = self.get_config("image")
        compute_zone = self.get_config("computeZone")
        data_instance = self.get_config("instance")

        # get Flavor resource Info
        flavor_resource = self.get_flavor(flavor_resource_uuid)
        # try to get main volume size from flavor
        flavor_configs = flavor_resource.get("attributes", None).get("configs", None)
        quotas["appengine.cores"] = flavor_configs.get("vcpus", 0)
        quotas["appengine.ram"] = flavor_configs.get("memory", 0)
        if quotas["appengine.ram"] > 0:
            quotas["appengine.ram"] = quotas["appengine.ram"] / 1024

        # get availability zone from request parameters
        av_zone = data_instance.get("AvailabilityZone", None)

        # check subnet
        subnet_id = data_instance.get("SubnetId", None)
        if subnet_id is None:
            raise ApiManagerError("Subnet is not defined")

        subnet_inst = self.controller.check_service_instance(subnet_id, ApiComputeSubnet, account=account_id)
        if av_zone is None:
            subnet_inst.get_main_config()
            av_zone = subnet_inst.get_config("site")

        # check availability zone status
        if self.is_availability_zone_active(compute_zone, av_zone) is False:
            raise ApiManagerError("Availability zone %s is not in available status" % av_zone)

        # get engine info and config
        version = self.get_config("version")
        engine = self.get_config("engine")
        engine_configs = data_instance.get("EngineConfigs")
        farm_name = engine_configs.get("FarmName", None)

        engine_resource_configs = {
            "farm_name": farm_name,
            "share_dimension": engine_configs.get("ShareDimension", 10),
        }

        # check subnet
        subnet_id = data_instance.get("SubnetId", None)
        if subnet_id is None:
            raise ApiManagerError("Subnet is not defined")

        subnet_inst = self.controller.check_service_instance(subnet_id, ApiComputeSubnet, account=account_id)
        subnet_inst.get_main_config()
        av_zone = subnet_inst.get_config("site")

        # get key name
        key_name = data_instance.get("KeyName", None)
        # get key name from database definition
        if key_name is None:
            key_name = self.get_config("key_name").get(av_zone, None)
        else:
            ApiComputeKeyPairsHelper(self.controller).check_service_instance(key_name, account_id)

        # check availability zone status
        if self.is_availability_zone_active(compute_zone, av_zone) is False:
            raise ApiManagerError("Availability zone %s is not in available status" % av_zone)

        # get vpc
        vpc_resource_uuid = self.controller.get_service_instance(
            subnet_inst.model.linkParent[0].start_service_id
        ).resource_uuid

        # check app engine is public
        is_public = data_instance.get("IsPublic")
        public_vpc_resource_uuid = None
        routes = []
        if is_public is True:
            public_subnet_id = data_instance.get("PublicSubnetId")
            inst_public_subnet = self.controller.check_service_instance(
                public_subnet_id, ApiComputeSubnet, account=account_id
            )

            # get public vpc
            public_vpc = self.controller.get_service_instance(inst_public_subnet.model.linkParent[0].start_service_id)
            self.set_config("PublicVpcId", public_vpc.uuid)
            public_vpc_resource_uuid = public_vpc.resource_uuid

            # get routes
            routes = data_instance.get("routes")

        # get and check the id SecurityGroupId
        securitygroup_ids = data_instance.get("SecurityGroupId_N")
        sg_resource_uuids = []
        for securityGroup in securitygroup_ids:
            sg_inst = self.controller.check_service_instance(securityGroup, ApiComputeSecurityGroup, account=account_id)
            if sg_inst.resource_uuid is None:
                raise ApiManagerWarning("SecurityGroup %s is invalid" % securityGroup)
            sg_resource_uuids.append(sg_inst.resource_uuid)

            # link security group to instance
            self.instance.add_link(
                name="link-%s-%s" % (self.instance.oid, sg_inst.oid),
                type="sg",
                end_service=sg_inst.oid,
                attributes={},
            )

        # check quotas
        self.check_quotas(compute_zone, quotas)

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        data = {
            "name": name,
            "desc": name,
            "container": container_id,
            "compute_zone": compute_zone,
            "availability_zone": av_zone,
            "flavor": flavor_resource_uuid,
            "image": image_resource_uuid,
            "vpc": vpc_resource_uuid,
            "subnet": subnet_inst.get_config("cidr"),
            "vpc_public": public_vpc_resource_uuid,
            "is_public": is_public,
            "security_group": sg_resource_uuids[0],
            "key_name": key_name,
            "version": version,
            "engine": engine,
            "engine_configs": engine_resource_configs,
            "routes": routes,
        }
        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))
        return params

    #
    # resource client method
    #
    @trace(op="view")
    def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=100):
        """Get resource info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if zones is None:
            zones = []
        if uuids is None:
            uuids = []
        if tags is None:
            tags = []
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)

        instances = self.controller.api_client.admin_request(
            "resource", "/v1.0/nrs/provider/app_stacks", "get", data=urlencode(data)
        ).get("app_stacks", [])
        self.controller.logger.debug("Get app stack resources: %s" % truncate(instances))
        return instances

    @trace(op="insert")
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"app_stack": args[0]}
        try:
            uri = "/v1.0/nrs/provider/app_stacks"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create app stack resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.controller.logger.debug("Update app stack resource: %s" % uuid)

        return uuid
