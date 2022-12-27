# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

# from beehive_service.controller.api_service_price_list import ApiServicePriceList
from beehive_service.entity import ServiceApiObject


class ApiServicePriceMetric(ServiceApiObject):
    objdef = 'ServicePriceList.ServicePriceMetric'
    objuri = 'servicepricemetric'
    objname = 'servicepricemetric'
    objdesc = 'servicepricemetric'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.price = None
        self.metric_type_id = None
        self.price_list_id = None
        self.time_unit = None
        self.metric_type = None
        self.price_list = None
        self.price_type = None
        # self.params = None

        if self.model is not None:
            self.price = self.model.price
            self.metric_type_id = self.model.metric_type_id
            self.price_list_id = self.model.price_list_id
            self.time_unit = self.model.time_unit
            self.price_type = self.model.price_type
            # self.params = self.model.params

        # child classes
        self.child_classes = []
        self.update_object = self.manager.update_service_price_metric
        self.delete_object = self.manager.delete
        self.expunge_object = self.manager.purge_service_price_metric

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'price': self.price,
            'metric_type_id': str(self.metric_type_id),
            'price_list_id': str(self.price_list_id),
            'time_unit': self.time_unit
        })

        if self.metric_type is not None:
            info['metric_type_id'] = self.metric_type.uuid
            info['metric_type_name'] = self.metric_type.name
        if self.price_list is not None:
            info['price_list_id'] = self.price_list.uuid
            info['price_list_name'] = self.price_list.name
        return info

    def detail(self):
        """Get object extended info
        """
        info = self.info()
        return info