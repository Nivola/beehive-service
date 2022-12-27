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
from beehive_service.service_util import __PRICE_TIME_UNIT__ ,__PRICE_TYPE__
from marshmallow.validate import OneOf

class CrudServicePriceMetricThresholdSchema(Schema):
    price = fields.Float(required=True)
    ammount_from = fields.Float(required=True)
    ammount_till = fields.Float(required=False)


class GetServicePriceMetricParamsResponseSchema(ApiServiceObjectResponseSchema):
    price = fields.Float(required=True)
    time_unit = fields.String(required=True)
    metric_type_id = fields.String(required=True)
    price_list_id = fields.String(required=True)
    metric_type_name = fields.String(required=False)
    price_list_name = fields.String(required=False)
    price_type = fields.String(required=False)
    thresholds = fields.Nested(CrudServicePriceMetricThresholdSchema,required=False, allow_none=True, many=True )

class GetServicePriceMetricResponseSchema(Schema):
    price_metric = fields.Nested(GetServicePriceMetricParamsResponseSchema, required=True, allow_none=True)


class GetServicePriceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServicePriceMetricResponseSchema': GetServicePriceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServicePriceMetricResponseSchema
        }
    })
    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_price_metric(oid)
        return {u'price_metric': servicepricelist.detail()}


class ListServicePriceMetricRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                          PaginatedRequestQuerySchema):
    price_list_id = fields.String(Required=True, context=u'query')
    metric_type_id = fields.Integer(Required=False, context=u'query')
    time_unit = fields.String(Required=False, context=u'query')


class ListServicePriceMetricResponseSchema(PaginatedResponseSchema):
    price_metric = fields.Nested(GetServicePriceMetricParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServicePriceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServicePriceMetricResponseSchema': ListServicePriceMetricResponseSchema,
        u'ListServicePriceMetricRequestSchema': ListServicePriceMetricRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServicePriceMetricRequestSchema)
    parameters_schema = ListServicePriceMetricRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServicePriceMetricResponseSchema
        }
    })
    response_schema = ListServicePriceMetricResponseSchema

    def get(self, controller, data, *args, **kwargs):
        service_price_metric, total = controller.get_service_price_metrics(**data)
        res = [r.info() for r in service_price_metric]
        res_dict = self.format_paginated_response(res, u'price_metric', total, **data)
        return res_dict


class CreateServicePriceMetricParamRequestSchema(ApiBaseServiceObjectCreateRequestSchema):
    price = fields.Float(required=True)
    metric_type_id = fields.String(required=True)
    price_list_id = fields.String(required=True)
    time_unit = fields.String(required=True, validate=OneOf(__PRICE_TIME_UNIT__))
    price_type = fields.String(required=False, validate=OneOf(__PRICE_TYPE__))
    thresholds = fields.Nested(CrudServicePriceMetricThresholdSchema, required=False, allow_none=True, many=True )


class CreateServicePriceMetricRequestSchema(Schema):
    price_metric = fields.Nested(CreateServicePriceMetricParamRequestSchema, context=u'body')


class CreateServicePriceMetricBodyRequestSchema(Schema):
    body = fields.Nested(CreateServicePriceMetricRequestSchema, context=u'body')


class CreateServicePriceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateServicePriceMetricRequestSchema': CreateServicePriceMetricRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServicePriceMetricBodyRequestSchema)
    parameters_schema = CreateServicePriceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    def post(self, controller, data, *args, **kwargs):
        data = data.get(u'price_metric')

        resp = controller.add_service_price_metric(**data)
        return {u'uuid': resp}, 201


class UpdateServicePriceMetricParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    price = fields.Float(required=False, allow_none=True)
    metric_type_id = fields.Integer(required=False, allow_none=True)
    price_list_id = fields.Integer(required=False, allow_none=True)
    time_unit = fields.String(required=False, allow_none=True, validate=OneOf(__PRICE_TIME_UNIT__))
    # thresholds = fields.Nested(CrudServicePriceMetricThresholdSchema, required=False, allow_none=True, many=True )
    thresholds = fields.Nested(CrudServicePriceMetricThresholdSchema, required=False,  many=True )


class UpdateServicePriceMetricRequestSchema(Schema):
    price_metric = fields.Nested(UpdateServicePriceMetricParamRequestSchema)


class UpdateServicePriceMetricBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServicePriceMetricRequestSchema, context=u'body')


class UpdateServicePriceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateServicePriceMetricRequestSchema':UpdateServicePriceMetricRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServicePriceMetricBodyRequestSchema)
    parameters_schema = UpdateServicePriceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        data = data.get(u'price_metric')
        srv_mt = controller.get_service_price_metric(oid=oid)

        resp = srv_mt.update(**data)
        return {u'uuid': resp}, 200


class DeleteServicePriceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        resp = None
        srv_pm = controller.get_service_price_metric(oid)
        srv_price = controller.get_service_price_list(srv_pm.price_list_id, for_update=False)
        if srv_price.is_used():
            raise ApiManagerWarning(u'You can\'t delete Price Metric associated to used Price List!')

#         resp = srv_pm.delete(soft=True)
        resp = srv_pm.expunge()
        return resp, 204


class GetServicePriceMetricPerms(ServiceApiView):
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
    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_price_metric(oid)
        res, total = servicepricelist.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)


class ServicePriceMetricAPI(ApiView):
    """ServiceInstance api routes:
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/prices/metrics' % base, u'GET', ListServicePriceMetric, {}),
            (u'%s/prices/metrics' % base, u'POST', CreateServicePriceMetric, {}),
            (u'%s/prices/metrics/<oid>' % base, u'GET', GetServicePriceMetric, {}),
            (u'%s/prices/metrics/<oid>' % base, u'PUT', UpdateServicePriceMetric, {}),
            (u'%s/prices/metrics/<oid>' % base, u'DELETE', DeleteServicePriceMetric, {}),
            (u'%s/prices/metrics/<oid>/perms' % base, u'GET', GetServicePriceMetricPerms, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
