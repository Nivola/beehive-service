# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from typing import Dict
from flasgger import fields, Schema
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView
from beehive_service.plugins.computeservice.controller import ApiComputeCustomization, ApiComputeService
from marshmallow.validate import OneOf
from beehive_service.controller import ServiceController
from beehive_service.model.base import SrvStatusType
from beehive.common.data import operation


class DescribeCustomizationsApiRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, default=10, context='query', description='number of results')
    NextToken = fields.String(required=False, default=0, context='query', description='result list page number')
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=False, context='query',
                             collection_format='multi', data_key='owner-id.N',
                             description='account ID of the customization owner')
    customization_name_N = fields.List(fields.String(), required=False,  example='',
                                       description='name of the customization', context='query',
                                       collection_format='multi', data_key='customization-name.N')
    customization_id_N = fields.List(fields.String(), required=False, context='query', data_key='customization-id.N',
                                     example='348970ea-0c4a-46e3-99d4-2b0cbb467655',
                                     description='list of customization id')
    customization_type_N = fields.List(fields.String(), required=False, context='query',
                                       data_key='customization-type.N', example='348970ea-0c4a-46e3-99d4-2b0cbb467655',
                                       description='list of customization type id')
    instance_id = fields.String(required=False, context='query', example='348970ea-0c4a-46e3-99d4-2b0cbb467655',
                                description='compute instance id')
    launch_time_N = fields.List(fields.String(example=''), required=False, context='query', collection_format='multi',
                                data_key='launch-time.N', description='time when the customization was created')
    tag_key_N = fields.List(fields.String(example=''), required=False, context='query', collection_format='multi',
                            data_key='tag-key.N', description='value of a tag assigned to the resource')
    state_name_N = fields.List(fields.String(example='', validate=OneOf(['pending', 'running', 'shutting-down',
                                                                         'terminated', 'stopping', 'stopped'])),
                               required=False, context='query', collection_format='multi', data_key='state-name.N',
                               description='state name of the customization')


class DescribeCustomizationSetArgResponseSchema(Schema):
    name = fields.String(required=True, example='test', description='parameter name')
    value = fields.String(required=True, example='test', description='parameter value')


class CustomizationStateResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, example='0', description='code of customization state')
    name = fields.String(required=False, example='pending | running | ....', description='name of customization state',
                         validate=OneOf([getattr(ApiComputeCustomization.state_enum, x)
                                         for x in dir(ApiComputeCustomization.state_enum) if not x.startswith("__")]))
    # ['pending', 'running', 'shutting-down', 'terminated', 'stopping', 'stopped', 'error', 'unknown']


class DescribeCustomizationSetResponseSchema(Schema):
    customizationId = fields.String(required=False, allow_none=True, example='5d1277c7-a69f-4dd3-9248-ccb080ee8c9f',
                                    description='customization id')
    customizationName = fields.String(required=False, allow_none=True, example='test', description='customization name')
    customizationType = fields.String(required=False, allow_none=True, example='5d1277c7-a69f-4dd3-9248-ccb080ee8c9f',
                                      description='customization definition for the customization')
    customizationState = fields.Nested(CustomizationStateResponseSchema, many=False, required=False)
    reason = fields.String(required=False, allow_none=True, example='',
                           description='reason for the current state of the customization')
    ownerAlias = fields.String(required=False, allow_none=True, example='',
                               description='name of the account that owns the customization')
    ownerId = fields.String(required=False, allow_none=True, example='',
                            description='ID of the account that owns the customization')
    launchTime = fields.DateTime(required=False, example='', description='the timestamp the customization was launched')
    resourceId = fields.String(required=False, allow_none=True, example='',
                               description='ID of the customization resource')
    #instances = fields.List(fields.String, required=True, exmaple='["6ee1916d-28b9-4d54-9676-63bb20784669"]',
    #                        description='list of compute instance id')
    args = fields.Nested(DescribeCustomizationSetArgResponseSchema, required=True, many=True, allow_none=False,
                         description='customization type args')
    instances = fields.List(fields.String(required=False, allow_none=True, many=True))


class DescribeCustomizationsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='123', description='api request id')
    customizationsSet = fields.Nested(DescribeCustomizationSetResponseSchema, required=True, many=True, allow_none=True,
                                     description='list of customization info')
    customizationTotal = fields.Integer(required=True, description='total number of customizations')
    xmlns = fields.String(required=False, data_key='__xmlns')


class DescribeCustomizationsApiResponseSchema(Schema):
    DescribeCustomizationsResponse = fields.Nested(DescribeCustomizationsApi1ResponseSchema, required=True, many=False,
                                                   allow_none=False)


class DescribeCustomizations(ServiceApiView):
    summary = 'Describe compute customization'
    description = 'Describe compute customization'
    tags = ['computeservice']
    definitions = {
        'DescribeCustomizationsApiRequestSchema': DescribeCustomizationsApiRequestSchema,
        'DescribeCustomizationsApiResponseSchema': DescribeCustomizationsApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeCustomizationsApiRequestSchema)
    parameters_schema = DescribeCustomizationsApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeCustomizationsApiResponseSchema
        }
    })
    response_schema = DescribeCustomizationsApiResponseSchema

    def get(self, controller: ServiceController, data: Dict, *args, **kwargs):
        data_search = {}
        data_search['size'] = data.get('MaxResults', 10)
        data_search['page'] = int(data.get('NextToken', 0))

        # check Account
        account_id_list = data.get('owner_id_N', [])
        account_id_list.extend(data.get('requester_id_N', []))

        # get customization identifier
        customization_id_list = data.get('customization_id_N', [])

        # get customization name
        customization_name_list = data.get('customization_name_N', [])

        # get customization service definition
        customization_def_list = data.get('customization_type_N', [])

        # get customization launch time
        customization_launch_time_list = data.get('launch_time_N', [])
        customization_launch_time = None
        if len(customization_launch_time_list) == 1:
            customization_launch_time = customization_launch_time_list[0]
        elif len(customization_launch_time_list) > 1:
            self.logger.warn('For the moment only one customization_launch_time can be submitted as filter')

        # get tags
        tag_values = data.get('tag_key_N', None)
        # resource_tags = ['nws$%s' % t for t in tag_values]

        # get status
        status_mapping = {
            'pending': SrvStatusType.PENDING,
            'building': SrvStatusType.BUILDING,
            'active': SrvStatusType.ACTIVE,
            'error': SrvStatusType.ERROR,
            'terminated': SrvStatusType.TERMINATED,
        }

        status_name_list = None
        status_list = data.get('state_name_N', None)
        if status_list is not None:
            status_name_list = [status_mapping[i] for i in status_list if i in status_mapping.keys()]

        # get customizations list
        res, total = controller.get_service_type_plugins(service_uuid_list=customization_id_list,
                                                         service_name_list=customization_name_list,
                                                         account_id_list=account_id_list,
                                                         filter_creation_date_start=customization_launch_time,
                                                         service_definition_id_list=customization_def_list,
                                                         servicetags_or=tag_values,
                                                         service_status_name_list=status_name_list,
                                                         plugintype=ApiComputeCustomization.plugintype,
                                                         **data_search)

        # format result
        customizations_set = [r.aws_info() for r in res]

        res = {
            'DescribeCustomizationsResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'customizationsSet': customizations_set,
                'customizationTotal': total
            }
        }
        return res


class CustomizationTypeArgResponseSchema(Schema):
    name = fields.String(required=True, example='test', description='parameter name')
    desc = fields.String(required=True, example='test', description='parameter description')
    type = fields.String(required=True, example='str', description='parameter type like int, str')
    default = fields.String(required=False, example='test', description='parameter default value')
    allowed = fields.String(required=False, example='', description='parameter allowed value')
    required = fields.String(required=False, example='', description='set if parameter is required')


class CustomizationTypeResponseSchema(Schema):
    id = fields.String(required=True, example='', description='customization type id')
    uuid = fields.String(required=True, example='', description='customization type uuid')
    name = fields.String(required=True, example='', description='customization type name')
    description = fields.String(required=True, allow_none=True, example='',
                                description='customization type description')
    args = fields.Nested(CustomizationTypeArgResponseSchema, required=False, many=False, allow_none=False,
                         description='customization type args')


class DescribeCustomizationTypesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='123', description='api request id')
    customizationTypesSet = fields.Nested(CustomizationTypeResponseSchema, required=True, many=True, allow_none=True,
                                          description='list of customization type info')
    customizationTypesTotal = fields.Integer(required=True, description='total number of customization type')


class DescribeCustomizationTypesApiResponseSchema(Schema):
    DescribeCustomizationTypesResponse = fields.Nested(DescribeCustomizationTypesApi1ResponseSchema, required=True,
                                                       many=False, allow_none=False)


class DescribeCustomizationTypesApiRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, default=10, missing=10, description='entities list page size',
                                context='query')
    NextToken = fields.Integer(required=False, default=0, missing=0, description='entities list page selected',
                               context='query')
    owner_id = fields.String(example='d35d19b3-d6b8-4208-b690-a51da2525497', required=True, context='query',
                             data_key='owner-id', description='account id of the instance type owner')
    CustomizationType = fields.String(required=False, allow_none=True, context='query', missing=None,
                                      description='list of customization type uuid')


class DescribeCustomizationTypes(ServiceApiView):
    summary = 'Describe compute customization types'
    description = 'Describe compute customization types'
    tags = ['computeservice']
    definitions = {
        'DescribeCustomizationTypesApiRequestSchema': DescribeCustomizationTypesApiRequestSchema,
        'DescribeCustomizationTypesApiResponseSchema': DescribeCustomizationTypesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeCustomizationTypesApiRequestSchema)
    parameters_schema = DescribeCustomizationTypesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeCustomizationTypesApiResponseSchema
        }
    })
    response_schema = DescribeCustomizationTypesApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        account_id = data.pop('owner_id')
        size = data.pop('MaxResults')
        page = data.pop('NextToken')
        def_id = data.pop('CustomizationType')
        account = controller.get_account(account_id)

        instance_types_set, total = account.get_definitions(plugintype=ApiComputeCustomization.plugintype,
                                                            service_definition_id=def_id, size=size, page=page)

        res_type_set = []
        for r in instance_types_set:
            res_type_item = {
                'id': r.oid,
                'uuid': r.uuid,
                'name': r.name,
                'description': r.desc,
                'args': []
            }

            if total == 1:
                config = r.get_main_config().params
                res_type_item['args'] = config.get('args', [])

            res_type_set.append(res_type_item)

        #     features = []
        #     if r.desc is not None:
        #         features = r.desc.split(' ')
        #
        #     feature = {}
        #     for f in features:
        #         try:
        #             k, v = f.split(':')
        #             feature[k] = v
        #         except ValueError:
        #             pass
        #
        #     res_type_item['features'] = feature
        #     res_type_set.append(res_type_item)
        #
        # if total == 1:
        #     res_type_set[0]['config'] = instance_types_set[0].get_main_config().params

        # customization_types_set, total = controller.get_catalog_service_definitions(
        #     size=data.pop('MaxResults', 10), page=int(data.pop('NextToken', 0)),
        #     plugintype='ComputeCustomization', def_uuids=data.pop('customization_type_N', []))



        res = {
            'DescribeCustomizationTypesResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'customizationTypesSet': res_type_set,
                'customizationTypesTotal': total
            }
        }
        return res


class RunCustomizationsApiParamArgRequestSchema(Schema):
    Name = fields.String(required=True, example='test', description='parameter name')
    Value = fields.String(required=True, example='test', description='parameter value')


class RunCustomizationsApiParamRequestSchema(Schema):
    Name = fields.String(required=True, example='test', description='customization name')
    owner_id = fields.String(required=True, example='test', data_key='owner-id', description='parent account id')
    CustomizationType = fields.String(required=True, example='nginx', description='customization type')
    Instances = fields.List(fields.String, required=True, exmaple='["6ee1916d-28b9-4d54-9676-63bb20784669"]',
                            description='list of compute instance id')
    Args = fields.Nested(RunCustomizationsApiParamArgRequestSchema, required=True, many=True, allow_none=False,
                         description='customization type args')


class RunCustomizationsApiRequestSchema(Schema):
    customization = fields.Nested(RunCustomizationsApiParamRequestSchema, context='body')


class RunCustomizationsApiBodyRequestSchema(Schema):
    body = fields.Nested(RunCustomizationsApiRequestSchema, context='body')


class RunCustomizationsApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='123', description='api request id')
    customizationId = fields.String(required=True, example='6ee1916d-28b9-4d54-9676-63bb20784669',
                                    description='customization id created')


class RunCustomizationsApiResponseSchema(Schema):
    RunCustomizationResponse = fields.Nested(RunCustomizationsApi1ResponseSchema, required=True)


class RunCustomization(ServiceApiView):
    summary = 'Create compute customization'
    description = 'Create compute customization'
    tags = ['computeservice']
    definitions = {
        'RunCustomizationsApiRequestSchema': RunCustomizationsApiRequestSchema,
        'RunCustomizationsApiResponseSchema': RunCustomizationsApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(RunCustomizationsApiBodyRequestSchema)
    parameters_schema = RunCustomizationsApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': RunCustomizationsApiResponseSchema
        }
    })
    response_schema = RunCustomizationsApiResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        inner_data = data.get('customization')

        service_definition_id = inner_data.get('CustomizationType')
        account_id = inner_data.get('owner_id')
        name = inner_data.get('Name')
        desc = name

        # check account
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        data['computeZone'] = parent_plugin.resource_uuid

        inst = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                  parent_plugin=parent_plugin, instance_config=data, account=account)

        res = {
            'RunCustomizationResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'customizationId': inst.instance.uuid
            }
        }

        return res, 202


class UpdateCustomizationResponseItemSchema(Schema):
    requestId = fields.String(required=True, example='123', description='api request id')
    customizationId = fields.String(required=True, example='3dd726eb-a303-4e97-9f99-d3b79e255b46',
                                    description='customization id')


class UpdateCustomizationResponseSchema(Schema):
    UpdateCustomizationResponse = fields.Nested(UpdateCustomizationResponseItemSchema, required=True, many=False,
                                                   allow_none=False)


class UpdateCustomizationRequestSchema(Schema):
    CustomizationId = fields.String(required=True, example='3dd726eb-a303-4e97-9f99-d3b79e255b46', context='query',
                                    description='customization id')


class UpdateCustomizationBodyRequestSchema(Schema):
    body = fields.Nested(UpdateCustomizationRequestSchema, context='body')


class UpdateCustomization(ServiceApiView):
    summary = 'Update compute customization'
    description = 'Update compute customization'
    tags = ['computeservice']
    definitions = {
        'UpdateCustomizationRequestSchema': UpdateCustomizationRequestSchema,
        'UpdateCustomizationResponseSchema': UpdateCustomizationResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateCustomizationBodyRequestSchema)
    parameters_schema = UpdateCustomizationRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UpdateCustomizationResponseSchema
        }
    })
    response_schema = UpdateCustomizationResponseSchema

    def put(self, controller: ServiceController, data, *args, **kwargs):
        customization_id = data.pop('CustomizationId')

        type_plugin = controller.get_service_type_plugin(customization_id)
        type_plugin.update()

        res = {
            'UpdateCustomizationResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'customizationId': customization_id
            }
        }

        return res, 202


class TerminateCustomizationResponseItemSchema(Schema):
    requestId = fields.String(required=True, example='123', description='api request id')
    customizationId = fields.String(required=True, example='3dd726eb-a303-4e97-9f99-d3b79e255b46',
                                    description='customization id')


class TerminateCustomizationResponseSchema(Schema):
    TerminateCustomizationResponse = fields.Nested(TerminateCustomizationResponseItemSchema, required=True, many=False,
                                                   allow_none=False)


class TerminateCustomizationRequestSchema(Schema):
    CustomizationId = fields.String(required=True, example='3dd726eb-a303-4e97-9f99-d3b79e255b46', context='query',
                                    description='customization id')


class TerminateCustomizationBodyRequestSchema(Schema):
    body = fields.Nested(TerminateCustomizationRequestSchema, context='body')


class TerminateCustomization(ServiceApiView):
    summary = 'Terminate compute customization'
    description = 'Terminate compute customization'
    tags = ['computeservice']
    definitions = {
        'TerminateCustomizationRequestSchema': TerminateCustomizationRequestSchema,
        'TerminateCustomizationResponseSchema': TerminateCustomizationResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(TerminateCustomizationBodyRequestSchema)
    parameters_schema = TerminateCustomizationRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': TerminateCustomizationResponseSchema
        }
    })
    response_schema = TerminateCustomizationResponseSchema

    def delete(self, controller:ServiceController, data, *args, **kwargs):
        customization_id = data.pop('CustomizationId')

        type_plugin = controller.get_service_type_plugin(customization_id)
        type_plugin.delete()

        res = {
            'TerminateCustomizationResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'customizationId': customization_id
            }
        }

        return res, 202


class ComputeCustomizationAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/computeservices/customization'
        rules = [
            # customization
            ('%s/describecustomizations' % base, 'GET', DescribeCustomizations, {}),
            ('%s/runcustomizations' % base, 'POST', RunCustomization, {}),
            ('%s/updatecustomizations' % base, 'PUT', UpdateCustomization, {}),
            ('%s/terminatecustomizations' % base, 'DELETE', TerminateCustomization, {}),
            # customization types
            ('%s/describecustomizationtypes' % base, 'GET', DescribeCustomizationTypes, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
