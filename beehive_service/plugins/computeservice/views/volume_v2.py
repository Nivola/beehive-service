# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from flasgger import fields, Schema
from beecell.simple import id_gen, format_date
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
from .volume import (
    AttachVolume,
    CreateVolume,
    DeleteVolume,
    DescribeVolumes,
    DetachVolume,
)


class AttachVolumeV20(AttachVolume):
    pass


class CreateVolumeV20(CreateVolume):
    pass


class DeleteVolumeV20(DeleteVolume):
    pass


class DescribeVolumesV20(DescribeVolumes):
    pass


class DetachVolumeV20(DetachVolume):
    pass


class InstanceTypeFeatureResponseSchema(Schema):
    vcpus = fields.String(required=False, allow_none=True, metadata={"description": ""})
    ram = fields.String(required=False, allow_none=True, metadata={"description": ""})
    disk = fields.String(required=False, allow_none=True, metadata={"description": ""})


class InstanceTypeConfigResponseSchema(Schema):
    flavor = fields.String(required=False, allow_none=True, metadata={"description": ""})
    container = fields.String(required=False, allow_none=True, metadata={"description": ""})


class InstanceTypeResponseSchema(Schema):
    id = fields.Integer(required=True, metadata={"description": ""})
    uuid = fields.String(required=True, metadata={"description": ""})
    name = fields.String(required=True, metadata={"description": ""})
    # resource_id = fields.String(required=False, allow_none=True, example="", description="")
    description = fields.String(required=True, allow_none=True, metadata={"description": ""})
    features = fields.Nested(InstanceTypeFeatureResponseSchema, required=True, many=False, allow_none=False)
    config = fields.Nested(InstanceTypeConfigResponseSchema, required=False, many=False, allow_none=False)


class DescribeVolumeTypesV20Api1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True)
    volumeTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    volumeTypesTotal = fields.Integer(required=True)


class DescribeVolumeTypesV20ApiResponseSchema(Schema):
    DescribeVolumeTypesResponse = fields.Nested(
        DescribeVolumeTypesV20Api1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeVolumeTypesV20ApiRequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False,
        dump_default=10,
        load_default=10,
        context="query",
        metadata={"description": "entities list page size"},
    )
    NextToken = fields.Integer(
        required=False,
        dump_default=0,
        load_default=0,
        context="query",
        metadata={"description": "entities list page selected"},
    )
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id of the instance type owner"},
    )
    VolumeType = fields.String(
        required=False,
        allow_none=True,
        context="query",
        load_default=None,
        metadata={"description": "volume type uuid"},
    )


class DescribeVolumeTypesV20(ServiceApiView):
    summary = "Describe compute volume types"
    description = "Describe compute volume types"
    tags = ["computeservice"]
    definitions = {
        "DescribeVolumeTypesV20ApiRequestSchema": DescribeVolumeTypesV20ApiRequestSchema,
        "DescribeVolumeTypesV20ApiResponseSchema": DescribeVolumeTypesV20ApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeVolumeTypesV20ApiRequestSchema)
    parameters_schema = DescribeVolumeTypesV20ApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeVolumeTypesV20ApiResponseSchema,
            }
        }
    )
    response_schema = DescribeVolumeTypesV20ApiResponseSchema

    def get(self, controller: ServiceController, data: dict, *args, **kwargs):
        account_id = data.pop("owner_id")
        size = data.pop("MaxResults")
        page = data.pop("NextToken")
        def_id = data.pop("VolumeType")
        account = controller.get_account(account_id)

        instance_types_set, total = account.get_definitions(
            plugintype=ApiComputeVolume.plugintype,
            service_definition_id=def_id,
            size=size,
            page=page,
        )

        res_type_set = []
        for r in instance_types_set:
            res_type_item = {
                "id": r.oid,
                "uuid": r.uuid,
                "name": r.name,
                "description": r.desc,
            }

            features = []
            if r.desc is not None:
                features = r.desc.split(" ")

            feature = {}
            for f in features:
                try:
                    k, v = f.split(":")
                    feature[k] = v
                except ValueError:
                    pass

            res_type_item["features"] = feature
            res_type_set.append(res_type_item)

        if total == 1:
            res_type_set[0]["config"] = instance_types_set[0].get_main_config().params

        res = {
            "DescribeVolumeTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "volumeTypesSet": res_type_set,
                "volumeTypesTotal": total,
            }
        }
        return res


class ComputeVolumeV20API(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/computeservices/volume"
        rules = [
            ("%s/attachvolume" % base, "PUT", AttachVolumeV20, {}),
            ("%s/createvolume" % base, "POST", CreateVolumeV20, {}),
            ("%s/deletevolume" % base, "DELETE", DeleteVolumeV20, {}),
            # # DescribeVolumeAttribute
            ("%s/describevolumes" % base, "GET", DescribeVolumesV20, {}),
            # # DescribeVolumesModifications
            # # DescribeVolumeStatus
            ("%s/detachvolume" % base, "PUT", DetachVolumeV20, {}),
            # # EnableVolumeIO
            # # ModifyVolume
            # # ModifyVolumeAttribute
            ("%s/describevolumetypes" % base, "GET", DescribeVolumeTypesV20, {}),
        ]

        kwargs["version"] = "v2.0"
        ApiView.register_api(module, rules, **kwargs)
