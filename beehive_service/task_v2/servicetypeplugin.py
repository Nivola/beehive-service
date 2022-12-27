# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiManagerError
from beehive.common.task_v2 import task_step, run_sync_task
from beehive.common.task_v2.manager import task_manager
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.model import SrvStatusType
from beehive_service.task_v2 import ServiceTask
import logging

logger = logging.getLogger(__name__)


class AccountDeleteTask(ServiceTask):
    """AccountDeleteTask task
    """
    name = 'account_delete_task'
    entity_class = ApiServiceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = []

    def get_account(self, account_id):
        """get account

        :param account_id: account id
        :return: account instance
        :raises ApiManagerError: if query empty return error.
        """
        account = self.controller.get_account(account_id)
        return account

    @staticmethod
    @task_step()
    def delete_services_step(task, step_id, params, *args, **kvargs):
        """Delete account services

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.account_id: account id
        :return: account_id, params
        """
        account_id = params.get('account')
        account = task.get_account(account_id)

        task.progress(step_id, msg='delete all account %s services - START' % account_id)
        service_idx = account.get_service_index()

        def loop_childs(service):
            plugin = service['plugin']
            task.progress(step_id, msg='delete service %s - START' % plugin.instance.name)
            for child_id in service['childs']:
                loop_childs(service_idx.get(child_id))
            # delete service
            plugin.delete(sync=True)
            prepared_task = plugin.active_task
            if prepared_task is not None and prepared_task != {}:
                run_sync_task(prepared_task, task, step_id)
            task.progress(step_id, msg='delete service %s - STOP' % plugin.instance.name)

        for k, v in service_idx.items():
            if v['core'] is True:
                loop_childs(v)

        task.progress(step_id, msg='delete all account %s services - STOP' % account_id)

        return account_id, params

    @staticmethod
    @task_step()
    def delete_tags_step(task, step_id, params, *args, **kvargs):
        """Delete account tags

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.account_id: account id
        :return: account_id, params
        """
        account_id = params.get('account')
        account = task.get_account(account_id)

        #account.delete_object(account.model)
        #task.progress(step_id, msg='soft delete account %s' % account_id)

        return account_id, params

    @staticmethod
    @task_step()
    def delete_account_step(task, step_id, params, *args, **kvargs):
        """Delete account

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.account_id: account id
        :return: account_id, params
        """
        account_id = params.get('account')
        account = task.get_account(account_id)

        account.delete_object(account.model)
        account.update_status(6)
        task.progress(step_id, msg='soft delete account %s' % account_id)

        return account_id, params


class AbstractServiceTypePluginTask(ServiceTask):
    """AbstractServiceTypePlugin task
    """
    name = 'service_type_plugin_task'
    entity_class = ApiServiceInstance

    def get_type_plugin(self, instance, plugin_class=None, details=False):
        """get type plugin instance.

        :param instance: service instance oid
        :param plugin_class: service type plugin class [optional]
        :param details: if False does not get entity details [default=False]
        :return: service type plugin instance
        :raises ApiManagerError: if query empty return error.
        """
        plugin = self.controller.get_service_type_plugin(instance, plugin_class=plugin_class, details=details)
        return plugin

    def failure(self, params, error):
        # get service
        try:
            plugin = self.get_type_plugin(params.get('id'), details=False)

            # update resource state
            plugin.update_status(SrvStatusType.ERROR, error=error)
        except ApiManagerError as ex:
            if ex.code == 404:
                self.logger.warning(ex)
            else:
                raise

    @staticmethod
    @task_step()
    def create_resource_step(task, step_id, params, *args, **kvargs):
        """Create remote resource

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.id: instance id
        :param params.uuid: instance uuid
        :param params.objid: instance objid
        :param params.name: name
        :param params.desc: desc
        :param params.attribute: None
        :param params.tags: None
        :param params.resource_params: input params
        :return: True, params, params
        """
        # validate input params
        instance_id = params.get('id')
        resource_params = params.get('resource_params')

        plugin = task.get_type_plugin(instance_id)

        # create resource
        res = plugin.create_resource(task, resource_params)
        task.progress(step_id, msg='create resource %s' % res)

        # update configuration
        plugin.update_status(SrvStatusType.ACTIVE)
        task.progress(step_id, msg='set plugin %s configuration' % plugin)

        return True, params

    @staticmethod
    @task_step()
    def update_resource_step(task, step_id, params, *args, **kvargs):
        """Update remote resource

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.id: instance id
        :param params.uuid: instance uuid
        :param params.objid: instance objid
        :param params.name: instance name
        :param params.resource_uuid: instance uuid
        :param params.resource_params: input params
        :return: True, params
        """
        instance_id = params.get('id')
        resource_params = params.get('resource_params')
        resource_uuid = params.get('resource_uuid')

        plugin = task.get_type_plugin(instance_id)
        task.progress(step_id, msg='get plugin %s' % plugin)

        # update resource
        if resource_uuid is not None:
            res = plugin.update_resource(task, **resource_params)
            task.progress(step_id, msg='update resource %s' % res)

        # update configuration
        plugin.update_status(SrvStatusType.ACTIVE)
        task.progress(step_id, msg='set plugin %s configuration' % plugin)

        return True, params

    @staticmethod
    @task_step()
    def patch_resource_step(task, step_id, params, *args, **kvargs):
        """Patch remote resource

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.id: instance id
        :param params.id: instance oid
        :param params.uuid: instance uuid
        :param params.objid: instance objid
        :param params.name: instance name
        :param params.resource_uuid: instance uuid
        :param params.resource_params: input params
        :return: True, params
        """
        instance_id = params.get('id')
        resource_params = params.get('resource_params')
        resource_uuid = params.get('resource_uuid')

        plugin = task.get_type_plugin(instance_id)
        task.progress(step_id, msg='get plugin %s' % plugin)

        # update resource
        if resource_uuid is not None:
            res = plugin.patch_resource(task, **resource_params)
            task.progress(step_id, msg='Patch resource %s' % res)

        # update configuration
        plugin.update_status(SrvStatusType.ACTIVE)
        task.progress(step_id, msg='set plugin %s configuration' % plugin)

        return True, params

    @staticmethod
    @task_step()
    def action_resource_step(task, step_id, params, *args, **kvargs):
        """Send action remote resource

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.id: instance id
        :param params.id: instance oid
        :param params.uuid: instance uuid
        :param params.objid: instance objid
        :param params.name: instance name
        :param params.resource_uuid: instance uuid
        :param params.resource_params: input params
        :return: True, params
        """
        instance_id = params.get('id')
        resource_params = params.get('resource_params')
        resource_uuid = params.get('resource_uuid')

        plugin = task.get_type_plugin(instance_id)
        task.progress(step_id, msg='get plugin %s' % plugin)

        # send action to resource
        if resource_uuid is not None:
            res = plugin.action_resource(task, **resource_params)
            task.progress(step_id, msg='Send action to resource %s' % res)

        # # update configuration
        # plugin.update_status(SrvStatusType.ACTIVE)
        # task.progress(step_id, msg='set plugin %s configuration' % plugin)

        return True, params

    @staticmethod
    @task_step()
    def delete_resource_step(task, step_id, params, *args, **kvargs):
        """Delete remote resource

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :param params.id: instance id
        :param params.uuid: instance uuid
        :param params.objid: instance objid
        :param params.name: instance name
        :param params.resource_uuid: instance uuid
        :param params.resource_params: input params
        :return: True, params
        """
        instance_id = params.get('id')
        resource_params = params.get('resource_params')
        resource_uuid = params.get('resource_uuid')
        task.progress(step_id, msg='get configuration params')

        # run action over orchestrator entity
        plugin = task.get_type_plugin(instance_id)
        plugin.post_get()
        task.progress(step_id, msg='get plugin %s' % plugin)

        # delete resource
        if resource_uuid is not None:
            res = plugin.delete_resource(task, resource_params)
            task.progress(step_id, msg='delete resource %s' % res)

        # update configuration
        plugin.delete_instance()
        task.progress(step_id, msg='set plugin %s configuration' % plugin)

        return True, params


class TypePluginInstanceAddTask(AbstractServiceTypePluginTask):
    """TypePluginInstanceAdd task

    :param cid: container id
    :param id: resource id
    :param uuid: return resource id, params
    :param objid: resource objid
    :param name: resource name
    :param desc: resource desc
    :param parent: resource parent
    :param ext_id: physical id
    :param active: active
    :param attribute: attribute
    :param tags: list of tags to add
    """
    abstract = False
    name = 'service_type_plugin_inst_task'
    entity_class = ApiServiceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            TypePluginInstanceAddTask.create_resource_step
        ]


class TypePluginInstanceUpdateTask(AbstractServiceTypePluginTask):
    """TypePluginInstanceUpdate task

    :param cid: container id
    :param id: resource id
    :param uuid: return resource id, params
    :param objid: resource objid
    :param ext_id: physical id
    """
    abstract = False
    name = 'service_type_plugin_inst_update_task'
    entity_class = ApiServiceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            TypePluginInstanceUpdateTask.update_resource_step
        ]


class TypePluginInstancePatchTask(AbstractServiceTypePluginTask):
    """TypePluginInstancePatch task

    :param cid: container id
    :param id: resource id
    :param uuid: return resource id, params
    :param objid: resource objid
    :param ext_id: physical id
    """
    abstract = False
    name = 'service_type_plugin_inst_patch_task'
    entity_class = ApiServiceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            TypePluginInstancePatchTask.patch_resource_step
        ]


class TypePluginInstanceDeleteTask(AbstractServiceTypePluginTask):
    """TypePluginInstanceDelete task

    :param cid: container id
    :param id: resource id
    :param uuid: return resource id, params
    :param objid: resource objid
    """
    abstract = False
    name = 'service_type_plugin_inst_delete_task'
    entity_class = ApiServiceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            TypePluginInstanceDeleteTask.delete_resource_step
        ]


class TypePluginInstanceActionTask(AbstractServiceTypePluginTask):
    """TypePluginInstanceAction task
    """
    abstract = False
    name = 'service_type_plugin_inst_action_task'
    entity_class = ApiServiceInstance


task_manager.tasks.register(AccountDeleteTask())
task_manager.tasks.register(TypePluginInstanceAddTask())
task_manager.tasks.register(TypePluginInstanceUpdateTask())
task_manager.tasks.register(TypePluginInstancePatchTask())
task_manager.tasks.register(TypePluginInstanceDeleteTask())
task_manager.tasks.register(TypePluginInstanceActionTask())
