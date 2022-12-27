# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.computeservice import ApiComputeService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, CrudApiObjectResponseSchema, \
    ApiManagerError, ApiView, CrudApiObjectTaskResponseSchema
from beehive_service.controller import ApiServiceType, ServiceController


class DescribeComputeServiceRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class StateReasonResponseSchema(Schema):
    code = fields.String(required=False, allow_none=True, example='', description='reason code for the state change')
    message = fields.String(required=False, allow_none=True, example='', description='message for the state change')


class ComputeSetResponseSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(required=False, allow_none=True, description='date creation')
    description = fields.String(required=True)
    state = fields.String(required=False, default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=True)
    template = fields.String(required=True)
    template_name = fields.String(required=True)
    stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False, allow_none=False, description='array of status reason')
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribeComputeServiceResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns')
    requestId = fields.String(required=False)
    computeSet = fields.Nested(ComputeSetResponseSchema, many=True, required=False)
    computeTotal = fields.Integer(required=False)


class DescribeComputeApiResponseSchema(Schema):
    DescribeComputeResponse = fields.Nested(DescribeComputeServiceResponseSchema, required=True, many=False, allow_none=False)


class DescribeComputeService(ServiceApiView):
    summary = 'Get compute service info'
    description = 'Get compute service info'
    tags = ['computeservice']
    definitions = {
        'DescribeComputeServiceRequestSchema': DescribeComputeServiceRequestSchema,
        'DescribeComputeApiResponseSchema': DescribeComputeApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeComputeServiceRequestSchema)
    parameters_schema = DescribeComputeServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeComputeApiResponseSchema
        }
    })
    response_schema = DescribeComputeApiResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiComputeService.plugintype)
        compute_set = [r.aws_info() for r in res]

        res = {
            'DescribeComputeResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'computeSet': compute_set,
                'computeTotal': 1
            }
        }
        return res


class CreateComputeServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=True, example='')
    resource_desc = fields.String(required=False, default='')


class CreateComputeServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateComputeServiceApiRequestSchema, context='body')


class CreateComputeService(ServiceApiView):
    summary = 'Create compute service info'
    description = 'Create compute service info'
    tags = ['computeservice']
    definitions = {
        'CreateComputeServiceApiRequestSchema': CreateComputeServiceApiRequestSchema,
        'CrudApiObjectTaskResponseSchema': CrudApiObjectTaskResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateComputeServiceApiBodyRequestSchema)
    parameters_schema = CreateComputeServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CrudApiObjectTaskResponseSchema
        }
    })
    response_schema = CrudApiObjectTaskResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kvargs):
        service_definition_id = data.pop('service_def_id')
        account_id = data.pop('owner_id')
        desc = data.pop('desc', 'Compute service account %s' % account_id)
        name = data.pop('name')

        plugin = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                    instance_config=data)

        uuid = plugin.instance.uuid
        taskid = getattr(plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class UpdateComputeServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=False, default='')


class UpdateComputeServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateComputeServiceApiRequestParamSchema, context='body')


class UpdateComputeServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateComputeServiceApiRequestSchema, context='body')


class UpdateComputeService(ServiceApiView):
    summary = 'Update compute service info'
    description = 'Update compute service info'
    tags = ['computeservice']
    definitions = {
        'UpdateComputeServiceApiRequestSchema': UpdateComputeServiceApiRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateComputeServiceApiBodyRequestSchema)
    parameters_schema = UpdateComputeServiceApiRequestSchema
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
                                                                        plugintype=ApiComputeService.plugintype,
                                                                        filter_expired=False)
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError('Account %s has no compute instance associated' % account_id)

        # get service def
        if def_id is not None:
            plugin_root = ApiServiceType(controller).instancePlugin(None, inst=inst_service)
            plugin_root.change_definition(inst_service, def_id)

        return {'uuid': inst_service.uuid}


class DescribeAccountAttributesRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class DescribeAccountAttributesResponseSchema(Schema):
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

#AHMAD NSP-344 -begin
class DescribeAccountAttributeCSItemResponseSchema(Schema):
    attributeValue = fields.Integer(required=False)
    nvlAttributeUsed = fields.Integer(required=False,data_key='nvl-attributeUsed')

class DescribeAccountAttributeCSValueSetResponseSchema(Schema):
    item = fields.Nested(DescribeAccountAttributeCSItemResponseSchema,required=False, many=False)

class DescribeAccountAttributeSetCSResponseSchema(Schema):
    attributeName = fields.String(required=False)
    nvlAttributeUnit = fields.String(required=False,data_key='nvl-attributeUnit')
    attributeValueSet = fields.Nested(DescribeAccountAttributeCSValueSetResponseSchema, many=True)

class DescribeAccountAttributeCSResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetCSResponseSchema, many=True, required=True)
    xmlns = fields.String(required=False, data_key='__xmlns')

class DescribeAccountAttributesCSResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeCSResponseSchema, many=False)
#AHMAD NSP-344 -end

class DescribeAccountAttributes(ServiceApiView):
    summary = 'Describes attributes of compute service'
    description = 'Describes attributes of compute service'
    tags = ['computeservice']
    definitions = {
        'DescribeAccountAttributesRequestSchema': DescribeAccountAttributesRequestSchema,
        'DescribeAccountAttributesCSResponseSchema': DescribeAccountAttributesCSResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAccountAttributesRequestSchema)
    parameters_schema = DescribeAccountAttributesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAccountAttributesCSResponseSchema
        }
    })
    response_schema = DescribeAccountAttributesCSResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiComputeService.plugintype)
        if tot > 0:
            attribute_set = res[0].aws_get_attributes()
        else:
            raise ApiManagerError('Account %s has no compute instance associated' % data.get('owner_id'), code=404)

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
    summary = 'Modify attributes of compute service'
    description = 'Modify attributes of compute service'
    tags = ['computeservice']
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
                                                       plugintype=ApiComputeService.plugintype)
        if tot > 0:
            res[0].set_attributes(data.get('quotas'))
            attribute_set = [{'uuid': res[0].instance.uuid}]
        else:
            raise ApiManagerError('Account %s has no compute instance associated' % data.get('owner_id'), code=404)

        res = {
            'ModifyAccountAttributesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                '': attribute_set
            }
        }
        return res


class DescribeAvailabilityZonesRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class AvailabilityZoneMessageResponseSchema (Schema):
    message = fields.String(required=False, allow_none=True, description='message about the Availability Zone')


class DescribeAvailabilityZonesItemResponseSchema (Schema):
    zoneName = fields.String(required=False, allow_none=True, description='name of the Availability Zone')
    zoneState = fields.String(required=False, allow_none=True, description='state of the Availability Zone')
    regionName = fields.String(required=False, allow_none=True, description='name of the region')
    messageSet = fields.Nested(AvailabilityZoneMessageResponseSchema, required=False, many=True, allow_none=False)


class DescribeAvailabilityZonesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    availabilityZoneInfo = fields.Nested(DescribeAvailabilityZonesItemResponseSchema, required=True, many=True,
                                         allow_none=False)
    xmlns = fields.String(required=False, data_key='__xmlns')


class DescribeAvailabilityZonesResponseSchema(Schema):
    DescribeAvailabilityZonesResponse = fields.Nested(DescribeAvailabilityZonesApi1ResponseSchema, required=True,
                                                      many=False, allow_none=False)


class DescribeAvailabilityZonesResponse(ServiceApiView):
    summary = 'Describes zone and region attribute for compute service'
    description = 'Describes zone and region attribute for compute service'
    tags = ['computeservice']
    definitions = {
        'DescribeAvailabilityZonesRequestSchema': DescribeAvailabilityZonesRequestSchema,
        'DescribeAvailabilityZonesResponseSchema': DescribeAvailabilityZonesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAvailabilityZonesRequestSchema)
    parameters_schema = DescribeAvailabilityZonesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeAvailabilityZonesResponseSchema
        }
    })
    response_schema = DescribeAvailabilityZonesResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiComputeService.plugintype)
        if tot > 0:
            avzs = res[0].aws_get_availability_zones()
        else:
            raise ApiManagerError('Account %s has no compute instance associated' % data.get('owner_id'),code=404)

        res = {
            'DescribeAvailabilityZonesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'availabilityZoneInfo': avzs
            }
        }
        return res


class DeleteComputeServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description='Instance id')
    taskid = fields.String(required=True, description='task id')


class DeleteComputeServiceRequestSchema(Schema):
    instanceId = fields.String(required=True, allow_none=True, context='query', description='Instance uuid or name')


class DeleteComputeService(ServiceApiView):
    summary = 'Terminate a compute service'
    description = 'Terminate a compute service'
    tags = ['computeservice']
    definitions = {
        'DeleteComputeServiceRequestSchema': DeleteComputeServiceRequestSchema,
        'DeleteComputeServiceResponseSchema': DeleteComputeServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteComputeServiceRequestSchema)
    parameters_schema = DeleteComputeServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': DeleteComputeServiceResponseSchema
        }
    })
    response_schema = DeleteComputeServiceResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop('instanceId')

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiComputeService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class ComputeServiceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/computeservices' % base, 'GET', DescribeComputeService, {}),
            ('%s/computeservices' % base, 'POST', CreateComputeService, {}),
            ('%s/computeservices' % base, 'PUT', UpdateComputeService, {}),
            ('%s/computeservices' % base, 'DELETE', DeleteComputeService, {}),

            ('%s/computeservices/describeaccountattributes' % base, 'GET', DescribeAccountAttributes, {}),
            ('%s/computeservices/modifyaccountattributes' % base, 'PUT', ModifyAccountAttributes, {}),
            ('%s/computeservices/describeavailabilityzones' % base, 'GET', DescribeAvailabilityZonesResponse, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
