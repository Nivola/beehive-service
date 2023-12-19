# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from copy import deepcopy
from typing import List, Dict
from beecell.simple import format_date, obscure_data, dict_get
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
    ApiServiceTypeContainer,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model.base import SrvStatusType
from beehive.common.apimanager import ApiManagerWarning, ApiManagerError
from six.moves.urllib.parse import urlencode
from beehive.common.assert_util import AssertUtil
from beehive_service.controller import ServiceController, ApiServiceInstance
from beehive_service.plugins.computeservice.controller import ApiComputeSubnet
from beehive_service.service_util import (
    __SRV_STORAGE_PROTOCOL_TYPE_NFS__,
    __SRV_STORAGE_PROTOCOL_TYPE_CIFS__,
)
from pprint import pprint


class StorageParamsNames(object):
    Nvl_FileSystem_Size = "Nvl_FileSystem_Size"
    Nvl_FileSystem_Type = "Nvl_FileSystem_Type"
    Nvl_shareProto = "Nvl_shareProto"
    Nvl_FileSystemId = "Nvl_FileSystemId"
    SubnetId = "SubnetId"
    owner_id = "owner_id"
    CreationToken = "CreationToken"


class ApiStorageService(ApiServiceTypeContainer):
    objuri = "storageservice"
    objname = "storageservice"
    objdesc = "StorageService"
    plugintype = "StorageService"

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
    def customize_list(
        controller: ServiceController,
        entities: List["ApiStorageService"],
        *args,
        **kvargs,
    ):
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
        instance_type_idx = controller.get_service_definition_idx(ApiStorageService.plugintype)

        # get resources
        # zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiStorageService(controller).list_resources(uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

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

        # instance_type_idx = self.controller.get_service_definition_idx(ApiStorageService.plugintype)

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
            if name.find("share") == 0:
                name = name.replace("share.", "")
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
            data["share.%s" % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix="share"):
        return self.get_container_attributes(prefix=prefix)

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: the running task which is calling the method
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


class ApiStorageEFS(AsyncApiServiceTypePlugin):
    plugintype = "StorageEFS"

    task_path = "beehive_service.plugins.storageservice.tasks_v2."
    create_task = None

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.subnet_idx: Dict[str, ApiServiceInstance]
        self.child_classes = []
        self.available_capabilities = {
            "openstack": ["resize", "grant"],
            "ontap": [],
        }

    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        share_size = self.get_config("share_data.%s" % StorageParamsNames.Nvl_FileSystem_Size)

        # base quotas
        quotas = {"share.instances": 1, "share.blocks": share_size}

        compute_zone = self.get_config("computeZone")

        # check quotas
        self.check_quotas(compute_zone, quotas)

        return params

    def post_create(self, **params):
        """Post creation of EFS service instance

        Logics:
        Nothing to do while creating the EFS.
        Everything will be done when we will create the mount target.
        After service instance is been created we only need to set his status as active

        :param params:
        :return:
        """
        self.instance.update_status(SrvStatusType.ACTIVE)

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        if self.check_resource() is not None:
            raise ApiManagerError(
                "File system %s has an active mount target. It can not be deleted" % self.instance.uuid
            )
        return params

    def delete_share(self, **kvargs):
        """Delete share using a celery task

        :param subnet_id: subnet id
        :param share_proto: share protocol
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        self.instance.verify_permisssions("delete")
        self.instance.verify_permisssions("update")

        # self.logger.info('delete_share instance data  %s' .format(pprint(self.instance.__dict__)))
        # storage_id_list = []
        # account_id_list = []
        # data_search = {}
        params = {
            "data": {"grants": [], "mountTargets": []},
            "action": "delete_share",
        }

        # check service instance configuration
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "" or self.instance.oid is None:
            self.logger.warning("File system %s does not have any mount target" % self.instance.uuid)
        else:
            mount_target = self.get_mount_target_resource()
            params["data"]["mountTargets"] = [self.instance.resource_uuid]

            grants = []

            if "grant" in self.get_available_capabilities():
                sites = mount_target.get("details", {}).get("grants", {})
                for site in sites:
                    grant = sites[site]
                    if isinstance(grant, dict):
                        grant = [grant]
                    grants.extend(grant)

                if len(grants) > 0:
                    self.logger.info("Share with grants %s  " % str(len(grants)))
                    ids = [element["id"] for element in grants]
                    params["data"]["grants"] = ids
                else:
                    self.logger.warning("Share %s has no grants " % str(self.instance.uuid))

        self.action(**params)
        self.logger.info("Delete share using task %s" % str(self.active_task))
        return self.active_task

    def pre_action(self, **params):
        """configure params for implemented action

        :param params: action parameters varying according to which action is executing
        :return: new params dictionary
        """

        params["id"] = self.instance.oid

        action = params.pop("action", "")
        if action == "create_mount_target":
            params["steps"] = [self.task_path + "create_mount_target_step"]
        elif action == "delete_mount_target":
            params["steps"] = [self.task_path + "delete_mount_target_step"]
        elif action == "mount_target_grant":
            params["steps"] = [self.task_path + "create_mount_target_grant_step"]
        elif action == "delete_share":
            params["steps"] = [
                self.task_path + "delete_mount_grants_step",
                self.task_path + "delete_mount_targets_step",
            ]
        else:
            # do nothing
            params["steps"] = []

        return params

    def post_action(self, **params):
        """
        aciotn finalization
        :param params:
        :return:
        """
        return None

    def get_orchestrator_type(self):
        return self.get_config("orchestrator_type")

    def get_available_capabilities(self):
        return self.available_capabilities.get(self.get_config("orchestrator_type"), [])

    def has_capability(self, capability):
        if capability not in self.get_available_capabilities():
            raise ApiManagerError("file system %s capability %s is not available" % (self.uuid, capability))

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
            # self.resource = None

    @staticmethod
    def customize_list(controller: ServiceController, entities: List["ApiStorageEFS"], *args, **kvargs):
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
        # vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)
        # security_group_idx = controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)
        # instance_type_idx = controller.get_service_definition_idx(ApiDatabaseServiceInstance.plugintype)

        # get resources
        zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.subnet_idx = subnet_idx
            # entity.subnet = subnet_idx.get(str(entity.get_config('dbinstance.DBSubnetGroupName')))
            # entity.subnet_vpc = vpc_idx.get(entity.subnet.get_parent_id())
            # entity.avzone = entity.subnet.get_config('site')
            # if entity.compute_service.resource_uuid not in zones:
            #     zones.append(entity.compute_service.resource_uuid)
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        if len(resources) > 3:
            resources = []
        else:
            zones = []

        resources_list = ApiStorageEFS(controller).list_mount_target_resources(zones=zones, uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid, {})

        return entities

    def get_share_export_location_ip_address(self, proto, export_location):
        if export_location is not None:
            if proto == __SRV_STORAGE_PROTOCOL_TYPE_NFS__:
                if export_location is not None:
                    data = export_location.split(":/")
                    if len(data) > 0:
                        return data[0]

            if proto == __SRV_STORAGE_PROTOCOL_TYPE_CIFS__:
                if export_location is not None:
                    data = export_location.split("\\")
                    if len(data) > 2:
                        return export_location.split("\\")[2]
        return ""

    def get_share_export_location_target(self, proto, export_location):
        if export_location is not None and export_location != "":
            if proto == __SRV_STORAGE_PROTOCOL_TYPE_NFS__:
                if export_location is not None:
                    vals = export_location.split(":/")
                    if len(vals) > 1:
                        return vals[1]
                    else:
                        return ""

            if proto == __SRV_STORAGE_PROTOCOL_TYPE_CIFS__:
                if export_location is not None:
                    vals = export_location.split("\\")
                    if len(vals) > 3:
                        return vals[3]
                    else:
                        return ""
        return ""

    def share_state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: "creating",
            SrvStatusType.PENDING: "creating",
            SrvStatusType.BUILDING: "creating",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETING: "deleting",
            SrvStatusType.DELETED: "delete",
            SrvStatusType.ERROR: "error",
        }
        return mapping.get(state, "unknown")

    def mount_target_state_mapping(self, state):
        mapping = {
            "PENDING": "creating",
            "BUILDING": "creating",
            "ACTIVE": "available",
            "UPDATING": "updating",
            "ERROR": "error",
            "DELETING": "deleting",
            "DELETED": "delete",
            "EXPUNGING": "deleting",
            "EXPUNGED": "delete",
            "UNKNOWN": "unknown",
        }
        return mapping.get(state, "unknown")

    def has_mount_target(self):
        """Check if share has a mount target

        :return: True or False
        """
        if self.resource_uuid is not None:
            return True
        return False

    def get_performance_mode(self):
        """get share performance mode

        :return: generalPurpose or localPurpose
        """
        data = self.get_config("share_data")
        res = data.get("PerformanceMode")
        if res is None:
            res = "generalPurpose"
        return res

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        instance_item = {}
        resource = self.resource

        instance_item["NumberOfMountTargets"] = 0
        instance_item["nvl_shareProto"] = ""

        if resource != {}:
            instance_item["NumberOfMountTargets"] = 1
            instance_item["nvl_shareProto"] = dict_get(resource, "details.proto")

        instance_item["CreationToken"] = self.instance.name
        instance_item["CreationTime"] = format_date(self.instance.model.creation_date)
        instance_item["FileSystemId"] = self.instance.uuid
        instance_item["LifeCycleState"] = self.share_state_mapping(self.instance.status)
        instance_item["Name"] = self.instance.name
        instance_item["OwnerId"] = self.account.uuid
        instance_item["nvl-OwnerAlias"] = self.account.name

        instance_item["nvl-stateReason"] = {"nvl-code": None, "nvl-message": None}
        if self.instance.status == "ERROR":
            instance_item["nvl-stateReason"] = {
                "nvl-code": "400",
                "nvl-message": self.instance.last_error,
            }

        # NOT SUPPORTED
        #  instance_item['KmsKeyId'] = ''
        #  instance_item['Encrypted'] = False
        instance_item["PerformanceMode"] = self.get_performance_mode()

        share_size = dict_get(resource, "details.size", default=0)
        # share_size = self.get_config('share_data.%s' % StorageParamsNames.Nvl_FileSystem_Size)
        if share_size is None:
            share_size = 0
        size_bytes = share_size * 1024 * 1024 * 1024
        file_system_size = {
            "Value": size_bytes,
            "Timestamp": format_date(self.instance.model.creation_date),
        }

        instance_item["SizeInBytes"] = file_system_size

        # capabilities
        instance_item["nvl-Capabilities"] = self.get_available_capabilities()

        return instance_item

    def aws_info_target(self):
        """Get info for mount target as required by aws api

        :return:
        """
        subnet_id = self.get_config("mount_target_data.subnet_id")
        share_proto = self.get_config("mount_target_data.share_proto")
        network = self.get_config("mount_target_data.network")
        avzone = None

        self.logger.warn(f" self.subnet_idx contains {len(self.subnet_idx)} items")
        self.logger.warn(subnet_id)

        if subnet_id is not None:
            avzone = self.subnet_idx.get(subnet_id).get_config("site")

        if share_proto is not None:
            share_proto = share_proto.upper()

        resource = self.resource
        self.logger.warn(resource)
        if resource is None:
            resource = {}
        exp_location = dict_get(resource, "details.export", default="")

        target_item = {}
        target_item["FileSystemId"] = self.instance.uuid
        target_item["IpAddress"] = self.get_share_export_location_ip_address(share_proto, exp_location)
        target_item["LifeCycleState"] = self.mount_target_state_mapping(resource.get("state", None))
        target_item["MountTargetId"] = self.get_share_export_location_target(share_proto, exp_location)
        target_item["NetworkInterfaceId"] = None
        target_item["OwnerId"] = self.account.uuid
        target_item["nvl-OwnerAlias"] = self.account.name
        target_item["SubnetId"] = subnet_id
        target_item["nvl-ShareProto"] = share_proto
        target_item["nvl-AvailabilityZone"] = avzone

        return target_item

    def create_mount_target(self, subnet_id, share_proto, share_label=None, share_volume=None):
        """Create mount target using a celery task

        :param subnet_id: subnet id
        :param share_proto: share protocol
        :param share_label: share label [optional]
        :param share_volume: id of a physical existing volume to set for mount target [optional]
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        # check service instance configuration
        if self.instance.resource_uuid is not None and self.instance.resource_uuid != "":
            resourceisvailid = True
            try:
                self.get_mount_target_resource()
            except ApiManagerError:
                resourceisvailid = False
            if resourceisvailid:
                raise ApiManagerError("File system %s has already a mount target" % self.instance.uuid)

        # verify permissions
        self.instance.verify_permisssions("update")

        # get subnet
        subnet_inst = self.controller.get_service_type_plugin(subnet_id, plugin_class=ApiComputeSubnet)
        vpc_inst = subnet_inst.get_parent()

        if self.instance.account_id != subnet_inst.instance.account_id:
            raise ApiManagerError("Subnet %s is not in the StorageService account" % subnet_id)

        cfg = self.instance.config_object
        share_data = cfg.get_json_property("share_data")

        if self.get_performance_mode() == "generalPurpose":
            subnet = None
        elif self.get_performance_mode() == "localPurpose":
            subnet = subnet_inst.get_cidr()

        orchestrator_type = self.get_orchestrator_type()
        params = {
            "data": {
                "container": cfg.get_json_property("container"),
                "desc": self.instance.name,
                "name": self.instance.name,
                "compute_zone": cfg.get_json_property("computeZone"),
                "availability_zone": subnet_inst.get_config("subnet.AvailabilityZone"),
                "network": vpc_inst.instance.resource_uuid,
                "subnet": subnet,
                "type": orchestrator_type,
                "orchestrator_tag": cfg.get_json_property("orchestrator_tag"),
                "share_proto": share_proto,
                "share_label": share_label,
                "size": share_data.get(StorageParamsNames.Nvl_FileSystem_Size),
                "multi_avz": False,
            },
            "action": "create_mount_target",
        }
        if orchestrator_type == "ontap":
            if share_volume is None:
                raise ApiManagerError("share with orchestrator type ontap requires Nvl_shareVolume")
            params["data"]["share_volume"] = share_volume

        self.set_config("mount_target_data.subnet_id", subnet_inst.instance.uuid)
        self.set_config("mount_target_data.share_proto", share_proto)

        self.action(**params)

        self.logger.info("Create mount target using task %s" % str(self.active_task))
        return self.active_task

    def delete_mount_target(self, **kvargs):
        """Delete mount target using a celery task

        :param subnet_id: subnet id
        :param share_proto: share protocol
        :return: celery task instance id, resource uuid
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.instance.verify_permisssions("delete")

        # check service instance configuration
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            raise ApiManagerWarning("File system %s does not have any mount target" % self.instance.uuid)

        try:
            self.get_mount_target_resource()
        except ApiManagerWarning:
            raise ApiManagerWarning("File system %s does not have any mount target" % self.instance.uuid)

        params = {
            "data": kvargs,
            "action": "delete_mount_target",
        }
        self.action(**params)
        self.logger.info("Delete mount target using task %s" % str(self.active_task))
        return self.active_task

    def resize_filesystem(self, **data):
        """Resize filesystem

        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        # check capability
        self.has_capability("resize")

        # verify permissions
        self.instance.verify_permisssions("update")

        size = data.get(StorageParamsNames.Nvl_FileSystem_Size)
        self.set_config("share_data.%s" % StorageParamsNames.Nvl_FileSystem_Size, size)

        # check service instance configuration
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            return None

        params = {
            "resource_params": {
                "size": size,
            },
        }
        self.update(**params)
        self.logger.info("Update resource mount target using task %s" % str(self.active_task))
        return self.active_task

    def grant_operation(self, action="add", **data):
        """assign or deassign a grant

        :param action: string add or delete
        :param data:
          access_level: rw, ro, w
          access_to: 10.102.186.0/24
          access_type: ip
        :return:
        """
        # check capability
        self.has_capability("grant")

        if self.instance.resource_uuid == "":
            AssertUtil.fail("File System uuid is null. Did you add a mount point?")

        # verify permissions
        self.instance.verify_permisssions("update")
        data["action"] = action

        params = {
            "data": data,
            "action": "mount_target_grant",
        }

        self.action(**params)

        self.logger.info("Grant %s using task %s" % (action, str(self.active_task)))
        return self.active_task

    #
    # resource methods
    #
    def get_mount_target_resource(self):
        """Get mount target share info from the resource layer

        :return: share info
        :rtype: dict
        """
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            raise ApiManagerError("There is not a connected resource to share %s" % self.instance.oid)

        uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
        share = self.controller.api_client.admin_request("resource", uri, "get").get("share")
        return share

    def list_mount_target_resources(self, zones=None, uuids=None, page=0, size=-1):
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

        uri = "/v1.0/nrs/provider/shares"
        data = urlencode(data)
        res = self.controller.api_client.admin_request("resource", uri, "get", data=data).get("shares", [])
        return res

    def create_mount_target_resource(self, task, **data):
        """Called by celery task create_mount_target_task only while creating a mount point

        :param task: the task which is calling the  method
        :param share_proto: share protocol  nfs/cifs
        :param av_zone: avalability zone
        :param network: vpc id
        :return: resource uid
        :rtype: str
        """
        self.logger.debug2("Input data: %s" % data)
        res = self.controller.api_client.admin_request(
            "resource", "/v1.0/nrs/provider/shares", "post", data={"share": data}
        )
        uuid = res.get("uuid", None)

        # set resource uuid
        if uuid is not None or uuid != "":
            # sync creation
            model_data = {"resource_uuid": uuid, "status": SrvStatusType.BUILDING}
            self.instance.update(**model_data)

            # Wait asinc resource creation
            taskid = res.get("taskid")

            if taskid is not None:
                self.wait_for_task(taskid, delta=2, maxtime=600, task=task)

            # update configuration
            self.set_config("mount_target_data.network", data.get("network"))
            self.update_status(SrvStatusType.ACTIVE)

        return uuid

    def delete_mount_target_resource(self, task):
        """Asyncronous task method
        Delete share resource

        :param task: asyncronous task invoking the method
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
            res = self.controller.api_client.admin_request("resource", uri, "delete", data="")
            taskid = res.get("taskid", None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))

        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.set_resource("")
            self.manager.update_entity_null(self.instance.model.__class__, oid=self.oid, resource_uuid=None)
            self.set_config("mount_target_data", None)
        self.logger.debug("Delete mount_target_resource: %s" % res)

        return True

    # AHMAD 17-12-2020 NSP-160
    def delete_mount_grants(self, task, grants):
        """Asyncronous task method

        Delete share resource

        :param task: asyncronous task invoking the method
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if len(grants) > 0:
            self.logger.debug("There are %s grants to delete" % len(grants))
            for grant in grants:
                data = {
                    "share": {
                        "grant": {
                            "action": "del",
                            "access_id": grant,
                        }
                    }
                }
                self.logger.debug("Removing Grant with id %s" % grant)
                uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                job = res.get("taskid")
                if job is not None:
                    self.logger.debug("Removing Grant  %s with job %s" % (grant, job))
                    self.wait_for_task(job, delta=2, maxtime=180, task=task)
                    self.logger.debug(
                        "Deleted grant resource %s in file system instance %s res=%s" % (data, self.instance.uuid, res)
                    )
        else:
            self.logger.debug("There are no Grants to delete ")
        return True

    def delete_share_mount_targets(self, task, mounts):
        """Asyncronous task method. Delete share resource

        :param task: asynchronous task invoking the method
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if len(mounts) > 0:
            self.logger.debug("There are %s Mount Targets to delete" % len(mounts))
            for mount in mounts:
                self.logger.debug("Removing Grant with id %s" % mount)
                try:
                    uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
                    res = self.controller.api_client.admin_request("resource", uri, "delete", data="")
                    taskid = res.get("taskid", None)
                except ApiManagerError as ex:
                    self.logger.error(ex, exc_info=1)
                    self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
                    raise
                except Exception as ex:
                    self.logger.error(ex, exc_info=1)
                    self.update_status(SrvStatusType.ERROR, error=str(ex))
                    raise ApiManagerError(str(ex))

                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                    self.set_resource("")
                    self.manager.update_entity_null(self.instance.model.__class__, oid=self.oid, resource_uuid=None)
                    self.set_config("mount_target_data", None)
                self.logger.debug("Delete mount_target_resource: %s" % res)
        return True

    def update_resource(self, task, size=None, **kwargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """

        if size is None:
            raise ApiManagerError("size mast be set whene risizing a file system")
        data = {"share": {"size": size}}
        res = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid,
            "put",
            data=data,
        )
        job = res.get("taskid")
        if job is not None:
            self.wait_for_task(job, delta=2, maxtime=180, task=task)
        return job

    def do_file_system_grant_op(
        self,
        task,
        action="add",
        access_level="ro",
        access_type="ip",
        access_to=None,
        access_id=None,
    ):
        """Asyncronous task method perform grant operation (add/del)

        :param   task: runnin asyncronous task
        :param   action: action to perform should be add | del
        :param   access_level: add only rw
        :param   access_type: add only ip
        :param   access_to: add only 158.102.160.0/24
        :param   access_id:del only uuid of the acces grant
        :return:
        """
        if action == "add":
            data = {
                "share": {
                    "grant": {
                        "action": action,
                        "access_level": access_level,
                        "access_type": access_type,
                        "access_to": access_to,
                    }
                }
            }
        elif action == "del":
            data = {
                "share": {
                    "grant": {
                        "action": action,
                        "access_id": access_id,
                    }
                }
            }
        else:
            raise ApiManagerError("Unknown grant action :%s" % action)
        res = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid,
            "put",
            data=data,
        )
        job = res.get("taskid")
        if job is not None:
            self.wait_for_task(job, delta=2, maxtime=180, task=task)
        self.logger.debug(
            "Created grant resource %s in file system instance %s res=%s" % (data, self.instance.uuid, res)
        )
        return job
