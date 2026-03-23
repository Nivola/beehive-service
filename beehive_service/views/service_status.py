# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import (
    GetApiObjectRequestSchema,
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    SwaggerApiView,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ServiceController
from beehive_service.views import (
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectRequestSchema,
    ServiceApiView,
)


class GetServiceStatusParamsResponseSchema(Schema):
    id = fields.Integer(required=True, dump_default=10, metadata={"example": 10, "description": "entity database id"})
    name = fields.String(required=True, dump_default="test", metadata={"example": "test", "description": "entity name"})
    desc = fields.String(required=True, dump_default="test", metadata={"example": "test", "description": "entity name"})

class GetServiceStatusResponseSchema(Schema):
    service_status = fields.Nested(GetServiceStatusParamsResponseSchema, required=True, allow_none=True)


class GetServiceStatus(ServiceApiView):
    summary = "Get service status"
    description = "Get service status"
    tags = ["service"]
    definitions = {
        "GetServiceStatusResponseSchema": GetServiceStatusResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetServiceStatusResponseSchema}})

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        service_status = controller.get_service_status(oid)
        return {"service_status": service_status.detail()}


class ListServiceStatusRequestSchema(
    # ApiServiceObjectRequestSchema,
    # ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    pass

class ListServiceStatusResponseSchema(PaginatedResponseSchema):
    service_statuses = fields.Nested(GetServiceStatusParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceStatus(ServiceApiView):
    summary = "Get service types"
    description = "Get service types"
    tags = ["service"]
    definitions = {
        "ListServiceStatusResponseSchema": ListServiceStatusResponseSchema,
        "ListServiceStatusRequestSchema": ListServiceStatusRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceStatusRequestSchema)
    parameters_schema = ListServiceStatusRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListServiceStatusResponseSchema}})
    response_schema = ListServiceStatusResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        service_type, total = controller.get_service_statuses(**data)
        res = [r.info() for r in service_type]
        res_dict = self.format_paginated_response(res, "service_statuses", total, **data)
        return res_dict


class ServiceStatusAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/servicestatus" % base, "GET", ListServiceStatus, {}),
            ("%s/servicestatus/<oid>" % base, "GET", GetServiceStatus, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
