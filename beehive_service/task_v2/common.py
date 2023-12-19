# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from celery.utils.log import get_task_logger

logger = get_task_logger("beehive_service.tasks")

MAX_CONCURRENT_TASKS_CELERY = 3


#
# resource task
#
class ServiceTaskException(Exception):
    pass
