# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import ApiObject
from beehive_service.entity import ServiceApiObject


class ApiServiceJob(ServiceApiObject):
    objdef = "ServiceJob"
    objuri = "servicejob"
    objname = "servicejob"
    objdesc = "servicejob"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.job = None
        self.params = None
        self.account_id = None

        if self.model is not None:
            self.job = self.model.job
            self.params = self.model.params
            self.account_id = self.model.account_id
            self.task_id = self.model.task_id
            self.last_error = self.model.last_error
            self.status = self.model.status
        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_job
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "job": str(self.job),
                "account_id": str(self.account_id),
                "params": self.params,
                "task_id": self.task_id,
                "last_error": self.last_error,
                "status": self.status,
            }
        )
        return info

    def detail(self):
        """Get object extended info"""
        info = self.info()
        return info

    def update(self, status, last_error=None, authorize=True):
        """Update status of service_job api instance.

        :param task_id: task id
        :return: ApiServiceJob
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return ApiObject.update(status=status, last_error=last_error)
