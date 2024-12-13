# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import copy

from beecell.simple import truncate
from beecell.auth import IdentityMgr, AuthError
from beehive.common.apimanager import ApiManagerError
from beehive.common.client.apiclient import BeehiveApiClientError
from beehive.common.data import get_operation_params, operation
from beehive_service.entity import ServiceApiObject
from typing import List, Tuple


class AuthorityApiObject(ServiceApiObject):
    MASTER = "master"
    OPERATOR = "operator"
    VIEWER = "viewer"
    role_templates = {}

    def update_status(self, status):
        if self.update_object is not None:
            self.update_object(oid=self.oid, service_status_id=status)
            self.logger.debug("Update status of %s to %s" % (self.uuid, status))

    def post_create(self, batch=True, *args, **kvargs):
        """Post create function.

        :param args: custom params
        :param kvargs: custom params
        :return:
        :raise ApiManagerError:
        """
        op_params = get_operation_params()
        self.customize(op_params, *args, **kvargs)

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.

        :param args: custom params
        :param kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method. Extend
        this function to execute action after object was deleted.

        :param args: custom params
        :param kvargs: custom params
        :return: True
        :raise ApiManagerError:
        """
        self.update_status(6)
        return True

    def patch(self, *args, **kvargs):
        """Patch function.

        :param args: custom params
        :param kvargs: custom params
        :param services: list of services to add
        :return: kvargs
        :raise ApiManagerError:
        """
        import gevent

        op_params = get_operation_params()
        res = gevent.spawn(self.customize, op_params, *args, **kvargs)
        self.logger.debug("Start asynchronous operation: %s" % res)

    #
    # customization
    #
    def customize(self, op_params, *args, **kvargs):
        """Customization function.

        :param op_params: operation params
        :param args: custom params
        :param kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.logger.info("Customize %s %s - START" % (self.objname, self.oid))

        try:
            self.update_status(14)  # UPDATING
            self.add_roles()
            self.update_status(1)  # ACTIVE
            self.logger.info("Customize %s %s - STOP" % (self.objname, self.oid))
            return True
        except Exception:
            self.logger.error("", exc_info=True)
            self.logger.error("Customize %s %s - ERROR" % (self.objname, self.oid))

        return False

    #
    # authorization
    #
    def get_role_templates(self):
        res = []
        for k, v in self.role_templates.items():
            res.append({"name": k, "desc": v.get("desc"), "role": v.get("name") % self.oid})
        return res

    def __set_perms_objid(self, perms, objid):
        new_perms = []
        for perm in perms:
            if perm.get("objid").find("<objid>") >= 0:
                new_perm = copy.deepcopy(perm)
                new_perm["objid"] = new_perm["objid"].replace("<objid>", objid)
                new_perms.append(new_perm)
            else:
                # new_perm = copy.deepcopy(perm)
                # new_perms.append(new_perm)
                new_perms.append(perm)
        return new_perms

    def __add_role(self, name, desc, perms):
        try:
            # add role
            role = self.api_client.exist_role(name)
            if role is None:
                role = self.api_client.add_role(name, desc)
                self.logger.debug("Add %s %s role %s" % (self.objname, self.name, name))
        except BeehiveApiClientError:
            self.logger.error("Error creating %s %s roles" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error creating %s %s roles" % (self.objname, self.name))

        try:
            # add role permissions
            # from beecell.debug import  dbgprint
            # dbgprint (role["uuid"], perms)
            self.api_client.append_role_permission_list(role["uuid"], perms)

            self.logger.debug("Add %s %s role %s perms" % (self.objname, self.name, name))
        except BeehiveApiClientError:
            self.logger.error("Error creating %s %s roles" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error creating %s %s roles" % (self.objname, self.name))

        return True

    def add_roles(self):
        """
        create roles for the object in auth subsystem
        """
        self.logger.info("Add %s %s roles - START" % (self.objname, self.uuid))

        # add roles
        for role in self.role_templates.values():
            name = role.get("name") % self.oid
            desc = role.get("desc")
            perms = self.__set_perms_objid(role.get("perms"), self.objid)
            # from beecell.debug import  dbgprint
            # dbgprint (name, desc, perms)
            self.__add_role(name, desc, perms)

        self.logger.info("Add %s %s roles - STOP" % (self.objname, self.uuid))
        return True

    def get_users(self):
        """
        get all users that has roles fore the self object
        """
        res = []
        users = None
        try:
            # get users
            for tmpl, role in self.role_templates.items():
                name = role.get("name") % self.oid
                users = self.api_client.get_users(role=name)
                for user in users:
                    user["role"] = tmpl
                    res.append(user)
        except BeehiveApiClientError:
            self.logger.error("Error get %s %s users" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error get %s %s users" % (self.objname, self.name))
        self.logger.debug("Get %s %s users: %s" % (self.objname, self.name, truncate(str(users))))
        return res

    def set_user(self, user_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.append_user_roles(user_id, [(role_name, "2099-12-31")])

            self.sync_users_account()
        except BeehiveApiClientError:
            self.logger.error("Error set %s %s users" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error set %s %s users" % (self.objname, self.name))
        self.logger.debug("Set %s %s users: %s" % (self.objname, self.name, res))
        return True

    def role_name(self, role: str) -> str:
        """
        get the rolename
        """
        role_ref = self.role_templates.get(role)
        role_name = role_ref.get("name") % self.oid
        return role_name

    def role_permissions(self, role: str) -> List[tuple]:
        """
        usate solo 2-type 3-definition 4-objid 6-action
        |0-pid  |1-oid |2-type     |3-definition                         | 4-objid       | 5-aid|6-action
        |3554420|444305|'resource' |'Zabbix.Template'                    |'*//*'         |1     |'*'    |
        |3554348|444296|'container'|'Zabbix'                             |'*'            |1     |'*'    |
        """
        perms = []
        role = self.role_templates.get(role)
        if role is None:
            raise ApiManagerError(f"role '{role}' not found", code=404)
        for perm in role.get("perms", []):
            p2type = perm.get("subsystem")
            p3definition = perm.get("type")
            p4objid = perm.get("objid").replace("<objid>", self.objid)
            p6action = perm.get("action")
            p = (-1, -1, p2type, p3definition, p4objid, -1, p6action)
            perms.append(p)
        return perms

    def play_role(self, role: str):
        """
        change current  identity  permission in  order to play a single role

        raise ApimanagerError if identity not found
        raise ApimanagerError if Identity permsions do not match role permission
        """
        perms = self.role_permissions(role)
        token = operation.user[2]
        idmgr: IdentityMgr
        try:
            idmgr = IdentityMgr.factory(token, controller=self.controller)
        except AuthError as ex:
            raise ApiManagerError("Identity not found", code=404)
        except Exception as ex:
            raise ApiManagerError("Identity not found", code=404)
        try:
            if len(perms) > 0:
                idmgr.set_perms(perms, store=True)
        except AuthError:
            raise ApiManagerError("Identity permsions do not match role permission", code=403)

    def reset_role(self):
        try:
            token = operation.user[2]
            idmgr = IdentityMgr.factory(token, controller=self.controller)
            idmgr.restore_full_perms()
            idmgr.save()
        except AuthError as ex:
            code = 400
            if ex.code == AuthError.TOKENEXPIRED:
                code = 428
            raise ApiManagerError(f"{ex.info}", code=code)

    def unset_user(self, user_id, role):
        """
        remove role from user
        """
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.remove_user_roles(user_id, [role_name])

            self.sync_users_account()
        except BeehiveApiClientError:
            self.logger.error("Error unset %s %s users" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error unset %s %s users" % (self.objname, self.name))
        self.logger.debug("Unset %s %s users: %s" % (self.objname, self.name, res))

        return True

    def sync_users_account(self):
        services, tot = self.controller.get_service_type_plugins(account_id=self.oid, size=-1, with_perm_tag=False)
        for service in services:
            # self.logger.debug('+++++ delete - service: {}'.format(service))

            from beehive_service.plugins.monitoringservice.controller import (
                ApiMonitoringFolder,
            )

            if isinstance(service, ApiMonitoringFolder):
                self.logger.debug("sync_users_account - isinstance ApiMonitoringFolder")
                return_value = service.sync_users()

            from beehive_service.plugins.loggingservice.controller import (
                ApiLoggingSpace,
            )

            if isinstance(service, ApiLoggingSpace):
                self.logger.debug("sync_users_account - isinstance ApiLoggingSpace")
                return_value = service.sync_users()

    def get_groups(self):
        res = []
        groups = None
        try:
            # get groups
            for tmpl, role in self.role_templates.items():
                name = role.get("name") % self.oid
                groups = self.api_client.get_groups(role=name)
                for group in groups:
                    group["role"] = tmpl
                    res.append(group)
        except BeehiveApiClientError:
            self.logger.error("Error get %s %s groups" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error get %s %s groups" % (self.objname, self.name))
        self.logger.debug("Get %s %s groups: %s" % (self.objname, self.name, truncate(groups)))
        return res

    def set_group(self, group_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.append_group_roles(group_id, [(role_name, "2099-12-31")])
        except BeehiveApiClientError:
            self.logger.error("Error set %s %s groups" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error set %s %s groups" % (self.objname, self.name))
        self.logger.debug("Set %s %s groups: %s" % (self.objname, self.name, res))
        return True

    def unset_group(self, group_id, role):
        try:
            # get role
            role_ref = self.role_templates.get(role)
            role_name = role_ref.get("name") % self.oid
            res = self.api_client.remove_group_roles(group_id, [role_name])
        except BeehiveApiClientError:
            self.logger.error("Error unset %s %s groups" % (self.objname, self.name), exc_info=True)
            raise ApiManagerError("Error unset %s %s groups" % (self.objname, self.name))
        self.logger.debug("Unset %s %s groups: %s" % (self.objname, self.name, res))
        return True
