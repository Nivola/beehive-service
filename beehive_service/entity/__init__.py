# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import import_class, id_gen
from beehive.common.apimanager import ApiObject, ApiManagerWarning
from beehive.common.assert_util import AssertUtil
from beehive_service.dao.ServiceDao import ServiceDbManager
from beehive_service.model import ServiceType
from beehive_service.model.base import SrvStatusType
from beehive_service.service_util import ServiceUtil
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from beehive_service.controller import ServiceController


class ServiceApiObject(ApiObject):
    module: str = 'ServiceModule'
    objtype: str = 'service'

    manager: ServiceDbManager = ServiceDbManager()

    def __init__(self, *args, **kvargs):
        """ """
        ApiObject.__init__(self, *args, **kvargs)
        self.controller: ServiceController

    @property
    def version(self)->str:
        """Get version

        :return:
        """
        if self.model is not None:
            return getattr(self.model, 'version', '1.0')
        else:
            return None

    def info(self)->dict:
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info:dict = ApiObject.info(self)
        info.update({
            'version': self.version
        })
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
        servicetype: ServiceType
        servicetype = instance.model.service_definition.service_type
        plugin = None
        try:
            self.logger.debug('Tento la creazione del Plugin %s' % servicetype.objclass)
            serviceTypePlugin = import_class(servicetype.objclass)
            self.logger.debug('Instanziato il Plugin %s' % serviceTypePlugin)
            plugin = ServiceUtil.instanceApi(self.controller, serviceTypePlugin, servicetype)

        except Exception:
            self.logger.error('', exc_info=1)
            raise ApiManagerWarning('Plugin class "%s" not found  for SericeType [%s ]' %
                                    (servicetype.objclass, repr(servicetype)))

        return plugin

    def update_status(self, status):
        if self.update_object is not None:
            # if status == SrvStatusType.DELETED:
            #     name = '%s-%s-DELETED' % (self.name, id_gen())
            # else:
            #     name = self.name
            self.update_object(oid=self.oid, status=status)
            self.logger.debug('Update status of %s to %s' % (self.uuid, status))

    def is_active(self)-> bool:
        """Check if object has status ACTIVE

        :return: True if active
        """
        res = False
        service_status_id = getattr(self.model, 'service_status_id', None)
        status = getattr(self.model, 'status', None)

        # status for Account, Org and Div
        if self.model.is_active() and service_status_id is not None and (service_status_id == 1 or
                                                                         service_status_id == 14):
            res = True
        # status for Service**
        if self.model.is_active() and status is not None and status == SrvStatusType.ACTIVE:
            res = True

        return res


class ApiServiceLink(ServiceApiObject):
    objdef = 'ServiceType.ServiceLink'
    objuri = 'servicelink'
    objname = 'servicelink'
    objdesc = 'servicelink'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.start_service_id = None
        self.end_service_id = None
        self.attributes = None
        self.priority = None

        if self.model is not None:
            self.start_service_id = self.model.start_service_id
            self.end_service_id = self.model.end_service_id
            self.attributes = self.model.attributes
            self.priority = self.model.priority

        # child classes
        self.child_classes = [
        ]

        #
        self.update_object = self.manager.update
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'start_service_id': str(self.start_service_id),
            'end_service_id': str(self.end_service_id),
            'attributes': self.attributes,
            'priority': self.priority,
        }
        )
        return info

    def __repr__(self):
        return '<%s id=%s objid=%s uuid=%s, name=%s, desc=%s, active=%s, start_service_id=%s, end_service_id=%s, ' \
               'attributes=%s, priority=%s>' % ('ApiServiceLink', self.oid, self.objid, self.uuid, self.name,
                                                 self.desc, self.active, self.start_service_id, self.end_service_id,
                                                 self.attributes, self.priority)

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info