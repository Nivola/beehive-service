# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from typing import Dict
from beehive.common.apimanager import (
    ApiObjectResponseDateSchema,
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
    CrudApiObjectSimpleResponseSchema,
)
from flasgger import fields, Schema
from marshmallow.validate import OneOf
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ApiDivision, ServiceController
from beehive_service.views import (
    ServiceApiView,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectRequestSchema,
)
from beehive_service.views.account import (
    ListAccountsResponseSchema,
    ContainerInstancesItemResponseSchema,
)
from .check import validate_div_name


class ListDivisionsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    service_status_id = fields.Integer(Required=False, context="query")
    version = fields.String(Required=False, context="query")
    organization_id = fields.String(Required=True, context="query")
    contact = fields.String(Required=False, context="query")
    email = fields.String(Required=False, context="query")
    postaladdress = fields.String(Required=False, context="query")


class ListDivisionsParamsResponseSchema(ApiObjectResponseSchema):
    service_status_id = fields.Integer(required=False, default=5)
    version = fields.String(required=False, default="x")
    organization_id = fields.String(required=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)
    accounts = fields.Integer(required=False, allow_none=True)
    organization_name = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True)
    price_lists_id = fields.Integer(required=False, allow_none=True)


class ListDivisionsResponseSchema(PaginatedResponseSchema):
    divisions = fields.Nested(ListDivisionsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListDivisions(ServiceApiView):
    summary = "List divisions"
    description = "List divisions"
    tags = ["authority"]
    definitions = {
        "ListDivisionsResponseSchema": ListDivisionsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListDivisionsRequestSchema)
    parameters_schema = ListDivisionsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListDivisionsResponseSchema}})
    response_schema = ListDivisionsResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        divisions, total = controller.get_divisions(**data)
        organization_ids = [d.organization_id for d in divisions]

        # get divs
        orgs = self.get_organization_idx(controller, organization_id_list=organization_ids)
        res = []
        for r in divisions:
            info = r.info()

            try:
                info["organization_name"] = getattr(orgs[str(r.organization_id)], "name")
            except Exception:
                self.logger.warning(
                    "organization_id=%s not found in organization_idx list=%s" % (r.organization_id, orgs)
                )

            res.append(info)

        return self.format_paginated_response(res, "divisions", total, **data)


class GetDivisionPerms(ServiceApiView):
    summary = "Get division permissions"
    description = "Get division permissions"
    tags = ["authority"]
    definitions = {
        # 'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        "PaginatedRequestQuerySchema": PaginatedRequestQuerySchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PaginatedRequestQuerySchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        res, total = division.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class GetDivisionParamsResponseSchema(ApiObjectResponseSchema):
    service_status_id = fields.Integer(required=False, default=5)
    price_lists_id = fields.Integer(required=False)
    accounts = fields.Integer(required=False)
    version = fields.String(required=False, default="x")
    organization_id = fields.String(required=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)


class GetDivisionResponseSchema(Schema):
    division = fields.Nested(GetDivisionParamsResponseSchema, required=True, allow_none=True)


class GetDivision(ServiceApiView):
    summary = "Get one division"
    description = "Get one division"
    tags = ["authority"]
    definitions = {
        "GetDivisionResponseSchema": GetDivisionResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetDivisionResponseSchema}})
    response_schema = GetDivisionResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        res = division.detail()
        resp = {"division": res}
        return resp


class ListDivisionAccountsRequestSchema(PaginatedRequestQuerySchema, GetApiObjectRequestSchema):
    pass


class GetDivisionAccounts(ServiceApiView):
    summary = "List account for division"
    description = "List account for division"
    tags = ["authority"]
    definitions = {
        "ListAccountsResponseSchema": ListAccountsResponseSchema,
        "ListDivisionAccountsRequestSchema": ListDivisionAccountsRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListDivisionAccountsRequestSchema)
    parameters_schema = ListDivisionAccountsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListAccountsResponseSchema}})
    response_schema = ListAccountsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        accounts, total = controller.get_accounts(division_id=controller.get_division(oid).oid)
        res = [r.info() for r in accounts]
        page = kwargs.pop("page", 0)
        return self.format_paginated_response(res, "accounts", total, page=page, **kwargs)


class CreateDivisionParamRequestSchema(Schema):
    name = fields.String(required=True, validate=validate_div_name)
    desc = fields.String(required=False, allow_none=True)
    organization_id = fields.String(required=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)
    price_list_id = fields.String(
        required=False,
        allow_none=True,
        description="DEPRECATED Price List are not managed any more",
    )


class CreateDivisionRequestSchema(Schema):
    division = fields.Nested(CreateDivisionParamRequestSchema, context="body")


class CreateDivisionBodyRequestSchema(Schema):
    body = fields.Nested(CreateDivisionRequestSchema, context="body")


class CreateDivision(ServiceApiView):
    summary = "Create a division"
    description = "Create a division"
    tags = ["authority"]
    definitions = {
        "CreateDivisionRequestSchema": CreateDivisionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDivisionBodyRequestSchema)
    parameters_schema = CreateDivisionRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data: Dict, *args, **kwargs):
        data = data.get("division")
        # create the division
        resp = controller.add_division(**data)
        return {"uuid": resp}, 201


class UpdateDivisionParamRequestSchema(Schema):
    name = fields.String(required=False, description="DEPRECATED renaming is disabled")
    desc = fields.String(required=False, allow_none=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)
    active = fields.Boolean(required=False)
    price_list_id = fields.String(
        required=False,
        allow_none=True,
        description="DEPRECATED Price List are not managed any more",
    )


class UpdateDivisionRequestSchema(Schema):
    division = fields.Nested(UpdateDivisionParamRequestSchema)


class UpdateDivisionBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateDivisionRequestSchema, context="body")


class UpdateDivision(ServiceApiView):
    summary = "Update a division"
    description = "Update a division"
    tags = ["authority"]
    definitions = {
        "UpdateDivisionRequestSchema": UpdateDivisionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateDivisionBodyRequestSchema)
    parameters_schema = UpdateDivisionRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller: ServiceController, data: Dict, oid, *args, **kwargs):
        resp = controller.update_division(oid, data)
        return {"uuid": resp}


class PatchDivisionParamRequestSchema(Schema):
    pass


class PatchDivisionRequestSchema(Schema):
    division = fields.Nested(PatchDivisionParamRequestSchema)


class PatchDivisionBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchDivisionRequestSchema, context="body")


class PatchDivision(ServiceApiView):
    summary = "Patch a division"
    description = "Patch a division"
    tags = ["authority"]
    definitions = {
        "PatchDivisionRequestSchema": PatchDivisionRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PatchDivisionBodyRequestSchema)
    parameters_schema = PatchDivisionRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def patch(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        data = data.get("division")
        division.patch(**data)
        return {"uuid": division.uuid}, 200


class DeleteDivision(ServiceApiView):
    summary = "Delete a division"
    description = "Delete a division"
    tags = ["authority"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        resp = division.delete(soft=True)
        return resp, 204


class GetDivisionRolesItemResponseSchema(Schema):
    role = fields.String(required=True, example="DivAdminRole-123456")
    name = fields.String(required=True, example="master")
    desc = fields.String(required=True, example="")


class GetDivisionRolesResponseSchema(Schema):
    roles = fields.Nested(GetDivisionRolesItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetDivisionRoles(ServiceApiView):
    summary = "Get division available logical authorization roles"
    description = "Get division available logical authorization roles"
    tags = ["authority"]
    definitions = {
        "GetDivisionRolesResponseSchema": GetDivisionRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetDivisionRolesResponseSchema}})
    response_schema = GetDivisionRolesResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        res = division.get_role_templates()
        return {"roles": res, "count": len(res)}


class GetDivisionUsersItemDateResponseSchema(ApiObjectResponseDateSchema):
    last_login = fields.DateTime(required=False, example="1990-12-31T23:59:59Z", description="last login date")


class GetDivisionUsersItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")
    email = fields.String(required=False, allow_none=True)
    taxcode = fields.String(required=False, allow_none=True)
    ldap = fields.String(required=False, allow_none=True)
    date = fields.Nested(GetDivisionUsersItemDateResponseSchema, required=True)


class GetDivisionUsersResponseSchema(Schema):
    users = fields.Nested(GetDivisionUsersItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetDivisionUsers(ServiceApiView):
    summary = "Get division authorized users"
    description = "Get division authorized users"
    tags = ["authority"]
    definitions = {
        "GetDivisionUsersResponseSchema": GetDivisionUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetDivisionUsersResponseSchema}})
    response_schema = GetDivisionUsersResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        res = division.get_users()
        return {"users": res, "count": len(res)}


class SetDivisionUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiDivision.role_templates.keys()),
    )


class SetDivisionUsersRequestSchema(Schema):
    user = fields.Nested(SetDivisionUsersParamRequestSchema)


class SetDivisionUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetDivisionUsersRequestSchema, context="body")


class SetDivisionUsers(ServiceApiView):
    summary = "Set division authorized user"
    description = "Set division authorized user"
    tags = ["authority"]
    definitions = {
        "SetDivisionUsersRequestSchema": SetDivisionUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetDivisionUsersBodyRequestSchema)
    parameters_schema = SetDivisionUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        data = data.get("user")
        resp = division.set_user(**data)
        return {"uuid": resp}, 200


class UnsetDivisionUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiDivision.role_templates.keys()),
    )


class UnsetDivisionUsersRequestSchema(Schema):
    user = fields.Nested(UnsetDivisionUsersParamRequestSchema)


class UnsetDivisionUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetDivisionUsersRequestSchema, context="body")


class UnsetDivisionUsers(ServiceApiView):
    summary = "Unset division authorized user"
    description = "Unset division authorized user"
    tags = ["authority"]
    definitions = {
        "UnsetDivisionUsersRequestSchema": UnsetDivisionUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetDivisionUsersBodyRequestSchema)
    parameters_schema = UnsetDivisionUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )

    def delete(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        data = data.get("user")
        resp = division.unset_user(**data)
        return {"uuid": resp}, 200


class GetDivisionGroupsItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")


class GetDivisionGroupsResponseSchema(Schema):
    groups = fields.Nested(GetDivisionGroupsItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True, example=0)


class GetDivisionGroups(ServiceApiView):
    summary = "Get division authorized groups"
    description = "Get division authorized groups"
    tags = ["authority"]
    definitions = {
        "GetDivisionGroupsResponseSchema": GetDivisionGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetDivisionGroupsResponseSchema}}
    )
    response_schema = GetDivisionGroupsResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        division: ApiDivision = controller.get_division(oid)
        res = division.get_groups()
        return {"groups": res, "count": len(res)}


class SetDivisionGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiDivision.role_templates.keys()),
    )


class SetDivisionGroupsRequestSchema(Schema):
    group = fields.Nested(SetDivisionGroupsParamRequestSchema)


class SetDivisionGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetDivisionGroupsRequestSchema, context="body")


class SetDivisionGroups(ServiceApiView):
    summary = "Set division authorized group"
    description = "Set division authorized group"
    tags = ["authority"]
    definitions = {
        "SetDivisionGroupsRequestSchema": SetDivisionGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetDivisionGroupsBodyRequestSchema)
    parameters_schema = SetDivisionGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        data = data.get("group")
        resp = division.set_group(**data)
        return {"uuid": resp}, 200


class UnsetDivisionGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiDivision.role_templates.keys()),
    )


class UnsetDivisionGroupsRequestSchema(Schema):
    group = fields.Nested(UnsetDivisionGroupsParamRequestSchema)


class UnsetDivisionGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetDivisionGroupsRequestSchema, context="body")


class UnsetDivisionGroups(ServiceApiView):
    summary = "Unset division authorized group"
    description = "Unset division authorized group"
    tags = ["authority"]
    definitions = {
        "UnsetDivisionGroupsRequestSchema": UnsetDivisionGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetDivisionGroupsBodyRequestSchema)
    parameters_schema = UnsetDivisionGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        division = controller.get_division(oid)
        data = data.get("group")
        resp = division.unset_group(**data)
        return {"uuid": resp}, 200


class GetActiveServicesByDivisionApiRequestSchema(Schema):
    oid = fields.String(required=True, description="id, uuid", context="path")


class GetActiveServicesByDivisionResponse1Schema(Schema):
    service_container = fields.Nested(ContainerInstancesItemResponseSchema, many=True, required=True, allow_none=False)
    extraction_date = fields.DateTime(required=True)
    accounts = fields.Integer(required=True)


class GetActiveServicesByDivisionResponseSchema(Schema):
    services = fields.Nested(
        GetActiveServicesByDivisionResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class GetActiveServicesByDivision(ServiceApiView):
    summary = (
        "Returns the active services list for an division, for each service are provided information about "
        "resources usage"
    )
    description = (
        "Returns the active services list for an division, for each service are provided information "
        "about resources usage"
    )
    tags = ["authority"]
    definitions = {
        "GetActiveServicesByDivisionResponseSchema": GetActiveServicesByDivisionResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetActiveServicesByDivisionApiRequestSchema)
    parameters_schema = GetActiveServicesByDivisionApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetActiveServicesByDivisionResponseSchema,
            }
        }
    )
    response_schema = GetActiveServicesByDivisionResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        # get division
        division = controller.get_division(oid)
        # get related service instant consume
        active_services = controller.get_service_instant_consume_by_division(division.oid)
        return {"services": active_services}


class DivisionAPI(ApiView):
    """DivisionAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/divisions" % base, "GET", ListDivisions, {}),
            ("%s/divisions/<oid>" % base, "GET", GetDivision, {}),
            ("%s/divisions/<oid>/accounts" % base, "GET", GetDivisionAccounts, {}),
            ("%s/divisions" % base, "POST", CreateDivision, {}),
            ("%s/divisions/<oid>" % base, "PUT", UpdateDivision, {}),
            ("%s/divisions/<oid>" % base, "PATCH", PatchDivision, {}),
            ("%s/divisions/<oid>" % base, "DELETE", DeleteDivision, {}),
            ("%s/divisions/<oid>/perms" % base, "GET", GetDivisionPerms, {}),
            ("%s/divisions/<oid>/roles" % base, "GET", GetDivisionRoles, {}),
            ("%s/divisions/<oid>/users" % base, "GET", GetDivisionUsers, {}),
            ("%s/divisions/<oid>/users" % base, "POST", SetDivisionUsers, {}),
            ("%s/divisions/<oid>/users" % base, "DELETE", UnsetDivisionUsers, {}),
            ("%s/divisions/<oid>/groups" % base, "GET", GetDivisionGroups, {}),
            ("%s/divisions/<oid>/groups" % base, "POST", SetDivisionGroups, {}),
            ("%s/divisions/<oid>/groups" % base, "DELETE", UnsetDivisionGroups, {}),
            (
                "%s/divisions/<oid>/activeservices" % base,
                "GET",
                GetActiveServicesByDivision,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
