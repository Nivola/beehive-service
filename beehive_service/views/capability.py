# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema, PaginatedResponseSchema, \
    ApiObjectResponseSchema, CrudApiObjectResponseSchema, GetApiObjectRequestSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ServiceController, ApiAccountCapability
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema
import json


DEFAULT_DEFAULT_SERVICE_TYPES = [
    'ComputeService',
    'DatabaseService',
    'StorageService',
    'AppEngineService',
    'ComputeImage',
    'ComputeVPC',
    'ComputeSecurityGroup',
    'ComputeSubnet'
]


# start added by ahmad 21-10-2020
class ParamsServiceParamsDescriptionSchema(Schema):
    cidr = fields.String(required=False, example='10.138.236.96/27')
    zone = fields.String(required=False, example='SiteVercelli01')
    vpc = fields.String(required=False, example='VpcRUPAR04')


class RequireServiceParamsDescriptionSchema(Schema):
    name = fields.String(required=False, example='ComputeService')
    type = fields.String(required=False, example='ComputeService')


class ServiceParamsDescriptionSchema(Schema):
    params = fields.Nested(ParamsServiceParamsDescriptionSchema, required=True, allow_none=True)
    type = fields.String(required=False, example='ComputeImage')
    name = fields.String(required=False, example='Windows2016')
    template = fields.String(required=False)
    require = fields.Nested(RequireServiceParamsDescriptionSchema, required=False)


class ParamsDescriptionSchema(Schema):
    services = fields.Nested(ServiceParamsDescriptionSchema, many=True,required=False)
# END added by ahmad 21-10-2020


class ListAccountCapabilitiesRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                           PaginatedRequestQuerySchema):
    status_id = fields.Integer(required=False, context='query')


class ListAccountCapabilitiesParamsResponseSchema(ApiObjectResponseSchema):
    status_id = fields.Integer(required=False, default=1)
    version = fields.String(required=False, default='1.0')
    plugin_name = fields.String(required=False, default='')
    params = fields.Nested(ParamsDescriptionSchema, allow_none=True, default='')


class ListAccountCapabilitiesResponseSchema(PaginatedResponseSchema):
    capabilities = fields.Nested(ListAccountCapabilitiesParamsResponseSchema, many=True, required=True, allow_none=True)


class ListAccountCapabilities(ServiceApiView):
    summary = 'List account capabilities'
    description = 'List account capabilities'
    tags = ['authority']
    definitions = {
        'ListAccountCapabilitiesResponseSchema': ListAccountCapabilitiesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountCapabilitiesRequestSchema)
    parameters_schema = ListAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListAccountCapabilitiesResponseSchema
        }
    })
    response_schema = ListAccountCapabilitiesResponseSchema

    def get(self, controller, data, *args, **kwargs):
        capabilities, total = controller.get_capabilities(**data)

        res = []
        for r in capabilities:
            info = r.info()
            res.append(info)
        resp = self.format_paginated_response(res, 'capabilities', total, **data)
        return resp


class GetAccountCapabilityParamsResponseSchema(ApiObjectResponseSchema):
    status_id = fields.Integer(required=False, default=1)
    version = fields.String(required=False, default='1.0')
    params = fields.String(required=False, allow_none=True, default='')


class GetAccountCapabilityResponseSchema(Schema):
    capabilities = fields.Nested(
        GetAccountCapabilityParamsResponseSchema,
        required=True,
        allow_none=True,
        description='The Capability description')


class GetAccountCapability(ServiceApiView):
    summary = 'Get account capability'
    description = 'Get account capability'
    tags = ['authority']
    definitions = {
        'GetAccountCapabilityResponseSchema': GetAccountCapabilityResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountCapabilityResponseSchema
        }
    })
    response_schema = GetAccountCapabilityResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        capability = controller.get_capability(oid)
        res = capability.detail()
        resp = {'capability': res}
        return resp


class BaseServiceDescriptonSchema(Schema):
    name = fields.String(required=True, example='prova', description='The name of the Service Instance')
    type = fields.String(required=True, example='ComputeService',
                         description='The Service Type for the Service Instance')


class ServiceDescriptionSchema(BaseServiceDescriptonSchema):
    template = fields.String(required=False,
                             description='The Service Definition describing the Service Instance template')
    params = fields.Dict(required=False, description='the parameter used for creating the Service instance')
    require = fields.Nested(BaseServiceDescriptonSchema, required=False,
                            description='List of Service definition added by the capability')


class CreateAccountCapabilityParamRequestSchema(Schema):
    name = fields.String(required=True, example='default')
    desc = fields.String(required=False, allow_none=True)
    version = fields.String(required=False, default='1.0')
    services = fields.Nested(ServiceDescriptionSchema, required=True, allow_none=False, many=True,
                             description='List of Service Instances added by the capability')
    definitions = fields.List(fields.String(required=False, allow_none=True, example=''), required=True,
                              allow_none=True, many=True,
                              description='List of Service definition added by the capability')


class CreateAccountCapabilityRequestSchema(Schema):
    capability = fields.Nested(CreateAccountCapabilityParamRequestSchema, context='body', many=False)


class CreateAccountCapabilityBodyRequestSchema(Schema):
    body = fields.Nested(CreateAccountCapabilityRequestSchema, context='body')


class CreateAccountCapability(ServiceApiView):
    summary = 'Create account capability'
    description = 'Create account capability'
    tags = ['authority']
    definitions = {
        'CreateAccountCapabilityRequestSchema': CreateAccountCapabilityRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateAccountCapabilityBodyRequestSchema)
    parameters_schema = CreateAccountCapabilityRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data:dict, *args, **kwargs):
        capability = data.get('capability')

        name = capability.get('name')
        desc = capability.get('desc')
        version = capability.get('version', '1.0')

        params = {
            'services': capability.get('services', []),
            'definitions': capability.get('definitions', []),
        }
        jsonparams = json.dumps(params)
        resp = controller.add_capability(name, desc=desc, version=version, params=jsonparams)

        return {'uuid': resp}, 201


class UpdateAccountCapabilityParamRequestSchema(Schema):
    name = fields.String(required=False)
    desc = fields.String(required=False)
    version = fields.String(required=False)
    plugin_name = fields.String(required=False)
    services = fields.Nested(ServiceDescriptionSchema, required=False, allow_none=True, many=True,
                             description='List of ServiceInstanced added by the capability')
    definitions = fields.List(fields.String(required=False, allow_none=True, example='compute.medium'),
                              required=False, allow_none=True, many=True,
                              description='List of Service definition added by the capability')


class UpdateAccountCapabilityRequestSchema(Schema):
    capability = fields.Nested(UpdateAccountCapabilityParamRequestSchema)


class UpdateAccountCapabilityBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateAccountCapabilityRequestSchema, context='body')


class UpdateAccountCapability(ServiceApiView):
    summary = 'Update account capability'
    description = 'Update account capability'
    tags = ['authority']
    definitions = {
        'UpdateAccountCapabilityRequestSchema': UpdateAccountCapabilityRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateAccountCapabilityBodyRequestSchema)
    parameters_schema = UpdateAccountCapabilityRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        capability = controller.get_capability(oid)

        in_data = data.get('capability')
        params = capability.get_params()

        setdata = {}
        if 'name' in in_data:
            setdata['name'] = in_data['name']
        if 'desc' in in_data:
            setdata['desc'] = in_data['desc']
        if 'version' in in_data:
            setdata['version'] = in_data['version']
        if 'plugin_name' in in_data:
            setdata['plugin_name'] = in_data['plugin_name']
        if 'services' in in_data:
            params['services'] = in_data['services']
        if 'definitions' in in_data:
            params['definitions'] = in_data['definitions']

        setdata['params'] = json.dumps(params)

        resp = capability.update(**setdata)

        return {'uuid': capability.uuid}, 200


class DeleteAccountCapability(ServiceApiView):
    summary = 'Delete account capability'
    description = 'Delete account capability'
    tags = ['authority']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        resp = controller.delete_capability(oid)
        return resp, 204


class AccountCapabilityAPI(ApiView):
    """AccountAPI
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/capabilities' % base, 'GET', ListAccountCapabilities, {}),
            ('%s/capabilities/<oid>' % base, 'GET', GetAccountCapability, {}),
            ('%s/capabilities' % base, 'POST', CreateAccountCapability, {}),
            ('%s/capabilities/<oid>' % base, 'PUT', UpdateAccountCapability, {}),
            ('%s/capabilities/<oid>' % base, 'DELETE', DeleteAccountCapability, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
