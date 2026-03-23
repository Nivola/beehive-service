#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from copy import deepcopy
from http.client import HTTPConnection
import json
import logging
from time import sleep
from urllib.parse import urlencode

from beecell.simple import format_date, jsonDumps, obscure_data, dict_get
from beecell.types.type_string import truncate
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
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

class ApiNamespaceInstance(AsyncApiServiceTypePlugin):
    plugintype = "NamespaceInstance"
    task_path = "beehive_service.plugins.containerservice.tasks_v2."

    # override update_task
    update_task = "beehive_service.plugins.containerservice.tasks_v2.container_plugin_inst_update_task"
    delete_task = "beehive_service.plugins.containerservice.tasks_v2.container_plugin_inst_delete_task"

    # CHART_TARGET_REVISION_LAST = "0.24.0"

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
            ApiNamespaceInstance.plugintype, index_key="account_id"
        )
        instance_type_idx = controller.get_service_definition_idx(ApiNamespaceInstance.plugintype)

        # get resources
        # logger.info('+++++ customize_list - entities: %s' % entities)
        for entity in entities:
            apiNamespaceInstance: ApiNamespaceInstance = entity
            account_id = str(apiNamespaceInstance.instance.account_id)
            apiNamespaceInstance.account = account_idx.get(account_id)
            apiNamespaceInstance.compute_service = compute_service_idx.get(account_id)
            apiNamespaceInstance.instance_type_idx = instance_type_idx

        return entities

    def container_state_mapping(self, state):
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
        instance_item["state"] = self.container_state_mapping(self.instance.status)
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

        # config
        namespace_config = self.instance.config.get("namespace")
        namespace_item = {}
        if "cluster_name" in namespace_config:
            namespace_item["cluster_name"] = namespace_config.get("cluster_name")
            namespace_item["codice_ente"] = namespace_config.get("codice_ente")
            namespace_item["codice_prodotto"] = namespace_config.get("codice_prodotto")
            namespace_item["environment"] = namespace_config.get("environment")
            namespace_item["email_pm"] = namespace_config.get("email_pm")

            namespace_item["limit_cpu"] = namespace_config.get("limit_cpu")
            namespace_item["limit_memory"] = namespace_config.get("limit_memory")
            namespace_item["limit_storage"] = namespace_config.get("limit_storage")

            namespace_item["backup_policy"] = namespace_config.get("backup_policy")
            namespace_item["allowedHosts"] = namespace_config.get("allowedHosts")
            namespace_item["allowedHostPatterns"] = namespace_config.get("allowedHostPatterns")
            namespace_item["allowedCIDR"] = namespace_config.get("allowedCIDR")
            namespace_item["networkPolicyActive"] = namespace_config.get("networkPolicyActive")

            namespace_item["chartTargetRevision"] = namespace_config.get("chartTargetRevision")

        instance_item["namespace"] = namespace_item
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
        # # inner_data = json_cfg['namespace']

        container_id = self.get_config("container")
        # compute_zone = self.get_config("computeZone")

        account_id = self.instance.account_id
        apiAccount: ApiAccount = self.controller.get_account(account_id)

        service_definition: ApiServiceDefinition = self.instance.get_definition()
        
        cluster_name = self.get_config("namespace.cluster_name")
        codice_ente = self.get_config("namespace.codice_ente")
        codice_prodotto = self.get_config("namespace.codice_prodotto")
        environment = self.get_config("namespace.environment")
        backup_policy = self.get_config("namespace.backup_policy")
        networkPolicyActive = self.get_config("namespace.networkPolicyActive")
        email_pm: str = self.get_config("namespace.email_pm")

        self.logger.debug("pre_create - cluster_name: %s" % cluster_name)
        self.logger.debug("pre_create - codice_ente: %s" % codice_ente)
        self.logger.debug("pre_create - codice_prodotto: %s" % codice_prodotto)
        self.logger.debug("pre_create - environment: %s" % environment)
        self.logger.debug("pre_create - backup_policy: %s" % backup_policy)
        self.logger.debug("pre_create - networkPolicyActive: %s" % networkPolicyActive)
        self.logger.debug("pre_create - email_pm: %s" % email_pm)

        # self.set_config("namespace.chartTargetRevision", self.CHART_TARGET_REVISION_LAST)
        chartTargetRevisionLast = service_definition.get_config("chartTargetRevisionLast")
        self.set_config("namespace.chartTargetRevision", chartTargetRevisionLast)

        norescreate = self.get_config("namespace.norescreate")
        if norescreate is None:
            norescreate = False

        self.check_cluster_name(apiAccount, cluster_name)
        self.check_environment(service_definition, environment)

        # some checks are not required if create operation is from batch
        if not norescreate:
            self.check_codice_ente(self.controller, codice_ente)
            self.check_codice_prodotto(self.controller, codice_prodotto)

        if backup_policy is not None:
            self.check_backup_policy(service_definition, backup_policy)
        elif not norescreate:
            raise ApiManagerError("Backup_policy not valid: %s" % backup_policy)
        
        if networkPolicyActive is None:
            self.set_config("namespace.networkPolicyActive", True)

        if email_pm is None or email_pm.strip() == "":
            email_pm = apiAccount.email
            if email_pm is None or email_pm.strip() == "" and not norescreate:
                raise ApiManagerError("Email pm not valid: %s" % email_pm)
            else:
                self.set_config("namespace.email_pm", email_pm)

        if not norescreate:
            limit_cpu: str = self.get_config("namespace.limit_cpu")
            limit_memory: str = self.get_config("namespace.limit_memory")
            limit_storage: str = self.get_config("namespace.limit_storage")

            if limit_cpu is None or limit_cpu.strip() == "":
                raise ApiManagerError("limit_cpu mandatory: %s" % limit_cpu)
            if limit_memory is None or limit_memory.strip() == "":
                raise ApiManagerError("limit_memory mandatory: %s" % limit_memory)
            if limit_storage is None or limit_storage.strip() == "":
                raise ApiManagerError("limit_storage mandatory: %s" % limit_storage)

        # name = params["name"]
        # desc = params["desc"]

        namespace = self.get_config("namespace")
        data = {
            # "compute_zone": compute_zone,
            "container": container_id,
            # "desc": desc,
            # "name": name,
            "namespace": namespace,
            "organization": self.get_config("organization"),
            "division": self.get_config("division"),
            "account": self.get_config("account"),
            "norescreate": norescreate,
        }
        params["resource_params"] = data
        self.logger.debug("pre_create - resource_params: %s" % obscure_data(deepcopy(params)))

        params["id"] = self.instance.oid

        self.logger.debug("pre_create - end")
        return params

    def pre_update(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        self.logger.debug('pre_update - begin')
        self.logger.debug('pre_update - params {}'.format(params))

        container_id = self.get_config("container")
        # compute_zone = self.get_config("computeZone")

        account_id = self.instance.account_id
        apiAccount: ApiAccount = self.controller.get_account(account_id)

        service_definition: ApiServiceDefinition = self.instance.get_definition()
        
        cluster_name = dict_get(params, "namespace.cluster_name")
        codice_ente = dict_get(params, "namespace.codice_ente")
        codice_prodotto = dict_get(params, "namespace.codice_prodotto")
        environment = dict_get(params, "namespace.environment")
        email_pm = dict_get(params, "namespace.email_pm")

        limit_cpu = dict_get(params, "namespace.limit_cpu")
        limit_memory = dict_get(params, "namespace.limit_memory")
        limit_storage = dict_get(params, "namespace.limit_storage")

        backup_policy = dict_get(params, "namespace.backup_policy")
        allowedHosts = dict_get(params, "namespace.allowedHosts")
        allowedHostPatterns = dict_get(params, "namespace.allowedHostPatterns")
        allowedCIDR = dict_get(params, "namespace.allowedCIDR")
        networkPolicyActive = dict_get(params, "namespace.networkPolicyActive")

        chartTargetRevision = dict_get(params, "namespace.chartTargetRevision")

        self.logger.debug("pre_update - cluster_name: %s" % cluster_name)
        self.logger.debug("pre_update - codice_prodotto: %s" % codice_prodotto)
        self.logger.debug("pre_update - environment: %s" % environment)
        self.logger.debug("pre_update - backup_policy: %s" % backup_policy)
        self.logger.debug("pre_update - networkPolicyActive: %s" % networkPolicyActive)
        self.logger.debug("pre_update - chartTargetRevision: %s" % chartTargetRevision)

        norescreate = dict_get(params, "namespace.norescreate")
        if norescreate is None:
            norescreate = False

        self.modified = False

        if cluster_name is not None:
            self.check_cluster_name(apiAccount, cluster_name)
        if backup_policy is not None:
            self.check_backup_policy(service_definition, backup_policy)

        # some checks are not required if updates comes from batch
        if not norescreate:
            if codice_prodotto is not None:
                self.check_codice_prodotto(self.controller, codice_prodotto)
            # if environment is not None:
            #     self.check_environment(service_definition, environment)

            chartTargetRevisionCurrent = self.get_config("namespace.chartTargetRevision")
            chartTargetRevisionUpdateFrom = service_definition.get_config("chartTargetRevisionUpdateFrom")
            if chartTargetRevisionCurrent is None:
                raise ApiManagerError("Update not allowed for namespace with chartTargetRevision empty")
            elif chartTargetRevisionCurrent < chartTargetRevisionUpdateFrom:
                raise ApiManagerError("Update not allowed for namespace with chartTargetRevision: %s" % (chartTargetRevisionCurrent))
            
            # update application to the last version
            chartTargetRevisionLast = service_definition.get_config("chartTargetRevisionLast")
            if chartTargetRevision is None and chartTargetRevisionCurrent != chartTargetRevisionLast:
                chartTargetRevision = chartTargetRevisionLast

        # update config
        if cluster_name is not None:
            self.update_config("namespace.cluster_name", cluster_name)
        if codice_ente is not None:
            self.update_config("namespace.codice_ente", codice_ente)        
        if codice_prodotto is not None:
            self.update_config("namespace.codice_prodotto", codice_prodotto)
        if environment is not None:
            self.update_config("namespace.environment", environment)
        if email_pm is not None:
            self.update_config("namespace.email_pm", email_pm)

        if limit_cpu is not None:
            self.update_config("namespace.limit_cpu", limit_cpu)
        if limit_memory is not None:
            self.update_config("namespace.limit_memory", limit_memory)
        if limit_storage is not None:
            self.update_config("namespace.limit_storage", limit_storage)

        if backup_policy is not None:
            self.update_config("namespace.backup_policy", backup_policy)

        if allowedHosts is not None:
            self.update_config("namespace.allowedHosts", allowedHosts)
        if allowedHostPatterns is not None:
            self.update_config("namespace.allowedHostPatterns", allowedHostPatterns)
        if allowedCIDR is not None:
            self.update_config("namespace.allowedCIDR", allowedCIDR)

        if networkPolicyActive is not None:
            self.update_config("namespace.networkPolicyActive", networkPolicyActive)

        if chartTargetRevision is not None:
            self.update_config("namespace.chartTargetRevision", chartTargetRevision)

        if not self.modified:
            raise ApiManagerError("No changes to namespace: %s - %s" % (self.instance.uuid, self.instance.name))

        # set param for update_resource
        namespace = self.get_config("namespace")

        account = self.controller.get_account(self.instance.account_id)
        # get parent division
        div = self.controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org = self.controller.manager.get_entity(Organization, div.organization_id)
    
        data = {
            # "compute_zone": compute_zone,
            "container": container_id,
            # "desc": desc,
            # "name": name,
            "namespace": namespace,
            # "organization": self.get_config("organization"),
            # "division": self.get_config("division"),
            # "account": self.get_config("account"),
            "organization": org.name,
            "division": div.name,
            "account": account.name,
            "norescreate": norescreate,
        }
        params["resource_params"] = data
        self.logger.debug("pre_update - resource_params: %s" % obscure_data(deepcopy(params)))

        self.logger.debug("pre_update - end")
        return params
    
    def update_config(self, attr_key, attr_value):
        old_value = self.get_config(attr_key)
        if old_value != attr_value:
            self.set_config(attr_key, attr_value)
            self.modified = True
    
    def post_update(self, **params):
        self.logger.debug('post_update - begin')
        self.logger.debug('post_update - params {}'.format(params))
        self.logger.debug('post_update - end')

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.logger.debug("pre_delete - begin")
        self.logger.debug("pre_delete - params {}".format(params))

        chartTargetRevisionCurrent = self.get_config("namespace.chartTargetRevision")
        service_definition: ApiServiceDefinition = self.instance.get_definition()
        chartTargetRevisionUpdateFrom = service_definition.get_config("chartTargetRevisionUpdateFrom")
        if chartTargetRevisionCurrent is None:
            raise ApiManagerError("Delete not allowed for namespace with chartTargetRevision empty")
        elif chartTargetRevisionCurrent < chartTargetRevisionUpdateFrom:
            raise ApiManagerError("Delete not allowed for namespace with chartTargetRevision: %s" % (chartTargetRevisionCurrent))

        container_id = self.get_config("container")

        noresdelete = dict_get(params, "noresdelete")
        if noresdelete is None:
            noresdelete = False

        namespace = self.get_config("namespace")
        data = {
            "container": container_id,
            "namespace": namespace,
            "noresdelete": noresdelete,
        }
        params["resource_params"] = data
        self.logger.debug("pre_delete - resource_params: %s" % obscure_data(deepcopy(params)))

        params["id"] = self.instance.oid

        self.logger.debug("pre_delete - end")
        return params
    
    # ***
    # utility check
    # ***
    def check_cluster_name(self, apiAccount: ApiAccount, cluster_name):
        b_cluster_name_found = False
        cluster_set, total = apiAccount.get_definitions(plugintype="VirtualService", size=-1)
        for def_cluster in cluster_set:
            apiServiceDefinition: ApiServiceDefinition = def_cluster
            def_name: str = apiServiceDefinition.name
            if def_name.find("namespace.cluster.") != 0:
                continue
            
            def_cluster_name = apiServiceDefinition.get_config("cluster_name")
            if def_cluster_name == cluster_name:
                b_cluster_name_found = True
        
        if b_cluster_name_found is False:
            raise ApiManagerError("Cluster name not valid: %s" % cluster_name)

    def check_codice_ente(self, controller: ServiceController, codice_ente):
        # def_codice_ente = None
        # try:
        #     def_codice_ente_name = "CODENTE--%s" % codice_ente
        #     def_codice_ente = controller.get_service_def(def_codice_ente_name)
        # except Exception as ex:
        #     controller.logger.error(ex, exc_info=True)

        # if not def_codice_ente:
        if codice_ente is None or codice_ente.strip() == "":
            raise ApiManagerError("Codice ente not valid: %s" % codice_ente)
        
    def check_codice_prodotto(self, controller: ServiceController, codice_prodotto):
        def_codice_prodotto = None
        try:
            def_codice_prodotto_name = "CODPROD--%s" % codice_prodotto
            def_codice_prodotto = controller.get_service_def(def_codice_prodotto_name)
        except Exception as ex:
            controller.logger.error(ex, exc_info=True)

        if not def_codice_prodotto:
            raise ApiManagerError("Codice prodotto not valid: %s" % codice_prodotto)
        
    def check_environment(self, service_definition: ApiServiceDefinition, environment):
        b_environment_found = False
        def_environments = service_definition.get_config("environments")
        for def_environment in def_environments:
            if def_environment == environment:
                b_environment_found = True

        if b_environment_found is False:
            raise ApiManagerError("environment not valid: %s" % environment)
        
    def check_backup_policy(self, service_definition: ApiServiceDefinition, backup_policy):
        b_backup_policy_found = False
        def_backup_policies = service_definition.get_config("backup_policies")
        for def_backup_policy in def_backup_policies:
            if def_backup_policy == backup_policy:
                b_backup_policy_found = True

        if b_backup_policy_found is False:
            raise ApiManagerError("Backup policy not valid: %s" % backup_policy)

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
        self.logger.debug('create_resource - begin')
        resource_params = args[0]
        self.logger.debug('create_resource - resource_params: {}'.format(resource_params))

        # compute_zone = args[0].get("compute_zone")
        container = resource_params.get("container")
        namespace = resource_params.get("namespace")
        self.manage_resource(resource_params, namespace)

        self.logger.debug("create_resource - end")
        return None

    def update_resource(self, task, **kvargs):
        """update resource and wait for result
        this function must be called only by a celery task ok any other asyncronuos environment

        :param task: the task which is calling the  method
        :param size: the size  to resize
        :param dict kwargs: unused only for compatibility
        :return:
        """
        self.logger.debug("update_resource - begin")
        self.logger.debug('update_resource - kvargs: {}'.format(kvargs))

        namespace = kvargs.get("namespace")
        self.manage_resource(kvargs, namespace)

        return True
    
    def basic_auth(self, username, password):
        from base64 import b64encode
        token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return f'Basic {token}'
    
    def add_authorization(self, headers: dict):
        username = "ns-user" 
        password = "Pdcp44ns!"
        headers.update({
            "Authorization": self.basic_auth(username, password)
        })

    def manage_resource(self, resource_params, namespace):
        self.logger.debug("manage_resource - namespace: %s" % namespace)

        if "norescreate" in resource_params:
            norescreate = resource_params["norescreate"]
        else:
            norescreate = False

        if norescreate:
            self.logger.info("manage_resource - no calls to ns-provisioning-api")
            return
            
        # create namespace calling ns-provisioning-api
        try:
            user_data = self.get_user()
            user = user_data.get("user")
            msg_commit = "%s CMP %s commit" % (self.instance.name, user)

            data = {
                "msg_commit": msg_commit,
                "cluster_name": namespace.get("cluster_name"),
                # cluster_id":  | None = None
                # project_id":  | None = None
                "codice_prodotto": namespace.get("codice_prodotto"),
                "codice_ente": namespace.get("codice_ente"),
                "ambiente": namespace.get("environment"),

                "limit_cpu": namespace.get("limit_cpu"),
                "limit_memory": namespace.get("limit_memory"),
                "storage": namespace.get("limit_storage"),

                "backup_policy": namespace.get("backup_policy"),
                "networkPolicyActive": namespace.get("networkPolicyActive"),
                "pm_mail": namespace.get("email_pm"),

                "organizzazione": resource_params.get("organization"), # aaa
                "divisione": resource_params.get("division"),
                "account": resource_params.get("account"),
            }

            # network
            allowedHosts: str = dict_get(namespace, "allowedHosts")
            allowedHostPatterns: str = dict_get(namespace, "allowedHostPatterns")
            allowedCIDR: str = dict_get(namespace, "allowedCIDR")

            data_allowedHosts = []
            if allowedHosts is not None and allowedHosts.strip() != "":
                data_allowedHosts = allowedHosts.split(",")

            data_allowedHostPatterns = []
            if allowedHostPatterns is not None and allowedHostPatterns.strip() != "":
                data_allowedHostPatterns = allowedHostPatterns.split(",")

            data_allowedCIDR = []
            if allowedCIDR is not None and allowedCIDR.strip() != "":
                data_allowedCIDR = allowedCIDR.split(",")

            data.update({
                "allowedHosts": data_allowedHosts,  # List[str] | None = []
                "allowedHostPatterns": data_allowedHostPatterns,     # List[str] | None = []
                "allowedCIDR": data_allowedCIDR,     # List[str] | None = []
            })

            import os
            ns_host: str = os.getenv("NS_PROVISIONING_API_CLUSTERIP_SERVICE_HOST")
            ns_port: str = os.getenv("NS_PROVISIONING_API_CLUSTERIP_SERVICE_PORT")
            self.logger.info("manage_resource - ns_host: %s" % ns_host)
            self.logger.info("manage_resource - ns_port: %s" % ns_port)

            json_data = jsonDumps(data)
            self.logger.info("manage_resource - json_data: %s" % json_data)

            if ns_host is None or ns_host.strip() == "":
                self.logger.error("manage_resource - NS_PROVISIONING_API service not found")
                raise ApiManagerError("NS_PROVISIONING_API service not found") 
                # return

            headers = {
                "Accept": "application/json",
                "User-Agent": "beehive/1.0",
            }
            self.add_authorization(headers)
            
            conn = HTTPConnection(ns_host, ns_port, timeout=300)
            conn.set_debuglevel(1)
            conn.request("POST", "/create_namespace/", json_data, headers)

            response = conn.getresponse()
            content_type = response.getheader("content-type")
            self.logger.debug("manage_resource - response content_type: %s" % content_type)
            self.logger.debug("manage_resource - response.status: %s - response.reason: %s" % (response.status, response.reason))
            res = response.read()
            self.logger.debug("manage_resource - response res: %s" % res)
            if content_type is not None and content_type.find("application/json") >= 0:
                res_json = json.loads(res)
                if "return_code" in res_json:
                    return_code = res_json["return_code"]
                    self.logger.debug("manage_resource - return_code: %s" % return_code)

                    if return_code != 0:
                        if "push_su_git" in res_json:
                            push_su_git = res_json["push_su_git"]
                            self.update_status(SrvStatusType.ERROR, error=push_su_git)
                            raise ApiManagerError(res)
                        else:
                            self.update_status(SrvStatusType.ERROR, error=res)
                            raise ApiManagerError(res)
                else:
                    self.update_status(SrvStatusType.ERROR, error=res)
                    raise ApiManagerError(res)
            else:
                self.update_status(SrvStatusType.ERROR, error=res)
                raise ApiManagerError(res)

            if conn is not None:
                conn.close()

        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(ex)

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

        resource_params = args[0]
        namespace = resource_params.get("namespace")
        self.logger.debug("delete_resource - namespace: %s" % namespace)

        codice_prodotto = namespace.get("codice_prodotto")
        codice_ente = namespace.get("codice_ente")
        environment = namespace.get("environment")

        if "noresdelete" in resource_params:
            noresdelete = resource_params["noresdelete"]
        else:
            noresdelete = False

        if noresdelete:
            self.logger.info("delete_resource - no calls to ns-provisioning-api")
            return
            
        # create namespace calling ns-provisioning-api
        try:
            user_data = self.get_user()
            user = user_data.get("user")
            msg_commit = "%s CMP %s delete" % (self.instance.name, user)

            data = {
                "msg_commit": msg_commit,
                "pull": True,
            }
            import os
            ns_host: str = os.getenv("NS_PROVISIONING_API_CLUSTERIP_SERVICE_HOST")
            ns_port: str = os.getenv("NS_PROVISIONING_API_CLUSTERIP_SERVICE_PORT")
            self.logger.info("delete_resource - ns_host: %s" % ns_host)
            self.logger.info("delete_resource - ns_port: %s" % ns_port)

            json_data = jsonDumps(data)
            self.logger.info("delete_resource - json_data: %s" % json_data)

            if ns_host is None or ns_host.strip() == "":
                self.logger.error("delete_resource - NS_PROVISIONING_API service not found")
                raise ApiManagerError("NS_PROVISIONING_API service not found") 
                # return

            uri_delete = f"/namespace/{codice_prodotto}/{codice_ente}/{environment}"
            self.logger.info("delete_resource - uri_delete: %s" % uri_delete)

            headers = {
                "Accept": "application/json",
                "User-Agent": "beehive/1.0",
            }
            self.add_authorization(headers)
            
            conn = HTTPConnection(ns_host, ns_port, timeout=300)
            conn.set_debuglevel(1)
            conn.request("DELETE", uri_delete, json_data, headers)

            response = conn.getresponse()
            content_type = response.getheader("content-type")
            self.logger.debug("delete_resource - response content_type: %s" % content_type)
            self.logger.debug("delete_resource - response.status: %s - response.reason: %s" % (response.status, response.reason))
            res = response.read()
            self.logger.debug("delete_resource - response res: %s" % res)
            if content_type is not None and content_type.find("application/json") >= 0:
                res_json = json.loads(res)
                if "return_code" in res_json:
                    return_code = res_json["return_code"]
                    self.logger.debug("delete_resource - return_code: %s" % return_code)

                    if return_code != 0:
                        if "push_su_git" in res_json:
                            push_su_git = res_json["push_su_git"]
                            self.update_status(SrvStatusType.ERROR, error=push_su_git)
                            raise ApiManagerError(res)
                        elif "msg_error" in res_json:
                            msg_error = res_json["msg_error"]
                            self.update_status(SrvStatusType.ERROR, error=msg_error)
                            raise ApiManagerError(msg_error)
                        else:
                            self.update_status(SrvStatusType.ERROR, error=res)
                            raise ApiManagerError(res)
                else:
                    self.update_status(SrvStatusType.ERROR, error=res)
                    raise ApiManagerError(res)
            else:
                self.update_status(SrvStatusType.ERROR, error=res)
                raise ApiManagerError(res)

            if conn is not None:
                conn.close()
        
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(ex)
        
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

        self.logger.debug("action_resource - end")
        return True
