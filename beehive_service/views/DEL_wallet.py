# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import (
    ApiView,
    ApiManagerError,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
)
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from beehive_service.views import (
    ServiceApiView,
    ApiObjectRequestFiltersSchema,
    ApiServiceObjectRequestSchema,
)
import uuid
from beehive_service.views.agreement import GetAgreementItemResponseSchema


#
# wallet
#


## list
class ListWalletsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    service_status_id = fields.Integer(required=False, context="query")
    capital_total = fields.Number(required=False, context="query")
    capital_total_min_range = fields.Number(required=False, context="query")
    capital_total_max_range = fields.Number(required=False, context="query")

    capital_used = fields.Number(required=False, context="query")
    capital_used_min_range = fields.Number(required=False, context="query")
    capital_used_max_range = fields.Number(required=False, context="query")

    evaluation_date = fields.DateTime(required=False, context="query")
    evaluation_date_start = fields.DateTime(required=False, context="query")
    evaluation_date_stop = fields.DateTime(required=False, context="query")

    division_id = fields.String(required=False, context="query")
    year = fields.Integer(required=False, context="query")


class ItemWalletsParamsResponseSchema(ApiObjectResponseSchema):
    service_status_id = fields.Integer(required=True)
    status = fields.String(required=True)
    version = fields.String(required=False, default="1.0")
    capital_total = fields.Number(required=False, default=0.00)
    capital_used = fields.Number(required=False, default=0.00)
    evaluation_date = fields.DateTime(required=False, default="1990-12-31T23:59:59Z")
    division_id = fields.String(required=False)
    year = fields.String(required=True)


class ListWalletsResponseSchema(PaginatedResponseSchema):
    wallets = fields.Nested(ItemWalletsParamsResponseSchema, many=True, required=True, allow_none=True)


# TODO ListWallets: extend filter to improve search
# TODO ListWallets: decide rule to search string filed (LIKE | EQUAL)
class ListWallets(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ListWalletsResponseSchema": ListWalletsResponseSchema,
        "ListWalletsRequestSchema": ListWalletsRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListWalletsRequestSchema)
    parameters_schema = ListWalletsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ListWalletsResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        List wallets
        Call this api to list all the existing wallet
        """
        if data.get("division_id") is not None:
            data["division_id"] = controller.get_division(data.get("division_id")).oid
        wallets, total = controller.get_wallets(**data)

        res = [r.info() for r in wallets]
        return self.format_paginated_response(res, "wallets", total, **data)


## get perms
class GetWalletPerms(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        res, total = wallet.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


## get
class GetWalletResponseSchema(Schema):
    wallet = fields.Nested(ItemWalletsParamsResponseSchema, required=True, allow_none=True)


class GetWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "GetWalletResponseSchema": GetWalletResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetWalletResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid, authorize=True)
        return {"wallet": wallet.detail()}


## create
class CreateWalletParamRequestSchema(Schema):
    name = fields.String(required=False, default="default wallet")
    desc = fields.String(required=False, allow_none=True)
    capital_total = fields.Number(required=False, allow_none=True)
    capital_used = fields.Number(required=False, allow_none=True)
    evaluation_date = fields.DateTime(required=False, allow_none=True, default="1990-12-31T23:59:59Z")
    division_id = fields.String(required=True, allow_none=False)
    year = fields.Integer(required=True, allow_none=False)


class CreateWalletRequestSchema(Schema):
    wallet = fields.Nested(CreateWalletParamRequestSchema, context="body")


class CreateWalletBodyRequestSchema(Schema):
    body = fields.Nested(CreateWalletRequestSchema, context="body")


class CreateWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "CreateWalletRequestSchema": CreateWalletRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateWalletBodyRequestSchema)
    parameters_schema = CreateWalletRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        data = data.get("wallet")
        # check the organization and take the id reference
        data["division_id"] = controller.get_division(data.get("division_id")).oid
        # create the division

        resp = controller.add_wallet(**data)
        return ({"uuid": resp}, 201)


## update
class UpdateWalletParamRequestSchema(Schema):
    name = fields.String(default="default wallet")
    desc = fields.String(default="default wallet")
    capital_used = fields.Number(default=0.00)
    capital_total = fields.Number(default=0.00)
    evaluation_date = fields.DateTime(default="1990-12-31T23:59:59Z")
    service_status_id = fields.Integer(default=6)
    version = fields.String(default="1.0")


class UpdateWalletRequestSchema(Schema):
    wallet = fields.Nested(UpdateWalletParamRequestSchema)


class UpdateWalletBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateWalletRequestSchema, context="body")


class UpdateWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "UpdateWalletRequestSchema": UpdateWalletRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateWalletBodyRequestSchema)
    parameters_schema = UpdateWalletRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.update(**data.get("wallet"))
        return ({"uuid": resp}, 200)


## deledelete chain
class DeleteWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.delete(soft=True)
        return (resp, 204)


## Close wallet
## Close wallet
class CloseWalletParamRequestSchema(Schema):
    force_closure = fields.Boolean(required=False, default=False)


class CloseWalletRequestSchema(Schema):
    wallet = fields.Nested(CloseWalletParamRequestSchema)


class CloseWalletBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CloseWalletRequestSchema, context="body")


class CloseWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "CloseWalletRequestSchema": CloseWalletRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CloseWalletBodyRequestSchema)
    parameters_schema = CloseWalletRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.close_year(**data.get("wallet"))
        return ({"uuid": resp}, 200)


# Reopen Wallet
class ReopenWallet(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = GetApiObjectRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.open_year()
        return ({"uuid": resp}, 200)


## list
class ListWalletAgreementsRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    pass


class ListWalletAgreementsResponseSchema(PaginatedResponseSchema):
    agreements = fields.Nested(GetAgreementItemResponseSchema, many=True, required=True, allow_none=True)


# TODO ListAgreements: extend filter to improve search
class listWalletAgreements(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ListWalletAgreementsResponseSchema": ListWalletAgreementsResponseSchema,
        "ListWalletAgreementsRequestSchema": ListWalletAgreementsRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListWalletAgreementsRequestSchema)
    parameters_schema = ListWalletAgreementsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListWalletAgreementsResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        """
        List Agreements by wallet id
        Call this api to list all the existing agreements
        """
        wallet = controller.get_wallet(oid)
        data["wallet_id"] = wallet.oid

        agreements, total = controller.get_agreements(**data)
        res = [r.info() for r in agreements]
        return self.format_paginated_response(res, "agreements", total, **data)


class WalletAPI(ApiView):
    """WalletAPI"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/wallets" % base, "GET", ListWallets, {}),
            ("%s/wallets/<oid>" % base, "GET", GetWallet, {}),
            ("%s/wallets/<oid>/perms" % base, "GET", GetWalletPerms, {}),
            ("%s/wallets" % base, "POST", CreateWallet, {}),
            ("%s/wallets/<oid>" % base, "PUT", UpdateWallet, {}),
            ("%s/wallets/<oid>" % base, "DELETE", DeleteWallet, {}),
            ("%s/wallets/<oid>/agreements" % base, "GET", listWalletAgreements, {}),
            ("%s/wallets/<oid>/close" % base, "PUT", CloseWallet, {}),
            ("%s/wallets/<oid>/reopen" % base, "PUT", ReopenWallet, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
