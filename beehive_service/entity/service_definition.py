# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from typing import Union
from beehive_service.model.service_definition import ServiceConfig
import ujson as json

from beecell.simple import str2bool, id_gen, dict_get, dict_set
from beehive.common.apimanager import ApiObject
from beehive_service.entity import ServiceApiObject, ApiServiceLink
from beehive_service.model.base import SrvStatusType, ConfParamType
from beehive_service.service_util import ServiceUtil
from beehive_service.model import ServiceDefinition, ServiceConfig
from six import text_type, binary_type


class ApiServiceConfig(ServiceApiObject):
    pass

class ApiServiceDefinition(ServiceApiObject):
    objdef = 'ServiceType.ServiceDefinition'
    objuri = 'servicedefinition'
    objname = 'servicedefinition'
    objdesc = 'ServiceDefinition'


    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.model: ServiceDefinition
        self.service_type_id = None
        self.status = None
        self.config_object: ApiServiceConfig = None

        if self.model is not None:
            self.service_type_id = self.model.service_type_id
            self.status = self.model.status

        # child classes
        self.child_classes = [
            ApiServiceConfig,
            ApiServiceLinkDef
        ]

        self.update_object = self.manager.update_service_definition
        self.delete_object = self.manager.delete

    @property
    def service_category(self) -> str:
        """ Return the service category for the Service definition
        """
        if self.model is None:
            return None
        return self.model.service_type.plugintype.service_category

    @property
    def hierarchical_category(self) -> str:
        """ Return the service category for the Service definition
        """
        if self.model is None:
            return None
        return self.model.service_type.plugintype.category

    @property
    def plugin_name(self) -> str:
        """ Return the service plugin name
        """
        if self.model is None:
            return None
        return self.model.service_type.plugintype.name_type

    def info(self)->dict:
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'service_type_id': str(self.service_type_id),
            'status': self.status,
            'is_default': str2bool(self.model.is_default)
        })
        return info

    def detail(self) -> dict:
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    #
    # config
    #
    def get_config(self, attr_key):
        """Get property from config

        :param attr_key: property name
        :return:
        """
        if self.config_object is None:
            self.get_main_config()

        if self.config_object is not None:
            return self.config_object.get_json_property(attr_key)
        return None

    def set_config(self, attr_key, attr_value):
        """Set property in config

        :param attr_key: property name
        :param attr_value: property value
        :return:
        """
        if self.config_object is None:
            self.get_main_config()

        if self.config_object is not None:
            self.config_object.set_json_property(attr_key, attr_value)

    def get_main_config(self) -> ApiServiceConfig:
        """Get ServiceInstance main configuration

        :return: ApiServiceInstanceConfig instance
        :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        if self.config_object is not None:
            return self.config_object

        configs, total = self.manager.get_paginated_service_configs(service_definition_id=self.oid,
                                                                    with_perm_tag=False)
        if total > 0:
            c = configs[0]
            config = ApiServiceConfig(self.controller, oid=c.id, objid=c.objid, name=c.name, desc=c.desc,
                                      active=c.active, model=c)
            self.config_object = config
        return self.config_object

    def get_active_config(self):
        active_cfg = None
        for cfg in self.model.config_params:
            if cfg.active is True:
                active_cfg = cfg
                break

        return ServiceUtil.instance_api(self.controller, ApiServiceConfig, active_cfg)

    def getActiveCFG(self):
        """
        :DEPRECATED:
        :return:
        """
        active_cfg = None
        for cfg in self.model.config_params:
            if cfg.active is True:
                active_cfg = cfg
                break

        return ServiceUtil.instanceApi(self.controller, ApiServiceConfig, active_cfg)

    def update_status(self, status):
        if self.update_object is not None:
            # if status == SrvStatusType.DELETED:
            #     name = '%s-%s-DELETED' % (self.name, id_gen())
            # else:
            #     name = self.name
            self.update_object(oid=self.oid, status=status)
            self.logger.debug('Update status of %s to %s' % (self.uuid, status))

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method. Extend
        this function to execute action after object was deleted.

        :param args: custom params
        :param kvargs: custom params
        :return: True

        :raise ApiManagerError:
        """
        self.update_status(SrvStatusType.DELETED)
        return True


class ApiServiceConfig(ServiceApiObject):
    objdef = ApiObject.join_typedef(ApiServiceDefinition.objdef, 'ServiceConfig')
    objuri = 'serviceconfig'
    objname = 'serviceconfig'
    objdesc = 'ServiceConfig'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.service_definition_id = None
        self.params = {}
        self.params_type = ConfParamType.JSON

        if self.model is not None:
            self.service_definition_id = self.model.service_definition_id

            if isinstance(self.model.params, dict):
                self.params.update(self.model.params)
            # elif isinstance(self.model.params, str) or isinstance(self.model.params, unicode):
            elif isinstance(self.model.params, (text_type, binary_type)):
                self.params.update(json.loads(self.model.params))

            self.params_type = self.model.params_type

        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_config
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'service_definition_id': str(self.service_definition_id),
            'params': self.params,
            'params_type': self.params_type,
        })
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def get_json_property(self, attr_key)-> Union[dict, None]:
        """Get property from config

        :param attr_key: property name. Can be a composed name like k1.k2.k3
        :return:
        """
        if self.params is None or attr_key is None:
            return None
        else:
            res = dict_get(self.params, attr_key)
            return res

    def set_json_property(self, attr_key, attr_value):
        """Set property in config

        :param attr_key: property name. Can be a composed name like k1.k2.k3
        :param attr_value: property value
        :return:
        """
        if self.params is not None:
            dict_set(self.params, attr_key, attr_value)
            self.params[attr_key] = attr_value
            self.update(params=self.params)

    def getJsonProperty(self, attrKey):
        """
        """
        if self.params is None or attrKey is None:
            return None
        else:
            return self.params.get(attrKey, None)


class ApiServiceLinkDef(ApiServiceLink):
    objdef = ApiObject.join_typedef(ApiServiceDefinition.objdef, 'ServiceLinkDef')
    objuri = 'servicelinkdef'
    objname = 'servicelinkdef'
    objdesc = 'servicelinkdef'

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceLink.__init__(self, *args, **kvargs)
        self.update_object = self.manager.update_service_deflink
