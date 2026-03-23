# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from flasgger import fields, Schema
from beecell.simple import id_gen, format_date
from beehive_service.service_util import __SITE_NAMES__
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView
from beehive_service.plugins.computeservice.controller import (
    ApiComputeInstance,
    ApiComputeService,
    ApiComputeVolume,
)
from marshmallow.validate import OneOf
from beehive_service.model.base import SrvStatusType
from beehive_service.controller import ServiceController
from beehive.common.data import operation
from typing import List, Type, Tuple, Any, Union, Dict


#class DescribeVolumesApiItemResponseSchema(Schema):
#    pass
    # attachmentSet
    # availabilityZone = fields.String(required=False, example='site01',
    #                                  description='The Availability Zone for the volume.')
    # createTime = fields.String(required=False, example='1999-03-17',
    #                            description='The time stamp when volume creation was initiated.')
    #
    #
    # volumeId = fields.String(required=False, allow_none=True, example='', description='instance id')
    # imageId = fields.String(required=False, allow_none=True, example='', description='image instance id')
    # instanceState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)
    # privateDnsName = fields.String(required=False, allow_none=True, example='',
    #                                description='private dns name assigned to the instance')
    # dnsName = fields.String(required=False, allow_none=True, example='',
    #                         description='public dns name assigned to the instance')
    # reason = fields.String(required=False, allow_none=True, example='',
    #                        description='reason for the current state of the instance')
    # keyName = fields.String(required=False, allow_none=True, example='',
    #                         description='name of the key pair used to create the instance')
    # instanceType = fields.String(required=False, allow_none=True, example='',
    #                              description='instance definition for the instance')
    # productCodes = fields.Nested(InstanceProductCodesResponseSchema, many=False, required=False)
    # launchTime = fields.DateTime (required=False, example='', description='the timestamp the instance was launched')
    # placement = fields.Nested(InstancePlacementsResponseSchema, many=False, required=False)
    # monitoring = fields.Nested(InstanceMonitoringResponseSchema, many=False, required=False)
    # subnetId = fields.String(required=False, allow_none=True, example='', description='subnet id ')
    # vpcId = fields.String(required=False, allow_none=True, example='', description='vpc id ')
    # privateIpAddress = fields.String(required=False, allow_none=True, example='192.168.1.78', description='')
    # ipAddress = fields.String(required=False, allow_none=True, example='192.168.1.98', description='')
    # groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)
    # architecture = fields.String(required=False, allow_none=True, example='i386 | x86_64', description='')
    # rootDeviceType = fields.String(required=False, allow_none=True, example='ebs',
    #                                description='root device type used by the AMI.')
    # blockDeviceMapping = fields.Nested(InstanceBlockDeviceMappingResponseSchema, many=True, required=False)
    # virtualizationType = fields.String(required=False, allow_none=True, example='hvm | paravirtual',
    #                                    description='virtualization type of the instance')
    # tagSet = fields.Nested(InstanceTagSetResponseSchema, many=True, required=False)
    # hypervisor = fields.String(required=False, allow_none=True, example='vmware | openstack',
    #                            description='type of the hypervisor')
    # networkInterfaceSet = fields.Nested(InstanceNetworkInterfaceSetResponseSchema, many=True, required=False)
    # ebsOptimized = fields.Boolean(required=False,
    #                               description='indicates whether the instance is optimized for Amazon EBS I/O')
    # nvl_name = fields.String(required=False, allow_none=True, example='',
    #                          description='name of the instance', data_key='nvl-name')
    # nvl_subnetName = fields.String(required=False, allow_none=True, example='',
    #                                description='subnet name of the instance', data_key='nvl-subnetName')
    # nvl_vpcName = fields.String(required=False, allow_none=True, example='',
    #                             description='vpc name of the instance', data_key='nvl-vpcName')
    # nvl_imageName = fields.String(required=False, allow_none=True, example='',
    #                               description='image name of the instance', data_key='nvl-imageName')
    # nvl_ownerAlias = fields.String(required=False, allow_none=True, example='',
    #                                description='name of the account that owns the instance', data_key='nvl-ownerAlias')
    # nvl_ownerId = fields.String(required=False, allow_none=True, example='',
    #                             description='ID of the account that owns the instance', data_key='nvl-ownerId')
    # nvl_resourceId = fields.String(required=False, allow_none=True, example='',
    #                                description='ID of the instance resource', data_key='nvl-resourceId')
    # nvl_InstanceTypeExt = fields.Nested(InstanceTypeExtResponseSchema, many=False,
    #                                     required=True, data_key='nvl-InstanceTypeExt',
    #                                     description='flavor attributes')


class DescribeVolumesAttachmentSetResponseSchema(Schema):
    requestId = fields.String(required=False, metadata={"description": "api request id"})
    volumeId = fields.String(required=False, allow_none=True, metadata={"description": "volume id"})
    instanceId = fields.String(required=False, allow_none=True, metadata={"description": "instance id"})
    device = fields.String(required=False, allow_none=True, metadata={"description": "instance device"})
    status = fields.String(required=False, metadata={"description": "volume attachment status"})
    attachTime = fields.String(required=False, allow_none=True, metadata={"description": "volume attachment status"})
    deleteOnTermination = fields.Bool(
        required=False,
        metadata={"example": True, "description": "Indicates whether the volume is deleted on instance termination."},
    )


class DescribeVolumesApi1ItemResponseSchema(Schema):
    volumeId = fields.String(required=False, allow_none=True, metadata={"description": "instance id"})
    size = fields.Integer(required=False, metadata={"example": 10, "description": "The size of the volume, in GiBs"})
    snapshotId = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "123", "description": "The snapshot ID"},
    )
    availabilityZone = fields.String(
        required=False,
        metadata={"example": "site01", "description": "The Availability Zone for the volume."},
    )
    status = fields.String(required=False, allow_none=True, metadata={"description": "volume status"})
    createTime = fields.String(
        required=False,
        metadata={"example": "1999-03-17", "description": "The time stamp when volume creation was initiated."},
    )
    attachmentSet = fields.Nested(
        DescribeVolumesAttachmentSetResponseSchema,
        many=True,
        required=False,
        allow_none=False,
    )
    volumeType = fields.String(required=False, metadata={"description": "The volume type"})
    encrypted = fields.Boolean(required=False, allow_none=True, metadata={"description": "volume is encrypted"})
    multiAttachEnabled = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "volume is multi attach"},
    )
    nvl_hypervisor = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-hypervisor",
        metadata={"example": "vmware | openstack", "description": "type of the hypervisor"},
    )
    nvl_name = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-name",
        metadata={"description": "name of the instance"},
    )
    nvl_volumeOwnerAlias = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-volumeOwnerAlias",
        metadata={"description": "Owner Alias"},
    )
    nvl_volumeOwnerId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-volumeOwnerId",
        metadata={"description": "ID of the account that owns the instance"},
    )
    nvl_resourceId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-resourceId",
        metadata={"description": "ID of the instance resource"},
    )


class DescribeVolumesApi1ResponseSchema(Schema):
    nextToken = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True)
    volumesSet = fields.Nested(DescribeVolumesApi1ItemResponseSchema, many=True, required=True, allow_none=False)
    nvl_volumeTotal = fields.Integer(
        required=False,
        allow_none=True,
        data_key="nvl-volumeTotal",
        metadata={"example": 2, "description": "ID of the instance resource"},
    )
    xmlns = fields.String(required=False, data_key="__xmlns")


class DescribeVolumesApiResponseSchema(Schema):
    DescribeVolumesResponse = fields.Nested(
        DescribeVolumesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeVolumesAttachmentApiRequestSchema(Schema):
    instance_id = fields.String(
        required=False,
        allow_none=True,
        data_key="instance-id",
        metadata={"example": "1999-09-23", "description": "The ID of the instance the volume is attached to."},
    )


class DescribeVolumesApiRequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False,
        dump_default=10,
        data_key="MaxResults",
        context="query",
        metadata={"description": ""},
    )

    NextToken = fields.String(
        required=False,
        dump_default="0",
        data_key="NextToken",
        context="query",
        metadata={"description": ""},
    )

    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    Nvl_Name_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="Nvl_Name.N",
        metadata={"description": "name of the volume"},
    )

    VolumeId_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="VolumeId.N",
        metadata={"description": "volume id"},
    )

    volume_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="volume-id.N",
        metadata={"description": "volume id"},
    )

    volume_type_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="volume-type.N",
        metadata={"description": "The volume type."},
    )

    status_N = fields.List(
        fields.String(
            example="",
            validate=OneOf(["creating", " available", "in-use", "deleting", " deleted", "error"]),
        ),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="status.N",
        metadata={"description": "The status of the volume (creating | available | " "in-use | deleting | deleted | error)"},
    )

    tag_key_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="tag-key.N",
        metadata={"description": "value of a tag assigned to the resource"},
    )

    create_time_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="create-time.N",
        metadata={"description": "The time stamp when the volume was created."},
    )

    attachment_N = fields.Nested(
        DescribeVolumesAttachmentApiRequestSchema,
        many=True,
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="attachment.N",
        metadata={"description": "Attachment"},
    )


class DescribeVolumes(ServiceApiView):
    summary = "Describe compute volume"
    description = "Describe compute volume"
    tags = ["computeservice"]
    definitions = {
        "DescribeVolumesApiRequestSchema": DescribeVolumesApiRequestSchema,
        "DescribeVolumesApiResponseSchema": DescribeVolumesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeVolumesApiRequestSchema)
    parameters_schema = DescribeVolumesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DescribeVolumesApiResponseSchema}}
    )
    response_schema = DescribeVolumesApiResponseSchema

    def get(self, controller: ServiceController, data: dict, *args, **kwargs):
        data_search = {}
        data_search["size"] = data.get("MaxResults", 10)
        data_search["page"] = int(data.get("NextToken", 0))

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance name
        volume_name_list = data.get("Nvl_Name_N", [])

        # get volume identifier
        volume_id_list = data.get("volume_id_N", [])
        volume_id_list.extend(data.get("VolumeId_N", []))

        # get volume service definition
        volume_def_list = data.get("volume_type_N", [])

        # get volume launch time
        volume_launch_time_list = data.get("create_time_N", [])
        volume_launch_time = None
        if len(volume_launch_time_list) == 1:
            volume_launch_time = volume_launch_time_list[0]
        elif len(volume_launch_time_list) > 1:
            self.logger.warn("For the moment only one create_time can be submitted as filter")

        # get tags
        tag_values = data.get("tag_key_N", None)
        # resource_tags = ['nws$%s' % t for t in tag_values]

        # get status
        status_mapping = {
            "creating": SrvStatusType.PENDING,
            "available": SrvStatusType.ACTIVE,
            "in-use": SrvStatusType.ACTIVE,
            "deleting": SrvStatusType.TERMINATED,
            "deleted": SrvStatusType.TERMINATED,
            "error": SrvStatusType.ERROR,
        }

        status_name_list = None
        status_list = data.get("status_N", None)
        if status_list is not None:
            status_name_list = [status_mapping[i] for i in status_list if i in status_mapping.keys()]

        # get volumes list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=volume_id_list,
            account_id_list=account_id_list,
            service_name_list=volume_name_list,
            filter_creation_date_start=volume_launch_time,
            service_definition_id_list=volume_def_list,
            servicetags_or=tag_values,
            service_status_name_list=status_name_list,
            plugintype=ApiComputeVolume.plugintype,
            **data_search,
        )

        # format result
        volumes_set = [r.aws_info() for r in res]

        res = {
            "DescribeVolumesResponse": {
                "__xmlns": self.xmlns,
                "nextToken": str(data_search["page"] + 1),
                "requestId": operation.id,
                "volumesSet": volumes_set,
                "nvl-volumeTotal": total,
            }
        }
        return res

class CreateVolumeApiParamRequestSchema(Schema):
    # AccountId managed by AWS Wrapper
    owner_id = fields.String(
        required=True,
        data_key="owner-id",
        metadata={"example": "1", "description": "account id or uuid associated to compute zone"},
    )
    VolumeType = fields.String(required=True, metadata={"example": "vol.default", "description": "The volume type"})
    SnapshotId = fields.String(
        required=False,
        metadata={"example": "123", "description": "The snapshot from which to create the " "volume. You must specify either a snapshot ID"},
    )
    # TagSpecification_N = fields.Nested(TagSpecificationMappingApiRequestSchema, required=False, many=True,
    #                                    allow_none=False, data_key='TagSpecification.N',
    #                                    description='The tags to apply to the resources during launch')
    Size = fields.Integer(required=True, metadata={"example": 10, "description": "The size of the volume, in GiBs"})
    Iops = fields.Integer(
        required=False,
        load_default=-1,
        metadata={"example": 1000, "description": "The number of I/O operations per "
        "second (IOPS) to provision for the volume, with a maximum ratio of xx IOPS/GiB"},
    )
    AvailabilityZone = fields.String(
        required=True,
        validate=OneOf(__SITE_NAMES__),
        metadata={"example": "SiteTorino01", "description": "The Availability Zone in which to create the volume"},
    )
    MultiAttachEnabled = fields.Bool(
        required=False,
        load_default=False,
        metadata={"example": True, "description": "Specifies whether to "
        "enable volume Multi-Attach. If you enable Multi-Attach, you can attach the "
        "volume to up to xx instances in the same Availability Zone"},
    )
    Encrypted = fields.Bool(
        required=False,
        load_default=False,
        metadata={"example": True, "description": "Specifies whether the volume should be encrypted"},
    )
    Nvl_Hypervisor = fields.String(
        load_default="openstack",
        required=False,
        validate=OneOf(["openstack", "vsphere"]),
        metadata={"example": "openstack", "description": "hypervisor type"},
    )
    Nvl_Name = fields.String(required=False, metadata={"example": "test", "description": "volume name"})


class CreateVolumeApiRequestSchema(Schema):
    volume = fields.Nested(CreateVolumeApiParamRequestSchema, context="body")


class CreateVolumeApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True, metadata={"description": "api request id"})
    volumeId = fields.String(required=True, allow_none=True, metadata={"description": "volume id"})
    size = fields.Integer(required=True, allow_none=True, metadata={"description": "volume size"})
    iops = fields.String(required=True, allow_none=True, metadata={"description": "volume iops"})
    snapshotId = fields.String(required=False, allow_none=True, metadata={"description": "volume snapshot id"})
    availabilityZone = fields.String(
        required=True,
        allow_none=True,
        metadata={"description": "volume availability zone"},
    )
    status = fields.String(required=True, allow_none=True, metadata={"description": "volume status"})
    createTime = fields.String(required=True, allow_none=True, metadata={"description": "volume creation time"})
    volumeType = fields.String(required=True, allow_none=True, metadata={"description": "volume type"})
    encrypted = fields.Boolean(required=True, allow_none=True, metadata={"description": "volume is encrypted"})
    multiAttachEnabled = fields.Boolean(
        required=True,
        allow_none=True,
        metadata={"description": "volume is multi attach"},
    )

class CreateVolumeApiResponseSchema(Schema):
    CreateVolumeResponse = fields.Nested(CreateVolumeApi1ResponseSchema, required=True)


class CreateVolumeApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateVolumeApiRequestSchema, context="body")


class CreateVolume(ServiceApiView):
    summary = "Create compute volume"
    description = "Create compute volume"
    tags = ["computeservice"]
    definitions = {
        "CreateVolumeApiRequestSchema": CreateVolumeApiRequestSchema,
        "CreateVolumeApiResponseSchema": CreateVolumeApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateVolumeApiBodyRequestSchema)
    parameters_schema = CreateVolumeApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": CreateVolumeApiResponseSchema}})
    response_schema = CreateVolumeApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs) -> Tuple[dict, int]:
        inner_data = data.get("volume")

        service_definition_id = inner_data.get("VolumeType")
        account_id = inner_data.get("owner_id")
        name = inner_data.get("Nvl_Name", "volume-%s" % id_gen())
        desc = name

        # check instance with the same name already exists
        # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiComputeService.plugintype
        )

        data["computeZone"] = parent_plugin.resource_uuid
        inst = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        res = {
            "CreateVolumeResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "volumeId": inst.instance.uuid,
                "size": inner_data.get("Size"),
                "iops": None,
                "snapshotId": inner_data.get("SnapshotId"),
                "availabilityZone": inner_data.get("AvailabilityZone"),
                "status": "creating",
                "createTime": format_date(inst.model.creation_date),
                "volumeType": inner_data.get("VolumeType"),
                "encrypted": inner_data.get("Encrypted"),
                "multiAttachEnabled": inner_data.get("MultiAttachEnabled"),
            }
        }
        self.logger.debug("Service Aws response: %s" % res)

        return res, 202


class DeleteVolumeResponseItemSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    # nvl_return = fields.Integer(required=True, example=True, data_key='return', description='return status')
    nvl_return = fields.Boolean(required=True, data_key="return", metadata={"description": "return status"})


class DeleteVolumeResponseSchema(Schema):
    DeleteVolumeResponse = fields.Nested(DeleteVolumeResponseItemSchema, required=True, many=False, allow_none=False)


class DeleteVolumeRequestSchema(Schema):
    VolumeId = fields.String(required=True, descritpion="volume id")


class DeleteVolumeBodyRequestSchema(Schema):
    body = fields.Nested(DeleteVolumeRequestSchema, context="body")


class DeleteVolume(ServiceApiView):
    summary = "Delete compute volume"
    description = "Delete compute volume"
    tags = ["computeservice"]
    definitions = {
        "DeleteVolumeRequestSchema": DeleteVolumeRequestSchema,
        "DeleteVolumeResponseSchema": DeleteVolumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteVolumeBodyRequestSchema)
    parameters_schema = DeleteVolumeRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": DeleteVolumeResponseSchema}})
    response_schema = DeleteVolumeResponseSchema

    def delete(self, controller: ServiceController, data: dict, *args, **kwargs):
        instance_id = data.pop("VolumeId")
        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiComputeVolume)
        type_plugin.delete()

        res = {
            "DeleteVolumeResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": True,
            }
        }

        return res, 202


class AttachVolumeApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    volumeId = fields.String(required=True, metadata={"description": "volume id"})
    instanceId = fields.String(required=True, metadata={"description": "instance id"})
    device = fields.String(required=True, metadata={"description": "instance device"})
    status = fields.String(required=True, metadata={"description": "volume attachment status"})
    attachTime = fields.String(required=True, metadata={"description": "volume attachment status"})
    xmlns = fields.String(required=False, data_key="__xmlns")


class AttachVolumeApiResponseSchema(Schema):
    AttachVolumeResponse = fields.Nested(AttachVolumeApi1ResponseSchema, required=True, many=False, allow_none=False)


class AttachVolumeApiRequestSchema(Schema):
    Device = fields.String(required=True, metadata={"example": "/dev/sdh", "description": "The device name"})
    InstanceId = fields.String(required=True, metadata={"example": "123", "description": "The ID of the instance"})
    VolumeId = fields.String(
        required=True,
        metadata={"example": "123", "description": "The ID of the volume. The volume and instance " "must be within the same Availability Zone."},
    )


class AttachVolumeBodyRequestSchema(Schema):
    body = fields.Nested(AttachVolumeApiRequestSchema, context="body")


class AttachVolume(ServiceApiView):
    summary = "Attach compute volume to an instance"
    description = "Attach compute volume to an instance"
    tags = ["computeservice"]
    definitions = {
        "AttachVolumeApiRequestSchema": AttachVolumeApiRequestSchema,
        "AttachVolumeApiResponseSchema": AttachVolumeApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(AttachVolumeBodyRequestSchema)
    parameters_schema = AttachVolumeApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": AttachVolumeApiResponseSchema}})
    response_schema = AttachVolumeApiResponseSchema

    def put(self, controller: ServiceController, data: dict, *args, **kwargs):
        instance_id = data.pop("InstanceId")
        volume_id = data.pop("VolumeId")
        device = data.pop("Device")

        type_plugin = controller.get_service_type_plugin(volume_id)
        type_plugin.attach(instance_id, device)

        res = {
            "AttachVolumeResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "volumeId": volume_id,
                "instanceId": instance_id,
                "device": device,
                "status": "attaching",
                "attachTime": "",
            }
        }
        return res


class DetachVolumeApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    volumeId = fields.String(required=True, metadata={"description": "volume id"})
    instanceId = fields.String(required=True, metadata={"description": "instance id"})
    device = fields.String(required=True, metadata={"description": "instance device"})
    status = fields.String(required=True, metadata={"description": "volume attachment status"})
    attachTime = fields.String(required=True, metadata={"description": "volume attachment status"})
    deleteOnTermination = fields.Bool(
        required=True,
        metadata={"example": "True", "description": "Indicates whether the volume is deleted on instance termination."},
    )
    xmlns = fields.String(required=False, data_key="__xmlns")


class DetachVolumeApiResponseSchema(Schema):
    DetachVolumeResponse = fields.Nested(DetachVolumeApi1ResponseSchema, required=True, many=False, allow_none=False)


class DetachVolumeApiRequestSchema(Schema):
    Force = fields.Bool(
        required=False,
        load_default=False,
        metadata={"example": True, "description": "Forces detachment if the previous "
        "detachment attempt did not occur cleanly (for example, logging into an instance, unmounting "
        "the volume, and detaching normally). This option can lead to data loss or a corrupted file "
        "system. Use this option only as a last resort to detach a volume from a failed instance"},
    )
    Device = fields.String(required=True, metadata={"example": "/dev/sdh", "description": "The device name"})
    InstanceId = fields.String(required=True, metadata={"example": "123", "description": "The ID of the instance"})
    VolumeId = fields.String(
        required=True,
        metadata={"example": "123", "description": "The ID of the volume. The volume and instance " "must be within the same Availability Zone."},
    )


class DetachVolumeBodyRequestSchema(Schema):
    body = fields.Nested(DetachVolumeApiRequestSchema, context="body")


class DetachVolume(ServiceApiView):
    summary = "Detach compute volume to an instance"
    description = "Detach compute volume to an instance"
    tags = ["computeservice"]
    definitions = {
        "DetachVolumeApiRequestSchema": DetachVolumeApiRequestSchema,
        "DetachVolumeApiResponseSchema": DetachVolumeApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DetachVolumeBodyRequestSchema)
    parameters_schema = DetachVolumeApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": DetachVolumeApiResponseSchema}})
    response_schema = DetachVolumeApiResponseSchema

    def put(self, controller: ServiceController, data: dict, *args, **kwargs):
        instance_id = data.pop("InstanceId")
        volume_id = data.pop("VolumeId")
        device = data.pop("Device")

        type_plugin = controller.get_service_type_plugin(volume_id)
        type_plugin.detach(instance_id, device)

        res = {
            "DetachVolumeResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "volumeId": volume_id,
                "instanceId": instance_id,
                "device": device,
                "status": "detaching",
                "attachTime": "",
                "deleteOnTermination": True,
            }
        }
        return res


class InstanceTypeFeatureResponseSchema(Schema):
    vcpus = fields.String(required=False, allow_none=True, metadata={"description": ""})
    ram = fields.String(required=False, allow_none=True, metadata={"description": ""})
    disk = fields.String(required=False, allow_none=True, metadata={"description": ""})


class InstanceTypeResponseSchema(Schema):
    id = fields.Integer(required=True, metadata={"description": ""})
    uuid = fields.String(required=True, metadata={"description": ""})
    name = fields.String(required=True, metadata={"description": ""})
    resource_id = fields.String(required=False, allow_none=True, metadata={"description": ""})
    description = fields.String(required=True, allow_none=True, metadata={"description": ""})
    features = fields.Nested(InstanceTypeFeatureResponseSchema, required=True, many=False, allow_none=False)


class DescribeVolumeTypesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    volumeTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    volumeTypesTotal = fields.Integer(required=True)


class DescribeVolumeTypesApiResponseSchema(Schema):
    DescribeVolumeTypesResponse = fields.Nested(
        DescribeVolumeTypesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeVolumeTypesApiRequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False,
        dump_default=10,
        context="query",
        metadata={"description": "entities list page size"},
    )
    NextToken = fields.String(
        required=False,
        dump_default="0",
        context="query",
        metadata={"description": "entities list page selected"},
    )
    volume_type_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="volume-type.N",
        metadata={"description": "list of volume type uuid"},
    )


class DescribeVolumeTypes(ServiceApiView):
    summary = "Describe compute volume types"
    description = "Describe compute volume types"
    tags = ["computeservice"]
    definitions = {
        "DescribeVolumeTypesApiRequestSchema": DescribeVolumeTypesApiRequestSchema,
        "DescribeVolumeTypesApiResponseSchema": DescribeVolumeTypesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeVolumeTypesApiRequestSchema)
    parameters_schema = DescribeVolumeTypesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeVolumeTypesApiResponseSchema,
            }
        }
    )
    response_schema = DescribeVolumeTypesApiResponseSchema

    def get(self, controller: ServiceController, data: dict, *args, **kwargs):
        volume_types_set, total = controller.get_catalog_service_definitions(
            size=data.pop("MaxResults", 10),
            page=int(data.pop("NextToken", 0)),
            plugintype="ComputeVolume",
            def_uuids=data.pop("volume_type_N", []),
        )

        res = {
            "DescribeVolumeTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "volumeTypesSet": volume_types_set,
                "volumeTypesTotal": total,
            }
        }
        return res


class ComputeVolumeAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/computeservices/volume"
        rules = [
            ("%s/attachvolume" % base, "PUT", AttachVolume, {}),
            ("%s/createvolume" % base, "POST", CreateVolume, {}),
            ("%s/deletevolume" % base, "DELETE", DeleteVolume, {}),
            # # DescribeVolumeAttribute
            ("%s/describevolumes" % base, "GET", DescribeVolumes, {}),
            # # DescribeVolumesModifications
            # # DescribeVolumeStatus
            ("%s/detachvolume" % base, "PUT", DetachVolume, {}),
            # # EnableVolumeIO
            # # ModifyVolume
            # # ModifyVolumeAttribute
            ("%s/describevolumetypes" % base, "GET", DescribeVolumeTypes, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
