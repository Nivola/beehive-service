# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import json
from typing import List

from beehive_service.entity import ServiceApiObject
from beehive_service.model.account_capability import AccountCapability


class ApiAccountCapability(ServiceApiObject):
    objdef = "AccountCapability"
    objuri = "capabilities"
    objname = "accountcapabilities"
    objdesc = "accountcapabilities"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.update_object = self.manager.update_capability
        self.delete_object = self.manager.delete
        self.model: AccountCapability

    def __repr__(self):
        return "<%s id=%s objid=%s name=%s>" % (
            "ApiAccountCapability",
            self.oid,
            self.objid,
            self.name,
        )

    # @property
    # def name(self):
    #     """
    #     name getter
    #     :return: str
    #     """
    #     if self.model is not None:
    #         return getattr(self.model, 'name', None)
    #     else:
    #         return None

    @property
    def status(self):
        """
        status getter
        :return:
        """
        if self.model is not None:
            return getattr(self.model, "status")
        else:
            return None

    def get_params(self):
        """params getter

        :return: dict
        """
        if self.model is not None:
            params = getattr(self.model, "params")
            return json.loads(params)
        else:
            return None

    @property
    def version(self):
        """
        params getter
        :return: dict
        """
        if self.model is not None:
            return getattr(self.model, "version")
        else:
            return None

    @property
    def plugin_name(self):
        """
        params getter
        :return: dict
        """
        if self.model is not None:
            return getattr(self.model, "plugin_name", None)
        else:
            return None

    # @property
    # def default_service_types(self):
    #     if self.model is not None:
    #         return getattr(self.model, 'params', {}).get('default_service_types',{})
    #     else:
    #         return None

    @property
    def services(self) -> List[dict]:
        params = self.get_params()
        if params is not None:
            return params.get("services", [])
        else:
            return None

    @property
    def definitions(self) -> List[str]:
        params = self.get_params()
        if params is not None:
            return params.get("definitions", [])
        else:
            return None

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "name": self.name,
                "status": self.status,
                # 'plugin_name': self.plugin_name,
                "version": self.version,
                "params": self.get_params(),
            }
        )
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info
