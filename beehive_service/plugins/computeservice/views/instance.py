# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive_service.controller.api_account import ApiAccount
from typing import Dict
from flasgger import fields, Schema
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    ApiView,
    ApiManagerWarning,
    ApiManagerError,
)
from beehive_service.plugins.computeservice.controller import (
    ApiComputeInstance,
    ApiComputeService,
    ApiComputeImage,
)
from marshmallow.validate import OneOf, Length, Range
from beehive_service.controller import ServiceController
from beehive_service.model.base import SrvStatusType
from beehive.common.data import operation
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from beehive_service.service_util import __SRV_AWS_TAGS_RESOURCE_TYPE_INSTANCE__
from beehive_service.controller import ServiceController
from beehive_service.plugins.computeservice.controller import ApiComputeInstance


class InstanceProductCodesResponseSchema(Schema):
    productCode = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "product code AMI used to launch the instance"},
    )
    type = fields.String(required=False, allow_none=True, metadata={"description": "type of product code"})


class InstancePlacementsResponseSchema(Schema):
    affinity = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "affinity setting for the instance on the dedicated host"},
    )
    availabilityZone = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "availability zone of the instance id"},
    )
    groupName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the placement group the instance"},
    )
    spreadDomain = fields.String(required=False, allow_none=True, metadata={"description": "instance id"})
    hostId = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "host id on which the instance reside"},
    )
    tenancy = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "tenancy of the instance (if the instance is running in a VPC)"},
    )


class InstanceMonitoringResponseSchema(Schema):
    state = fields.String(required=False, allow_none=True, metadata={"description": "status of monitoring"})


class InstanceGroupSetResponseSchema(Schema):
    groupName = fields.String(required=False, allow_none=True, metadata={"description": "security group name"})
    groupId = fields.String(required=False, allow_none=True, metadata={"description": "security group id"})


class InstanceBlockDeviceMappingItem1ResponseSchema(Schema):
    volumeId = fields.String(required=False, allow_none=True, metadata={"description": "id volume ebs"})
    status = fields.String(required=False, allow_none=True, metadata={"description": "attachment status"})
    attachTime = fields.DateTime(required=False, allow_none=True, metadata={"description": "attachment timestamp"})

    deleteOnTermination = fields.Boolean(
        required=False,
        metadata={"description": "boolean to know if the volume is deleted on " "instance termination."},
    )

    volumeSize = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 10, "description": "The size of the volume, in GiB."},
    )


class InstanceBlockDeviceMappingResponseSchema(Schema):
    deviceName = fields.String(required=False, allow_none=True, metadata={"description": "device name"})
    ebs = fields.Nested(InstanceBlockDeviceMappingItem1ResponseSchema, many=False, required=False)


class InstanceTagSetResponseSchema(Schema):
    key = fields.String(required=False, metadata={"description": "tag key"})
    value = fields.String(required=False, metadata={"description": "tag value"})


class InstanceAssociationResponseSchema(Schema):
    publicIp = fields.String(required=False, allow_none=True, metadata={"description": "public IP address "})


class InstancePrivateIpAddressesSetResponseSchema(Schema):
    privateIpAddress = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "private IPv4 address associated with the network interface"},
    )

    association = fields.Nested(InstanceAssociationResponseSchema, many=True, required=False)


class InstanceNetworkInterfaceSetResponseSchema(Schema):
    networkInterfaceId = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "network interface id"},
    )

    subnetId = fields.String(required=False, allow_none=True, metadata={"description": "subnet id"})
    vpcId = fields.String(required=False, allow_none=True, metadata={"description": "vpc id"})
    status = fields.String(required=False, allow_none=True, metadata={"description": "status of the network interface"})

    privateDnsName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "private DNS name of the network interface"},
    )

    groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)
    association = fields.Nested(InstanceAssociationResponseSchema, many=False, required=False)
    privateIpAddressesSet = fields.Nested(InstancePrivateIpAddressesSetResponseSchema, many=False, required=False)


class InstanceStateResponseSchema(Schema):
    code = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 0, "description": "code of instance state"},
    )

    name = fields.String(
        required=False,
        validate=OneOf(
            [
                getattr(ApiComputeInstance.state_enum, x)
                for x in dir(ApiComputeInstance.state_enum)
                if not x.startswith("__")
            ]
        ),
        metadata={"example": "pending | running | ....", "description": "name of instance state"},
    )


class InstanceTypeExtResponseSchema(Schema):
    vcpus = fields.Integer(required=False, metadata={"example": 1, "description": "number of virtual cpu"})
    bandwidth = fields.Integer(required=False, metadata={"example": 0, "description": "bandwidth"})
    memory = fields.Integer(required=False, metadata={"example": 0, "description": "RAM"})
    disk_iops = fields.Integer(required=False, metadata={"example": 0, "description": "available disk IOPS"})
    disk = fields.Integer(required=False, metadata={"example": 0, "description": "number of virtual disk"})


class StateReasonResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, metadata={"example": 400})
    message = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "Parent instance <ServiceInstance at 0x7f3158628d90> is not bound to a Session"},
    )
    

class InstanceInstancesSetResponseSchema(Schema):
    instanceId = fields.String(required=False, allow_none=True, metadata={"description": "instance id"})
    imageId = fields.String(required=False, allow_none=True, metadata={"description": "image instance id"})
    instanceState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)

    privateDnsName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "private dns name assigned to the instance"},
    )

    dnsName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "public dns name assigned to the instance"},
    )

    reason = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "reason for the current state of the instance"},
    )

    keyName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the key pair used to create the instance"},
    )

    instanceType = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "instance definition for the instance"},
    )

    productCodes = fields.Nested(InstanceProductCodesResponseSchema, many=False, required=False)
    launchTime = fields.DateTime(required=False, metadata={"description": "the timestamp the instance was launched"})
    placement = fields.Nested(InstancePlacementsResponseSchema, many=False, required=False)
    monitoring = fields.Nested(InstanceMonitoringResponseSchema, many=False, required=False)
    subnetId = fields.String(required=False, allow_none=True, metadata={"description": "subnet id "})
    vpcId = fields.String(required=False, allow_none=True, metadata={"description": "vpc id "})

    privateIpAddress = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "###.###.###.###", "description": ""},
    )

    ipAddress = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "###.###.###.###", "description": ""},
    )

    groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)

    architecture = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "i386 | x86_64", "description": ""},
    )

    rootDeviceType = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "ebs", "description": "root device type used by the AMI."},
    )

    blockDeviceMapping = fields.Nested(InstanceBlockDeviceMappingResponseSchema, many=True, required=False)

    virtualizationType = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "hvm | paravirtual", "description": "virtualization type of the instance"},
    )

    tagSet = fields.Nested(InstanceTagSetResponseSchema, many=True, required=False)

    hypervisor = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "vmware | openstack", "description": "type of the hypervisor"},
    )

    networkInterfaceSet = fields.Nested(InstanceNetworkInterfaceSetResponseSchema, many=True, required=False)

    ebsOptimized = fields.Boolean(
        required=False,
        metadata={"description": "indicates whether the instance is optimized for Amazon EBS I/O"},
    )

    nvl_name = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-name",
        metadata={"description": "name of the instance"},
    )

    nvl_subnetName = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-subnetName",
        metadata={"description": "subnet name of the instance"},
    )

    nvl_vpcName = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-vpcName",
        metadata={"description": "vpc name of the instance"},
    )

    nvl_imageName = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-imageName",
        metadata={"description": "image name of the instance"},
    )

    nvl_ownerAlias = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-ownerAlias",
        metadata={"description": "name of the account that owns the instance"},
    )

    nvl_ownerId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-ownerId",
        metadata={"description": "ID of the account that owns the instance"},
    )

    nvl_resourceId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-resourceId",
        metadata={"description": "ID of the instance resource"},
    )

    nvl_InstanceTypeExt = fields.Nested(
        InstanceTypeExtResponseSchema,
        many=False,
        required=True,
        data_key="nvl-InstanceTypeExt",
        metadata={"description": "flavor attributes"},
    )

    stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False)


class InstanceReservationSetResponseSchema(Schema):
    groupSet = fields.Nested(InstanceGroupSetResponseSchema, required=False, many=True, allow_none=True)
    instancesSet = fields.Nested(InstanceInstancesSetResponseSchema, required=False, many=True, allow_none=True)
    ownerId = fields.String(required=False, metadata={"description": ""})
    requesterId = fields.String(required=False, metadata={"description": ""})
    reservationId = fields.String(required=False, metadata={"description": ""})
    nvl_instanceTotal = fields.Integer(required=True, data_key="nvl-instanceTotal", metadata={"description": ""})


class DescribeInstancesApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    nextToken = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True)
    reservationSet = fields.Nested(InstanceReservationSetResponseSchema, many=True, required=True, allow_none=False)


class DescribeInstancesApiResponseSchema(Schema):
    DescribeInstancesResponse = fields.Nested(
        DescribeInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class IamInstanceProfileApiRequestSchema(Schema):
    arn = fields.List(fields.String(), required=False, metadata={"description": ""})


class NetworkInterfaceAddresses2ApiRequestSchema(Schema):
    public_ip = fields.List(fields.String(), required=False, metadata={"description": "network public IPv4 address"})

    ip_owner_id = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "owner of the IPv4 associated with the " "network interface"},
    )


class NetworkInterfaceAddresses1ApiRequestSchema(Schema):
    private_ip_address = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "network private IPv4 address"},
    )

    primary = fields.List(
        fields.Boolean(),
        required=False,
        metadata={"description": "Specify if the IPv4 address of the network " "interface is the primary private IPv4 " "address"},
    )

    association = fields.Nested(NetworkInterfaceAddresses2ApiRequestSchema, required=False, context="query")


class NetworkInterfaceAssociationApiRequestSchema(Schema):
    public_ip = fields.List(fields.String(), required=False, metadata={"description": "network public IPv4 address"})

    ip_owner_id = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "owner of the IPv4 associated with the network interface"},
    )

    allocation_id = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "allocation ID for the network IPv4 address"},
    )

    association_id = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "association ID for the network IPv4 address"},
    )


class NetworkInterfaceAttachmentApiRequestSchema(Schema):
    attachment_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    instance_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    instance_owner_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    device_index = fields.List(fields.String(), required=False, metadata={"description": ""})
    status = fields.List(fields.String(), required=False, metadata={"description": ""})
    attach_time = (fields.List(fields.DateTime(), required=False, description=""),)
    delete_on_termination = fields.List(fields.Boolean(), required=False, metadata={"description": ""})


class NetworkInterfaceIpv6ApiRequestSchema(Schema):
    ipv6_address = fields.List(fields.String(), required=False, metadata={"description": ""})


class NetworkInterfaceApiRequestSchema(Schema):
    addresses = fields.Nested(NetworkInterfaceAddresses1ApiRequestSchema, required=False, context="query")
    association = fields.Nested(NetworkInterfaceAssociationApiRequestSchema, required=False, context="query")
    attachment = fields.Nested(NetworkInterfaceAttachmentApiRequestSchema, required=False, context="query")
    availability_zone = fields.List(fields.String(), required=False, metadata={"description": "availability zone"})
    description = fields.List(fields.String(), required=False, metadata={"description": ""})
    group_id = fields.List(fields.String(), required=False, metadata={"description": "security group id"})
    group_name = fields.List(fields.String(), required=False, metadata={"description": "security group name"})
    ipv6_addresses = fields.Nested(NetworkInterfaceIpv6ApiRequestSchema, required=False, context="query")
    mac_address = fields.List(fields.String(), required=False, metadata={"description": ""})
    network_interface_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    owner_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    private_dns_name = fields.List(fields.String(), required=False, metadata={"description": ""})
    requester_id = fields.List(fields.String(), required=False, metadata={"description": ""})
    requester_managed = fields.List(fields.String(), required=False, metadata={"description": ""})
    status = fields.List(fields.String(), required=False, metadata={"description": ""})
    source_dest_check = fields.List(fields.String(), required=False, metadata={"description": ""})
    subnet_id = fields.List(fields.String(), required=False, metadata={"description": "subnet id"})
    vpc_id = fields.List(fields.String(), required=False, metadata={"description": "vpc id"})


class DescribeInstancesApiRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, dump_default=10, context="query", metadata={"description": ""})
    NextToken = fields.String(required=False, dump_default="0", context="query", metadata={"description": ""})

    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    name_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="name.N",
        metadata={"description": "name of the instance"},
    )

    name_pattern = fields.String(
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="name-pattern",
        metadata={"description": "name of the instance"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instanceId.N",
        metadata={"description": "instance id"},
    )

    instance_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-id.N",
        metadata={"description": "instance id"},
    )

    instance_state_name_N = fields.List(
        fields.String(example="", validate=OneOf(["pending", "running", "terminated", "error"])),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-state-name.N",
        metadata={"description": "state name of the instance"},
    )

    instance_type_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-type.N",
        metadata={"description": "instance type"},
    )

    launch_time_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="launch-time.N",
        metadata={"description": "time when the instance was created"},
    )

    requester_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="requester-id.N",
        metadata={"description": "ID of the entity that launched the instance"},
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

    group_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance.group-id.N",
        metadata={"description": "ID of the security group. Only one is supported for the moment"},
    )

    group_name_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance.group-name.N",
        metadata={"description": "Name of the security group. Only one is supported for the moment"},
    )


class DescribeInstances(ServiceApiView):
    summary = "Describe compute instance"
    description = "Describe compute instance"
    tags = ["computeservice"]

    definitions = {
        "DescribeInstancesApiRequestSchema": DescribeInstancesApiRequestSchema,
        "DescribeInstancesApiResponseSchema": DescribeInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeInstancesApiRequestSchema)
    parameters_schema = DescribeInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DescribeInstancesApiResponseSchema}}
    )

    response_schema = DescribeInstancesApiResponseSchema
    # TODO filter to select only instances of a specific owner

    def get(self, controller: ServiceController, data: Dict, *args, **kwargs):
        data_search = {}
        data_search["size"] = data.get("MaxResults", 10)
        data_search["page"] = int(data.get("NextToken", 0))

        # check Account
        account_id_list = data.get("owner_id_N", [])
        account_id_list.extend(data.get("requester_id_N", []))

        # get instance identifier
        instance_id_list = data.get("instance_id_N", [])
        instance_id_list.extend(data.get("InstanceId_N", []))

        # get instance name
        instance_name_list = data.get("name_N", [])

        # get instance name pattern
        instance_name_pattern = data.get("name_pattern", None)

        # get instance service definition
        instance_def_list = data.get("instance_type_N", [])
        instance_def_list = [controller.get_service_def(instance_def).oid for instance_def in instance_def_list]

        # get instance launch time
        instance_launch_time_list = data.get("launch_time_N", [])
        instance_launch_time = None
        if len(instance_launch_time_list) == 1:
            instance_launch_time = instance_launch_time_list[0]
        elif len(instance_launch_time_list) > 1:
            self.logger.warn("For the moment only one instance_launch_time can be submitted as filter")

        # get tags
        tag_values = data.get("tag_key_N", None)
        # resource_tags = ['nws$%s' % t for t in tag_values]

        # get security groups
        sgs = data.get("group_id_N", [])
        sgs.extend(data.get("group_name_N", []))
        if len(sgs) > 1:
            self.logger.warn("For the moment only one security group can be submitted as filter")

        # make search using security group
        if len(sgs) > 0 and sgs[0] is not None:
            sg = controller.get_service_instance(sgs[0])
            res, total = sg.get_linked_services(link_type="sg", filter_expired=False)
            for instSrv in res:
                instance_id_list.append(instSrv.uuid)

        # get status
        status_mapping = {
            "pending": SrvStatusType.PENDING,
            "running": SrvStatusType.ACTIVE,
            # 'stopping': SrvStatusType.STOPPING,
            # 'stopped': SrvStatusType.STOPPED,
            # 'shutting-down': SrvStatusType.SHUTTINGDOWN,
            "terminated": SrvStatusType.TERMINATED,
            "error": SrvStatusType.ERROR,
        }

        status_name_list = None
        status_list = data.get("instance_state_name_N", None)
        if status_list is not None:
            status_name_list = [status_mapping[i] for i in status_list if i in status_mapping.keys()]

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            name=instance_name_pattern,
            account_id_list=account_id_list,
            filter_creation_date_start=instance_launch_time,
            service_definition_id_list=instance_def_list,
            servicetags_or=tag_values,
            service_status_name_list=status_name_list,
            plugintype=ApiComputeInstance.plugintype,
            **data_search,
        )

        # format result
        instances_set = [r.aws_info() for r in res]

        res = {
            "DescribeInstancesResponse": {
                "__xmlns": self.xmlns,
                "nextToken": str(data_search["page"] + 1),
                "requestId": operation.id,
                "reservationSet": [
                    {
                        "requesterId": "",
                        "reservationId": "",
                        "ownerId": "",
                        "groupSet": [{}],
                        "instancesSet": instances_set,
                        "nvl-instanceTotal": total,
                    }
                ],
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


class DescribeInstanceTypesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    instanceTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    instanceTypesTotal = fields.Integer(required=True)


class DescribeInstanceTypesApiResponseSchema(Schema):
    DescribeInstanceTypesResponse = fields.Nested(
        DescribeInstanceTypesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeInstanceTypesApiRequestSchema(Schema):
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

    instance_type_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-type.N",
        metadata={"description": "list of instance type uuid"},
    )


class DescribeInstanceTypes(ServiceApiView):
    summary = "Describe compute instance types"
    description = "Describe compute instance types"
    tags = ["computeservice"]

    definitions = {
        "DescribeInstanceTypesApiRequestSchema": DescribeInstanceTypesApiRequestSchema,
        "DescribeInstanceTypesApiResponseSchema": DescribeInstanceTypesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeInstanceTypesApiRequestSchema)
    parameters_schema = DescribeInstanceTypesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeInstanceTypesApiResponseSchema,
            }
        }
    )

    response_schema = DescribeInstanceTypesApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_types_set, total = controller.get_catalog_service_definitions(
            size=data.pop("MaxResults", 10),
            page=int(data.pop("NextToken", 0)),
            plugintype="ComputeInstance",
            def_uuids=data.pop("instance_type_N", []),
        )

        res = {
            "DescribeInstanceTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceTypesSet": instance_types_set,
                "instanceTypesTotal": total,
            }
        }
        return res


class EbsBlockDeviceMappingApiRequestSchema(Schema):
    DeleteOnTermination = fields.Boolean(
        required=False,
        allow_none=True,
        load_default=True,
        metadata={
            "example": True,
            "description": "Indicates whether the EBS volume is deleted on instance termination."
        },
    )

    Encrypted = fields.Boolean(
        required=False,
        allow_none=True,
        load_default=False,
        metadata={"example": False, "description": "Indicates whether the EBS volume is encrypted"},
    )

    Iops = fields.Integer(
        required=False,
        allow_none=True,
        metadata={
            "example": 10,
            "description": "The number of I/O operations per second (IOPS) that the volume supports."
        },
    )

    KmsKeyId = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Identifier (key ID, key alias, ID ARN, or alias ARN) for a user-managed CMK "
                           "under which the EBS volume is encrypted."},
    )
    SnapshotId = fields.String(required=False, allow_none=True, metadata={"description": "The ID of the snapshot."})

    Nvl_VolumeId = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "The ID of the volume to clone"},
    )

    VolumeSize = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 10, "description": "The size of the volume, in GiB."},
    )

    VolumeType = fields.String(
        required=False,
        allow_none=True,
        load_default=None,
        metadata={"example": "default", "description": "The volume type: default, oracle."},
    )


class BlockDeviceMappingApiRequestSchema(Schema):
    DeviceName = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "/dev/sdh", "description": "The device name (for example, /dev/sdh or xvdh)."},
    )

    Ebs = fields.Nested(
        EbsBlockDeviceMappingApiRequestSchema,
        required=False,
        allow_none=True,
        metadata={"description": "Parameters used to automatically set up EBS volumes when the instance is launched."},
    )

    NoDevice = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "Suppresses the specified device included in the block device mapping of the AMI."},
    )

    VirtualName = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "example": "/dev/sdh",
            "description": (
                "The virtual device name (ephemeralN). Instance store volumes are "
                "numbered starting from 0. An instance type with 2 available instance "
                "store volumes can specify mappings for ephemeral0 and ephemeral1. "
                "The number of available instance store volumes depends on the instance type. "
                "After you connect to the instance, you must mount the volume."
            ),
        },
    )


class TagRequestSchema(Schema):
    Key = fields.String(required=True, validate=Length(max=127), metadata={"description": "tag key"})
    # Value = fields.String(required=False, validate=Length(max=255), example='', description='tag value')

    @validates_schema
    def validate_unsupported_parameters(self, data, *args, **kvargs):
        keys = data.keys()
        if "Value" in keys:
            raise ValidationError(
                "Parameters Tags.Value is not supported. Can be used only the parameter " "Parameters Tags.Key"
            )


class TagSpecificationMappingApiRequestSchema(Schema):
    ResourceType = fields.String(
        required=False,
        load_default=__SRV_AWS_TAGS_RESOURCE_TYPE_INSTANCE__,
        validate=OneOf([__SRV_AWS_TAGS_RESOURCE_TYPE_INSTANCE__]),
        metadata={"description": "type of resource to tag"},
    )

    Tags = fields.Nested(
        TagRequestSchema,
        load_default=[],
        required=False,
        many=True,
        allow_none=False,
        metadata={"description": "list of tags to apply to the resource"},
    )


class RunInstancesApiParamRequestSchema(Schema):
    Name = fields.String(
        required=False,
        allow_none=True,
        load_default="default istance name",
        metadata={"description": "instance name"},
    )

    AdditionalInfo = fields.String(required=False, allow_none=True, metadata={"description": "instance description"})

    SubnetId = fields.String(
        required=False,
        metadata={"example": "12", "description": "instance id or uuid of the subnet"},
    )

    # AccountId managed by AWS Wrapper
    owner_id = fields.String(
        required=True,
        data_key="owner-id",
        metadata={"example": "1", "description": "account id or uuid associated to compute zone"},
    )

    # PlacementAvailabilityZone managed by AWS Wrapper
    # PlacementAvailabilityZone = fields.String(required=False, default='')
    InstanceType = fields.String(
        required=True,
        metadata={"example": "small2", "description": "service definition of the instance"},
    )

    AdminPassword = fields.String(
        required=False,
        metadata={"example": "myPwd1$", "description": "admin password to set"},
    )

    ImageId = fields.String(
        required=True,
        metadata={"example": "12", "description": "instance id or uuid of the image"},
    )

    SecurityGroupId_N = fields.List(
        fields.String(example="12"),
        required=False,
        allow_none=False,
        data_key="SecurityGroupId.N",
        metadata={"description": "list of instance security group ids"},
    )

    KeyName = fields.String(required=False, metadata={"example": "1ffd", "description": "The name of the key pair"})

    BlockDeviceMapping_N = fields.Nested(
        BlockDeviceMappingApiRequestSchema,
        required=False,
        many=True,
        data_key="BlockDeviceMapping.N",
        allow_none=True,
    )

    Nvl_Hypervisor = fields.String(
        load_default="openstack",
        required=False,
        validate=OneOf(["openstack", "vsphere"]),
        metadata={"example": "openstack", "description": "hypervisor type"},
    )

    Nvl_Metadata = fields.Dict(
        allow_none=True,
        required=False,
        metadata={"example": '{"cluster":"","dvp":""}', "description": "custom configuration keys"},
    )

    Nvl_MultiAvz = fields.Boolean(
        load_default=True,
        required=False,
        metadata={"example": True, "description": "Define if instance must be deployed to work in all the availability "
        "zone or only in the selected one"},
    )

    Nvl_HostGroup = fields.String(
        load_default=None,
        required=False,
        metadata={"example": "oracle", "description": "hypervisor host group"},
    )


class RunInstancesApiRequestSchema(Schema):
    instance = fields.Nested(RunInstancesApiParamRequestSchema, context="body")


class RunInstancesApiBodyRequestSchema(Schema):
    body = fields.Nested(RunInstancesApiRequestSchema, context="body")


class RunInstancesApi3ResponseSchema(Schema):
    code = fields.Integer(required=False, dump_default=0)
    name = fields.String(required=True, metadata={"example": "PENDING"})


class RunInstancesApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True)
    currentState = fields.Nested(RunInstancesApi3ResponseSchema, required=True)


class RunInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    instancesSet = fields.Nested(RunInstancesApi2ResponseSchema, many=True, required=True)


class RunInstancesApiResponseSchema(Schema):
    RunInstanceResponse = fields.Nested(RunInstancesApi1ResponseSchema, required=True)


class RunInstances(ServiceApiView):
    summary = "Create compute instance"
    description = "Create compute instance"
    tags = ["computeservice"]
    definitions = {
        "RunInstancesApiRequestSchema": RunInstancesApiRequestSchema,
        "RunInstancesApiResponseSchema": RunInstancesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(RunInstancesApiBodyRequestSchema)
    parameters_schema = RunInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": RunInstancesApiResponseSchema}})

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        inner_data = data.get("instance")

        service_definition_id = inner_data.get("InstanceType")
        account_id = inner_data.get("owner_id")
        name = inner_data.get("Name")
        if name is None:
            raise ApiManagerWarning("The Name of the VM cannot be None")

        desc = inner_data.get("AdditionalInfo")
        if desc is None:
            desc = ""

        block_device_mappings = inner_data.get("BlockDeviceMapping_N")
        if block_device_mappings is None or len(block_device_mappings) == 0:
            raise ApiManagerWarning("BlockDeviceMapping_N cannot be None, should be provided with EBS information")

        # check instance with the same name already exists
        # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account: ApiAccount
        parent_plugin: ApiComputeService

        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiComputeService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid


        # check service definition
        service_defs, total = controller.get_paginated_service_defs(
            service_definition_uuid_list=[service_definition_id],
            plugintype=ApiComputeInstance.plugintype,
        )

        self.logger.warn(service_defs)
        if total < 1:
            raise ApiManagerError("InstanceType is wrong")

        # create service instance
        inst = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        instances_set = [
            {
                "instanceId": inst.instance.uuid,
                "currentState": {"name": inst.instance.status},
            }
        ]
        res = self.format_create_response("RunInstanceResponse", instances_set)

        return res, 202


class ModifyInstanceAttribute1ResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True, metadata={"example": "Request id"})
    return_status = fields.Boolean(required=True, allow_none=True, data_key="return", metadata={"example": True})
    xmlns = fields.String(required=False, data_key="__xmlns")


class ModifyInstanceAttributeResponseSchema(Schema):
    ModifyInstanceAttributeResponse = fields.Nested(
        ModifyInstanceAttribute1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class ModifyInstanceAttribute1UserRequestSchema(Schema):
    Nvl_Action = fields.String(
        required=True,
        validate=OneOf(["add", "delete", "set-password"]),
        metadata={"example": "add", "description": "Instance user action. Can be add, delete or set-password"},
    )

    Nvl_Name = fields.String(required=True, metadata={"example": "test", "description": "The instance user name"})

    Nvl_Password = fields.String(
        required=False,
        metadata={"example": "test", "description": "The instance user password. Required with action add and set-password"},
    )

    Nvl_SshKey = fields.String(
        required=False,
        metadata={"example": "test", "description": "The instance user ssh key id. Required with action add"},
    )


class ModifyInstanceAttribute1RequestSchema(Schema):
    InstanceId = fields.String(
        required=True,
        metadata={"example": "ce72f656-4c97-4ce7-8bb4-5da60daedc81", "description": "The ID of the instance."},
    )

    InstanceType = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "example": "ce72f656-4c97-4ce7-8bb4-5da60daedc81",
            "description": (
                "Changes the instance type to the specified value. For more information, "
                "see Instance Types. If the instance type is not valid, the error "
                "returned is InvalidInstanceAttributeValue."
            ),
        },
    )

    GroupId_N = fields.List(
        fields.String(example="12"),
        required=False,
        allow_none=False,
        data_key="GroupId.N",
        metadata={
            "description": (
                "Changes the security groups of the instance. You must specify only one "
                "security group id followed by :ADD to add and :DEL to remove"
            ),
        },
    )

    Nvl_User = fields.Nested(
        ModifyInstanceAttribute1UserRequestSchema,
        required=False,
        many=False,
        allow_none=True,
        metadata={"description": "Manage instance user: add, delete, change password"},
    )


class ModifyInstanceAttributeRequestSchema(Schema):
    instance = fields.Nested(ModifyInstanceAttribute1RequestSchema, context="body")


class ModifyInstanceAttributeBodyRequestSchema(Schema):
    body = fields.Nested(ModifyInstanceAttributeRequestSchema, context="body")


class ModifyInstanceAttribute(ServiceApiView):
    summary = "Modify compute instance"

    description = (
        "Modify compute instance. Modifies the specified attribute of the specified instance. You can "
        "specify only one attribute at a time. To modify some attributes, the instance must be stopped."
    )

    tags = ["computeservice"]

    definitions = {
        "ModifyInstanceAttributeRequestSchema": ModifyInstanceAttributeRequestSchema,
        "ModifyInstanceAttributeResponseSchema": ModifyInstanceAttributeResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(ModifyInstanceAttributeBodyRequestSchema)
    parameters_schema = ModifyInstanceAttributeRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": ModifyInstanceAttributeResponseSchema,
            }
        }
    )

    response_schema = ModifyInstanceAttributeResponseSchema

    def put(self, controller: ServiceController, data, *args, **kwargs):
        data = data.get("instance")
        instance_id = data.pop("InstanceId")
        type_plugin: ApiComputeInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.update(**data)

        res = {
            "ModifyInstanceAttributeResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": True,
            }
        }
        return res, 202


class StateInstancesApi2ResponseSchema(Schema):
    currentState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)
    instanceId = fields.String(required=False, metadata={"description": "instance ID"})
    previousState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)


class StateInstancesApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    instancesSet = fields.Nested(StateInstancesApi2ResponseSchema, required=True, many=True, allow_none=True)


class StartInstancesApiResponseSchema(Schema):
    StartInstancesResponse = fields.Nested(
        StateInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class StartInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    Schedule = fields.Dict(
        required=False,
        load_default=None,
        metadata={"description": "schedule to use when you want to run a scheduled " "action"},
    )


class StartInstancesBodyRequestSchema(Schema):
    body = fields.Nested(StartInstancesApiRequestSchema, context="body")


class StartInstances(ServiceApiView):
    summary = "Start compute instance"
    description = "Start compute instance"
    tags = ["computeservice"]

    definitions = {
        "StartInstancesApiRequestSchema": StartInstancesApiRequestSchema,
        "StartInstancesApiResponseSchema": StartInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(StartInstancesBodyRequestSchema)
    parameters_schema = StartInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": StartInstancesApiResponseSchema}}
    )

    response_schema = StartInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        schedule = data.pop("Schedule")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.start(schedule=schedule)
            instances_set.append({"instanceId": instance_id})

        res = {
            "StartInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class StopInstancesApiResponseSchema(Schema):
    StopInstancesResponse = fields.Nested(StateInstancesApi1ResponseSchema, required=True, many=False, allow_none=False)


class StopInstancesApiRequestSchema(Schema):
    Force = fields.Boolean(
        required=False,
        allow_none=True,
        load_default=False,
        metadata={
            "description": (
                "Forces the instances to stop. The instances do not have an opportunity to "
                "flush file system caches or file system metadata. If you use this option, you "
                "must perform file system check and repair procedures."
            )
        },
    )

    Hibernate = fields.Boolean(
        required=False,
        allow_none=True,
        load_default=False,
        metadata={
            "description": (
                "Hibernates the instance if the instance was enabled for hibernation at "
                "launch. If the instance cannot hibernate successfully, a normal shutdown occurs."
            )
        },
    )

    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id list"},
    )

    Schedule = fields.Dict(
        required=False,
        load_default=None,
        metadata={"description": "schedule to use when you want to run a scheduled " "action"},
    )


class StopInstancesBodyRequestSchema(Schema):
    body = fields.Nested(StopInstancesApiRequestSchema, context="body")


class StopInstances(ServiceApiView):
    summary = "Stop compute instance"
    description = "Stop compute instance"
    tags = ["computeservice"]

    definitions = {
        "StopInstancesApiRequestSchema": StopInstancesApiRequestSchema,
        "StopInstancesApiResponseSchema": StopInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(StopInstancesBodyRequestSchema)
    parameters_schema = StopInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": StopInstancesApiResponseSchema}})
    response_schema = StopInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        schedule = data.pop("Schedule")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.stop(schedule=schedule)
            instances_set.append({"instanceId": instance_id})

        res = {
            "StopInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class RebootInstancesApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    req_return = fields.Boolean(required=True, data_key="return", metadata={"example": True})


class RebootInstancesApiResponseSchema(Schema):
    RebootInstancesResponse = fields.Nested(
        RebootInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class RebootInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id list"},
    )

    Schedule = fields.Dict(
        required=False,
        load_default=None,
        metadata={"description": "schedule to use when you want to run a scheduled action"},
    )


class RebootInstancesBodyRequestSchema(Schema):
    body = fields.Nested(RebootInstancesApiRequestSchema, context="body")


class RebootInstances(ServiceApiView):
    summary = "Reboot compute instance"
    description = "Reboot compute instance"
    tags = ["computeservice"]

    definitions = {
        "RebootInstancesApiRequestSchema": RebootInstancesApiRequestSchema,
        "RebootInstancesApiResponseSchema": RebootInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(RebootInstancesBodyRequestSchema)
    parameters_schema = RebootInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": RebootInstancesApiResponseSchema}}
    )

    response_schema = RebootInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        schedule = data.pop("Schedule")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.reboot(schedule=schedule)
            instances_set.append({"instanceId": instance_id})

        res = {
            "RebootInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": True,
            }
        }
        return res


class TerminateInstancesResponseItemSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True)
    instancesSet = fields.Nested(StateInstancesApi2ResponseSchema, required=True, many=True, allow_none=True)
    nvl_return = fields.Boolean(required=True, data_key="nvl-return", metadata={"example": True})


class TerminateInstancesResponseSchema(Schema):
    TerminateInstancesResponse = fields.Nested(
        TerminateInstancesResponseItemSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class TerminateInstancesRequestSchema(Schema):
    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id list"},
    )


class TerminateInstancesBodyRequestSchema(Schema):
    body = fields.Nested(TerminateInstancesRequestSchema, context="body")


class TerminateInstances(ServiceApiView):
    summary = "Terminate compute instance"
    description = "Terminate compute instance"
    tags = ["computeservice"]

    definitions = {
        "TerminateInstancesRequestSchema": TerminateInstancesRequestSchema,
        "TerminateInstancesResponseSchema": TerminateInstancesResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(TerminateInstancesBodyRequestSchema)
    parameters_schema = TerminateInstancesRequestSchema

    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": TerminateInstancesResponseSchema}}
    )

    response_schema = TerminateInstancesResponseSchema

    def delete(self, controller: ServiceController, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")

        instances_set = []
        for instance_id in instance_ids:
            type_plugin: ApiComputeInstance = controller.get_service_type_plugin(instance_id)
            type_plugin.delete()
            instances_set.append({"instanceId": instance_id})

        res = {
            "TerminateInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
                "nvl-return": True,
            }
        }

        return res, 202


class SnapshotsResponseSchema(Schema):
    snapshotId = fields.String(required=True, metadata={"example": "123", "description": "snapshot ID"})
    snapshotStatus = fields.String(required=True, metadata={"description": "snapshot status"})
    snapshotName = fields.String(required=True, metadata={"example": "prova", "description": "snapshot name"})
    createTime = fields.String(required=True, metadata={"description": "the timestamp the snapshot was created"})


class DescribeInstanceSnapshotsApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True, metadata={"description": "instance ID"})
    snapshots = fields.Nested(
        SnapshotsResponseSchema,
        many=True,
        required=True,
        metadata={"description": "list of snapshots"},
    )


class DescribeInstanceSnapshotsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(DescribeInstanceSnapshotsApi2ResponseSchema, required=True, many=True, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class DescribeInstanceSnapshotsApiResponseSchema(Schema):
    DescribeInstanceSnapshotsResponse = fields.Nested(
        DescribeInstanceSnapshotsApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeInstanceSnapshotsApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        context="query",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        context="query",
        metadata={"description": "instance id"},
    )


class DescribeInstanceSnapshots(ServiceApiView):
    summary = "List instance snapshots"
    description = "List instance snapshots"
    tags = ["computeservice"]

    definitions = {
        "DescribeInstanceSnapshotsApiRequestSchema": DescribeInstanceSnapshotsApiRequestSchema,
        "DescribeInstanceSnapshotsApiResponseSchema": DescribeInstanceSnapshotsApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeInstanceSnapshotsApiRequestSchema)
    parameters_schema = DescribeInstanceSnapshotsApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": DescribeInstanceSnapshotsApiResponseSchema,
            }
        }
    )

    response_schema = DescribeInstanceSnapshotsApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            snapshots = type_plugin.get_snapshots()
            instances_set.append({"instanceId": instance_id, "snapshots": snapshots})

        res = {
            "DescribeInstanceSnapshotsResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class CreateInstanceSnapshotsApi2ResponseSchema(Schema):
    instanceId = fields.String(required=False, metadata={"description": "instance ID"})
    snapshotName = fields.String(required=False, metadata={"description": "snapshot name"})


class CreateInstanceSnapshotsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(CreateInstanceSnapshotsApi2ResponseSchema, required=True, many=True, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class CreateInstanceSnapshotsApiResponseSchema(Schema):
    CreateInstanceSnapshotsResponse = fields.Nested(
        CreateInstanceSnapshotsApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )

class CreateInstanceSnapshotsApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    SnapshotName = fields.String(required=False, load_default=None, metadata={"description": "snapshot name"})


class CreateInstanceSnapshotsBodyRequestSchema(Schema):
    body = fields.Nested(CreateInstanceSnapshotsApiRequestSchema, context="body")


class CreateInstanceSnapshots(ServiceApiView):
    summary = "Add instance snapshots"
    description = "Add instance snapshots"
    tags = ["computeservice"]

    definitions = {
        "CreateInstanceSnapshotsApiRequestSchema": CreateInstanceSnapshotsApiRequestSchema,
        "CreateInstanceSnapshotsApiResponseSchema": CreateInstanceSnapshotsApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(CreateInstanceSnapshotsBodyRequestSchema)
    parameters_schema = CreateInstanceSnapshotsApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": CreateInstanceSnapshotsApiResponseSchema,
            }
        }
    )

    response_schema = CreateInstanceSnapshotsApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        snapshot = data.pop("SnapshotName")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.add_snapshot(snapshot)
            instances_set.append({"instanceId": instance_id, "snapshotName": snapshot})

        res = {
            "CreateInstanceSnapshotsResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class DeleteInstanceSnapshotsApi2ResponseSchema(Schema):
    instanceId = fields.String(required=False, metadata={"description": "instance ID"})
    snapshotId = fields.String(required=False, metadata={"description": "snapshot ID"})


class DeleteInstanceSnapshotsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(DeleteInstanceSnapshotsApi2ResponseSchema, required=True, many=True, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class DeleteInstanceSnapshotsApiResponseSchema(Schema):
    DeleteInstanceSnapshotsResponse = fields.Nested(
        DeleteInstanceSnapshotsApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteInstanceSnapshotsApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    SnapshotId = fields.String(required=False, load_default=None, metadata={"description": "snapshot id"})


class DeleteInstanceSnapshotsBodyRequestSchema(Schema):
    body = fields.Nested(DeleteInstanceSnapshotsApiRequestSchema, context="body")


class DeleteInstanceSnapshots(ServiceApiView):
    summary = "Delete instance snapshots"
    description = "Delete instance snapshots"
    tags = ["computeservice"]

    definitions = {
        "DeleteInstanceSnapshotsApiRequestSchema": DeleteInstanceSnapshotsApiRequestSchema,
        "DeleteInstanceSnapshotsApiResponseSchema": DeleteInstanceSnapshotsApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DeleteInstanceSnapshotsBodyRequestSchema)
    parameters_schema = DeleteInstanceSnapshotsApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": DeleteInstanceSnapshotsApiResponseSchema,
            }
        }
    )

    response_schema = DeleteInstanceSnapshotsApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        snapshot = data.pop("SnapshotId")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.del_snapshot(snapshot)
            instances_set.append({"instanceId": instance_id, "snapshotId": snapshot})

        res = {
            "DeleteInstanceSnapshotsResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class RevertInstanceSnapshotsApi2ResponseSchema(Schema):
    instanceId = fields.String(required=False, metadata={"description": "instance ID"})
    snapshotId = fields.String(required=False, metadata={"description": "snapshot ID"})


class RevertInstanceSnapshotsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(RevertInstanceSnapshotsApi2ResponseSchema, required=True, many=True, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class RevertInstanceSnapshotsApiResponseSchema(Schema):
    RevertInstanceSnapshotsResponse = fields.Nested(
        RevertInstanceSnapshotsApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class RevertInstanceSnapshotsApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    SnapshotId = fields.String(required=False, load_default=None, metadata={"description": "snapshot id"})


class RevertInstanceSnapshotsBodyRequestSchema(Schema):
    body = fields.Nested(RevertInstanceSnapshotsApiRequestSchema, context="body")


class RevertInstanceSnapshots(ServiceApiView):
    summary = "Revert instance to snapshot"
    description = "Revert instance to snapshot"
    tags = ["computeservice"]

    definitions = {
        "RevertInstanceSnapshotsApiRequestSchema": RevertInstanceSnapshotsApiRequestSchema,
        "RevertInstanceSnapshotsApiResponseSchema": RevertInstanceSnapshotsApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(RevertInstanceSnapshotsBodyRequestSchema)
    parameters_schema = RevertInstanceSnapshotsApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": RevertInstanceSnapshotsApiResponseSchema,
            }
        }
    )

    response_schema = RevertInstanceSnapshotsApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        snapshot = data.pop("SnapshotId")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.revert_snapshot(snapshot)
            instances_set.append({"instanceId": instance_id, "snapshotId": snapshot})

        res = {
            "RevertInstanceSnapshotsResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class MonitorInstancesApi3ResponseSchema(Schema):
    state = fields.String(required=True, metadata={"example": "pending", "description": "monitoring state"})


class MonitorInstancesApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True, metadata={"description": "instance ID"})
    monitoring = fields.Nested(MonitorInstancesApi3ResponseSchema, required=True, allow_none=True)


class MonitorInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(MonitorInstancesApi2ResponseSchema, required=True, allow_none=True)


class MonitorInstancesApiResponseSchema(Schema):
    MonitorInstancesResponse = fields.Nested(
        StateInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class MonitorInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    Nvl_Templates = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        load_default=None,
        metadata={"description": "List of monitoring template"},
    )


class MonitorInstancesBodyRequestSchema(Schema):
    body = fields.Nested(MonitorInstancesApiRequestSchema, context="body")


class MonitorInstances(ServiceApiView):
    summary = "Enables detailed monitoring for a running instance. Otherwise, basic monitoring is enabled."
    description = "Enables detailed monitoring for a running instance. Otherwise, basic monitoring is enabled."
    tags = ["computeservice"]

    definitions = {
        "MonitorInstancesApiRequestSchema": MonitorInstancesApiRequestSchema,
        "MonitorInstancesApiResponseSchema": MonitorInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(MonitorInstancesBodyRequestSchema)
    parameters_schema = MonitorInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": MonitorInstancesApiResponseSchema}}
    )

    response_schema = MonitorInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        templates = data.pop("Nvl_Templates")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.enable_monitoring(templates)
            instances_set.append({"instanceId": instance_id, "monitoring": {"state": "pending"}})

        res = {
            "MonitorInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class UnmonitorInstancesApiResponseSchema(MonitorInstancesApiResponseSchema):
    pass


class UnmonitorInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )


class UnmonitorInstancesBodyRequestSchema(Schema):
    body = fields.Nested(UnmonitorInstancesApiRequestSchema, context="body")


class UnmonitorInstances(ServiceApiView):
    summary = "Disables detailed monitoring for a running instance."
    description = "Disables detailed monitoring for a running instance."
    tags = ["computeservice"]

    definitions = {
        "UnmonitorInstancesApiRequestSchema": UnmonitorInstancesApiRequestSchema,
        "UnmonitorInstancesApiResponseSchema": UnmonitorInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(UnmonitorInstancesBodyRequestSchema)
    parameters_schema = UnmonitorInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": UnmonitorInstancesApiResponseSchema}}
    )

    response_schema = UnmonitorInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.disable_monitoring()
            instances_set.append({"instanceId": instance_id, "monitoring": {"state": "pending"}})

        res = {
            "UnmonitorInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class ForwardLogInstancesApi3ResponseSchema(Schema):
    state = fields.String(required=True, metadata={"example": "pending", "description": "logging state"})


class ForwardLogInstancesApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True, metadata={"description": "instance ID"})
    logging = fields.Nested(ForwardLogInstancesApi3ResponseSchema, required=True, allow_none=True)


class ForwardLogInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, dump_default="", allow_none=True)
    instancesSet = fields.Nested(ForwardLogInstancesApi2ResponseSchema, required=True, many=True, allow_none=True)


class ForwardLogInstancesApiResponseSchema(Schema):
    ForwardLogInstancesResponse = fields.Nested(
        StateInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class ForwardLogInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the instance owner"},
    )

    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="InstanceId.N",
        metadata={"description": "instance id"},
    )

    Files = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        load_default=None,
        metadata={"description": "List of files to forward"},
    )

    Pipeline = fields.Integer(
        required=False,
        allow_none=True,
        load_default=5044,
        metadata={"description": "Log collector pipeline port"},
    )


class ForwardLogInstancesBodyRequestSchema(Schema):
    body = fields.Nested(ForwardLogInstancesApiRequestSchema, context="body")


class ForwardLogInstances(ServiceApiView):
    summary = "Enables log forwarding from a running instance to a log collector. [DEPRECATED]"
    description = "Enables log forwarding from a running instance to a log collector. [DEPRECATED]"
    tags = ["computeservice"]

    definitions = {
        "ForwardLogInstancesApiRequestSchema": ForwardLogInstancesApiRequestSchema,
        "ForwardLogInstancesApiResponseSchema": ForwardLogInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(ForwardLogInstancesBodyRequestSchema)
    parameters_schema = ForwardLogInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": ForwardLogInstancesApiResponseSchema,
            }
        }
    )

    response_schema = ForwardLogInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("InstanceId_N")
        files = data.pop("Files")
        pipeline = data.pop("Pipeline")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            type_plugin.enable_logging(files, pipeline)
            instances_set.append({"instanceId": instance_id, "logging": {"state": "pending"}})

        res = {
            "ForwardLogInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class ComputeInstanceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/computeservices/instance"
        rules = [
            # instance
            ("%s/describeinstances" % base, "GET", DescribeInstances, {}),
            ("%s/runinstances" % base, "POST", RunInstances, {}),
            ("%s/modifyinstanceattribute" % base, "PUT", ModifyInstanceAttribute, {}),
            ("%s/terminateinstances" % base, "DELETE", TerminateInstances, {}),
            ("%s/startinstances" % base, "PUT", StartInstances, {}),
            ("%s/stopinstances" % base, "PUT", StopInstances, {}),
            ("%s/rebootinstances" % base, "PUT", RebootInstances, {}),
            # instance types
            ("%s/describeinstancetypes" % base, "GET", DescribeInstanceTypes, {}),
            # instance snapshot
            (
                "%s/describeinstancesnapshots" % base,
                "GET",
                DescribeInstanceSnapshots,
                {},
            ),
            ("%s/createinstancesnapshots" % base, "PUT", CreateInstanceSnapshots, {}),
            ("%s/deleteinstancesnapshots" % base, "PUT", DeleteInstanceSnapshots, {}),
            ("%s/revertinstancesnapshots" % base, "PUT", RevertInstanceSnapshots, {}),
            # instance monitoring
            ("%s/monitorinstances" % base, "PUT", MonitorInstances, {}),
            ("%s/unmonitorinstances" % base, "PUT", UnmonitorInstances, {}),
            # instance forward log
            ("%s/forwardloginstances" % base, "PUT", ForwardLogInstances, {}),
            # ('%s/unforwardloginstances' % base, 'PUT', UnforwardLogInstances, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
