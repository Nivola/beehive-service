# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
from beehive.common.task_v2.manager import task_manager
from beehive.common.task_v2 import task_step
from beehive_service.model.base import SrvStatusType
from datetime import datetime

from beehive_service.task_v2.servicetypeplugin import TypePluginInstanceAddTask
from beehive_service.plugins.storageservice.controller import ApiStorageEFS


class EfsInstanceAddTask(TypePluginInstanceAddTask):
    name = "efs_add_inst_task"
    entity_class = ApiStorageEFS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [EfsInstanceAddTask.create_volume_step]

    @staticmethod
    @task_step()
    def create_volume_step(task, step_id, params, *args, **kvargs):
        """
        create volume. only for the new ontap api.
        same as default service inst create task
        but with conditional creation based on stass type
        """
        instance_id = params.pop("id")
        resource_params = params.get("resource_params")

        plugin = task.get_type_plugin(instance_id)

        if resource_params is None:
            task.progress(msg="Detected legacy staas type. Will not create resource now.")
        else:
            # create resource
            res = plugin.create_resource(task, resource_params)
            task.progress(step_id, msg="create resource %s" % res)

        # update configuration
        plugin.update_status(SrvStatusType.ACTIVE)
        task.progress(step_id, msg="set plugin %s configuration" % plugin)

        return True, params


task_manager.tasks.register(EfsInstanceAddTask())


@task_step()
def create_mount_target_step(task, step_id, params, *args, **kvargs):
    """create resource share

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.pop("id")
    data = params.get("data")

    plugin = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="get plugin %s" % plugin)

    # create share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.create_mount_target_resource(task, **data)
    task.progress(step_id, msg="create share resource %s" % res)

    # update configuration
    # plugin.set_config('mount_target_data.network', network)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg="set plugin %s configuration" % plugin)

    return True, params


@task_step()
def delete_mount_target_step(task, step_id, params, *args, **kvargs):
    """delete resource share

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.pop("id")
    data = params.get("data")

    plugin = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="get plugin %s" % plugin)

    # delete share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_mount_target_resource(task)
    task.progress(step_id, msg="Delete share resource %s" % res)

    # update configuration
    # plugin.set_config('mount_target_data', None)
    plugin.update_status(SrvStatusType.ACTIVE)
    # plugin.instance.update(status=SrvStatusType.ACTIVE, resource_uuid=None)
    task.progress(step_id, msg="set plugin %s configuration" % plugin)

    return True, params


@task_step()
def create_mount_target_grant_step(task, step_id, params, *args, **kvargs):
    """create resource share grant

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.pop("id")
    data = params.get("data")

    plugin = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="get plugin %s" % plugin)

    # do grant operation
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.do_file_system_grant_op(task=task, **data)
    task.progress(step_id, msg="create share resource %s" % res)

    # update configuration
    # plugin.set_config('mount_target_data', None)
    plugin.update_status(SrvStatusType.ACTIVE)
    # plugin.instance.update(status=SrvStatusType.ACTIVE, resource_uuid=None)
    task.progress(step_id, msg="set plugin %s configuration" % plugin)

    return True, params


@task_step()
def delete_mount_grants_step(task, step_id, params, *args, **kvargs):
    """delete resource share

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.get("id")
    grants = params.get("data").get("grants", [])

    plugin = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="delete share %s grants " % instance_id)

    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_mount_grants(task, grants)
    task.progress(step_id, msg="Delete Share Grants %s" % res)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg="set plugin %s configuration" % plugin)

    return True, params


@task_step()
def delete_mount_targets_step(task, step_id, params, *args, **kvargs):
    """delete resource share

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.get("id")
    mountTargets = params.get("data").get("mountTargets", [])

    plugin = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="delete share %s mount targets " % instance_id)

    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_share_mount_targets(task, mountTargets)
    task.progress(step_id, msg="Delete Share Mount Targets resource %s" % res)
    # plugin.update_status(SrvStatusType.DELETED)
    plugin.instance.update(status=SrvStatusType.DELETED, expiry_date=datetime.today())
    task.progress(step_id, msg="set plugin %s configuration" % plugin)

    return True, params
