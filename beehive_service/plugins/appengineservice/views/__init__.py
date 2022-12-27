# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.appengineservice.controller import ApiAppEngineService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, CrudApiObjectResponseSchema, \
    ApiManagerError, ApiView, CrudApiObjectTaskResponseSchema
from beehive_service.controller import ApiServiceType, ServiceController


class DescribeAppengineServiceRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class DescribeAppengineServiceResponseSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    account_id = fields.String(required=True)
    account_name = fields.String(required=True)
    template_id = fields.String(required=True)
    template_name = fields.String(required=True)
    state = fields.String(required=False, default=SrvStatusType.DRAFT)
    resource_uuid = fields.String(required=False, allow_none=True)
    stateReason = fields.String(required=False, default='')
    limits = fields.Dict(required=False, default={})


class DescribeAppengineService(ServiceApiView):
    summary = 'Get appengine service info'
    description = 'Get appengine service info'
    tags = ['appengineservice']
    definitions = {
        'DescribeAppengineServiceRequestSchema': DescribeAppengineServiceRequestSchema,
        'DescribeAppengineServiceResponseSchema': DescribeAppengineServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAppengineServiceRequestSchema)
    parameters_schema = DescribeAppengineServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAppengineServiceResponseSchema
        }
    })

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiAppEngineService.plugintype)
        appengine_set = [r.aws_info() for r in res]

        res = {
            'DescribeAppengineResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'appengineSet': appengine_set,
                'appengineTotal': 1
            }
        }
        return res


class CreateAppengineServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=True, example='')
    resource_desc = fields.String(required=False, default='')


class CreateAppengineServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateAppengineServiceApiRequestSchema, context='body')


class CreateAppengineService(ServiceApiView):
    summary = 'Create appengine service info'
    description = 'Create appengine service info'
    tags = ['appengineservice']
    definitions = {
        'CreateAppengineServiceApiRequestSchema': CreateAppengineServiceApiRequestSchema,
        'CrudApiObjectTaskResponseSchema': CrudApiObjectTaskResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateAppengineServiceApiBodyRequestSchema)
    parameters_schema = CreateAppengineServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CrudApiObjectTaskResponseSchema
        }
    })

    def post(self, controller: ServiceController, data: dict, *args, **kvargs):
        service_definition_id = data.pop('service_def_id')
        account_id = data.pop('owner_id')
        desc = data.pop('desc', 'Appengine service account %s' % account_id)
        name = data.pop('name')

        plugin = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                    instance_config=data)

        uuid = plugin.instance.uuid
        taskid = getattr(plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class UpdateAppengineServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=False, default='')


class UpdateAppengineServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateAppengineServiceApiRequestParamSchema, context='body')


class UpdateAppengineServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateAppengineServiceApiRequestSchema, context='body')


class UpdateAppengineService(ServiceApiView):
    summary = 'Update appengine service info'
    description = 'Update appengine service info'
    tags = ['appengineservice']
    definitions = {
        'UpdateAppengineServiceApiRequestSchema': UpdateAppengineServiceApiRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateAppengineServiceApiBodyRequestSchema)
    parameters_schema = UpdateAppengineServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, *args, **kvargs):
        data = data.get('serviceinst')

        def_id = data.get('service_def_id', None)
        account_id = data.get('owner_id')

        inst_services, tot = controller.get_paginated_service_instances(account_id=account_id,
                                                                        plugintype=ApiAppEngineService.plugintype,
                                                                        filter_expired=False)
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError('Account %s has no appengine instance associated' % account_id)

        # get service def
        if def_id is not None:
            plugin_root = ApiServiceType(controller).instancePlugin(None, inst=inst_service)
            plugin_root.change_definition(inst_service, def_id)

        return {'uuid': inst_service.uuid}


class DescribeAccountAttributesRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class DescribeAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True, example='')


class DescribeAccountAttributeResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetResponseSchema, many=True, required=True)


class DescribeAccountAttributesResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeResponseSchema, required=True, many=False,
                                                      allow_none=False)


class DescribeAccountAttributes(ServiceApiView):
    summary = 'Describes attributes of appengine service'
    description = 'Describes attributes of appengine service'
    tags = ['appengineservice']
    definitions = {
        'DescribeAccountAttributesRequestSchema': DescribeAccountAttributesRequestSchema,
        'DescribeAccountAttributesResponseSchema': DescribeAccountAttributesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAccountAttributesRequestSchema)
    parameters_schema = DescribeAccountAttributesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAccountAttributesResponseSchema
        }
    })

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiAppEngineService.plugintype)
        if tot > 0:
            attribute_set = res[0].aws_get_attributes()
        else:
            raise ApiManagerError('Account %s has no appengine instance associated' % data.get('owner_id'))

        res = {
            'DescribeAccountAttributesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'accountAttributeSet': attribute_set
            }
        }
        return res


class ModifyAccountAttributeBodyRequestSchema(Schema):
    owner_id = fields.String(required=True)
    quotas = fields.Dict(required=True, example='')


class ModifyAccountAttributesBodyRequestSchema(Schema):
    body = fields.Nested(ModifyAccountAttributeBodyRequestSchema, context='body')


class ModifyAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True, example='')


class ModifyAccountAttributeResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(ModifyAccountAttributeSetResponseSchema, many=True, required=True)


class ModifyAccountAttributesResponseSchema(Schema):
    ModifyAccountAttributesResponse = fields.Nested(ModifyAccountAttributeResponseSchema, required=True, many=False,
                                                    allow_none=False)


class ModifyAccountAttributes(ServiceApiView):
    summary = 'Modify attributes of appengine service'
    description = 'Modify attributes of appengine service'
    tags = ['appengineservice']
    definitions = {
        'ModifyAccountAttributeBodyRequestSchema': ModifyAccountAttributeBodyRequestSchema,
        'ModifyAccountAttributesResponseSchema': ModifyAccountAttributesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ModifyAccountAttributesBodyRequestSchema)
    parameters_schema = ModifyAccountAttributeBodyRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAccountAttributesResponseSchema
        }
    })

    def put(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiAppEngineService.plugintype)
        if tot > 0:
            res[0].set_attributes(data.get('quotas'))
            attribute_set = [{'uuid': res[0].instance.uuid}]
        else:
            raise ApiManagerError('Account %s has no appengine instance associated' % data.get('owner_id'))

        res = {
            'ModifyAccountAttributesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                '': attribute_set
            }
        }
        return res


class DeleteAppengineServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description='Instance name')


class DeleteAppengineServiceRequestSchema(Schema):
    instanceId = fields.String(required=True, allow_none=True, context='query', description='Instance uuid or name')


class DeleteAppengineService(ServiceApiView):
    summary = 'Terminate a appengine service'
    description = 'Terminate a appengine service'
    tags = ['appengineservice']
    definitions = {
        'DeleteAppengineServiceRequestSchema': DeleteAppengineServiceRequestSchema,
        'DeleteAppengineServiceResponseSchema': DeleteAppengineServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteAppengineServiceRequestSchema)
    parameters_schema = DeleteAppengineServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DeleteAppengineServiceResponseSchema
        }
    })

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop('instanceId')

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiAppEngineService)
        inst_service_uuid = type_plugin.instance.uuid
        type_plugin.delete()

        return {'uuid': inst_service_uuid}


class AppengineServiceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, version=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/appengineservices' % base, 'GET', DescribeAppengineService, {}),
            ('%s/appengineservices' % base, 'POST', CreateAppengineService, {}),
            ('%s/appengineservices' % base, 'PUT', UpdateAppengineService, {}),
            ('%s/appengineservices' % base, 'DELETE', DeleteAppengineService, {}),

            ('%s/appengineservices/describeaccountattributes' % base, 'GET', DescribeAccountAttributes, {}),
            ('%s/appengineservices/modifyaccountattributes' % base, 'PUT', ModifyAccountAttributes, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
