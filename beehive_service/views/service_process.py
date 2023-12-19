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
    SwaggerApiView,
    ApiView,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView


class GetServiceProcessParamsResponseSchema(ApiObjectResponseSchema):
    service_type_id = fields.String(Required=True)
    name = fields.String(Required=True, allow_none=True, example="default name")
    objid = fields.String(Required=True)
    method_key = fields.String(Required=True)
    process_key = fields.String(Required=True)
    template = fields.String(Required=True)


class GetServiceProcessResponseSchema(Schema):
    serviceprocess = fields.Nested(GetServiceProcessParamsResponseSchema, required=True, allow_none=True)


class GetServiceProcess(ServiceApiView):
    summary = "Get service process"
    description = "Get service process"
    tags = ["service"]
    definitions = {
        "GetServiceProcessResponseSchema": GetServiceProcessResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceProcessResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        serviceprocess = controller.get_service_process(oid)
        return {"serviceprocess": serviceprocess.detail()}


class ListServiceProcessRequestSchema(PaginatedRequestQuerySchema):
    service_type_id = fields.String(Required=False, context="query")
    name = fields.String(Required=False, context="query")
    objid = fields.String(Required=False, context="query")
    method_key = fields.String(Required=False, context="query")
    process_key = fields.String(Required=False, context="query")


class ListServiceProcessResponseSchema(PaginatedResponseSchema):
    serviceprocesses = fields.Nested(GetServiceProcessParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceProcess(ServiceApiView):
    summary = "List service process"
    description = "List service process"
    tags = ["service"]
    definitions = {
        "ListServiceProcessResponseSchema": ListServiceProcessResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceProcessRequestSchema)
    parameters_schema = ListServiceProcessRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceProcessResponseSchema}}
    )
    response_schema = ListServiceProcessResponseSchema

    def get(self, controller, data, *args, **kwargs):
        service_type, total = controller.get_service_processes(**data)
        res = [r.info() for r in service_type]
        return self.format_paginated_response(res, "serviceprocesses", total, **data)


class CreateServiceProcessParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    service_type_id = fields.String(required=True)
    method_key = fields.String(required=True)
    process_key = fields.String(required=True)
    template = fields.String(required=True)


class CreateServiceProcessRequestSchema(Schema):
    serviceprocess = fields.Nested(CreateServiceProcessParamRequestSchema, context="body")


class CreateServiceProcessBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceProcessRequestSchema, context="body")


class CreateServiceProcess(ServiceApiView):
    summary = "Create a service process"
    description = "Create a service process"
    tags = ["service"]
    definitions = {
        "CreateServiceProcessRequestSchema": CreateServiceProcessRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceProcessBodyRequestSchema)
    parameters_schema = CreateServiceProcessRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_process(**data.get("serviceprocess"))
        return {"uuid": resp}, 201


class UpdateServiceProcessParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    service_type_id = fields.String(Required=False, allow_none=True)
    method_key = fields.String(Required=False, allow_none=True)
    process_key = fields.String(Required=False, allow_none=True)
    template = fields.String(Required=False, allow_none=True)


class UpdateServiceProcessRequestSchema(Schema):
    serviceprocess = fields.Nested(UpdateServiceProcessParamRequestSchema)


class UpdateServiceProcessBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceProcessRequestSchema, context="body")


class UpdateServiceProcess(ServiceApiView):
    summary = "Update a service process"
    description = "Update a service process"
    tags = ["service"]
    definitions = {
        "UpdateServiceProcessRequestSchema": UpdateServiceProcessRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceProcessBodyRequestSchema)
    parameters_schema = UpdateServiceProcessRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        srv_cp = controller.get_service_process(oid)
        data = data.get("serviceprocess")
        resp = srv_cp.update(**data)
        return {"uuid": resp}, 200


class DeleteServiceProcess(ServiceApiView):
    summary = "Delete a service process"
    description = "Delete a service process"
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        srv_cp = controller.get_service_process(oid)
        resp = srv_cp.delete(soft=True)
        return resp, 204


class ServiceProcessAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/serviceprocesses" % base, "GET", ListServiceProcess, {}),
            ("%s/serviceprocesses" % base, "POST", CreateServiceProcess, {}),
            ("%s/serviceprocesses/<oid>" % base, "GET", GetServiceProcess, {}),
            ("%s/serviceprocesses/<oid>" % base, "PUT", UpdateServiceProcess, {}),
            ("%s/serviceprocesses/<oid>" % base, "DELETE", DeleteServiceProcess, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
