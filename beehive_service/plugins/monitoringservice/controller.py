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
from beehive_service.plugins.computeservice.controller import (
    ApiComputeInstance,
    ApiComputeSubnet,
)
from pprint import pprint
from uuid import uuid4
from beecell.types.type_id import id_gen


class ApiMonitoringService(ApiServiceTypeContainer):
    objuri = "monitoringservice"
    objname = "monitoringservice"
    objdesc = "MonitoringService"
    plugintype = "MonitoringService"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypeContainer.__init__(self, *args, **kvargs)
        self.flag_async = True

        self.child_classes = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypeContainer.info(self)
        info.update({})
        return info

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
        account_idx = controller.get_account_idx()
        instance_type_idx = controller.get_service_definition_idx(ApiMonitoringService.plugintype)

        # get resources
        # zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiMonitoringService(controller).list_resources(uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        self.logger.debug("pre_create - begin - params: %s" % obscure_data(deepcopy(params)))
        compute_services, tot = self.controller.get_paginated_service_instances(
            plugintype="ComputeService",
            account_id=self.instance.account_id,
            filter_expired=False,
        )
        self.logger.debug("pre_create - tot: %s" % tot)
        if tot == 0:
            raise ApiManagerError("Some service dependency does not exist")

        compute_service = compute_services[0]
        if compute_service.is_active() is False:
            raise ApiManagerError("Some service dependency are not in the correct status")

        # set resource uuid
        self.set_resource(compute_service.resource_uuid)

        params["resource_params"] = {}
        self.logger.debug("pre_create - end - params: %s" % obscure_data(deepcopy(params)))

        return params

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: "pending",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETED: "deregistered",
            SrvStatusType.DRAFT: "trasient",
            SrvStatusType.ERROR: "error",
        }
        return mapping.get(state, "unknown")

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        # instance_type_idx = self.controller.get_service_definition_idx(ApiMonitoringService.plugintype)

        instance_item = {}
        instance_item["id"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["creationDate"] = format_date(self.instance.model.creation_date)
        instance_item["description"] = self.instance.desc
        instance_item["state"] = self.state_mapping(self.instance.status)
        instance_item["owner"] = self.account.uuid
        instance_item["owner_name"] = self.account.name
        instance_item["template"] = self.instance_type.uuid
        instance_item["template_name"] = self.instance_type.name
        instance_item["stateReason"] = {"code": None, "message": None}
        # reason = self.resource.get('reason', None)
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "code": 400,
                "message": self.instance.last_error,
            }
        instance_item["resource_uuid"] = self.instance.resource_uuid

        return instance_item

    def aws_get_attributes(self):
        """Get account attributes like quotas

        :return:
        """
        if self.resource is None:
            self.resource = {}
        attributes = []

        for quota in self.get_resource_quotas():
            name = quota.get("quota")
            if name.find("monitoring") == 0:
                name = name.replace("monitoring.", "")
                attributes_item = {
                    "attributeName": "%s [%s]" % (name, quota.get("unit")),
                    "attributeValueSet": [
                        {
                            "item": {
                                "attributeValue": quota.get("value"),
                                "nvl-attributeUsed": quota.get("allocated"),
                            }
                        }
                    ],
                }
                attributes.append(attributes_item)

        return attributes

    def set_attributes(self, quotas):
        """Set service quotas

        :param quotas: dict with quotas to set
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {}
        for quota, value in quotas.items():
            data["monitoring.%s" % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix="monitoring"):
        return self.get_container_attributes(prefix=prefix)

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: the running task which is calling the method
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("create_resource begin")
        self.update_status(SrvStatusType.PENDING)
        quotas = self.get_config("quota")
        self.logger.debug("create_resource quotas: {}".format(quotas))
        self.set_resource_quotas(task, quotas)

        # update service status
        self.update_status(SrvStatusType.CREATED)
        self.logger.debug("create_resource - Update instance resources: %s" % self.instance.resource_uuid)

        return self.instance.resource_uuid

    def delete_resource(self, *args, **kvargs):
        """Delete resource do nothing. Compute zone is owned by ComputeService

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("delete_resource begin")
        return True

    def aws_get_availability_zones(self):
        """Get account availability zones

        :return:
        """
        if self.resource is None:
            self.resource = {}

        def state_mapping(state):
            mapping = {"ACTIVE": "available", "ERROR": "unavailable"}
            return mapping.get(state, "unavailable")

        res = []
        for avz in self.get_resource_availability_zones():
            reason = avz.get("reason", None)
            if avz.get("state") != "ACTIVE" and isinstance(reason, list) and len(reason) > 0:
                reason = reason[0]
            else:
                reason = None
            res.append(
                {
                    "zoneName": dict_get(avz, "site.name"),
                    "zoneState": state_mapping(avz.get("state")),
                    "regionName": dict_get(avz, "region.name"),
                    "messageSet": [{"message": reason}],
                }
            )

        return res


class ApiMonitoringFolder(AsyncApiServiceTypePlugin):
    plugintype = "MonitoringFolder"
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
            # get parent account
            account = self.controller.get_account(self.instance.account_id)
            # get parent division
            div = self.controller.manager.get_entity(Division, account.division_id)
            # get parent organization
            org = self.controller.manager.get_entity(Organization, div.organization_id)

            if self.resource_uuid is not None:
                try:
                    self.resource = self.get_resource()
                except:
                    self.resource = None

            resource_desc = "%s.%s.%s" % (org.name, div.name, account.name)
            self.logger.debug("post_get - resource_desc: %s" % resource_desc)

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
        compute_service_idx = controller.get_service_instance_idx(
            ApiMonitoringFolder.plugintype, index_key="account_id"
        )
        instance_type_idx = controller.get_service_definition_idx(ApiMonitoringFolder.plugintype)

        # get resources
        zones = []
        resources = []
        # logger.info('+++++ customize_list - entities: %s' % entities)
        for entity in entities:
            # entity: ApiMonitoringFolder
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
            resources_list = ApiMonitoringFolder(controller).list_resources(zones=zones, uuids=resources)
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
            self.resource = {}

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

        # grafana_folder_name = self.instance.config.get('grafana_folder_name')
        # instance_item['grafanaFolderName'] = grafana_folder_name

        # endpoints
        # self.logger.debug('aws_info - self.resource: %s' % self.resource)
        base_endpoint = self.get_config("dashboard_endpoint")
        # grafana_folder_name = self.instance.config.get('grafana_folder_name')
        # grafana_folder_ext_id = self.instance.config.get('grafana_folder_ext_id')
        grafana_folder_ext_id = self.resource.get("physical_ext_id")

        instance_item["endpoints"] = {
            # 'home': '%s/s/%s/app/home#/' % (base_endpoint, grafana_folder_name),
            "home": "%s/dashboards/f/%s"
            % (base_endpoint, grafana_folder_ext_id)
            # 'discover': '%s/s/%s/app/discover#/' % (base_endpoint, grafana_folder_name)
        }

        # dashboard
        instance_item["dashboards"] = []
        if "dashboards" in self.resource:
            for d in self.resource.get("dashboards"):
                instance_item["dashboards"].append(
                    {
                        "dashboardId": d.get("id"),
                        "dashboardName": d.get("desc"),
                        "dashboardVersion": d.get("version"),
                        "dashboardScore": d.get("score"),
                        "modificationDate": d.get("updated_at"),
                        # 'endpoint': '%s/s/%s/app/dashboards#/view/%s' % (base_endpoint, grafana_folder_name, d.get('id'))
                        "endpoint": "%s/d/%s/" % (base_endpoint, d.get("uid")),
                    }
                )

        # permission
        instance_item["permissions"] = []
        if "permissions" in self.resource:
            for d in self.resource.get("permissions"):
                instance_item["permissions"].append(
                    {
                        "teamId": d.get("teamId"),
                        "teamName": d.get("team"),
                        "permissionName": d.get("permissionName"),
                        "modificationDate": d.get("updated"),
                    }
                )

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # self.logger.debug('pre_create - begin')
        # self.logger.debug('pre_create - params {}'.format(params))

        # # params = self.get_config()
        # json_cfg = self.instance.config_object.json_cfg
        # self.logger.debug('pre_create - dopo get_config - json_cfg {}'.format(json_cfg))
        # # inner_data = json_cfg['folder']

        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")

        # from "monitoring.folder.default" service definition
        dashboard_folder_from = self.get_config("dashboard_folder_from")
        dashboard = self.get_config("dashboard")
        # name = '%s-%s' % (self.instance.name, id_gen(length=8))

        account_id = self.instance.account_id
        apiAccount: ApiAccount = self.controller.get_account(account_id)
        account_email = apiAccount.email

        users: list = apiAccount.get_users()
        users_to_add = []
        for user in users:
            # self.logger.debug('pre_create - user: {}'.format(user))
            if user["role"] == "master" or user["role"] == "viewer":
                email = user["email"]
                # to avoid duplicates
                if email is not None and email not in users_to_add:
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
        self.logger.debug("pre_create - triplet: %s" % triplet)

        organization = self.get_config("organization")
        division = self.get_config("division")
        account = self.get_config("account")

        folder = self.get_config("folder")
        if "norescreate" in folder:
            norescreate = folder["norescreate"]
        else:
            norescreate = False

        data = {
            "compute_zone": compute_zone,
            "container": container_id,
            "desc": desc,
            "name": name,
            "dashboard_folder_from": dashboard_folder_from,
            "dashboard": dashboard,
            "str_users": str_users,
            "account_email": account_email,
            "triplet": triplet,
            "organization": organization,
            "division": division,
            "account": account,
            "norescreate": norescreate,
            "grafana_folder": {
                # 'folder_id': triplet.replace('.', '-'),
                "name": triplet + "-folder",
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
            # raise ApiManagerError('Monitoring %s has an active folder. It can not be deleted' % self.instance.uuid)
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

    def sync_users(self):
        """Synchronize users in a folder

        :return:
        """
        try:
            # creazione triplet
            account_id = self.instance.account_id
            account: ApiAccount = self.controller.get_account(account_id)
            users: list = account.get_users()
            # str_users: str = 'xxx@csi.it,' # per test
            users_to_add = []
            for user in users:
                # self.logger.debug('sync_users - user: {}'.format(user))
                if user["role"] == "master" or user["role"] == "viewer":
                    # si accede a Grafana con l'utenza LDAP @csi.it o @fornitori.nivola
                    # ma l'utente viene registrato con l'email
                    email = user["email"]
                    # ldap = user["ldap"]

                    # to avoid duplicates
                    if email is not None and email not in users_to_add:
                        users_to_add.append(email)

            str_users: str = ""
            for email in users_to_add:
                str_users = str_users + email + ","
            self.logger.debug("sync_users - str_users: %s" % str_users)
            if str_users.endswith(","):
                str_users = str_users[:-1]

            resource_folder_id = self.instance.resource_uuid
            self.logger.debug("sync_users - resource_folder_id: %s" % resource_folder_id)

            # find team child of folder
            team_data = {"parent": resource_folder_id}
            res_team = self.controller.api_client.admin_request(
                "resource",
                "/v1.0/nrs/provider/monitoring_teams",
                "get",
                data=team_data,
                other_headers=None,
            )
            self.logger.debug("sync_users - res_team {}".format(res_team))
            monitoring_teams: list = res_team.get("monitoring_teams")
            if len(monitoring_teams) == 0:
                self.logger.warning("sync_users - no teams found for resource_folder_id: {}".format(resource_folder_id))

            elif len(monitoring_teams) > 0:
                for monitoring_team in monitoring_teams:
                    resource_team_id = monitoring_team.get("uuid")
                    self.logger.debug("sync_users - resource_team_id {}".format(resource_team_id))

                    # task creation
                    params = {
                        "resource_params": {
                            "action": {
                                "name": "sync-users",
                                "args": {
                                    "str_users": str_users,
                                    "resource_team_id": resource_team_id,
                                },
                            }
                        }
                    }
                    self.logger.debug("sync_users - params {}".format(params))
                    self.action(**params)

            self.logger.debug("sync_users - end")

        except Exception:
            self.logger.error("sync_users", exc_info=2)
            raise ApiManagerError("Error sync_users for folder %s" % self.instance.uuid)

        return True

    #
    # resource
    #
    def __get_team_viewer_name(self, triplet):
        name = "Viewer-%s" % triplet
        return name

    def __get_alert_name(self, triplet):
        name = "Mail-%s" % triplet
        return name

    def get_resource(self, uuid=None):
        """Get resource info

        :param uuid: resource uuid [optional]
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        folder = None
        if uuid is None:
            uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v1.0/nrs/provider/monitoring_folders/%s" % uuid
            folder = self.controller.api_client.admin_request("resource", uri, "get", data="").get("monitoring_folder")
        self.logger.debug("Get monitoring folder resource: %s" % truncate(folder))
        return folder

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
        uri = "/v1.0/nrs/provider/monitoring_folders"
        data = urlencode(data)
        # self.logger.debug('+++++ Get monitoring folder resources - data: %s' % data)
        folders = self.controller.api_client.admin_request("resource", uri, "get", data=data).get(
            "monitoring_folders", []
        )
        self.logger.debug("Get monitoring folder resources: %s" % truncate(folders))
        return folders

    def enable_dash_config(self, def_config, dashboard_item_selected, data):
        """enable dashboard config in a folder

        :param module_params: module params
        :param conf: dashboard name params
        :return:
        """
        try:
            # config = self.get_config('instance')
            # compute_instance_id = config.get('ComputeInstanceId')

            # # get compute instance service instance
            # compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

            # # task creation
            # params = {
            #     # 'resource_uuid': compute_service_instance.resource_uuid,
            #     'resource_uuid': self.instance.resource_uuid,
            #     'resource_params': {
            #         'action': 'enable-dash-config',
            #         'def_config': def_config
            #     }
            # }
            # self.logger.debug('enable dash config - params {}'.format(params))
            # self.action(**params)

            resource_folder_id = data["resource_folder_id"]

            triplet = data["triplet"]
            organization = data["organization"]
            division = data["division"]
            account = data["account"]

            dashboard_folder_from = def_config["dashboard_folder_from"]
            dashboard = []
            dashboard.append(dashboard_item_selected)

            # copy dashboard to folder (don't execute just after creation, the resource sometimes isn't already active)
            task = None
            self.__create_resource_dashboard(
                task,
                resource_folder_id,
                organization,
                division,
                account,
                dashboard,
                dashboard_folder_from,
                triplet,
                False,
            )

        except Exception:
            self.logger.error("enable dash config", exc_info=2)
            raise ApiManagerError("Error enabling dash config for folder %s" % self.instance.uuid)

        return True

    def disable_dash_config(self, def_config, dashboard_item_selected, data):
        """disable dashboard config in a folder

        :param module_params: module params
        :param conf: dashboard name params
        :return:
        """
        try:
            resource_folder_id = data["resource_folder_id"]

            dashboard = []
            dashboard.append(dashboard_item_selected)

            # copy dashboard to folder (don't execute just after creation, the resource sometimes isn't already active)
            task = None
            self.__delete_resource_dashboard(
                task,
                resource_folder_id,
                dashboard,
            )

        except ApiManagerError as api_error:
            self.logger.error("disable dash config", exc_info=2)
            raise ApiManagerError(
                "Error disabling dash config for folder %s - error: %s" % (self.instance.uuid, api_error.value)
            )

        except Exception:
            self.logger.error("disable dash config", exc_info=2)
            raise ApiManagerError("Error disabling dash config for folder %s" % self.instance.uuid)

        return True

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # self.logger.debug('create_resource - begin')
        # data = {'monitoring_folder': args[0]}
        # self.logger.debug('create_resource - data: {}'.format(data))

        compute_zone = args[0].get("compute_zone")
        container = args[0].get("container")

        # params for dashboard copy
        dashboard_folder_from = args[0].pop("dashboard_folder_from")
        dashboard = args[0].pop("dashboard")

        # params for alert notification
        str_users = args[0].pop("str_users")
        account_email = args[0].pop("account_email")  # può essere None

        grafana_folder = args[0].get("grafana_folder")
        # folder_id = grafana_folder.get('folder_id')
        folder_name = grafana_folder.get("name")

        triplet = args[0].pop("triplet")
        organization = args[0].pop("organization")
        division = args[0].pop("division")
        account = args[0].pop("account")

        norescreate = args[0].pop("norescreate")

        folder_data = {
            "monitoring_folder": {
                "container": container,
                "compute_zone": compute_zone,
                "name": folder_name,
                "desc": folder_name,
                "norescreate": norescreate,
                "grafana_folder": {
                    "name": folder_name,
                    "desc": folder_name,
                },
            }
        }
        self.logger.debug("create_resource - folder_data: %s" % folder_data)

        # create folder
        try:
            uri = "/v1.0/nrs/provider/monitoring_folders"
            # data = {'monitoring_folder': args[0]}
            res = self.controller.api_client.admin_request("resource", uri, "post", data=folder_data)
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
            resource_folder_id = uuid
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)

            self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update folder resource: %s" % uuid)

            # create team
            team_viewer_name = self.__get_team_viewer_name(triplet)
            resource_team_id = self.__create_resource_team(
                task, container, team_viewer_name, resource_folder_id, norescreate
            )

            # create alert notification
            # Attention: in Grafana version 11 alert notrification doesn't exist!
            # alert_name = self.__get_alert_name(triplet)
            # self.__create_resource_alert(
            #     task,
            #     container,
            #     alert_name,
            #     resource_folder_id,
            #     account_email,
            #     norescreate,
            # )

            if norescreate is False:
                # set permission folder - team
                self.__create_resource_permission(task, resource_folder_id, team_viewer_name)

                # set team users
                self.__create_resource_users(task, resource_team_id, str_users)

                # copy dashboard to folder (don't execute just after creation, the resource sometimes isn't already active)
                self.__create_resource_dashboard(
                    task,
                    resource_folder_id,
                    organization,
                    division,
                    account,
                    dashboard,
                    dashboard_folder_from,
                    triplet,
                )

        grafana_folder_name = folder_name
        self.logger.debug("create_resource - grafana_folder_name: %s" % grafana_folder_name)
        self.instance.set_config("grafana_folder_name", grafana_folder_name)

        # grafana_folder_ext_id = self.__get_folder(resource_folder_id)
        # grafana_folder_ext_id = self.get_resource(resource_folder_id).get('ext_id', None)
        # save grafana_folder_ext_id in config
        # self.instance.set_config('grafana_folder_ext_id', grafana_folder_ext_id)

        self.logger.debug("create_resource - end")

        return uuid

    # def __get_folder(self, resource_folder_id):
    #     """Get resource folder

    #     :param task:
    #     :param container:
    #     :param resource_folder_id:
    #     :return:
    #     """
    #     self.logger.debug('__get_folder - resource_folder_id: %s' % resource_folder_id)

    #     # get folder
    #     try:
    #         uri = '/v1.0/nrs/provider/monitoring_folders'
    #         res = self.controller.api_client.admin_request('resource', uri, 'get', other_headers=None)
    #         self.logger.debug('__get_folder - res: %s' % res)
    #         monitoring_folders = res.get('monitoring_folders', None)
    #         monitoring_folder = monitoring_folders[0]
    #         ext_id = monitoring_folder.get('ext_id', None)
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=True)
    #         raise ApiManagerError(ex.message)

    #     self.logger.debug('__get_folder - ext_id %s' % ext_id)
    #     return ext_id

    def __create_resource_team(self, task, container, team_name, resource_folder_id, norescreate):
        """Create team

        :param task: task instance
        :param container:
        :param triplet:
        :param resource_folder_id:
        :return:
        """
        team_data = {
            "monitoring_team": {
                "container": container,
                "name": team_name,
                "desc": team_name,
                "monitoring_folder": resource_folder_id,
                "norescreate": norescreate,
                "grafana_team": {
                    "name": team_name,
                    "desc": team_name,
                    # 'folder_id': folder_id
                },
            }
        }
        self.logger.debug("create_resource_team - team data: %s" % team_data)

        # create team
        try:
            res = self.controller.api_client.admin_request(
                "resource",
                "/v1.0/nrs/provider/monitoring_teams",
                "post",
                data=team_data,
                other_headers=None,
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
            raise ApiManagerError("team job does not started")

        self.logger.debug("create_resource_team - team resource %s" % uuid)
        return uuid

    def __create_resource_dashboard(
        self,
        task,
        resource_folder_id,
        organization,
        division,
        account,
        dashboard,
        dashboard_folder_from,
        triplet=None,
        check_default: bool = True,
    ):
        """Create dashboard

        :param task: celery task reference
        :param resource_folder_id: resource folder id
        :param organization: organization
        :param division: division
        :param account: account
        :param dashboard: list of
        :param triplet: account triplet
        :rtype: bool
        """
        self.logger.debug("__create_resource_dashboard - begin")
        self.logger.debug("__create_resource_dashboard - organization: %s" % organization)
        self.logger.debug("__create_resource_dashboard - division: %s" % division)
        self.logger.debug("__create_resource_dashboard - account: %s" % account)

        for dashboard_item in dashboard:
            # from "monitoring.folder.default" service definition
            title = dashboard_item["title"]
            monitortype = dashboard_item["monitortype"]

            default = False
            if "default" in dashboard_item:
                default = dashboard_item["default"]

            if check_default and not default:
                self.logger.info("__create_resource_dashboard - dashboard %s not default" % title)
                continue

            dash_tag = None
            if "tag" in dashboard_item:
                dash_tag = dashboard_item["tag"]

            dashboard_data = {
                "action": {
                    "add_dashboard": {
                        "dashboard_folder_from": dashboard_folder_from,
                        "dashboard_to_search": title,
                        "dash_tag": dash_tag,
                        "organization": organization,
                        "division": division,
                        "account": account,
                    }
                }
            }
            self.logger.debug("__create_resource_dashboard - dashboard_data: %s" % dashboard_data)

            # create dashboard_data
            try:
                url_action = "/v1.0/nrs/provider/monitoring_folders/%s/actions" % resource_folder_id
                self.logger.debug("__create_resource_dashboard - url_action: %s" % url_action)
                res = self.controller.api_client.admin_request(
                    "resource",
                    url_action,
                    "put",
                    data=dashboard_data,
                    other_headers=None,
                )
                taskid = res.get("taskid", None)
                uuid = res.get("uuid", None)
                self.logger.debug("__create_resource_dashboard - taskid %s" % taskid)
                self.logger.debug("__create_resource_dashboard - resource %s" % uuid)

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
                raise ApiManagerError("dashboard_data job does not started")

        return True

    def __delete_resource_dashboard(
        self,
        task,
        resource_folder_id,
        dashboard,
    ):
        """Delete dashboard

        :param task: celery task reference
        :param resource_folder_id: resource folder id
        :param organization: organization
        :param division: division
        :param account: account
        :param dashboard: list of
        :param triplet: account triplet
        :rtype: bool
        """
        self.logger.debug("__delete_resource_dashboard - begin")

        for dashboard_item in dashboard:
            title = dashboard_item["title"]
            dashboard_data = {
                "action": {
                    "delete_dashboard": {
                        "dashboard_to_search": title,
                    }
                }
            }
            self.logger.debug("__delete_resource_dashboard - dashboard_data: %s" % dashboard_data)

            try:
                url_action = "/v1.0/nrs/provider/monitoring_folders/%s/actions" % resource_folder_id
                self.logger.debug("__delete_resource_dashboard - url_action: %s" % url_action)
                res = self.controller.api_client.admin_request(
                    "resource",
                    url_action,
                    "put",
                    data=dashboard_data,
                    other_headers=None,
                )
                taskid = res.get("taskid", None)
                uuid = res.get("uuid", None)
                self.logger.debug("__delete_resource_dashboard - taskid %s" % taskid)
                self.logger.debug("__delete_resource_dashboard - resource %s" % uuid)

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
                raise ApiManagerError("dashboard_data job does not started")

        return True

    def __create_resource_permission(self, task, resource_folder_id, team_viewer_name):
        """Create permission

        :param task: celery task reference
        :param resource_folder_id: resource folder id
        :param team_viewer_name: team_viewer_name
        :rtype: bool
        """
        self.logger.debug("__create_resource_permission - begin")
        self.logger.debug("__create_resource_permission - team_viewer_name: %s" % team_viewer_name)

        permission_data = {"action": {"add_permission": {"team_viewer": team_viewer_name, "team_editor": None}}}
        self.logger.debug("__create_resource_permission - permission_data: %s" % permission_data)

        # create permission_data
        try:
            url_action = "/v1.0/nrs/provider/monitoring_folders/%s/actions" % resource_folder_id
            self.logger.debug("__create_resource_permission - url_action: %s" % url_action)
            res = self.controller.api_client.admin_request(
                "resource", url_action, "put", data=permission_data, other_headers=None
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
            raise ApiManagerError("permission_data job does not started")

        self.logger.debug("__create_resource_permission - resource %s" % uuid)
        return True

    def __create_resource_users(self, task, resource_team_id, str_users):
        """Create permission

        :param task: celery task reference
        :param resource_folder_id: resource folder id
        :param team_viewer_name: team_viewer_name
        :param str_users: str_users
        :rtype: bool
        """
        self.logger.debug("__create_resource_users - begin")
        self.logger.debug("__create_resource_users - str_users: %s" % str_users)

        user_data = {
            "action": {
                "add_user": {
                    "users_email": str_users,
                }
            }
        }
        self.logger.debug("__create_resource_users - user_data: %s" % user_data)

        # create user_data
        try:
            url_action = "/v1.0/nrs/provider/monitoring_teams/%s/actions" % resource_team_id
            self.logger.debug("__create_resource_users - url_action: %s" % url_action)
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

        self.logger.debug("__create_resource_users - resource %s" % uuid)
        return True

    def __create_resource_alert(
        self,
        task,
        container,
        alert_name,
        resource_folder_id,
        account_email,
        norescreate,
    ):
        """Create alert notification

        :param task:
        :param container:
        :param triplet:
        :param resource_folder_id:
        :param team_name:
        :param users_email:
        :return:
        """
        if account_email is None:
            account_email = ""

        alert_data = {
            "monitoring_alert": {
                "container": container,
                "name": alert_name,
                "desc": alert_name,
                "monitoring_folder": resource_folder_id,
                "norescreate": norescreate,
                "grafana_alert": {
                    "name": alert_name,
                    "desc": alert_name,
                    "email": account_email,
                },
            }
        }
        self.logger.debug("create_resource_alert - alert_data: %s" % alert_data)

        # create alert notification
        try:
            uri = "/v1.0/nrs/provider/monitoring_alerts"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=alert_data, other_headers=None)
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
            raise ApiManagerError("alert notification job does not started")

        self.logger.debug("create_resource_alert - resource %s" % uuid)
        return True

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
                uri = "/v1.0/nrs/provider/monitoring_folders/%s/actions" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("update_resource - Update folder action resources: %s" % res)

            # base update
            elif len(kvargs.keys()) > 0:
                data = {"monitoring_folder": kvargs}
                self.controller.api_client
                api_client: ApiClient = self.controller.api_client
                res = api_client.admin_request(
                    "resource",
                    "/v1.0/nrs/provider/monitoring_folders/%s" % self.instance.resource_uuid,
                    "put",
                    data=data,
                )
                taskid = res.get("taskid")
                if taskid is not None:
                    self.wait_for_task(taskid, delta=2, maxtime=180, task=task)

                self.logger.debug("update_resource - Update monitoring folder action resources: %s" % res)

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

        self.__delete_team(task)
        # self.__delete_alert(task)

        # delete current resource entities - folder
        res_folder = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)
        self.logger.debug("delete_resource - res_folder {}".format(res_folder))

        self.logger.debug("delete_resource - end")

    def __delete_team(self, task):
        # find team child of folder
        team_data = {"parent": self.instance.resource_uuid}
        res_team = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/monitoring_teams",
            "get",
            data=team_data,
            other_headers=None,
        )
        self.logger.debug("__delete_team - res_team {}".format(res_team))
        monitoring_teams: list = res_team.get("monitoring_teams")
        if len(monitoring_teams) > 0:
            # monitoring_team = monitoring_teams.pop(0)
            # uuid_team = monitoring_team.get('uuid')
            for monitoring_team in monitoring_teams:
                uuid_team = monitoring_team.get("uuid")

                # delete team
                self.logger.debug("__delete_team - delete uuid_team %s" % uuid_team)
                team_delete_data = {}
                uri = "/v1.0/nrs/provider/monitoring_teams/" + uuid_team
                res_team_delete = self.controller.api_client.admin_request(
                    "resource", uri, "delete", data=team_delete_data, other_headers=None
                )
                self.logger.debug("__delete_team - res_team_delete {}".format(res_team_delete))
                uuid = res_team_delete.get("uuid")
                taskid = res_team_delete.get("taskid")
                if uuid is not None and taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                    self.logger.debug("__delete_team - ok - deleted uuid_team %s" % uuid_team)
        else:
            self.logger.debug("__delete_team - no team to delete")

    def __delete_alert(self, task):
        # find alert notification child of folder
        alert_data = {"parent": self.instance.resource_uuid}
        uri = "/v1.0/nrs/provider/monitoring_alerts"
        res_alert = self.controller.api_client.admin_request(
            "resource", uri, "get", data=alert_data, other_headers=None
        )
        self.logger.debug("delete_alert - res_alert {}".format(res_alert))
        monitoring_alerts: list = res_alert.get("monitoring_alerts")
        if len(monitoring_alerts) > 0:
            monitoring_alert = monitoring_alerts.pop(0)
            uuid_alert = monitoring_alert.get("uuid")

            # delete alert
            self.logger.debug("delete_alert - delete uuid_alert %s" % uuid_alert)
            alert_delete_data = {}
            uri = "/v1.0/nrs/provider/monitoring_alerts/" + uuid_alert
            res_alert_delete = self.controller.api_client.admin_request(
                "resource", uri, "delete", data=alert_delete_data, other_headers=None
            )
            self.logger.debug("delete_alert - res_alert_delete {}".format(res_alert_delete))
            uuid = res_alert_delete.get("uuid")
            taskid = res_alert_delete.get("taskid")
            if uuid is not None and taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                self.logger.debug("delete_alert - ok - deleted uuid_alert %s" % uuid_alert)
        else:
            self.logger.debug("delete_alert - no alert to delete")

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

        # TODO verifica # compute_zone = self.get_config("computeZone")
        # TODO verifica # container = self.get_config("container")

        # create new rules
        action = kvargs.get("action", None)
        if action is not None:
            name = action.get("name")
            action_args = action.get("args")
            self.logger.debug("action_resource - action name: %s" % name)

            if name == "sync-users":
                # self.instance.sync_users_action()
                resource_team_id = action_args.get("resource_team_id")
                str_users = action_args.get("str_users")

                self.__create_resource_users(task, resource_team_id, str_users)

        self.logger.debug("action_resource - end")
        return True


class ApiMonitoringInstance(AsyncApiServiceTypePlugin):
    plugintype = "MonitoringInstance"
    task_path = "beehive_service.plugins.monitoringservice.tasks_v2."

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.child_classes = []
        self.account = None

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
        #     # get parent account
        #     account = self.controller.get_account(self.instance.account_id)
        #     # get parent division
        #     div = self.controller.manager.get_entity(Division, account.division_id)
        #     # get parent organization
        #     org = self.controller.manager.get_entity(Organization, div.organization_id)
        #
        #     resource_desc = '%s.%s.%s' % (org.name, div.name, account.name)
        #     self.logger.debug('post_get - resource_desc: %s' % resource_desc)

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
        account_idx = controller.get_account_idx()
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)

        return entities

    def monitoring_state_mapping(self, state):
        mapping = {
            SrvStatusType.DRAFT: "creating",
            SrvStatusType.PENDING: "creating",
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
        if self.resource is None:
            self.resource = {}

        inner_data = self.instance.config.get("instance")
        compute_instance = None
        if inner_data is not None and "ComputeInstanceId" in inner_data:
            compute_instance = inner_data.get("ComputeInstanceId")

        instance_item = {}
        instance_item["id"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["creationDate"] = format_date(self.instance.model.creation_date)
        instance_item["description"] = self.instance.desc
        instance_item["state"] = self.monitoring_state_mapping(self.instance.status)
        instance_item["ownerId"] = str(self.instance.account_id)
        instance_item["ownerAlias"] = self.account.name
        # instance_item['template'] = self.instance_type.uuid
        # instance_item['template_name'] = self.instance_type.name
        instance_item["stateReason"] = {"nvl-code": 0, "nvl-message": ""}
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "nvl-code": 400,
                "nvl-message": self.instance.last_error,
            }

        instance_item["computeInstanceId"] = compute_instance

        # modules = self.instance.config.get('modules')
        # instance_item['modules'] = modules

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        compute_zone = self.get_config("computeZone")

        # base quotas
        quotas = {"monitoring.instances": 1}

        # check quotas
        # commentare in fase di add
        self.check_quotas(compute_zone, quotas)

        # read config
        config = self.get_config("instance")
        compute_instance_id = config.get("ComputeInstanceId")
        norescreate = config.get("norescreate")

        # get compute instance service instance
        plugin: ApiComputeInstance = self.controller.get_service_type_plugin(compute_instance_id)
        if plugin.get_simple_runstate() == "poweredOff":
            raise ApiManagerError("Can't create monitoring instance. Compute instance not running")

        compute_instance_resource_uuid = plugin.instance.resource_uuid
        compute_instance_oid = plugin.instance.oid

        params["resource_params"] = {
            "compute_instance_resource_uuid": compute_instance_resource_uuid,
            "compute_instance_id": compute_instance_oid,
            "norescreate": norescreate,
        }

        self.logger.debug("pre_create - end")
        return params

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        return params

    #
    # resource
    #
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        norescreate = args[0].pop("norescreate", None)
        compute_instance_id = args[0].pop("compute_instance_id", None)
        compute_instance_resource_uuid = args[0].pop("compute_instance_resource_uuid", None)

        # create link between instance and compute instance
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)
        self.add_link(
            name="monitoring-%s" % id_gen(),
            type="monitoring",
            end_service=compute_service_instance.oid,
            attributes={},
        )

        if norescreate is not None and norescreate == True:
            self.logger.debug("+++++ No action on compute instance %s" % (compute_instance_resource_uuid))
        else:
            templates = None
            data = {"action": {"enable_monitoring": {"templates": templates}}}
            uri = "/v1.0/nrs/provider/instances/%s/actions" % compute_instance_resource_uuid
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug(
                "+++++ Update compute instance %s action resources: %s" % (compute_instance_resource_uuid, res)
            )

        return self.instance.resource_uuid

    def update_resource(self, task, **kwargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """
        self.logger.debug("update_resource - begin")
        self.logger.debug("update_resource - end")

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        config = self.get_config("instance")
        compute_instance_id = config.get("ComputeInstanceId")

        # get compute instance service instance
        plugin: ApiComputeInstance = self.controller.get_service_type_plugin(compute_instance_id)
        if plugin.get_simple_runstate() == "poweredOff":
            raise ApiManagerError("Can't delete monitoring instance. Connected compute instance not running")

        compute_instance_resource_uuid = plugin.instance.resource_uuid
        data = {"action": {"disable_monitoring": {}}}
        uri = "/v1.0/nrs/provider/instances/%s/actions" % compute_instance_resource_uuid
        res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
        taskid = res.get("taskid", None)
        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug("Update compute instance %s action resources: %s" % (compute_instance_resource_uuid, res))

        return True

    def check_resource(self, *args, **kvargs):
        """Check resource exists

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        config = self.get_config("instance")
        self.logger.debug("+++++ config: {}".format(config))

        compute_instance_id = None
        if config is not None and "ComputeInstanceId" in config:
            compute_instance_id = config.get("ComputeInstanceId")

        # get compute instance service instance
        self.logger.debug("+++++ compute_instance_id: %s" % (compute_instance_id))
        compute_service_instance: ApiServiceInstance = self.controller.get_service_instance(compute_instance_id)

        return compute_service_instance.resource_uuid
