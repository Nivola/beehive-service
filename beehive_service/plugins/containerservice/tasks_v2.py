# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
from datetime import datetime
from typing import TYPE_CHECKING

from beecell.types.type_dict import dict_get
from beehive.common.task_v2.manager import get_task_manager
from beehive.common.task_v2 import task_step
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.containerservice.controller_namespace import ApiNamespaceInstance
from beehive_service.task_v2.servicetypeplugin import TypePluginInstanceAddTask, TypePluginInstanceDeleteTask, TypePluginInstanceUpdateTask
if TYPE_CHECKING:
    from beehive_service.task_v2.servicetypeplugin import AbstractServiceTypePluginTask

class NamespaceInstanceUpdateTask(TypePluginInstanceUpdateTask):
    name = "container_plugin_inst_update_task"
    entity_class = ApiNamespaceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [NamespaceInstanceUpdateTask.update_resource_step]

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
        print("update_resource_step - custom - params: %s" % params)
        instance_id = params.get("id")
        resource_params = params.get("resource_params")
        resource_uuid = params.get("resource_uuid")

        plugin: ApiNamespaceInstance = task.get_type_plugin(instance_id)
        task.progress(step_id, msg="get plugin %s" % plugin)

        # update resource
        # for namespace instance resource_uuid is None: external service is called
        # if resource_uuid is not None:
        res = plugin.update_resource(task, **resource_params)
        task.progress(step_id, msg="update resource %s" % res)

        # update configuration
        plugin.update_status(SrvStatusType.ACTIVE)
        task.progress(step_id, msg="set plugin %s configuration" % plugin)

        return True, params


class NamespaceInstanceDeleteTask(TypePluginInstanceDeleteTask):
    name = "container_plugin_inst_delete_task"
    entity_class = ApiNamespaceInstance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [NamespaceInstanceDeleteTask.delete_resource_step]

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
        instance_id = params.get("id")
        resource_params = params.get("resource_params")
        resource_uuid = params.get("resource_uuid")
        task.progress(step_id, msg="get configuration params")

        # run action over orchestrator entity
        plugin: ApiNamespaceInstance = task.get_type_plugin(instance_id)
        plugin.post_get()
        task.progress(step_id, msg="get plugin %s" % plugin)

        # delete resource
        # for namespace instance resource_uuid is None: external service is called
        # if resource_uuid is not None:
        res = plugin.delete_resource(task, resource_params)
        task.progress(step_id, msg="delete resource %s" % res)

        # update configuration
        plugin.delete_instance()
        task.progress(step_id, msg="set plugin %s configuration" % plugin)

        return True, params


task_manager = get_task_manager()
task_manager.register_task(NamespaceInstanceUpdateTask())
task_manager.register_task(NamespaceInstanceDeleteTask())
