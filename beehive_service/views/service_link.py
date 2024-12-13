# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    PaginatedRequestQuerySchema,
    SwaggerApiView,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectSmallResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsRequestSchema,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.entity.service_instance import ApiServiceInstanceLink


class ServiceSmallResponseSchema(ApiObjectSmallResponseSchema):
    pass


class UpdateServiceTagDescRequestSchema(Schema):
    cmd = fields.String(default="add", required=True)
    values = fields.List(fields.String(default="test"), required=True)


class ListLinksRequestSchema(PaginatedRequestQuerySchema):
    start_service = fields.String(context="query")
    end_service = fields.String(context="query")
    service = fields.String(context="query")
    type = fields.String(context="query")
    tags = fields.String(context="query", description="comma separated tag list")


class ListLinksParamsDetailsResponseSchema(Schema):
    type = fields.String(required=True, example="relation")
    attributes = fields.Dict(required=True, example={})
    start_service = fields.Nested(ServiceSmallResponseSchema, required=True, allow_none=True)
    end_service = fields.Nested(ServiceSmallResponseSchema, required=True, allow_none=True)


class ListLinksParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListLinksParamsDetailsResponseSchema, allow_none=True)
    version = fields.String(required=False, allow_none=True)


class ListLinksResponseSchema(PaginatedResponseSchema):
    links = fields.Nested(ListLinksParamsResponseSchema, many=True, required=True, allow_none=True)


class ListLinks(SwaggerApiView):
    summary = "List service links"
    description = "List service links"
    tags = ["service"]
    definitions = {
        "ListLinksResponseSchema": ListLinksResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListLinksRequestSchema)
    parameters_schema = ListLinksRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListLinksResponseSchema}})
    response_schema = ListLinksResponseSchema

    def get(self, controller, data, *args, **kwargs):
        tags = data.pop("tags", None)
        data["servicetags"] = tags
        links, total = controller.get_links(**data)
        res = [r.info() for r in links]
        return self.format_paginated_response(res, "links", total, **data)


class GetLinkParamsDetailsResponseSchema(Schema):
    type = fields.String(required=True, example="relation")
    attributes = fields.Dict(required=True, example={})
    start_service = fields.Nested(ServiceSmallResponseSchema, required=True, allow_none=True)
    end_service = fields.Nested(ServiceSmallResponseSchema, required=True, allow_none=True)


class GetLinkParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListLinksParamsDetailsResponseSchema, required=True, allow_none=True)


class GetLinkResponseSchema(Schema):
    link = fields.Nested(GetLinkParamsResponseSchema, required=True, allow_none=True)


class GetLink(SwaggerApiView):
    summary = "Get service link"
    description = "Get service link"
    tags = ["service"]
    definitions = {
        "GetLinkResponseSchema": GetLinkResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetLinkResponseSchema}})
    response_schema = GetLinkResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        link = controller.get_link(oid)
        return {"link": link.detail()}


class GetLinkPerms(SwaggerApiView):
    summary = "Get service link permissions"
    description = "Get service link permissions"
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
        link = controller.get_link(oid)
        res, total = link.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class CreateLinkParamRequestSchema(Schema):
    type = fields.String(required=True, example="relation")
    name = fields.String(required=True, example="1")
    attributes = fields.Dict(required=True, example={})
    start_service = fields.String(required=True, example="2")
    end_service = fields.String(required=True, example="3")
    account = fields.String(required=True, description="Account id or uuid related to tag")


class CreateLinkRequestSchema(Schema):
    link = fields.Nested(CreateLinkParamRequestSchema)


class CreateLinkBodyRequestSchema(Schema):
    body = fields.Nested(CreateLinkRequestSchema, context="body")


class CreateLink(SwaggerApiView):
    summary = "Create service link"
    description = "Create service link"
    tags = ["service"]
    definitions = {
        "CreateLinkRequestSchema": CreateLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateLinkBodyRequestSchema)
    parameters_schema = CreateLinkRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_link(**data.get("link"))
        return {"uuid": resp}, 201


class UpdateLinkParamRequestSchema(Schema):
    type = fields.String(default="relation")
    name = fields.String(default="1")
    attributes = fields.Dict(default={})
    start_service = fields.String(default="2")
    end_service = fields.String(default="3")
    tags = fields.Nested(UpdateServiceTagDescRequestSchema, allow_none=True)


class UpdateLinkRequestSchema(Schema):
    link = fields.Nested(UpdateLinkParamRequestSchema)


class UpdateLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateLinkRequestSchema, context="body")


class UpdateLink(SwaggerApiView):
    summary = "Update service link"
    description = "Update service link"
    tags = ["service"]
    definitions = {
        "UpdateLinkRequestSchema": UpdateLinkRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateLinkBodyRequestSchema)
    parameters_schema = UpdateLinkRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        link: ApiServiceInstanceLink = controller.get_link(oid)
        data = data.get("link")
        tags = data.pop("tags", None)
        resp = link.update(**data)
        if tags is not None:
            cmd = tags.get("cmd")
            values = tags.get("values")
            # add tag
            if cmd == "add":
                for value in values:
                    link.add_tag(value)
            elif cmd == "delete":
                for value in values:
                    link.remove_tag(value)
        return {"uuid": resp}


class DeleteLink(SwaggerApiView):
    summary = "Delete service link"
    description = "Delete service link"
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        link = controller.get_link(oid)
        resp = link.delete()
        return resp, 204


class ServiceInstanceLinkAPI(ApiView):
    """Service api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/links" % base, "GET", ListLinks, {}),
            ("%s/links" % base, "POST", CreateLink, {}),
            ("%s/links/<oid>" % base, "GET", GetLink, {}),
            ("%s/links/<oid>" % base, "DELETE", DeleteLink, {}),
            ("%s/links/<oid>" % base, "PUT", UpdateLink, {}),
            ("%s/links/<oid>/perms" % base, "GET", GetLinkPerms, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
