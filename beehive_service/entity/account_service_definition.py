# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import import_class
from beehive.common.apimanager import ApiManagerError
from beehive_service.entity import ServiceApiObject
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_definition import ApiServiceDefinition, ApiServiceConfig
from beehive_service.model import AccountServiceDefinition
from beehive_service.model.base import SrvStatusType


class ApiAccountServiceDefinition(ServiceApiObject):
    module = 'ServiceModule'
    objdef = 'Organization.Division.Account.CATEGORY.AccountServiceDefinition'
    objuri = 'accountservicedefinition'
    objname = 'accountservicedefinition'
    objdesc = 'accountservicedefinition'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.model: AccountServiceDefinition
        self._account: ApiAccount = None
        self._definition: ApiServiceDefinition = None
        self._config: ApiServiceConfig = None
        # self.definition = None
        # self.account = None

        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_instance
        self.delete_object = self.manager.delete
        self.expunge_object = self.manager.purge

    def __repr__(self):
        return '<%s id=%s objid=%s name=%s>' % (self.__class__.__module__ + '.' + self.__class__.__name__,
                                                self.oid, self.objid, self.name)

    @property
    def config(self) -> ApiServiceConfig:
        if self.model is None:
            return None
        if self._config is None:
            if self._definition is None:
                self._definition = ApiServiceDefinition(
                    self.controller,
                    oid=self.model.service_definition.id,
                    objid=self.model.service_definition.objid,
                    name=self.model.service_definition.name,
                    desc=self.model.service_definition.desc,
                    active=self.model.service_definition.active,
                    model=self.model.service_definition)
            self._config = self._definition.get_main_config()
            return self._config
        else:
            return self._config

    @property
    def account_id(self) -> int:
        if self.model is not None:
            return self.model.account_id
        else:
            return None

    @property
    def account(self) -> ApiAccount:

        if self.model is None:
            return None

        if self._account is None:
            self._account = ApiAccount(self.controller,
                                       oid=self.model.account.id,
                                       objid=self.model.account.objid,
                                       name=self.model.account.name,
                                       desc=self.model.account.desc,
                                       active=self.model.account.active,
                                       model=self.model.account)
            return self.model._account
        else:
            return None

    @property
    def service_definition_id(self) -> int:
        if self.model is not None:
            return self.model.service_definition_id
        else:
            return None

    @property
    def service_definition(self) -> ApiServiceDefinition:
        if self.model is None:
            return None
        if self._definition is None:
            self._definition = ApiServiceDefinition(
                self.controller,
                oid=self.model.service_definition.id,
                objid=self.model.service_definition.objid,
                name=self.model.service_definition.name,
                desc=self.model.service_definition.desc,
                active=self.model.service_definition.active,
                model=self.model.service_definition)
            return self._definition
        else:
            return self._definition

    def is_active(self) -> bool:
        """Check if object has status ACTIVE

        :return: True if active
        """
        if self.model is None:
            return False
        if self.model.active:
            return True
        return False

    def info(self) -> dict:
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.service_definition.info(self)
        return info

    def detail(self) -> dict:
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.service_definition.detail()
        return info

    def pre_delete(self, *args, **kvargs) -> dict:
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.

        :param args: custom params
        :param kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        # self.update_status(SrvStatusType.DELETING)
        return kvargs

    def post_delete(self, *args, **kvargs) -> bool:
        """Post delete function. This function is used in delete method. Extend
        this function to execute action after object was deleted.

        :param args: custom params
        :param kvargs: custom params
        :return: True
        :raise ApiManagerError:
        """
        # self.update_status(SrvStatusType.DELETED)
        return True

    def get_service_type_name(self) -> str:
        return self.model.service_definition.service_type.plugintype.name_type

    def get_service_type_plugin(self):
        """Get ServiceType Plugin

        :return: Plugin instance  object info.
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        servicetype_model = self.model.service_definition.service_type
        try:
            plugin_class = import_class(servicetype_model.objclass)
            plugin = plugin_class(self.controller, oid=servicetype_model.id, objid=servicetype_model.objid,
                                  name=servicetype_model.name, desc=servicetype_model.desc,
                                  active=servicetype_model.active, model=servicetype_model)
            plugin.instance = self
            self.logger.debug(
                'Get service instance %s plugin type: %s' % (self.uuid, plugin))
        except Exception:
            self.logger.error('', exc_info=1)
            raise ApiManagerError('Plugin class "%s" not found  for ServiceType plugin "%s"' %
                                    (servicetype_model.objclass, repr(servicetype_model)))

        return plugin

    def is_activable(self):
        """ is it an activable instance
            :return True if has no Parent or has Parent in active state. False otherwise
        """
        return (self.model.linkParent is None or len(self.model.linkParent) == 0) or (len(self.model.linkParent) == 1
            and SrvStatusType.ACTIVE == self.model.linkParent[0].start_service.status) \
            and SrvStatusType.CREATED == self.model.status

    def getPluginTypeName(self):
        return self.model.service_definition.service_type.plugintype.name_type

    def getPluginType(self, pluginNameType=None):
        """Check if the instance refers to a specific plugintype

        :return entity: plugin type entity model
        """
        if pluginNameType is None:
            return None
        elif self.model.service_definition.service_type.plugintype.name_type == pluginNameType:
            return self.model.service_definition.service_type.plugintype
        return None
