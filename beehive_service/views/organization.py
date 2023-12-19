# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

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
from marshmallow.validate import OneOf, Length
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ApiOrganization, ServiceController
from beehive_service.views import (
    ServiceApiView,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectRequestSchema,
)
from beehive_service.views.account import ContainerInstancesItemResponseSchema


class ListOrganizationsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    org_type = fields.String(context="query")
    service_status_id = fields.Integer(context="query")
    version = fields.String(context="query")
    ext_anag_id = fields.String(context="query")
    attributes = fields.String(context="query")
    hasvat = fields.Boolean(context="query")
    partner = fields.Boolean(context="query")
    referent = fields.String(context="query")
    email = fields.String(context="query")
    legalemail = fields.String(context="query")
    postaladdress = fields.String(context="query")


class ListOrganizationsParamsResponseSchema(ApiObjectResponseSchema):
    org_type = fields.String(required=False, default="Public")
    service_status_id = fields.Integer(required=False, default=6)
    version = fields.String(required=False, default="1.0")
    ext_anag_id = fields.String(required=False, allow_none=True)
    attributes = fields.String(required=False, allow_none=True)
    hasvat = fields.Boolean(required=False, default=False)
    partner = fields.Boolean(required=False, default=False)
    referent = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    legalemail = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True)
    divisions = fields.Integer(required=False, allow_none=True)


class ListOrganizationsResponseSchema(PaginatedResponseSchema):
    organizations = fields.Nested(ListOrganizationsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListOrganizations(ServiceApiView):
    summary = "List organizations"
    description = "List organizations"
    tags = ["authority"]
    definitions = {
        "ListOrganizationsResponseSchema": ListOrganizationsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListOrganizationsRequestSchema)
    parameters_schema = ListOrganizationsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListOrganizationsResponseSchema}}
    )
    response_schema = ListOrganizationsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        organizations, total = controller.get_organizations(**data)
        res = [r.info() for r in organizations]
        return self.format_paginated_response(res, "organizations", total, **data)


class GetOrganizationParamsServicesResponseSchema(Schema):
    pass


class GetOrganizationParamsResponseSchema(ApiObjectResponseSchema):
    org_type = fields.String(required=True, example="Public")
    service_status_id = fields.Integer(required=False, default=6)
    version = fields.String(required=False, default="1.0")
    ext_anag_id = fields.String(required=False, allow_none=True)
    attributes = fields.String(required=False, allow_none=True)
    hasvat = fields.Boolean(required=False, default=False)
    partner = fields.Boolean(required=False, default=False)
    referent = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    legalemail = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)


class GetOrganizationResponseSchema(Schema):
    organization = fields.Nested(GetOrganizationParamsResponseSchema, required=True, allow_none=True)


class GetOrganization(ServiceApiView):
    summary = "Get one organization"
    description = "Get one organization"
    tags = ["authority"]
    definitions = {
        "GetOrganizationResponseSchema": GetOrganizationResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetOrganizationResponseSchema}})
    response_schema = GetOrganizationResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        return {"organization": organization.detail()}


class GetOrganizationPerms(ServiceApiView):
    summary = "Get organization permissions"
    description = "Get organization permissions"
    tags = ["authority"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        res, total = organization.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class CreateOrganizationParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    org_type = fields.String(required=True)
    ext_anag_id = fields.String(required=False, allow_none=True)
    attributes = fields.String(required=False, allow_none=True)
    hasvat = fields.Boolean(required=False, default=False)
    partner = fields.Boolean(required=False, default=False)
    referent = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    legalemail = fields.String(required=False, allow_none=True)
    postaladdress = fields.String(required=False, allow_none=True)


class CreateOrganizationRequestSchema(Schema):
    organization = fields.Nested(CreateOrganizationParamRequestSchema, context="body")


class CreateOrganizationBodyRequestSchema(Schema):
    body = fields.Nested(CreateOrganizationRequestSchema, context="body")


class CreateOrganization(ServiceApiView):
    summary = "Create an organization"
    description = "Create an organization"
    tags = ["authority"]
    definitions = {
        "CreateOrganizationRequestSchema": CreateOrganizationRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateOrganizationBodyRequestSchema)
    parameters_schema = CreateOrganizationRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_organization(**data.get("organization"))
        return {"uuid": resp}, 201


class UpdateOrganizationParamRequestSchema(Schema):
    name = fields.String(required=False, default="test", description="DEPRECATED renaming is disabled")
    desc = fields.String(required=False, default="test")
    org_type = fields.String(required=False, default="Public")
    ext_anag_id = fields.String(required=False, default="")
    attributes = fields.String(required=False, default="")
    hasvat = fields.Boolean(required=False, default=False)
    partner = fields.Boolean(required=False, default=False)
    referent = fields.String(required=False, default="")
    email = fields.String(required=False, default="")
    legalemail = fields.String(required=False, default="")
    postaladdress = fields.String(required=False, default="")
    active = fields.Boolean(required=False, default=False)


class UpdateOrganizationRequestSchema(Schema):
    organization = fields.Nested(UpdateOrganizationParamRequestSchema)


class UpdateOrganizationBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateOrganizationRequestSchema, context="body")


class UpdateOrganization(ServiceApiView):
    summary = "Update an organization"
    description = "Update an organization"
    tags = ["authority"]
    definitions = {
        "UpdateOrganizationRequestSchema": UpdateOrganizationRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateOrganizationBodyRequestSchema)
    parameters_schema = UpdateOrganizationRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller: ServiceController, data: Dict, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data: Dict = data.get("organization")
        data.pop("name", None)
        resp = organization.update(**data)
        return {"uuid": resp}, 200


class PatchOrganizationParamRequestSchema(Schema):
    pass


class PatchOrganizationRequestSchema(Schema):
    organization = fields.Nested(PatchOrganizationParamRequestSchema)


class PatchOrganizationBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchOrganizationRequestSchema, context="body")


class PatchOrganization(ServiceApiView):
    summary = "Patch an organization"
    description = "Patch an organization"
    tags = ["authority"]
    definitions = {
        "PatchOrganizationRequestSchema": PatchOrganizationRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PatchOrganizationBodyRequestSchema)
    parameters_schema = PatchOrganizationRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def patch(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data = data.get("organization")
        organization.patch(**data)
        return {"uuid": organization.uuid}, 200


class DeleteOrganization(ServiceApiView):
    summary = "Delete an organization"
    description = "Delete an organization"
    tags = ["authority"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        resp = organization.delete(soft=True)
        return resp, 204


class GetOrganizationRolesItemResponseSchema(Schema):
    name = fields.String(required=True, example="master")
    desc = fields.String(required=True, example="")


class GetOrganizationRolesResponseSchema(Schema):
    roles = fields.Nested(
        GetOrganizationRolesItemResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )
    count = fields.Integer(required=True)


class GetOrganizationRoles(ServiceApiView):
    summary = "Get organization available logical authorization roles"
    description = "Get organization available logical authorization roles"
    tags = ["authority"]
    definitions = {
        "GetOrganizationRolesResponseSchema": GetOrganizationRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetOrganizationRolesResponseSchema}}
    )
    response_schema = GetOrganizationRolesResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        res = organization.get_role_templates()
        return {"roles": res, "count": len(res)}


class GetOrganizationUsersItemDateResponseSchema(ApiObjectResponseDateSchema):
    last_login = fields.DateTime(required=False, example="1990-12-31T23:59:59Z", description="last login date")


class GetOrganizationUsersItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")
    email = fields.String(required=False)
    date = fields.Nested(GetOrganizationUsersItemDateResponseSchema, required=True)


class GetOrganizationUsersResponseSchema(Schema):
    users = fields.Nested(
        GetOrganizationUsersItemResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )
    count = fields.Integer(required=True)


class GetOrganizationUsers(ServiceApiView):
    summary = "Get organization authorized users"
    description = "Get organization authorized users"
    tags = ["authority"]
    definitions = {
        "GetOrganizationUsersResponseSchema": GetOrganizationUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetOrganizationUsersResponseSchema}}
    )
    response_schema = GetOrganizationUsersResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        res = organization.get_users()
        return {"users": res, "count": len(res)}


class SetOrganizationUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiOrganization.role_templates.keys()),
    )


class SetOrganizationUsersRequestSchema(Schema):
    user = fields.Nested(SetOrganizationUsersParamRequestSchema)


class SetOrganizationUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetOrganizationUsersRequestSchema, context="body")


class SetOrganizationUsers(ServiceApiView):
    summary = "Set organization authorized user"
    description = "Set organization authorized user"
    tags = ["authority"]
    definitions = {
        "SetOrganizationUsersRequestSchema": SetOrganizationUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetOrganizationUsersBodyRequestSchema)
    parameters_schema = SetOrganizationUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data = data.get("user")
        resp = organization.set_user(**data)
        return {"uuid": resp}, 200


class UnsetOrganizationUsersParamRequestSchema(Schema):
    user_id = fields.String(
        required=True,
        default="prova",
        description="User name, id or uuid",
        allow_none=False,
        validate=Length(1, error="user_id Must not be Empty"),
    )
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiOrganization.role_templates.keys()),
    )


class UnsetOrganizationUsersRequestSchema(Schema):
    user = fields.Nested(UnsetOrganizationUsersParamRequestSchema, required=True)


class UnsetOrganizationUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetOrganizationUsersRequestSchema, context="body")


class UnsetOrganizationUsers(ServiceApiView):
    summary = "Unset organization authorized user"
    description = "Unset organization authorized user"
    tags = ["authority"]
    definitions = {
        "UnsetOrganizationUsersRequestSchema": UnsetOrganizationUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetOrganizationUsersBodyRequestSchema)
    parameters_schema = UnsetOrganizationUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data = data.get("user")
        resp = organization.unset_user(**data)
        return {"uuid": resp}, 200


class GetOrganizationGroupsItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")


class GetOrganizationGroupsResponseSchema(Schema):
    groups = fields.Nested(
        GetOrganizationGroupsItemResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )
    count = fields.Integer(required=True)


class GetOrganizationGroups(ServiceApiView):
    summary = "Get organization authorized groups"
    description = "Get organization authorized groups"
    tags = ["authority"]
    definitions = {
        "GetOrganizationGroupsResponseSchema": GetOrganizationGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetOrganizationGroupsResponseSchema}}
    )
    response_schema = GetOrganizationGroupsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        res = organization.get_groups()
        return {"groups": res, "count": len(res)}


class SetOrganizationGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiOrganization.role_templates.keys()),
    )


class SetOrganizationGroupsRequestSchema(Schema):
    group = fields.Nested(SetOrganizationGroupsParamRequestSchema)


class SetOrganizationGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetOrganizationGroupsRequestSchema, context="body")


class SetOrganizationGroups(ServiceApiView):
    summary = "Set organization authorized group"
    description = "Set organization authorized group"
    tags = ["authority"]
    definitions = {
        "SetOrganizationGroupsRequestSchema": SetOrganizationGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetOrganizationGroupsBodyRequestSchema)
    parameters_schema = SetOrganizationGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data = data.get("group")
        resp = organization.set_group(**data)
        return {"uuid": resp}, 200


class UnsetOrganizationGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiOrganization.role_templates.keys()),
    )


class UnsetOrganizationGroupsRequestSchema(Schema):
    group = fields.Nested(UnsetOrganizationGroupsParamRequestSchema)


class UnsetOrganizationGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetOrganizationGroupsRequestSchema, context="body")


class UnsetOrganizationGroups(ServiceApiView):
    summary = "Unset organization authorized group"
    description = "Unset organization authorized group"
    tags = ["authority"]
    definitions = {
        "UnsetOrganizationGroupsRequestSchema": UnsetOrganizationGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetOrganizationGroupsBodyRequestSchema)
    parameters_schema = UnsetOrganizationGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        organization = controller.get_organization(oid)
        data = data.get("group")
        resp = organization.unset_group(**data)
        return {"uuid": resp}, 200


class GetActiveServicesByOrganizationApiRequestSchema(Schema):
    oid = fields.String(required=True, description="id, uuid", context="path")


class GetActiveServicesByOrganitazionResponse1Schema(Schema):
    service_container = fields.Nested(ContainerInstancesItemResponseSchema, many=True, required=True, allow_none=False)
    extraction_date = fields.DateTime(required=True)
    accounts = fields.Integer(required=True)
    divisions = fields.Integer(required=True)


class GetActiveServicesByOrganizationResponseSchema(Schema):
    services = fields.Nested(
        GetActiveServicesByOrganitazionResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class GetActiveServicesByOrganization(ServiceApiView):
    summary = (
        "Returns the active services list for an organization, for each service are provided information about "
        "resources usage"
    )
    description = (
        "Returns the active services list for an organization, for each service are provided information "
        "about resources usage"
    )
    tags = ["authority"]
    definitions = {
        "GetActiveServicesByOrganizationResponseSchema": GetActiveServicesByOrganizationResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetActiveServicesByOrganizationApiRequestSchema)
    parameters_schema = GetActiveServicesByOrganizationApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetActiveServicesByOrganizationResponseSchema,
            }
        }
    )
    response_schema = GetActiveServicesByOrganizationResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        # get division
        organization = controller.get_organization(oid)
        # get related service instant consume
        active_services = controller.get_service_instant_consume_by_organization(organization.oid)
        return {"services": active_services}


class OrganizationAPI(ApiView):
    """OrganizationAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/organizations" % base, "GET", ListOrganizations, {}),
            ("%s/organizations/<oid>" % base, "GET", GetOrganization, {}),
            ("%s/organizations" % base, "POST", CreateOrganization, {}),
            ("%s/organizations/<oid>" % base, "PUT", UpdateOrganization, {}),
            ("%s/organizations/<oid>" % base, "PATCH", PatchOrganization, {}),
            ("%s/organizations/<oid>" % base, "DELETE", DeleteOrganization, {}),
            ("%s/organizations/<oid>/perms" % base, "GET", GetOrganizationPerms, {}),
            ("%s/organizations/<oid>/roles" % base, "GET", GetOrganizationRoles, {}),
            ("%s/organizations/<oid>/users" % base, "GET", GetOrganizationUsers, {}),
            ("%s/organizations/<oid>/users" % base, "POST", SetOrganizationUsers, {}),
            (
                "%s/organizations/<oid>/users" % base,
                "DELETE",
                UnsetOrganizationUsers,
                {},
            ),
            ("%s/organizations/<oid>/groups" % base, "GET", GetOrganizationGroups, {}),
            ("%s/organizations/<oid>/groups" % base, "POST", SetOrganizationGroups, {}),
            (
                "%s/organizations/<oid>/groups" % base,
                "DELETE",
                UnsetOrganizationGroups,
                {},
            ),
            (
                "%s/organizations/<oid>/activeservices" % base,
                "GET",
                GetActiveServicesByOrganization,
                {},
            ),
        ]
        ApiView.register_api(module, rules, **kwargs)
