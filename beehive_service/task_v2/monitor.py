# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from .servicetask import ServiceTask
from beehive_service.controller import ServiceController, ApiAccount
from beehive_service.model import ServiceJob, Account, ServiceInstance
from beehive_service.entity.service_type import ApiServiceTypeContainer
from beehive.common.task.job import task_local
from beehive_service.controller import ApiServiceType
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive.common.task_v2 import task_step
from beehive.common.task_v2.manager import task_manager
from datetime import datetime, timedelta, date
from beecell.simple import id_gen
from beehive_service.model import ServiceMetric, SrvStatusType, ServiceMetricType
from beehive_service.service_util import ServiceUtil
from typing import List, Type, Tuple, Any, Union, Dict


#
# Metrics And Consumes Tasks
#
class AcquisitionMonitorTask(ServiceTask):
    entity_class = ApiAccount
    name = "acquisition_monitor_task"
    inner_type = "TASK"
    prefix = "celery-task-shared-"
    prefix_stack = "celery-task-stack-"
    expire = 3600
    controller: ServiceController = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.steps = [
            AcquisitionMonitorTask.step_monitoring,
        ]

    @staticmethod
    def step_monitoring(task: ServiceTask, step_id: str, params: dict, *args, **kvargs):
        """
        richiama fnzioni di monitoraggio interno della acquisizione metriche della cmp

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """

        task.logger.debug("step_monitoring")
        controller: ServiceController = task.controller

        controller.add_job(task.request.id, "step_monitoring", params)
        msg, recipients = controller.compute_monitoring_message()
        # recipients ="abcd@def.gh"
        if msg is not None and recipients is not None:
            # send email
            if controller.api_manager.mailer:
                controller.api_manager.mailer.send(
                    controller.api_manager.mail_sender,
                    recipients,
                    "Nivola Cmp Monitor",
                    msg,
                    msg,
                )
            pass
        return True, params


task_manager.tasks.register(AcquisitionMonitorTask())
