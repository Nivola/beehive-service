# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.task_v2 import task_step
from beehive_service.model.base import SrvStatusType
from datetime import datetime
from logging import getLogger

from beehive_service.plugins.loggingservice.controller import ApiLoggingSpace

logger = getLogger(__name__)

# @task_step()
# def create_space_step(task, step_id, params, *args, **kvargs):
#     """create resource share

#     :param task: parent celery task
#     :param str step_id: step id
#     :param dict params: step params
#     :param params.id: instance id
#     :param params.data: resource data
#     :return: True, params
#     """
#     instance_id = params.pop('id')
#     logger.debug('+++++ create_space_step %s' % (instance_id))
#     data = params.get('data')
#     logger.debug('+++++ create_space_step data {}'.format(data))

#     plugin: ApiLoggingSpace
#     plugin = task.get_type_plugin(instance_id)
#     logger.debug('+++++ create_space_step passo 01')
#     task.progress(step_id, msg='get plugin %s' % plugin)

#     # create share
#     plugin.update_status(SrvStatusType.UPDATING)
#     res = plugin.create_space_resource(task, **data)
#     task.progress(step_id, msg='create space resource %s' % res)

#     # update configuration
#     plugin.update_status(SrvStatusType.ACTIVE)
#     task.progress(step_id, msg='set plugin %s configuration' % plugin)

#     return True, params


# @task_step()
# def delete_mount_target_step(task, step_id, params, *args, **kvargs):
#     """delete resource share

#     :param task: parent celery task
#     :param str step_id: step id
#     :param dict params: step params
#     :param params.id: instance id
#     :param params.data: resource data
#     :return: True, params
#     """
#     instance_id = params.pop('id')
#     data = params.get('data')

#     plugin = task.get_type_plugin(instance_id)
#     task.progress(step_id, msg='get plugin %s' % plugin)

#     # delete share
#     plugin.update_status(SrvStatusType.UPDATING)
#     res = plugin.delete_mount_target_resource(task)
#     task.progress(step_id, msg='Delete share resource %s' % res)

#     # update configuration
#     # plugin.set_config('mount_target_data', None)
#     plugin.update_status(SrvStatusType.ACTIVE)
#     # plugin.instance.update(status=SrvStatusType.ACTIVE, resource_uuid=None)
#     task.progress(step_id, msg='set plugin %s configuration' % plugin)

#     return True, params
