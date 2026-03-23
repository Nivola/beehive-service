# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from flasgger import fields, Schema

from beehive.common.apimanager import ApiView
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from flasgger.marshmallow_apispec import fields
from marshmallow.validate import OneOf
from beehive_service.controller import ApiAccount, ServiceController
from beehive_service.plugins.computeservice.controller import (
    ApiComputeImage,
    ApiComputeService,
)
from beehive_service.service_util import __ARCHITECTURE__


class InstanceTagSetResponseSchema(Schema):
    key = fields.String(required=False, allow_none=True, metadata={"description": "tag key"})
    value = fields.String(required=False, allow_none=True, metadata={"description": "tag value"})


class InstancestatusReasonResponseSchema(Schema):
    code = fields.String(required=False, allow_none=True, metadata={"description": "reason code for the state change"})
    message = fields.String(required=False, allow_none=True, metadata={"description": "message for the state change"})


class ImageProductCodesResponseSchema(Schema):
    productCode = fields.String(required=False, allow_none=True, metadata={"description": "product code"})
    type = fields.String(required=False, allow_none=True, metadata={"description": "type of product code"})


class ImageBlockDeviceMappingItem1ResponseSchema(Schema):
    deleteOnTermination = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "boolean to know if the volume is deleted " "on instance termination"},
    )
    encrypted = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "indicates whether the volume is encrypted"},
    )
    iops = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "number of I/O operations per second (IOPS) that the volume support"},
    )
    KmsKeyId = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": " key id for a user-managed CMK under which the volume is encrypted."},
    )
    snapshotId = fields.String(required=False, allow_none=True, metadata={"description": "ID of the snapshot."})
    volumeSize = fields.Integer(required=False, allow_none=True, metadata={"description": "size of the volume, in GiB"})
    volumeType = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(["gp2", "io1", "st1", "sc1", "standard"]),
        metadata={"description": "type of the volume"},
    )


class ImageBlockDeviceMappingResponseSchema(Schema):
    deviceName = fields.String(required=False, allow_none=True, metadata={"description": "device name"})
    ebs = fields.Nested(ImageBlockDeviceMappingItem1ResponseSchema, many=False, required=False)
    noDevice = fields.List(
        fields.String(),
        required=False,
        metadata={"description": "suppresses the specified device included " "in the block device mapping of the AMI"},
    )
    virtualName = fields.List(fields.String(), required=False, metadata={"description": "virtual device names"})


class ImageItemParameterResponseSchema(Schema):
    # NOT SUPPORTED
    architecture = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(__ARCHITECTURE__),
        metadata={"description": "architecture of the image"},
    )
    blockDeviceMapping = fields.Nested(
        ImageBlockDeviceMappingResponseSchema,
        required=False,
        many=True,
        allow_none=True,
        metadata={"description": "block device mapping"},
    )
    creationDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "image date creation"})
    description = fields.String(required=False, allow_none=True, metadata={"description": "image description"})
    enaSupport = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "indicates whether the ENA enhanced networking is enabled"},
    )
    hypervisor = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "openstack,vsphere", "description": "type of the hypervisor"},
    )
    imageId = fields.String(required=False, allow_none=True, metadata={"description": "image instance id"})
    imageLocation = fields.String(required=False, allow_none=True, metadata={"description": "image location"})
    imageOwnerAlias = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "account alias of the AMI owner"},
    )
    imageOwnerId = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "account id of the image owner"},
    )
    # ['pending', 'available', 'invalid', 'deregistered', 'transient', 'failed', 'error']
    imageState = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            [getattr(ApiComputeImage.state_enum, x) for x in dir(ApiComputeImage.state_enum) if not x.startswith("__")]
        ),
        metadata={"description": "state of image"},
    )
    imageType = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(["machine", "kernel", "ramdisk"]),
        metadata={"description": "type of image"},
    )
    isPublic = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "indicates whether the image is public"},
    )
    kernelId = fields.String(required=False, allow_none=True, metadata={"description": "kernel id of the image"})
    name = fields.String(required=False, allow_none=True, metadata={"description": "image name"})
    platform = fields.String(required=False, allow_none=True, metadata={"description": "platform"})
    productCodes = fields.Nested(
        ImageProductCodesResponseSchema,
        many=True,
        required=False,
        allow_none=True,
        metadata={"description": "array of ProductCode objects"},
    )
    ramdiskId = fields.String(required=False, allow_none=True, metadata={"description": "ram disk for the image"})
    rootDeviceName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "type of root device used by the AMI"},
    )
    rootDeviceType = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "rtype of root device used by the AMI"},
    )
    sriovNetSupport = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "indicates whether the Intel 82599 Virtual enhanced networking is " "enabled"},
    )
    stateReason = fields.Nested(
        InstancestatusReasonResponseSchema,
        many=False,
        required=False,
        allow_none=False,
        metadata={"description": "array of status reason"},
    )
    tagSet = fields.Nested(InstanceTagSetResponseSchema, many=True, required=False, allow_none=True)
    virtualizationType = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "hvm | paravirtual", "description": "virtualization type of the instance"},
    )
    nvl_resourceId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-resourceId",
        metadata={"description": "resource id"},
    )
    nvl_minDiskSize = fields.Integer(
        required=False,
        allow_none=True,
        data_key="nvl-minDiskSize",
        metadata={"description": "minimum image disk size"},
    )


class DescribeImagesResponse1Schema(Schema):
    requestId = fields.String(required=True, allow_none=True, metadata={"description": ""})
    imagesSet = fields.Nested(ImageItemParameterResponseSchema, many=True, required=False)
    xmlns = fields.String(required=False, data_key="$xmlns")
    nvl_imageTotal = fields.Integer(
        required=False,
        data_key="nvl-imageTotal",
        metadata={"description": "total number of items"},
    )


class DescribeImagesResponseSchema(Schema):
    DescribeImagesResponse = fields.Nested(DescribeImagesResponse1Schema, required=True, many=False, allow_none=False)


class DescribeImagesRequestSchema(Schema):
    image_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="image-id.N",
        metadata={"description": "image id"},
    )

    imageId_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="ImageId.N",
        metadata={"description": "image id"},
    )

    name_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="name.N",
        metadata={"description": "name of the AMI"},
    )

    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account ID of the image owner"},
    )

    state_N = fields.List(
        fields.String(example="", validate=OneOf(["pending", "available", "failed"])),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="state.N",
        metadata={"description": "state of the image (pending | available | failed)"},
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

    Nvl_MaxResults = fields.Integer(
        required=False,
        dump_default=10,
        data_key="Nvl-MaxResults",
        context="query",
    )

    Nvl_NextToken = fields.String(
        required=False,
        dump_default="0",
        data_key="Nvl-NextToken",
        context="query",
    )


class DescribeImages(ServiceApiView):
    summary = "Describe compute image"
    description = "Describe compute image"
    tags = ["computeservice"]
    definitions = {"DescribeImagesResponseSchema": DescribeImagesResponseSchema}
    parameters = SwaggerHelper().get_parameters(DescribeImagesRequestSchema)
    parameters_schema = DescribeImagesRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": DescribeImagesResponseSchema}})
    response_schema = DescribeImagesResponseSchema

    def get(self, controller, data, *args, **kwargs):
        data_search = {}
        data_search["size"] = data.get("Nvl_MaxResults", 10)
        data_search["page"] = int(data.get("Nvl_NextToken", 0))

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("image_id_N", [])
        instance_id_list.extend(data.get("imageId_N", []))

        # get instance name
        instance_name_list = data.get("name_N", [])

        # get tags
        tag_values = data.get("tag_key_N", None)

        # get status
        status_mapping = {
            "pending": SrvStatusType.PENDING,
            "available": SrvStatusType.ACTIVE,
            "failed": SrvStatusType.ERROR,
        }

        status_name_list = None
        status_list = data.get("state_N", None)
        if status_list is not None:
            status_name_list = [status_mapping[i] for i in status_list if i in status_mapping.keys()]

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            account_id_list=account_id_list,
            servicetags_or=tag_values,
            service_status_name_list=status_name_list,
            plugintype=ApiComputeImage.plugintype,
            **data_search,
        )

        # format result
        instances_set = [r.aws_info() for r in res]

        res = {
            "DescribeImagesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "imagesSet": instances_set,
                "nvl-imageTotal": total,
            }
        }
        return res


class CreateImageApiResponse1Schema(Schema):
    # groupId = fields.String(required=False, allow_none=False)
    imageId = fields.String(required=True, allow_none=False)
    requestId = fields.String(required=True, allow_none=True)
    xmlns = fields.String(required=False, allow_none=True, data_key="__xmlns")


class CreateImageApiResponseSchema(Schema):
    CreateImageResponse = fields.Nested(CreateImageApiResponse1Schema, required=True, allow_none=False)


class CreateImageApiParamRequestSchema(Schema):
    owner_id = fields.String(required=True, data_key="owner_id", metadata={"description": "account id"})
    ImageName = fields.String(required=True, metadata={"description": "name of the image"})
    ImageDescription = fields.String(required=False, metadata={"description": "description of the image"})
    ImageType = fields.String(
        required=False,
        load_default="--DEFAULT--image",
        metadata={"description": "image template"},
    )


class CreateImageApiRequestSchema(Schema):
    image = fields.Nested(CreateImageApiParamRequestSchema, context="body")


class CreateImageApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateImageApiRequestSchema, context="body")


class CreateImage(ServiceApiView):
    summary = "Create a compute image"
    description = "Create a compute image"
    tags = ["computeservice"]
    definitions = {
        "CreateImageApiRequestSchema": CreateImageApiRequestSchema,
        "CreateImageApiResponseSchema": CreateImageApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateImageApiBodyRequestSchema)
    parameters_schema = CreateImageApiRequestSchema
    responses = ServiceApiView.setResponses({202: {"description": "success", "schema": CreateImageApiResponseSchema}})
    response_schema = CreateImageApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        inner_data = data.get("image")
        service_definition_id = inner_data.get("ImageType")
        account_id = inner_data.get("owner_id")
        name = inner_data.get("ImageName")
        desc = inner_data.get("ImageDescription", name)

        # check instance with the same name already exists
        # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account: ApiAccount
        parent_plugin: ApiComputeService
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
            "CreateImageResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "imageId": inst.instance.uuid,
            }
        }
        self.logger.debug("Service Aws response: %s" % res)

        return res, 202


class ComputeImageAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            # image
            (
                "%s/computeservices/image/describeimages" % base,
                "GET",
                DescribeImages,
                {},
            ),
            ("%s/computeservices/image/createimage" % base, "POST", CreateImage, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
