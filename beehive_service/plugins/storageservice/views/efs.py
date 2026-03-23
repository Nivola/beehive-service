# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import re
from ipaddress import IPv4Address, AddressValueError
from typing import TYPE_CHECKING, List

from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from beecell.util import ensure_text
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    GetApiObjectRequestSchema,
    DeleteApiObjectRequestSchema,
    PaginatedRequestQuerySchema,
    ApiView,
    ApiManagerWarning,
)
from beehive.common.assert_util import AssertUtil
from beehive_service.views import ServiceApiView
from beehive_service.plugins.storageservice.controller import (
    StorageParamsNames as StPar,
    ApiStorageService,
    ApiStorageEFS,
)
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
)
if TYPE_CHECKING:
    from beehive_service.controller import ServiceController

class CreateFileSystemApiRequestSchema(Schema):
    """create empty filesystem object v1 if ontap
    else create on openstack"""
    owner_id = fields.String(required=True, metadata={"description": "account id"})
    Nvl_FileSystem_Size = fields.Integer(
        required=True,
        metadata={"example": 10, "description": "size in Giga byte of storage file system to create"},
    )
    Nvl_FileSystem_Type = fields.String(
        required=False,
        load_default=None,
        metadata={"description": "service definition for storage file system"},
    )
    CreationToken = fields.String(
        required=True,
        validate=Length(min=1, max=64),
        metadata={"example": "myFileSystem1", "description": "a string used to identify the file system"},
    )
    PerformanceMode = fields.String(
        required=False,
        validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__),
        metadata={"example": "shared", "description": "The performance mode of the file system. Can be shared or private"},
    )

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if (
            "KmsKeyId" in keys
            or "Encrypted" in keys
            or "ProvisionedThroughputInMibps" in keys
            or "ThroughputMode" in keys
        ):
            raise ValidationError(
                "The Encrypted, KmsKeyId, ProvisionedThroughputInMibps and "
                "ThroughputMode parameter are not supported"
            )


class CreateFileSystemApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateFileSystemApiRequestSchema, context="body")


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
        metadata={"description": "File System dimension"},
    )
    Name = fields.String(required=False, validate=Length(min=0, max=256), metadata={"description": "resource tag name"})
    nvl_shareProto = fields.String(
        required=False,
        allow_none=False,
        metadata={"example": "NFS", "description": "file system share protocol"},
    )


class StateReasonResponseSchema(Schema):
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


class MountTargetInfoSchema(Schema):
    id = fields.String(required=False)
    protocol = fields.String(required=False)
    mounts = fields.List(fields.String(), required=True)


class FileSystemReplicaInfoSchema(Schema):
    replica_id = fields.String(required=False)
    replica_name = fields.String(required=False)
    rpo = fields.String(required=False)
    site = fields.String(required=False)
    msg = fields.String(required=False)
    healthy = fields.Boolean(required=False)
    state = fields.String(required=False)
    #policy_name = fields.String(required=False)


class FileSystemSourceInfoSchema(Schema):
    source_id = fields.String(required=False)
    source_name = fields.String(required=False)
    site = fields.String(required=False)
    msg = fields.String(required=False)
    healthy = fields.Boolean(required=False)
    state = fields.String(required=False)
    #policy_name = fields.String(required=False)


class FileSystemDescriptionResponseSchema(Schema):
    CreationTime = fields.DateTime(
        required=True,
        metadata={"example": "1970-01-01T00:00:00Z", "description": "creation time file system storage"},
    )
    CreationToken = fields.String(
        required=True,
        validate=Length(min=1, max=64),
        metadata={"description": "file system storage name"},
    )
    Encrypted = fields.Boolean(
        required=False,
        load_default=False,
        metadata={"description": "boolean value to indicate whether the storage file system is encrypted or not"},
    )
    EncryptionState = fields.String(
        required=False,
        metadata={"description": "current encryption state", "example": "encrypted, encrypting"},
    )
    SnapshotPolicy = fields.String(
        required=False,
        metadata={"description": "snapshot policy name", "example": "staas_snap_default"},
    )
    ReplicaPolicy = fields.String(
        required=False,
        metadata={"description": "replica policy name", "example": "staas_mirror_1h"},
    )
    FileSystemId = fields.String(required=True, metadata={"description": "ID of the storage file system"})
    FileSystemState = fields.String(
        required=False,
        metadata={
            "example": " | ".join(map(str, __SRV_STORAGE_STATUS__)),
            "description": "FileSystem state"
        },
    )
    InstanceVersion = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "Storage service instance version"},
    )
    IpAddress = fields.String(
        required=False,
        metadata={"example": "###.###.###.###", "description": "SVM leaf ip address"},
    )
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
    MountTargets = fields.Nested(MountTargetInfoSchema, required=True, many=True)
    Name = fields.String(required=False, validate=Length(min=0, max=256), metadata={"description": "resource tag name"})
    NumberOfMountTargets = fields.Integer(
        required=False,
        dump_default=0,
        load_default=0,
        validate=Range(min=0),
        metadata={"description": "current number of mount targets that the file system has"},
    )
    nvl_AvailabilityZone = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-AvailabilityZone",
        metadata={"example": "SiteTorino01"},
    )
    nvl_Capabilities = fields.List(
        fields.String,
        required=False,
        data_key="nvl-Capabilities",
        metadata={"example": ["grant"], "description": "list of file system available capabilities"},
    )
    nvl_complianceMode = fields.Boolean(
        required=False,
        allow_none=True,
        data_key="nvl-complianceMode",
        metadata={"description": "ACN compliant or not; if compliant, ontap creates snaplock volume too"},
    )
    nvl_complianceRPO = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-complianceRPO",
        metadata={"description": "share RPO, used only when compliance is enabled"},
    )
    nvl_OwnerAlias = fields.String(
        required=True,
        data_key="nvl-OwnerAlias",
        metadata={"description": "account name that created the file system"},
    )
    nvl_shareProto = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "nfs", "description": "share protocol"},
    )
    nvl_stateReason = fields.Nested(
        StateReasonResponseSchema,
        many=False,
        required=False,
        allow_none=True,
        data_key="nvl-stateReason",
    )
    OwnerId = fields.String(required=True, metadata={"description": "account id that created the file system"})
    PerformanceMode = fields.String(
        required=False,
        load_default=__SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__,
        allow_none=True,
        validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__),
        metadata={"description": ""},
    )
    ProvisionedThroughputInMibps = fields.Integer(
        required=False,
        metadata={"description": "The throughput, measured " "in MiB/s, that you want to provision for a file system."},
    )
    Replicas = fields.Nested(FileSystemReplicaInfoSchema, required=False, many=True)
    Size = fields.Float(required=False, allow_none=True, metadata={"description": "File system dimension in gigabytes"})
    SizeInBytes = fields.Nested(
        FileSystemSize,
        required=True,
        many=False,
        allow_none=True,
        metadata={"description": "File System dimension"},
    )
    Source = fields.Nested(FileSystemSourceInfoSchema, required=False, many=False)


class CreateFileSystem(ServiceApiView):
    summary = "Create storage efs file system"
    description = "Create storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "FileSystemDescriptionResponseSchema": FileSystemDescriptionResponseSchema,
        "CreateFileSystemApiRequestSchema": CreateFileSystemApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemApiBodyRequestSchema)
    parameters_schema = CreateFileSystemApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": FileSystemDescriptionResponseSchema}}
    )
    response_schema = FileSystemDescriptionResponseSchema

    def post(self, controller: 'ServiceController', data, *args, **kwargs):
        inner_data = data
        service_definition_id = inner_data.get("Nvl_FileSystem_Type")
        account_id = inner_data.get("owner_id")
        name = inner_data.get("CreationToken")

        # check account
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiStorageService.plugintype
        )

        # get vpc definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiStorageEFS.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)

        # create service
        data["computeZone"] = parent_plugin.resource_uuid
        desc = "efs " + name + " owned by " + account.name
        cfg = {
            "share_data": data,
            "computeZone": parent_plugin.resource_uuid,
            "StorageService": parent_plugin.resource_uuid,
        }
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=cfg,
        )
        plugin.account = account
        res = plugin.aws_info()

        return res, 202


class DescribeFileSystemsRequestSchema(Schema):
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
    InstanceVersion = fields.String(
        context="query",
        required=False,
        allow_none=True,
        validate=OneOf(["1.0", "2.0"]),
        metadata={"description": "Storage service instance version"},
    )


class DescribeFileSystemResponseSchema(FileSystemDescriptionResponseSchema):
    nvl_stateReason = fields.Nested(
        StateReasonResponseSchema,
        many=False,
        required=False,
        allow_none=True,
        data_key="nvl-stateReason",
    )


class DescribeFileSystemsResponseSchema(Schema):
    FileSystems = fields.Nested(DescribeFileSystemResponseSchema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, metadata={"description": "pagination token"})
    NextMarker = fields.String(required=True, allow_none=True, metadata={"description": "next pagination token"})
    nvl_fileSystemTotal = fields.Integer(
        required=True,
        allow_none=True,
        data_key="nvl-fileSystemTotal",
        metadata={"description": "total number of filesystem items"},
    )


class DescribeFileSystems(ServiceApiView):
    summary = "Describe storage efs file system"
    description = "Describe storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "DescribeFileSystemsResponseSchema": DescribeFileSystemsResponseSchema,
        "DescribeFileSystemsRequestSchema": DescribeFileSystemsRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeFileSystemsRequestSchema)
    parameters_schema = DescribeFileSystemsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeFileSystemsResponseSchema}}
    )
    response_schema = DescribeFileSystemsResponseSchema

    def get(self, controller: 'ServiceController', data, *args, **kwargs):
        size = data.get("MaxItems")
        if size is not None and (size == -1 or abs(size) > __SRV_STORAGE_QUERY_MAX_SIZE__):
            raise ApiManagerWarning("Too large size value. You should use pagination.")

        storage_id_list = []
        data_search = {}
        data_search["size"] = size
        data_search["page"] = int(data.get("Marker"))

        instance_version = data.get("InstanceVersion")
        if instance_version:
            data_search["instance_version"] = instance_version

        # check accounts
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
        res: List['ApiStorageEFS']
        res, total = controller.get_service_type_plugins(
            service_id_list=storage_id_list,
            account_id_list=account_id_list,
            plugintype=ApiStorageEFS.plugintype,
            **data_search,
        )

        storage_instances = [r.aws_info() for r in res]
        if len(res)==1:
            replicas = res[0].get_replicas()
            source = res[0].get_source_efs()
            if replicas:
                storage_instances[0]["Replicas"] = replicas
            if source:
                storage_instances[0]["Source"] = source

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


class UpdateFileSystemResponseSchema(Schema):
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
        metadata={"description": "The throughput, measured in " "MiB/s, that you want to provision for a file system."},
    )
    ThroughputMode = fields.String(
        required=False,
        validate=OneOf(["bursting", "provisioned"]),
        metadata={"description": "The throughput mode for a file system. There are two throughput modes "
        "to choose from for your file system: bursting and provisioned."},
    )


class UpdateFileSystemRequestSchema(Schema):
    oid = fields.String(required=False, metadata={"description": "id, uuid or name"})
    Nvl_FileSystem_Size = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 10, "description": "Size of the file system size in Giga "},
    )
    # ProvisionedThroughputInMibps
    # ThroughputMode

    @validates_schema
    def validate_parameters(self, data, *rags, **kvargs):
        if "ProvisionedThroughputInMibps" in data or "ThroughputMode" in data:
            raise ValidationError("The parameters ProvisionedThroughputInMibps, ThroughputMode are not supported")
        if StPar.Nvl_FileSystem_Size not in data:
            raise ValidationError("The parameters %s is required" % StPar.Nvl_FileSystem_Size)


class UpdateFileSystemBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateFileSystemRequestSchema, context="body")


class UpdateFileSystemBodyResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        allow_none=True,
        metadata={"example": "6d960236-d280-46d2-817d-f3ce8f0aeff7", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        allow_none=True,
        metadata={"example": "6d960236-d280-46d2-817d-f3ce8f0aeff7", "description": "ID of the running task"},
    )


class UpdateFileSystem(ServiceApiView):
    summary = "Update storage efs file system"
    description = "Update storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "UpdateFileSystemRequestSchema": UpdateFileSystemRequestSchema,
        "UpdateFileSystemBodyResponseSchema": UpdateFileSystemBodyResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateFileSystemBodyRequestSchema)
    parameters_schema = UpdateFileSystemRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "success", "schema": UpdateFileSystemBodyResponseSchema}}
    )
    response_schema = UpdateFileSystemBodyResponseSchema

    def put(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        data.pop("oid", None)
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = type_plugin.resize_filesystem(**data)

        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteFileSystemResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class DeleteFileSystem(ServiceApiView):
    summary = "Delete storage efs file system"
    description = "Delete storage efs file system"
    tags = ["storageservice"]
    definitions = {
        "DeleteApiObjectRequestSchema": DeleteApiObjectRequestSchema,
        "DeleteFileSystemResponseSchema": DeleteFileSystemResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "deleted instance uuid",
                "schema": DeleteFileSystemResponseSchema,
            }
        }
    )
    response_schema = DeleteFileSystemResponseSchema

    def delete(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        type_plugin.delete_share()
        return {
            "nvl_JobId": type_plugin.active_task,
            "nvl_TaskId": type_plugin.active_task,
        }, 202


class CreateMountTargetApiRequestSchema(Schema):
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
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if "IpAddress" in keys or "SecurityGroups" in keys:
            raise ValidationError("The parameters IpAddress, SecurityGroups are not supported")


class CreateMountTargetApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateMountTargetApiRequestSchema, context="body")


class CreateMountTargetApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class CreateMountTarget(ServiceApiView):
    summary = "Create storage efs file system mount target"
    description = "Create storage efs file system mount target"
    tags = ["storageservice"]
    definitions = {
        "CreateMountTargetApiResponseSchema": CreateMountTargetApiResponseSchema,
        "CreateMountTargetApiRequestSchema": CreateMountTargetApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateMountTargetApiBodyRequestSchema)
    parameters_schema = CreateMountTargetApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": CreateMountTargetApiResponseSchema}}
    )
    response_schema = CreateMountTargetApiResponseSchema

    def post(self, controller: 'ServiceController', data, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(data.get(StPar.Nvl_FileSystemId), plugin_class=ApiStorageEFS)
        task = plugin_inst.create_mount_target(
            data.get("SubnetId"),
            data.get("Nvl_shareProto"),
            share_label=data.get("Nvl_shareLabel"),
            share_volume=data.get("Nvl_shareVolume"),
        )
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteMountTargetApiRequestSchema(Schema):
    MountTargetId = fields.String(required=False, context="query", metadata={"description": "resource file system ID"})
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


class DeleteMountTargetApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class DeleteMountTarget(ServiceApiView):
    summary = "Delete storage efs file system mount target"
    description = "Delete storage efs file system mount target"
    tags = ["storageservice"]
    definitions = {
        "DeleteMountTargetApiRequestSchema": DeleteMountTargetApiRequestSchema,
        "DeleteMountTargetApiResponseSchema": DeleteMountTargetApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteMountTargetApiRequestSchema)
    parameters_schema = DeleteMountTargetApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "no response",
                "schema": DeleteMountTargetApiResponseSchema,
            }
        }
    )
    response_schema = DeleteMountTargetApiResponseSchema

    def delete(self, controller: 'ServiceController', data, *args, **kwargs):
        task = None
        instance_id = data.get(StPar.Nvl_FileSystemId)

        if instance_id is not None:
            plugin_inst = controller.get_service_type_plugin(instance_id, plugin_class=ApiStorageEFS)
            task = plugin_inst.delete_mount_target()

        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DescribeMountTargetNestedResponseSchema(Schema):
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
    MountTargetId = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "fsmt-55a4413c", "description": ""},
    )
    MountTargetState = fields.String(required=False, allow_none=True)
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


class DescribeMountTargetsResponseSchema(Schema):
    MountTargets = fields.Nested(DescribeMountTargetNestedResponseSchema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, metadata={"description": "pagination token"})
    NextMarker = fields.String(required=True, allow_none=True, metadata={"description": "next pagination token"})
    nvl_fileSystemTargetTotal = fields.Integer(
        required=True,
        allow_none=True,
        data_key="nvl_fileSystemTargetTotal",
        metadata={"description": "total number of target filesystem item"},
    )


class DescribeMountTargetsRequestSchema(Schema):
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
        "DescribeMountTargetsRequestSchema": DescribeMountTargetsRequestSchema,
        "DescribeMountTargetsResponseSchema": DescribeMountTargetsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeMountTargetsRequestSchema)
    parameters_schema = DescribeMountTargetsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeMountTargetsResponseSchema}}
    )
    response_schema = DescribeMountTargetsResponseSchema

    def get(self, controller: 'ServiceController', data, *args, **kwargs):
        storage_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

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


class GrantItemResponseSchema(Schema):
    access_level = fields.String(
        required=True,
        metadata={"example": "rw", "description": "The access level to the share file system instance. Is hold be rw or ro"},
    )
    access_type = fields.String(
        required=True,
        metadata={"example": "ip", "description": "The access rule type. Valid value are: ip, cert, user"},
    )
    access_to = fields.String(
        required=True,
        metadata={"example": "###.###.###.###", "description": "The value that defines the access."},
    )
    state = fields.String(
        required=True,
        metadata={"example": "active", "description": "The state of access rule of a given share file system instance"},
    )
    id = fields.String(
        required=True,
        metadata={"example": "52bea969-78a2-4f7e-ae84-fb4599dc06ca", "description": "The access rule ID."},
    )
    access_key = fields.String(required=False, allow_none=True)
    created_at = fields.String(required=False, allow_none=True)
    updated_at = fields.String(required=False, allow_none=True)


class ListFileSystemGrantResponseSchema(Schema):
    FileSystemId = fields.String(required=True, metadata={"description": "ID of the storage file system"})
    grants = fields.Nested(GrantItemResponseSchema, required=True, many=True, allow_none=True)


class ListFileSystemGrantRequestSchema(GetApiObjectRequestSchema, PaginatedRequestQuerySchema):
    pass


class ListFileSystemGrant(ServiceApiView):
    summary = "List storage efs file system grant"
    description = "List storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "ListFileSystemGrantResponseSchema": ListFileSystemGrantResponseSchema,
        "ListFileSystemGrantRequestSchema": ListFileSystemGrantRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListFileSystemGrantRequestSchema)
    parameters_schema = ListFileSystemGrantRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListFileSystemGrantResponseSchema}}
    )
    response_schema = ListFileSystemGrantResponseSchema

    def get(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        grants = []

        try:
            res = plugin_inst.get_mount_target_resource()
            grants = res.get("details", {}).get("grants", {})

        except Exception:
            pass

        res = {"FileSystemId": plugin_inst.instance.uuid, "grants": grants}

        return res, 200


class CreateFileSystemGrantParamsApiRequestSchema(Schema):
    access_level = fields.String(
        required=True,
        validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_LEVEL__),
        metadata={"example": "rw", "description": "The access level to the share should be rw or ro"},
    )
    access_type = fields.String(
        required=True,
        validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_TYPE__),
        metadata={"example": "ip", "description": "The access rule type"},
    )
    access_to = fields.String(
        required=True,
        metadata={"example": "###.###.###.###/##", "description": "The value that defines the access. - ip. A valid format is XX.XX.XX.XX or "
        "XX.XX.XX.XX/XX. For example 0.0.0.0/0. - cert. A valid value is any string up to 64 "
        "characters long in the common name(CN) of the certificate. - user. A valid value is an "
        "alphanumeric string that can contain some special characters and is from 4 to 32 "
        "characters long."},
    )

    @validates_schema
    def validate_grant_access_parameters(self, data, *rags, **kvargs):
        msg1 = "parameter is malformed. Range network prefix must be >= 0 and < 33"
        access_type = data.get("access_type", "").lower()
        access_to: str = data.get("access_to", "")
        if access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__:
            try:
                ip, prefix = access_to.split("/")
                prefix = int(prefix)
                if prefix < 0 or prefix > 32:
                    raise ValidationError(msg1)
                IPv4Address(ensure_text(ip))
            except AddressValueError:
                raise ValidationError("parameter access_to is malformed. Use xxx.xxx.xxx.xxx/xx syntax")
            except ValueError:
                raise ValidationError(msg1)
        elif access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__:
            if re.match(__REGEX_SHARE_GRANT_ACCESS_TO_USER__, access_to) is None:
                raise ValidationError(
                    "parameter access_to is malformed. A valid value is an alphanumeric string that "
                    "can contain some special characters and is from 4 to 32 characters long"
                )
        elif access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__:
            raise ValidationError('parameter access_to "cert|CERT" value is not supported')
        else:
            raise ValidationError("parameter access_to is malformed")


class CreateFileSystemGrantApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class CreateFileSystemGrantApiRequestSchema(Schema):
    grant = fields.Nested(CreateFileSystemGrantParamsApiRequestSchema, context="body")


class CreateFileSystemGrantApiBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CreateFileSystemGrantApiRequestSchema, context="body")


class CreateFileSystemGrant(ServiceApiView):
    summary = "Create storage efs file system grant"
    description = "Create storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "CreateFileSystemGrantApiRequestSchema": CreateFileSystemGrantApiRequestSchema,
        "CreateFileSystemGrantApiResponseSchema": CreateFileSystemGrantApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemGrantApiBodyRequestSchema)
    parameters_schema = CreateFileSystemGrantApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": CreateFileSystemGrantApiResponseSchema,
            }
        }
    )
    response_schema = CreateFileSystemGrantApiResponseSchema

    def post(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        action_data = data.get("grant", {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_grant(action="add", **action_data)

        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class DeleteFileSystemGrantParamRequestSchema(Schema):
    access_ids = fields.List(
        fields.Integer(example=2),
        required=True,
        metadata={
            "description": "The IDs of the access policies to be deleted",
            "example": [2,4,5]
        },
    )


class DeleteFileSystemGrantRequestSchema(Schema):
    grant = fields.Nested(DeleteFileSystemGrantParamRequestSchema, required=True, many=False, allow_none=False)


class DeleteFileSystemGrantBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteFileSystemGrantRequestSchema, context="body")


class DeleteFileSystemGrantResponseSchema(Schema):
    nvl_JobId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running job"},
    )
    nvl_TaskId = fields.UUID(
        required=True,
        metadata={"example": "db078b20-19c6-4f0e-909c-94745de667d4", "description": "ID of the running task"},
    )


class DeleteFileSystemGrant(ServiceApiView):
    summary = "Delete storage efs file system grant"
    description = "Delete storage efs file system grant"
    tags = ["storageservice"]
    definitions = {
        "DeleteFileSystemGrantRequestSchema": DeleteFileSystemGrantRequestSchema,
        "DeleteFileSystemGrantResponseSchema": DeleteFileSystemGrantResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteFileSystemGrantBodyRequestSchema)
    parameters_schema = DeleteFileSystemGrantRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "success", "schema": DeleteFileSystemGrantResponseSchema}}
    )
    response_schema = DeleteFileSystemGrantResponseSchema

    def delete(self, controller: 'ServiceController', data, oid, *args, **kwargs):
        action_data = data.get("grant", {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.manage_grant(action="del", **action_data)
        return {"nvl_JobId": task, "nvl_TaskId": task}, 202


class StorageEfsServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, version=None, **kwargs):
        base = "nws"
        rules = [
            (
                f"{base}/storageservices/efs/file-systems",
                "POST",
                CreateFileSystem,
                {},
            ),
            (
                f"{base}/storageservices/efs/file-systems",
                "GET",
                DescribeFileSystems,
                {},
            ),
            (
                f"{base}/storageservices/efs/file-systems/<oid>",
                "PUT",
                UpdateFileSystem,
                {},
            ),
            (
                f"{base}/storageservices/efs/file-systems/<oid>",
                "DELETE",
                DeleteFileSystem,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets",
                "POST",
                CreateMountTarget,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets",
                "DELETE",
                DeleteMountTarget,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets",
                "GET",
                DescribeMountTargets,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets/<oid>/grants",
                "POST",
                CreateFileSystemGrant,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets/<oid>/grants",
                "DELETE",
                DeleteFileSystemGrant,
                {},
            ),
            (
                f"{base}/storageservices/efs/mount-targets/<oid>/grants",
                "GET",
                ListFileSystemGrant,
                {},
            ),
        ]
        ApiView.register_api(module, rules, **kwargs)
