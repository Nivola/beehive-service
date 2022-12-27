# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiObjectRequestFiltersSchema,\
    ApiServiceObjectRequestSchema
import uuid
from beehive_service.views.agreement import GetAgreementItemResponseSchema


#
# wallet
#

## list
class ListWalletsRequestSchema(ApiServiceObjectRequestSchema,
         ApiObjectRequestFiltersSchema,
         PaginatedRequestQuerySchema):
    service_status_id=fields.Integer (required=False, context=u'query')
    capital_total=fields.Number(required=False, context=u'query')
    capital_total_min_range=fields.Number(required=False, context=u'query')
    capital_total_max_range=fields.Number(required=False, context=u'query')

    capital_used=fields.Number(required=False, context=u'query')
    capital_used_min_range=fields.Number(required=False, context=u'query')
    capital_used_max_range=fields.Number(required=False, context=u'query')

    evaluation_date=fields.DateTime(required=False, context=u'query')
    evaluation_date_start=fields.DateTime(required=False, context=u'query')
    evaluation_date_stop=fields.DateTime(required=False, context=u'query')

    division_id = fields.String (required=False, context=u'query')
    year = fields.Integer(required=False, context=u'query')

class ItemWalletsParamsResponseSchema(ApiObjectResponseSchema):
    service_status_id=fields.Integer (required=True)
    status = fields.String(required=True)
    version=fields.String(required=False, default=u'1.0')
    capital_total = fields.Number(required=False, default=0.00)
    capital_used = fields.Number(required=False, default=0.00)
    evaluation_date = fields.DateTime(required=False, default=u'1990-12-31T23:59:59Z')
    division_id = fields.String (required=False)
    year = fields.String(required=True)


class ListWalletsResponseSchema(PaginatedResponseSchema):
    wallets = fields.Nested(ItemWalletsParamsResponseSchema,
                                  many=True, required=True, allow_none=True)
# TODO ListWallets: extend filter to improve search
# TODO ListWallets: decide rule to search string filed (LIKE | EQUAL)
class ListWallets(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ListWalletsResponseSchema': ListWalletsResponseSchema,
        u'ListWalletsRequestSchema':ListWalletsRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListWalletsRequestSchema)
    parameters_schema = ListWalletsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListWalletsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        List wallets
        Call this api to list all the existing wallet
        """
        if data.get(u'division_id') is not None:
            data[u'division_id'] = controller.get_division(
                        data.get(u'division_id')).oid
        wallets, total = controller.get_wallets(**data)

        res = [r.info() for r in wallets]
        return self.format_paginated_response(res, u'wallets', total, **data)



## get perms
class GetWalletPerms(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        res, total = wallet.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)



## get
class GetWalletResponseSchema(Schema):
    wallet = fields.Nested(ItemWalletsParamsResponseSchema,
                                 required=True, allow_none=True)

class GetWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'GetWalletResponseSchema': GetWalletResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetWalletResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid, authorize=True)
        return {u'wallet':wallet.detail()}

## create
class CreateWalletParamRequestSchema(Schema):
    name = fields.String(required=False, default=u'default wallet')
    desc = fields.String(required=False, allow_none=True)
    capital_total = fields.Number(required=False, allow_none=True)
    capital_used = fields.Number(required=False, allow_none=True)
    evaluation_date = fields.DateTime(required=False, allow_none=True, default=u'1990-12-31T23:59:59Z')
    division_id = fields.String(required=True, allow_none=False)
    year = fields.Integer(required=True, allow_none=False)

class CreateWalletRequestSchema(Schema):
    wallet = fields.Nested(CreateWalletParamRequestSchema, context=u'body')

class CreateWalletBodyRequestSchema(Schema):
    body = fields.Nested(CreateWalletRequestSchema, context=u'body')

class CreateWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'CreateWalletRequestSchema': CreateWalletRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateWalletBodyRequestSchema)
    parameters_schema = CreateWalletRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        data = data.get(u'wallet')
        # check the organization and take the id reference
        data[u'division_id'] = controller.get_division(data.get(u'division_id')).oid
        # create the division

        resp = controller.add_wallet(**data)
        return ({u'uuid':resp}, 201)


## update
class UpdateWalletParamRequestSchema(Schema):
    name = fields.String(default=u'default wallet')
    desc = fields.String(default=u'default wallet')
    capital_used = fields.Number(default=0.00)
    capital_total = fields.Number(default=0.00)
    evaluation_date = fields.DateTime(default=u'1990-12-31T23:59:59Z')
    service_status_id = fields.Integer(default=6)
    version = fields.String(default=u"1.0")

class UpdateWalletRequestSchema(Schema):
    wallet = fields.Nested(UpdateWalletParamRequestSchema)

class UpdateWalletBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateWalletRequestSchema, context=u'body')

class UpdateWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'UpdateWalletRequestSchema':UpdateWalletRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateWalletBodyRequestSchema)
    parameters_schema = UpdateWalletRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.update(**data.get(u'wallet'))
        return ({u'uuid':resp}, 200)


## deledelete chain
class DeleteWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

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
    body = fields.Nested(CloseWalletRequestSchema, context=u'body')


class CloseWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'CloseWalletRequestSchema':CloseWalletRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CloseWalletBodyRequestSchema)
    parameters_schema = CloseWalletRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.close_year(**data.get(u'wallet'))
        return ({u'uuid':resp}, 200)

#Reopen Wallet
class ReopenWallet(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'GetApiObjectRequestSchema':GetApiObjectRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = GetApiObjectRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        wallet = controller.get_wallet(oid)
        resp = wallet.open_year()
        return ({u'uuid':resp}, 200)

## list
class ListWalletAgreementsRequestSchema(ApiServiceObjectRequestSchema,
         ApiObjectRequestFiltersSchema,
         PaginatedRequestQuerySchema):
    pass


class ListWalletAgreementsResponseSchema(PaginatedResponseSchema):
    agreements = fields.Nested(GetAgreementItemResponseSchema,
                                  many=True, required=True, allow_none=True)
# TODO ListAgreements: extend filter to improve search
class listWalletAgreements(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ListWalletAgreementsResponseSchema': ListWalletAgreementsResponseSchema,
        u'ListWalletAgreementsRequestSchema': ListWalletAgreementsRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListWalletAgreementsRequestSchema)
    parameters_schema = ListWalletAgreementsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListWalletAgreementsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        List Agreements by wallet id
        Call this api to list all the existing agreements
        """
        wallet = controller.get_wallet(oid)
        data[u'wallet_id'] = wallet.oid

        agreements, total = controller.get_agreements(**data)
        res = [r.info() for r in agreements]
        return self.format_paginated_response(res, u'agreements', total, **data)


class WalletAPI(ApiView):
    """WalletAPI
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/wallets' % base, u'GET', ListWallets, {}),
            (u'%s/wallets/<oid>' % base, u'GET', GetWallet, {}),
            (u'%s/wallets/<oid>/perms' % base, u'GET', GetWalletPerms, {}),
            (u'%s/wallets' % base, u'POST', CreateWallet, {}),
            (u'%s/wallets/<oid>' % base, u'PUT', UpdateWallet, {}),
            (u'%s/wallets/<oid>' % base, u'DELETE', DeleteWallet, {}),
            (u'%s/wallets/<oid>/agreements' % base, u'GET', listWalletAgreements, {}),

            (u'%s/wallets/<oid>/close' % base, u'PUT', CloseWallet, {}),
            (u'%s/wallets/<oid>/reopen' % base, u'PUT', ReopenWallet, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)