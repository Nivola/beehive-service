# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib import response
from flasgger import fields, Schema
from beehive_service.plugins.computeservice.controller import ApiComputeService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerError
from marshmallow.validate import OneOf
from beehive.common.data import operation


class DescribeBackupRestorePointsRequestSchema(Schema):
    owner_id = fields.String(required=True, data_key='owner-id', description='account id', context='query')
    InstanceId = fields.String(required=False, data_key='InstanceId', missing=None, description='instance id', context='query')
    JobId = fields.String(required=False, data_key='JobId', missing=None, description='job id', context='query')
    RestorePointId = fields.String(required=False, data_key='RestorePointId', missing=None,
                                   description='restore point id', context='query')


class DescribeInstanceBackup3ResponseSchema(Schema):
    tot = fields.Float(required=False, description='restore point total storage size')
    restore = fields.Float(required=False, description='restore point restore storage size')
    uploaded = fields.Float(required=False, description='restore point uploaded storage size')


class DescribeInstanceBackup4ResponseSchema(Schema):
    warning = fields.String(required=False, allow_none=True, description='restore point warning message')
    progress = fields.String(required=False, allow_none=True, description='restore point progress message')
    error = fields.String(required=False, allow_none=True, description='restore point error message')


class DescribeInstanceBackup5ResponseSchema(Schema):
    uuid = fields.String(required=False, description='instance uuid')
    name = fields.String(required=False, description='instance name')


class DescribeInstanceBackup2ResponseSchema(Schema):
    id = fields.String(required=True, description='restore point id')
    name = fields.String(required=True, description='restore point name')
    desc = fields.String(required=True, description='restore point description')
    created = fields.String(required=True, description='restore point creation date')
    finished = fields.String(required=False, description='restore point end date')
    updated = fields.String(required=False, description='restore point update date')
    type = fields.String(required=True, description='restore point type. Can be full or incremental')
    status = fields.String(required=True, description='restore point status')
    hypervisor = fields.String(required=False, description='restore point hypervisor. Only openstack is actually '
                                                           'supported')
    site = fields.String(required=False, description='restore point site')
    resource_type = fields.String(required=False, description='restore point type of managed resource. Only '
                                                              'ComputeInstance is actually supported')
    time_taken = fields.Int(required=False, description='restore point execution time')
    progress = fields.Int(required=False, description='restore point execution progress in %')
    size = fields.Nested(DescribeInstanceBackup3ResponseSchema, required=False, allow_none=True,
                         description='restore point storage size explain')
    message = fields.Nested(DescribeInstanceBackup4ResponseSchema, required=False, allow_none=True,
                            description='restore point execution messages')
    instanceSet = fields.Nested(DescribeInstanceBackup5ResponseSchema, required=False, many=True, allow_none=True,
                                description='list of restore point instances')


class DescribeInstanceBackup1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='$xmlns')
    requestId = fields.String(required=True, example='', allow_none=True, description='api request id')
    restorePointSet = fields.Nested(DescribeInstanceBackup2ResponseSchema, required=True, many=True, allow_none=True,
                                    description='list of restore points')
    restorePointTotal = fields.Integer(required=True, description='number of restore points')


class DescribeBackupRestorePointsResponseSchema(Schema):
    DescribeBackupRestorePointsResponse = fields.Nested(DescribeInstanceBackup1ResponseSchema, required=True,
                                                        many=False, allow_none=False)


class DescribeBackupRestorePoints(ServiceApiView):
    summary = 'Describe backup job restore points'
    description = 'Describe backup job restore points'
    tags = ['computeservice']
    definitions = {
        'DescribeBackupRestorePointsRequestSchema': DescribeBackupRestorePointsRequestSchema,
        'DescribeBackupRestorePointsResponseSchema': DescribeBackupRestorePointsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeBackupRestorePointsRequestSchema)
    parameters_schema = DescribeBackupRestorePointsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeBackupRestorePointsResponseSchema
        }
    })
    response_schema = DescribeBackupRestorePointsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        instance_id = data.get('InstanceId', None)
        job_id = data.get('JobId', None)
        restore_point_id = data.get('RestorePointId', None)

        from beehive_service.plugins.computeservice.controller import ApiComputeInstance, ApiComputeInstanceBackup

        restore_points = []
        if job_id is not None:
            account, parent_plugin = self.check_parent_service(controller, account_id,
                                                               plugintype=ApiComputeService.plugintype)
            plugin: ApiComputeInstanceBackup = parent_plugin.get_compute_instance_backup()
            restore_points = plugin.get_job_restore_points(job_id, restore_point_id=restore_point_id)

        elif instance_id is not None:
            plugin: ApiComputeInstance = controller.get_service_type_plugin(instance_id)
            restore_points = plugin.get_job_restore_points()

        else:
            msg = 'Filter for job_id (and restore_point_id for detail) or instance_id to return restore points'
            self.logger.warning(msg)
            raise ApiManagerError(msg)

        res = {
            'DescribeBackupRestorePointsResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'restorePointSet': restore_points,
                'restorePointTotal': len(restore_points)
            }
        }
        return res


class DescribeInstanceBackupRestores2ResponseSchema(Schema):
    instanceId = fields.String(required=True, example='', description='instance id')
    restores = fields.List(fields.Dict, required=True, example='[{}]', description='list of restores')


class DescribeInstanceBackupRestores1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='$xmlns')
    requestId = fields.String(required=True, example='', allow_none=True)
    restoreSet = fields.Nested(DescribeInstanceBackupRestores2ResponseSchema, required=True, many=True, allow_none=True)
    restoreTotal = fields.Integer(required=True)


class DescribeBackupRestoresResponseSchema(Schema):
    DescribeBackupRestoresResponse = fields.Nested(DescribeInstanceBackupRestores1ResponseSchema,
                                                   required=True, many=False, allow_none=False)


class DescribeBackupRestoresRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=False,
                             collection_format='multi', data_key='owner-id.N',
                             description='account ID of the instance owner', context='query')
    InstanceId_N = fields.List(fields.String(example=''), required=True, allow_none=True,
                               collection_format='multi', data_key='InstanceId.N', description='instance id list', context='query')
    RestorePoint = fields.String(required=True, allow_none=True, data_key='RestorePoint', description='restore point', context='query')


# class DescribeBackupRestoresBodyRequestSchema(Schema):
#     body = fields.Nested(DescribeBackupRestoresRequestSchema, context='body')


class DescribeBackupRestores(ServiceApiView):
    summary = 'Reboot compute instance'
    description = 'Reboot compute instance'
    tags = ['computeservice']
    definitions = {
        'DescribeBackupRestoresRequestSchema': DescribeBackupRestoresRequestSchema,
        'DescribeBackupRestoresResponseSchema': DescribeBackupRestoresResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeBackupRestoresRequestSchema)
    parameters_schema = DescribeBackupRestoresRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeBackupRestoresResponseSchema
        }
    })
    response_schema = DescribeBackupRestoresResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_ids = data.pop('InstanceId_N')
        restore_point = data.get('RestorePoint')
        instance_backups_set = []
        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id)
            resp = {'instanceId': instance_id}
            resp.update(type_plugin.get_backup_restores(restore_point))
            instance_backups_set.append(resp)

        res = {
            'DescribeBackupRestoresResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'restoreSet': instance_backups_set,
                'restoreTotal': len(instance_ids)
            }
        }
        return res


class CreateBackupRestorePointsRequestSchema(Schema):
    owner_id = fields.String(required=True, data_key='owner-id', description='account id')
    JobId = fields.String(required=True, data_key='JobId', description='backup job id')
    Name = fields.String(required=True, data_key='Name', description='backup job restore point name')
    Desc = fields.String(required=False, data_key='Desc', missing=None,
                         description='backup job restore point description')
    BackupFull = fields.Boolean(required=False, missing=True,
                                description='If True make a full backup otherwise make an incremental backup')


class CreateInstancesBackupBodyRequestSchema(Schema):
    body = fields.Nested(CreateBackupRestorePointsRequestSchema, context='body')


# class CreateInstancesBackup2ResponseSchema(Schema):
#     instanceId = fields.String(required=False, example='', description='instance ID')


class CreateInstancesBackup1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    request_return = fields.String(required=True, example=True, data_key='return', description='simple return value')
    # restorePointSet = fields.Nested(CreateInstancesBackup2ResponseSchema, required=True, many=True, allow_none=True)


class CreateBackupRestorePointsResponseSchema(Schema):
    CreateBackupRestorePoints = fields.Nested(CreateInstancesBackup1ResponseSchema, required=True, many=False,
                                              allow_none=False)


class CreateBackupRestorePoints(ServiceApiView):
    summary = 'Create backup restore points'
    description = 'Create backup restore points'
    tags = ['computeservice']
    definitions = {
        'CreateBackupRestorePointsRequestSchema': CreateBackupRestorePointsRequestSchema,
        'CreateBackupRestorePointsResponseSchema': CreateBackupRestorePointsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateInstancesBackupBodyRequestSchema)
    parameters_schema = CreateBackupRestorePointsRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateBackupRestorePointsResponseSchema
        }
    })
    response_schema = CreateBackupRestorePointsResponseSchema

    def post(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId', None)
        name = data.get('Name', None)
        desc = data.get('Desc', None)
        backup_full = data.get('BackupFull', True)

        restore_point_set = []
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        plugin = parent_plugin.get_compute_instance_backup()
        res = plugin.add_job_restore_point(job_id, name, desc=desc, full=backup_full)

        res = {
            'CreateBackupRestorePoints': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'return': True
                # 'restorePointSet': restore_point_set
            }
        }
        return res, 202


class DeleteBackupRestorePointsRequestSchema(Schema):
    owner_id = fields.String(required=True, data_key='owner-id', description='account id')
    JobId = fields.String(required=True, data_key='JobId', description='backup job id')
    RestorePointId = fields.String(required=True, data_key='RestorePointId',
                                   description='id of the restore point to use')


class DeleteInstancesBackupBodyRequestSchema(Schema):
    body = fields.Nested(DeleteBackupRestorePointsRequestSchema, context='body')


class DeleteInstancesBackup1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    request_return = fields.String(required=True, example=True, data_key='return', description='simple return value')


class DeleteBackupRestorePointsResponseSchema(Schema):
    DeleteBackupRestorePoints = fields.Nested(DeleteInstancesBackup1ResponseSchema, required=True, many=False,
                                              allow_none=False)


class DeleteBackupRestorePoints(ServiceApiView):
    summary = 'Delete backup restore points'
    description = 'Delete backup restore points'
    tags = ['computeservice']
    definitions = {
        'DeleteBackupRestorePointsRequestSchema': DeleteBackupRestorePointsRequestSchema,
        'DeleteBackupRestorePointsResponseSchema': DeleteBackupRestorePointsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteInstancesBackupBodyRequestSchema)
    parameters_schema = DeleteBackupRestorePointsRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': DeleteBackupRestorePointsResponseSchema
        }
    })
    response_schema = DeleteBackupRestorePointsResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId', None)
        restore_point_id = data.get('RestorePointId', None)

        # restore_point_set = []
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        plugin = parent_plugin.get_compute_instance_backup()
        res = plugin.del_job_restore_point(job_id, restore_point_id)

        res = {
            'DeleteBackupRestorePoints': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'return': True
                # 'restorePointSet': restore_point_set
            }
        }
        return res, 202


class CreateBackupRestoreApiRequestSchema(Schema):
    owner_id = fields.String(required=False, allow_none=False, data_key='owner-id',
                             description='account ID of the instance owner')
    InstanceId = fields.String(required=True, data_key='InstanceId', description='id of the instance to restore')
    RestorePointId = fields.String(required=True, data_key='RestorePointId',
                                   description='id of the restore point to use')
    InstanceName = fields.String(required=True, example='test', description='restored instance name')
    # AdminPassword = fields.String(required=False, example='myPwd1$', description='admin password to set')
    # SecurityGroupId_N = fields.List(fields.String(example='12'), required=False, allow_none=False,
    #                                 data_key='SecurityGroupId.N', description='list of instance security group ids')
    # KeyName = fields.String(required=False, example='1ffd', description='The name of the key pair')


class CreateBackupRestoreApiRequestSchema(Schema):
    instance = fields.Nested(CreateBackupRestoreApiRequestSchema, context='body')


class CreateBackupRestoreBodyRequestSchema(Schema):
    body = fields.Nested(CreateBackupRestoreApiRequestSchema, context='body')


class CreateBackupRestoreApi3ResponseSchema(Schema):
    code = fields.Integer(required=False, default=0)
    name = fields.String(required=True, example='PENDING')


class CreateBackupRestoreApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True)


class CreateBackupRestoreApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    instancesSet = fields.Nested(CreateBackupRestoreApi2ResponseSchema, many=True, required=True)


class CreateBackupRestoreApiResponseSchema(Schema):
    CreateBackupRestoreResponse = fields.Nested(CreateBackupRestoreApi1ResponseSchema, required=True)


class CreateBackupRestore(ServiceApiView):
    summary = 'Restore an instance from a Backup restore point. A new instance is created'
    description = 'Restore an instance from a Backup restore point. A new instance is created'
    tags = ['computeservice']
    definitions = {
        'CreateBackupRestoreApiRequestSchema': CreateBackupRestoreApiRequestSchema,
        'CreateBackupRestoreApiResponseSchema': CreateBackupRestoreApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateBackupRestoreBodyRequestSchema)
    parameters_schema = CreateBackupRestoreApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateBackupRestoreApiResponseSchema
        }
    })
    response_schema = CreateBackupRestoreApiResponseSchema

    def post(self, controller, data, *args, **kwargs):
        from beehive_service.plugins.computeservice.controller import ApiComputeInstance, ApiComputeInstanceBackup

        data = data.get('instance')
        instance_id = data.pop('InstanceId')
        restore_point_id = data.pop('RestorePointId')
        name = data.pop('InstanceName')
        instances_set = []
        type_plugin: ApiComputeInstance = controller.get_service_type_plugin(instance_id)
        inst: ApiComputeInstanceBackup = type_plugin.restore_from_backup(restore_point_id, name)
        instances_set.append({'instanceId': inst.instance.uuid})

        res = {
            'CreateBackupRestoreResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'instancesSet': instances_set
            }
        }
        return res, 202


class DescribeBackupJobsRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=True, allow_none=False, context='query',
        collection_format='multi', data_key='owner-id.N', description='account ID of the job owner')
    jobId = fields.String(example='34r5tfgyyg', required=False, missing=None, data_key='JobId', context='query', description='backup job id')


class DescribeBackupJobsInstanceResponseSchema(Schema):
    instanceId = fields.String(required=True, example='4ee5557c-1994-49de-8411-0652df230ef6',
                               description='compute instance id')
    name = fields.String(required=True, example='instance123', description='compute instance name')


class InstanceSetResponseSchema(Schema):
    uuid = fields.String(required=True, example='2ddd528d-c9b4-4d7e-8722-cc395140255a', description='instance uuid')
    name = fields.String(required=True, example='bk-job-policy-14-retention', description='instance name')

class DescribeBackupJobs2ResponseSchema(Schema):
    jobId = fields.String(required=False, allow_none=True, example='', description='instance id')
    owner_id = fields.String(example='test123', required=True, data_key='owner_id',
                             description='account ID of the job owner')
    name = fields.String(required=True, example='job123', description='job name')
    desc = fields.String(required=False, allow_none=True, example='desc job123', description='desc job name')
    hypervisor = fields.String(example='openstack', missing='openstack', required=False, description='hypervisor type')
    policy = fields.Dict(required=True, example='bk-job-policy-14-retention', description='job policy')
    availabilityZone = fields.String(required=True, example='SiteTorino01', description='availability zone of the job')
    # instanceSet = fields.String(required=True, example='SiteTorino01', description='list of compute instances')
    instanceSet = fields.Nested(InstanceSetResponseSchema, required=False, many=True, allow_none=True)
    instanceNum = fields.Integer(required=False, data_key='instanceNum', description='number of compute instances')
    jobState = fields.String(required=True, example='available', description='current job status')
    reason = fields.String(required=True, allow_none=True, example='', description='reason for the current state of the job')
    created = fields.DateTime(required=True, example='2021-06-28T12:12:02.000000', description='job creation time')
    updated = fields.DateTime(required=True, example='2021-07-12T15:11:49.000000', description='job update time')
    enabled = fields.Boolean(required=True, example=True, description='tell if job schedule is enabled')
    usage = fields.Float(required=False, description='usage space backup')


class DescribeBackupJobs1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobSet = fields.Nested(DescribeBackupJobs2ResponseSchema, required=True, many=True, allow_none=True)
    jobTotal = fields.Integer(required=True)
    xmlns = fields.String(required=False, data_key='$xmlns')


class DescribeBackupJobsResponseSchema(Schema):
    DescribeBackupJobsResponse = fields.Nested(DescribeBackupJobs1ResponseSchema, required=True,
                                               many=False, allow_none=False)


class DescribeBackupJobs(ServiceApiView):
    summary = 'Describe backup jobs'
    description = 'Describe backup jobs'
    tags = ['computeservice']
    definitions = {
        'DescribeBackupJobsRequestSchema': DescribeBackupJobsRequestSchema,
        'DescribeBackupJobsResponseSchema': DescribeBackupJobsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeBackupJobsRequestSchema)
    parameters_schema = DescribeBackupJobsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeBackupJobsResponseSchema
        }
    })
    response_schema = DescribeBackupJobsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_ids = data.get('owner_id_N')
        job_id = data.get('jobId')
        
        self.logger.debug('DescribeBackupJobs - account_ids: %s' % account_ids)
        self.logger.debug('DescribeBackupJobs - job_id: %s' % job_id)

        if job_id is not None and len(account_ids) == 0:
            raise ApiManagerError('Filter for account list or for tuple (account, job_id)')

        # response
        all_jobs = []

        # check accounts
        from beehive_service.plugins.computeservice.controller import ApiComputeInstanceBackup, ApiComputeService
        for account_id in account_ids:
            parent_plugin: ApiComputeService
            account, parent_plugin = self.check_parent_service(controller, account_id,
                                                               plugintype=ApiComputeService.plugintype)
            inst: ApiComputeInstanceBackup = parent_plugin.get_compute_instance_backup()
            jobs = inst.list_jobs(job_id=job_id)
            all_jobs.extend(jobs)

        # get backup job set
        job_backups_set = all_jobs

        res = {
            'DescribeBackupJobsResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'jobSet': job_backups_set,
                'jobTotal': len(job_backups_set)
            }
        }
        return res


class CreateBackupJobRequestSchema(Schema):
    owner_id = fields.String(example='test123', required=True, data_key='owner-id',
                             description='account ID of the job owner')
    Name = fields.String(required=True, example='job123', description='job name')
    Desc = fields.String(required=False, allow_none=True, example='desc job123', description='desc job name')
    Hypervisor = fields.String(example='openstack', missing='openstack', required=False,
                               validate=OneOf(['openstack']), description='hypervisor type')
    Policy = fields.String(required=False, missing='bk-job-policy-7-7-retention', example='bk-job-policy-7-7-retention',
                           description='job policy')
    AvailabilityZone = fields.String(required=True, example='SiteTorino01', description='availability zone of the job')
    InstanceId_N = fields.List(fields.String(example=''), required=True, collection_format='multi',
                               data_key='InstanceId.N', description='job id')


class CreateInstancesBackupBodyRequestSchema(Schema):
    body = fields.Nested(CreateBackupJobRequestSchema, context='body')


class CreateInstancesBackup2ResponseSchema(Schema):
    jobId = fields.String(required=False, example='29647df5-5228-46d0-a2a9-09ac9d84c099', description='job ID')


class CreateInstancesBackup1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobsSet = fields.Nested(CreateInstancesBackup2ResponseSchema, required=True, many=True, allow_none=True)


class CreateBackupJobResponseSchema(Schema):
    CreateBackupJob = fields.Nested(CreateInstancesBackup1ResponseSchema, required=True, many=False,
                                    allow_none=False)


class CreateBackupJob(ServiceApiView):
    summary = 'Create backup job'
    description = 'Create backup job'
    tags = ['computeservice']
    definitions = {
        'CreateBackupJobRequestSchema': CreateBackupJobRequestSchema,
        'CreateBackupJobResponseSchema': CreateBackupJobResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateInstancesBackupBodyRequestSchema)
    parameters_schema = CreateBackupJobRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateBackupJobResponseSchema
        }
    })
    response_schema = CreateBackupJobResponseSchema

    def post(self, controller, data, *args, **kwargs):
        from beehive_service.plugins.computeservice.controller import ApiComputeInstanceBackup, ApiComputeService
        from beehive_service.controller.api_account import ApiAccount
        
        account_id = data.get('owner_id')
        instance_ids = data.pop('InstanceId_N')
        name = data.get('Name')
        desc = data.get('Desc')
        site = data.get('AvailabilityZone')
        flavor = data.get('Policy')
        hypervisor = data.get('Hypervisor')

        jobs_set = []
        parent_plugin: ApiComputeService
        account: ApiAccount
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        inst: ApiComputeInstanceBackup = parent_plugin.get_compute_instance_backup()
        job_id = inst.add_job(account, name, desc, site, flavor, instance_ids, hypervisor=hypervisor)
        jobs_set.append({'jobId': job_id})

        res = {
            'CreateBackupJob': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'jobsSet': jobs_set
            }
        }
        return res, 202


class ModifyBackupJobRequestSchema(Schema):
    owner_id = fields.String(example='test123', required=True, data_key='owner-id',
                             description='account ID of the job owner')
    JobId = fields.String(example='job123', required=True, data_key='JobId', description='job id')
    Name = fields.String(required=False, example='job123', description='job name')
    Policy = fields.String(required=False, missing=None, example='bk-job-policy-14-retention',
                           description='job policy')
    Enabled = fields.Boolean(required=False, example=True, description='enable or disable job')


class ModifyInstancesBackupBodyRequestSchema(Schema):
    body = fields.Nested(ModifyBackupJobRequestSchema, context='body')


class ModifyInstancesBackup2ResponseSchema(Schema):
    jobId = fields.String(required=False, example='', description='job ID')


class ModifyInstancesBackup1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobsSet = fields.Nested(ModifyInstancesBackup2ResponseSchema, required=True, many=True, allow_none=True)


class ModifyBackupJobResponseSchema(Schema):
    ModifyBackupJob = fields.Nested(ModifyInstancesBackup1ResponseSchema, required=True, many=False,
                                    allow_none=False)


class ModifyBackupJob(ServiceApiView):
    summary = 'Modify backup job'
    description = 'Modify backup job'
    tags = ['computeservice']
    definitions = {
        'ModifyBackupJobRequestSchema': ModifyBackupJobRequestSchema,
        'ModifyBackupJobResponseSchema': ModifyBackupJobResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ModifyInstancesBackupBodyRequestSchema)
    parameters_schema = ModifyBackupJobRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': ModifyBackupJobResponseSchema
        }
    })
    response_schema = ModifyBackupJobResponseSchema

    def put(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId')
        name = data.get('Name')
        flavor = data.get('Policy')
        enabled = data.get('Enabled')

        jobs_set = []
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        inst = parent_plugin.get_compute_instance_backup()
        job_id = inst.update_job(job_id, name=name, flavor=flavor, enabled=enabled)
        jobs_set.append({'jobId': job_id})

        res = {
            'ModifyBackupJob': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'jobsSet': jobs_set
            }
        }
        return res, 202


class DeleteBackupJobRequestSchema(Schema):
    owner_id = fields.String(example='account123', required=True, data_key='owner-id',
                             description='account ID of the job owner')
    JobId = fields.String(example='job123', required=True, data_key='JobId', description='job id')


class DeleteJobsBackupBodyRequestSchema(Schema):
    body = fields.Nested(DeleteBackupJobRequestSchema, context='body')


class DeleteJobsBackup2ResponseSchema(Schema):
    jobId = fields.String(required=False, example='', description='job ID')


class DeleteJobsBackup1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobsSet = fields.Nested(DeleteJobsBackup2ResponseSchema, required=True, many=True, allow_none=True)


class DeleteBackupJobResponseSchema(Schema):
    DeleteBackupJob = fields.Nested(DeleteJobsBackup1ResponseSchema, required=True, many=False, allow_none=False)


class DeleteBackupJob(ServiceApiView):
    summary = 'Delete backup restore points'
    description = 'Delete backup restore points'
    tags = ['computeservice']
    definitions = {
        'DeleteBackupJobRequestSchema': DeleteBackupJobRequestSchema,
        'DeleteBackupJobResponseSchema': DeleteBackupJobResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteJobsBackupBodyRequestSchema)
    parameters_schema = DeleteBackupJobRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': DeleteBackupJobResponseSchema
        }
    })
    response_schema = DeleteBackupJobResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId')

        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        inst = parent_plugin.get_compute_instance_backup()
        inst.del_job(job_id)
        jobs_set = {'jobId': job_id}

        res = {
            'DeleteBackupJob': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'jobsSet': jobs_set
            }
        }
        return res, 202


class AddBackupJobInstanceRequestSchema(Schema):
    owner_id = fields.String(example='account123', required=True, data_key='owner-id',
                             description='account ID of the job owner')
    JobId = fields.String(example='job123', required=True, data_key='JobId', description='job id')
    InstanceId = fields.String(example='inst123', required=True, data_key='InstanceId',
                               description='compute instance id')


class AddBackupJobInstanceBodyRequestSchema(Schema):
    body = fields.Nested(AddBackupJobInstanceRequestSchema, context='body')


class AddBackupJobInstance2ResponseSchema(Schema):
    jobId = fields.String(required=False, example='', description='job ID')


class AddBackupJobInstance1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobsSet = fields.Nested(AddBackupJobInstance2ResponseSchema, required=True, many=True, allow_none=True)


class AddBackupJobInstanceResponseSchema(Schema):
    AddBackupJobInstance = fields.Nested(AddBackupJobInstance1ResponseSchema, required=True, many=False,
                                         allow_none=False)


class AddBackupJobInstance(ServiceApiView):
    summary = 'Create backup job'
    description = 'Create backup job'
    tags = ['computeservice']
    definitions = {
        'AddBackupJobInstanceRequestSchema': AddBackupJobInstanceRequestSchema,
        'AddBackupJobInstanceResponseSchema': AddBackupJobInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(AddBackupJobInstanceBodyRequestSchema)
    parameters_schema = AddBackupJobInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': AddBackupJobInstanceResponseSchema
        }
    })
    response_schema = AddBackupJobInstanceResponseSchema

    def post(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId')
        instance_id = data.get('InstanceId')

        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        inst = parent_plugin.get_compute_instance_backup()
        inst.add_instance_to_job(job_id, instance_id)
        jobs_set = {'jobId': job_id}

        res = {
            'AddBackupJobInstance': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'jobsSet': jobs_set
            }
        }
        return res, 202


class DelBackupJobInstanceRequestSchema(Schema):
    owner_id = fields.String(example='account123', required=True, data_key='owner-id',
                             description='account ID of the job owner')
    JobId = fields.String(example='job123', required=True, data_key='JobId', description='job id')
    InstanceId = fields.String(example='inst123', required=True, data_key='InstanceId',
                               description='compute instance id')


class DelBackupJobInstanceBodyRequestSchema(Schema):
    body = fields.Nested(DelBackupJobInstanceRequestSchema, context='body')


class DelBackupJobInstance2ResponseSchema(Schema):
    jobId = fields.String(required=False, example='', description='job ID')


class DelBackupJobInstance1ResponseSchema(Schema):
    requestId = fields.String(required=True, example='', allow_none=True)
    jobsSet = fields.Nested(DelBackupJobInstance2ResponseSchema, required=True, many=True, allow_none=True)


class DelBackupJobInstanceResponseSchema(Schema):
    DelBackupJobInstance = fields.Nested(DelBackupJobInstance1ResponseSchema, required=True, many=False,
                                         allow_none=False)


class DelBackupJobInstance(ServiceApiView):
    summary = 'Delete backup restore points'
    description = 'Delete backup restore points'
    tags = ['computeservice']
    definitions = {
        'DelBackupJobInstanceRequestSchema': DelBackupJobInstanceRequestSchema,
        'DelBackupJobInstanceResponseSchema': DelBackupJobInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DelBackupJobInstanceBodyRequestSchema)
    parameters_schema = DelBackupJobInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': DelBackupJobInstanceResponseSchema
        }
    })
    response_schema = DelBackupJobInstanceResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        account_id = data.get('owner_id')
        job_id = data.get('JobId')
        instance_id = data.get('InstanceId')

        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        inst = parent_plugin.get_compute_instance_backup()
        inst.del_instance_from_job(job_id, instance_id)
        jobs_set = {'jobId': job_id}

        res = {
            'DelBackupJobInstance': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'jobsSet': jobs_set
            }
        }
        return res, 202


class DescribeBackupJobPoliciesApiRequestSchema(Schema):
    owner_id = fields.String(example='d35d19b3-d6b8-4208-b690-a51da2525497', required=True, context='query',
                             data_key='owner-id', description='account id of the instance type owner')
    # MaxResults = fields.Integer(required=False, default=10, description='entities list page size', context='query')
    # NextToken = fields.String(required=False, default='0', description='entities list page selected', context='query')
    # job_policy_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                            collection_format='multi', data_key='instance-type.N',
    #                            description='list of instance type uuid')


class InstanceTypeFeatureResponseSchema(Schema):
    vcpus = fields.String(required=False, allow_none=True, example='', description='')
    ram = fields.String(required=False, allow_none=True, example='', description='')
    disk = fields.String(required=False, allow_none=True, example='', description='')


class JobPolicyResponseSchema(Schema):
    id = fields.Integer(required=True, example='123', description='policy id')
    uuid = fields.String(required=True, example='2ddd528d-c9b4-4d7e-8722-cc395140255a', description='policy uuid')
    name = fields.String(required=True, example='bk-job-policy-14-retention', description='policy name')
    fullbackup_interval = fields.Integer(required=True, example=7, description='interval between full backup')
    restore_points = fields.Integer(required=True, example=14, description='number of restore points to retain')
    start_time_window = fields.String(required=True, example='19:00-05:00', description='window where is selected '
                                      'starting tim from the system')
    interval = fields.String(required=True, example='24hrs', description='time interval from two restore points')
    timezone = fields.String(required=True, example='Europe/Rome', description='backup job timezone')


class DescribeBackupJobPoliciesApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key='$xmlns')
    requestId = fields.String(required=True, description='api request id')
    jobPoliciesSet = fields.Nested(JobPolicyResponseSchema, required=True, many=True, allow_none=True)
    jobPoliciesTotal = fields.Integer(required=True)


class DescribeBackupJobPoliciesApiResponseSchema(Schema):
    DescribeBackupJobPoliciesResponse = fields.Nested(DescribeBackupJobPoliciesApi1ResponseSchema, required=True,
                                                      many=False, allow_none=False)


class DescribeBackupJobPolicies(ServiceApiView):
    summary = 'List backup job policies'
    description = 'List backup job policies'
    tags = ['computeservice']
    definitions = {
        'DescribeBackupJobPoliciesApiRequestSchema': DescribeBackupJobPoliciesApiRequestSchema,
        'DescribeBackupJobPoliciesApiResponseSchema': DescribeBackupJobPoliciesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeBackupJobPoliciesApiRequestSchema)
    parameters_schema = DescribeBackupJobPoliciesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeBackupJobPoliciesApiResponseSchema
        }
    })
    response_schema = DescribeBackupJobPoliciesApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.pop('owner_id')
        account = controller.get_account(account_id)

        service_defs, total = account.get_definitions(plugintype='VirtualService', size=-1)

        job_policies_set, total = [], 0
        for service_def in service_defs:
            if service_def.name.find('bk-job-policy') != 0:
                continue
            self.logger.warn(service_def.get_config('start_time_window'))
            item = {
                'id': service_def.oid,
                'uuid': service_def.uuid,
                'name': service_def.name,
                'fullbackup_interval': service_def.get_config('fullbackup_interval'),
                'restore_points': service_def.get_config('restore_points'),
                'start_time_window': '-'.join(service_def.get_config('start_time_window')),
                'interval': service_def.get_config('interval'),
                'timezone': service_def.get_config('timezone')
            }
            job_policies_set.append(item)
            total += 1

        res = {
            'DescribeBackupJobPoliciesResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'jobPoliciesSet': job_policies_set,
                'jobPoliciesTotal': total
            }
        }
        return res


class ComputeInstanceBackupAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/computeservices/instancebackup'
        rules = [
            # backup job
            ('%s/describebackupjobs' % base, 'GET', DescribeBackupJobs, {}),
            ('%s/createbackupjob' % base, 'POST', CreateBackupJob, {}),
            ('%s/modifybackupjob' % base, 'PUT', ModifyBackupJob, {}),
            ('%s/deletebackupjob' % base, 'DELETE', DeleteBackupJob, {}),
            ('%s/addbackupjobinstance' % base, 'POST', AddBackupJobInstance, {}),
            ('%s/delbackupjobinstance' % base, 'DELETE', DelBackupJobInstance, {}),

            # backup job types
            ('%s/describebackupjobpolicies' % base, 'GET', DescribeBackupJobPolicies, {}),

            # instance
            ('%s/describebackuprestorepoints' % base, 'GET', DescribeBackupRestorePoints, {}),
            ('%s/createbackuprestorepoints' % base, 'POST', CreateBackupRestorePoints, {}),
            ('%s/deletebackuprestorepoints' % base, 'DELETE', DeleteBackupRestorePoints, {}),
            ('%s/describebackuprestores' % base, 'GET', DescribeBackupRestores, {}),
            ('%s/createbackuprestores' % base, 'POST', CreateBackupRestore, {}),
        ]
        kwargs["version"]='v1.0'
        ApiView.register_api(module, rules, **kwargs)
