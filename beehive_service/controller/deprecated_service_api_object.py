# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beecell.simple import import_class
from beehive.common.apimanager import ApiObject, ApiManagerWarning
from beehive.common.assert_util import AssertUtil
from beehive_service.dao.ServiceDao import ServiceDbManager
from beehive_service.model.base import SrvStatusType
from beehive_service.service_util import ServiceUtil


class ServiceApiObject1(ApiObject):
    module = "ServiceModule"
    objtype = "service"

    manager = ServiceDbManager()

    def __init__(self, *args, **kvargs):
        """ """
        ApiObject.__init__(self, *args, **kvargs)

    @property
    def version(self):
        """
        version getter
        :return:
        """
        if self.model is not None:
            return getattr(self.model, "version", "1.0")
        else:
            return None

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiObject.info(self)
        info.update({"version": self.version})
        return info

    def instancePlugin(self, oid, inst=None):
        """Get ServiceType Plugin

        :DEPRECATED:
        :return: Plugin instance  object info.
        :rtype: plugin
        :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        if inst is not None:
            instance = inst
        else:
            AssertUtil.assert_is_not_none(oid)
            instance = self.controller.get_service_instance(oid)

        AssertUtil.assert_is_not_none(instance)
        servicetype = instance.model.service_definition.service_type
        plugin = None
        try:
            self.logger.debug("Tento la creazione del Plugin %s" % servicetype.objclass)
            serviceTypePlugin = import_class(servicetype.objclass)
            self.logger.debug("Instanziato il Plugin %s" % serviceTypePlugin)
            plugin = ServiceUtil.instanceApi(self.controller, serviceTypePlugin, servicetype)

        except Exception:
            self.logger.error("", exc_info=True)
            raise ApiManagerWarning(
                'Plugin class "%s" not found  for SericeType [%s ]' % (servicetype.objclass, repr(servicetype))
            )

        return plugin

    def update_status(self, status):
        if self.update_object is not None:
            # name non definita self.update_object(oid=self.oid, status=status, name=name)
            self.update_object(oid=self.oid, status=status)
            self.logger.debug("Update status of %s to %s" % (self.uuid, status))

    def is_active(self):
        """Check if object has status ACTIVE

        :return: True if active
        """
        res = False
        service_status_id = getattr(self.model, "service_status_id", None)
        status = getattr(self.model, "status", None)

        # status for Account, Org and Div
        if service_status_id is not None and (service_status_id == 1 or service_status_id == 14):
            res = True
        # status for Service**
        if status is not None and status == SrvStatusType.ACTIVE:
            res = True

        return res
