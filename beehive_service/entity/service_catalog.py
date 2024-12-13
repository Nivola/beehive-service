# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import copy
from beecell.simple import truncate
from beehive.common.apiclient import BeehiveApiClientError
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import (
    get_operation_params,
    set_operation_params,
    operation,
    trace,
)
from beehive_service.entity import ServiceApiObject
from beehive_service.entity.service_definition import ApiServiceDefinition


class ApiServiceCatalog(ServiceApiObject):
    objdef = "ServiceCatalog"
    objuri = "servicecatalog"
    objname = "servicecatalog"
    objdesc = "servicecatalog"

    role_templates = {
        "master": {
            "desc": "Service Catalog administrator. Can manage everything in the account",
            "name": "CatalogAdminRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "ServiceCatalog",
                    "objid": "<objid>",
                    "action": "*",
                },
            ],
            "perm_tmpls": [
                {
                    "subsystem": "service",
                    "type": "ServiceType.ServiceDefinition",
                    "objid": "<objid>",
                    "action": "view",
                }
            ],
        },
        "viewer": {
            "desc": "Service Catalog viewer. Can view everything in the account",
            "name": "CatalogViewerRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "ServiceCatalog",
                    "objid": "<objid>",
                    "action": "view",
                }
            ],
        },
        "operator": {
            "desc": "Service Catalog operator. Can manage services in the account",
            "name": "CatalogOperatorRole-%s",
            "perms": [],
        },
    }

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_catalog
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        return info

    def detail(self):
        """Get object extended info"""
        info = self.info()
        return info

    def post_create(self, batch=False, *args, **kvargs):
        """Post create function.

        :param args: custom params
        :param kvargs: custom params

        :return::raise ApiManagerError:
        """
        op_params = get_operation_params()
        self.customize(op_params, *args, **kvargs)

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.

        :param args: custom params
        :param kvargs: custom params
        :return:kvargs
        :raise ApiManagerError:
        """
        return kvargs

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method. Extend
        this function to execute action after object was deleted.

        :param args: custom params
        :param kvargs: custom params
        :return:True
        :raise ApiManagerError:
        """
        # self.update_status(SrvStatusType.DELETED)
        return True

    def patch(self, *args, **kvargs):
        """Patch function.

        :param args: custom params
        :param kvargs: custom params
        :param services: list of services to add
        :return:kvargs
        :raise ApiManagerError:
        """
        op_params = get_operation_params()
        res = self.customize(op_params, *args, **kvargs)

        self.logger.debug("Patch service catalog %s: %s" % (self.uuid, res))

    #
    # customization
    #
    def customize(self, op_params, *args, **kvargs):
        """Customization function.

        :param user: copy of operation.user
        :param perms: copy of operation.perms
        :param opid: copy of operation.id
        :param args: custom params
        :param kvargs: custom params
        :param services: list of services to add
        :return:kvargs
        :raise ApiManagerError:
        """
        self.logger.info("Customize %s %s - START" % (self.objname, self.oid))

        try:
            # set local thread operation
            # operation.user = user
            # operation.perms = perms
            # operation.id = opid
            # set_operation_params(op_params)
            # operation.transaction = None
            #
            # # open db session
            # self.get_session()

            # self.update_status(SrvStatusType.UPDATING)  # UPDATING
            self.add_roles()
            # self.update_status(SrvStatusType.ACTIVE)  # ACTIVE
            self.logger.info("Customize %s %s - STOP" % (self.objname, self.oid))
            return True
        except BaseException:
            self.logger.error("", exc_info=1)
            self.logger.error("Customize %s %s - ERROR" % (self.objname, self.oid))
        # finally:
        #     self.release_session()

        return False

    def get_service_definitions(self):
        """Get linked service definitions

        :return: list of service definitions info
        """
        srv_defs = self.model.service_definitions
        res = [
            {
                "id": r.id,
                "uuid": r.uuid,
                "name": r.name,
                "version": r.version,
                "status": r.status,
                "service_type_id": r.service_type_id,
                "active": r.active,
            }
            for r in srv_defs
        ]
        self.logger.debug("Get service definitions linked to catalog %s: %s" % (self.oid, res))
        return res

    @trace(op="view")
    def get_paginated_service_defs(self, *args, **kvargs):
        """Get child ServiceDefinition.

        :param plugintype: plugin type name [optional]
        :param flag_container boolean: if True select only definition with type that is a container [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceDefinition
        :raises ApiManagerError: if query empty return error.
        """
        kvargs["catalogs"] = str(self.oid)

        def recuperaServiceDefinitions(*args, **kvargs):
            # show only active service definition
            kvargs["filter_expired"] = False
            entities, total = self.controller.manager.get_paginated_service_definitions(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        # self.resolve_fk_id('service_type_id', self.get_service_type, kvargs)

        res, total = self.controller.get_paginated_entities(
            ApiServiceDefinition,
            recuperaServiceDefinitions,
            customize=customize,
            authorize=False,
            *args,
            **kvargs,
        )

        return res, total

    #
    # authorization
    #
    def get_role_templates(self) -> list:
        """
        return: List of role template described by a dict
            whith name. description
        """
        res = []
        for k, v in self.role_templates.items():
            res.append({"name": k, "desc": v.get("desc")})
        return res

    def __set_perms_objid(self, perms, objid):
        new_perms = []
        for perm in perms:
            if perm.get("objid").find("<objid>") >= 0:
                new_perm = copy.deepcopy(perm)
                new_perm["objid"] = new_perm["objid"].replace("<objid>", objid)
                new_perms.append(new_perm)
        return new_perms

    def __add_role(self, name, desc, perms):
        try:
            # add role
            role = self.api_client.exist_role(name)
            if role is None:
                role = self.api_client.add_role(name, desc)
                self.logger.debug("Add %s %s role %s" % (self.objname, self.name, name))
        except BeehiveApiClientError:
            self.logger.error("Error creating %s %s roles" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error creating %s %s roles" % (self.objname, self.name))

        try:
            # add role permissions
            # for perm in perms:
            #     self.api_client.append_role_permission_list(role['uuid'], [perm])
            self.api_client.append_role_permission_list(role["uuid"], perms)

            self.logger.debug("Add %s %s role %s perms" % (self.objname, self.name, name))
        except BeehiveApiClientError:
            self.logger.error("Error creating %s %s roles" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error creating %s %s roles" % (self.objname, self.name))

        return True

    def add_roles(self):
        self.logger.info("Add %s %s roles - START" % (self.objname, self.uuid))

        # get catalog defs
        defs_objid = []
        srv_defs, total = self.controller.manager.get_paginated_service_definitions(
            catalogs=str(self.oid), filter_expired=False, size=1000
        )
        for definition in srv_defs:
            defs_objid.append(definition.objid)

        # add roles
        for role in self.role_templates.values():
            name = role.get("name") % self.oid
            desc = role.get("desc")
            perms = self.__set_perms_objid(role.get("perms"), self.objid)

            if role.get("perm_tmpls", None) is not None:
                perm_tmpl = role.get("perm_tmpls")[0]
                for def_objid in defs_objid:
                    perm = self.__set_perms_objid([perm_tmpl], def_objid)
                    perms.extend(perm)
            # perms = [{'objid': p.get('objid')} for p in perms]
            self.__add_role(name, desc, perms)

        self.logger.info("Add %s %s roles - STOP" % (self.objname, self.uuid))
        return True

    def get_users(self):
        res = []
        users = []
        try:
            # get users
            for tmpl, role in self.role_templates.items():
                name = role.get("name") % self.oid
                users = self.api_client.get_users(role=name)
                for user in users:
                    user["role"] = tmpl
                    res.append(user)
        except BeehiveApiClientError:
            self.logger.error("Error get %s %s users" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error get %s %s users" % (self.objname, self.name))
        self.logger.debug("Get %s %s users: %s" % (self.objname, self.name, truncate(str(users))))
        return res

    def set_user(self, user_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.append_user_roles(user_id, [(role_name, "2099-12-31")])
        except BeehiveApiClientError as ex:
            self.logger.error("Error set %s %s users" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error set %s %s users: %s" % (self.objname, self.name, ex.value))
        self.logger.debug("Set %s %s users: %s" % (self.objname, self.name, res))
        return True

    def unset_user(self, user_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.remove_user_roles(user_id, [role_name])
        except BeehiveApiClientError as ex:
            self.logger.error("Error unset %s %s users" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error unset %s %s users: %s" % (self.objname, self.name, ex.value))
        self.logger.debug("Unset %s %s users: %s" % (self.objname, self.name, res))
        return True

    def get_groups(self):
        res = []
        groups = []
        try:
            # get groups
            for tmpl, role in self.role_templates.items():
                name = role.get("name") % self.oid
                groups = self.api_client.get_groups(role=name)
                for group in groups:
                    group["role"] = tmpl
                    res.append(group)
        except BeehiveApiClientError:
            self.logger.error("Error get %s %s groups" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error get %s %s groups" % (self.objname, self.name))
        self.logger.debug("Get %s %s groups: %s" % (self.objname, self.name, truncate(str(groups))))
        return res

    def set_group(self, group_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.append_group_roles(group_id, [(role_name, "2099-12-31")])
        except BeehiveApiClientError as ex:
            self.logger.error("Error set %s %s groups" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error set %s %s groups: %s" % (self.objname, self.name, ex.value))
        self.logger.debug("Set %s %s groups: %s" % (self.objname, self.name, res))
        return True

    def unset_group(self, group_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.remove_group_roles(group_id, [role_name])
        except BeehiveApiClientError as ex:
            self.logger.error("Error unset %s %s groups" % (self.objname, self.name), exc_info=1)
            raise ApiManagerError("Error unset %s %s groups: %s" % (self.objname, self.name, ex.value))
        self.logger.debug("Unset %s %s groups: %s" % (self.objname, self.name, res))
        return True
