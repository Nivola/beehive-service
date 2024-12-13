# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from marshmallow.validate import OneOf

from beehive.common.apimanager import (
    ApiObjectResponseDateSchema,
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
    ApiObjectResponseSchema,
    CrudApiObjectSimpleResponseSchema,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ServiceController, ApiServiceCatalog
from beehive_service.views import (
    ServiceApiView,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectRequestSchema,
)
from beehive_service.views.service_definition import (
    GetServiceDefinitionParamsResponseSchema,
)


class ListCatalogRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    pass


class ListCatalogParamsResponseSchema(ApiObjectResponseSchema):
    version = fields.String(required=False, default="1.0")


class ListCatalogResponseSchema(PaginatedResponseSchema):
    catalogs = fields.Nested(ListCatalogParamsResponseSchema, many=True, required=True, allow_none=True)


class ListCatalog(ServiceApiView):
    summary = "List service catalog"
    description = "List service catalog"
    tags = ["service"]
    definitions = {
        "ListCatalogResponseSchema": ListCatalogResponseSchema,
        "ListCatalogRequestSchema": ListCatalogRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListCatalogRequestSchema)
    parameters_schema = ListCatalogRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListCatalogResponseSchema}})
    response_schema = ListCatalogResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        catalogs, total = controller.get_service_catalogs(**data)
        res = [r.info() for r in catalogs]
        return self.format_paginated_response(res, "catalogs", total, **data)


class GetCatalogPerms(ServiceApiView):
    summary = "Get service catalog permissions"
    description = "Get service catalog permissions"
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        res, total = catalog.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class GetCatalogDefsRequestSchema(PaginatedRequestQuerySchema):
    oid = fields.String(
        required=True,
        description='id, uuid or name. If value is "all" select definitions for all the' "catalogs you can view",
        context="path",
    )
    plugintype = fields.String(required=False, context="query", description="plugin type name")
    flag_container = fields.Boolean(
        required=False,
        context="query",
        description="if True select only definition with type that is a container",
    )


class GetCatalogDefsResponseSchema(PaginatedResponseSchema):
    servicedefs = fields.Nested(
        GetServiceDefinitionParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class GetCatalogDefs(ServiceApiView):
    summary = "Get service catalog definitions"
    description = "Get service catalog definitions"
    tags = ["service"]
    definitions = {
        "GetCatalogDefsRequestSchema": GetCatalogDefsRequestSchema,
        "GetCatalogDefsResponseSchema": GetCatalogDefsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetCatalogDefsRequestSchema)
    parameters_schema = GetCatalogDefsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetCatalogDefsResponseSchema}})
    response_schema = GetCatalogDefsResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        if oid == "all":
            # get visible catalogs
            catalogs, total = controller.get_service_catalogs()
            catalog_ids = ",".join([str(c.oid) for c in catalogs])
            service_def, total = controller.get_paginated_service_defs(catalogs=catalog_ids, authorize=False, **data)
        else:
            catalog = controller.get_service_catalog(oid)
            service_def, total = catalog.get_paginated_service_defs(**data)
        res = [r.info() for r in service_def]
        return self.format_paginated_response(res, "servicedefs", total, **data)


class CatalogDefParamRequestSchema(Schema):
    oids = fields.List(fields.String(default=""), required=True)


class CatalogDefRequestSchema(Schema):
    definitions = fields.Nested(CatalogDefParamRequestSchema, required=True, allow_none=False, many=False)


class CatalogDefBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CatalogDefRequestSchema, context="body")


class CrudApiObjectListResponseSchema(Schema):
    uuid = fields.List(fields.UUID(required=True, description="api object uuid"))


class CreateCatalogDefs(ServiceApiView):
    summary = "Set service catalog definitions"
    description = "set service catalog definitions"
    tags = ["service"]
    definitions = {
        "CatalogDefRequestSchema": CatalogDefRequestSchema,
        "CrudApiObjectListResponseSchema": CrudApiObjectListResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CatalogDefBodyRequestSchema)
    parameters_schema = CatalogDefRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectListResponseSchema}}
    )
    response_schema = CrudApiObjectListResponseSchema

    def put(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        data = data.get("definitions")
        def_oids = data.get("oids", None)
        res = controller.add_service_catalog_def(oid, def_oids)

        return {"uuid": res}, 200


class DeleteCatalogDefs(ServiceApiView):
    summary = "Unset service catalog definitions"
    description = "Unset service catalog definitions"
    tags = ["service"]
    definitions = {
        "CatalogDefRequestSchema": CatalogDefRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CatalogDefBodyRequestSchema)
    parameters_schema = CatalogDefRequestSchema
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
        data = data.get("definitions")
        def_oids = data.get("oids", None)
        res = controller.delete_service_catalog_def(oid, def_oids)
        return res, 204


class GetCatalogParamsResponseSchema(ApiObjectResponseSchema):
    pass


class GetCatalogResponseSchema(Schema):
    catalog = fields.Nested(GetCatalogParamsResponseSchema, required=True, allow_none=True)


class GetCatalog(ServiceApiView):
    summary = "Get service catalog"
    description = "Get service catalog"
    tags = ["service"]
    definitions = {
        "GetCatalogResponseSchema": GetCatalogResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetCatalogResponseSchema}})
    response_schema = GetCatalogResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        return {"catalog": catalog.detail()}


class CreateCatalogParamRequestSchema(Schema):
    name = fields.String(required=True, example="default catalog")
    desc = fields.String(required=True, allow_none=True, example="default catalog")


class CreateCatalogRequestSchema(Schema):
    catalog = fields.Nested(CreateCatalogParamRequestSchema, context="body")


class CreateCatalogBodyRequestSchema(Schema):
    body = fields.Nested(CreateCatalogRequestSchema, context="body")


class CreateCatalog(ServiceApiView):
    summary = "Create service catalog"
    description = "Create service catalog"
    tags = ["service"]
    definitions = {
        "CreateCatalogRequestSchema": CreateCatalogRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateCatalogBodyRequestSchema)
    parameters_schema = CreateCatalogRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        data = data.get("catalog")
        resp = controller.add_service_catalog(**data)
        return {"uuid": resp}, 201


class UpdateCatalogParamRequestSchema(Schema):
    name = fields.String(required=False, default="default catalog")
    desc = fields.String(required=False, allow_none=True, default="default catalog")
    active = fields.Boolean(default=False)
    version = fields.String(default="1.0")


class UpdateCatalogRequestSchema(Schema):
    catalog = fields.Nested(UpdateCatalogParamRequestSchema)


class UpdateCatalogBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateCatalogRequestSchema, context="body")


class UpdateCatalog(ServiceApiView):
    summary = "Update service catalog"
    description = "Update service catalog"
    tags = ["service"]
    definitions = {
        "UpdateCatalogRequestSchema": UpdateCatalogRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateCatalogBodyRequestSchema)
    parameters_schema = UpdateCatalogRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        resp = catalog.update(**data.get("catalog"))
        return {"uuid": resp}, 200


class PatchCatalogParamRequestSchema(Schema):
    pass


class PatchCatalogRequestSchema(Schema):
    catalog = fields.Nested(PatchCatalogParamRequestSchema)


class PatchCatalogBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchCatalogRequestSchema, context="body")


class PatchCatalog(ServiceApiView):
    summary = "Patch service catalog"
    description = "Patch service catalog"
    tags = ["authority"]
    definitions = {
        "PatchCatalogRequestSchema": PatchCatalogRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PatchCatalogBodyRequestSchema)
    parameters_schema = PatchCatalogRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def patch(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        data = data.get("catalog")
        catalog.patch(**data)
        return {"uuid": catalog.uuid}, 200


class DeleteCatalog(ServiceApiView):
    summary = "Delete service catalog"
    description = "Delete service catalog"
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        resp = catalog.delete(soft=True)
        return resp, 204


class GetCatalogRolesItemResponseSchema(Schema):
    name = fields.String(required=True, example="master")
    desc = fields.String(required=True, example="Service Catalog administrator")


class GetCatalogRolesResponseSchema(Schema):
    roles = fields.Nested(GetCatalogRolesItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetCatalogRoles(ServiceApiView):
    summary = "Get service catalog available logical authorization roles"
    description = "Get service catalog available logical authorization roles"
    tags = ["authority"]
    definitions = {
        "GetCatalogRolesResponseSchema": GetCatalogRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetCatalogRolesResponseSchema}})
    response_schema = GetCatalogRolesResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        res = catalog.get_role_templates()
        return {"roles": res, "count": len(res)}


class ApiObjectResponseDateLoginSchema(ApiObjectResponseDateSchema):
    last_login = fields.DateTime(required=True, example="1990-12-31T23:59:59Z", description="last login date")


class GetCatalogUsersItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")
    date = fields.Nested(ApiObjectResponseDateLoginSchema, required=True)
    email = fields.String(required=False)


class GetCatalogUsersResponseSchema(Schema):
    users = fields.Nested(GetCatalogUsersItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetCatalogUsers(ServiceApiView):
    summary = "Get service catalog authorized users"
    description = "Get service catalog authorized users"
    tags = ["authority"]
    definitions = {
        "GetCatalogUsersResponseSchema": GetCatalogUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetCatalogUsersResponseSchema}})
    response_schema = GetCatalogUsersResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        res = catalog.get_users()
        return {"users": res, "count": len(res)}


class SetCatalogUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiServiceCatalog.role_templates.keys()),
    )


class SetCatalogUsersRequestSchema(Schema):
    user = fields.Nested(SetCatalogUsersParamRequestSchema)


class SetCatalogUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetCatalogUsersRequestSchema, context="body")


class SetCatalogUsers(ServiceApiView):
    summary = "Set service catalog authorized user"
    description = "Set service catalog authorized user"
    tags = ["authority"]
    definitions = {
        "SetCatalogUsersRequestSchema": SetCatalogUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetCatalogUsersBodyRequestSchema)
    parameters_schema = SetCatalogUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        data = data.get("user")
        resp = catalog.set_user(**data)
        return {"res": resp}, 200


class UnsetCatalogUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiServiceCatalog.role_templates.keys()),
    )


class UnsetCatalogUsersRequestSchema(Schema):
    user = fields.Nested(UnsetCatalogUsersParamRequestSchema)


class UnsetCatalogUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetCatalogUsersRequestSchema, context="body")


class UnsetCatalogUsers(ServiceApiView):
    summary = "Unset service catalog authorized user"
    description = "Unset service catalog authorized user"
    tags = ["authority"]
    definitions = {
        "UnsetCatalogUsersRequestSchema": UnsetCatalogUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetCatalogUsersBodyRequestSchema)
    parameters_schema = UnsetCatalogUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        data = data.get("user")
        resp = catalog.unset_user(**data)
        return {"res": resp}, 200


class GetCatalogGroupsItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")


class GetCatalogGroupsResponseSchema(Schema):
    groups = fields.Nested(GetCatalogGroupsItemResponseSchema, required=True, allow_none=True, many=True)
    count = fields.Integer(required=True)


class GetCatalogGroups(ServiceApiView):
    summary = "Get service catalog authorized groups"
    description = "Get service catalog authorized groups"
    tags = ["authority"]
    definitions = {
        "GetCatalogGroupsResponseSchema": GetCatalogGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetCatalogGroupsResponseSchema}})
    response_schema = GetCatalogGroupsResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        res = catalog.get_groups()
        return {"groups": res, "count": len(res)}


class SetCatalogGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiServiceCatalog.role_templates.keys()),
    )


class SetCatalogGroupsRequestSchema(Schema):
    group = fields.Nested(SetCatalogGroupsParamRequestSchema)


class SetCatalogGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetCatalogGroupsRequestSchema, context="body")


class SetCatalogGroups(ServiceApiView):
    summary = "Set service catalog authorized group"
    description = "Set service catalog authorized group"
    tags = ["authority"]
    definitions = {
        "SetCatalogGroupsRequestSchema": SetCatalogGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetCatalogGroupsBodyRequestSchema)
    parameters_schema = SetCatalogGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        data = data.get("group")
        resp = catalog.set_group(**data)
        return {"res": resp}, 200


class UnsetCatalogGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiServiceCatalog.role_templates.keys()),
    )


class UnsetCatalogGroupsRequestSchema(Schema):
    group = fields.Nested(UnsetCatalogGroupsParamRequestSchema)


class UnsetCatalogGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetCatalogGroupsRequestSchema, context="body")


class UnsetCatalogGroups(ServiceApiView):
    summary = "Unset service catalog authorized group"
    description = "Unset service catalog authorized group"
    tags = ["authority"]
    definitions = {
        "UnsetCatalogGroupsRequestSchema": UnsetCatalogGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetCatalogGroupsBodyRequestSchema)
    parameters_schema = UnsetCatalogGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
        catalog = controller.get_service_catalog(oid)
        data = data.get("group")
        resp = catalog.unset_group(**data)
        return {"res": resp}, 200


class ServiceCatalogAPI(ApiView):
    """ServiceCatalogAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/srvcatalogs" % base, "GET", ListCatalog, {}),
            ("%s/srvcatalogs/<oid>" % base, "GET", GetCatalog, {}),
            ("%s/srvcatalogs/<oid>/defs" % base, "GET", GetCatalogDefs, {}),
            ("%s/srvcatalogs/<oid>/defs" % base, "PUT", CreateCatalogDefs, {}),
            ("%s/srvcatalogs/<oid>/defs" % base, "DELETE", DeleteCatalogDefs, {}),
            ("%s/srvcatalogs" % base, "POST", CreateCatalog, {}),
            ("%s/srvcatalogs/<oid>" % base, "PUT", UpdateCatalog, {}),
            ("%s/srvcatalogs/<oid>" % base, "PATCH", PatchCatalog, {}),
            ("%s/srvcatalogs/<oid>" % base, "DELETE", DeleteCatalog, {}),
            ("%s/srvcatalogs/<oid>/perms" % base, "GET", GetCatalogPerms, {}),
            ("%s/srvcatalogs/<oid>/roles" % base, "GET", GetCatalogRoles, {}),
            ("%s/srvcatalogs/<oid>/users" % base, "GET", GetCatalogUsers, {}),
            ("%s/srvcatalogs/<oid>/users" % base, "POST", SetCatalogUsers, {}),
            ("%s/srvcatalogs/<oid>/users" % base, "DELETE", UnsetCatalogUsers, {}),
            ("%s/srvcatalogs/<oid>/groups" % base, "GET", GetCatalogGroups, {}),
            ("%s/srvcatalogs/<oid>/groups" % base, "POST", SetCatalogGroups, {}),
            ("%s/srvcatalogs/<oid>/groups" % base, "DELETE", UnsetCatalogGroups, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
