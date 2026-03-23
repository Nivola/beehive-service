# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from copy import deepcopy
from typing import List, Dict, TYPE_CHECKING, Set, Any
from beecell.simple import format_date, obscure_data, dict_get
from beecell.types.type_id import test_oid
from beehive.common.apimanager import ApiManagerWarning, ApiManagerError
from urllib.parse import urlencode
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
    ApiServiceTypeContainer,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.computeservice.controller import ApiComputeSubnet
from beehive_service.service_util import (
    __SRV_STORAGE_PROTOCOL_TYPE_NFS__,
    __SRV_STORAGE_PROTOCOL_TYPE_CIFS__,
    __SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_UPPER__,
)
if TYPE_CHECKING:
    from beehive_service.plugins.computeservice.controller import ApiComputeVPC
    from beehive_service.controller import ServiceController
    from beehive_service.entity.service_definition import ApiServiceDefinition
    from beehive_service.controller.api_account import ApiAccount


class StorageParamsNames(object):
    Nvl_FileSystem_Size = "Nvl_FileSystem_Size"
    Nvl_FileSystem_Type = "Nvl_FileSystem_Type"
    Nvl_shareProto = "Nvl_shareProto"
    Nvl_FileSystemId = "Nvl_FileSystemId"
    Nvl_MountTarget_Status = "Nvl_MountTarget_Status"
    Nvl_SnapshotPolicy = "Nvl_SnapshotPolicy"
    Nvl_ComplianceMode = "Nvl_ComplianceMode"
    Nvl_Rpo = "Rpo"
    SubnetId = "SubnetId"
    owner_id = "owner_id"
    CreationToken = "CreationToken"
    ReplicaNamePrefix = "dr-"
    ReplicaActionUnlink = "unlink"
    ReplicaActionSuspend = "suspend"
    ReplicaActionResume = "resume"
    ReplicaActionUpdate = "update"
    ReplicaRpo = "rpo"


class ApiStorageService(ApiServiceTypeContainer):
    objuri = "storageservice"
    objname = "storageservice"
    objdesc = "StorageService"
    plugintype = "StorageService"

    account: 'ApiAccount'
    instance_type: 'ApiServiceDefinition'

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
        return info

    def check_storage_service_configuration(self, compute_zone_id):
        """for staas service v2.0 only

        :param compute_zone_id: compute zone id
        :type compute_zone_id: int
        :return: the svm configuration
        :rtype: Dict
        :raises ApiManagerError:
        """
        uri = f"/v1.0/nrs/provider/compute_zones/{compute_zone_id}/storage/conf"
        return self.controller.api_client.admin_request("resource", uri, "get")

    @staticmethod
    def customize_list(
        controller: 'ServiceController',
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

    def pre_create(self, **params) -> Dict:
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

    def set_attributes(self, quotas: Dict):
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
    create_task = "beehive_service.plugins.storageservice.tasks_v2.efs_add_inst_task"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self._share_site_name: str = None
        self._share_subnet: 'ApiComputeSubnet' = None # legacy
        self._subnet_id: int = None
        self.child_classes = []
        self.available_capabilities = {
            "openstack": {
                "1.0": ["resize", "grant"],
                "2.0": [],
            },
            "ontap": {
                "1.0": [],
                "2.0": ["resize", "grant", "set-status", "replica", "snapshot-policy", "compliance"]
            },
        }

    def _check_get_resource_client_list(self, account_id, clients: List, site_name: str):
        """
        Checks if the specified vms are in the same site as the specified one, and
        returns the corresponding resource provider ids

        :param account_id: the account id
        :param clients: the list of clients (service vm names or ids or uuids)
        :param site_name: the site name (e.g. SiteTorino01)

        :returns: the resource provider ids of the clients (List[Int])
        :raises: Exception if any is in a different site
        """
        requested_clients = len(clients)
        if requested_clients==0:
            raise Exception("You must specify at least one client")

        from beehive_service.plugins.computeservice.controller import ApiComputeInstance

        client_resources = set()
        client_names = []
        client_uuids = []
        client_ids = []
        for client in clients:
            kind = test_oid(client)
            if kind=="id":
                client_ids.append(client)
            elif kind=="uuid":
                client_uuids.append(client)
            elif kind=="name":
                client_names.append(client)
            else:
                self.logger.warning("Invalid client %s", client)

        if not client_names and not client_uuids and not client_ids:
            raise Exception("No valid client found")

        res_list, total_clients = self.controller.get_service_type_plugins(
            service_uuid_list=client_uuids,
            service_id_list=client_ids,
            service_name_list=client_names,
            account_id=account_id,
            plugintype=ApiComputeInstance.plugintype,
            details=True,
            size=-1,
            service_list_filter_mode="OR"
        )
        if total_clients!=requested_clients:
            self.logger.warning("Query found %s clients, but %s were requested",total_clients,requested_clients)

        for vm in res_list:
            vm_resource = vm.resource
            vm_resource_id = vm_resource.get("id")
            vm_zone_name = vm_resource.get("availability_zone").get("name")
            if vm_zone_name == site_name:
                client_resources.add(str(vm_resource_id))
            else:
                raise Exception(f"Specified client {vm.instance.name} is not part of the specified site {site_name}")

        if len(client_resources) == 0:
            raise Exception("No valid clients found")

        return list(client_resources)


    def pre_create(self, **params) -> Dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # version = self.version
        version = self.get_config("version")
        compute_zone = self.get_config("computeZone")
        container_id = self.get_config("container")

        # get orchestrator type and orchestrator tag
        orchestrator_type = self.get_orchestrator_type()
        orchestrator_tag = self.get_config("orchestrator_tag")

        share_params = self.get_config("share_data")
        share_size = share_params.get(StorageParamsNames.Nvl_FileSystem_Size)

        # check service definition exists and account can see it
        service_definition_id = share_params.get(StorageParamsNames.Nvl_FileSystem_Type)
        _ = self.controller.get_service_def(service_definition_id)

        if orchestrator_type != "ontap":
            # altra gestione / unsupported
            raise Exception("Unsupported api version %s for orchestrator %s" % (version, orchestrator_type))

        if not version or version=="1.0":
            # vecchia gestione. non crea risorsa
            quotas = {"share.instances": 1, "share.blocks": share_size}
            # check quotas
            self.check_quotas(compute_zone, quotas)
            return params

        if share_params.get("SourceId"):
            # replica creation. nuova gestione
            # find source efs resource uuid
            res_source_uuid = self.controller.get_service_instance(share_params.get("SourceId")).resource_uuid
            data = {
                "container": container_id,
                "compute_zone": compute_zone,
                "site": share_params.get("SiteName"),
                "rpo": share_params.get("Rpo"),
                "res_source_uuid": res_source_uuid,
                "compliance": False,
                "awx_orchestrator_tag": version
            }
            # TODO QUOTAS
            quotas = {"share.instances": 1, "share.blocks": share_size}
        else:
            # volume creation. nuova gestione
            data = {
                "name": params.get("name"),
                "desc": f"ComputeFileShareV2 of ComputeZone {compute_zone}",
                "container": container_id,
                "compute_zone": compute_zone,
                "orchestrator_type": orchestrator_type,
                "orchestrator_tag": orchestrator_tag,
                "awx_orchestrator_tag": version,
            }

            # base dict for orchestrator specific params
            share_orch_params = {
                "size": share_size,
                "share_proto": share_params.get(StorageParamsNames.Nvl_shareProto).lower(),
                "encrypted": share_params.get("Encrypted", False),
                "snapshot_policy": share_params.get("snapshot_policy"),
            }

            compliance_mode = share_params.get("ComplianceMode")
            dest_site = share_params.get("SiteName")
            account_id = share_params.pop("owner_id")

            # check compute zone has valid staas configuration
            parent_plugin: 'ApiStorageService'
            _, parent_plugin = self.controller.check_service_type_plugin_parent_service(
                account_id, plugintype=ApiStorageService.plugintype
            )
            # raise exception is resource endpoint raises exception
            _svm_conf = parent_plugin.check_storage_service_configuration(compute_zone).get("storage_conf")
            data["site"] = dest_site
            if compliance_mode:
                data["compliance"] = True
                data["compliance_rpo"] = share_params.get("Rpo")
                quotas = {"share.instances": 1, "share.blocks": share_size*2} # size of volume + size of snaplock volume
                # TODO maybe better to have new quota for compliance volume e.g. share.compliance.blocks
            else:
                quotas = {"share.instances": 1, "share.blocks": share_size}  # size of volume
                data["compliance"] = False
            data["share_params"] = share_orch_params

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # remove no longer useful data from service instance config
        share_params.pop("computeZone", None)
        self.set_config("share_data", share_params)

        params["resource_params"] = data
        return params

    #@trace(op="insert")
    def create_resource(self, task, *args, **kvargs):
        data = {"share": args[0]}

        res_source_uuid = data["share"].pop("res_source_uuid",None)
        if not res_source_uuid:
            # normal share creation
            uri = "/v2.0/nrs/provider/shares"
        else:
            # replica share creation
            data["share"].pop("compliance",None)
            uri = f"/v2.0/nrs/provider/shares/{res_source_uuid}/replica"

        try:
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
        except (ApiManagerError,Exception) as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError("Error during creation: %s" % ex)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=2, maxtime=3600, task=task)
            self.update_status(SrvStatusType.CREATED)

        return uuid

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

        params = {
            "data": {
                "grants": [],
                "mountTargets": []
            },
            "action": "delete_share",
        }

        # check service instance configuration
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "" or self.instance.oid is None:
            self.logger.warning("File system %s does not have any mount target" % self.instance.uuid)
        else:
            mount_target = self.get_mount_target_resource()
            params["data"]["mountTargets"] = [self.instance.resource_uuid]

            # grants = []
            if "grant" in self.get_available_capabilities(self.instance.version):
                grants = mount_target.get("details", {}).get("grants", [])
                if len(grants) > 0:
                    self.logger.info("Share with grants %s  " % str(len(grants)))
                    params["data"]["grants"] = grants
                    params["data"]["action"] = "del"
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
        elif action == "manage_mount_target_grant":
            params["steps"] = [self.task_path + "manage_mount_target_grant_step"]
        elif action == "delete_share":
            params["steps"] = []
            if self.instance.version != "2.0":
                params["steps"].append(self.task_path + "manage_mount_target_grant_step")
            params["steps"].append(self.task_path + "delete_mount_targets_step")
        elif action == "manage_replica":
            params["steps"] = [self.task_path + "manage_replica_step"]
            # rename service instance in case of unlink operation
            if params.get("data", {}).get("action") == StorageParamsNames.ReplicaActionUnlink:
                params["steps"].append(self.task_path + "rename_service_instance_step")
            # update rpo in service instance config
            elif params.get("data", {}).get("action") == StorageParamsNames.ReplicaActionUpdate:
                if params.get("data", {}).get("rpo") is not None:
                    params["steps"].append(self.task_path + "update_rpo_step")
        elif action == "manage":
            # for now just mount
            params["steps"] = [self.task_path + "manage_step"]
        elif action == "manage_compliance":
            params["steps"] = [
                self.task_path + "manage_step",
                self.task_path + "update_compliance_step"
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

    def get_available_capabilities(self, version="1.0"):
        orch_capabilities = self.available_capabilities.get(self.get_config("orchestrator_type"))
        if orch_capabilities is None:
            return []
        return orch_capabilities.get(version)

    def has_capability(self, capability):
        if capability not in self.get_available_capabilities(self.instance.version):
            raise ApiManagerError("file system %s capability %s is not available" % (self.uuid, capability))

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({"instance-version": self.instance.version})
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
    def customize_list(controller: 'ServiceController', entities: List["ApiStorageEFS"], *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        if not entities:
            return entities

        account_idx = controller.get_account_idx()
        subnet_idx = controller.get_service_instance_idx(ApiComputeSubnet.plugintype)
        # vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)
        # security_group_idx = controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)
        account_ids = [e.instance.account_id for e in entities]
        storage_service_idx = controller.get_service_instance_idx(
            ApiStorageService.plugintype,
            account_id_list=account_ids,
            index_key="account_id"
        )
        #instance_type_idx = controller.get_service_definition_idx(ApiStorageEFS.plugintype) # TODO

        # get resources
        zones_legacy: Dict[str,Set] = {}
        zones: Dict[str,Set] = {}
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.legacy_share_subnet = subnet_idx.get(entity.subnet_id)
            account_compute_service = storage_service_idx.get(account_id)
            compute_zone_uuid = account_compute_service.resource_uuid
            entity_resource_uuid = entity.instance.resource_uuid
            version = entity.instance.version
            if not entity_resource_uuid:
                continue
            if version=="1.0":
                # legacy
                if not zones_legacy.get(compute_zone_uuid):
                    zones_legacy[compute_zone_uuid] = set()
                zones_legacy[compute_zone_uuid].add(entity_resource_uuid)
            else:
                if not zones.get(compute_zone_uuid):
                    zones[compute_zone_uuid] = set()
                zones[compute_zone_uuid].add(entity_resource_uuid)

        controller.logger.debug("ALL_ZONES %s ||| LEGACY %s" % (zones,zones_legacy))

        if entities and len(entities)==1:
            # if just one, assume we need details. call detail endpoint later
            return entities

        from itertools import islice
        def slice_list(iterable, size):
            it = iter(iterable)
            return iter(lambda: list(islice(it, size)), [])

        # simplification: either one account is passed as filter (e.g. -account), or uuid lists (-size ... -page...)
        # so if more than one account, thus more than one zone, just consider uuids

        # paginate uuids
        pagination = 20
        resources_idx = {}

        resources = []
        if zones_legacy:
            _zones = list(zones_legacy.keys())
            _resources = [zone for subset in zones_legacy.values() for zone in subset] # flatten
            if len(_zones)>1:
                # do not filter by zone, but use uuids and paginate if necessary
                _zones = []
            else:
                # filter by single zone and use uuids and paginate if necessary
                pass
            list_slices = slice_list(_resources,pagination)
            for sublist in list_slices:
                try:
                    resources += ApiStorageEFS(controller).list_mount_target_resources(
                        zones = _zones,
                        uuids = sublist,
                        version="1.0",
                        size=len(sublist)
                    )
                except Exception as ex:
                    controller.logger.error(ex)

        if zones:
            _zones = list(zones.keys())
            _resources = [zone for subset in zones.values() for zone in subset] # flatten
            if len(_zones)>1:
                # do not filter by zone, but use uuids and paginate if necessary
                _zones = []
            else:
                # filter by single zone and use uuids and paginate if necessary
                pass
            list_slices = slice_list(_resources,pagination)
            for sublist in list_slices:
                try:
                    resources += ApiStorageEFS(controller).list_mount_target_resources(
                        zones = _zones,
                        uuids = sublist,
                        version="2.0",
                        size=len(sublist)
                    )
                except Exception as ex:
                    controller.logger.error(ex)

        resources_idx = {r["uuid"]: r for r in resources}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid, {})

        return entities

    def get_share_protocol(self):
        # staas v2.0
        proto = self.get_config("share_data.Nvl_shareProto")
        if proto is not None:
            return proto.lower()
        # staas v1.0
        proto = self.get_config("mount_target_data.share_proto")
        if proto is not None:
            return proto.lower()
        return None

    @property
    def subnet_id(self):
        if not self._subnet_id:
            self._subnet_id = self.get_config("mount_target_data.subnet_id") # legacy
        return self._subnet_id

    @property
    def legacy_share_subnet(self):
        if not self._share_subnet and self.subnet_id:
            subnet = self.controller.get_service_instance(oid=self.subnet_id)
            self._share_subnet = subnet
        return self._share_subnet

    @legacy_share_subnet.setter
    def legacy_share_subnet(self, subnet: 'ApiComputeSubnet'):
        self._share_subnet = subnet

    @property
    def share_site_name(self):
        if not self._share_site_name:
            if self.legacy_share_subnet:
                # staas v1.0
                site = self.legacy_share_subnet.get_config("site")
            else:
                # staas v2.0
                site = self.get_config("share_data.SiteName")
            if site:
                self._share_site_name = site
        return self._share_site_name

    @share_site_name.setter
    def share_site_name(self, site_name: str):
        self._share_site_name = site_name

    def get_share_export_location_ip_address(self, proto, export_location):
        try:
            if proto in __SRV_STORAGE_PROTOCOL_TYPE_NFS__:
                data = export_location.split(":")
                if len(data) > 0:
                    return data[0]
            if proto in __SRV_STORAGE_PROTOCOL_TYPE_CIFS__:
                data = export_location.split("\\")
                if len(data) > 2:
                    return export_location.split("\\")[2]
            return ""
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            return ""

    def get_share_export_location_target(self, proto, export_location):
        try:
            if proto in __SRV_STORAGE_PROTOCOL_TYPE_NFS__:
                data = export_location.split(":")
                if len(data) > 1 and data[1].startswith('/'):
                    return data[1][1:]
            if proto in __SRV_STORAGE_PROTOCOL_TYPE_CIFS__:
                vals = export_location.split("\\")
                if len(vals) > 3:
                    return vals[3]
            return ""
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            return ""

    @staticmethod
    def share_state_mapping(state):
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

    @staticmethod
    def mount_target_state_mapping(state):
        if not state:
            return "unknown"
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
        if self.resource_uuid:
            return True
        return False

    def get_performance_mode(self):
        """get share performance mode

        :return: generalPurpose or localPurpose
        """
        data = self.get_config("share_data")
        if data is None:
            return None
        res = data.get("PerformanceMode")
        if res is None:
            res = "generalPurpose"
        return res

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        error_list = []

        instance_item = {}
        instance_item["NumberOfMountTargets"] = 1 # TODO
        instance_item["nvl_shareProto"] = self.get_share_protocol()
        instance_item["CreationToken"] = self.instance.name
        instance_item["CreationTime"] = format_date(self.instance.model.creation_date)
        instance_item["FileSystemId"] = self.instance.uuid
        instance_item["LifeCycleState"] = self.share_state_mapping(self.instance.status)
        instance_item["Name"] = self.instance.name
        instance_item["OwnerId"] = self.account.uuid
        instance_item["nvl-OwnerAlias"] = self.account.name
        instance_item["InstanceVersion"] = self.instance.version
        instance_item["PerformanceMode"] = self.get_performance_mode()
        instance_item["nvl-AvailabilityZone"] = self.share_site_name
        instance_item["nvl-complianceMode"] = self.get_config("share_data.ComplianceMode")
        if self.get_config("share_data.ComplianceMode"):
            instance_item["nvl-complianceRPO"] = self.get_config("share_data.Rpo")

        # capabilities
        instance_item["nvl-Capabilities"] = self.get_available_capabilities(self.instance.version)

        instance_item["nvl-stateReason"] = {}
        if self.instance.status == "ERROR":
            instance_item["nvl-stateReason"].update(
                {
                    "nvl-code": "400",
                    "nvl-message": self.instance.last_error
                }
            )
        else:
            instance_item["nvl-stateReason"].update(
                {
                    "nvl-code": None,
                    "nvl-message": None
                }
            )

        try:
            resource = self.get_mount_target_resource()
        except Exception as ex:
            resource = {}
            error_list.append(str(ex))

        exports = dict_get(resource, "details.exports", default=[])
        if exports:
            # TODO refactor resource code in order to return primary ip address, or remove it
            first_proto = exports[0].get("protocol", instance_item["nvl_shareProto"])
            first_path = exports[0].get("mounts",[""])[0]
            ip_address = self.get_share_export_location_ip_address(first_proto, first_path)
        else:
            ip_address = "" # None not valid for view
        instance_item["IpAddress"] = ip_address
        instance_item["MountTargets"] = exports

        instance_item["EncryptionState"] = dict_get(resource, "details.remote_encryption_state", default="unencrypted")
        if instance_item["EncryptionState"] == "unencrypted":
            instance_item["Encrypted"] = False
        else:
            instance_item["Encrypted"] = True

        snapshot_policy = dict_get(resource, "details.snapshot_policy")
        if snapshot_policy:
            instance_item["SnapshotPolicy"] = snapshot_policy
        replica_policy = dict_get(resource, "details.snapmirror_policy")
        if replica_policy:
            instance_item["ReplicaPolicy"] = replica_policy

        share_size = dict_get(resource, "details.size", default=0)
        instance_item["Size"] = float(share_size)
        size_bytes = dict_get(resource, "details.size_bytes")
        if not size_bytes:
            size_bytes = int(float(share_size)*1024*1024*1024)
        instance_item["SizeInBytes"] = {
            "Value": size_bytes,
            "Timestamp": format_date(self.instance.model.creation_date),
        }

        instance_item["FileSystemState"] = dict_get(resource, "details.remote_state", default="N/A")
        return instance_item

    def get_source_efs(self, resource=None):
        """if replica, find source efs

        :param resource: _description_, defaults to None
        :type resource: _type_, optional
        """
        if not self.is_replica():
            return None
        # need detail info in order to have a list of snapmirrors
        if not resource:
            resource = self.get_mount_target_resource()
        if not resource:
            return None
        source_res_info = dict_get(resource,"details.snapmirrors")
        if source_res_info:
            if len(source_res_info)>1:
                self.logger.error("More than one source volume detected for replica volume %s",self.uuid)
            source_res_info = source_res_info[0]
            try:
                source_service: 'ApiStorageEFS' = self.controller.get_service_instance_by_resource_uuid(
                    resource_uuid=source_res_info.get("source_id"),
                    plugintype=ApiStorageEFS.plugintype
                )
            except Exception as ex:
                self.logger.info("Unable to find source service for volume %s: %s",self.uuid,ex)
                # continue and return partial result

            r_uuid = source_res_info.pop("source_id",None)
            source_res_info.pop("source_name",None)
            source_res_info.pop("uuid",None)
            source_res_info.pop("source_path",None)
            source_res_info.pop("dest_path",None)

            if source_service:
                config_source_id = self.instance.get_config("share_data.SourceId")
                if config_source_id != source_service.uuid:
                    self.logger.error("share_data.SourceId mismatch with configuration: expected %s but found %s", config_source_id, source_service.uuid)
                source_res_info["source_id"] = source_service.uuid
                source_res_info["source_name"] = source_service.name
            else:
                source_res_info["msg"] = "source service not found with resource uuid: %s" % r_uuid
            source_res_info.pop("policy_name", None)
            return source_res_info
        return None

    def get_replicas(self, resource=None):
        """
        find replicas by looking at resource links
        """
        if self.is_replica():
            return None
        linked_replica_services = []
        replica_services = []

        # need detail info in order to have a list of snapmirrors
        if not resource:
            resource = self.get_mount_target_resource()
        if not resource:
            return []
        replica_resources = dict_get(resource,"details.snapmirrors", default=[])

        replica_res_uuids = [r.get("replica_id") for r in replica_resources]
        if replica_res_uuids:
            try:
                replica_services: List['ApiStorageEFS'] = self.controller.get_service_instances_by_resource_uuids(
                    resource_uuid_list=replica_res_uuids,
                    plugintype=ApiStorageEFS.plugintype
                )
            except Exception as ex:
                self.logger.info("Unable to find service replicas for volume %s: %s",self.uuid,ex)
                # continue and return partial result
            resource_service_map = {service.resource_uuid : service for service in replica_services}

            for replica in replica_resources:
                r_uuid = replica.pop("replica_id",None)
                replica.pop("replica_name",None)
                replica.pop("uuid",None)
                replica.pop("source_path",None)
                replica.pop("dest_path",None)
                replica_service = resource_service_map.get(r_uuid)
                if replica_service:
                    replica["replica_id"] = replica_service.uuid
                    replica["replica_name"] = replica_service.name
                    replica["rpo"] = replica_service.get_config("share_data.Rpo")
                else:
                    replica["msg"] = "replica service not found with resource uuid: %s" % r_uuid
                replica.pop("policy_name", None)
                linked_replica_services.append(replica)

        return linked_replica_services

    def aws_info_target(self):
        """Get info for mount target as required by aws api

        :return:
        """
        if not self.resource:
            try:
                resource = self.get_mount_target_resource()
            except Exception as ex:
                self.logger.error(ex)
                resource = None
            #self.logger.warning(resource)
        else:
            resource = self.resource

        share_proto = self.get_share_protocol()
        exports = dict_get(resource, "details.exports", default=[])
        if exports:
            ip_address = self.get_share_export_location_ip_address(share_proto, exports[0].get("mounts",[""])[0])
        else:
            ip_address = "" # None not valid for view

        target_item = {}
        target_item["FileSystemId"] = self.instance.uuid
        target_item["MountTargetId"] = "\n".join([mount for export in exports for mount in export.get("mounts")])

        #target_item["MountTargetId"] = self.get_share_export_location_target(share_proto, export_location)
        #target_item["IpAddress"] = self.get_share_export_location_ip_address(share_proto, export_location)
        target_item["IpAddress"] = ip_address

        target_item["LifeCycleState"] = target_item["LifeCycleState"] = self.mount_target_state_mapping(dict_get(resource,"state"))

        target_item["MountTargetState"] = dict_get(resource, "details.remote_state", default="N/A")
        target_item["NetworkInterfaceId"] = None
        target_item["OwnerId"] = self.account.uuid
        target_item["nvl-OwnerAlias"] = self.account.name
        target_item["SubnetId"] = self.subnet_id
        target_item["nvl-ShareProto"] = share_proto
        target_item["nvl-AvailabilityZone"] = self.share_site_name
        target_item["EncryptionState"] = dict_get(resource, "details.remote_encryption_state", default="unencrypted")

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
        vpc_inst: 'ApiComputeVPC' = subnet_inst.get_parent()

        if self.instance.account_id != subnet_inst.instance.account_id:
            raise ApiManagerError("Subnet %s is not in the StorageService account" % subnet_id)

        cfg = self.instance.config_object
        share_data = cfg.get_json_property("share_data")

        if self.get_performance_mode() == "generalPurpose":
            subnet = None
        elif self.get_performance_mode() == "localPurpose":
            subnet = subnet_inst.get_cidr()
        else:
            raise ApiManagerError("Invalid performance mode %s" % self.get_performance_mode())

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

        # check service instance configuration
        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            return None

        size = self.get_config("share_data.Nvl_FileSystem_Size")
        new_size = data.get(StorageParamsNames.Nvl_FileSystem_Size)

        params = {
            "resource_params": {}
        }
        if self.instance.version == "2.0":
            is_replica = self.instance.get_config("share_data.SourceId") is not None
            if is_replica:
                raise ApiManagerError("Resize not available for replicas")

            params["resource_params"].update({
                "action": "resize",
                "new_size": new_size,
                "extend_shrink": "extend" if new_size > size else "shrink",
            })
        else:
            params["resource_params"].update({
                "action": "resize",
                "size": new_size,
            })
        self.update(**params)

        # update service instance config with new size
        self.set_config("share_data.%s" % StorageParamsNames.Nvl_FileSystem_Size, new_size)

        self.logger.info("Update resource mount target using task %s" % str(self.active_task))
        return self.active_task

    def update_efs_status(self, **data):
        """Update status of remote efs

        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        # check capability
        self.has_capability("set-status")

        # verify permissions
        self.instance.verify_permisssions("update")

        # check service instance configuration
        if not self.instance.resource_uuid:
            return None

        status = data.get(StorageParamsNames.Nvl_MountTarget_Status)

        params = {
            "resource_params": {
                "action": "set-status",
                "state": status,
            },
        }
        self.update(**params)
        self.logger.info("Update resource mount target using task %s" % str(self.active_task))
        return self.active_task

    def update_snapshot_policy(self, **data):
        """Update snapshot policy of remote efs

        :param data:
        :return:
        """
        # check capability
        self.has_capability("snapshot-policy")

        # verify permissions
        self.instance.verify_permisssions("update")

        # check service instance configuration
        if not self.instance.resource_uuid:
            return None

        snapshot_policy = data.get(StorageParamsNames.Nvl_SnapshotPolicy)
        service_definition_name = f"staas_snap_{snapshot_policy}"
        service_definition = self.controller.get_service_def(service_definition_name)
        snapshot_policy_value = service_definition.get_config("ontap_snapshot_policy")

        params = {
            "resource_params": {
                "action": "update-snapshot-policy",
                "snapshot_policy": snapshot_policy_value,
            },
        }
        self.update(**params)
        self.logger.info("Update resource mount target using task %s" % str(self.active_task))
        return self.active_task

    def manage_grant(self, action=None, **data):
        """assign or revoke a grant

        :param action: string add or delete
        :param data: the action params
        :return:
        """
        # check capability
        self.has_capability("grant")

        if action is None:
            return None

        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            return None

        # verify permissions
        self.instance.verify_permisssions("update")

        orchestrator_type = self.get_orchestrator_type()
        client_type: str = data.get("client_type")
        if client_type:
            client_type = client_type.upper()

        if self.instance.version == "2.0" and orchestrator_type == "ontap":
            if action == "add":
                if (self.is_replica() and data.get("access_level") not in [
                    __SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_LOWER__,
                    __SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_UPPER__
                ]):
                    raise ApiManagerError(
                        f"Cannot grant an access level other than read-only to an efs replica instance.\n"
                        f"instance id  : {self.instance.uuid}\n"
                        f"instance type: replica\n"
                        f"access grant : {data.get('access_level')}"
                    )

                protocol: str = data.get("protocol")
                if not protocol:
                    protocol = self.get_share_protocol()
                else:
                    protocol = protocol.lower()
                data["protocol"] = protocol

                if client_type == "ID":
                    clients = data.pop("client_N")
                    account = self.get_account()
                    site_name = self.get_config("share_data.SiteName")

                    # check clients are valid and get resource provider target ids
                    data["clients"] = self._check_get_resource_client_list(account.uuid, clients, site_name)
                elif client_type == "CIDR":
                    data["clients"] = data.pop("client_N")
            elif action == "del":
                grants_to_delete = data.pop("access_ids")
                res = self.get_mount_target_resource()
                grants = res.get("details", {}).get("grants", [])
                grants_ids = [int(grant.get("id")) for grant in grants]
                if not set(grants_to_delete).issubset(grants_ids):
                    raise Exception("One or more grant ids do not exist. Please check and try again.")
                data = {"ids": grants_to_delete}

        params = {
            "data": {
                "grant": data,
                "action": action,
            },
            "action": "manage_mount_target_grant",
        }
        self.action(**params)

        self.logger.info(f"{action} export policy rule using task {str(self.active_task)}")
        return self.active_task

    def is_replica(self):
        """Check whether an efs instance is a source storage or a replica

        :return: True if the instance is a replica, False otherwise
        """
        if self.instance.get_config("share_data.SourceId"):
            return True
        return False

    def manage(self, action: str = None, **data):
        """execute an operation on any share instance

        :param action: action name, defaults to None
        :type action: str, optional
        """
        # check capability
        # NB: for now "mount" falls under set-status
        # TODO refactor capabilities
        self.has_capability("set-status")

        if action is None:
            # TODO decide
            return None

        if not self.instance.resource_uuid:
            # TODO decide in which cases we can proceed even without resource, if any
            raise ApiManagerError("No resource to manage for action %s" % action)

        # verify permissions
        self.instance.verify_permisssions("update")

        # TODO for now only "mount" handled here
        data["subaction"] = action
        params = {
            "data": data,
            "action": "manage",
        }
        self.action(**params)

        self.logger.info(
            "Execute %s operation on efs %s using task %s" % (action, self.instance.uuid, str(self.active_task))
        )
        return self.active_task

    def update_compliance(self, **data):
        """

        :param data:
        :return:
        """
        # check capability
        self.has_capability("compliance")

        # verify permissions
        self.instance.verify_permisssions("update")

        # check service instance configuration
        if not self.instance.resource_uuid:
            raise Exception("unable to find resource")

        # check service instance is a replica
        if self.is_replica():
            raise ApiManagerError(
                "Instance %s is a replica. Compliance mode can only be applied to source volumes"
                % self.instance.uuid
            )

        compliance = self.get_config("share_data.ComplianceMode")
        new_compliance = data.get(StorageParamsNames.Nvl_ComplianceMode)
        if compliance and new_compliance:
            raise ApiManagerError("Compliance mode is already enabled for instance %s" % self.instance.uuid)
        if not compliance and not new_compliance:
            raise ApiManagerError("Compliance mode is already disabled for instance %s" % self.instance.uuid)

        subaction_name = "compliance_enable" if new_compliance is True else "compliance_disable"
        params = {
            "data": {
                "subaction": subaction_name,
                "subaction_params": {
                    "compliance": new_compliance
                }
            },
            "action": "manage_compliance",
        }
        if new_compliance:
            params["data"]["subaction_params"]["rpo"] = data.get(StorageParamsNames.Nvl_Rpo)
        params["alias"] = self.plugintype + '.action.' + subaction_name
        self.action(**params)
        self.logger.info("Update resource mount target using task %s", str(self.active_task))
        return self.active_task

    def manage_replica(self, action=None, **data):
        """execute an operation (unlink, suspend, resume, ...) on a replica instance

        :param action: action string
        :param data: action params
        :return:
        """
        # check capability
        self.has_capability("replica")

        if action is None:
            return None

        if self.instance.resource_uuid is None or self.instance.resource_uuid == "":
            return None

        # verify permissions
        self.instance.verify_permisssions("update")

        # verify the service instance is a replica
        if not self.is_replica():
            raise ApiManagerError("Instance %s is not a replica, but a source volume." % self.instance.uuid)

        data["action"] = action
        params = {
            "data": data,
            "action": "manage_replica",
        }
        self.action(**params)

        self.logger.info(
            "Execute %s operation on replica %s using task %s" % (action, self.instance.uuid, str(self.active_task))
        )
        return self.active_task

    #
    # resource methods
    #
    def get_mount_target_resource(self, force=False):
        """Get mount target share info from the resource layer

        :param force: if True, get even if already available
        :type force: bool, optional
        :return: resource information
        :rtype: Dict
        """
        if self.resource and force==False:
            return self.resource
        if not self.has_mount_target():
            return None
        uri = f"/v{self.instance.version}/nrs/provider/shares/{self.instance.resource_uuid}"
        share = self.controller.api_client.admin_request("resource", uri, "get").get("share")
        self.logger.debug("get_mount_target_resource: %s", share)
        return share

    def list_mount_target_resources(self, zones=None, uuids=None, size=20, version=None):
        """List resources
        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size}
        if zones:
            data["parent_list"] = ",".join(zones)
        if uuids:
            data["uuids"] = ",".join(uuids)
        self.logger.debug("list_resources %s" % data)

        if not version:
            # if not specified use version of current service instance
            version = self.instance.version

        res = self.controller.api_client.admin_request(
            "resource",
            f"/v{version}/nrs/provider/shares",
            "get",
            data=urlencode(data),
            timeout=100,
        ).get("shares", [])

        return res

    def create_mount_target_resource(self, task, **data):
        """Called by celery task create_mount_target_task only while creating a mount point

        :param task: the task which is calling the  method
        :param share_proto: share protocol  nfs/cifs
        :param av_zone: availability zone
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
        """Asynchronous task method. Delete share resource

        :param task: asynchronous task invoking the method
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            uri = f"/v{self.instance.version}/nrs/provider/shares/{self.instance.resource_uuid}"
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

    # # AHMAD 17-12-2020 NSP-160
    # def delete_mount_grants(self, task, grants):
    #     """Asynchronous task method. Delete share resource
    #
    #     :param task: asynchronous task invoking the method
    #     :return: True
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     if len(grants) > 0:
    #         self.logger.debug("There are %s grants to delete" % len(grants))
    #         for grant in grants:
    #             data = {
    #                 "share": {
    #                     "grant": {
    #                         "action": "del",
    #                         "access_id": grant,
    #                     }
    #                 }
    #             }
    #             self.logger.debug("Removing Grant with id %s" % grant)
    #             uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
    #             res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
    #             job = res.get("taskid")
    #             if job is not None:
    #                 self.logger.debug("Removing Grant  %s with job %s" % (grant, job))
    #                 self.wait_for_task(job, delta=2, maxtime=180, task=task)
    #                 self.logger.debug(
    #                     "Deleted grant resource %s in file system instance %s res=%s" % (data, self.instance.uuid, res)
    #                 )
    #     else:
    #         self.logger.debug("There are no Grants to delete ")
    #     return True

    def delete_share_mount_targets(self, task, mounts):
        """Asynchronous task method. Delete share resource

        :param task: asynchronous task invoking the method
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if len(mounts) > 0:
            self.logger.debug("There are %s mount targets to delete" % len(mounts))
            for mount in mounts:
                self.logger.debug("Removing mount target with id %s" % mount)
                try:
                    if self.instance.version == "2.0":
                        uri = "/v2.0/nrs/provider/shares/%s" % self.instance.resource_uuid
                    else:
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
                self.logger.debug("Delete mount target resource: %s" % res)
        return True

    def update_resource(self, task, **kwargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asynchronous environment

        :param task: the task which is calling the  method
        :param dict kwargs: unused only for compatibility
        :return:
        """
        action = kwargs.pop("action", None)
        if action == "resize":
            if self.instance.version == "2.0":
                uri = "/v2.0/nrs/provider/shares/%s/resize" % self.instance.resource_uuid
            else:
                uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
        elif action == "set-status":
            if self.instance.version == "2.0":
                uri = "/v2.0/nrs/provider/shares/%s/setstatus" % self.instance.resource_uuid
            else:
                uri = "/v1.0/nrs/provider/shares/%s" % self.instance.resource_uuid
        elif action == "update-snapshot-policy":
            if self.instance.version == "2.0":
                uri = "/v2.0/nrs/provider/shares/%s/snapshotpolicy" % self.instance.resource_uuid
            else:
                raise ApiManagerError("Snapshot policy update not supported for STAAS v1.0")
        else:
            return None

        data = {"share": kwargs}
        res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
        job = res.get("taskid")
        if job is not None:
            self.wait_for_task(job, delta=2, maxtime=180, task=task)
        return job

    def manage_mount_target_grant_resource(self, task, grant, action):
        """Asynchronous task method performing grant operation (add/del)

        :param task: running asynchronous task
        :param grant: grant params
        :param grants: the operation to run
        :return:
        """
        if grant:
            data = {"share": {}}
            if self.instance.version == "2.0":
                # API v2.0 - nuova gestione / nuovo codice
                if action == "add":
                    data["share"]["policy"] = {
                        "action": "grant_access",
                        "rw_access": grant.get("access_level"),
                        "su_access": grant.get("access_superuser"),
                        "client_type": grant.get("client_type").lower(),
                        "clients": grant.get("clients"),
                        "protocol": grant.get("protocol", "nfs").lower(),
                    }
                elif action == "del":
                    data["share"]["policy"] = {
                        "action": "revoke_access",
                        "access_ids": grant.get("ids"),
                    }
                else:
                    raise ApiManagerError(f"Action not supported: {action}")

                res = self.controller.api_client.admin_request(
                    "resource",
                    "/v2.0/nrs/provider/shares/%s/policy" % self.instance.resource_uuid,
                    "put",
                    data=data,
                )
            else:
                # vecchia gestione / vecchio codice
                data["share"]["grant"] = {}
                if action == "add":
                    data["share"]["grant"].update(
                        {
                            "action": action,
                            "access_level": grant.get("access_level"),
                            "access_type": grant.get("access_type"),
                            "access_to": grant.get("access_to"),
                        }
                    )
                elif action == "del":
                    data["share"]["grant"].update(
                        {
                            "action": action,
                            "access_ids": grant.get("ids"),
                        }
                    )
                else:
                    raise ApiManagerError(f"Action not supported: {action}")

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
                "Manage grant for efs instance %s: res=%s" % (self.instance.uuid, res)
            )
            return job
        else:
            self.logger.debug("There are no grants to handle")
            return True

    def manage_resource(self, task, **kwargs):
        subaction = kwargs.get("subaction")
        subaction_params = kwargs.get("subaction_params")
        data = {
            "share": {
                "subaction": subaction,
                "subaction_params": subaction_params
            }
        }
        res = self.controller.api_client.admin_request(
            "resource",
            "/v2.0/nrs/provider/shares/%s" % self.instance.resource_uuid,
            "put",
            data=data,
        )
        job = res.get("taskid")
        if job is not None:
            self.wait_for_task(job, delta=2, maxtime=180, task=task)
        self.logger.debug(
            "Execute %s operation on replica %s: res=%s " % (subaction, self.instance.uuid, res)
        )
        return job

    def manage_replica_resource(self, task, **kvargs):
        """

        :param task:
        :param kvargs:
        :return:
        """
        action = kvargs.get("action")
        data = {
            "share": {
                "subaction": action,
                "new_name": kvargs.get("new_name"),
                "rpo": kvargs.get("rpo"),
            }
        }

        res = self.controller.api_client.admin_request(
            "resource",
            "/v2.0/nrs/provider/shares/%s/replication" % self.instance.resource_uuid,
            "put",
            data=data,
        )

        job = res.get("taskid")
        if job is not None:
            self.wait_for_task(job, delta=2, maxtime=180, task=task)
        self.logger.debug(
            "Execute %s operation on replica %s: res=%s " % (action, self.instance.uuid, res)
        )
        return job
