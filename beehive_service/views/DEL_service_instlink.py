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
    ApiServiceObjectCreateRequestSchema,
)


#
# service instance link
#
## list
class ListLinksRequestSchema(
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


class ListLinksParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example="default link name")
    desc = fields.String(required=True, example="default link description")
    attributes = fields.String(required=True, example="default value")
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# # TODO ListLinksParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class ListLinksParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListLinksParamsDetailsResponseSchema)


class ListLinksResponseSchema(PaginatedResponseSchema):
    instancelinks = fields.Nested(ListLinksParamsDetailsResponseSchema, many=True, required=True, allow_none=True)


class ListLinks(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListLinksResponseSchema": ListLinksResponseSchema,
        "ListLinksRequestSchema": ListLinksRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListLinksRequestSchema)
    parameters_schema = ListLinksRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListLinksResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        service_links, total = controller.list_service_instlink(**data)
        res = [r.info() for r in service_links]
        return self.format_paginated_response(res, "instancelinks", total, **data)


## count
class CountLinks(ServiceApiView):
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
class GetLinkParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example="default link name")
    desc = fields.String(required=True, example="default link description")
    attributes = fields.String(required=False, default="")
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# TODO GetLinkParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class GetLinkParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(GetLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetLinkResponseSchema(Schema):
    service_link = fields.Nested(GetLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetLinkResponseSchema": GetLinkResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetLinkResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        res = controller.get_service_instlink(oid)
        resp = {"service_link": res.detail()}
        return resp


## get perms
class GetLinkPerms(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        link = controller.get_service_instlink(oid)
        res, total = link.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


## create
class CreateLinkParamRequestSchema(Schema):
    # TODO CreateLinkParamRequestSchema getsione campi di tipo DICT
    #     attributes = fields.Dict(required=False, default={})
    name = fields.String(required=False, default="")
    desc = fields.String(required=False, allow_none=True)
    attributes = fields.String(required=False, default="")
    start_service_id = fields.String(required=True, allow_none=False)
    end_service_id = fields.String(required=True, allow_none=False)
    priority = fields.Integer(required=False)


class CreateLinkRequestSchema(Schema):
    instancelink = fields.Nested(CreateLinkParamRequestSchema, context="body")


class CreateLinkBodyRequestSchema(Schema):
    body = fields.Nested(CreateLinkRequestSchema, context="body")


class CreateLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateLinkRequestSchema": CreateLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateLinkBodyRequestSchema)
    parameters_schema = CreateLinkRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_instlink(**data.get("instancelink"))
        return ({"uuid": resp}, 201)


## update
class UpdateLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default="default link name")
    desc = fields.String(required=False, default="default link description")
    attributes = fields.Dict(required=False, default={})
    priority = fields.Integer(required=False)
    active = fields.Boolean(required=False, default=False)


class UpdateLinkRequestSchema(Schema):
    instancelink = fields.Nested(UpdateLinkParamRequestSchema)


class UpdateLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateLinkRequestSchema, context="body")


class UpdateLink(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateLinkRequestSchema": UpdateLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateLinkBodyRequestSchema)
    parameters_schema = UpdateLinkRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        srv_instlink = controller.get_service_instlink(oid)
        resp = srv_instlink.update(**data.get("instancelink"))
        return ({"uuid": resp}, 200)


## delete
class DeleteLink(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        #         link = controller.delete_service_instlink(oid)
        #         resp = link.delete()

        srv_instlink = controller.get_service_instlink(oid)
        resp = srv_instlink.delete(soft=True)
        return (resp, 204)


class ServiceInstLinkAPI(ApiView):
    """Service Link Instance api routes:
    * /serviceinstlinks - **GET**
    * /serviceinstlinks - **POST**
    * /serviceinstlinks/count - **GET**
    * /serviceinstlinks/<oid> - **GET**
    * /serviceinstlinks/<oid> - **DELETE**
    * /serviceinstlinks/<oid> - **PUT**
    * /serviceinstlinks/<oid>/perms - **GET**

    """

    @staticmethod
    def register_api(module, dummyrules=None, version=None):
        base = "nws"
        rules = [
            ("%s/serviceinstlinks" % base, "GET", ListLinks, {}),
            ("%s/serviceinstlinks" % base, "POST", CreateLink, {}),
            ("%s/serviceinstlinks/count" % base, "GET", CountLinks, {}),
            ("%s/serviceinstlinks/<oid>" % base, "GET", GetLink, {}),
            ("%s/serviceinstlinks/<oid>" % base, "DELETE", DeleteLink, {}),
            ("%s/serviceinstlinks/<oid>" % base, "PUT", UpdateLink, {}),
            ("%s/serviceinstlinks/<oid>/perms" % base, "GET", GetLinkPerms, {}),
        ]

        ApiView.register_api(module, rules)
