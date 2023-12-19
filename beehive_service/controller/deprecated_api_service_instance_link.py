# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import json

from beecell.db import TransactionError
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import trace
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity import ServiceApiObject
from beecell.simple import jsonDumps


class ApiServiceInstanceLink1(ServiceApiObject):
    """ """

    objdef = ServiceApiObject.join_typedef(ApiAccount.objdef, "ServiceLink")
    objuri = "links"
    objname = "link"
    objdesc = "Service link"

    def __init__(self, *args, **kvargs):
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.start_node = None
        self.end_node = None
        self.type = None
        if self.model is not None:
            self.type = self.model.type

        self.set_attribs()

        self.update_object = self.manager.update_link
        self.delete_object = self.manager.delete_link

    def set_attribs(self):
        """Set attributes

        :param attributes: attributes
        """
        if self.model is not None:
            self.attribs = {}
            if self.model is not None and self.model.attributes is not None:
                try:
                    self.attribs = json.loads(self.model.attributes)
                except Exception as ex:
                    pass

    def small_info(self):
        """Get service small infos.

        :return: Dictionary with system capabilities.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.small_info(self)
        return info

    def info(self):
        """Get service link infos.

        :return: Dictionary with system capabilities.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)

        # get start and end services
        start_service = self.get_start_service()
        end_service = self.get_end_service()

        info["details"] = {
            "attributes": self.attribs,
            "type": self.model.type,
            "start_service": start_service.small_info(),
            "end_service": end_service.small_info(),
        }

        return info

    def detail(self):
        """Get service link details.

        :return: Dictionary with system capabilities.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return self.info()

    def get_start_service(self):
        """ """
        start_service = self.controller.get_service_instance(self.model.start_service_id, authorize=False)
        return start_service

    def get_end_service(self):
        """ """
        end_service = self.controller.get_service_instance(self.model.end_service_id, authorize=False)
        return end_service

    def pre_update(self, **kvargs):
        """Pre change function. Extend this function to manipulate and validate
        input params.


        :param name: link name
        :param ltype: link type
        :param start_service: start service reference id, uuid
        :param end_service: end service reference id, uuid
        :param attributes: link attributes [default={}]

        :return:

            kvargs

        :raise ApiManagerError:
        """
        # get services
        start_service = kvargs.pop("start_service", None)
        if start_service is not None:
            kvargs["start_service_id"] = self.controller.get_service_instance(start_service).oid
        end_service = kvargs.pop("end_service", None)
        if end_service is not None:
            kvargs["end_service_id"] = self.controller.get_service_instance(end_service).oid
        attributes = kvargs.pop("attributes", None)
        if attributes is not None:
            kvargs["attributes"] = jsonDumps(attributes)

        return kvargs

    # tags
    #
    @trace(op="tag-assign.update")
    def add_tag(self, value):
        """Add tag

        :param value: str tag value
        :param authorize: if True check authorization
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions("update")

        # get tag
        tag = self.controller.get_tag(value)

        try:
            res = self.manager.add_link_tag(self.model, tag.model)
            self.logger.info("Add tag %s to link %s: %s" % (value, self.name, res))
            return res
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)

    @trace(op="tag-deassign.update")
    def remove_tag(self, value):
        """Remove tag

        :param value: str tag value
        :param authorize: if True check authorization
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions("update")

        # get tag
        tag = self.controller.get_tag(value)

        try:
            res = self.manager.remove_link_tag(self.model, tag.model)
            self.logger.info("Remove tag %s from link %s: %s" % (value, self.name, res))
            return res
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)
