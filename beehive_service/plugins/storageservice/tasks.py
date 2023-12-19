# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

# TODO Deorecated
# TODO delete this file
from beehive.common.task.job import job_task
from beehive.common.task.manager import task_manager
from beehive_service.model.base import SrvStatusType
from beehive_service.task.servicetypeplugin import ServiceTypePluginJobTask


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def create_mount_target_task(self, options):
    """Send action to physical server.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :dict sharedarea: input params
    :sharedarea:
        * **id**: instance id
        * **share_proto**: share protocol
        * **network**:
        * **network.availability_zone**: site where create share
        * **network.subnet**: subnet cidr
        * **network.vpc**: vpc id
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()
    data = params.get("data")

    # validate input params
    instance_id = params.pop("id")
    network = params.get("network")
    self.update("PROGRESS", msg="Get configuration params")

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.update("PROGRESS", msg="Get plugin %s" % plugin)

    # create share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.create_mount_target_resource(self, **data)
    self.update("PROGRESS", msg="Create share resource %s" % res)

    # update configuration
    # plugin.set_config(u'mount_target_data.network', network)
    plugin.update_status(SrvStatusType.ACTIVE)
    self.update("PROGRESS", msg="Set plugin %s configuration" % plugin)

    return res


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def delete_mount_target_task(self, options):
    """Send action to physical server.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :dict sharedarea: input params
    :sharedarea:
        * **id**: instance id
        * **share_proto**: share protocol
        * **network**:
        * **network.availability_zone**: site where create share
        * **network.subnet**: subnet cidr
        * **network.vpc**: vpc id
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()
    data = params.get("data")

    # validate input params
    instance_id = params.pop("id")
    self.update("PROGRESS", msg="Get configuration params")

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.update("PROGRESS", msg="Get plugin %s" % plugin)

    # delete share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.delete_mount_target_resource(self)
    self.update("PROGRESS", msg="Create share resource %s" % res)

    # update configuration
    # plugin.set_config(u'mount_target_data', None)
    plugin.update_status(SrvStatusType.ACTIVE)
    # plugin.instance.update(status=SrvStatusType.ACTIVE, resource_uuid=None)
    self.update("PROGRESS", msg="Set plugin %s configuration" % plugin)

    return res


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def mount_grant_operation_task(self, options):
    """Send action to physical server.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :dict sharedarea: input params
    :sharedarea:
        * **id**: instance id
        * **share_proto**: share protocol
        * **network**:
        * **network.availability_zone**: site where create share
        * **network.subnet**: subnet cidr
        * **network.vpc**: vpc id
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()
    data = params.get("data")

    # validate input params
    instance_id = params.pop("id")
    self.update("PROGRESS", msg="Get configuration params")

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.update("PROGRESS", msg="Get plugin %s" % plugin)

    # do grant operation
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.do_file_system_grant_op(task=self, **data)
    self.update("PROGRESS", msg="Create share resource %s" % res)

    # update configuration
    # plugin.set_config(u'mount_target_data', None)
    plugin.update_status(SrvStatusType.ACTIVE)
    # plugin.instance.update(status=SrvStatusType.ACTIVE, resource_uuid=None)
    self.update("PROGRESS", msg="Set plugin %s configuration" % plugin)

    return res


@task_manager.task(bind=True, base=ServiceTypePluginJobTask)
@job_task()
def update_efs_resource(self, options):
    """Update share .

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :dict sharedarea: input params
    :sharedarea:
        * **id**: instance id
        * **share_proto**: share protocol
        * **network**:
        * **network.availability_zone**: site where create share
        * **network.subnet**: subnet cidr
        * **network.vpc**: vpc id
    :return: True
    """
    self.set_operation()
    params = self.get_shared_data()
    data = params.get("data")

    # validate input params
    instance_id = params.pop("id")
    self.update("PROGRESS", msg="Get configuration params")

    # run action over orchestrator entity
    self.get_session()
    plugin = self.get_type_plugin(instance_id)
    self.update("PROGRESS", msg="Get plugin %s" % plugin)

    # create share
    plugin.update_status(SrvStatusType.UPDATING)
    res = plugin.ucreate_mount_target_resource(**data)
    self.update("PROGRESS", msg="Create share resource %s" % res)

    # update configuration
    # plugin.set_config(u'mount_target_data.network', network)
    plugin.update_status(SrvStatusType.ACTIVE)
    self.update("PROGRESS", msg="Set plugin %s configuration" % plugin)

    return res
