# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.task_v2 import task_step
from beehive_service.model.base import SrvStatusType
from datetime import datetime


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
