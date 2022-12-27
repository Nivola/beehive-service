# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import  PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, \
    GetApiObjectRequestSchema, \
    SwaggerApiView, ApiView, ApiObjectResponseDateSchema
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView
from beehive_service.service_util import __PLATFORM_NAME__
from marshmallow.validate import OneOf
from beecell.simple import format_date

# # get
class GetServiceMetricConsumeViewParamsResponseSchema(Schema):
    metric_id = fields.Integer(required=True,  example=10)
    value = fields.Float(required=True)
    metric_num = fields.Integer(required=True)
    type_id = fields.Integer(required=True)
    type_name = fields.String(required=True)
    instance_id = fields.Integer(required=True)
    account_id = fields.Integer(required=True)
    job_id = fields.Integer(required=True)
    extraction_date = fields.DateTime(required=True,  example=u'1990-12-31T23:59:59Z')
    
    @staticmethod
    def detail(m):
        res = {u'metric_id': m.id,
                u'value': m.value,
                u'metric_num': m.metric_num,
                u'type_id': m.metric_type_id,
                u'type_name': m.metric_type_name,
                u'instance_id': m.service_instance_id,
                u'account_id': m.account_id,
                u'job_id': m.job_id,
                u'extraction_date': format_date(m.extraction_date),
            }
        return res
    
    
class GetServiceMetricConsumeViewResponseSchema(Schema):
    metric_consume = fields.Nested(GetServiceMetricConsumeViewParamsResponseSchema,
                             required=True, allow_none=True)


class GetServiceMetricConsumeView(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServiceMetricConsumeViewResponseSchema': GetServiceMetricConsumeViewResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServiceMetricConsumeViewResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        metric_consume_view = controller.get_service_metric_consume_view(oid)
        return {u'metric_consume': GetServiceMetricConsumeViewParamsResponseSchema.detail(metric_consume_view)} 


# # list
class ListServiceMetricConsumeViewRequestSchema(PaginatedRequestQuerySchema):
    id = fields.Integer(required=False, context=u'query')
    metric_type_id = fields.Integer(required=False, context=u'query')
    metric_type_name = fields.String(required=False, context=u'query')
    metric_num = fields.Integer(required=False, context=u'query')
    
    instance_id = fields.String(required=False, context=u'query')
    instance_parent_id = fields.String(required=False, context=u'query')
    account_id = fields.String(required=False, context=u'query')
    extraction_date_start = fields.DateTime(required=False, context=u'query')
    extraction_date_end = fields.DateTime(required=False, context=u'query')
    job_id = fields.Integer(required=False, context=u'query')
    
    field = fields.String(validate=OneOf([u'id', u'metric_type_name', u'extraction_date', u'metric_num', \
                                                    u'instance_parent_id', u'instance_id'],
                                error=u'Field can be id, metric_type_name, extraction_date, metric_num, instance_parent_id, instance_id'),
                          description=u'enitities list order field. Ex. id, metric_type_name, ...',
                          default=u'id', example=u'id', missing=u'id', context=u'query')


class ListServiceMetricConsumeViewResponseSchema(PaginatedResponseSchema):
    metric_consume = fields.Nested(GetServiceMetricConsumeViewParamsResponseSchema,
                                  many=True, required=True, allow_none=True)


class ListServiceMetricConsumeView(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServiceMetricConsumeViewResponseSchema': ListServiceMetricConsumeViewResponseSchema,
        u'ListServiceMetricConsumeViewRequestSchema': ListServiceMetricConsumeViewRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServiceMetricConsumeViewRequestSchema)
    parameters_schema = ListServiceMetricConsumeViewRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServiceMetricConsumeViewResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        metric_consume_view, total = controller.get_paginated_metric_consume_views(**data)
        res = [GetServiceMetricConsumeViewParamsResponseSchema.detail(m) for m in metric_consume_view]
        res_dict = self.format_paginated_response(res, u'metric_consume', total, **data)
        return res_dict


class ServiceMetricConsumeViewAPI(ApiView):
    """ServiceMetricConsumeView api routes:
    """

    @staticmethod
    def register_api(module):
        base = u'nws'
        rules = [
            (u'%s/services/consume_views' % base, u'GET', ListServiceMetricConsumeView, {}),
            (u'%s/services/consume_views/<oid>' % base, u'GET', GetServiceMetricConsumeView, {})           
        ]

        ApiView.register_api(module, rules)
