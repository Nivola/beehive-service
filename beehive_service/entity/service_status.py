# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import TYPE_CHECKING
from beehive_service.entity import ServiceApiObject
if TYPE_CHECKING:
    from beehive_service.model import ServiceStatus as ModelServiceStatus

class ApiServiceStatus(ServiceApiObject):
# class ApiServiceStatus(object):
    objdef = "ServiceStatus"
    objuri = "servicestatus"
    objname = "servicestatus"
    objdesc = "ServiceStatus"

    model: 'ModelServiceStatus'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.objclass = None

        if self.model is not None:
            self.objclass = self.model.objclass

        # child classes
        self.child_classes = [
        ]

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = {
            # "__meta__": {
            #     "objid": self.objid,
            #     "type": self.objtype,
            #     "definition": self.objdef,
            #     "uri": self.objuri,
            # },
            "id": self.oid,
            # "uuid": self.uuid,
            "name": self.name,
            "desc": self.desc,
        }
        # info = ServiceApiObject.info(self)
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info
