# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from six import ensure_text
from beehive_service.controller import ServiceController
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, GetApiObjectRequestSchema, PaginatedRequestQuerySchema, ApiView, \
    ApiManagerWarning
from beehive_service.plugins.storageservice.controller import StorageParamsNames as StPar, \
    ApiStorageService, ApiStorageEFS
from beehive.common.assert_util import AssertUtil
from beehive_service.service_util import __SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__, \
    __SRV_STORAGE_PERFORMANCE_MODE__,\
    __SRV_AWS_STORAGE_STATUS__, __SRV_STORAGE_GRANT_ACCESS_TYPE__,\
    __SRV_STORAGE_GRANT_ACCESS_LEVEL__, __REGEX_SHARE_GRANT_ACCESS_TO_USER__, \
    __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__, \
    __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__, \
    __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__
from ipaddress import IPv4Address, AddressValueError


class CreateFileSystemApiRequestSchema(Schema):
    owner_id = fields.String(required=True, example='', description='account id')
    Nvl_FileSystem_Size = fields.Integer(required=True, example=10,
                                         description='size in Giga byte of storage file system to create')
    Nvl_FileSystem_Type = fields.String(required=False, example='', missing=None,
                                        description='service definition for storage file system')
    CreationToken = fields.String(required=True, example='myFileSystem1', validate=Length(min=1, max=64),
                                  description='a string used to identify the file system')
    PerformanceMode = fields.String(required=False, example='shared', validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__),
                                    description='The performance mode of the file system. Can be shared or private')

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if 'KmsKeyId' in keys or 'Encrypted' in keys or 'ProvisionedThroughputInMibps' in keys \
                or 'ThroughputMode' in keys:
            raise ValidationError('The Encrypted, KmsKeyId, ProvisionedThroughputInMibps and '
                                  'ThroughputMode parameter are not supported')


class CreateFileSystemApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateFileSystemApiRequestSchema, context='body')


class FileSystemSize(Schema):
    Value = fields.Float(required=True, example='10',
                         description='Latest known metered size(in bytes) of data stored in the file system')
    Timestamp = fields.DateTime( required=False, example='1403301078',
                                 description='time of latest metered size of data in the file system')


class CustomMountTargetParamsApiResponse(Schema):
    CreationToken = fields.String(required=True, example='', description='file system storage name',
                                  validate=Length(min=1, max=64))
    CreationTime = fields.DateTime(required=True, example='1970-01-01T00:00:00Z',
                                   description='creation time file system storage')
    NumberOfMountTargets = fields.Integer(required=False, default=0, missing=0, example='', validate=Range(min=0),
                                          description='current number of mount targets that the file system has')
    SizeInBytes = fields.Nested(FileSystemSize, required=True, many=False, allow_none=True,
                                description='File System dimension')
    Name = fields.String(required=False, example='', description='resource tag name', validate=Length(min=0, max=256))
    nvl_shareProto = fields.String(required=False, allow_none=False, example='NFS',
                                   description='file system share protocol')


class StateReasonResponseSchema(Schema):
    nvl_code = fields.String(required=False, allow_none=True, example='', description='state code',
                             data_key='nvl-code')
    nvl_message = fields.String(required=False, allow_none=True, example='', description='state message',
                                data_key='nvl-message')


class FileSystemDescriptionResponseSchema(Schema):
    CreationToken = fields.String(required=True, example='', description='file system storage name',
                                  validate=Length(min=1, max=64))
    CreationTime = fields.DateTime(required=True, example='1970-01-01T00:00:00Z',
                                   description='creation time file system storage')
    Encrypted = fields.Boolean(required=False, missing=False,
                               description='boolean value that indicate if the storage file system is encrypted')
    FileSystemId = fields.String(required=True, example='', description='ID of the storage file system')
    KmsKeyId = fields.String(required=False, example='', description='ID of a Key Management Service',
                             validate=Length(min=1, max=2048))
    LifeCycleState = fields.String(required=True, example=' | '.join(map(str, __SRV_AWS_STORAGE_STATUS__)),
                                   description='LifeCycle state of FileSystem',
                                   validate=OneOf(__SRV_AWS_STORAGE_STATUS__))
    Name = fields.String(required=False, example='', description='resource tag name', validate=Length(min=0, max=256))
    NumberOfMountTargets = fields.Integer(required=False, default=0, missing=0, example='', validate=Range(min=0),
                                          description='current number of mount targets that the file system has')
    OwnerId = fields.String(required=True, example='', description='account id that created the file system')
    nvl_OwnerAlias = fields.String(required=True, example='', description='account name that created the file system',
                                   data_key='nvl-OwnerAlias')
    SizeInBytes = fields.Nested(FileSystemSize, required=True, many=False, allow_none=True,
                                description='File System dimension')
    PerformanceMode = fields.String(required=False, missing=__SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__, allow_none=True,
                                    example='', description='', validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__))
    ProvisionedThroughputInMibps = fields.Integer(required=False, example='', description='The throughput, measured '
                                                  'in MiB/s, that you want to provision for a file system.')
    ThroughputMode = fields.String(required=False, example='', validate=OneOf(['bursting', 'provisioned']),
                                   description='The throughput mode for a file system. There are two throughput modes '
                                   'to choose from for your file system: bursting and provisioned.')
    nvl_Capabilities = fields.List(fields.String, required=False, example=['grant'], data_key='nvl-Capabilities',
                                   description='list of file system available capabilities')
    nvl_shareProto = fields.String(required=False, description='share protocol', example='nfs')
    nvl_stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False, allow_none=True,
                                    data_key='nvl-stateReason')


class CreateFileSystemResultApiResponseSchema(Schema):
    fields.Nested(FileSystemDescriptionResponseSchema, required=True, many=False, allow_none=False)


class CreateFileSystem(ServiceApiView):
    summary = 'Create storage efs file system'
    description = 'Create storage efs file system'
    tags = ['storageservice']
    definitions = {
        'FileSystemDescriptionResponseSchema': FileSystemDescriptionResponseSchema,
        'CreateFileSystemApiRequestSchema': CreateFileSystemApiRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemApiBodyRequestSchema)
    parameters_schema = CreateFileSystemApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': FileSystemDescriptionResponseSchema
        }
    })
    response_schema = FileSystemDescriptionResponseSchema

    def post(self, controller, data, *args, **kwargs):
        inner_data = data
        service_definition_id = inner_data.get('Nvl_FileSystem_Type')
        account_id = inner_data.get('owner_id')
        name = inner_data.get('CreationToken')

        # check instance with the same name already exists
        # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiStorageService.plugintype)

        # get vpc definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiStorageEFS.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)

        # create service
        data['computeZone'] = parent_plugin.resource_uuid
        desc = 'efs ' + name + 'owned by ' + account.name
        cfg = {
            'share_data': data,
            'computeZone': parent_plugin.resource_uuid,
            'StorageService': parent_plugin.resource_uuid

        }
        plugin = controller.add_service_type_plugin(service_definition.oid, account_id, name=name, desc=desc,
                                                    parent_plugin=parent_plugin, instance_config=cfg)
        plugin.account = account
        res = plugin.aws_info()

        return res, 202


class DescribeFileSystemsRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='owner-id.N')
    CreationToken = fields.String(required=False, example='myFileSystem1', description='file system storage name',
                                  validate=Length(min=1, max=64), context='query')
    FileSystemId = fields.String(required=False, example='', description='ID of the File System', context='query')
    MaxItems = fields.Integer(required=False, default=10, missing=10, example='10', context='query',
                              description='max number elements to return in the response')
    Marker = fields.String(required=False, default='0', missing='0', example='0', description='pagination token',
                           context='query')


class DescribeFileSystemResponseSchema(FileSystemDescriptionResponseSchema):
    nvl_stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False, allow_none=True,
                                    data_key='nvl-stateReason')


class DescribeFileSystemsResponseSchema(Schema):
    FileSystems = fields.Nested(DescribeFileSystemResponseSchema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, description='pagination token')
    NextMarker = fields.String(required=True, allow_none=True, description='next pagination token')
    nvl_fileSystemTotal = fields.Integer(required=True, allow_none=True, data_key='nvl-fileSystemTotal',
                                         description='total number of filesystem items')


class DescribeFileSystems(ServiceApiView):
    summary = 'Describe storage efs file system'
    description = 'Describe storage efs file system'
    tags = ['storageservice']
    definitions = {
        'DescribeFileSystemsResponseSchema': DescribeFileSystemsResponseSchema,
        'DescribeFileSystemsRequestSchema': DescribeFileSystemsRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeFileSystemsRequestSchema)
    parameters_schema = DescribeFileSystemsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeFileSystemsResponseSchema
        }
    })
    response_schema = DescribeFileSystemsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        storage_id_list = []

        data_search = {}
        data_search['size'] = data.get('MaxItems')
        data_search['page'] = int(data.get('Marker'))

        # check Account
        owner_ids = data.get('owner_id_N', [])

        if len(owner_ids) > 0:
            account_id_list, zone_list = self.get_account_list(controller, data, ApiStorageService)
            if len(account_id_list) == 0:
                raise ApiManagerWarning("No StorageService found for owners ", code=404)
        else:
            account_id_list = []

        if data.get('FileSystemId', None) is not None:
            storage_inst = controller.get_service_instance(
                data.get('FileSystemId', None))
            AssertUtil.assert_is_not_none(storage_inst.getPluginType(ApiStorageEFS.plugintype),
                                          'instance id %s is not of plugin type %s' %
                                          (storage_inst.oid, ApiStorageEFS.plugintype))
            storage_id_list.append(storage_inst.oid)

        if data.get(StPar.CreationToken, None) is not None:
            storage_inst = controller.get_service_instance(
                data.get(StPar.CreationToken, None))
            AssertUtil.assert_is_not_none(storage_inst.getPluginType(ApiStorageEFS.plugintype),
                                          'instance id %s is not of plugin type %s' %
                                          (storage_inst.oid, ApiStorageEFS.plugintype))
            storage_id_list.append(storage_inst.oid)

        # get instances list
        res, total = controller.get_service_type_plugins(service_id_list=storage_id_list,
                                                         account_id_list=account_id_list,
                                                         plugintype=ApiStorageEFS.plugintype,
                                                         **data_search)
        storage_instances = [r.aws_info() for r in res]

        if total == 0:
            next_marker = '0'
        else:
            next_marker = str(data_search['page'] + 1)

        response = {
            'FileSystems': storage_instances,
            'Marker': data.get('Marker'),
            'NextMarker': next_marker,
            'nvl-fileSystemTotal': total
        }

        return response


class UpdateFileSystemResponseSchema(Schema):
    CreationToken = fields.String( required=True, example='', validate=Length(min=1, max=64),
                                   description='file system storage name')
    CreationTime = fields.DateTime(required=True, example='1970-01-01T00:00:00Z',
                                   description='creation time file system storage')
    Encrypted = fields.Boolean(required=False, missing=False,
                               description='boolean value that indicate if the storage file system is encrypted')
    FileSystemId = fields.String(required=True, example='', description='ID of the storage file system')
    KmsKeyId = fields.String(required=False, example='', description='ID of a Key Management Service',
                             validate=Length(min=1, max=2048))
    LifeCycleState = fields.String(required=True, example=' | '.join(map(str, __SRV_AWS_STORAGE_STATUS__)), description='LifeCycle state of FileSystem',
                                   validate=OneOf(__SRV_AWS_STORAGE_STATUS__))
    Name = fields.String(required=False, example='', description='resource tag name', validate=Length(min=0, max=256))
    NumberOfMountTargets = fields.Integer(required=False, default=0, missing=0, example='', validate=Range(min=0),
                                          description='current number of mount targets that the file system has')
    OwnerId = fields.String(required=True, example='', description='account id that created the file system')
    nvl_OwnerAlias = fields.String(required=True, example='', description='account name that created the file system')
    SizeInBytes = fields.Nested(FileSystemSize, required=True, many=False, allow_none=True,
                                description='File System dimension (Bytes)')
    PerformanceMode = fields.String(required=False, missing=__SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__, allow_none=True,
                                    example='', description='', validate=OneOf(__SRV_STORAGE_PERFORMANCE_MODE__))
    ProvisionedThroughputInMibps = fields.Integer(required=False, example='', description='The throughput, measured in '
                                                  'MiB/s, that you want to provision for a file system.')
    ThroughputMode = fields.String(required=False, example='', validate=OneOf(['bursting', 'provisioned']),
                                   description='The throughput mode for a file system. There are two throughput modes '
                                               'to choose from for your file system: bursting and provisioned.')


class UpdateFileSystemRequestSchema(Schema):
    oid = fields.String(required=False, description='id, uuid or name')
    Nvl_FileSystem_Size = fields.Integer(required=False, allow_none=True, example=10,
                                         description='Size of the file system size in Giga ')
    # ProvisionedThroughputInMibps
    # ThroughputMode

    @validates_schema
    def validate_parameters(self, data, *rags, **kvargs):
        if 'ProvisionedThroughputInMibps' in data or 'ThroughputMode' in data:
            raise ValidationError('The parameters ProvisionedThroughputInMibps, ThroughputMode are not supported')
        if StPar.Nvl_FileSystem_Size not in data:
            raise ValidationError('The parameters %s is required' % StPar.Nvl_FileSystem_Size)


class UpdateFileSystemBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateFileSystemRequestSchema, context='body')


class UpdateFileSystemBodyResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, allow_none=True, example='6d960236-d280-46d2-817d-f3ce8f0aeff7', description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, allow_none=True, example='6d960236-d280-46d2-817d-f3ce8f0aeff7', description='ID of the running task')


class UpdateFileSystem(ServiceApiView):
    summary = 'Update storage efs file system'
    description = 'Update storage efs file system'
    tags = ['storageservice']
    definitions = {
        'UpdateFileSystemRequestSchema': UpdateFileSystemRequestSchema,
        'UpdateFileSystemBodyResponseSchema': UpdateFileSystemBodyResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateFileSystemBodyRequestSchema)
    parameters_schema = UpdateFileSystemRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            'description': 'success',
            'schema': UpdateFileSystemBodyResponseSchema
        }
    })
    response_schema = UpdateFileSystemBodyResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        data.pop('oid', None)
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = type_plugin.resize_filesystem(**data)

        return {'nvl_JobId': task, 'nvl_TaskId': task}, 202


class DeleteFileSystemApiRequestSchema(GetApiObjectRequestSchema):
    pass


class DeleteFileSystemResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                            description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running task')


class DeleteFileSystem(ServiceApiView):
    summary = 'Delete storage efs file system'
    description = 'Delete storage efs file system'
    tags = ['storageservice']
    definitions = {
        'DeleteFileSystemApiRequestSchema': DeleteFileSystemApiRequestSchema,
        'DeleteFileSystemResponseSchema': DeleteFileSystemResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteFileSystemApiRequestSchema)
    # parameters_schema = DeleteFileSystemApiRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            'description': 'deleted instance uuid',
            'schema': DeleteFileSystemResponseSchema,
        }
    })
    response_schema = DeleteFileSystemResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        type_plugin = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        # type_plugin.instance.verify_permisssions('delete')
        # type_plugin.instance.verify_permisssions('update')
        type_plugin.delete_share()
        return {'nvl_JobId': type_plugin.active_task, 'nvl_TaskId': type_plugin.active_task}, 202


class CreateMountTargetApiRequestSchema(Schema):
    Nvl_FileSystemId = fields.String(required=True, example='fs-47a2c22e', description='storage file system ID')
    SubnetId = fields.String(required=True, example='subnet-748c5d03',
                             description='ID of the subnet to add the mount target in')
    Nvl_shareProto = fields.String(required=False, example='nfs', missing='nfs', validate=OneOf(['nfs', 'cifs']),
                                   description='File system share protocol')
    Nvl_shareLabel = fields.String(required=False, example='project', missing=None,
                                   description='Label to be used when you want to use a labelled share type')
    Nvl_shareVolume = fields.String(required=False, example='uenx79dsns', missing=None,
                                    description='id of a physical existing volume to set for mount target')

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if 'IpAddress' in keys or 'SecurityGroups' in keys:
            raise ValidationError('The parameters IpAddress, SecurityGroups are not supported')


class CreateMountTargetApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateMountTargetApiRequestSchema, context='body')


class CreateMountTargetApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                            description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running task')


class CreateMountTarget(ServiceApiView):
    summary = 'Create storage efs file system mount target'
    description = 'Create storage efs file system mount target'
    tags = ['storageservice']
    definitions = {
        'CreateMountTargetApiResponseSchema': CreateMountTargetApiResponseSchema,
        'CreateMountTargetApiRequestSchema': CreateMountTargetApiRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateMountTargetApiBodyRequestSchema)
    parameters_schema = CreateMountTargetApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CreateMountTargetApiResponseSchema
        }
    })
    response_schema = CreateMountTargetApiResponseSchema

    def post(self, controller, data, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(data.get(StPar.Nvl_FileSystemId), plugin_class=ApiStorageEFS)
        task = plugin_inst.create_mount_target(data.get('SubnetId'), data.get('Nvl_shareProto'),
                                               share_label=data.get('Nvl_shareLabel'),
                                               share_volume=data.get('Nvl_shareVolume'))
        return {'nvl_JobId': task, 'nvl_TaskId': task}, 202


# # create v1.1 create volume and mount target + tags
#
# class FileSystemTagSchema(Schema):
#     key = fields.String(required=False, allow_none=False, description='tag key')
#     value = fields.String(required=False, allow_none=False, description='tag value')
#
#
# class CreateFileSystemWithMountTargetRequestSchema(CreateFileSystemApiRequestSchema):
#     SubnetId = fields.String(
#         required=True,
#         example='subnet-748c5d03',
#         description='ID of the subnet to add the mount target in')
#     Nvl_shareProto = fields.String(
#         required=False,
#         example='nfs',
#         missing='nfs',
#         validate=OneOf(['nfs', 'cifs']),
#         description='File system share protocol')
#     Nvl_tags = fields.Nested(
#         FileSystemTagSchema,
#         many=True,
#         required=False,
#         allow_none=True)
#
#     @validates_schema
#     def validate_unsupported_parameters(self, data, *rags, **kvargs):
#         keys = data.keys()
#         if 'IpAddress' in keys or 'SecurityGroups' in keys:
#             raise ValidationError(
#                 'The parameters IpAddress, SecurityGroups are not supported')
#         if 'KmsKeyId' in keys or 'Encrypted' in keys or 'PerformanceMode' in keys or \
#                 'ProvisionedThroughputInMibps' in keys or 'ThroughputMode' in keys:
#             raise ValidationError('The Encrypted, KmsKeyId, PerformanceMode, ProvisionedThroughputInMibps and '
#                                   'ThroughputMode parameter are not supported')
#
#
# class CreateFileSystemWithMountTargetBodyRequestSchema(Schema):
#     body = fields.Nested(CreateFileSystemWithMountTargetRequestSchema, context='body')
#
#
# class CreateFileSystemWithMountTargetResponseSchema(FileSystemDescriptionResponseSchema):
#     nvl_JobId = fields.UUID(
#         default='db078b20-19c6-4f0e-909c-94745de667d4',
#         example='6d960236-d280-46d2-817d-f3ce8f0aeff7',
#         description='ID of the running job',
#         required=True)
#
#
# class CreateFileSystemWithMountTarget(ServiceApiView):
#     summary = 'Create storage efs file system mount target'
#     description = 'Create storage efs file system mount target'
#     tags = ['storageservice']
#     definitions = {
#         'CreateFileSystemWithMountTargetResponseSchema': CreateFileSystemWithMountTargetResponseSchema,
#         'CreateFileSystemWithMountTargetRequestSchema': CreateFileSystemWithMountTargetRequestSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(CreateFileSystemWithMountTargetBodyRequestSchema)
#     parameters_schema = CreateFileSystemWithMountTargetRequestSchema
#     responses = SwaggerApiView.setResponses({
#         202: {
#             'description': 'success',
#             'schema': CreateFileSystemWithMountTargetResponseSchema
#         }
#     })
#
#     def post(self, controller, data, *args, **kwargs):
#         """
#         Creates a new empty storage file system and his mount target and tags
#         """
#         service_definition_id = data.get(
#             StPar.Nvl_FileSystem_Type, None)
#         if service_definition_id is None:
#             raise ApiManagerWarning("empty %s" % StPar.Nvl_FileSystem_Type)
#
#         # Check  service definition is a beehive_service.plugins.storageservice.controller.ApiStorageEFS
#         servdef = controller.get_service_def(service_definition_id)
#         if servdef.model.service_type.plugintype.name_type != 'StorageEFS':
#             raise ApiManagerWarning("%s is not StorageEFS" % service_definition_id)
#
#         share_size = data.get(StPar.Nvl_FileSystem_Size, None)
#         if share_size is None:
#             raise ApiManagerWarning("empty %s" % StPar.Nvl_FileSystem_Size)
#
#         account_id = data.get(StPar.owner_id)
#         name = data.get(StPar.CreationToken)
#
#         account, parent_plugin = controller.check_service_type_plugin_parent_service(
#             account_id, 'StorageService')
#         cfg = {
#             'share_data': {
#                 StPar.CreationToken: name,
#                 StPar.Nvl_FileSystem_Size: share_size,
#                 StPar.Nvl_FileSystem_Type: service_definition_id,
#                 StPar.owner_id: account_id
#                 },
#             'computeZone': parent_plugin.resource_uuid,
#             'StorageService': parent_plugin.resource_uuid,
#         }
#
#         desc = 'efs ' + name + 'owned by ' + account.name
#         plugin = controller.add_service_type_plugin(
#             service_definition_id,
#             account_id,
#             name=name,
#             desc=desc,
#             parent_plugin=parent_plugin,
#             instance_config=cfg)
#         plugin.account=account
#         res = plugin.aws_info()
#
#         res['nvl_JobId'] = plugin.create_mount_target(data.get(StPar.SubnetId), data.get(StPar.Nvl_shareProto))
#
#         return res, 202


class DeleteMountTargetApiRequestSchema(Schema):
    MountTargetId = fields.String(required=False, example='', description='resource file system ID', context='query')
    Nvl_FileSystemId = fields.String( required=True, allow_none=False, example='', description='File system ID',
                                      data_key='Nvl_FileSystemId', context='query')

    @validates_schema
    def validate_unsupported_parameters(self, data, *rags, **kvargs):
        keys = data.keys()
        if 'MountTargetId' in keys:
            raise ValidationError(
                'The MountTargetId parameter is not supported: use Nvl_FileSystemId')


class DeleteMountTargetApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running task')


class DeleteMountTarget(ServiceApiView):
    summary = 'Delete storage efs file system mount target'
    description = 'Delete storage efs file system mount target'
    tags = ['storageservice']
    definitions = {
        'DeleteMountTargetApiRequestSchema': DeleteMountTargetApiRequestSchema,
        'DeleteMountTargetApiResponseSchema': DeleteMountTargetApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteMountTargetApiRequestSchema)
    parameters_schema = DeleteMountTargetApiRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            'description': 'no response',
            'schema': DeleteMountTargetApiResponseSchema
        }
    })
    response_schema = DeleteMountTargetApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        task = None
        instance_id = data.get(StPar.Nvl_FileSystemId)

        if instance_id is not None:
            plugin_inst = controller.get_service_type_plugin(instance_id, plugin_class=ApiStorageEFS)
            task = plugin_inst.delete_mount_target()

        return {'nvl_JobId': task, 'nvl_TaskId': task}, 202

#
# class DescribeMountTargetsRequestSchema(Schema):
#     owner_id_N = fields.List(
#         fields.String(example=''),
#         required=False,
#         allow_none=True,
#         context='query',
#         collection_format='multi',
#         data_key='owner-id.N')
#     MountTargetId = fields.String(
#         required=False,
#         example='fsmt-55a4413c',
#         description='mount target ID',
#         context='query')
#     FileSystemId = fields.String(
#         required=False,
#         example='',
#         description='file system ID',
#         context='query')
#     MaxItems = fields.Integer(
#         required=False,
#         missing=100,
#         validation=Range(min=1),
#         context='query',
#         description='max number elements to return in the response')
#     Marker = fields.String(
#         required=False,
#         missing='0',
#         example='',
#         description='pagination token',
#         context='query')


class DescribeMountTargetNestedResponseSchema(Schema):
    FileSystemId = fields.String(required=True, example='fs-47a2c22e', description='EFS File System Id')
    IpAddress = fields.String(required=False, example='172.16.1.1', description='uuid della risorsa.')
    LifeCycleState = fields.String(required=True, example=' | '.join(map(str, __SRV_AWS_STORAGE_STATUS__)), description='LifeCycle state of FileSystem',
                                   validate=OneOf(__SRV_AWS_STORAGE_STATUS__))
    MountTargetId = fields.String(required=False, allow_none=True, example='fsmt-55a4413c',
                                  description='The ID of an AWS Key Management Service customer master key(CMK) that '
                                  'was used to protect the encrypted file system.')
    NetworkInterfaceId = fields.String(required=False, allow_none=True, example='eni-d95852af')
    OwnerId = fields.String(required=False, example='251839141158', description='account id')
    nvl_OwnerAlias = fields.String(required=False, example='test', description='account name',
                                   data_key='nvl-OwnerAlias')
    SubnetId = fields.String(required=False, allow_none=True, example='subnet-748c5d03',
                             description='ID of the subnet to add the mount target in.')
    nvl_ShareProto = fields.String(required=False, allow_none=True, example='nfs', data_key='nvl-ShareProto',
                                   description='file system share protocol')
    nvl_AvailabilityZone = fields.String(required=False, allow_none=True, data_key='nvl-AvailabilityZone', example='SiteTorino01')
    # custom_params = fields.Nested(
    #     CustomMountTargetParamsApiResponse,
    #     required=False,
    #     many=False,
    #     allow_none=True,
    #     description='custom parameters')
    # CreationToken = fields.String(required=True, example='', description='file system storage name',
    #                               validate=Length(min=1, max=64))
    # CreationTime = fields.DateTime(required=True, example='1970-01-01T00:00:00Z',
    #                                description='creation time file system storage')
    # NumberOfMountTargets = fields.Integer(required=False, example='', validate=Range(min=0),
    #                                       description='current number of mount targets that the file system has')
    # SizeInBytes = fields.Nested(FileSystemSize, required=True, many=False, allow_none=True,
    #                             description='File System dimension')
    # Name = fields.String(required=False, example='', description='resource tag name',
    #                      validate=Length(min=0, max=256))


class DescribeMountTargetsResponseSchema(Schema):
    MountTargets = fields.Nested(DescribeMountTargetNestedResponseSchema, required=True, many=True, allow_none=True)
    Marker = fields.String(required=True, allow_none=True, description='pagination token')
    NextMarker = fields.String(required=True, allow_none=True, description='next pagination token')
    nvl_fileSystemTargetTotal = fields.Integer(required=True, allow_none=True, data_key='nvl_fileSystemTargetTotal',
                                               description='total number of target filesystem item')


class DescribeMountTargetsRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='owner-id.N')
    # MountTargetId = fields.String(required=False, example='fsmt-55a4413c', description='mount target ID',
    #                               context='query')
    FileSystemId = fields.String(required=False, example='', description='file system ID', context='query')
    MaxItems = fields.Integer(required=False, missing=100, validation=Range(min=1), context='query',
                              description='max number elements to return in the response')
    Marker = fields.String(required=False, missing='0', example='', description='pagination token', context='query')


class DescribeMountTargets(ServiceApiView):
    summary = 'Describe storage efs file system mount target'
    description = 'Describe storage efs file system mount target'
    tags = ['storageservice']
    definitions = {
        'DescribeMountTargetsRequestSchema': DescribeMountTargetsRequestSchema,
        'DescribeMountTargetsResponseSchema': DescribeMountTargetsResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeMountTargetsRequestSchema)
    parameters_schema = DescribeMountTargetsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeMountTargetsResponseSchema
        }
    })
    response_schema = DescribeMountTargetsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        storage_id_list = []

        data_search = {}
        data_search['size'] = data.get('MaxItems')
        data_search['page'] = int(data.get('Marker'))

        # check Account
        account_id_list, zone_list = self.get_account_list(controller, data, ApiStorageService)

        if data.get('FileSystemId', None) is not None:
            storage_inst = controller.get_service_instance(data.get('FileSystemId', None))
            AssertUtil.assert_is_not_none(storage_inst.getPluginType(ApiStorageEFS.plugintype),
                                          'instance id %s is not of plugin type %s' %
                                          (storage_inst.oid, ApiStorageEFS.plugintype))
            storage_id_list.append(storage_inst.oid)

        # get instances list
        res, total = controller.get_service_type_plugins(service_id_list=storage_id_list,
                                                         account_id_list=account_id_list,
                                                         plugintype=ApiStorageEFS.plugintype,
                                                         **data_search)
        mount_targets = [r.aws_info_target() for r in res if r.has_mount_target()]

        if total == 0:
            next_marker = '0'
        else:
            next_marker = str(data_search['page'] + 1)

        response = {
            'MountTargets': mount_targets,
            'Marker': data.get('Marker'),
            'NextMarker': next_marker,
            'nvl_fileSystemTargetTotal': total
        }

        return response


class GrantItemResponseSchema(Schema):
    access_level = fields.String(required=True, example='rw',
                                 description='The access level to the share file system instance. Is hold be rw or ro')
    access_type = fields.String(required=True, example='ip',
                                description='The access rule type. Valid value are: ip, cert, user')
    access_to = fields.String(required=True, example='10.102.186.0/24',
                              description='The value that defines the access.')
    state = fields.String(required=True, example='active',
                          description='The state of access rule of a given share file system instance')
    id = fields.String(required=True, example='52bea969-78a2-4f7e-ae84-fb4599dc06ca', description='The access rule ID.')


class ListFileSystemGrantResponseSchema(Schema):
    FileSystemId = fields.String(required=True, example='', description='ID of the storage file system')
    grants = fields.Nested(GrantItemResponseSchema, required=True, many=True, allow_none=True)


class ListFileSystemGrantRequestSchema(GetApiObjectRequestSchema, PaginatedRequestQuerySchema):
    pass


class ListFileSystemGrant(ServiceApiView):
    summary = 'List storage efs file system grant'
    description = 'List storage efs file system grant'
    tags = ['storageservice']
    definitions = {
        'ListFileSystemGrantResponseSchema': ListFileSystemGrantResponseSchema,
        'ListFileSystemGrantRequestSchema': ListFileSystemGrantRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListFileSystemGrantRequestSchema)
    parameters_schema = ListFileSystemGrantRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListFileSystemGrantResponseSchema
        }
    })
    response_schema = ListFileSystemGrantResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        grants = []

        try:
            res = plugin_inst.get_mount_target_resource()

            share_grants = res.get('details', {}).get('grants', {})
            for item in share_grants:
                grant = share_grants[item]
                if isinstance(grant, dict):
                    grant = [grant]
                grants.extend(grant)
        except:
            pass

        res = {
            'FileSystemId': plugin_inst.instance.uuid,
            'grants': grants
        }

        return res, 200


class CreateFileSystemGrantApiResponseSchema(Schema):
    jobid = fields.String(required=True, example='', allow_none=True, description='file system storage name',
                          validate=Length(min=1, max=64))


class CreateFileSystemGrantParamsApiRequestSchema(Schema):
    access_level = fields.String(required=True, example='rw', validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_LEVEL__),
                                 description='The access level to the share should be rw or ro')
    access_type = fields.String(required=True, example='ip', description='The access rule type',
                                validate=OneOf(__SRV_STORAGE_GRANT_ACCESS_TYPE__))
    access_to = fields.String(required=True, example='10.102.186.0/24',
                              description='The value that defines the access. - ip. A valid format is XX.XX.XX.XX or '
                              'XX.XX.XX.XX/XX. For example 0.0.0.0/0. - cert. A valid value is any string up to 64 '
                              'characters long in the common name(CN) of the certificate. - user. A valid value is an '
                              'alphanumeric string that can contain some special characters and is from 4 to 32 '
                              'characters long.')

    @validates_schema
    def validate_grant_access_parameters(self, data, *rags, **kvargs):
        msg1 = 'parameter is malformed. Range network prefix must be >= 0 and < 33'
        access_type = data.get('access_type', '').lower()
        access_to = data.get('access_to', '')
        if access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__:
            try:
                ip, prefix = access_to.split('/')
                prefix = int(prefix)
                if prefix < 0 or prefix > 32:
                    raise ValidationError(msg1)
                IPv4Address(ensure_text(ip))
            except AddressValueError:
                raise ValidationError(
                    'parameter access_to is malformed. Use xxx.xxx.xxx.xxx/xx syntax')
            except ValueError:
                raise ValidationError(msg1)
        elif access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__:
            if re.match(__REGEX_SHARE_GRANT_ACCESS_TO_USER__, access_to) is None:
                raise ValidationError('parameter access_to is malformed. A valid value is an alphanumeric string that '
                                      'can contain some special characters and is from 4 to 32 characters long')
        elif access_type == __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__:
            raise ValidationError(
                'parameter access_to "cert|CERT" value is not supported')
        else:
            raise ValidationError('parameter access_to is malformed')


class CreateFileSystemGrantApiResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running task')


class CreateFileSystemGrantApiRequestSchema(Schema):
    grant = fields.Nested(CreateFileSystemGrantParamsApiRequestSchema, context='body')


class CreateFileSystemGrantApiBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CreateFileSystemGrantApiRequestSchema, context='body')


class CreateFileSystemGrant(ServiceApiView):
    summary = 'Create storage efs file system grant'
    description = 'Create storage efs file system grant'
    tags = ['storageservice']
    definitions = {
        'CreateFileSystemGrantApiRequestSchema': CreateFileSystemGrantApiRequestSchema,
        'CreateFileSystemGrantApiResponseSchema': CreateFileSystemGrantApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateFileSystemGrantApiBodyRequestSchema)
    parameters_schema = CreateFileSystemGrantApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateFileSystemGrantApiResponseSchema
        }
    })
    response_schema = CreateFileSystemGrantApiResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        actiondata = data.get('grant', {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.grant_operation(action='add', **actiondata)

        return {'nvl_JobId': task, 'nvl_TaskId': task}, 202


class DeleteFileSystemGrantParamRequestSchema(Schema):
    access_id = fields.String(required=True, example='52bea969-78a2-4f7e-ae84-fb4599dc06ca',
                              description='The UUID of the access granted to a file system instance to be deletd')


class DeleteFileSystemGrantRequestSchema(Schema):
    grant = fields.Nested(DeleteFileSystemGrantParamRequestSchema, required=True, many=False, allow_none=False)


class DeleteFileSystemGrantBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteFileSystemGrantRequestSchema, context='body')


class DeleteFileSystemGrantResponseSchema(Schema):
    nvl_JobId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                             description='ID of the running job')
    nvl_TaskId = fields.UUID(required=True, example='db078b20-19c6-4f0e-909c-94745de667d4',
                              description='ID of the running task')


class DeleteFileSystemGrant(ServiceApiView):
    summary = 'Delete storage efs file system grant'
    description = 'Delete storage efs file system grant'
    tags = ['storageservice']
    definitions = {
        'DeleteFileSystemGrantRequestSchema': DeleteFileSystemGrantRequestSchema,
        'DeleteFileSystemGrantResponseSchema': DeleteFileSystemGrantResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteFileSystemGrantBodyRequestSchema)
    parameters_schema = DeleteFileSystemGrantRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            'description': 'success',
            'schema': DeleteFileSystemGrantResponseSchema
        }
    })
    response_schema = DeleteFileSystemGrantResponseSchema

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
        actiondata = data.get('grant', {})
        plugin_inst = controller.get_service_type_plugin(oid, plugin_class=ApiStorageEFS)
        task = plugin_inst.grant_operation(action='del', **actiondata)
        return {'nvl_JobId': task, 'nvl_TaskId': task}, 202


class StorageEfsServiceAPI(ApiView):

    @staticmethod
    def register_api(module, rules=None, version=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/storageservices/efs/file-systems' % base, 'POST', CreateFileSystem, {}),
            ('%s/storageservices/efs/file-systems' % base, 'GET', DescribeFileSystems, {}),
            # ('%s/storageservices/efs/file-systems/mount-targets' % base, 'POST', CreateFileSystemWithMountTarget, {}),

            ('%s/storageservices/efs/file-systems/<oid>' % base, 'PUT', UpdateFileSystem, {}),
            ('%s/storageservices/efs/file-systems/<oid>' % base, 'DELETE', DeleteFileSystem, {}),

            ('%s/storageservices/efs/mount-targets' % base, 'POST', CreateMountTarget, {}),
            ('%s/storageservices/efs/mount-targets' % base, 'DELETE', DeleteMountTarget, {}),
            ('%s/storageservices/efs/mount-targets' % base, 'GET', DescribeMountTargets, {}),

            ('%s/storageservices/efs/mount-targets/<oid>/grants' % base, 'POST', CreateFileSystemGrant, {}),
            ('%s/storageservices/efs/mount-targets/<oid>/grants' % base, 'DELETE', DeleteFileSystemGrant, {}),
            ('%s/storageservices/efs/mount-targets/<oid>/grants' % base, 'GET', ListFileSystemGrant, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
        # ApiView.register_api(module, rulesv11, version='v1.1')
