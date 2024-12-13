# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2024 CSI-Piemonte

from copy import deepcopy
import logging
from time import sleep
from urllib.parse import urlencode

from marshmallow.fields import String
from sqlalchemy.sql.functions import array_agg
from beecell.simple import format_date, obscure_data, dict_get
from beecell.types.type_string import truncate
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
    ApiServiceTypeContainer,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model.account import Account
from beehive_service.model.base import SrvStatusType
from beehive.common.apimanager import ApiClient, ApiManagerWarning, ApiManagerError
from beehive_service.model import Division, Organization
from beehive.common.assert_util import AssertUtil
from pprint import pprint
from uuid import uuid4
from beecell.types.type_id import id_gen
from beecell.sendmail import check_email


class ApiMonitoringAlert(AsyncApiServiceTypePlugin):
    plugintype = "MonitoringAlert"
    task_path = "beehive_service.plugins.monitoringservice.tasks_v2."

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        if self.instance is not None:
            self.account = self.controller.get_account(self.instance.account_id)

            # # get parent division
            # div = self.controller.manager.get_entity(Division, self.account.division_id)
            # # get parent organization
            # org = self.controller.manager.get_entity(Organization, div.organization_id)

            if self.resource_uuid is not None:
                try:
                    self.resource = self.get_resource()
                except:
                    self.resource = None

            # resource_desc = "%s.%s.%s" % (org.name, div.name, self.account.name)
            # self.logger.debug("post_get - resource_desc: %s" % resource_desc)

    @staticmethod
    def customize_list(controller, entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        # +++++++ logger = logging.getLogger(__name__)

        account_idx = controller.get_account_idx()
        compute_service_idx = controller.get_service_instance_idx(ApiMonitoringAlert.plugintype, index_key="account_id")
        instance_type_idx = controller.get_service_definition_idx(ApiMonitoringAlert.plugintype)

        # get resources
        zones = []
        resources = []
        # logger.info('+++++ customize_list - entities: %s' % entities)
        for entity in entities:
            # entity: ApiMonitoringAlert
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.compute_service = compute_service_idx.get(account_id)
            entity.instance_type_idx = instance_type_idx

            if entity.compute_service.resource_uuid not in zones:
                zones.append(entity.compute_service.resource_uuid)
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        if len(resources) == 0:
            resources_idx = {}
        else:
            if len(resources) > 3:
                resources = None
            else:
                zones = []
            if len(zones) > 40 or len(zones) == 0:
                zones = None
            resources_list = ApiMonitoringAlert(controller).list_resources(zones=zones, uuids=resources)
            resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        # logger.info('+++++ customize_list')
        for entity in entities:
            # logger.info('+++++ customize_list - entity.instance.resource_uuid: %s' % entity.instance.resource_uuid)
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def monitoring_state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: "creating",
            SrvStatusType.PENDING: "creating",
            SrvStatusType.CREATED: "creating",
            SrvStatusType.BUILDING: "creating",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETING: "deleting",
            SrvStatusType.DELETED: "delete",
            SrvStatusType.ERROR: "error",
        }
        return mapping.get(state, "unknown")

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        self.logger.debug("aws_info - begin")
        self.logger.debug("aws_info - config: %s" % self.instance.config)

        if self.resource is None:
            # self.resource = {}
            self.resource = self.get_resource()

        instance_type = self.instance_type_idx.get(str(self.instance.service_definition_id))

        instance_item = {}
        instance_item["id"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["creationDate"] = format_date(self.instance.model.creation_date)
        instance_item["description"] = self.instance.desc
        instance_item["state"] = self.monitoring_state_mapping(self.instance.status)
        instance_item["ownerId"] = self.account.uuid
        instance_item["ownerAlias"] = self.account.name
        instance_item["templateId"] = instance_type.uuid
        instance_item["templateName"] = instance_type.name
        instance_item["stateReason"] = {"nvl-code": 0, "nvl-message": ""}
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "nvl-code": 400,
                "nvl-message": self.instance.last_error,
            }

        instance_item["resource_uuid"] = self.instance.resource_uuid
        # self.logger.debug("aws_info - self.resource: %s" % self.resource)

        # if "severity" in self.resource:
        #    instance_item["severity"] = self.resource.get("severity")

        instance_item["users_email"] = "-"
        instance_item["user_severities"] = "-"

        if self.resource is not None:
            if "users_email" in self.resource:
                instance_item["users_email"] = self.resource.get("users_email")

            if "user_severities" in self.resource:
                instance_item["user_severities"] = self.resource.get("user_severities")

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        self.logger.debug("pre_create - begin")
        self.logger.debug("pre_create - params {}".format(params))

        # # params = self.get_config()
        # json_cfg = self.instance.config_object.json_cfg
        # self.logger.debug('pre_create - dopo get_config - json_cfg {}'.format(json_cfg))
        # # inner_data = json_cfg['alert']

        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")

        account_id = self.instance.account_id
        apiAccount: ApiAccount = self.controller.get_account(account_id)
        account_email = apiAccount.email

        # get email users
        users: list = apiAccount.get_users()
        users_to_add = []
        if check_email(account_email):
            users_to_add.append(account_email)

        for user in users:
            # self.logger.debug('pre_create - user: {}'.format(user))
            if user["role"] == "master":  # or user["role"] == "viewer":
                email = user["email"]

                # to avoid duplicates
                if email is not None and email not in users_to_add and check_email(email):
                    users_to_add.append(email)

        str_users: str = ""
        for email in users_to_add:
            str_users = str_users + email + ","
        self.logger.debug("pre_create - str_users: %s" % str_users)
        if str_users.endswith(","):
            str_users = str_users[:-1]

        name = params["name"]
        desc = params["desc"]

        # triplet arriva dalla view
        triplet = self.get_config("triplet")
        triplet_desc = self.get_config("triplet_desc")
        self.logger.debug("pre_create - triplet: %s" % triplet)
        self.logger.debug("pre_create - triplet_desc: %s" % triplet_desc)

        organization = self.get_config("organization")
        division = self.get_config("division")
        account = self.get_config("account")
        availability_zone = self.get_config("availability_zone")

        alert = self.get_config("alert")
        if "norescreate" in alert:
            norescreate = alert["norescreate"]
        else:
            norescreate = False

        data = {
            "compute_zone": compute_zone,
            "container": container_id,
            "desc": desc,
            "name": name,
            "str_users": str_users,
            "account_email": account_email,
            "triplet": triplet,
            "triplet_desc": triplet_desc,
            "organization": organization,
            "division": division,
            "account": account,
            "availability_zone": availability_zone,
            "norescreate": norescreate,
            "zabbix_threshold": {
                # 'alert_id': triplet.replace('.', '-'),
                "name": triplet + "-alert",
                "desc": desc,
            },
        }
        params["resource_params"] = data
        self.logger.debug("pre_create - resource_params: %s" % obscure_data(deepcopy(params)))

        params["id"] = self.instance.oid

        self.logger.debug("pre_create - end")
        return params

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.logger.debug("pre_delete - begin")
        self.logger.debug("pre_delete - params {}".format(params))

        if self.check_resource() is not None:
            # raise ApiManagerError('Monitoring %s has an active alert. It can not be deleted' % self.instance.uuid)
            container_id = self.get_config("container")
            compute_zone = self.get_config("computeZone")

            data = {
                "container": container_id,
                "compute_zone": compute_zone,
            }
            params["resource_params"] = data
            self.logger.debug("pre_delete params: %s" % params)

            return params

        self.logger.debug("pre_delete - end")
        return params

    #
    # resource
    #
    def get_resource(self, uuid=None):
        """Get resource info

        :param uuid: resource uuid [optional]
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        alert = None
        if uuid is None:
            uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v1.0/nrs/provider/monitoring_thresholds/%s" % uuid
            alert = self.controller.api_client.admin_request("resource", uri, "get", data="").get(
                "monitoring_threshold"
            )
        self.logger.debug("Get monitoring alert resource: %s" % alert)
        return alert

    def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if zones is not None:
            data["parent_list"] = ",".join(zones)
        if uuids is not None:
            data["uuids"] = ",".join(uuids)
        if tags is not None:
            data["tags"] = ",".join(tags)
        uri = "/v1.0/nrs/provider/monitoring_thresholds"
        data = urlencode(data)
        # self.logger.debug('+++++ Get monitoring alert resources - data: %s' % data)
        thresholds = self.controller.api_client.admin_request("resource", uri, "get", data=data).get(
            "monitoring_threshold", []
        )
        self.logger.debug("Get monitoring threshold resources: %s" % truncate(thresholds))
        return thresholds

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # self.logger.debug('create_resource - begin')
        # data = {'monitoring_threstold': args[0]}
        # self.logger.debug('create_resource - data: {}'.format(data))

        compute_zone = args[0].get("compute_zone")
        container = args[0].get("container")

        # params for alert notification
        str_users = args[0].pop("str_users")
        account_email = args[0].pop("account_email")  # può essere None

        zabbix_threshold = args[0].get("zabbix_threshold")
        alert_name = zabbix_threshold.get("name")

        triplet = args[0].pop("triplet")
        triplet_desc = args[0].pop("triplet_desc")
        organization = args[0].pop("organization")
        division = args[0].pop("division")
        account = args[0].pop("account")
        availability_zone = args[0].pop("availability_zone")

        norescreate = args[0].pop("norescreate")
        compute_monitoring_threshold_name = "%s-%s" % (alert_name, availability_zone)

        threshold_data = {
            "monitoring_threshold": {
                "container": container,
                "compute_zone": compute_zone,
                "name": compute_monitoring_threshold_name,
                "desc": compute_monitoring_threshold_name,
                "norescreate": norescreate,
                "availability_zone": availability_zone,
                "zabbix_threshold": {
                    "name": alert_name,
                    "desc": alert_name,
                    "triplet": triplet,
                    "triplet_desc": triplet_desc,
                    "str_users": str_users,
                },
            }
        }
        self.logger.debug("create_resource - threshold_data: %s" % threshold_data)

        # create threshold
        try:
            uri = "/v1.0/nrs/provider/monitoring_thresholds"
            # data = {'monitoring_threstold': args[0]}
            res = self.controller.api_client.admin_request("resource", uri, "post", data=threshold_data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            resource_alert_id = uuid
            self.set_resource(resource_alert_id)
            self.update_status(SrvStatusType.PENDING)

            self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update alert resource: %s" % uuid)

        zabbix_threshold_name = alert_name
        self.logger.debug("create_resource - zabbix_threshold_name: %s" % zabbix_threshold_name)
        self.instance.set_config("zabbix_threshold_name", zabbix_threshold_name)

        self.logger.debug("create_resource - end")
        return uuid

    def update_resource(self, task, **kvargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """
        self.logger.debug("update_resource - begin")

        try:
            # single action
            action = kvargs.pop("action", None)
            if action is not None:
                data = {"action": {action.get("name"): action.get("args")}}
                uri = "/v1.0/nrs/provider/monitoring_threshold/%s/actions" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("update_resource - Update alert action resources: %s" % res)

            # base update
            elif len(kvargs.keys()) > 0:
                data = {"monitoring_threstold": kvargs}
                self.controller.api_client
                api_client: ApiClient = self.controller.api_client
                res = api_client.admin_request(
                    "resource",
                    "/v1.0/nrs/provider/monitoring_threshold/%s" % self.instance.resource_uuid,
                    "put",
                    data=data,
                )
                taskid = res.get("taskid")
                if taskid is not None:
                    self.wait_for_task(taskid, delta=2, maxtime=180, task=task)

                self.logger.debug("update_resource - Update monitoring alert action resources: %s" % res)

                self.logger.debug("update_resource - end")
                return taskid

        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))
        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("delete_resource - begin")
        self.logger.debug("delete_resource - args {}".format(args))
        self.logger.debug("delete_resource - kvargs {}".format(kvargs))

        # delete current resource entities - alert
        res_alert = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)
        self.logger.debug("delete_resource - res_alert {}".format(res_alert))

        self.logger.debug("delete_resource - end")

    def action_resource(self, task, *args, **kvargs):
        """Send action to resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("action_resource - begin")
        self.logger.debug("action_resource - kvargs {}".format(kvargs))

        # create new rules
        action = kvargs.get("action", None)
        if action is not None:
            name = action.get("name")
            action_args = action.get("args")
            self.logger.debug("action_resource - action name: %s" % name)

            if name == "update-users":
                resource_threshold_id = action_args.get("resource_threshold_id")
                triplet = action_args.get("triplet")
                users_email = action_args.get("users_email")
                severity = action_args.get("severity")

                self.__update_resource_users(task, resource_threshold_id, triplet, users_email, severity)

        self.logger.debug("action_resource - end")
        return True

    def __update_resource_users(self, task, resource_threshold_id, triplet, users_email, severity):
        """update users

        :param task: celery task reference
        :param resource_threshold_id: resource threshold id
        :param users_email: users_email
        :rtype: bool
        """
        self.logger.debug("__update_resource_users - begin")
        self.logger.debug("__update_resource_users - triplet: %s" % triplet)
        self.logger.debug("__update_resource_users - users_email: %s" % users_email)
        self.logger.debug("__update_resource_users - severity: %s" % severity)

        user_data = {
            "action": {
                "modify_user": {
                    "triplet": triplet,
                    "users_email": users_email,
                    "severity": severity,
                }
            }
        }
        self.logger.debug("__update_resource_users - user_data: %s" % user_data)

        # create user_data
        try:
            url_action = "/v1.0/nrs/provider/monitoring_thresholds/%s/actions" % resource_threshold_id
            self.logger.debug("__update_resource_users - url_action: %s" % url_action)
            res = self.controller.api_client.admin_request(
                "resource", url_action, "put", data=user_data, other_headers=None
            )
            taskid = res.get("taskid", None)
            uuid = res.get("uuid", None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # wait job
        if taskid is not None:
            self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
        else:
            raise ApiManagerError("user_data job does not started")

        self.logger.debug("__update_resource_users - resource %s" % uuid)
        return True

    def update_users(self, triplet: str, users_email: str, severity: str):
        """Update users in a folder

        :return:
        """
        # check emails are valid
        from beecell.sendmail import check_email

        email_array = users_email.split(",")
        for email in email_array:
            if not check_email(email):
                raise ApiManagerError("Error email not valid %s" % email)

        # check severities are valid
        uri = "/v1.0/nrs/provider/monitoring_thresholds/user/severities"
        res = self.controller.api_client.admin_request("resource", uri, "get")
        user_severities = res.get("user_severities")

        severity_array = severity.split(",")
        for severity_item in severity_array:
            if severity_item not in user_severities:
                raise ApiManagerError("Error severity not valid %s" % severity_item)

        try:
            resource_threshold_id = self.instance.resource_uuid
            self.logger.debug("update_users - resource_threshold_id: %s" % resource_threshold_id)

            # task creation
            params = {
                "resource_params": {
                    "action": {
                        "name": "update-users",
                        "args": {
                            "triplet": triplet,
                            "users_email": users_email,
                            "severity": severity,
                            "resource_threshold_id": resource_threshold_id,
                        },
                    }
                }
            }
            self.logger.debug("update_users - params {}".format(params))
            self.action(**params)

            self.logger.debug("update_users - end")

        except Exception:
            self.logger.error("update_users", exc_info=2)
            raise ApiManagerError("Error update_users for folder %s" % self.instance.uuid)

        return True
