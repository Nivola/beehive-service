# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, GetApiObjectRequestSchema,\
    CrudApiObjectResponseSchema, ApiObjectResponseSchema,\
    ApiObjectPermsRequestSchema, ApiObjectPermsResponseSchema,\
    PaginatedRequestQuerySchema, PaginatedResponseSchema, SwaggerApiView
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema,\
    ApiObjectRequestFiltersSchema, ApiServiceObjectCreateRequestSchema
from beecell.swagger import SwaggerHelper
from flasgger import fields, Schema
from beehive.common.data import trace, transaction
from beehive_service.model import SrvStatusType, ServiceConfig
from beehive_service.controller import ApiServiceConfig

#
# servicecfg
#
## list
class ListServiceConfigsRequestSchema(ApiServiceObjectRequestSchema,
                                      ApiObjectRequestFiltersSchema,
                                      PaginatedRequestQuerySchema):
    service_definition_id=fields.String (context='query')
    params_type=fields.String(Required=False, context='query')


class ServiceConfigParamsResponseSchema(ApiObjectResponseSchema):
    service_definition_id=fields.String(required=True)
    params=fields.Dict(Required=True)
    params_type=fields.String(Required=True)


class ListServiceConfigsResponseSchema(PaginatedResponseSchema):
    servicecfgs = fields.Nested(ServiceConfigParamsResponseSchema,
                                  many=True, required=True, allow_none=True)

class ListServiceConfigs(ServiceApiView):
    tags = ['service']
    definitions = {
        'ListServiceConfigsResponseSchema': ListServiceConfigsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceConfigsRequestSchema)
    parameters_schema = ListServiceConfigsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServiceConfigsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        List servicecfgs
        Call this api to list all the existing servicecfgs
        """

        servicecfgs, total = controller.get_service_cfgs(**data)
        res = [r.info() for r in servicecfgs]
        return self.format_paginated_response(res, 'servicecfgs', total, **data)


## get
class GetServiceConfigResponseSchema(Schema):
    servicecfg = fields.Nested(ServiceConfigParamsResponseSchema,
                             required=True, allow_none=True)

class GetServiceConfig(ServiceApiView):
    tags = ['service']
    definitions = {
        'GetServiceConfigResponseSchema': GetServiceConfigResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetServiceConfigResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        servicecfg = controller.get_service_cfg(oid)
        resp = {'servicecfg':servicecfg.detail()}
        return resp

## create
class CreateServiceConfigParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    service_definition_id = fields.String(required=True, allow_none=False)
    params=fields.Dict(required=True, example={})
    params_type=fields.String(required=True)

class CreateServiceConfigRequestSchema(Schema):
    servicecfg = fields.Nested(CreateServiceConfigParamRequestSchema,
                                 context='body')

class CreateServiceConfigBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceConfigRequestSchema, context='body')

class CreateServiceConfig(ServiceApiView):
    tags = ['service']
    definitions = {
        'CreateServiceConfigRequestSchema': CreateServiceConfigRequestSchema,
        'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceConfigBodyRequestSchema)
    parameters_schema = CreateServiceConfigRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })



    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_cfg(**data.get('servicecfg'))
        return ({'uuid':resp}, 201)


## update
class UpdateServiceConfigParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    service_definition_id = fields.String(required=False)
    params=fields.Dict(required=False)
    params_type=fields.Integer(required=False)

class UpdateServiceConfigRequestSchema(Schema):
    servicecfg = fields.Nested(UpdateServiceConfigParamRequestSchema)

class UpdateServiceConfigBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceConfigRequestSchema, context='body')

class UpdateServiceConfig(ServiceApiView):
    tags = ['service']
    definitions = {
        'UpdateServiceConfigRequestSchema':UpdateServiceConfigRequestSchema,
        'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceConfigBodyRequestSchema)
    parameters_schema = UpdateServiceConfigRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        srv_cfg = controller.get_service_cfg(oid)
        data = data.get('servicecfg')

        resp = srv_cfg.update(**data)
        return ({'uuid':resp}, 200)

class DeleteServiceConfig(ServiceApiView):
    tags = ['service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_cfg = controller.get_service_cfg(oid)

        resp = srv_cfg.delete(soft=True)
        return (resp, 204)


## get perms
class GetServiceConfigPerms(ServiceApiView):
    tags = ['service']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        servicecfg = controller.get_service_cfg(oid)
        res, total = servicecfg.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


class ServiceCfgAPI(ApiView):
    """ServiceCfgAPI
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/servicecfgs' % base, 'GET', ListServiceConfigs, {}),
            ('%s/servicecfgs/<oid>' % base, 'GET', GetServiceConfig, {}),
            ('%s/servicecfgs/<oid>/perms' % base, 'GET', GetServiceConfigPerms, {}),
            ('%s/servicecfgs' % base, 'POST', CreateServiceConfig, {}),
            ('%s/servicecfgs/<oid>' % base, 'PUT', UpdateServiceConfig, {}),
            ('%s/servicecfgs/<oid>' % base, 'DELETE', DeleteServiceConfig, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
