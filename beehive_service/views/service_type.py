# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from tkinter import FALSE
from beehive.common.data import transaction
from beehive.common.apimanager import PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema,\
    SwaggerApiView, ApiView
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectResponseSchema,\
    ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,\
    ApiServiceObjectCreateRequestSchema
from beehive_service.model import SrvStatusType


class GetServiceTypeParamsResponseSchema(ApiServiceObjectResponseSchema):
    status = fields.String(required=False, allow_none=True)
    objclass = fields.String(required=True, allow_none=False)
    flag_container = fields.Boolean(required=True, allow_none=False)
    plugintype = fields.String(required=True, allow_none=False)
    template_cfg = fields.String(required=True, allow_none=False)


class GetServiceTypeResponseSchema(Schema):
    servicetype = fields.Nested(GetServiceTypeParamsResponseSchema, required=True, allow_none=True)


class GetServiceType(ServiceApiView):
    summary = 'Get service type'
    description = 'Get service type'
    tags = ['service']
    definitions = {
        'GetServiceTypeResponseSchema': GetServiceTypeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetServiceTypeResponseSchema
        }
    })
    def get(self, controller, data, oid, *args, **kwargs):
        servicetype = controller.get_service_type(oid)
        return {'servicetype': servicetype.detail()}


class ListServiceTypeRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                   PaginatedRequestQuerySchema):
    status = fields.String(Required=False, context='query')
    version = fields.String(Required=False, context='query')
    flag_container = fields.Boolean(Required=False, context='query')
    objclass = fields.String(Required=False, context='query')
    plugintype = fields.String(required=False, context='query')


class ListServiceTypeResponseSchema(PaginatedResponseSchema):
    servicetypes = fields.Nested(GetServiceTypeParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceType(ServiceApiView):
    summary = 'Get service types'
    description = 'Get service types'
    tags = ['service']
    definitions = {
        'ListServiceTypeResponseSchema': ListServiceTypeResponseSchema,
        'ListServiceTypeRequestSchema': ListServiceTypeRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServiceTypeRequestSchema)
    parameters_schema = ListServiceTypeRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServiceTypeResponseSchema
        }
    })
    response_schema = ListServiceTypeResponseSchema

    def get(self, controller, data,   *args, **kwargs):
        service_type, total = controller.get_service_types(**data)
        res = [r.info() for r in service_type]
        res_dict = self.format_paginated_response(res, 'servicetypes', total, **data)
        return res_dict


class ListServicePluginTypeParamsResponseSchema(Schema):
    id = fields.String(Required=True)
    name = fields.String(Required=True)
    objclass = fields.String(Required=True)


class ListServicePluginTypeResponseSchema(Schema):
    count = fields.Integer(Required=True)
    plugintypes = fields.Nested(ListServicePluginTypeParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServicePluginType(ServiceApiView):
    summary = 'Get service plugin type'
    description = 'Get service plugin type'
    tags = ['service']
    definitions = {
        'ListServicePluginTypeResponseSchema': ListServicePluginTypeResponseSchema
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServicePluginTypeResponseSchema
        }
    })
    response_schema = ListServicePluginTypeResponseSchema

    def get(self, controller, data,   *args, **kwargs):
        plugintypes = controller.get_service_plugin_type()
        return {'plugintypes': plugintypes, 'count': len(plugintypes)}


class CreateServiceTypeParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    status = fields.String(required=False, default=SrvStatusType.DRAFT)
    objclass = fields.String(required=True, allow_none=False)
    flag_container = fields.Boolean(required=True, allow_none=False)
    template_cfg = fields.String(required=True, allow_none=False)


class CreateServiceTypeRequestSchema(Schema):
    servicetype = fields.Nested(CreateServiceTypeParamRequestSchema, context='body')


class CreateServiceTypeBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceTypeRequestSchema, context='body')


class CreateServiceType(ServiceApiView):
    summary = 'Create service type'
    description = 'Create service type'
    tags = ['service']
    definitions = {
        'CreateServiceTypeRequestSchema': CreateServiceTypeRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceTypeBodyRequestSchema)
    parameters_schema = CreateServiceTypeRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        data = data.get('servicetype')
        resp = controller.add_service_type(**data)
        return {'uuid': resp}, 201


class UpdateServiceTypeParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True)
    objclass = fields.String(required=False, allow_none=True)
    flag_container = fields.Boolean(required=False, allow_none=True)
    template_cfg = fields.String(required=False, allow_none=True)


class UpdateServiceTypeRequestSchema(Schema):
    servicetype = fields.Nested(UpdateServiceTypeParamRequestSchema)


class UpdateServiceTypeBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceTypeRequestSchema, context='body')


class UpdateServiceType(ServiceApiView):
    summary = 'Update service type'
    description = 'Update service type'
    tags = ['service']
    definitions = {
        'UpdateServiceTypeRequestSchema': UpdateServiceTypeRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceTypeBodyRequestSchema)
    parameters_schema = UpdateServiceTypeRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    def put(self, controller, data, oid, *args, **kwargs):
        srv_type = controller.get_service_type(oid)
        data = data.get('servicetype')

        resp = srv_type.update(**data)
        return {'uuid': resp}, 200


class DeleteServiceType(ServiceApiView):
    summary = 'Delete service type'
    description = 'Delete service type'
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
        srv_type = controller.get_service_type(oid)
        resp = srv_type.delete(soft=True)
        return resp, 204


class GetServiceTypePerms(ServiceApiView):
    summary = 'Get service type permissions'
    description = 'Get service type permissions'
    tags = ['service']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })
    def get(self, controller, data, oid, *args, **kwargs):
        servicetype = controller.get_service_type(oid)
        res, total = servicetype.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


class ServiceTypeAPI(ApiView):
    """ServiceInstance api routes:
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = 'nws'
        rules = [
            ('%s/servicetypes' % base, 'GET', ListServiceType, {}),
            ('%s/servicetypes/plugintypes' % base, 'GET', ListServicePluginType, {}),
            ('%s/servicetypes' % base, 'POST', CreateServiceType, {}),
            ('%s/servicetypes/<oid>' % base, 'GET', GetServiceType, {}),
            ('%s/servicetypes/<oid>' % base, 'PUT', UpdateServiceType, {}),
            ('%s/servicetypes/<oid>' % base, 'DELETE', DeleteServiceType, {}),
            ('%s/servicetypes/<oid>/perms' % base, 'GET', GetServiceTypePerms, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
