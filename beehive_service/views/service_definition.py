# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte
from beehive_service.controller import ServiceController
from beecell.simple import dict_get
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
    ApiManagerWarning,
    ApiManagerError,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.entity.service_definition import (
    ApiServiceLinkDef,
    ApiServiceConfig,
    ApiServiceDefinition,
)
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectResponseSchema,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectCreateRequestSchema,
)
from beehive_service.model import SrvStatusType
from beehive_service.service_util import ServiceUtil


class GetServiceDefinitionParamsResponseSchema(ApiServiceObjectResponseSchema):
    status = fields.String(required=False, allow_none=True)
    service_type_id = fields.String(required=False, allow_none=True)
    is_default = fields.Boolean(required=False, allow_none=True)


class GetServiceDefinitionResponseSchema(Schema):
    servicedef = fields.Nested(
        GetServiceDefinitionParamsResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )


class GetServiceDefinition(ServiceApiView):
    summary = "Get service definition"
    description = "Get service definition"
    tags = ["service"]
    definitions = {
        "GetServiceDefinitionResponseSchema": GetServiceDefinitionResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceDefinitionResponseSchema}}
    )
    response_schema = GetServiceDefinitionResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicedef = controller.get_service_def(oid)
        return {"servicedef": servicedef.detail()}


class ListServiceDefinitionRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    status = fields.String(Required=False, context="query")
    plugintype = fields.String(required=False, context="query")
    flag_container = fields.Boolean(required=False, context="query")


class ListServiceDefinitionResponseSchema(PaginatedResponseSchema):
    servicedefs = fields.Nested(
        GetServiceDefinitionParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListServiceDefinition(ServiceApiView):
    summary = "List service definition"
    description = "List service definition"
    tags = ["service"]
    definitions = {
        "ListServiceDefinitionResponseSchema": ListServiceDefinitionResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceDefinitionRequestSchema)
    parameters_schema = ListServiceDefinitionRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceDefinitionResponseSchema}}
    )
    response_schema = ListServiceDefinitionResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        service_def, total = controller.get_paginated_service_defs(**data)
        res = [r.info() for r in service_def]
        return self.format_paginated_response(res, "servicedefs", total, **data)


class CreateServiceDefinitionParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    service_type_id = fields.String(required=True)
    parent_id = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, allow_none=True)
    status = fields.String(required=False, missing=SrvStatusType.ACTIVE)
    is_default = fields.Bool(required=False, missing=False)


class CreateServiceDefinitionRequestSchema(Schema):
    servicedef = fields.Nested(CreateServiceDefinitionParamRequestSchema, context="body")


class CreateServiceDefinitionBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceDefinitionRequestSchema, context="body")


class CreateServiceDefinition(ServiceApiView):
    summary = "Create a service definition"
    description = "Create a service definition"
    tags = ["service"]
    definitions = {
        "CreateServiceDefinitionRequestSchema": CreateServiceDefinitionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceDefinitionBodyRequestSchema)
    parameters_schema = CreateServiceDefinitionRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_def(**data.get("servicedef"))
        return {"uuid": resp}, 201


class UpdateServiceDefinitionConfigParamRequestSchema(Schema):
    key = fields.String(required=False, allow_none=True, description="Service config key")
    value = fields.String(required=False, allow_none=True, description="Service config value")


class UpdateServiceDefinitionParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True, description="Service definition name")
    desc = fields.String(required=False, allow_none=True, description="Service definition description")
    status = fields.String(required=False, allow_none=True, description="Service definition statue")
    config = fields.String(
        required=False,
        allow_none=True,
        many=False,
        description="Service definition config key:value",
    )


class UpdateServiceDefinitionRequestSchema(Schema):
    servicedef = fields.Nested(UpdateServiceDefinitionParamRequestSchema)


class UpdateServiceDefinitionBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceDefinitionRequestSchema, context="body")


class UpdateServiceDefinition(ServiceApiView):
    summary = "Update a service definition"
    description = "Update a service definition"
    tags = ["service"]
    definitions = {
        "UpdateServiceDefinitionRequestSchema": UpdateServiceDefinitionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceDefinitionBodyRequestSchema)
    parameters_schema = UpdateServiceDefinitionRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        srv_def = controller.get_service_def(oid)
        data = data.get("servicedef")
        if "config" in data:
            config = data.pop("config").split(":")
            if len(config) < 2:
                raise ApiManagerError("Config syntax is wrong. Must be key:value")
            srv_def.set_config(config[0], config[1])
        resp = srv_def.update(**data)
        return {"uuid": resp}, 200


class DeleteServiceDefinitionRequestSchema(Schema):
    pass


class DeleteServiceDefinitionBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteServiceDefinitionRequestSchema, context="body")


class DeleteServiceDefinition(ServiceApiView):
    summary = "Delete a service definition"
    description = "Delete a service definition"
    tags = ["service"]
    definitions = {
        "DeleteServiceDefinitionRequestSchema": DeleteServiceDefinitionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteServiceDefinitionBodyRequestSchema)
    parameters_schema = DeleteServiceDefinitionRequestSchema
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kvargs):
        srv_def = controller.get_service_def(oid)
        resp = srv_def.delete(soft=True)
        return resp, 204


class GetServiceDefinitionPerms(ServiceApiView):
    summary = "Get service definition permissions"
    description = "Get service definition permissions"
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicedef = controller.get_service_def(oid)
        res, total = servicedef.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


#
# service definition config
#
class ListServiceConfigsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    service_definition_id = fields.String(context="query")
    params_type = fields.String(Required=False, context="query")


class ServiceConfigParamsResponseSchema(ApiObjectResponseSchema):
    service_definition_id = fields.String(required=True)
    params = fields.Dict(Required=True)
    params_type = fields.String(Required=True)


class ListServiceConfigsResponseSchema(PaginatedResponseSchema):
    servicecfgs = fields.Nested(ServiceConfigParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceConfigs(ServiceApiView):
    summary = "List service definition configs"
    description = "List service definition configs"
    tags = ["service"]
    definitions = {
        "ListServiceConfigsResponseSchema": ListServiceConfigsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceConfigsRequestSchema)
    parameters_schema = ListServiceConfigsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceConfigsResponseSchema}}
    )
    response_schema = ListServiceConfigsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        servicecfgs, total = controller.get_service_cfgs(**data)
        res = [r.info() for r in servicecfgs]
        return self.format_paginated_response(res, "servicecfgs", total, **data)


class GetServiceConfigResponseSchema(Schema):
    servicecfg = fields.Nested(ServiceConfigParamsResponseSchema, required=True, allow_none=True)


class GetServiceConfig(ServiceApiView):
    summary = "Get a service definition config"
    description = "Get a service definition config"
    tags = ["service"]
    definitions = {
        "GetServiceConfigResponseSchema": GetServiceConfigResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetServiceConfigResponseSchema}})
    response_schema = GetServiceConfigResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicecfg = controller.get_service_cfg(oid)
        resp = {"servicecfg": servicecfg.detail()}
        return resp


class CreateServiceConfigParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    service_definition_id = fields.String(required=True, allow_none=False)
    params = fields.Dict(required=True, example={})
    params_type = fields.String(required=True)


class CreateServiceConfigRequestSchema(Schema):
    servicecfg = fields.Nested(CreateServiceConfigParamRequestSchema, context="body")


class CreateServiceConfigBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceConfigRequestSchema, context="body")


class CreateServiceConfig(ServiceApiView):
    summary = "Create a service definition config"
    description = "Create a service definition config"
    tags = ["service"]
    definitions = {
        "CreateServiceConfigRequestSchema": CreateServiceConfigRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceConfigBodyRequestSchema)
    parameters_schema = CreateServiceConfigRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_cfg(**data.get("servicecfg"))
        return {"uuid": resp}, 201


class UpdateServiceConfigParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    service_definition_id = fields.String(required=False)
    params = fields.Dict(required=False)
    params_type = fields.Integer(required=False)


class UpdateServiceConfigRequestSchema(Schema):
    servicecfg = fields.Nested(UpdateServiceConfigParamRequestSchema)


class UpdateServiceConfigBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceConfigRequestSchema, context="body")


class UpdateServiceConfig(ServiceApiView):
    summary = "Update a service definition config"
    description = "Update a service definition config"
    tags = ["service"]
    definitions = {
        "UpdateServiceConfigRequestSchema": UpdateServiceConfigRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceConfigBodyRequestSchema)
    parameters_schema = UpdateServiceConfigRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        srv_cfg = controller.get_service_cfg(oid)
        data = data.get("servicecfg")
        resp = srv_cfg.update(**data)
        return {"uuid": resp}, 200


class DeleteServiceConfig(ServiceApiView):
    summary = "Delete a service definition config"
    description = "Delete a service definition config"
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        srv_cfg = controller.get_service_cfg(oid)
        resp = srv_cfg.delete(soft=True)
        return resp, 204


class GetServiceConfigPerms(ServiceApiView):
    summary = "Get service definition config permissions"
    description = "Get service definition config permissions"
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicecfg = controller.get_service_cfg(oid)
        res, total = servicecfg.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class ServiceDefinitionAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/servicedefs" % base, "GET", ListServiceDefinition, {}),
            ("%s/servicedefs" % base, "POST", CreateServiceDefinition, {}),
            ("%s/servicedefs/<oid>" % base, "GET", GetServiceDefinition, {}),
            ("%s/servicedefs/<oid>" % base, "PUT", UpdateServiceDefinition, {}),
            ("%s/servicedefs/<oid>" % base, "DELETE", DeleteServiceDefinition, {}),
            ("%s/servicedefs/<oid>/perms" % base, "GET", GetServiceDefinitionPerms, {}),
            ("%s/servicecfgs" % base, "GET", ListServiceConfigs, {}),
            ("%s/servicecfgs/<oid>" % base, "GET", GetServiceConfig, {}),
            ("%s/servicecfgs/<oid>/perms" % base, "GET", GetServiceConfigPerms, {}),
            ("%s/servicecfgs" % base, "POST", CreateServiceConfig, {}),
            ("%s/servicecfgs/<oid>" % base, "PUT", UpdateServiceConfig, {}),
            ("%s/servicecfgs/<oid>" % base, "DELETE", DeleteServiceConfig, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
