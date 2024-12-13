# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.controller.api_division import ApiDivision
from beehive_service.controller.api_orgnization import ApiOrganization
from beehive_service.entity.service_definition import ApiServiceDefinition
from beecell.simple import format_date
from beehive.common.apimanager import (
    ApiObjectMetadataResponseSchema,
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
    CrudApiObjectTaskResponseSchema,
)
from flasgger import fields, Schema
from marshmallow import ValidationError
from marshmallow.decorators import validates_schema
from marshmallow.validate import OneOf
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ApiAccount, ServiceController
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
)
from beehive_service.views import ApiServiceObjectResponseSchema
from beehive_service.service_util import __SRV_SERVICE_CATEGORY__, __SRV_PLUGIN_TYPE__
from typing import List

API_ACCOUNT_VERSION = "v2.0"


try:
    from dateutil.parser import relativedelta
except ImportError as ex:
    from dateutil import relativedelta


class ListAccountsV20RequestSchema(
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


class AccountResponseSchema(ApiObjectResponseSchema):
    service_status_id = fields.Integer(required=False, default=6)
    version = fields.String(required=False, default="1.0")
    division_id = fields.String(required=True)
    note = fields.String(required=False, allow_none=True, default="")
    contact = fields.String(required=False, allow_none=True, default="")
    email = fields.String(required=False, allow_none=True, default="")
    email_support = fields.String(required=False, allow_none=True, default="")
    email_support_link = fields.String(required=False, allow_none=True, default="")
    managed = fields.Boolean(required=False, allow_none=True, default=False)
    acronym = fields.String(required=False, allow_none=True, default="")
    account_type = fields.String(required=False, allow_none=True, default="")
    management_model = fields.String(required=False, allow_none=True, default="")
    pods = fields.String(required=False, allow_none=True, default="")


class ListAccountsV20ResponseSchema(PaginatedResponseSchema):
    accounts = fields.Nested(AccountResponseSchema, many=True, required=True, allow_none=True)


class ListAccountsV20(ServiceApiView):
    summary = "List accounts"
    description = "List accounts"
    tags = ["authority"]
    definitions = {
        "ListAccountsV20ResponseSchema": ListAccountsV20ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountsV20RequestSchema)
    parameters_schema = ListAccountsV20RequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListAccountsV20ResponseSchema}})
    response_schema = ListAccountsV20ResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        accounts, total = controller.get_accounts(**data)

        # get divs
        divs = self.get_division_idx(controller)

        services = controller.count_service_instances_by_accounts()
        for entity in accounts:
            entity.services = services.get(entity.oid, None)
            if entity.services is None:
                entity.services = {"core": 0, "base": 0}

        res = []
        for r in accounts:
            info = r.info(version=API_ACCOUNT_VERSION)
            info["division_name"] = getattr(divs[str(r.division_id)], "name")
            res.append(info)
        resp = self.format_paginated_response(res, "accounts", total, **data)
        return resp


class GetAccountV20ResponseSchema(Schema):
    account = fields.Nested(AccountResponseSchema, required=True, allow_none=True)


class GetAccountV20(ServiceApiView):
    summary = "Get one account"
    description = "Get one account"
    tags = ["authority"]
    definitions = {
        "GetAccountV20ResponseSchema": GetAccountV20ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAccountV20ResponseSchema}})
    response_schema = GetAccountV20ResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.detail(version=API_ACCOUNT_VERSION)
        resp = {"account": res}
        return resp


class DeleteAccountV20RequestSchema(Schema):
    delete_services = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        context="query",
        description="if True delete all child services before remove the account",
    )
    delete_tags = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        context="query",
        description="if True delete all child tags before remove the account",
    )
    close_account = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        context="query",
        description="if True close the account",
    )


class DeleteAccountV20RequestSchema2(GetApiObjectRequestSchema, DeleteAccountV20RequestSchema):
    pass


class DeleteAccountV20(ServiceApiView):
    summary = "Delete an account"
    description = "Delete an account"
    tags = ["authority"]
    definitions = {
        "DeleteAccountV20RequestSchema": DeleteAccountV20RequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteAccountV20RequestSchema2)
    parameters_schema = DeleteAccountV20RequestSchema
    responses = ServiceApiView.setResponses(
        {
            204: {"description": "no response"},
            201: {"description": "success", "schema": CrudApiObjectTaskResponseSchema},
        }
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        data["soft"] = True
        account: ApiAccount = controller.get_account(oid)
        resp = account.delete(**data)
        return resp


class GetAccountDefinitionsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    oid = fields.String(required=False, context="path", description="account id")
    plugintype = fields.String(
        required=False,
        context="query",
        description="plugin type name",
        validate=OneOf(__SRV_PLUGIN_TYPE__),
    )
    category = fields.String(
        required=False,
        context="query",
        description="definiton category",
        validate=OneOf(__SRV_SERVICE_CATEGORY__),
    )
    only_container = fields.Boolean(
        required=False,
        context="query",
        description="if True select only definition with type that is a container",
    )


class GetAccountDefinitionsSchema(ApiServiceObjectResponseSchema):
    service_type_id = fields.String(required=False, allow_none=True)
    status = fields.String(Required=False, allow_none=True)
    is_default = fields.Boolean(required=False, allow_none=True)
    category = fields.String(required=False, allow_none=True)
    plugintype = fields.String(required=False, allow_none=True)
    is_a = fields.String(required=False, allow_none=True)


class GetAccountDefinitionsResponseSchema(PaginatedResponseSchema):
    definitions = fields.Nested(GetAccountDefinitionsSchema, many=True, required=True, allow_none=True)


class GetAccountDefinitions(ServiceApiView):
    summary = "Get Account available Service Definitions"
    description = "Get Account available Service Definitions"
    tags = ["authority"]
    definitions = {
        "GetAccountDefinitionsRequestSchema": GetAccountDefinitionsRequestSchema,
        "GetAccountDefinitionsResponseSchema": GetAccountDefinitionsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetAccountDefinitionsRequestSchema)
    parameters_schema = GetAccountDefinitionsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetAccountDefinitionsResponseSchema}}
    )
    response_schema = GetAccountDefinitionsResponseSchema

    def get(self, controller: ServiceController, data: dict, oid: str, *args, **kwargs):
        data["page"] = int(data.get("page", 0))
        data["size"] = int(data.get("size", 10))
        account: ApiAccount = controller.get_account(oid)
        # defs: List[ApiServiceDefinition]
        defs, tot = account.get_definitions(**data)
        # resp = [{'name': d.name, 'category': d.service_category,
        #         'plugintype': d.plugin_name, 'is_a': d.hierarchical_category} for d in defs]
        resp = []
        for d in defs:
            info = d.info()
            info.update(
                {
                    "category": d.service_category,
                    "plugintype": d.plugin_name,
                    "is_a": d.hierarchical_category,
                }
            )
            resp.append(info)
        return self.format_paginated_response(resp, "definitions", tot, **data)


class AddAccountDefinitionsRequestSchema(Schema):
    definitions = fields.List(fields.String(), required=True, description="list of service definition uuid")


class AddAccountDefinitionsBodyRequestSchema(Schema):
    oid = fields.String(required=False, context="path", description="account id")
    body = fields.Nested(AddAccountDefinitionsRequestSchema, context="body")


class AddAccountDefinitionsResponseSchema(PaginatedResponseSchema):
    definitions = fields.List(fields.String(), required=True, description="list of service definition uuid")


class AddAccountDefinitions(ServiceApiView):
    summary = "Get Account available Service Definitions"
    description = "Get Account available Service Definitions"
    tags = ["authority"]
    definitions = {
        "AddAccountDefinitionsRequestSchema": AddAccountDefinitionsRequestSchema,
        "AddAccountDefinitionsResponseSchema": AddAccountDefinitionsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(AddAccountDefinitionsBodyRequestSchema)
    parameters_schema = AddAccountDefinitionsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": AddAccountDefinitionsResponseSchema}}
    )
    response_schema = AddAccountDefinitionsResponseSchema

    def post(self, controller: ServiceController, data: dict, oid: str, *args, **kwargs):
        account: ApiAccount = controller.get_account(oid)
        definitions = data.get("definitions")
        res = []
        for definition in definitions:
            try:
                apidefinition = controller.check_service_definition(definition)
                controller.add_account_service_definition(
                    account.oid,
                    apidefinition.oid,
                    account=account,
                    servicedefinition=apidefinition,
                )
                res.append(apidefinition.uuid)
            except Exception as ex:
                self.logger.warning("error adding service definition %s in account %s: %s" % (definition, oid, ex))
                raise ex

        return {"definitions": res}


class CheckAccountRequestSchema(Schema):
    oid = fields.String(required=False, context="path", description="account id")


class CheckAccountResponseSchema(PaginatedResponseSchema):
    account = fields.Nested(AccountResponseSchema, required=True, allow_none=True)


class CheckAccount(ServiceApiView):
    summary = "Check account"
    description = "Check account"
    tags = ["authority"]
    definitions = {
        "CheckAccountRequestSchema": CheckAccountRequestSchema,
        "CheckAccountResponseSchema": CheckAccountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CheckAccountRequestSchema)
    parameters_schema = CheckAccountRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CheckAccountResponseSchema}})
    response_schema = CheckAccountResponseSchema

    # override service default
    authorizable = False

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        self.logger.debug("CheckAccount - data: %s" % data)
        triplet: str = oid
        oid = triplet.split(".")
        accounts = None

        # override authorize default of get_paginated_entities and get_entity
        if len(oid) == 1:
            accounts, total = controller.get_accounts(name=oid[0], authorize=False)
        elif len(oid) == 2:
            # get division
            division: ApiDivision = controller.get_division(oid[0], authorize=False)
            # get account
            accounts, total = controller.get_accounts(name=oid[1], division_id=division.oid, authorize=False)
        elif len(oid) == 3:
            # get organization
            organization: ApiOrganization = controller.get_organization(oid[0], authorize=False)
            # get division
            division: ApiDivision = controller.get_division(oid[1], organization_id=organization.oid, authorize=False)
            # get account
            accounts, total = controller.get_accounts(name=oid[2], division_id=division.oid, authorize=False)

        resp = {}
        if accounts and total == 1:
            account: ApiAccount = accounts[0]
            resp = {"uuid": account.uuid}

        if total > 1:
            raise Exception("There are some account with name %s. Select one using uuid" % triplet)
        if total == 0:
            raise Exception("The account %s does not exist" % triplet)

        return resp


class AccountV20API(ApiView):
    """AccountAPI version 2.0"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/accounts/<oid>/checkname" % base, "GET", CheckAccount, {"secure": False}),
            ("%s/accounts" % base, "GET", ListAccountsV20, {}),
            ("%s/accounts/<oid>" % base, "GET", GetAccountV20, {}),
            ("%s/accounts/<oid>" % base, "DELETE", DeleteAccountV20, {}),
            ("%s/accounts/<oid>/definitions" % base, "GET", GetAccountDefinitions, {}),
            ("%s/accounts/<oid>/definitions" % base, "POST", AddAccountDefinitions, {}),
            # ('%s/accounts/<oid>/definitions' % base, 'DELETE', DelAccountDefinitions, {}),
        ]

        kwargs["version"] = API_ACCOUNT_VERSION
        ApiView.register_api(module, rules, **kwargs)
