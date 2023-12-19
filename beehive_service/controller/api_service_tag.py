# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.apimanager import ApiObject

# from beehive_service.controller.ApiAccount import ApiAccount
from beehive_service.entity import ServiceApiObject


class ApiServiceTag(ServiceApiObject):
    """Service tag"""

    objdef = ApiObject.join_typedef("Organization.Division.Account", "ServiceTag")
    objuri = "tag"
    objname = "tag"
    objdesc = "Service Tag"

    def __init__(self, *args, **kvargs):
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.update_object = self.manager.update_tag
        self.delete_object = self.manager.delete_tag

        if self.model is not None:
            self.services = self.model.__dict__.get("services", None)
            self.links = self.model.__dict__.get("links", None)

    def info(self):
        """Get tag info

        :return: Dictionary with tag info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        if self.services is not None:
            info.update({"services": self.services, "links": self.links})
        return info

    def detail(self):
        """Get service details.

        :return: Dictionary with system capabilities.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = []
        cont = []

        """ TODO
        try:
            # containers
            containers = self.manager.get_containers_from_tags([self.name])
            objs = self.controller.can('view', 'container')

            for i in containers:
                objdef = i.value.lower()
                objclass = i.objclass
                objset = set(objs[objdef])

                # create needs
                needs = self.controller.get_needs(i.objid.split('//'))

                # check if needs overlaps perms
                if self.controller.has_needs(needs, objset) is True:
                    # prepare service
                    container_class = import_class(objclass)
                    obj = container_class(self, connection=i.connection,
                                          oid=i.id, name=i.name,
                                          objid=i.objid, desc=i.desc,
                                          active=i.active, model=i)
                    # append service
                    cont.append(obj.small_info())

            # services
            containers = {c.oid:c for c in
                          self.controller.get_containers(authorize=False)}
            services = self.manager.get_services_from_tags([self.name])
            objs = self.controller.can('view', 'service')

            for i in services:
                # get container
                container = containers[i.container_id]

                objdef = i.value.lower()
                objclass = i.objclass
                objset = set(objs[objdef])

                # create needs
                needs = self.controller.get_needs(i.objid.split('//'))

                # check if needs overlaps perms
                if self.controller.has_needs(needs, objset) is True:
                    # prepare service
                    service_class = import_class(objclass)
                    obj = service_class(self, container, oid=i.id,
                                         objid=i.objid, name=i.name, desc=i.desc,
                                         active=i.active, ext_id=i.ext_id,
                                         attribute=i.attribute,
                                         parent_id=i.parent_id, model=i)
                    # append service
                    res.append(obj.small_info())
        except Exception as ex:
            self.logger.warn('No service found for tag %s: %s' %
                            (self.name, ex), exc_info=True)
        """
        info = ServiceApiObject.info(self)
        if self.services is not None:
            info.update({"services": self.services, "links": self.links})
        return info
