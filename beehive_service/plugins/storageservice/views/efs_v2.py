# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import re
from ipaddress import IPv4Address, AddressValueError
from typing import TYPE_CHECKING, List, Dict
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from beecell.util import ensure_text
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    GetApiObjectRequestSchema,
    PaginatedRequestQuerySchema,
    ApiView,
    ApiManagerWarning, ApiManagerError,
)
from beehive.common.assert_util import AssertUtil
from beehive.common.data import operation
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.service_util import (
    __SRV_STORAGE_QUERY_MAX_SIZE__,
    __SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__,
    __SRV_STORAGE_PERFORMANCE_MODE__,
    __SRV_AWS_STORAGE_STATUS__,
    __SRV_STORAGE_STATUS__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE__,
    __SRV_STORAGE_GRANT_ACCESS_LEVEL__,
    __REGEX_SHARE_GRANT_ACCESS_TO_USER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_CIDR_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_ID_LOWER__,
    __SRV_STORAGE_PROTOCOL_TYPE__,
    __SITE_NAMES__,
    __MAP_SITE_NAME_SHORT_SUFFIX__,
    __SRV_STORAGE_GRANT_ACCESS_PROTOCOL__,
    __SRV_STORAGE_SNAPSHOT_POLICY_VALUES__,
    __SRV_STORAGE_REPLICA_RPO_VALUES__,
)
from beehive_service.plugins.storageservice.controller import (
    StorageParamsNames as StPar,
    ApiStorageService,
    ApiStorageEFS,
)
from beehive_service.plugins.storageservice.views.efs import DescribeFileSystems, FileSystemDescriptionResponseSchema
from beehive_service.views import ServiceApiView

if TYPE_CHECKING:
    from beehive_service.controller import ServiceController


class CrudFileSystemApiResponseV20Schema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class CreateFileSystemApiRequestV20Schema(Schema):
    owner_id = fields.String(required=True, metadata={"example": "posc-preprod", "description": "account id"})
    Nvl_FileSystem_Size = fields.Integer(
        required=True,
        metadata={"example": 10, "description": "size in Giga byte of storage file system to create"},
    )
    Nvl_FileSystem_Type = fields.String(
        required=False,
        load_default=None,
        metadata={"example": "store.ontap.m1", "description": "service definition for storage file system"},
    )
    CreationToken = fields.String(
        required=True,
        validate=Length(min=1, max=64),
        metadata={"example": "myFileSystem1", "description": "a string used to identify the file system"},
    )
    SiteName = fields.String(required=True, validate=OneOf(__SITE_NAMES__), metadata={"example": "SiteTorino05"})
    Nvl_shareProto = fields.String(
        required=False,
        load_default="NFS",
        validate=OneOf(__SRV_STORAGE_PROTOCOL_TYPE__),
        metadata={"example": "NFS", "description": "File system share protocol"},
    )
    ComplianceMode = fields.Boolean(
        required=False,
        dump_default=True,
        metadata={"description": "ACN compliant or not; if compliant, ontap creates snaplock volume too"},
    )
    Encrypted = fields.Boolean(
        required=False,
        dump_default=False,
        metadata={"description": "whether to create an encrypted volume or not"},
    )
    Rpo = fields.String(
        required=False,
        validate=OneOf(["12h","24h"]),
        metadata={"description": "share rpo, used only if compliance"},
    )
    version = fields.String(required=False, metadata={"description": "efs instance version"})
    SnapshotPolicy = fields.String(
        required=False,
        validate=OneOf(__SRV_STORAGE_SNAPSHOT_POLICY_VALUES__),
        metadata={"example": "4h_7d_2w", "description": "snapshot policy value"},
    )

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if (
            "KmsKeyId" in keys
            or "ProvisionedThroughputInMibps" in keys
            or "ThroughputMode" in keys
        ):
            raise ValidationError(
                "The KmsKeyId, ProvisionedThroughputInMibps and "
                "ThroughputMode parameter are not supported"
            )
        if data.get("ComplianceMode") and data.get("Rpo",None) is None:
            raise Exception("When compliance mode is enabled you must specify a valid rpo %s",self.fields.get('Rpo').validate.choices)

        name = data.get("CreationToken")
        name = name.lower()
        if name.startswith(StPar.ReplicaNamePrefix):
            raise ValidationError(
                "Efs instance name cannot start with %s prefix" % StPar.ReplicaNamePrefix
            )

class CreateFileSystemApiBodyRequestV20Schema(Schema):
    body = fields.Nested(CreateFileSystemApiRequestV20Schema, context="body")


class FileSystemSize(Schema):
    Value = fields.Float(
        required=True,
        metadata={"example": "10", "description": "Latest known metered size(in bytes) of data stored in the file system"},
    )
    Timestamp = fields.DateTime(
        required=False,
        metadata={"example": "1403301078", "description": "time of latest metered size of data in the file system"},
    )


class CustomMountTargetParamsApiResponse(Schema):
    CreationToken = fields.String(
        required=True,
        validate=Length(min=1, max=64),
        metadata={"description": "file system storage name"},
    )
    CreationTime = fields.DateTime(
        required=True,
        metadata={"example": "1970-01-01T00:00:00Z", "description": "creation time file system storage"},
    )
    NumberOfMountTargets = fields.Integer(
        required=False,
        dump_default=0,
        load_default=0,
        validate=Range(min=0),
        metadata={"description": "current number of mount targets that the file system has"},
    )
    SizeInBytes = fields.Nested(
        FileSystemSize,
        required=True,
        many=False,
        allow_none=True,
        metadata={"description": "file System dimension"},
    )
    Name = fields.String(required=False, validate=Length(min=0, max=256), metadata={"description": "resource tag name"})
    nvl_shareProto = fields.String(
        required=False,
        allow_none=False,
        metadata={"example": "NFS", "description": "file system share protocol"},
    )


class StateReasonResponseV20Schema(Schema):
    nvl_code = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-code",
        metadata={"description": "state code"},
    )
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-message",
        metadata={"description": "state message"},
    )

class CreateFileSystemResultApiResponseV20Schema(Schema):
    FileSystem = fields.Nested(FileSystemDescriptionResponseSchema, required=True, many=False, allow_none=False)

class CreateFileSystem(ServiceApiView):
    summary = "Create storage efs file system"
    description = "Create storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "CreateFileSystemResultApiResponseV20Schema": CreateFileSystemResultApiResponseV20Schema,
        "CreateFileSystemApiRequestV20Schema": CreateFileSystemApiRequestV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemApiBodyRequestV20Schema)
    parameters_schema = CreateFileSystemApiRequestV20Schema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CreateFileSystemResultApiResponseV20Schema}}
    )
    response_schema = CreateFileSystemResultApiResponseV20Schema

    def post(self, controller: 'ServiceController', data, *args, **kwargs):
        version: str = kwargs.get("version", "default")
        if version.startswith("v"):
            instance_version = version[1:]
            version = f"0{version[1]}"
        else:
            instance_version = "1.0"
            version = "default"

        service_definition_id = data.get("Nvl_FileSystem_Type")
        account_id = data.get("owner_id")
        name = data.get("CreationToken")
        snapshot_policy = data.get("SnapshotPolicy")

        # check account
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiStorageService.plugintype
        )

        # get definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiStorageEFS.plugintype)
            data["Nvl_FileSystem_Type"] = service_definition.oid
        else:
            service_definition = controller.get_service_def(service_definition_id)

        # get snapshot policy definition
        if snapshot_policy:
            snapshot_policy_service_def_name = f"staas_snap_{snapshot_policy}"
            snapshot_policy_service_def = controller.get_service_def(snapshot_policy_service_def_name)
            snapshot_policy_value = snapshot_policy_service_def.get_config("ontap_snapshot_policy")
            data.update({"snapshot_policy": snapshot_policy_value})

        # create service
        data["computeZone"] = parent_plugin.resource_uuid
        desc = "efs " + name + " owned by " + account.name
        cfg = {
            "share_data": data,
            "computeZone": parent_plugin.resource_uuid,
            "StorageService": parent_plugin.resource_uuid,
            "version": version,
        }
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=cfg,
            instance_version=instance_version,
        )
        plugin.account = account
        response = {
            "FileSystem": plugin.aws_info() # NB: FileSystem = same as key in response schema
        }
        return response, 202


class DescribeFileSystemsRequestV20Schema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
    )
    CreationToken = fields.String(
        required=False,
        validate=Length(min=1, max=64),
        context="query",
        metadata={"example": "myFileSystem1", "description": "file system storage name"},
    )
    FileSystemId = fields.String(required=False, context="query", metadata={"description": "ID of the File System"})
    MaxItems = fields.Integer(
        required=False,
        dump_default=10,
        load_default=10,
        context="query",
        metadata={"example": "10", "description": "max number elements to return in the response"},
    )
    Marker = fields.String(
        required=False,
        dump_default="0",
        load_default="0",
        context="query",
        metadata={"example": "0", "description": "pagination token"},
    )


class DescribeFileSystemResponseV20Schema(FileSystemDescriptionResponseSchema):
    nvl_stateReason = fields.Nested(
        StateReasonResponseV20Schema,
        many=False,
        required=False,
        allow_none=True,
        data_key="nvl-stateReason",
    )


class DescribeFileSystemsResponseV20Schema(Schema):
    FileSystems = fields.Nested(DescribeFileSystemResponseV20Schema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, metadata={"description": "pagination token"})
    NextMarker = fields.String(required=True, allow_none=True, metadata={"description": "next pagination token"})
    nvl_fileSystemTotal = fields.Integer(
        required=True,
        allow_none=True,
        data_key="nvl-fileSystemTotal",
        metadata={"description": "total number of filesystem items"},
    )


class DescribeFileSystems2(DescribeFileSystems):
    pass


class DescribeFileSystems3(ServiceApiView):
    summary = "Describe storage efs file system"
    description = "Describe storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "DescribeFileSystemsResponseV20Schema": DescribeFileSystemsResponseV20Schema,
        "DescribeFileSystemsRequestV20Schema": DescribeFileSystemsRequestV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeFileSystemsRequestV20Schema)
    parameters_schema = DescribeFileSystemsRequestV20Schema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeFileSystemsResponseV20Schema}}
    )
    response_schema = DescribeFileSystemsResponseV20Schema

    def get(self, controller: 'ServiceController', data, *args, **kwargs):
        size = data.get("MaxItems")
        if size is not None and (size == -1 or abs(size) > __SRV_STORAGE_QUERY_MAX_SIZE__):
            raise ApiManagerWarning("Too large size value. You should use pagination.")

        storage_id_list = []
        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        # check Account
        owner_ids = data.get("owner_id_N", [])

        if len(owner_ids) > 0:
            account_id_list, zone_list = self.get_account_list(controller, data, ApiStorageService)
            if len(account_id_list) == 0:
                raise ApiManagerWarning("No StorageService found for owners ", code=404)
        else:
            account_id_list = []

        if data.get("FileSystemId", None) is not None:
            storage_inst = controller.get_service_instance(data.get("FileSystemId", None))
            AssertUtil.assert_is_not_none(
                storage_inst.getPluginType(ApiStorageEFS.plugintype),
                "instance id %s is not of plugin type %s" % (storage_inst.oid, ApiStorageEFS.plugintype),
            )
            storage_id_list.append(storage_inst.oid)

        if data.get(StPar.CreationToken, None) is not None:
            storage_inst = controller.get_service_instance(data.get(StPar.CreationToken, None))
            AssertUtil.assert_is_not_none(
                storage_inst.getPluginType(ApiStorageEFS.plugintype),
                "instance id %s is not of plugin type %s" % (storage_inst.oid, ApiStorageEFS.plugintype),
            )
            storage_id_list.append(storage_inst.oid)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_id_list=storage_id_list,
            account_id_list=account_id_list,
            plugintype=ApiStorageEFS.plugintype,
            **data_search,
        )
        storage_instances = [r.aws_info() for r in res]

        if total == 0:
            next_marker = "0"
        else:
            next_marker = str(data_search["page"] + 1)

        response = {
            "FileSystems": storage_instances,
            "Marker": data.get("Marker"),
            "NextMarker": next_marker,
            "nvl-fileSystemTotal": total,
        }

        return response


class UpdateFileSystemResponseV20Schema(Schema):
    CreationToken = fields.String(
        required=True,
        validate=Length(min=1, max=64),
        metadata={"description": "file system storage name"},
    )
    CreationTime = fields.DateTime(
        required=True,
        metadata={"example": "1970-01-01T00:00:00Z", "description": "creation time file system storage"},
    )
    Encrypted = fields.Boolean(
        required=False,
        load_default=False,
        metadata={"description": "boolean value that indicate if the storage file system is encrypted"},
    )
    FileSystemId = fields.String(required=True, metadata={"description": "ID of the storage file system"})
    KmsKeyId = fields.String(
        required=False,
        validate=Length(min=1, max=2048),
        metadata={"description": "ID of a Key Management Service"},
    )

    LifeCycleState = fields.String(
        required=True,
        validate=OneOf(__SRV_AWS_STORAGE_STATUS__),
        metadata={
            "example": " | ".join(map(str, __SRV_AWS_STORAGE_STATUS__)),
            "description": "LifeCycle state of FileSystem"
        },
    )

    Name = fields.String(required=False, validate=Length(min=0, max=256), metadata={"description": "resource tag name"})

    NumberOfMountTargets = fields.Integer(
        required=False,
        dump_default=0,
        load_default=0,
        validate=Range(min=0),
        metadata={"description": "current number of mount targets that the file system has"},
    )

    OwnerId = fields.String(required=True, metadata={"description": "account id that created the file system"})
    nvl_OwnerAlias = fields.String(required=True, metadata={"description": "account name that created the file system"})

    SizeInBytes = fields.Nested(
        FileSystemSize,
        required=True,
        many=False,
        allow_none=True,
        metadata={"description": "File System dimension (Bytes)"},
    )

    PerformanceMode = fields.String(
        required=False,
        load_default=__SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__,
        allow_none=True,
        validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__),
        metadata={"description": ""},
    )

    ProvisionedThroughputInMibps = fields.Integer(
        required=False,
        metadata={"description": "The throughput, measured in MiB/s, that you want to provision for a file system."},
    )

    ThroughputMode = fields.String(
        required=False,
        validate=OneOf(["bursting", "provisioned"]),
        metadata={
            "description": (
                "The throughput mode for a file system. There are two throughput modes "
                "to choose from for your file system: bursting and provisioned."
            )
        },
    )


class UpdateFileSystemRequestV20Schema(Schema):
    Nvl_FileSystem_Size = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 10, "description": "Size of the file system size in Giga "},
    )
    Nvl_MountTarget_Status = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(__SRV_STORAGE_STATUS__),
        metadata={"example": "online", "description": "The mount target status: online | offline"},
    )
    Nvl_SnapshotPolicy = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(__SRV_STORAGE_SNAPSHOT_POLICY_VALUES__),
        metadata={"example": "4h_1d", "description": "snapshot policy value"},
    )
    Nvl_ComplianceMode = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "ACN compliant or not. If True, a snaplock volume is created and linked to the main volume;"
                    " if False, the snaplock volume is unlinked from the main volume"},
    )
    Rpo = fields.String(
        required=False,
        validate=OneOf(["12h","24h"]),
        metadata={"description": "Share RPO, used when enabling compliance on a non-compliant volume"},
    )

    @validates_schema
    def validate_parameters(self, data, *rags, **kvargs):
        # TODO validate combinations
        if "ProvisionedThroughputInMibps" in data or "ThroughputMode" in data:
            raise ValidationError("The parameters ProvisionedThroughputInMibps, ThroughputMode are not supported")
        if data.get("Rpo") and not data.get("Nvl_ComplianceMode"):
            raise ValidationError("Compliance mode must be True when Rpo value is not null")


class UpdateFileSystemBodyRequestV20Schema(Schema):
    body = fields.Nested(UpdateFileSystemRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class UpdateFileSystemBodyResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class UpdateFileSystem(ServiceApiView):
    summary = "Update storage efs file system"
    description = "Update storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "UpdateFileSystemRequestV20Schema": UpdateFileSystemRequestV20Schema,
        "UpdateFileSystemBodyResponseV20Schema": UpdateFileSystemBodyResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateFileSystemBodyRequestV20Schema)
    parameters_schema = None #UpdateFileSystemRequestV20Schema
    responses = ServiceApiView.setResponses(
        {202: {"description": "success", "schema": UpdateFileSystemBodyResponseV20Schema}}
    )
    response_schema = UpdateFileSystemBodyResponseV20Schema

    def put(self, controller: 'ServiceController', data: Dict, oid, *args, **kwargs):
        type_plugin: 'ApiStorageEFS' = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        # resize
        if data.get(StPar.Nvl_FileSystem_Size) is not None:
            task = type_plugin.resize_filesystem(**data)
        # set online/offline
        elif data.get(StPar.Nvl_MountTarget_Status) is not None:
            task = type_plugin.update_efs_status(**data)
        # update snapshot policy
        elif data.get(StPar.Nvl_SnapshotPolicy) is not None:
            task = type_plugin.update_snapshot_policy(**data)
        # enable/disable compliance with ACN requirements i.e. create/remove volume snaplock
        elif data.get(StPar.Nvl_ComplianceMode) is not None:
            task = type_plugin.update_compliance(**data)
        else:
            task = None
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteFileSystemResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class DeleteFileSystem(ServiceApiView):
    summary = "Delete storage efs file system"
    description = "Delete storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
        "DeleteFileSystemResponseV20Schema": DeleteFileSystemResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "deleted instance uuid",
                "schema": DeleteFileSystemResponseV20Schema,
            }
        }
    )
    response_schema = DeleteFileSystemResponseV20Schema

    def delete(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        type_plugin.delete_share()
        return {
            "nvl_JobId": type_plugin.active_task,
            "nvl_TaskId": type_plugin.active_task,
        }, 202


class CreateMountTargetApiRequestV20Schema(Schema):
    Nvl_FileSystemId = fields.String(
        required=True,
        metadata={"example": "fs-47a2c22e", "description": "storage file system ID"},
    )
    SubnetId = fields.String(
        required=True,
        metadata={"example": "subnet-748c5d03", "description": "ID of the subnet to add the mount target in"},
    )
    Nvl_shareProto = fields.String(
        required=False,
        load_default="nfs",
        validate=OneOf(["nfs", "cifs"]),
        metadata={"example": "nfs", "description": "File system share protocol"},
    )
    Nvl_shareLabel = fields.String(
        required=False,
        load_default=None,
        metadata={"example": "project", "description": "Label to be used when you want to use a labelled share type"},
    )
    Nvl_shareVolume = fields.String(
        required=False,
        load_default=None,
        metadata={"example": "uenx79dsns", "description": "id of a physical existing volume to set for mount target"},
    )

    @validates_schema
    def validate_unsupported_parameters(self, data, *args, **kvargs):
        keys = data.keys()
        if "IpAddress" in keys or "SecurityGroups" in keys:
            raise ValidationError("The parameters IpAddress, SecurityGroups are not supported")


class CreateMountTargetApiBodyRequestV20Schema(Schema):
    body = fields.Nested(CreateMountTargetApiRequestV20Schema, context="body")


class CreateMountTargetApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class CreateMountTarget(ServiceApiView):
    summary = "Create storage efs file system mount target"
    description = "Create storage efs file system mount target"
    tags = ["storageservice"]
    definitions = {
        "CreateMountTargetApiResponseV20Schema": CreateMountTargetApiResponseV20Schema,
        "CreateMountTargetApiRequestV20Schema": CreateMountTargetApiRequestV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(CreateMountTargetApiBodyRequestV20Schema)
    parameters_schema = CreateMountTargetApiRequestV20Schema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": CreateMountTargetApiResponseV20Schema}}
    )
    response_schema = CreateMountTargetApiResponseV20Schema

    def post(self, controller: 'ServiceController', data, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(data.get(StPar.Nvl_FileSystemId), plugin_class=ApiStorageEFS)
        task = plugin_inst.create_mount_target(
            data.get("SubnetId"),
            data.get("Nvl_shareProto"),
            share_label=data.get("Nvl_shareLabel"),
            share_volume=data.get("Nvl_shareVolume"),
        )
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteMountTargetApiRequestV20Schema(Schema):
    MountTargetId = fields.String(
        required=False,
        context="query",
        metadata={"description": "physical resource file system ID"},
    )
    Nvl_FileSystemId = fields.String(
        required=True,
        allow_none=False,
        data_key="Nvl_FileSystemId",
        context="query",
        metadata={"description": "File system ID"},
    )

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if "MountTargetId" in keys:
            raise ValidationError("The MountTargetId parameter is not supported: use Nvl_FileSystemId")


class DeleteMountTargetApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class DeleteMountTarget(ServiceApiView):
    summary = "Delete storage efs file system mount target"
    description = "Delete storage efs file system mount target"
    tags = ["storageservice"]
    definitions = {
        "DeleteMountTargetApiRequestV20Schema": DeleteMountTargetApiRequestV20Schema,
        "DeleteMountTargetApiResponseV20Schema": DeleteMountTargetApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteMountTargetApiRequestV20Schema)
    parameters_schema = DeleteMountTargetApiRequestV20Schema
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "no response",
                "schema": DeleteMountTargetApiResponseV20Schema,
            }
        }
    )
    response_schema = DeleteMountTargetApiResponseV20Schema

    def delete(self, controller: 'ServiceController', data, *args, **kwargs):
        task = None
        instance_id = data.get(StPar.Nvl_FileSystemId)

        if instance_id is not None:
            plugin_inst = controller.get_service_type_plugin(instance_id, plugin_class=ApiStorageEFS)
            task = plugin_inst.delete_mount_target()

        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DescribeMountTargetNestedResponseV20Schema(Schema):
    FileSystemId = fields.String(
        required=True,
        metadata={"example": "fs-47a2c22e", "description": "EFS File System Id"},
    )

    IpAddress = fields.String(
        required=False,
        metadata={"example": "###.###.###.###", "description": "uuid della risorsa."},
    )

    LifeCycleState = fields.String(
        required=True,
        validate=OneOf(__SRV_AWS_STORAGE_STATUS__),
        metadata={
            "example": " | ".join(map(str, __SRV_AWS_STORAGE_STATUS__)),
            "description": "LifeCycle state of FileSystem"
        },
    )

    MountTargetState = fields.String(
        required=True,
        validate=OneOf(__SRV_STORAGE_STATUS__),
        metadata={
            "example": " | ".join(map(str, __SRV_STORAGE_STATUS__)),
            "description": "Mount target state"
        },
    )

    MountTargetId = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "example": "fsmt-55a4413c",
            "description": (
                "The ID of an AWS Key Management Service customer master key(CMK) that "
                "was used to protect the encrypted file system."
            )
        },
    )

    NetworkInterfaceId = fields.String(required=False, allow_none=True, metadata={"example": "eni-d95852af"})
    OwnerId = fields.String(required=False, metadata={"example": "251839141158", "description": "account id"})

    nvl_OwnerAlias = fields.String(
        required=False,
        data_key="nvl-OwnerAlias",
        metadata={"example": "test", "description": "account name"},
    )

    SubnetId = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "subnet-748c5d03", "description": "ID of the subnet to add the mount target in."},
    )

    nvl_ShareProto = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-ShareProto",
        metadata={"example": "nfs", "description": "file system share protocol"},
    )

    nvl_AvailabilityZone = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-AvailabilityZone",
        metadata={"example": "SiteTorino01"},
    )

    EncryptionState = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "encrypted", "description": "Volume encryption state"},
    )


class DescribeMountTargetsResponseV20Schema(Schema):
    MountTargets = fields.Nested(DescribeMountTargetNestedResponseV20Schema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, metadata={"description": "pagination token"})
    NextMarker = fields.String(required=True, allow_none=True, metadata={"description": "next pagination token"})
    nvl_fileSystemTargetTotal = fields.Integer(
        required=True,
        allow_none=True,
        data_key="nvl_fileSystemTargetTotal",
        metadata={"description": "total number of target filesystem item"},
    )


class DescribeMountTargetsRequestV20Schema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
    )
    FileSystemId = fields.String(required=False, context="query", metadata={"description": "file system ID"})
    MaxItems = fields.Integer(
        required=False,
        load_default=100,
        validation=Range(min=1),
        context="query",
        metadata={"description": "max number elements to return in the response"},
    )
    Marker = fields.String(
        required=False,
        load_default="0",
        context="query",
        metadata={"description": "pagination token"},
    )


class DescribeMountTargets(ServiceApiView):
    summary = "Describe storage efs file system mount target"
    description = "Describe storage efs file system mount target"
    tags = ["storageservice"]
    definitions = {
        "DescribeMountTargetsRequestV20Schema": DescribeMountTargetsRequestV20Schema,
        "DescribeMountTargetsResponseV20Schema": DescribeMountTargetsResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeMountTargetsRequestV20Schema)
    parameters_schema = DescribeMountTargetsRequestV20Schema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeMountTargetsResponseV20Schema}}
    )
    response_schema = DescribeMountTargetsResponseV20Schema

    def get(self, controller: 'ServiceController', data, *args, **kwargs):
        storage_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))
        data_search["service-version"] = "v2.0"

        # check Account
        # account_id_list, _ = self.get_account_list(controller, data, ApiStorageService)
        account_id_list = data.get("owner_id_N", [])

        if data.get("FileSystemId", None) is not None:
            storage_inst = controller.get_service_instance(data.get("FileSystemId", None))
            AssertUtil.assert_is_not_none(
                storage_inst.getPluginType(ApiStorageEFS.plugintype),
                "instance id %s is not of plugin type %s" % (storage_inst.oid, ApiStorageEFS.plugintype),
            )
            storage_id_list.append(storage_inst.oid)

        # get instances list
        res: List['ApiStorageEFS']
        res, total = controller.get_service_type_plugins(
            service_id_list=storage_id_list,
            account_id_list=account_id_list,
            plugintype=ApiStorageEFS.plugintype,
            **data_search,
        )
        mount_targets = [r.aws_info_target() for r in res if r.has_mount_target()]

        if total == 0:
            next_marker = "0"
        else:
            next_marker = str(data_search["page"] + 1)

        response = {
            "MountTargets": mount_targets,
            "Marker": data.get("Marker"),
            "NextMarker": next_marker,
            "nvl_fileSystemTargetTotal": total,
        }

        return response


class GrantItemResponseV20Schema(Schema):
    access_level = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "rw", "description": "The access level to the shared file system instance"},
    )
    access_superuser = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"example": "True", "description": "If superuser access to shared file system instance is allowed or not"},
    )
    protocols = fields.List(
        fields.String(example="nfs"),
        required=False,
        allow_none=True,
        metadata={"description": "Protocol to access shared file system instance"},
    )
    clients = fields.List(
        fields.String(example="10.138.187.188"),
        required=False,
        allow_none=True,
        metadata={"description": "The targets the access grants are applied to."},
    )
    id = fields.Integer(required=True, metadata={"example": 1, "description": "The access rule id."})


class ListFileSystemGrantResponseV20Schema(Schema):
    FileSystemId = fields.String(required=True, metadata={"description": "ID of the storage file system"})
    grants = fields.Nested(GrantItemResponseV20Schema, required=True, many=True, allow_none=True)


class ListFileSystemGrantRequestV20Schema(PaginatedRequestQuerySchema):
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class ListFileSystemGrant(ServiceApiView):
    summary = "List storage efs file system grant"
    description = "List storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "ListFileSystemGrantResponseV20Schema": ListFileSystemGrantResponseV20Schema,
        "ListFileSystemGrantRequestV20Schema": ListFileSystemGrantRequestV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(ListFileSystemGrantRequestV20Schema)
    parameters_schema = ListFileSystemGrantRequestV20Schema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListFileSystemGrantResponseV20Schema}}
    )
    response_schema = ListFileSystemGrantResponseV20Schema

    def get(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)

        share_grants = {}
        try:
            res = plugin_inst.get_mount_target_resource()
            share_grants = res.get("details", {}).get("grants", {})
        except Exception:
            pass

        res = {"FileSystemId": plugin_inst.instance.uuid, "grants": share_grants}

        return res, 200


class SnapshotPolicyResponseSchema(Schema):
    uuid = fields.String(required=True, metadata={"description": ""})
    name = fields.String(required=True, metadata={"description": ""})
    description = fields.String(required=True, allow_none=True, metadata={"description": ""})


class DescribeSnapshotPoliciesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    snapshotPoliciesSet = fields.Nested(SnapshotPolicyResponseSchema, required=True, many=True, allow_none=True)
    snapshotPoliciesTotal = fields.Integer(required=True)


class DescribeSnapshotPoliciesApiResponseSchema(Schema):
    DescribeSnapshotPoliciesResponse = fields.Nested(
        DescribeSnapshotPoliciesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeSnapshotPoliciesApiRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id"},
    )


class DescribeSnapshotPolicies(ServiceApiView):
    summary = "Describe snapshot policies"
    description = "Describe snapshot policies"
    tags = ["storageservice"]
    definitions = {
        "DescribeSnapshotPoliciesApiRequestSchema": DescribeSnapshotPoliciesApiRequestSchema,
        "DescribeSnapshotPoliciesApiResponseSchema": DescribeSnapshotPoliciesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeSnapshotPoliciesApiRequestSchema)
    parameters_schema = DescribeSnapshotPoliciesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeSnapshotPoliciesApiResponseSchema,
            }
        }
    )
    response_schema = DescribeSnapshotPoliciesApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)

        res, _ = account.get_definitions(plugintype="VirtualService", size=-1)

        snapshot_policies_set = []
        for r in res:
            r: ApiServiceDefinition
            if r.name.find("staas_snap_") != 0:
                continue
            snapshot_policies_set.append(
                {
                    "uuid": r.uuid,
                    "name": r.name,
                    "description": r.desc,
                }
            )

        resp = {
            "DescribeSnapshotPoliciesResponse": {
                "requestId": operation.id,
                "snapshotPoliciesSet": snapshot_policies_set,
                "snapshotPoliciesTotal": len(snapshot_policies_set),
            }
        }
        return resp


class ReplicaPolicyResponseSchema(Schema):
    uuid = fields.String(required=True, metadata={"description": ""})
    name = fields.String(required=True, metadata={"description": ""})
    description = fields.String(required=True, allow_none=True, metadata={"description": ""})


class DescribeReplicaPoliciesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    replicaPoliciesSet = fields.Nested(ReplicaPolicyResponseSchema, required=True, many=True, allow_none=True)
    replicaPoliciesTotal = fields.Integer(required=True)


class DescribeReplicaPoliciesApiResponseSchema(Schema):
    DescribeReplicaPoliciesResponse = fields.Nested(
        DescribeReplicaPoliciesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeReplicaPoliciesApiRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id"},
    )


class DescribeReplicaPolicies(ServiceApiView):
    summary = "Describe replica policies"
    description = "Describe replica policies"
    tags = ["storageservice"]
    definitions = {
        "DescribeReplicaPoliciesApiRequestSchema": DescribeReplicaPoliciesApiRequestSchema,
        "DescribeReplicaPoliciesApiResponseSchema": DescribeReplicaPoliciesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeReplicaPoliciesApiRequestSchema)
    parameters_schema = DescribeReplicaPoliciesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeReplicaPoliciesApiResponseSchema,
            }
        }
    )
    response_schema = DescribeReplicaPoliciesApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)

        res, _ = account.get_definitions(plugintype="VirtualService", size=-1)

        replica_policies_set = []
        for r in res:
            r: ApiServiceDefinition
            if r.name.find("staas_mirror_") != 0:
                continue
            replica_policies_set.append(
                {
                    "uuid": r.uuid,
                    "name": r.name,
                    "description": r.desc,
                }
            )

        resp = {
            "DescribeReplicaPoliciesResponse": {
                "requestId": operation.id,
                "replicaPoliciesSet": replica_policies_set,
                "replicaPoliciesTotal": len(replica_policies_set),
            }
        }
        return resp


class CreateFileSystemGrantParamsApiRequestV20Schema(Schema):
    access_level = fields.String(
        required=True,
        allow_none=False,
        validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_LEVEL__),
        metadata={"example": "rw", "description": "The access level, should be rw or ro"},
    )
    access_superuser = fields.Boolean(
        required=True,
        allow_none=False,
        metadata={"example": True, "description": "If True provide superuser access; False otherwise"},
    )
    client_type = fields.String(
        required=True,
        allow_none=False,
        validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_TYPE__),
        metadata={"example": "ID", "description": "The type of clients can access the share, should be ID, CIDR or USER (the last one for CIFS share only)"},
    )
    client_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=False,
        collection_format="multi",
        data_key="client.N",
        metadata={"description": "list of clients to grant access on the share"},
    )
    protocol = fields.String(
        required=True,
        allow_none=False,
        validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_PROTOCOL__),
        metadata={"description": "grant protocol", "example": "nfs3"},
    )

    @validates_schema
    def validate_params(self, data, *args, **kvargs):
        client_type = data.get("client_type", "").lower()
        clients: List[str] = data.get("client.N", [])
        if client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_ID_LOWER__:
            pass
        elif client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_CIDR_LOWER__ or client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__:
            for cidr in clients:
                try:
                    ip, prefix = cidr.split("/")
                    if client_type==__SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__ and prefix is None:
                        prefix = 32
                    else:
                        prefix = int(prefix)
                    if prefix < 0 or prefix > 32:
                        raise ValidationError(
                            f"Malformed {client_type.upper()} client. Network prefix must be >= 0 and <= 32"
                        )
                    IPv4Address(ensure_text(ip))
                except AddressValueError:
                    raise ValidationError(f"Malformed {client_type.upper()} client. Use ###.###.###.###/## syntax")
                except ValueError:
                    raise ValidationError(f"Malformed {client_type.upper()} client.")
        elif client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__:
            for user in clients:
                if re.match(__REGEX_SHARE_GRANT_ACCESS_TO_USER__, user) is None:
                    raise ValidationError(
                        f"Malformed {client_type.upper()} client. A valid value for a client of this type "
                        "is an alphanumeric string that can contain some special characters and is from 4 "
                        "to 32 characters long"
                    )
        #elif client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__:
        #    raise ValidationError(f"Target type {client_type.upper()} is not supported")
        elif client_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__:
            raise ValidationError(f"Target type {client_type.upper()} is not supported")
        else:
            raise ValidationError("Target type parameter is malformed")


class CreateFileSystemGrantApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class CreateFileSystemGrantApiRequestV20Schema(Schema):
    grant = fields.Nested(CreateFileSystemGrantParamsApiRequestV20Schema, context="body")


class CreateFileSystemGrantApiBodyRequestV20Schema(Schema):
    body = fields.Nested(CreateFileSystemGrantApiRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class CreateFileSystemGrant(ServiceApiView):
    summary = "Create storage efs file system grant"
    description = "Create storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "CreateFileSystemGrantApiRequestV20Schema": CreateFileSystemGrantApiRequestV20Schema,
        "CreateFileSystemGrantApiResponseV20Schema": CreateFileSystemGrantApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemGrantApiBodyRequestV20Schema)
    parameters_schema = CreateFileSystemGrantApiRequestV20Schema
    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": CreateFileSystemGrantApiResponseV20Schema,
            }
        }
    )
    response_schema = CreateFileSystemGrantApiResponseV20Schema

    def post(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        action_data = data.get("grant", {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_grant(action="add", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteFileSystemGrantParamsApiRequestV20Schema(Schema):
    access_ids = fields.List(
        fields.Integer(example=2),
        required=True,
        metadata={
           "description": "The IDs of the access policies to be deleted",
           "example": [2, 4, 5]
        },
    )


class DeleteFileSystemGrantApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class DeleteFileSystemGrantApiRequestV20Schema(Schema):
    grant = fields.Nested(DeleteFileSystemGrantParamsApiRequestV20Schema, context="body")


class DeleteFileSystemGrantBodyRequestV20Schema(Schema):
    body = fields.Nested(DeleteFileSystemGrantApiRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})



class DeleteFileSystemGrant(ServiceApiView):
    summary = "Delete storage efs file system grant"
    description = "Delete storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "DeleteFileSystemGrantApiRequestV20Schema": DeleteFileSystemGrantApiRequestV20Schema,
        "DeleteFileSystemGrantApiResponseV20Schema": DeleteFileSystemGrantApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteFileSystemGrantBodyRequestV20Schema)
    parameters_schema = DeleteFileSystemGrantApiRequestV20Schema
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": DeleteFileSystemGrantApiResponseV20Schema,
            }
        }
    )
    response_schema = DeleteFileSystemGrantApiResponseV20Schema

    def delete(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        action_data = data.get("grant", {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_grant(action="del", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class CreateFileSystemReplicaApiRequestV20Schema(Schema):
    SiteName = fields.String(required=True, validate=OneOf(__SITE_NAMES__), metadata={"example": "SiteTorino05"})

    Rpo = fields.String(
        required=True,
        validate=OneOf(__SRV_STORAGE_REPLICA_RPO_VALUES__),
        metadata={
            "description": "replica rpo",
            "example": " | ".join(__SRV_STORAGE_REPLICA_RPO_VALUES__)
        },
    )


class CreateFileSystemReplicaApiBodyRequestV20Schema(Schema):
    body = fields.Nested(CreateFileSystemReplicaApiRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class CreateFileSystemReplica(ServiceApiView):
    summary = "Create storage efs file system replica"
    description = "Create storage efs file system replica"
    tags = ["storageservice"]
    definitions = {
        "CreateFileSystemResultApiResponseV20Schema": CreateFileSystemResultApiResponseV20Schema,
        "CreateFileSystemReplicaApiRequestV20Schema": CreateFileSystemReplicaApiRequestV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemReplicaApiBodyRequestV20Schema)
    parameters_schema = CreateFileSystemReplicaApiRequestV20Schema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CreateFileSystemResultApiResponseV20Schema}}
    )
    response_schema = CreateFileSystemResultApiResponseV20Schema

    def post(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        """
        create filesystem replica
        """
        source_efs = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        instance_version = source_efs.instance.version
        version = source_efs.get_config("version")
        account_id = source_efs.account.oid
        dest_site = data.get("SiteName")

        source_efs_data = source_efs.get_config("share_data")
        source_efs_name = source_efs_data.pop(StPar.CreationToken)

        orchestrator_type =  source_efs.get_config("orchestrator_type")
        if instance_version!="2.0" or orchestrator_type!="ontap":
            raise Exception(f"Replica unsupported through this endpoint for efs instance version {instance_version} of type {orchestrator_type}")

        # check account
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiStorageService.plugintype
        )

        # get definition
        service_definition_id = source_efs_data.get("Nvl_FileSystem_Type")
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiStorageEFS.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)

        dest_efs_data = source_efs_data
        dest_efs_data.pop("client_N",None)
        dest_efs_data["SiteName"] = dest_site
        dest_efs_data["SourceId"] = source_efs.instance.uuid
        dest_efs_data["ComplianceMode"] = False # TODO serve o no?
        dest_efs_data["Rpo"] = data.get("Rpo")

        # create service
        site_suffix = __MAP_SITE_NAME_SHORT_SUFFIX__.get(dest_site)
        name = f"dr-{source_efs_name}-{site_suffix}"
        desc = "efs replica " + name + " owned by " + account.name
        dest_efs_data["CreationToken"] = name
        cfg = {
            "share_data": dest_efs_data,
            "computeZone": parent_plugin.resource_uuid,
            "StorageService": parent_plugin.resource_uuid,
            "version": version,
        }
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=cfg,
            instance_version=instance_version,
        )
        plugin.account = account
        response = {
            "FileSystem": plugin.aws_info()
        }
        return response, 202


class UnlinkFileSystemReplicaApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class UnlinkFileSystemReplicaParamsApiRequestV20Schema(Schema):
    new_name = fields.String(
        required=True,
        allow_none=False,
        context="query",
        metadata={"example": "svmp5-asl-cdt-mongo-gpi", "description": "the name to assign to the volume after the peer relationship has broken"},
    )

    @validates_schema
    def validate_params(self, data, *args, **kvargs):
        name = data.get("new_name")
        name = name.lower()
        if name.startswith(StPar.ReplicaNamePrefix):
            raise ValidationError(f"Efs instance name cannot start with {StPar.ReplicaNamePrefix} prefix")


class UnlinkFileSystemReplicaApiRequestV20Schema(Schema):
    replica = fields.Nested(UnlinkFileSystemReplicaParamsApiRequestV20Schema, context="body")


class UnlinkFileSystemReplicaApiBodyRequestV20Schema(Schema):
    body = fields.Nested(UnlinkFileSystemReplicaApiRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class UnlinkFileSystemReplica(ServiceApiView):
    summary = "Delete the relationship between a replica and its source storage efs filesystem"
    description = "Delete the relationship between a replica and its source storage efs filesystem"
    tags = ["storageservice"]
    definitions = {
        "UnlinkFileSystemReplicaApiRequestV20Schema": UnlinkFileSystemReplicaApiRequestV20Schema,
        "UnlinkFileSystemReplicaApiResponseV20Schema": UnlinkFileSystemReplicaApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(UnlinkFileSystemReplicaApiBodyRequestV20Schema)
    parameters_schema = UnlinkFileSystemReplicaApiRequestV20Schema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": UnlinkFileSystemReplicaApiResponseV20Schema}}
    )
    response_schema = UnlinkFileSystemReplicaApiResponseV20Schema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        """
        delete the relationship between a replica and its source storage efs filesystem
        """
        action_data = data.get("replica", {})
        new_name = action_data.get("new_name")
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        _, tot = controller.get_paginated_service_instances(
            name=new_name, account_id=plugin_inst.instance.account_id, filter_expired=False, authorize=False
        )
        if tot > 0:
            raise ApiManagerError("Name %s already used in account %s" % (new_name, plugin_inst.instance.account_id))
        task = plugin_inst.manage_replica(action="unlink", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class SuspendFileSystemReplicaApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class SuspendFileSystemReplica(ServiceApiView):
    summary = "Suspend/pause the relationship between a replica and its source storage efs filesystem"
    description = "Suspend/pause the relationship between a replica and its source storage efs filesystem"
    tags = ["storageservice"]
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
        "SuspendFileSystemReplicaApiResponseV20Schema": SuspendFileSystemReplicaApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = None # GetApiObjectRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": SuspendFileSystemReplicaApiResponseV20Schema}}
    )
    response_schema = SuspendFileSystemReplicaApiResponseV20Schema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        """
        suspend/pause the relationship between a replica and its source storage efs filesystem
        """
        # action_data = data.get("replica", {})
        action_data = {}
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_replica(action="suspend", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class ResumeFileSystemReplicaApiResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass

class ResumeFileSystemReplica(ServiceApiView):
    summary = "Resume the relationship between a replica and its source storage efs filesystem"
    description = "Resume the relationship between a replica and its source storage efs filesystem"
    tags = ["storageservice"]
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
        "ResumeFileSystemReplicaApiResponseV20Schema": ResumeFileSystemReplicaApiResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = None # GetApiObjectRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ResumeFileSystemReplicaApiResponseV20Schema}}
    )
    response_schema = ResumeFileSystemReplicaApiResponseV20Schema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        """
        resume the relationship between a replica and its source storage efs filesystem
        """
        #action_data = data.get("replica", {})
        action_data = {}
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_replica(action="resume",**action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class UpdateFileSystemReplicaParamsApiRequestV20Schema(Schema):
    rpo = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(__SRV_STORAGE_REPLICA_RPO_VALUES__),
        metadata={
            "description": "replica rpo",
            "example": " | ".join(__SRV_STORAGE_REPLICA_RPO_VALUES__)
        },
    )


class UpdateFileSystemReplicaRequestV20Schema(Schema):
    replica = fields.Nested(UpdateFileSystemReplicaParamsApiRequestV20Schema, context="body")


class UpdateFileSystemReplicaBodyRequestV20Schema(Schema):
    body = fields.Nested(UpdateFileSystemReplicaRequestV20Schema, context="body")
    oid = fields.String(required=True, context="path", metadata={"description": "id, uuid or name"})


class UpdateFileSystemReplicaBodyResponseV20Schema(CrudFileSystemApiResponseV20Schema):
    pass


class UpdateFileSystemReplica(ServiceApiView):
    summary = "Update storage efs file system replica"
    description = "Update storage efs file system replica"
    tags = ["storageservice"]
    definitions = {
        "UpdateFileSystemReplicaRequestV20Schema": UpdateFileSystemReplicaRequestV20Schema,
        "UpdateFileSystemReplicaBodyResponseV20Schema": UpdateFileSystemReplicaBodyResponseV20Schema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateFileSystemReplicaBodyRequestV20Schema)
    parameters_schema = None
    responses = ServiceApiView.setResponses(
        {202: {"description": "success", "schema": UpdateFileSystemReplicaBodyResponseV20Schema}}
    )
    response_schema = UpdateFileSystemReplicaBodyResponseV20Schema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        action_data = data.get("replica", {})
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        # update replica policy
        if action_data.get(StPar.ReplicaRpo) is not None:
            task = type_plugin.manage_replica(action="update", **action_data)
        else:
            task = None
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class MountFileSystemApiResponseSchema(CrudFileSystemApiResponseV20Schema):
    pass


class MountFileSystem(ServiceApiView):
    summary = "Make share mount-able if it isn't"
    description = "Set main mount target and export policy, if necessary"
    tags = ["storageservice"]
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
        "MountFileSystemApiResponseSchema": MountFileSystemApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = None # GetApiObjectRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": MountFileSystemApiResponseSchema}}
    )
    response_schema = MountFileSystemApiResponseSchema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        """
        make replica mount-able
        """
        action_data = {}
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage(action="mount", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class StorageEfsServiceV2API(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, version=None, **kwargs):
        base = module.base_path + "/storageservices/efs"
        version = "v2.0"
        rules = [
            (
                f"{base}/file-systems",
                "POST",
                CreateFileSystem,
                {"version": version},
            ),
            (
                f"{base}/file-systems",
                "GET",
                DescribeFileSystems2,
                {},
            ),
            (
                f"{base}/file-systems/<oid>",
                "PUT",
                UpdateFileSystem,
                {},
            ),
            (
                f"{base}/file-systems/<oid>",
                "DELETE",
                DeleteFileSystem,
                {},
            ),
            (
                f"{base}/file-systems/<oid>/replica",
                "POST",
                CreateFileSystemReplica,
                {}
            ),
            (
                f"{base}/file-systems/<oid>/unlinkreplica",
                "PUT",
                UnlinkFileSystemReplica,
                {}
            ),
            (
                f"{base}/file-systems/<oid>/suspendreplica",
                "PUT",
                SuspendFileSystemReplica,
                {}
            ),
            (
                f"{base}/file-systems/<oid>/resumereplica",
                "PUT",
                ResumeFileSystemReplica,
                {}
            ),
            (
                f"{base}/file-systems/<oid>/updatereplica",
                "PUT",
                UpdateFileSystemReplica,
                {}
            ),
            (
                f"{base}/file-systems/<oid>/mount",
                "PUT",
                MountFileSystem,
                {}
            ),
            (
                f"{base}/file-systems/describesnapshotpolicies",
                "GET",
                DescribeSnapshotPolicies,
                {}
            ),
            (
                f"{base}/file-systems/describereplicapolicies",
                "GET",
                DescribeReplicaPolicies,
                {}
            ),
            (
                f"{base}/mount-targets/<oid>/grants",
                "POST",
                CreateFileSystemGrant,
                {},
            ),
            (
                f"{base}/mount-targets/<oid>/grants",
                "DELETE",
                DeleteFileSystemGrant,
                {},
            ),
            (
                f"{base}/mount-targets/<oid>/grants",
                "GET",
                ListFileSystemGrant,
                {},
            ),
        ]
        kwargs["version"] = version
        ApiView.register_api(module, rules, **kwargs)
