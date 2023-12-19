# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import (
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
    SwaggerApiView,
    ApiView,
)
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectResponseSchema,
)


## get
class GetServiceInstCfgParamsResponseSchema(ApiServiceObjectResponseSchema):
    service_instance_id = fields.String(required=False, allow_none=True)


class GetServiceInstCfgResponseSchema(Schema):
    instancecfg = fields.Nested(GetServiceInstCfgParamsResponseSchema, required=True, allow_none=True)


class GetServiceInstCfg(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceInstCfgResponseSchema": GetServiceInstCfgResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceInstCfgResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        instancecfg = controller.get_service_instance_cfg(oid)
        return {"instancecfg": instancecfg.detail()}


## list
class ListServiceInstCfgRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    service_instance_id = fields.String(Required=False, context="query")


class ListServiceInstCfgResponseSchema(PaginatedResponseSchema):
    instancecfgs = fields.Nested(GetServiceInstCfgParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceInstCfg(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceInstCfgResponseSchema": ListServiceInstCfgResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceInstCfgRequestSchema)
    parameters_schema = ListServiceInstCfgRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceInstCfgResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        service_cfg, total = controller.get_service_instance_cfgs(**data)
        res = [r.info() for r in service_cfg]
        return self.format_paginated_response(res, "instancecfgs", total, **data)


## create
class CreateServiceInstCfgParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    active = fields.Boolean(required=False, allow_none=True)
    service_instance_id = fields.String(required=True)
    json_cfg = fields.Dict(required=True, example={})


class CreateServiceInstCfgRequestSchema(Schema):
    instancecfg = fields.Nested(CreateServiceInstCfgParamRequestSchema, context="body")


class CreateServiceInstCfgBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceInstCfgRequestSchema, context="body")


class CreateServiceInstCfg(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateServiceInstCfgRequestSchema": CreateServiceInstCfgRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceInstCfgBodyRequestSchema)
    parameters_schema = CreateServiceInstCfgRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_instance_cfg(**data.get("instancecfg"))
        return ({"uuid": resp}, 201)


## update
class UpdateServiceInstCfgParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    json_cfg = fields.Dict(required=False, allow_none=True)
    active = fields.String(required=False, allow_none=True)


class UpdateServiceInstCfgRequestSchema(Schema):
    instancecfg = fields.Nested(UpdateServiceInstCfgParamRequestSchema)


class UpdateServiceInstCfgBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstCfgRequestSchema, context="body")


class UpdateServiceInstCfg(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateServiceInstCfgRequestSchema": UpdateServiceInstCfgRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstCfgBodyRequestSchema)
    parameters_schema = UpdateServiceInstCfgRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        inst_cfg = controller.get_service_instance_cfg(oid)
        data = data.get("instancecfg")

        resp = inst_cfg.update(**data)
        return ({"uuid": resp}, 200)


class DeleteServiceInstCfg(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        inst_cfg = controller.get_service_instance_cfg(oid)
        resp = inst_cfg.delete(soft=True)
        return (resp, 204)


## get perms
class GetServiceInstCfgPerms(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        inst_cfg = controller.get_service_instance_cfg(oid)
        res, total = inst_cfg.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


## custom
class CustomServiceInstCfgApiParamsResponseSchema(ApiObjectResponseSchema):
    pass


class CustomServiceInstanceApiResponseSchema(Schema):
    service = fields.Nested(GetServiceInstCfgParamsResponseSchema, required=True)


class CustomServiceInstCfgApi(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceInstanceResponseSchema": GetServiceInstCfgResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceInstCfgResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        inst_cfg = controller.get_service_instance_cfg(oid)
        return {"instancecfg": inst_cfg.detail()}


class ServiceInstCfgAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, version=None):
        base = "nws"
        rules = [
            ("%s/instancecfgs" % base, "GET", ListServiceInstCfg, {}),
            ("%s/instancecfgs" % base, "POST", CreateServiceInstCfg, {}),
            ("%s/instancecfgs/<oid>" % base, "GET", GetServiceInstCfg, {}),
            ("%s/instancecfgs/<oid>" % base, "PUT", UpdateServiceInstCfg, {}),
            ("%s/instancecfgs/<oid>" % base, "DELETE", DeleteServiceInstCfg, {}),
            ("%s/instancecfgs/<oid>/perms" % base, "GET", GetServiceInstCfgPerms, {}),
        ]

        ApiView.register_api(module, rules)
