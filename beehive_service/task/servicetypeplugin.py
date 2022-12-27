# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.task.job import Job, JobTask, task_local, job_task, job
from beehive.common.task.manager import task_manager
from beecell.simple import id_gen, import_func
from ..model.base import SrvStatusType
from beehive.common.apimanager import ApiManagerError
from beehive_service.entity.service_instance import ApiServiceInstance
from .common import logger


#
# ServiceTypePluginJob
#
class AbstractServiceTypePluginTask(object):
    def __init__(self, *args, **kwargs):
        Job.__init__(self, *args, **kwargs)

    def get_type_plugin(self, instance, plugin_class=None, details=False):
        """Get type plugin instance.

        :param instance: service instance oid
        :param plugin_class: service type plugin class [optional]
        :param details: if False does not get entity details [default=False]
        :return: service type plugin instance
        :raises ApiManagerError: if query empty return error.
        """
        plugin = task_local.controller.get_service_type_plugin(
            instance, plugin_class=plugin_class, details=details)
        return plugin


class ServiceTypePluginJob(Job, AbstractServiceTypePluginTask):
    """ServiceTypePluginJob class. Use this class for task that execute create,
    update and delete of resources and childs.

    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    :example:

        .. code-block:: python

            @task_manager.task(bind=True, base=ServiceTypePluginJob)
            @job(entity_class=OpenstackRouter, name='insert')
            def prova(self, objid, **kvargs):
                pass
    """
    abstract = True


class ServiceTypePluginJobTask(JobTask, AbstractServiceTypePluginTask):
    """ServiceTypePluginJobTask class. Use this class for task that execute create,
    update and delete of resources and childs.

    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    :example:

        .. code-block:: python

            @task_manager.task(bind=True, base=ServiceTypePluginJobTask)
            @jobtask()
            def prova(self, options):
                pass
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.

        :param exc: The exception raised by the task.
        :param task_id: Unique id of the failed task.
        :param args: Original arguments for the task that failed.
        :param kwargs: Original keyword arguments for the task that failed.
        :param einfo: ExceptionInfo instance, containing the traceback.
        :return: The return value of this handler is ignored.
        """
        JobTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        # get params from shared data
        params = self.get_shared_data()
        self.get_session()

        # get resource
        try:
            plugin = self.get_type_plugin(params.get(u'id'), details=False)

            # update resource state
            plugin.update_status(SrvStatusType.ERROR, error=str(exc))
        except ApiManagerError as ex:
            if ex.code == 404:
                self.logger.warn(ex)
            else:
                raise


#
# service type plugin main job
#
def import_task(task_def):
    if isinstance(task_def, dict):
        components = task_def[u'task'].split(u'.')
        mod = __import__(
            u'.'.join(components[:-1]), globals(), locals(), [components[-1]], -1)
        func = getattr(mod, components[-1], None)

        task_def[u'task'] = import_func(task_def[u'task'])
        task = task_def
    else:
        task = import_func(task_def)
    return task


def job_helper(inst, objid, params):
    task_defs = params.pop(u'tasks')
    tasks = []
    for task_def in task_defs:
        if isinstance(task_def, list):
            sub_tasks = []
            for sub_task_def in task_def:
                sub_tasks.append(import_task(sub_task_def))
            tasks.append(sub_tasks)
        else:
            tasks.append(import_task(task_def))

    return Job.start(inst, tasks, params)


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'create.insert', delta=4)
def job_type_plugin_instance_create(self, objid, params):
    """Create type plugin instance

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params
    :param params:
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.desc: service instance desc
    :param params.attribute: attributes
    :param params.tags: comma separated service instance tags to assign [default=u'']
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
        a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'update.update', delta=4)
def job_type_plugin_instance_update(self, objid, params):
    """Update type plugin instance

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params {u'cid':.., u'id':.., u'etx_id':..}
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.resource_uuid: instance uuid
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
            a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'patch.update', delta=4)
def job_type_plugin_instance_patch(self, objid, params):
    """Patch type plugin instance

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params {u'cid':.., u'id':.., u'etx_id':..}
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.resource_uuid: instance uuid
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
            a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'action.update', delta=4)
def job_type_plugin_instance_action(self, objid, params):
    """Send action to type plugin instance

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params {u'cid':.., u'id':.., u'etx_id':..}
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.resource_uuid: instance uuid
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
            a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'remove.delete', delta=4)
def job_type_plugin_instance_delete(self, objid, params):
    """Delete type plugin instance

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params {u'cid':.., u'id':.., u'etx_id':..}
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.resource_uuid: instance uuid
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
            a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


@task_manager.task(bind=True, base=ServiceTypePluginJob)
@job(entity_class=ApiServiceInstance, name=u'action.update', delta=4)
def job_type_plugin_instance_action(self, objid, params):
    """Run type plugin instance action

    :param objid: objid of the service instance. Ex. 110//2222//334//*
    :param params: input params
    :param params.id: service instance id
    :param params.uuid: service instance uuid
    :param params.objid: service instance objid
    :param params.name: service instance name
    :param params.resource_uuid: instance uuid
    :param params.resource_params: params used to create resource
    :param params.tasks: list of task to execute. Set full module path for task. Task can be a string with task name or
            a dict like {u'task':<task name>, u'args':..}
    :return: True
    """
    res = job_helper(self, objid, params)
    return res


#
# service type plugin tasks
#
@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def create_resource_task(self, options):
    """Create remote resource

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param dict sharedarea: input params
    :param sharedarea.id: instance id
    :param sharedarea.id: instance oid
    :param sharedarea.uuid: instance uuid
    :param sharedarea.objid: instance objid
    :param sharedarea.name: name
    :param sharedarea.desc: desc
    :param sharedarea.attribute: None
    :param sharedarea.tags: None
    :param sharedarea.resource_params: input params
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()

    # validate input params
    instance_id = params.get(u'id')
    resource_params = params.get(u'resource_params')
    self.progress(u'Get configuration params')

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.progress(u'Get plugin %s' % plugin)

    # create resource
    res = plugin.create_resource(self, resource_params)
    self.progress(u'Create resource %s' % res)

    # update configuration
    plugin.update_status(SrvStatusType.ACTIVE)
    self.progress(u'Set plugin %s configuration' % plugin)

    return res


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def update_resource_task(self, options):
    """Update remote resource

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param dict sharedarea: input params
    :param sharedarea.id: instance id
    :param sharedarea.uuid: instance uuid
    :param sharedarea.objid: instance objid
    :param sharedarea.name: instance name
    :param sharedarea.resource_uuid: instance uuid
    :param sharedarea.resource_params: input params
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()

    # validate input params
    instance_id = params.get(u'id')
    resource_params = params.get(u'resource_params')
    resource_uuid = params.get(u'resource_uuid')
    self.progress(u'Get configuration params')

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.progress(u'Get plugin %s' % plugin)

    # update resource
    if resource_uuid is not None:
        res = plugin.update_resource(self, **resource_params)
        self.progress(u'Update resource %s' % res)

    # update configuration
    plugin.update_status(SrvStatusType.ACTIVE)
    self.progress(u'Set plugin %s configuration' % plugin)

    return True


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def patch_resource_task(self, options):
    """Patch remote resource

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param dict sharedarea: input params
    :param sharedarea.id: instance id
    :param sharedarea.id: instance oid
    :param sharedarea.uuid: instance uuid
    :param sharedarea.objid: instance objid
    :param sharedarea.name: instance name
    :param sharedarea.resource_uuid: instance uuid
    :param sharedarea.resource_params: input params
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()

    # validate input params
    instance_id = params.get(u'id')
    resource_params = params.get(u'resource_params')
    resource_uuid = params.get(u'resource_uuid')
    self.progress(u'Get configuration params')
    logger.warn(resource_params)
    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.progress(u'Get plugin %s' % plugin)

    # update resource
    if resource_uuid is not None:
        res = plugin.patch_resource(self, **resource_params)
        self.progress(u'Patch resource %s' % res)

    # update configuration
    plugin.update_status(SrvStatusType.ACTIVE)
    self.progress(u'Set plugin %s configuration' % plugin)

    return True


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def action_resource_task(self, options):
    """Send action remote resource

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param dict sharedarea: input params
    :param sharedarea.id: instance id
    :param sharedarea.id: instance oid
    :param sharedarea.uuid: instance uuid
    :param sharedarea.objid: instance objid
    :param sharedarea.name: instance name
    :param sharedarea.resource_uuid: instance uuid
    :param sharedarea.resource_params: input params
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()

    # validate input params
    instance_id = params.get(u'id')
    resource_params = params.get(u'resource_params')
    resource_uuid = params.get(u'resource_uuid')
    self.progress(u'Get configuration params')

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.progress(u'Get plugin %s' % plugin)

    # send action to resource
    if resource_uuid is not None:
        res = plugin.action_resource(self, **resource_params)
        self.progress(u'Send action to resource %s' % res)

    # # update configuration
    # plugin.update_status(SrvStatusType.ACTIVE)
    # self.progress(u'Set plugin %s configuration' % plugin)

    return True


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def delete_resource_task(self, options):
    """Delete remote resource

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param dict sharedarea: input params
    :param sharedarea.id: instance id
    :param sharedarea.id: instance oid
    :param sharedarea.uuid: instance uuid
    :param sharedarea.objid: instance objid
    :param sharedarea.name: instance name
    :param sharedarea.resource_uuid: instance uuid
    :param sharedarea.resource_params: input params
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()

    # validate input params
    instance_id = params.get(u'id')
    resource_params = params.get(u'resource_params')
    resource_uuid = params.get(u'resource_uuid')
    self.progress(u'Get configuration params')

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.progress(u'Get plugin %s' % plugin)

    # delete resource
    if resource_uuid is not None:
        res = plugin.delete_resource(self, resource_params)
        self.progress(u'Delete resource %s' % res)

    # update configuration
    plugin.delete_instance()
    self.progress(u'Set plugin %s configuration' % plugin)

    return True
