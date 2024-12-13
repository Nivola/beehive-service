# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.data import operation
from beehive_service.controller import ApiAccount
from beehive_service.controller import ServiceController
from beehive.common.task_v2 import BaseTask
from typing import List, Type, Tuple, Any, Union, Dict, Callable


class ServiceTask(BaseTask):
    abstract = True
    inner_type = "TASK"
    prefix = "celery-task-shared-"
    prefix_stack = "celery-task-stack-"
    expire = 3600
    entity_class = ApiAccount
    controller: ServiceController = None

    @staticmethod
    def has_session():
        return getattr(operation, "session", None) is not None

    def register_callback(self, callback: Callable = None, onfailure: bool = True):
        """Register a callback collable in case of success or failure

        :param callback:  a closure to be called
        :param onfailure: if true call on failure otherwise call on success
        :return:
        """
        if onfailure:
            setattr(self, "CB_ON_FAIL_CLOSURE", callback)
        else:
            setattr(self, "CB_ON_SUCC_CLOSURE", callback)

    def call_callback(
        self,
        task_id: str,
        retval: Any = None,
        exc: Exception = None,
        onfailure: bool = True,
    ):
        """Search for registered callback and execute them

        :param onfailure: if true call an failure  call back otherwise call on success call back
        :return:
        """
        if onfailure:
            callback = getattr(self, "CB_ON_FAIL_CLOSURE", None)
        else:
            callback = getattr(self, "CB_ON_SUCC_CLOSURE", None)
        if callable(callback):
            if not self.has_session():
                self.get_session()
            callback(task=self, task_id=task_id, retval=retval, exc=exc)
            self.release_session()

    # def on_success(self, retval, task_id, args, kwargs):
    #     """Run by the worker if the task executes successfully.
    #
    #     :param retval: The return value of the task.
    #     :param task_id: Unique id of the executed task.
    #     :param args: Original arguments for the executed task.
    #     :param kwargs: Original keyword arguments for the executed task.
    #     :return:
    #     """
    #     super(ServiceTask).on_success(self, retval, task_id, args, kwargs)
    #     self.call_callback(retval=retval, task_id=task_id, onfailure=False)
    #
    # def on_failure(self, exc, task_id, args, kwargs, einfo):
    #     super(ServiceTask).on_failure(self, exc, task_id, args, kwargs, einfo)
    #     self.call_callback(task_id=task_id, exc=exc, onfailure=True)
    #     # self.release_session()
