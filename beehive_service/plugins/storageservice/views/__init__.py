# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.storageservice.controller import ApiStorageService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, CrudApiObjectResponseSchema, ApiManagerError, ApiView, \
    CrudApiObjectTaskResponseSchema
from beehive_service.controller import ApiServiceType


class DescribeStorageServiceRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class DescribeStorageServiceResponseSchema(Schema):
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


class DescribeStorageService(ServiceApiView):
    summary = 'Get storage service info'
    description = 'Get storage service info'
    tags = ['storageservice']
    definitions = {
        'DescribeStorageServiceRequestSchema': DescribeStorageServiceRequestSchema,
        'DescribeStorageServiceResponseSchema': DescribeStorageServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeStorageServiceRequestSchema)
    parameters_schema = DescribeStorageServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeStorageServiceResponseSchema
        }
    })
    response_schema = DescribeStorageServiceResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiStorageService.plugintype)
        storage_set = [r.aws_info() for r in res]

        res = {
            'DescribeStorageResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'storageSet': storage_set,
                'storageTotal': 1
            }
        }
        return res


class CreateStorageServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=True, example='')
    resource_desc = fields.String(required=False, default='')


class CreateStorageServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateStorageServiceApiRequestSchema, context='body')


class CreateStorageService(ServiceApiView):
    summary = 'Create storage service info'
    description = 'Create storage service info'
    tags = ['storageservice']
    definitions = {
        'CreateStorageServiceApiRequestSchema': CreateStorageServiceApiRequestSchema,
        'CrudApiObjectTaskResponseSchema': CrudApiObjectTaskResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateStorageServiceApiBodyRequestSchema)
    parameters_schema = CreateStorageServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CrudApiObjectTaskResponseSchema
        }
    })
    response_schema = CrudApiObjectTaskResponseSchema

    def post(self, controller, data, *args, **kvargs):
        service_definition_id = data.pop('service_def_id')
        account_id = data.pop('owner_id')
        desc = data.pop('desc', 'Storage service account %s' % account_id)
        name = data.pop('name')

        plugin = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                    instance_config=data)

        uuid = plugin.instance.uuid
        taskid = getattr(plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class UpdateStorageServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=False, default='')


class UpdateStorageServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateStorageServiceApiRequestParamSchema, context='body')


class UpdateStorageServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateStorageServiceApiRequestSchema, context='body')


class UpdateStorageService(ServiceApiView):
    summary = 'Update storage service info'
    description = 'Update storage service info'
    tags = ['storageservice']
    definitions = {
        'UpdateStorageServiceApiRequestSchema': UpdateStorageServiceApiRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateStorageServiceApiBodyRequestSchema)
    parameters_schema = UpdateStorageServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, *args, **kvargs):
        data = data.get('serviceinst')

        def_id = data.get('service_def_id', None)
        account_id = data.get('owner_id')

        inst_services, tot = controller.get_paginated_service_instances(account_id=account_id,
                                                                        plugintype=ApiStorageService.plugintype,
                                                                        filter_expired=False)
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError('Account %s has no storage instance associated' % account_id)

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
#AHMAD NSP-484 -begin
class DescribeAccountAttributeSSItemResponseSchema(Schema):
    attributeValue = fields.Integer(required=False)
    nvlAttributeUsed = fields.Integer(required=False,data_key='nvl-attributeUsed')

class DescribeAccountAttributeSSValueSetResponseSchema(Schema):
    item = fields.Nested(DescribeAccountAttributeSSItemResponseSchema,required=False, many=False)

class DescribeAccountAttributeSetSSResponseSchema(Schema):
    attributeName = fields.String(required=False)
    nvlAttributeUnit = fields.String(required=False,data_key='nvl-attributeUnit')
    attributeValueSet = fields.Nested(DescribeAccountAttributeSSValueSetResponseSchema, many=True)

class DescribeAccountAttributeSSResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetSSResponseSchema, many=True, required=True)

class DescribeAccountAttributesSSResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeSSResponseSchema, many=False)
#AHMAD NSP-484 -end

class DescribeAccountAttributes(ServiceApiView):
    summary = 'Describes attributes of storage service'
    description = 'Describes attributes of storage service'
    tags = ['storageservice']
    definitions = {
        'DescribeAccountAttributesRequestSchema': DescribeAccountAttributesRequestSchema,
        'DescribeAccountAttributesSSResponseSchema': DescribeAccountAttributesSSResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAccountAttributesRequestSchema)
    parameters_schema = DescribeAccountAttributesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAccountAttributesSSResponseSchema
        }
    })
    response_schema = DescribeAccountAttributesSSResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiStorageService.plugintype)
        if tot > 0:
            attribute_set = res[0].aws_get_attributes()
        else:
            raise ApiManagerError('Account %s has no storage instance associated' % data.get('owner_id'), code=404)

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
    summary = 'Modify attributes of storage service'
    description = 'Modify attributes of storage service'
    tags = ['storageservice']
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
    response_schema = DescribeAccountAttributesResponseSchema

    def put(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiStorageService.plugintype)
        if tot > 0:
            res[0].set_attributes(data.get('quotas'))
            attribute_set = [{'uuid': res[0].instance.uuid}]
        else:
            raise ApiManagerError('Account %s has no storage instance associated' % data.get('owner_id'), code=404)

        res = {
            'ModifyAccountAttributesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                '': attribute_set
            }
        }
        return res


class DeleteStorageServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description='Instance id')
    taskid = fields.String(required=True, description='task id')


class DeleteStorageServiceRequestSchema(Schema):
    instanceId = fields.String(required=True, allow_none=True, context='query', description='Instance uuid or name')


class DeleteStorageService(ServiceApiView):
    summary = 'Terminate a storage service'
    description = 'Terminate a storage service'
    tags = ['storageservice']
    definitions = {
        'DeleteStorageServiceRequestSchema': DeleteStorageServiceRequestSchema,
        'DeleteStorageServiceResponseSchema': DeleteStorageServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteStorageServiceRequestSchema)
    parameters_schema = DeleteStorageServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DeleteStorageServiceResponseSchema
        }
    })
    response_schema = DeleteStorageServiceResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop('instanceId')

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiStorageService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class StorageServiceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, version=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/storageservices' % base, 'GET', DescribeStorageService, {}),
            ('%s/storageservices' % base, 'POST', CreateStorageService, {}),
            ('%s/storageservices' % base, 'PUT', UpdateStorageService, {}),
            ('%s/storageservices' % base, 'DELETE', DeleteStorageService, {}),

            ('%s/storageservices/describeaccountattributes' % base, 'GET', DescribeAccountAttributes, {}),
            ('%s/storageservices/modifyaccountattributes' % base, 'PUT', ModifyAccountAttributes, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
