# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from six import ensure_text
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.model import Division, Organization
from beehive_service.plugins.computeservice.controller import ApiComputeService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiManagerError, SwaggerApiView, GetApiObjectRequestSchema, PaginatedRequestQuerySchema, ApiView, \
    ApiManagerWarning
from beehive_service.plugins.monitoringservice.controller import ApiMonitoringService, ApiMonitoringFolder
from beehive.common.assert_util import AssertUtil
from ipaddress import IPv4Address, AddressValueError
from beehive.common.data import operation


class CreateFolderApiParamRequestSchema(Schema):
    owner_id = fields.String(required=True, example='1', data_key='owner-id', description='account id or uuid associated to compute zone')
    Name = fields.String(required=False, example='test', missing=None, description='folder name')
    AdditionalInfo = fields.String(required=False, example='test', missing=None, description='folder description')
    definition = fields.String(required=False, example='monitoring.folder.xxx', description='service definition of the folder')
    norescreate = fields.Boolean(required=False, allow_none=True, description='don\'t create physical resource of the folder')


class CreateFolderApiRequestSchema(Schema):
    folder = fields.Nested(CreateFolderApiParamRequestSchema, context='body')


class CreateFolderApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateFolderApiRequestSchema, context='body')


class CreateFolderApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns')
    requestId = fields.String(required=True, example='', allow_none=True)
    folderId = fields.String(required=True, example='29647df5-5228-46d0-a2a9-09ac9d84c099', description='folder id')
    nvl_activeTask = fields.String(required=True, example='29647df5-5228-46d0-a2a9-09ac9d84c099',
                                   data_key='nvl-activeTask', description='task id')


class CreateFolderApiResponseSchema(Schema):
    CreateFolderResponse = fields.Nested(CreateFolderApiResponse1Schema, required=True, many=False,
                                        allow_none=False)


class CreateFolder(ServiceApiView):
    summary = 'Create monitoring folder'
    description = 'Create monitoring folder'
    tags = ['monitoringservice']
    definitions = {
        'CreateFolderApiResponseSchema': CreateFolderApiResponseSchema,
        'CreateFolderApiRequestSchema': CreateFolderApiRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateFolderApiBodyRequestSchema)
    parameters_schema = CreateFolderApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CreateFolderApiResponseSchema
        }
    })
    response_schema = CreateFolderApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        self.logger.debug('CreateFolder post - begin')
        inner_data = data.get('folder')

        service_definition_id = inner_data.get('definition') # es. monitoring.folder.default2
        account_id = inner_data.get('owner_id')
        name = inner_data.get('Name', None)
        desc = inner_data.get('AdditionalInfo', None)

        # check account
        account: ApiAccount
        parent_plugin: ApiMonitoringService
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiMonitoringService.plugintype)
        data['computeZone'] = parent_plugin.resource_uuid

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = '%s.%s.%s' % (org.name, div.name, account.name)
        self.logger.debug('CreateFolder - triplet: %s' % triplet)

        if name is None:
            name = 'DefaultFolder'
            # name = triplet + '-folder'
            desc = triplet

        data.update({'triplet': triplet})
        data.update({'organization': org.name})
        data.update({'division': div.name})
        data.update({'account': account.name})

        if service_definition_id is None:
            # self.logger.debug('CreateFolder - ApiMonitoringFolder.plugintype: %s' % ApiMonitoringFolder.plugintype)
            service_definition = controller.get_default_service_def(ApiMonitoringFolder.plugintype)
        else:
            # self.logger.debug('CreateFolder - service_definition_id: %s' % service_definition_id)
            service_definition = controller.get_service_def(service_definition_id)
        self.logger.debug('CreateFolder - service_definition: %s' % service_definition)

        plugin: ApiMonitoringFolder
        plugin = controller.add_service_type_plugin(service_definition.oid, account_id, name=name, desc=desc,
                                                    parent_plugin=parent_plugin, instance_config=data, account=account)

        res = {
            'CreateFolderResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'folderId': plugin.instance.uuid,
                'nvl-activeTask': plugin.active_task
            }
        }
        return res, 202


class DeleteFolderApiRequestSchema(Schema):
    FolderId = fields.String(required=False, example='29647df5-5228-46d0-a2a9-09ac9d84c099', description='folder id',
                            context='query')


class DeleteFolderApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns')
    requestId = fields.String(required=True, example='', description='operation id')
    folderId = fields.String(required=False, example='29647df5-5228-46d0-a2a9-09ac9d84c099', description='folder id')
    nvl_activeTask = fields.String(required=True, example='29647df5-5228-46d0-a2a9-09ac9d84c099',
                                   data_key='nvl-activeTask', description='task id')


class DeleteFolderApiResponseSchema(Schema):
    DeleteFolderResponse = fields.Nested(DeleteFolderApiResponse1Schema, required=True, many=False,
                                        allow_none=False)


class DeleteFolder(ServiceApiView):
    summary = 'Delete monitoring folder'
    description = 'Delete monitoring folder'
    tags = ['monitoringservice']
    definitions = {
        'DeleteFolderApiRequestSchema': DeleteFolderApiRequestSchema,
        'DeleteFolderApiResponseSchema': DeleteFolderApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteFolderApiRequestSchema)
    parameters_schema = DeleteFolderApiRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            'description': 'no response',
            'schema': DeleteFolderApiResponseSchema
        }
    })
    response_schema = DeleteFolderApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        folder_id = data.get('FolderId')
        type_plugin = controller.get_service_type_plugin(folder_id)
        type_plugin.delete()

        res = {
            'DeleteFolderResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'folderId': type_plugin.instance.uuid,
                'nvl-activeTask': type_plugin.active_task
            }
        }
        return res, 202


class MonitoringFolderStateReasonResponseSchema(Schema):
    nvl_code = fields.Integer(required=False, allow_none=True, example='', description='state code',
                             data_key='nvl-code')
    nvl_message = fields.String(required=False, allow_none=True, example='', description='state message',
                                data_key='nvl-message')


class MonitoringFolderEndpointResponseSchema(Schema):
    home = fields.String(required=True, example='https://localhost/s/prova/app/home#/',
                         description='folder home endpoint')
    discover = fields.String(required=True, example='https://localhost/s/prova/app/discover#/',
                             description='folder discover view endpoint')


class MonitoringFolderDashboardResponseSchema(Schema):
    dashboardId = fields.String(required=True, example='c6772ba4-0fc2-493b-86a3-6edf717cb2ff',
                                description='id of the dashboard')
    dashboardName = fields.String(required=True, example='[Filebeat MySQL] Overview ECS',
                                  description='name of the dashboard')
    dashboardVersion = fields.String(required=True, example='WzE3Mjk0MTksMTRd', description='dashboard version')
    dashboardScore = fields.Int(required=True, example=1, description='dashboard score')
    modificationDate = fields.String(required=True, example='2022-01-25T10:21:26.772Z',
                                     description='dashboard modification date')
    endpoint = fields.String(required=True, description='folder dashboard endpoint',
                             example='https://localhost/s/prova/app/dashboards#/view/dusnawiu7cnsdiu')


class MonitoringFolderItemParameterResponseSchema(Schema):
    id = fields.String(required=True, example='075df680-2560-421c-aeaa-8258a6b733f0', description='id of the folder')
    name = fields.String(required=True, example='test', description='name of the folder')
    creationDate = fields.DateTime(required=True, example='2022-01-25T11:20:18Z', description='creation date')
    description = fields.String(required=True, example='test', description='description of the folder')
    ownerId = fields.String(required=True, example='075df680-2560-421c-aeaa-8258a6b733f0',
                            description='account id of the owner of the folder')
    ownerAlias = fields.String(required=True, allow_none=True, example='test',
                               description='account name of the owner of the folder')
    state = fields.String(required=True, example='available', description='state of the folder', data_key='state')
    stateReason = fields.Nested(MonitoringFolderStateReasonResponseSchema, many=False, required=True,
                                description='state folder description')
    templateId = fields.String(required=True, example='075df680-2560-421c-aeaa-8258a6b733f0',
                               description='id of the folder template')
    templateName = fields.String(required=True, example='test', description='name of the folder template')
    endpoints = fields.Nested(MonitoringFolderEndpointResponseSchema, many=False, required=True)
    dashboards = fields.Nested(MonitoringFolderDashboardResponseSchema, many=True, required=True)


class DescribeMonitoringFolders1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='$xmlns')
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True, allow_none=True)
    folderInfo = fields.Nested(MonitoringFolderItemParameterResponseSchema, many=True, required=False,
                              allow_none=True)
    folderTotal = fields.Integer(required=False, example='0', descriptiom='total monitoring instance',
                                data_key='folderTotal')


class DescribeFoldersResponseSchema(Schema):
    DescribeFoldersResponse = fields.Nested(DescribeMonitoringFolders1ResponseSchema, required=True, many=False)


class DescribeFoldersRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='owner-id.N', description='account id')
    FolderName = fields.String(required=False, description='folder name', context='query')
    folder_id_N = fields.List(fields.String(), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='folder-id.N',
                             description='list of folder id')
    MaxItems = fields.Integer(required=False, missing=100, validation=Range(min=1), context='query',
                              description='max number elements to return in the response')
    Marker = fields.String(required=False, missing='0', example='', description='pagination token', context='query')


class DescribeFolders(ServiceApiView):
    summary = 'Describe monitoring folder'
    description = 'Describe monitoring folder'
    tags = ['monitoringservice']
    definitions = {
        'DescribeFoldersRequestSchema': DescribeFoldersRequestSchema,
        'DescribeFoldersResponseSchema': DescribeFoldersResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeFoldersRequestSchema)
    parameters_schema = DescribeFoldersRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeFoldersResponseSchema
        }
    })
    response_schema = DescribeFoldersResponseSchema

    def get(self, controller, data, *args, **kwargs):
        monitoring_id_list = []

        data_search = {}
        data_search['size'] = data.get('MaxItems')
        data_search['page'] = int(data.get('Marker'))

        # check Account
        account_id_list, zone_list = self.get_account_list(controller, data, ApiMonitoringService)

        # get instance identifier
        instance_id_list = data.get('folder_id_N', [])
        self.logger.debug('DescribeFolders get - instance_id_list: %s' % instance_id_list)

        # get instance name
        instance_name_list = data.get('FolderName', None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]
        self.logger.debug('DescribeFolders get - instance_name_list: %s' % instance_name_list)

        # get instances list
        res, total = controller.get_service_type_plugins(service_uuid_list=instance_id_list,
                                                         service_name_list=instance_name_list,
                                                         service_id_list=monitoring_id_list,
                                                         account_id_list=account_id_list,
                                                         plugintype=ApiMonitoringFolder.plugintype,
                                                         **data_search)
        instances_set = []
        for r in res:
            r: ApiMonitoringFolder
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = '0'
        else:
            next_token = str(data_search['page'] + 1)

        res = {
            'DescribeFoldersResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'next_token': next_token,
                'folderInfo': instances_set,
                'folderTotal': total
            }
        }
        return res


class SyncUsersFolderApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns', example='http://nivolapiemonte.it/XMLdoc/2022-05-16/folder/')
    Return = fields.Boolean(required=True, example=True, allow_none=False, data_key='return')
    requestId = fields.String(required=True, example='folderXX-3525-4f95-880d-479acdb463a4', allow_none=True)
    nvl_activeTask = fields.String(required=True, allow_none=True, data_key='nvl-activeTask',
                                   description='active task id')


class SyncUsersFolderApiResponseSchema(Schema):
    SyncFolderUsersResponse = fields.Nested(SyncUsersFolderApi1ResponseSchema, required=True, many=False, allow_none=False)


class SyncUsersFolderApiRequestSchema(Schema):
    FolderId = fields.String(required=True, description='monitoring folder id', context='query')


class SyncUsersFolderApiBodyRequestSchema(Schema):
    body = fields.Nested(SyncUsersFolderApiRequestSchema, context='body')


class SyncUsersFolder(ServiceApiView):
    summary = 'Syncronize users in a grafana folder'
    description = 'Syncronize users in a grafana folder'
    tags = ['monitoringservice']
    definitions = {
        'SyncUsersFolderApiRequestSchema': SyncUsersFolderApiRequestSchema,
        'SyncUsersFolderApiResponseSchema': SyncUsersFolderApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(SyncUsersFolderApiBodyRequestSchema)
    parameters_schema = SyncUsersFolderApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': SyncUsersFolderApiResponseSchema
        }
    })
    response_schema = SyncUsersFolderApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        oid = data.get('FolderId')
        type_plugin: ApiMonitoringFolder = controller.get_service_type_plugin(oid, plugin_class=ApiMonitoringFolder)
        return_value = type_plugin.sync_users()

        res = {
            'SyncFolderUsersResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'return': return_value,
                'nvl-activeTask': type_plugin.active_task
            }
        }
        return res, 202


class MonitoringFolderServiceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/monitoringservices/folders'
        rules = [
            ('%s/createfolder' % base, 'POST', CreateFolder, {}),
            ('%s/deletefolder' % base, 'DELETE', DeleteFolder, {}),
            ('%s/describefolders' % base, 'GET', DescribeFolders, {}),
            ('%s/syncfolderusers' % base, 'PUT', SyncUsersFolder, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
