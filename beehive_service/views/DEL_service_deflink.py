# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
    ApiObjecCountResponseSchema,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
)


#
# service definition link
#
## list
class ListDefLinksRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    name = fields.String(required=False, context="query")
    desc = fields.String(required=False, context="query")
    attributes = fields.String(required=False, context="query")
    start_service_id = fields.String(required=False, context="query")
    end_service_id = fields.String(required=False, context="query")
    priority = fields.Integer(required=False, context="query")


class ListDefLinksParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example="default link name")
    desc = fields.String(required=True, example="default link description")
    attributes = fields.String(required=True, example="default value")
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# # TODO ListLinksParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class ListDefLinksParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListDefLinksParamsDetailsResponseSchema)


class ListDefLinksResponseSchema(PaginatedResponseSchema):
    service_links = fields.Nested(
        ListDefLinksParamsDetailsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListDefLinks(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListDefLinksResponseSchema": ListDefLinksResponseSchema,
        "ListDefLinksRequestSchema": ListDefLinksRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListDefLinksRequestSchema)
    parameters_schema = ListDefLinksRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListDefLinksResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        service_links, total = controller.list_service_instlink(**data)
        res = [r.info() for r in service_links]
        return self.format_paginated_response(res, "service_links", total, **data)


## count
class CountDefLinks(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ApiObjecCountResponseSchema": ApiObjecCountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjecCountResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        resp = controller.count_service_instlinks()
        return {"count": int(resp)}


## get
class GetDefLinkParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example="default link name")
    desc = fields.String(required=True, example="default link description")
    attributes = fields.String(required=False, default="")
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# TODO GetDefLinkParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class GetDefLinkParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(GetDefLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetDefLinkResponseSchema(Schema):
    service_link = fields.Nested(GetDefLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetDefLinkResponseSchema": GetDefLinkResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetDefLinkResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        res = controller.get_service_deflink(oid, authorize=True)
        resp = {"service_link": res.detail()}
        return resp


## get perms
class GetDefLinkPerms(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        link = controller.get_service_deflink(oid)
        res, total = link.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


## create
class CreateDefLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default="default link name")
    desc = fields.String(required=False, default="default link description")
    attributes = fields.String(required=False, default="")
    start_service_id = fields.String(required=True, allow_none=False)
    end_service_id = fields.String(required=True, allow_none=False)
    priority = fields.Integer(required=False)


class CreateDefLinkRequestSchema(Schema):
    service_link = fields.Nested(CreateDefLinkParamRequestSchema, context="body")


class CreateDefLinkBodyRequestSchema(Schema):
    body = fields.Nested(CreateDefLinkRequestSchema, context="body")


class CreateDefLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateDefLinkRequestSchema": CreateDefLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDefLinkBodyRequestSchema)
    parameters_schema = CreateDefLinkRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_deflink(**data.get("service_link"))
        return ({"uuid": resp}, 201)


## update
class UpdateDefLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default="default link name")
    desc = fields.String(required=False, default="default link description")
    attributes = fields.Dict(required=False, default={})
    priority = fields.Integer(required=False)


class UpdateDefLinkRequestSchema(Schema):
    service_link = fields.Nested(UpdateDefLinkParamRequestSchema)


class UpdateDefLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateDefLinkRequestSchema, context="body")


class UpdateDefLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateLinkRequestSchema": UpdateDefLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateDefLinkBodyRequestSchema)
    parameters_schema = UpdateDefLinkRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        srv_deflink = controller.get_service_deflink(oid)
        resp = srv_deflink.update(**data.get("service_link"))
        return ({"uuid": resp}, 200)


## delete
class DeleteDefLink(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        srv_deflink = controller.get_service_deflink(oid)
        resp = srv_deflink.delete(soft=True)
        return (resp, 204)


class ServiceDefLinkAPI(ApiView):
    """Service Link Definition api routes:
    * /servicedeflinks - **GET**
    * /servicedeflinks - **POST**
    * /servicedeflinks/count - **GET**
    * /servicedeflinks/<oid> - **GET**
    * /servicedeflinks/<oid> - **DELETE**
    * /servicedeflinks/<oid> - **PUT**
    * /servicedeflinks/<oid>/perms - **GET**
    """

    @staticmethod
    def register_api(module, dummyrules=None, version=None):
        base = "nws"
        rules = [
            ("%s/servicedeflinks" % base, "GET", ListDefLinks, {}),
            ("%s/servicedeflinks/<oid>" % base, "GET", GetLink, {}),
        ]

        ApiView.register_api(module, rules)
