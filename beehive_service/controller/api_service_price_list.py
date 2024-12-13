# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import ApiManagerWarning
from beehive_service.controller.api_service_price_metric import ApiServicePriceMetric
from beehive_service.entity import ServiceApiObject


class ApiServicePriceList(ServiceApiObject):
    objdef = "ServicePriceList"
    objuri = "servicepricelist"
    objname = "servicepricelist"
    objdesc = "servicepricelist"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.flag_default = None

        if self.model is not None:
            self.flag_default = self.model.flag_default

        # child classes
        self.child_classes = [ApiServicePriceMetric]

        self.update_object = self.manager.update_service_price_list
        self.delete_object = self.manager.delete
        self.expunge_object = self.manager.purge

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({"flag_default": self.flag_default})
        return info

    def detail(self):
        """Get object extended info"""
        info = self.info()
        return info

    def is_used(self):
        num_instance = self.manager.get_account_prices_by_pricelist(self.oid)
        if num_instance is not None and len(num_instance) > 0:
            num_instance = self.manager.get_division_prices_by_pricelist(self.oid)
        return num_instance is not None and len(num_instance) > 0

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.


        :param args: custom params
        :param kvargs: custom params

        :return:

            kvargs

        :raise ApiManagerError:
        """
        # check there are active metrics prices
        if len(self.model.metrics_prices.all()) > 0:
            msg = "Price list %s has child metrics prices. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)

        return kvargs

    def pre_expunge(self, *args, **kvargs):
        """Pre expunge function. This function is used in expunge method. Extend this function to manipulate and
        validate expunge input params.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        if len(self.model.metrics_prices.all()) > 0:
            msg = "Price list %s has child metrics prices. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)

        return kvargs
