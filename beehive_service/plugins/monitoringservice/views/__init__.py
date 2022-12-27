# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.monitoringservice.controller import ApiMonitoringService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, CrudApiObjectResponseSchema, ApiManagerError, ApiView, \
    CrudApiObjectTaskResponseSchema
from beehive_service.controller import ApiServiceType


class DescribeMonitoringServiceRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')


class MonitoringStateReasonResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, example='', description='state code', data_key='code')
    message = fields.String(required=False, allow_none=True, example='', description='state message', data_key='message')


class MonitoringSetResponseSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(required=True, example='2022-01-25T11:20:18Z', description='creation date')
    description = fields.String(required=True)
    state = fields.String(required=False, default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=True)
    template = fields.String(required=True)
    template_name = fields.String(required=True)
    stateReason = fields.Nested(MonitoringStateReasonResponseSchema, many=False, required=True, description='state description')
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribeMonitoringResponseInnerSchema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns')
    # next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True, allow_none=True)
    monitoringSet = fields.Nested(MonitoringSetResponseSchema, many=True, required=False, allow_none=True)
    monitoringTotal = fields.Integer(required=False, example='0', descriptiom='total monitoring', data_key='monitoringTotal')


class DescribeMonitoringServiceResponseSchema(Schema):
    DescribeMonitoringResponse = fields.Nested(DescribeMonitoringResponseInnerSchema, required=True, many=False)


class DescribeMonitoringService(ServiceApiView):
    summary = 'Get monitoring service info'
    description = 'Get monitoring service info'
    tags = ['monitoringservice']
    definitions = {
        'DescribeMonitoringServiceRequestSchema': DescribeMonitoringServiceRequestSchema,
        'DescribeMonitoringServiceResponseSchema': DescribeMonitoringServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeMonitoringServiceRequestSchema)
    parameters_schema = DescribeMonitoringServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeMonitoringServiceResponseSchema
        }
    })
    response_schema = DescribeMonitoringServiceResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
                                                       plugintype=ApiMonitoringService.plugintype)
        monitoring_set = [r.aws_info() for r in res]

        res = {
            'DescribeMonitoringResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'monitoringSet': monitoring_set,
                'monitoringTotal': 1
            }
        }
        return res


class CreateMonitoringServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=True, example='')
    resource_desc = fields.String(required=False, default='')


class CreateMonitoringServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateMonitoringServiceApiRequestSchema, context='body')


class CreateMonitoringService(ServiceApiView):
    summary = 'Create monitoring service info'
    description = 'Create monitoring service info'
    tags = ['monitoringservice']
    definitions = {
        'CreateMonitoringServiceApiRequestSchema': CreateMonitoringServiceApiRequestSchema,
        'CrudApiObjectTaskResponseSchema': CrudApiObjectTaskResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateMonitoringServiceApiBodyRequestSchema)
    parameters_schema = CreateMonitoringServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CrudApiObjectTaskResponseSchema
        }
    })

    def post(self, controller, data, *args, **kvargs):
        service_definition_id = data.pop('service_def_id')
        account_id = data.pop('owner_id')
        desc = data.pop('desc', 'Monitoring service account %s' % account_id)
        name = data.pop('name')

        self.logger.debug('+++++ CreateMonitoringService - post - service_definition_id: %s' % (service_definition_id))
        self.logger.debug('+++++ CreateMonitoringService - post - account_id: %s' % (account_id))
        self.logger.debug('+++++ CreateMonitoringService - post - name: %s' % (name))

        plugin = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                    instance_config=data)

        uuid = plugin.instance.uuid
        self.logger.debug('+++++ CreateMonitoringService - post - uuid: %s' % (uuid))

        taskid = getattr(plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class UpdateMonitoringServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, context='query', data_key='owner-id',
                             description='account ID of the instance owner')
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    service_def_id = fields.String(required=False, default='')


class UpdateMonitoringServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateMonitoringServiceApiRequestParamSchema, context='body')


class UpdateMonitoringServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateMonitoringServiceApiRequestSchema, context='body')


class UpdateMonitoringService(ServiceApiView):
    summary = 'Update monitoring service info'
    description = 'Update monitoring service info'
    tags = ['monitoringservice']
    definitions = {
        'UpdateMonitoringServiceApiRequestSchema': UpdateMonitoringServiceApiRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateMonitoringServiceApiBodyRequestSchema)
    parameters_schema = UpdateMonitoringServiceApiRequestSchema
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
                                                                        plugintype=ApiMonitoringService.plugintype,
                                                                        filter_expired=False)
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError('Account %s has no monitoring instance associated' % account_id)

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
    xmlns = fields.String(required=False, data_key='__xmlns')
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetResponseSchema, many=True, required=True)


class DescribeAccountAttributesResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeResponseSchema, required=True, many=False,
                                                      allow_none=False)


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
    xmlns = fields.String(required=False, data_key='__xmlns')
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetSSResponseSchema, many=True, required=True)


class DescribeAccountAttributesSSResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeSSResponseSchema, many=False)


class DescribeAccountAttributes(ServiceApiView):
    summary = 'Describes attributes of monitoring service'
    description = 'Describes attributes of monitoring service'
    tags = ['monitoringservice']
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
                                                       plugintype=ApiMonitoringService.plugintype)
        if tot > 0:
            apiMonitoringService: ApiMonitoringService = res[0]
            attribute_set = apiMonitoringService.aws_get_attributes()
        else:
            raise ApiManagerError('Account %s has no monitoring instance associated' % data.get('owner_id'))

        res = {
            'DescribeAccountAttributesResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'accountAttributeSet': attribute_set
            }
        }
        return res


# class ModifyAccountAttributeBodyRequestSchema(Schema):
#     owner_id = fields.String(required=True)
#     quotas = fields.Dict(required=True, example='')


# class ModifyAccountAttributesBodyRequestSchema(Schema):
#     body = fields.Nested(ModifyAccountAttributeBodyRequestSchema, context='body')


# class ModifyAccountAttributeSetResponseSchema(Schema):
#     uuid = fields.String(required=True, example='')


# class ModifyAccountAttributeResponseSchema(Schema):
#     requestId = fields.String(required=True, allow_none=True)
#     accountAttributeSet = fields.Nested(ModifyAccountAttributeSetResponseSchema, many=True, required=True)


# class ModifyAccountAttributesResponseSchema(Schema):
#     ModifyAccountAttributesResponse = fields.Nested(ModifyAccountAttributeResponseSchema, required=True, many=False,
#                                                     allow_none=False)


# class ModifyAccountAttributes(ServiceApiView):
#     summary = 'Modify attributes of monitoring service'
#     description = 'Modify attributes of monitoring service'
#     tags = ['monitoringservice']
#     definitions = {
#         'ModifyAccountAttributeBodyRequestSchema': ModifyAccountAttributeBodyRequestSchema,
#         'ModifyAccountAttributesResponseSchema': ModifyAccountAttributesResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(ModifyAccountAttributesBodyRequestSchema)
#     parameters_schema = ModifyAccountAttributeBodyRequestSchema
#     responses = SwaggerApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': DescribeAccountAttributesResponseSchema
#         }
#     })

#     def put(self, controller, data, *args, **kvargs):
#         # get instances list
#         res, tot = controller.get_service_type_plugins(account_id_list=[data.get('owner_id')],
#                                                        plugintype=ApiMonitoringService.plugintype)
#         if tot > 0:
#             res[0].set_attributes(data.get('quotas'))
#             attribute_set = [{'uuid': res[0].instance.uuid}]
#         else:
#             raise ApiManagerError('Account %s has no monitoring instance associated' % data.get('owner_id'))

#         res = {
#             'ModifyAccountAttributesResponse': {
#                 '__xmlns': self.xmlns,
#                 'requestId': operation.id,
#                 '': attribute_set
#             }
#         }
#         return res


class DeleteMonitoringServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description='Instance id')
    taskid = fields.String(required=True, description='task id')


class DeleteMonitoringServiceRequestSchema(Schema):
    instanceId = fields.String(required=True, allow_none=True, context='query', description='Instance uuid or name')


class DeleteMonitoringService(ServiceApiView):
    summary = 'Terminate a monitoring service'
    description = 'Terminate a monitoring service'
    tags = ['monitoringservice']
    definitions = {
        'DeleteMonitoringServiceRequestSchema': DeleteMonitoringServiceRequestSchema,
        'DeleteMonitoringServiceResponseSchema': DeleteMonitoringServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteMonitoringServiceRequestSchema)
    parameters_schema = DeleteMonitoringServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DeleteMonitoringServiceResponseSchema
        }
    })

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop('instanceId')

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiMonitoringService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, 'active_task', None)
        return {'uuid': uuid, 'taskid': taskid}, 202


class MonitoringServiceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/monitoringservices' % base, 'GET', DescribeMonitoringService, {}),
            ('%s/monitoringservices' % base, 'POST', CreateMonitoringService, {}),
            ('%s/monitoringservices' % base, 'PUT', UpdateMonitoringService, {}),
            ('%s/monitoringservices' % base, 'DELETE', DeleteMonitoringService, {}),

            ('%s/monitoringservices/describeaccountattributes' % base, 'GET', DescribeAccountAttributes, {}),
            #('%s/monitoringservices/modifyaccountattributes' % base, 'PUT', ModifyAccountAttributes, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
