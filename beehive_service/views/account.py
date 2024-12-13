# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from asyncio.log import logger
from beecell.simple import format_date
from beehive.common.apimanager import (
    ApiManagerError,
    ApiObjectResponseDateSchema,
    ApiObjectSmallResponseSchema,
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
from marshmallow import ValidationError
from marshmallow.decorators import validates_schema
from marshmallow.validate import OneOf
from beecell.swagger import SwaggerHelper
from beehive_service.controller import (
    ApiAccount,
    ServiceController,
    ApiAccountCapability,
)
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
)
from typing import List
from .check import validate_account_name, validate_acronym

try:
    from dateutil.parser import relativedelta
except ImportError as ex:
    from dateutil import relativedelta


class ListAccountsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    service_status_id = fields.Integer(required=False, context="query")
    division_id = fields.String(required=False, context="query")
    contact = fields.String(required=False, context="query")
    email = fields.String(required=False, context="query")
    email_support = fields.String(required=False, context="query")
    email_support_link = fields.String(required=False, context="query")


class AccountServiceResponseSchema(Schema):
    base = fields.Integer(required=False)
    core = fields.Integer(required=False)


class AccountResponseSchema(ApiObjectResponseSchema):
    desc = fields.String(required=False, allow_none=True, default="test", example="test")
    version = fields.String(required=False, default="1.0")
    division_id = fields.String(required=True)
    note = fields.String(required=False, allow_none=True, default="")
    contact = fields.String(required=False, allow_none=True, default="")
    email = fields.String(required=False, allow_none=True, default="")
    email_support = fields.String(required=False, allow_none=True, default="")
    email_support_link = fields.String(required=False, allow_none=True, default="")
    managed = fields.Boolean(required=False, allow_none=True, default=False)
    acronym = fields.String(required=False, allow_none=True, default="")
    # fix
    status = fields.String(required=False, allow_none=True, default="")
    division_name = fields.String(required=False, allow_none=True, default="")
    services = fields.Nested(AccountServiceResponseSchema, required=False, allow_none=True)
    account_type = fields.String(required=False, allow_none=True, default="")
    management_model = fields.String(required=False, allow_none=True, default="")
    pods = fields.String(required=False, allow_none=True, default="")


class ListAccountsResponseSchema(PaginatedResponseSchema):
    accounts = fields.Nested(AccountResponseSchema, many=True, required=True, allow_none=True)


class ListAccounts(ServiceApiView):
    summary = "List accounts"
    description = "List accounts"
    tags = ["authority"]
    definitions = {
        "ListAccountsResponseSchema": ListAccountsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountsRequestSchema)
    parameters_schema = ListAccountsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListAccountsResponseSchema}})
    response_schema = ListAccountsResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        accounts, total = controller.get_accounts(**data)
        account_ids = [a.oid for a in accounts]
        division_ids = [a.division_id for a in accounts]
        fall_back_service = {"core": 0, "base": 0}
        services = controller.count_service_instances_by_accounts(accounts=account_ids)
        divs = self.get_division_idx(controller, division_id_list=division_ids)
        res = []
        for account in accounts:
            info = account.info()
            info["division_name"] = getattr(divs[f"{account.division_id}"], "name")
            account.services = services.get(account.oid, None)
            if account.services is None:
                account.services = fall_back_service
            res.append(info)
        resp = self.format_paginated_response(res, "accounts", total, **data)
        return resp


class GetAccountResponseSchema(Schema):
    account = fields.Nested(AccountResponseSchema, required=True, allow_none=True)


class GetAccountRequestSchema(Schema):
    oid = fields.String(required=True, description="id, uuid or name", context="path")
    # filter_expired = fields.String(required=False, allow_none=True)
    filter_expired = fields.Boolean(required=False, missing=False)
    active = fields.Boolean(missing=True, allow_none=True)


class GetAccount(ServiceApiView):
    summary = "Get one account"
    description = "Get one account"
    tags = ["authority"]
    definitions = {
        "GetAccountRequestSchema": GetAccountRequestSchema,
        "GetAccountResponseSchema": GetAccountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAccountResponseSchema}})
    response_schema = GetAccountResponseSchema
    parameters_schema = GetAccountRequestSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        data.pop("oid")
        account = controller.get_account(oid, **data)
        res = account.detail()
        resp = {"account": res}
        return resp


class GetAccountPerms(ServiceApiView):
    summary = "Get account permissions"
    description = "Get account permissions"
    tags = ["authority"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res, total = account.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


class CreateAccountServiceBaseRequestSchema(Schema):
    name = fields.String(required=True, example="prova")
    type = fields.String(required=True, example="medium")


class CreateAccountServiceRequestSchema(CreateAccountServiceBaseRequestSchema):
    template = fields.String(required=False)
    params = fields.Dict(required=False, missing={})
    require = fields.Nested(CreateAccountServiceBaseRequestSchema, required=False)


class CreateAccountParamRequestSchema(Schema):
    name = fields.String(required=True, example="default", validate=validate_account_name)
    acronym = fields.String(
        required=False,
        default="default",
        example="prova",
        description="Account acronym. Set this for managed account",
        validate=validate_acronym,
    )
    desc = fields.String(required=False, allow_none=True)
    division_id = fields.String(required=True)
    price_list_id = fields.String(required=False, allow_none=True)
    note = fields.String(required=False, allow_none=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    email_support = fields.String(required=False, allow_none=True)
    email_support_link = fields.String(required=False, allow_none=True, default="")
    managed = fields.Boolean(required=False, description="if True account is managed", missing=True)
    account_type = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["csi", "ente", "private"],
            error="Field can be csi, ente, private",
        ),
    )
    management_model = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["m1", "m2", "m3"],
            error="Field can be m1, m2, m3",
        ),
    )
    pods = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["p1p2p3", "p5p6"],
            error="Field can be p1p2p3, p5p6",
        ),
    )

    @validates_schema
    def validate_parameters(self, data, *arg, **kvargs):
        managed = data.get("managed")
        if managed is True:
            acronym = data.get("acronym", None)
            if acronym is None:
                raise ValidationError("The acronym for managed account must bu specified")
            if len(acronym) > 10:
                raise ValidationError("The acronym can be up to 10 characters long")


class CreateAccountRequestSchema(Schema):
    account = fields.Nested(CreateAccountParamRequestSchema, context="body")


class CreateAccountBodyRequestSchema(Schema):
    body = fields.Nested(CreateAccountRequestSchema, context="body")


class CreateAccount(ServiceApiView):
    summary = "Create an account"
    description = "Create an account"
    tags = ["authority"]
    definitions = {
        "CreateAccountRequestSchema": CreateAccountRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateAccountBodyRequestSchema)
    parameters_schema = CreateAccountRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        # create the account
        data = data.get("account")
        resp = controller.add_account(**data)

        return {"uuid": resp}, 201


class UpdateAccountParamRequestSchema(Schema):
    name = fields.String(required=False, default="default", validate=validate_account_name)
    desc = fields.String(required=False, default="default")
    note = fields.String(required=False, default="default")
    price_list_id = fields.String(required=False, allow_none=True)
    contact = fields.String(required=False, default="default")
    email = fields.String(required=False, default="default")
    email_support = fields.String(required=False, default="default")
    email_support_link = fields.String(required=False, default="default")
    active = fields.Boolean(required=False, default=False)
    ### aggiunto 5/7/19
    acronym = fields.String(required=False, allow_none=True, default="", validate=validate_acronym)
    account_type = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["csi", "ente", "private"],
            error="Field can be csi, ente, private",
        ),
    )
    management_model = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["m1", "m2", "m3"],
            error="Field can be m1, m2, m3",
        ),
    )
    pods = fields.String(
        required=False,
        allow_none=True,
        validate=OneOf(
            ["p1p2p3", "p5p6"],
            error="Field can be p1p2p3, p5p6",
        ),
    )


class UpdateAccountRequestSchema(Schema):
    account = fields.Nested(UpdateAccountParamRequestSchema)


class UpdateAccountBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateAccountRequestSchema, context="body")


class UpdateAccount(ServiceApiView):
    summary = "Update an account"
    description = "Update an account"
    tags = ["authority"]
    definitions = {
        "UpdateAccountRequestSchema": UpdateAccountRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateAccountBodyRequestSchema)
    parameters_schema = UpdateAccountRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller: ServiceController, data: dict, oid: str, *args, **kwargs):
        data = data.get("account")
        resp = controller.update_account(oid, data)
        return {"uuid": resp}, 200


class PatchAccountParamRequestSchema(Schema):
    services = fields.Nested(CreateAccountServiceRequestSchema, required=False, allow_none=True, many=True)


class PatchAccountRequestSchema(Schema):
    account = fields.Nested(PatchAccountParamRequestSchema)


class PatchAccountBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchAccountRequestSchema, context="body")


class PatchAccount(ServiceApiView):
    summary = "Patch an account"
    description = "Patch an account"
    tags = ["authority"]
    definitions = {
        "PatchAccountRequestSchema": PatchAccountRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PatchAccountBodyRequestSchema)
    parameters_schema = PatchAccountRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def patch(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get("account")
        account.patch(**data)
        return {"uuid": account.uuid}, 200


class DeleteAccount(ServiceApiView):
    summary = "Delete an account"
    description = "Delete an account"
    tags = ["authority"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        resp = account.delete(soft=True)
        return resp, 204


class GetAccountRolesItemResponseSchema(Schema):
    role = fields.String(required=True, example="AccountAdminRole-123456")
    name = fields.String(required=True, example="master")
    desc = fields.String(required=True, example="")


class GetAccountRolesResponseSchema(Schema):
    roles = fields.Nested(GetAccountRolesItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetAccountRoles(ServiceApiView):
    summary = "Get account available logical authorization roles"
    description = "Get account available logical authorization roles"
    tags = ["authority"]
    definitions = {
        "GetAccountRolesResponseSchema": GetAccountRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAccountRolesResponseSchema}})
    response_schema = GetAccountRolesResponseSchema

    def get(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_role_templates()
        return {"roles": res, "count": len(res)}


class ApiObjectResponseDateUsersSchema(ApiObjectResponseDateSchema):
    last_login = fields.DateTime(required=False, example="1990-12-31T23:59:59Z", description="last login date")


class GetAccountUsersItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")
    email = fields.String(required=False, allow_none=True)
    taxcode = fields.String(required=False, allow_none=True)
    ldap = fields.String(required=False, allow_none=True)
    date = fields.Nested(ApiObjectResponseDateUsersSchema, required=True)


class GetAccountUsersResponseSchema(Schema):
    users = fields.Nested(GetAccountUsersItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True, example=0)


class GetAccountUsers(ServiceApiView):
    summary = "Get account authorized users"
    description = "Get account authorized users"
    tags = ["authority"]
    definitions = {
        "GetAccountUsersResponseSchema": GetAccountUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAccountUsersResponseSchema}})
    response_schema = GetAccountUsersResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_users()
        return {"users": res, "count": len(res)}


class SetAccountUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiAccount.role_templates.keys()),
    )


class SetAccountUsersRequestSchema(Schema):
    user = fields.Nested(SetAccountUsersParamRequestSchema)


class SetAccountUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetAccountUsersRequestSchema, context="body")


class SetAccountUsers(ServiceApiView):
    summary = "Set account authorized user"
    description = "Set account authorized user"
    tags = ["authority"]
    definitions = {
        "SetAccountUsersRequestSchema": SetAccountUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetAccountUsersBodyRequestSchema)
    parameters_schema = SetAccountUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller: ServiceController, data, oid, *args, **kwargs):
        account: ApiAccount = controller.get_account(oid)

        from beehive_service.model.account import Account

        model_account: Account = account.model
        if not model_account.is_active_or_closed():
            raise ApiManagerError(f"Accreditation not allowed on account {oid}")

        data = data.get("user")
        resp = account.set_user(**data)
        return {"uuid": resp}, 200


class UnsetAccountUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default="prova", description="User name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiAccount.role_templates.keys()),
    )


class UnsetAccountUsersRequestSchema(Schema):
    user = fields.Nested(UnsetAccountUsersParamRequestSchema)


class UnsetAccountUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetAccountUsersRequestSchema, context="body")


class UnsetAccountUsers(ServiceApiView):
    summary = "Unset account authorized user"
    description = "Unset account authorized user"
    tags = ["authority"]
    definitions = {
        "UnsetAccountUsersRequestSchema": UnsetAccountUsersRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetAccountUsersBodyRequestSchema)
    parameters_schema = UnsetAccountUsersRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        """
        Unset account authorized user
        remove account role frome user
        """
        account: ApiAccount = controller.get_account(oid)
        data = data.get("user")
        resp = account.unset_user(**data)
        return {"uuid": resp}, 200


class GetAccountGroupsItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example="master")


class GetAccountGroupsResponseSchema(Schema):
    groups = fields.Nested(GetAccountGroupsItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True, example=0)


class GetAccountGroups(ServiceApiView):
    summary = "Get account authorized groups"
    description = "Get account authorized groups"
    tags = ["authority"]
    definitions = {
        "GetAccountGroupsResponseSchema": GetAccountGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAccountGroupsResponseSchema}})
    response_schema = GetAccountGroupsResponseSchema

    def get(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_groups()
        return {"groups": res, "count": len(res)}


class SetAccountGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiAccount.role_templates.keys()),
    )


class SetAccountGroupsRequestSchema(Schema):
    group = fields.Nested(SetAccountGroupsParamRequestSchema)


class SetAccountGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetAccountGroupsRequestSchema, context="body")


class SetAccountGroups(ServiceApiView):
    summary = "Set account authorized group"
    description = "Set account authorized group"
    tags = ["authority"]
    definitions = {
        "SetAccountGroupsRequestSchema": SetAccountGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SetAccountGroupsBodyRequestSchema)
    parameters_schema = SetAccountGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )

    def post(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get("group")
        resp = account.set_group(**data)
        return {"uuid": resp}, 200


class UnsetAccountGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default="prova", description="Group name, id or uuid")
    role = fields.String(
        required=False,
        default="prova",
        description="Role name, id or uuid",
        validate=OneOf(ApiAccount.role_templates.keys()),
    )


class UnsetAccountGroupsRequestSchema(Schema):
    group = fields.Nested(UnsetAccountGroupsParamRequestSchema)


class UnsetAccountGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetAccountGroupsRequestSchema, context="body")


class UnsetAccountGroups(ServiceApiView):
    summary = "Unset account authorized group"
    description = "Unset account authorized group"
    tags = ["authority"]
    definitions = {
        "UnsetAccountGroupsRequestSchema": UnsetAccountGroupsRequestSchema,
        "CrudApiObjectSimpleResponseSchema": CrudApiObjectSimpleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnsetAccountGroupsBodyRequestSchema)
    parameters_schema = UnsetAccountGroupsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": CrudApiObjectSimpleResponseSchema}}
    )
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get("group")
        resp = account.unset_group(**data)
        return {"uuid": resp}, 200


class GetAccountRolesParamsResponseSchema(Schema):
    name = fields.String(required=True, example="master", description="Role name")
    id = fields.Integer(required=False, default="", description="role id")
    uuid = fields.String(required=False, default="", description="role uuid or objid")
    desc = fields.String(required=False, default="", description="Generic description")
    active = fields.Boolean(required=False, default=True, description="Describes if a user is active")
    alias = fields.String(required=False, description="role alias")


class GetAccountUsernameParamsResponseSchema(Schema):
    name = fields.String(required=True, example="", description="Username")
    id = fields.Integer(required=False, default="", description="user id")
    uuid = fields.String(required=False, default="", description="user uuid or objid")
    active = fields.Boolean(required=False, default=True, description="Describes if a user is active")
    desc = fields.String(required=False, default="", description="Generic description")
    contact = fields.String(required=False, allow_none=True, description="Primary contact Account")
    email = fields.String(required=False, allow_none=True, description="email Account")
    taxcode = fields.String(required=False, allow_none=True, description="taxcode Account")
    ldap = fields.String(required=False, allow_none=True, description="ldap Account")
    account_name = fields.String(required=False, default="", description="name of Account")
    account_status = fields.String(required=False, default="", description="status of Account")
    roles = fields.Nested(
        GetAccountRolesParamsResponseSchema,
        required=True,
        many=True,
        allow_none=True,
        description="List of roles associated with the user",
    )


class GetAccountUserRolesResponseSchema(Schema):
    usernames = fields.Nested(
        GetAccountUsernameParamsResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )


class GetAccountUserRoles(ServiceApiView):
    summary = "Get roles for all account's users"
    description = "Get roles for all account's users"
    tags = ["authority"]
    definitions = {
        "GetAccountUserRolesResponseSchema": GetAccountUserRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = GetApiObjectRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetAccountUserRolesResponseSchema}}
    )
    response_schema = GetAccountUserRolesResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        resp = account.get_username_roles()
        return resp


class AccountCapabilitiesDescriptionSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=True)
    active = fields.Boolean(required=True)


class AccountCapabilityAssociationDefinitionsSchema(ApiObjectSmallResponseSchema):
    pass


class AccountCapabilityAssociationServicesRequireSchema(Schema):
    name = fields.String(required=True)
    type = fields.String(required=True)


class AccountCapabilityAssociationServicesParamsSchema(Schema):
    vpc = fields.String(required=False)
    zone = fields.String(required=False)
    cidr = fields.String(required=False)
    protocol = fields.String(required=False)
    traffic_type = fields.String(required=False)
    persistence = fields.String(required=False)


class AccountCapabilityAssociationServicesSchema(Schema):
    template = fields.String(required=False)
    type = fields.String(required=True)
    name = fields.String(required=True)
    status = fields.String(required=True)
    require = fields.Nested(
        AccountCapabilityAssociationServicesRequireSchema,
        required=False,
        allow_none=True,
    )
    params = fields.Nested(
        AccountCapabilityAssociationServicesParamsSchema,
        required=False,
        allow_none=True,
    )


class AccountCapabilityAssociationReportServicesSchema(Schema):
    required = fields.Integer(required=False)
    created = fields.Integer(required=False)
    error = fields.Integer(required=False)


class AccountCapabilityAssociationReportDefinitionsMissedSchema(Schema):
    pass


class AccountCapabilityAssociationReportDefinitionsSchema(Schema):
    required = fields.Integer(required=False)
    created = fields.Integer(required=False)
    missed = fields.Nested(
        AccountCapabilityAssociationReportDefinitionsMissedSchema,
        required=False,
        many=True,
        allow_none=True,
    )


class AccountCapabilityAssociationReportSchema(Schema):
    services = fields.Nested(
        AccountCapabilityAssociationReportServicesSchema,
        required=False,
        allow_none=True,
    )
    definitions = fields.Nested(
        AccountCapabilityAssociationReportDefinitionsSchema,
        required=False,
        allow_none=True,
    )


class AccountCapabilityAssociationSchema(Schema):
    name = fields.String(required=True)
    status = fields.String(required=True)
    definitions = fields.Nested(
        AccountCapabilityAssociationDefinitionsSchema,
        required=True,
        many=True,
        allow_none=True,
    )
    services = fields.Nested(
        AccountCapabilityAssociationServicesSchema,
        required=True,
        many=True,
        allow_none=True,
    )
    report = fields.Nested(AccountCapabilityAssociationReportSchema, required=False, allow_none=True)


class GetAccountCapabilitiesResponseSchema(Schema):
    capabilities = fields.Nested(AccountCapabilityAssociationSchema, required=True, many=True, allow_none=True)


class GetAccountCapabilitiesRequestSchema(GetApiObjectRequestSchema):
    name = fields.String(required=False, description="name of the capability", context="query")


class GetAccountCapabilities(ServiceApiView):
    summary = "Get account capabilities"
    description = "Get account capabilities"
    tags = ["authority"]
    definitions = {
        "GetAccountCapabilitiesResponseSchema": GetAccountCapabilitiesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetAccountCapabilitiesRequestSchema)
    parameters_schema = GetAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetAccountCapabilitiesResponseSchema,
            }
        }
    )
    response_schema = GetAccountCapabilitiesResponseSchema

    def get(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        capabilities = account.get_capabilities_list()
        if data.get("name", None) is not None:
            resp = []
            for cap in capabilities:
                if cap.get("name") == data.get("name"):
                    resp = [cap]
                    break
        else:
            resp = capabilities

        resp = {"capabilities": resp}
        return resp, 200


class AddAccountCapabilitiesRequestSchema(Schema):
    capabilities = fields.List(fields.String(required=True, allow_none=False), required=True, allow_none=False)


class AddAccountCapabilitiesBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(AddAccountCapabilitiesRequestSchema, context="body")


class AddAccountCapabilitiesResponseSchema(Schema):
    taskid = fields.UUID(
        default="db078b20-19c6-4f0e-909c-94745de667d4",
        example="6d960236-d280-46d2-817d-f3ce8f0aeff7",
        required=True,
    )


class AddAccountCapabilities(ServiceApiView):
    """Add account capability

    Args:
        ServiceApiView (_type_): _description_

    Returns:
        _type_: _description_
    """

    summary = "Add account capability"
    description = "Add account capability"
    tags = ["authority"]
    definitions = {
        "AddAccountCapabilitiesRequestSchema": AddAccountCapabilitiesRequestSchema,
        "AddAccountCapabilitiesBodyRequestSchema": AddAccountCapabilitiesBodyRequestSchema,
    }

    parameters = SwaggerHelper().get_parameters(AddAccountCapabilitiesBodyRequestSchema)
    parameters_schema = AddAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": AddAccountCapabilitiesResponseSchema,
            },
        }
    )
    response_schema = AddAccountCapabilitiesResponseSchema

    def post(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        capabilities: str = data.get("capabilities")
        if len(capabilities) > 1:
            raise ApiManagerError("no more than a capability at a time can be added")
        capability = capabilities[0]
        resp = account.add_capability(capability)
        return resp


class UpdateAccountCapabilitiesRequestSchema(Schema):
    capabilities = fields.List(fields.String(required=True, allow_none=False), required=True, allow_none=False)


class UpdateAccountCapabilitiesBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateAccountCapabilitiesRequestSchema, context="body")


class UpdateAccountCapabilitiesResponseSchema(Schema):
    taskid = fields.UUID(
        default="db078b20-19c6-4f0e-909c-94745de667d4",
        example="6d960236-d280-46d2-817d-f3ce8f0aeff7",
        required=True,
    )


class UpdateAccountCapabilities(ServiceApiView):
    """Update account capability

    Args:
        ServiceApiView (_type_): _description_

    Returns:
        _type_: _description_
    """

    summary = "Update account capability"
    description = "Update account capability"
    tags = ["authority"]
    definitions = {
        "UpdateAccountCapabilitiesRequestSchema": UpdateAccountCapabilitiesRequestSchema,
        "UpdateAccountCapabilitiesBodyRequestSchema": UpdateAccountCapabilitiesBodyRequestSchema,
    }

    parameters = SwaggerHelper().get_parameters(UpdateAccountCapabilitiesBodyRequestSchema)
    parameters_schema = UpdateAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": UpdateAccountCapabilitiesResponseSchema,
            },
        }
    )
    response_schema = UpdateAccountCapabilitiesResponseSchema

    def put(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        capabilities: str = data.get("capabilities")
        if len(capabilities) > 1:
            raise ApiManagerError("no more than a capability at a time can be updated")
        capability = capabilities[0]
        resp = account.update_capability(capability)
        return resp


class ListAccountTagsItemResponseSchema(ApiObjectResponseSchema):
    services = fields.Integer(required=False, default=0, missing=0)
    links = fields.Integer(required=False, default=0, missing=0)
    version = fields.Integer(required=False, allow_none=True)
    ownerAlias = fields.String(required=False, allow_none=True)


class ListAccountTagsResponseSchema(PaginatedResponseSchema):
    tags = fields.Nested(ListAccountTagsItemResponseSchema, required=True, many=True, allow_none=True)


class ListAccountTagsRequestSchema(
    GetApiObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    pass


class ListAccountTags(ServiceApiView):
    summary = "Get account tags"
    description = "Get account tags"
    tags = ["authority"]
    definitions = {
        "ListAccountTagsResponseSchema": ListAccountTagsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountTagsRequestSchema)
    parameters_schema = ListAccountTagsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListAccountTagsResponseSchema}})
    response_schema = ListAccountTagsResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        objid_filter = controller.get_account(oid).objid + "%"
        res, total = controller.get_tags(objid=objid_filter)

        resp = [r.info() for r in res]
        resp = self.format_paginated_response(resp, "tags", total, **data)
        return resp


class GetActiveServicesByAccountApiRequestSchema(Schema):
    oid = fields.String(required=True, description="id, uuid", context="path")
    plugin_name = fields.String(required=False, description="plugin name", context="query")


class MetricsItemResponseSchema(Schema):
    metric = fields.String(required=True, example="ram", description="metric name")
    value = fields.Float(required=True, example=0.0, description="metric value consumed")
    unit = fields.String(required=True, example="Gb", description="metric unit")
    quota = fields.Float(
        required=False,
        allow_none=True,
        example=0.0,
        description="Total quota available on container",
    )


class ContainerInstancesItemResponseSchema(Schema):
    name = fields.String(required=True, example="computeservice-medium", description="service name")
    uuid = fields.String(
        required=True,
        example="148175b2-948a-4567-9ecd-9c80425fc8f0",
        description="service uuid",
    )
    status = fields.String(required=True, example="ACTIVE", description="service status")
    plugin_type = fields.String(
        required=True,
        example="ComputeService",
        description="Service container plugin name",
    )
    desc = fields.String(required=False)
    instances = fields.Integer(required=True, example=0, description="Num. instances")
    tot_metrics = fields.Nested(MetricsItemResponseSchema, many=True, required=True, allow_none=True)
    extraction_date = fields.DateTime(
        required=False,
        example="1990-12-31T23:59:59Z",
        description="metric extraction date",
    )


class GetActiveServicesByAccountResponse1Schema(Schema):
    service_container = fields.Nested(ContainerInstancesItemResponseSchema, many=True, required=True, allow_none=False)
    extraction_date = fields.DateTime(required=True)


class GetActiveServicesByAccountResponseSchema(Schema):
    services = fields.Nested(
        GetActiveServicesByAccountResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class GetActiveServicesByAccount(ServiceApiView):
    summary = (
        "Returns the active services list for an account, for each service are provided information about "
        "resources usage"
    )
    description = (
        "Returns the active services list for an account, for each service are provided information "
        "about resources usage"
    )
    tags = ["authority"]
    definitions = {
        "GetActiveServicesByAccountApiRequestSchema": GetActiveServicesByAccountApiRequestSchema,
        "GetActiveServicesByAccountResponseSchema": GetActiveServicesByAccountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetActiveServicesByAccountApiRequestSchema)
    parameters_schema = GetActiveServicesByAccountApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetActiveServicesByAccountResponseSchema,
            }
        }
    )
    response_schema = GetActiveServicesByAccountResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        # get account
        account = controller.get_account(oid)
        # get related service instant consume
        active_services = controller.get_service_instant_consume_by_account(
            account.oid, plugin_name=data.get("plugin_name", None)
        )

        return {"services": active_services}


class SetSessionResponseSchema(Schema):
    msg = fields.String()


class AccountOperationApiRequestSchema(Schema):
    oid = fields.String(required=True, description="id, uuid", context="path")


class AdministerAccount(ServiceApiView):
    summary = "Set current session permission as account Administrator"
    description = "Set current session permission as account Administrator"
    tags = ["authority"]
    definitions = {"SetSessionResponseSchema": SetSessionResponseSchema}
    parameters = SwaggerHelper().get_parameters(AccountOperationApiRequestSchema)
    # parameters_schema = AccountOperationApiRequestSchema

    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": SetSessionResponseSchema,
            }
        }
    )
    response_schema = SetSessionResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        # get account
        role = ApiAccount.MASTER
        account = controller.get_account(oid)
        account.play_role(role)
        return {"msg": f"you are now {role} of {account.name}"}


class ViewAccount(ServiceApiView):
    summary = "Set current session permission as Account Viewer Role"
    description = "Set current session permission as account Viewer"
    tags = ["authority"]
    definitions = {"SetSessionResponseSchema": SetSessionResponseSchema}
    parameters = SwaggerHelper().get_parameters(AccountOperationApiRequestSchema)
    # parameters_schema = AccountOperationApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": SetSessionResponseSchema,
            }
        }
    )
    response_schema = SetSessionResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        # get account
        role = ApiAccount.VIEWER
        account = controller.get_account(oid)
        account.play_role(role)
        return {"msg": f"you are now {role} of {account.name}"}


class OperateAccount(ServiceApiView):
    summary = "Set current session permission as Account Operator Role"
    description = "Set current session permission as account Operator"
    tags = ["authority"]
    definitions = {"SetSessionResponseSchema": SetSessionResponseSchema}
    parameters = SwaggerHelper().get_parameters(AccountOperationApiRequestSchema)
    # parameters_schema = AccountOperationApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": SetSessionResponseSchema,
            }
        }
    )
    response_schema = SetSessionResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        # get account
        role = ApiAccount.OPERATOR
        account = controller.get_account(oid)
        account.play_role(role)
        return {"msg": f"you are now {role} of {account.name}"}


class AccountAPI(ApiView):
    """AccountAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/accounts" % base, "GET", ListAccounts, {}),
            ("%s/accounts/<oid>" % base, "GET", GetAccount, {}),
            ("%s/accounts" % base, "POST", CreateAccount, {}),
            ("%s/accounts/<oid>" % base, "PUT", UpdateAccount, {}),
            ("%s/accounts/<oid>" % base, "PATCH", PatchAccount, {}),
            ("%s/accounts/<oid>" % base, "DELETE", DeleteAccount, {}),
            ("%s/accounts/<oid>/manage" % base, "GET", AdministerAccount, {}),
            ("%s/accounts/<oid>/view" % base, "GET", ViewAccount, {}),
            ("%s/accounts/<oid>/operate" % base, "GET", OperateAccount, {}),
            ("%s/accounts/<oid>/perms" % base, "GET", GetAccountPerms, {}),
            ("%s/accounts/<oid>/roles" % base, "GET", GetAccountRoles, {}),
            ("%s/accounts/<oid>/users" % base, "GET", GetAccountUsers, {}),
            ("%s/accounts/<oid>/users" % base, "POST", SetAccountUsers, {}),
            ("%s/accounts/<oid>/users" % base, "DELETE", UnsetAccountUsers, {}),
            ("%s/accounts/<oid>/groups" % base, "GET", GetAccountGroups, {}),
            ("%s/accounts/<oid>/groups" % base, "POST", SetAccountGroups, {}),
            ("%s/accounts/<oid>/groups" % base, "DELETE", UnsetAccountGroups, {}),
            # ('%s/accounts/<oid>/tasks' % base, 'GET', GetAccountUserTasks, {}),
            (
                "%s/accounts/<oid>/capabilities" % base,
                "GET",
                GetAccountCapabilities,
                {},
            ),
            (
                "%s/accounts/<oid>/capabilities" % base,
                "POST",
                AddAccountCapabilities,
                {},
            ),
            (
                "%s/accounts/<oid>/capabilities" % base,
                "PUT",
                UpdateAccountCapabilities,
                {},
            ),
            ("%s/accounts/<oid>/userroles" % base, "GET", GetAccountUserRoles, {}),
            ("%s/accounts/<oid>/tags" % base, "GET", ListAccountTags, {}),
            (
                "%s/accounts/<oid>/activeservices" % base,
                "GET",
                GetActiveServicesByAccount,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
