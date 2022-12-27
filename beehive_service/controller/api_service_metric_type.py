# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive_service.entity import ServiceApiObject


class ApiServiceMetricType(ServiceApiObject):
    objdef = 'ServiceMetricType'
    objuri = 'servicemetrictype'
    objname = 'servicemetrictype'
    objdesc = 'servicemetrictype'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.group_name = None
        self.metric_type = None
        self.measure_unit = None
        self.status = None
        self.limits = None

        if self.model is not None:
            self.group_name = self.model.group_name
            self.metric_type = self.model.metric_type
            self.measure_unit = self.model.measure_unit
            self.status = self.model.status
            self.limits = self.model.limits
        # child classes
        self.child_classes = []
        self.update_object = self.manager.update_service_metric_type
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'group_name': self.group_name,
            'metric_type': self.metric_type,
            'measure_unit': self.measure_unit,
            'status': self.status,
            'limits': self.limits
            })
        return info

    def detail(self):
        """Get object extended info
        """
        info = self.info()
        return info