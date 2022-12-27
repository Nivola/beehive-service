# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from flasgger import fields, Schema
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema,\
    ApiObjectRequestFiltersSchema
from beehive.common.apimanager import SwaggerApiView,\
    ApiView, PaginatedRequestQuerySchema, ApiObjectPermsResponseSchema,\
    ApiObjectPermsRequestSchema, PaginatedResponseSchema
from beecell.swagger import SwaggerHelper
from beecell.simple import format_date

## jobs
class ListServiceJobsRequestSchema(ApiServiceObjectRequestSchema, 
                                      ApiObjectRequestFiltersSchema, 
                                      PaginatedRequestQuerySchema):
    account_id = fields.String(required=False, context=u'query')
    task_id = fields.String(required=False, context=u'query')


class GetServiceJobParamsResponseSchema(Schema):
    job = fields.String(required=True, example=u'4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, example=u'test_job')
    params = fields.Dict(required=True, example={})
    task_id = fields.Dict(required=True, example=u'')
    timestamp = fields.DateTime(required=True, example=u'1990-12-31T23:59:59Z')


class GetServiceJobResponseSchema(PaginatedResponseSchema):
    servicejobs = fields.Nested(GetServiceJobParamsResponseSchema, required=True, many=True, allow_none=True)


class GetServiceJobs(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServiceJobsRequestSchema': ListServiceJobsRequestSchema,
        u'GetServiceJobResponseSchema': GetServiceJobResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceJobsRequestSchema)
    parameters_schema = ListServiceJobsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServiceJobResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        
        jobs, total = controller.get_jobs(**data)
        res = [j.detail() for j in jobs]
        
        return self.format_paginated_response(res, u'servicejobs', total, **data)

## get perms
class GetServiceJobPerms(ServiceApiView):
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
        servicejobs = controller.get_service_job(oid)
        res, total = servicejobs.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)


class ServiceJobAPI(ApiView):
    """ServiceJob api routes:
    """
    @staticmethod
    def register_api(module, rules=None, version=None):
        base = u'nws'
        rules = [
            (u'%s/services/jobs'% base, u'GET', GetServiceJobs, {}), 
            (u'%s/service/jobs/<oid>/perms' % base, u'GET', GetServiceJobPerms, {}), 
        ]

        ApiView.register_api(module, rules)
        
        