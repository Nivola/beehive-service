# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
from datetime import datetime
from typing import TYPE_CHECKING

from beecell.types.type_dict import dict_get
from beehive.common.task_v2.manager import get_task_manager
from beehive.common.task_v2 import task_step
from beehive_service.model.base import SrvStatusType
from beehive_service.task_v2.servicetypeplugin import TypePluginInstanceAddTask
from beehive_service.plugins.storageservice.controller import ApiStorageEFS
if TYPE_CHECKING:
    from beehive_service.task_v2.servicetypeplugin import AbstractServiceTypePluginTask

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


get_task_manager().register_task(EfsInstanceAddTask())


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
def delete_mount_target_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """delete resource share

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.pop("id")

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))

    # delete share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_mount_target_resource(task)
    task.progress(step_id, msg="Deleted share resource %s" % res)
    plugin.update_status(SrvStatusType.ACTIVE)

    return True, params


@task_step()
def manage_mount_target_grant_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """manage resource share grant

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.get("id")
    grant = params.get("data").get("grant", {})
    action = params.get("data").get("action")

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))

    # run operation
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.manage_mount_target_grant_resource(task, grant, action)
    task.progress(step_id, msg="manage mount target grant: res=%s" % res)

    # update configuration
    plugin.update_status(SrvStatusType.ACTIVE)

    return True, params


@task_step()
def delete_mount_targets_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
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

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="delete share %s mount targets " % instance_id)

    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_share_mount_targets(task, mountTargets)
    task.progress(step_id, msg="Delete Share Mount Targets resource %s" % res)
    plugin.instance.update(status=SrvStatusType.DELETED, expiry_date=datetime.today())

    return True, params

@task_step()
def manage_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kwargs):
    """execute an operation on a efs instance of any type

    :param task: parent celery task
    :type task: AbstractServiceTypePluginTask
    :param step_id: step id
    :type step_id: str
    :param params: step parameters
    :type params: Dict
    :return: True, params
    """
    instance_id = params.get("id")
    data = params.get("data")

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))

    # execute operation
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.manage_resource(task=task, **data)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg="manage resource: res=%s" % res)
    return True, params

@task_step()
def manage_replica_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """execute an operation (unlink, suspend, resume, ...) on a snapmirror efs instance

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.get("id")
    data = params.get("data")

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))

    # execute operation
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.manage_replica_resource(task=task, **data)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg="manage replica: res=%s" % res)

    return True, params

@task_step()
def rename_service_instance_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """rename service instance

    :param task: parent celery task
    :param str step_id: step id
    :param dict params: step params
    :param params.id: instance id
    :param params.data: resource data
    :return: True, params
    """
    instance_id = params.get("id")
    new_name = params.get("data", {}).get("new_name")

    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))

    # rename service instance
    plugin.update_status(SrvStatusType.UPDATING)
    plugin.update_name(new_name)
    plugin.unset_config("share_data.SourceId")
    plugin.set_config("share_data.CreationToken", new_name)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg=f"rename service instance {instance_id}")

    return True, params

@task_step()
def update_rpo_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """Update rpo value in service instance config

    :param task:
    :param step_id:
    :param params:
    :param args:
    :param kvargs:
    :return:
    """
    instance_id = params.get("id")
    new_rpo = params.get("data", {}).get("rpo")
    _update_share_data_step(task, step_id, instance_id, "share_data.Rpo", new_rpo)
    return True, params


@task_step()
def update_compliance_step(task: 'AbstractServiceTypePluginTask', step_id, params, *args, **kvargs):
    """Update compliance and rpo values in service instance config

    :param task:
    :param step_id:
    :param params:
    :param args:
    :param kvargs:
    :return:
    """
    instance_id = params.get("id")
    compliance = dict_get(params, "data.subaction_params.compliance")
    rpo = dict_get(params, "data.subaction_params.rpo")
    _update_share_data_step(task, step_id, instance_id, "share_data.ComplianceMode", compliance)
    _update_share_data_step(task, step_id, instance_id, "share_data.Rpo", rpo)
    if not compliance:
        _unset_share_data_step(task, step_id, instance_id, "share_data.Rpo")
    return True, params

def _update_share_data_step(task: 'AbstractServiceTypePluginTask', step_id, instance_id, key, value, *args, **kvargs):
    """Update share data param value in service instance config

    :param task:
    :param step_id:
    :param params:
    :param args:
    :param kvargs:
    :return:
    """
    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))
    # update service instance config
    plugin.update_status(SrvStatusType.UPDATING)
    plugin.set_config(key, value)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg=f"update service instance config: {instance_id}")

def _unset_share_data_step(task: 'AbstractServiceTypePluginTask', step_id, instance_id, key, *args, **kwargs):
    plugin: 'ApiStorageEFS' = task.get_type_plugin(instance_id)
    task.progress(step_id, msg="got ApiStorageEFS plugin with oid %s: %s" % (instance_id, plugin))
    plugin.update_status(SrvStatusType.UPDATING)
    plugin.unset_config(key)
    plugin.update_status(SrvStatusType.ACTIVE)
    task.progress(step_id, msg=f"update service instance config {instance_id} - unset key {key}")
