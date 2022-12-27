# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import  PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema,\
    SwaggerApiView,\
    ApiView, ApiManagerWarning
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectResponseSchema,\
    ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,\
    ApiBaseServiceObjectCreateRequestSchema



## get
class GetServicePriceListParamsResponseSchema(ApiServiceObjectResponseSchema):
    flag_default = fields.Boolean(required=False)

class GetServicePriceListResponseSchema(Schema):
    price_list = fields.Nested(GetServicePriceListParamsResponseSchema,
                             required=True, allow_none=True)

class GetServicePriceList(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServicePriceListResponseSchema': GetServicePriceListResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServicePriceListResponseSchema
        }
    })
    response_schema = GetServicePriceListResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_price_list(oid)
        return {u'price_list':servicepricelist.detail()}


## list
class ListServicePriceListRequestSchema(ApiServiceObjectRequestSchema,
                                   ApiObjectRequestFiltersSchema,
                                   PaginatedRequestQuerySchema):
    flag_default = fields.Boolean(Required=False, context=u'query')


class ListServicePriceListResponseSchema(PaginatedResponseSchema):
    price_list = fields.Nested(GetServicePriceListParamsResponseSchema,
                                  many=True, required=True, allow_none=True)


class ListServicePriceList(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServicePriceListResponseSchema': ListServicePriceListResponseSchema,
        u'ListServicePriceListRequestSchema': ListServicePriceListRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServicePriceListRequestSchema)
    parameters_schema = ListServicePriceListRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServicePriceListResponseSchema
        }
    })
    response_schema = ListServicePriceListResponseSchema

    def get(self, controller, data,   *args, **kwargs):
        service_price_list, total = controller.get_service_price_lists( **data)
        res = [r.info() for r in service_price_list]
        res_dict = self.format_paginated_response(res, u'price_list', total, **data)
        return res_dict


## create
class CreateServicePriceListParamRequestSchema(ApiBaseServiceObjectCreateRequestSchema):
    flag_default = fields.Boolean(required=False)


class CreateServicePriceListRequestSchema(Schema):
    price_list = fields.Nested(CreateServicePriceListParamRequestSchema,
                                 context=u'body')


class CreateServicePriceListBodyRequestSchema(Schema):
    body = fields.Nested(CreateServicePriceListRequestSchema, context=u'body')


class CreateServicePriceList(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateServicePriceListRequestSchema': CreateServicePriceListRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServicePriceListBodyRequestSchema)
    parameters_schema = CreateServicePriceListRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        data = data.get(u'price_list')

        resp = controller.add_service_price_list(**data)
        return ({u'uuid':resp}, 201)


## update
class UpdateServicePriceListParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    flag_default = fields.Boolean(required=False, allow_none=True)


class UpdateServicePriceListRequestSchema(Schema):
    price_list = fields.Nested(UpdateServicePriceListParamRequestSchema)


class UpdateServicePriceListBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServicePriceListRequestSchema, context=u'body')


class UpdateServicePriceList(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateServicePriceListRequestSchema':UpdateServicePriceListRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServicePriceListBodyRequestSchema)
    parameters_schema = UpdateServicePriceListRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_price_list(oid)

        data = data.get(u'price_list')
        flag_default = data.get(u'flag_default', None)

        if flag_default:
            # remove current flag_default
            srv_pl_default = controller.get_service_price_list_default()
            if srv_pl_default:
                srv_pl_default.update(flag_default = False)

        resp = srv_pl.update(**data)

        return ({u'uuid':resp}, 200)


class DeleteServicePriceList(ServiceApiView):
    tags = [u'service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_price_list(oid, for_update = True)
        if srv_pl.flag_default is True:
            raise ApiManagerWarning(u'You can\'t delete current default' \
                            u' Price List. Set as default another price list'\
                            u' and try again!')
        if srv_pl.is_used():
            raise ApiManagerWarning(u'You can\'t delete Price List associated'\
                                    u' to account or division entity!')
        # the price list is not used can be removed
#         resp = srv_pl.delete(soft=True)
        resp = srv_pl.expunge()
        return (resp, 204)


## get perms
class GetServicePriceListPerms(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_price_list(oid)
        res, total = servicepricelist.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)


class ServicePriceListAPI(ApiView):
    """ServiceInstance api routes:
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/pricelists' % base, u'GET', ListServicePriceList, {}),
            (u'%s/pricelists' % base, u'POST', CreateServicePriceList, {}),
            (u'%s/pricelists/<oid>' % base, u'GET', GetServicePriceList, {}),
            (u'%s/pricelists/<oid>' % base, u'PUT', UpdateServicePriceList, {}),
            (u'%s/pricelists/<oid>' % base, u'DELETE', DeleteServicePriceList, {}),
            (u'%s/pricelists/<oid>/perms' % base, u'GET', GetServicePriceListPerms, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
