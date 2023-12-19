# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from time import sleep

import ujson as json
from beecell.db import TransactionError
from beecell.db.util import QueryError
from beecell.password import obscure_data
from beecell.types.type_dict import dict_get, dict_set
from beecell.types.type_string import truncate
from beecell.simple import import_class
from beehive.common.apimanager import ApiObject, ApiManagerWarning, ApiManagerError
from beehive.common.data import transaction, trace, operation
from beehive_service.entity import ServiceApiObject, ApiServiceLink
from beehive_service.model import ServiceInstance, service_instance
from beehive_service.model.base import SrvStatusType
from beehive_service.service_util import ServiceUtil
from six import text_type, binary_type
from beecell.simple import jsonDumps


class ApiServiceInstance(ServiceApiObject):
    module = "ServiceModule"
    objdef = "Organization.Division.Account.ServiceInstance"
    objuri = "serviceinstance"
    objname = "serviceinstance"
    objdesc = "ServiceInstance"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.model: ServiceInstance
        self.config_object: ApiServiceInstanceConfig = None
        self.definition = None
        self.account = None
        # getters
        # self.account_id = None
        # self.service_definition_id = None
        # self.bpmn_process_id = None
        # self.resource_uuid = None
        # self.status = None

        # if self.model is not None:
        #     self.account_id = self.model.account_id
        #     self.service_definition_id = self.model.service_definition_id
        #     self.bpmn_process_id = self.model.bpmn_process_id
        #     self.resource_uuid = self.model.resource_uuid
        #     self.status = self.model.status

        # child classes
        self.child_classes = [ApiServiceInstanceConfig, ApiServiceLinkInst]

        self.update_object = self.manager.update_service_instance
        self.delete_object = self.manager.delete
        self.expunge_object = self.manager.purge

    def __repr__(self):
        return "<%s id=%s objid=%s name=%s, status=%s>" % (
            self.__class__.__module__ + "." + self.__class__.__name__,
            self.oid,
            self.objid,
            self.name,
            self.status,
        )

    @property
    def config(self):
        if self.config_object is not None:
            from copy import deepcopy

            return obscure_data(deepcopy(self.config_object.json_cfg))
        else:
            return None

    @property
    def account_id(self):
        if self.model is not None:
            return self.model.account_id
        else:
            return None

    @property
    def service_definition_id(self):
        if self.model is not None:
            return self.model.service_definition_id
        else:
            return None

    @property
    def bpmn_process_id(self):
        if self.model is not None:
            return self.model.bpmn_process_id
        else:
            return None

    @property
    def resource_uuid(self):
        if self.model is not None:
            return self.model.resource_uuid
        else:
            return None

    @property
    def status(self):
        if self.model is not None:
            return self.model.status
        else:
            return None

    @property
    def last_error(self):
        if self.model is not None:
            return self.model.last_error
        else:
            return ""

    def is_active(self):
        """Check if object has status ACTIVE

        :return: True if active
        """
        if self.status == "ACTIVE":
            return True
        return False

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

    #
    # params
    #
    def get_params(self, attr_key):
        """Get property from params

        :param attr_key: property name
        :return:
        """
        if self.model is not None and self.model.params is not None:
            params = json.loads(self.model.params)
            return dict_get(params, attr_key)
        return None

    # def set_params(self, attr_key, attr_value):
    #     """Set property in params
    #
    #     :param attr_key: property nameuse_role
    #     :param attr_value: property value
    #     :return:
    #     """
    #     if self.model is not None and self.model.params is not None:

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)

        parent = self.getParent()
        if parent is not None:
            parent = {"uuid": parent.uuid, "name": parent.name}
        else:
            parent = {}

        info.update(
            {
                "account_id": str(self.account_id),
                "service_definition_id": str(self.service_definition_id),
                "bpmn_process_id": self.bpmn_process_id,
                "resource_uuid": self.resource_uuid,
                "status": self.status,
                "parent": parent,
                "is_container": self.is_container(),
                "config": self.config,
                "last_error": self.model.last_error,
                "params": self.model.params,
            }
        )

        if self.account is not None:
            info["account"] = self.account.small_info()

        if self.definition is not None:
            info["definition"] = self.definition.small_info()

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def update_status(self, status, error=None):
        """Update service instance status

        :param status: status
        :param error: error [optional]
        """
        if self.update_object is not None:
            data = {"oid": self.oid, "status": status}
            if error is not None:
                data["last_error"] = error
            self.update_object(**data)
            self.logger.debug("Update status of %s to %s" % (self.uuid, status))

    def set_resource(self, resource):
        """Update service instance resource

        :param resource: resource uuid
        :param error: error [optional]
        """
        if self.update_object is not None:
            data = {"oid": self.oid, "resource_uuid": resource}
            self.update_object(**data)
            self.logger.debug("Update resource of %s to %s" % (self.uuid, resource))

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.

        :param args: custom params
        :param kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.update_status(SrvStatusType.DELETING)
        return kvargs

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

    def get_service_type_name(self):
        return self.model.service_definition.service_type.plugintype.name_type

    def get_service_type_plugin(self):
        """Get ServiceType Plugin

        :return: Plugin instance  object info.
        :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        servicetype_model = self.model.service_definition.service_type
        try:
            plugin_class = import_class(servicetype_model.objclass)
            plugin = plugin_class(
                self.controller,
                oid=servicetype_model.id,
                objid=servicetype_model.objid,
                name=servicetype_model.name,
                desc=servicetype_model.desc,
                active=servicetype_model.active,
                model=servicetype_model,
            )
            plugin.instance = self
            self.logger.debug("Get service instance %s plugin type: %s" % (self.uuid, plugin))
        except Exception:
            self.logger.error("", exc_info=1)
            raise ApiManagerWarning(
                'Plugin class "%s" not found  for ServiceType plugin "%s"'
                % (servicetype_model.objclass, repr(servicetype_model))
            )

        return plugin

    def get_main_config(self):
        """Get ServiceInstance main configuration

        :return: ApiServiceInstanceConfig instance
        :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        configs, total = self.manager.get_paginated_service_instance_configs(
            service_instance_id=self.oid, with_perm_tag=False
        )
        if total > 0:
            c = configs[0]
            config = ApiServiceInstanceConfig(
                self.controller,
                oid=c.id,
                objid=c.objid,
                name=c.name,
                desc=c.desc,
                active=c.active,
                model=c,
            )
            self.config_object = config
        return self.config_object

    def get_definition(self):
        """Get service instance definition

        :return: ServiceDefinition instance
        """
        service_def = self.controller.get_service_def(self.service_definition_id)
        return service_def

    def change_definition(self, definition):
        """Change service instance definition

        :param definition: definition id or name
        :return: True
        """
        service_def = self.controller.get_service_def(definition)

        # check actual definition id is different from new id
        if self.service_definition_id == service_def.oid:
            raise ApiManagerWarning("Service %s definition does not change" % self.uuid)

        service_def_config = service_def.get_active_config()

        service_inst_config = self.get_main_config()
        for k, v in service_def_config.params.items():
            service_inst_config.setJsonProperty(k, v)
        service_inst_config.update(json_cfg=service_inst_config.json_cfg)

        self.update_object(oid=self.oid, service_definition_id=service_def.oid)

        self.logger.debug("Change compute service %s definition to %s" % (self.uuid, definition))
        return service_def_config

    def get_child_instances(self, plugintype=None):
        """Get instance children of a specific plugintype"""
        instances = []
        childs = self.manager.get_service_instance_children(start_service_id=self.oid, plugintype=plugintype)
        for child in childs:
            instance = ApiServiceInstance(
                self.controller,
                oid=child.id,
                objid=child.objid,
                name=child.name,
                desc=child.desc,
                active=child.active,
                model=child,
            )
            instances.append(instance)
        self.logger.debug("Get instance %s childs: %s" % (self.uuid, truncate(instances)))
        return instances

    def is_container(self):
        return self.model.service_definition.service_type.flag_container

    def get_account(self):
        """Get account

        :return: Accunt instance
        """
        account = self.controller.get_account(self.account_id)
        return account

    def get_parent_id(self):
        """Get parent service instance id

        :return: ServiceInstance id
        """
        res = self.manager.get_service_instance_parent_id(self.oid)
        if res is not None:
            res = "%s" % res
        return res

    def has_parent(self):
        """Return True if parent service instance exists

        :return: True or False
        """
        entity = self.manager.get_service_instance_parent(self.oid)
        if entity is not None:
            return True
        return False

    def get_parent(self):
        """Get parent service instance

        :return: ServiceInstance
        """
        entity = self.manager.get_service_instance_parent(self.oid)
        res = None
        if entity is not None:
            res = ApiServiceInstance(
                self.controller,
                oid=entity.id,
                objid=entity.objid,
                name=entity.name,
                active=entity.active,
                desc=entity.desc,
                model=entity,
            )
        return res

    def getRoot(self):
        parent = self.getParent()
        if parent is not None:
            # this isn't root instance.
            return parent.getRoot()
        else:
            # I'm root
            return self

    def hasParent(self):
        """[DEPRECATED]"""
        return (
            self.model is not None
            and self.model.linkParent is not None
            and len(self.model.linkParent) == 1
            and self.model.linkParent[0].start_service_id is not None
        )

    def getParent(self):
        """[DEPRECATED]"""
        if (
            self.model is not None
            and self.model.linkParent is not None
            and len(self.model.linkParent) > 0
            and self.model.linkParent[0].start_service_id is not None
        ):
            return self.controller.get_service_instance(self.model.linkParent[0].start_service_id)
        else:
            return None

    def getActiveCFG(self):
        active_cfg = None
        for cfg in self.model.config:
            if cfg.active:
                active_cfg = cfg
                break

        return ServiceUtil.instanceApi(self.controller, ApiServiceInstanceConfig, active_cfg)

    def is_activable(self):
        """is it an activable instance
        :return True if has no Parent or has Parent in active state. False otherwise
        """
        return (
            (self.model.linkParent is None or len(self.model.linkParent) == 0)
            or (
                len(self.model.linkParent) == 1
                and SrvStatusType.ACTIVE == self.model.linkParent[0].start_service.status
            )
            and SrvStatusType.CREATED == self.model.status
        )

    @transaction
    def activeInstance(self):
        """"""
        self.logger.debug("Acivate instance %s " % self)
        # plugin = self.instancePlugin(None, self)

        if self.model.linkChildren is not None and self.model.linkChildren.count() > 0:
            self.activeInstanceChildren()

        self.state_change_manager(None, SrvStatusType.ACTIVE)

        return self.uuid

    def activeInstanceChildren(self):
        """Children recursive activation

        :return str :resource uuid
        """
        self.logger.info("Activate instance %s children - START " % self)
        # find ServiceInstance children
        children_instance = self.manager.get_service_instance_for_update(self.oid)

        for child in children_instance:
            self.logger.debug("Activate children: %s" % child)
            instChild = ApiServiceInstance(
                self.controller,
                oid=child.id,
                objid=child.objid,
                name=child.name,
                desc=child.desc,
                active=child.active,
                model=child,
            )

            instChild.activeInstance()

        self.logger.info("Activate instance %s children - STOP " % self)
        return self.model.uuid

    def state_change_manager(self, old_status, new_status, data={}):
        """Handler of ServiceInstance state change

        :raises ApiManagerWarning: raise :class:`.ApiManagerWarning`
        """
        if old_status is None:
            old_status = self.status

        updateData = {"status": new_status}
        if old_status == SrvStatusType.DRAFT:
            if new_status == SrvStatusType.DRAFT:
                self.logger.info("Set status=%s" % new_status)
                updateData.update({"bpmn_process_id": data.get("process_id")})

            elif new_status == SrvStatusType.PENDING:
                self.logger.info("Set status=%s" % new_status)
                updateData.update({"resource_uuid": data.get("resource_uuid")})

            elif new_status == SrvStatusType.ACTIVE:
                self.logger.info("Set status=%s" % new_status)
                updateData.update({"resource_uuid": data.get("resource_uuid")})

            else:
                raise ApiManagerWarning("invalid state change from %s to %s" % (old_status, new_status))

        elif old_status == SrvStatusType.PENDING:
            if new_status == SrvStatusType.PENDING:
                pass
            elif new_status == SrvStatusType.CREATED:
                self.logger.info("Set status=%s" % new_status)
                updateData.update({"resource_uuid": data.get("resource_uuid")})
            else:
                raise ApiManagerWarning("invalid state change from %s to %s" % (old_status, new_status))

        elif old_status == SrvStatusType.CREATED:
            if new_status == SrvStatusType.CREATED:
                pass
            elif new_status == SrvStatusType.ACTIVE:
                self.logger.info("Set status=%s" % new_status)

            else:
                raise ApiManagerWarning("invalid state change from %s to %s" % (old_status, new_status))

        elif old_status == SrvStatusType.ACTIVE:
            if new_status == SrvStatusType.STOPPED:
                pass
            elif new_status == SrvStatusType.ACTIVE:
                return
            else:
                raise ApiManagerWarning("invalid state change from %s to %s" % (old_status, new_status))
        elif old_status == SrvStatusType.STOPPED:
            if new_status == SrvStatusType.ACTIVE:
                pass
            elif new_status == SrvStatusType.DELETED:
                self.delete()
            else:
                raise ApiManagerWarning("invalid state change from %s to %s" % (old_status, new_status))

        self.update(**updateData)

    def getInstanceChildren(self, plugintype=None):
        """Get instance children of a specific plugintype [DEPRECATE]"""
        return ServiceUtil.instanceApi(
            self.controller,
            ApiServiceInstance,
            self.manager.get_service_instance_children(start_service_id=self.oid, plugintype=plugintype),
        )

    def getInstanceChildrenHierarchy(self, plugintype=None, tree=[]):
        """Get instance children of a specific plugintype"""

        # TBD: list of status to check
        status_list = [SrvStatusType.ACTIVE]

        children = ServiceUtil.instanceApi(
            self.controller,
            ApiServiceInstance,
            self.manager.get_service_instance_children(start_service_id=self.oid, plugintype=plugintype),
        )
        for child in children:
            # TBD: check if user can view child
            if child.is_active() is True:
                if child.status in status_list:
                    details = child.detail()
                    details.pop("is_container")
                    details.pop("bpmn_process_id")
                    details.pop("resource_uuid")
                    details.pop("service_definition_id")
                    tree.append(details)
                    self.logger.warning(" $$$ %s" % child.getPluginTypeName())
                    child.getInstanceChildrenHierarchy(tree=tree)

        return tree

    def getInstanceByResourceUUID(self, resource_uuid):
        """Get a service instance using the related resource uuid"""
        if resource_uuid is None:
            return None
        res = self.controller.get_service_instances(resource_uuid=resource_uuid)
        for r in res:
            return r
        return None

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

    #
    # links
    #
    @trace(op="view")
    def get_linked_services(self, link_type=None, link_type_filter=None, *args, **kvargs):
        """Get linked services

        :param link_type: link type [optional]
        :param link_type_filter: link type filter
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param details: if True execute customize_list()
        :return: :py:class:`list` of :py:class:`ResourceLink`
        :raise ApiManagerError:
        """

        def get_entities(*args, **kvargs):
            res, total = self.manager.get_linked_services(
                service=self.oid,
                link_type=link_type,
                link_type_filter=link_type_filter,
                *args,
                **kvargs,
            )
            return res, total

        def customize(entities, *args, **kvargs):
            return entities

        res, total = self.controller.get_paginated_entities(
            ApiServiceInstance, get_entities, customize=customize, *args, **kvargs
        )
        self.logger.debug("Get linked service instances: %s" % res)
        return res, total

    @trace(op="link-add.insert")
    def add_link(self, name=None, type=None, end_service=None, attributes={}):
        """Add service links

        :param name: link name
        :param type: link type
        :param end_service: end service reference id, uuid
        :param attributes: link attributes [default={}]
        :param authorize: if True check authorization
        :return: link uuid
        :raise ApiManagerError:
        """
        # # check authorization
        # if operation.authorize is True:
        #     self.controller.check_authorization(ApiServiceInstanceLink.objtype, ApiServiceInstanceLink.objdef,
        #                                         None, 'insert')

        # get service
        end_service_id = self.controller.get_service_instance(oid=end_service).oid

        link = self.controller.add_link(
            name,
            type,
            account=self.account_id,
            start_service=self.oid,
            end_service=end_service_id,
            attributes=attributes,
        )

        return link

    #
    # tags
    #
    @trace(op="view")
    def get_tags(self):
        """list tags

        :return: list of tags
        :rtype: list
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions("view")

        try:
            tags, tot = self.controller.get_tags(service=self.oid)
        except QueryError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)

        self.logger.debug("get service instance %s tags: %s" % (self.uuid, tags))
        return tags

    @trace(op="update")
    def add_tag(self, value):
        """Add tag

        :param str value: tag value
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions("update")

        try:
            # get tag
            tag = self.controller.get_tag(value)
        except ApiManagerError:
            # tag not found create it
            self.controller.add_tag(value=value, account=self.account_id)
            tag = self.controller.get_tag(value)

        try:
            res = self.manager.add_service_tag(self.model, tag.model)
            self.logger.info("Add tag %s to service %s: %s" % (value, self.name, res))
            return res
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)

    @trace(op="update")
    def remove_tag(self, value):
        """Remove tag

        :param str value: tag value
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions("update")

        # get tag
        tag = self.controller.get_tag(value)

        try:
            res = self.manager.remove_service_tag(self.model, tag.model)
            self.logger.info("Remove tag %s from service %s: %s" % (value, self.name, res))
            return res
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)

    def wait_for_status(self, statuslist, delta=2, maxtime=180):
        """
        wait until service instance reach the status
        :param statuslist:
        :param delta:
        :param maxtime:
        :return: str status
        """
        self.logger.info("wait for status: %s" % self.uuid)
        if isinstance(statuslist, list) and len(statuslist) > 0:
            state = self.model.status
            elapsed = 0
            while state not in statuslist:
                if elapsed > maxtime:
                    msg = "Service Instance timeout: %s uuid=%s" % (
                        self.uuid,
                        self.name,
                    )
                    self.logger.error(msg)
                    raise Exception("Service timeout: %s uuid=%s" % (self.uuid, self.name))
                sleep(delta)
                # todo update model
                # self.controller.get_session().refresh(self.model)
                operation.session.refresh(self.model)
                state = self.model.status
                elapsed += delta

            self.logger.info("Service %s reach Status %s " % (self.uuid, state))
            return state
        else:
            self.logger.error("Error got no status to wait for")
            raise Exception("Error no status to wait for")


class ApiServiceInstanceConfig(ServiceApiObject):
    objdef = ApiObject.join_typedef(ApiServiceInstance.objdef, "ServiceInstanceConfig")
    objuri = "instanceconfig"
    objname = "instanceconfig"
    objdesc = "ServiceInstanceConfig"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.service_instance_id = None
        self.json_cfg = {}

        if self.model is not None:
            self.service_instance_id = self.model.service_instance_id
            if isinstance(self.model.json_cfg, dict):
                self.json_cfg.update(self.model.json_cfg)
            # elif isinstance(self.model.json_cfg, str) or isinstance(self.model.json_cfg, unicode):
            elif isinstance(self.model.json_cfg, (text_type, binary_type)):
                self.json_cfg.update(json.loads(self.model.json_cfg))

        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_instance_config
        self.delete_object = self.manager.delete
        self.expunge_object = self.manager.purge

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "service_instance_id": str(self.service_instance_id),
                "json_cfg": self.json_cfg,
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

    def get_json_property(self, attr_key):
        """Get property from config

        :param attr_key: property name. Can be a composed name like k1.k2.k3
        :return:
        """
        if self.json_cfg is None or attr_key is None:
            return None
        else:
            res = dict_get(self.json_cfg, attr_key)
            return res

    def set_json_property(self, attr_key, attr_value):
        """Set property in config

        :param attr_key: property name. Can be a composed name like k1.k2.k3
        :param attr_value: property value
        :return:
        """
        if self.json_cfg is not None:
            dict_set(self.json_cfg, attr_key, attr_value)
            # self.json_cfg[attr_key] = attr_value
            self.update(json_cfg=self.json_cfg)

    def getJsonProperty(self, attrKey):
        """Get property from config [DEPRECATED]

        :param attrKey: property name
        :return:
        """
        if self.json_cfg is None or attrKey is None:
            return None
        else:
            return self.json_cfg.get(attrKey, None)

    def setJsonProperty(self, attrKey, attrValue):
        """Set property in config [DEPRECATED]

        :param attrKey: property name
        :param attrValue: property value
        :return:
        """
        if self.json_cfg is not None:
            self.json_cfg[attrKey] = attrValue


class ApiServiceInstanceLink(ServiceApiObject):
    """ """

    objdef = "Organization.Division.Account.ServiceLink"
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
        self.expunge_object = self.manager.purge

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
            "start_service": start_service.small_info() if start_service is not None else None,
            "end_service": end_service.small_info() if end_service is not None else None,
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
        try:
            start_service = self.controller.get_service_instance(self.model.start_service_id)
        except Exception:
            start_service = None
        return start_service

    def get_end_service(self):
        """ """
        end_service = None
        try:
            end_service = self.controller.get_service_instance(self.model.end_service_id)
        except Exception:
            start_service = None
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

        :param str value: tag value

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

        :param str value: tag value

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


class ApiServiceLinkInst(ApiServiceLink):
    objdef = ApiObject.join_typedef(ApiServiceInstance.objdef, "ServiceLinkInst")
    objuri = "servicelinkinst"
    objname = "servicelinkinst"
    objdesc = "servicelinkinst"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceLink.__init__(self, *args, **kvargs)
        self.update_object = self.manager.update_service_instlink
