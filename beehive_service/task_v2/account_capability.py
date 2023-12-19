# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
from time import sleep
from beehive.common.apimanager import ApiObject, ApiManagerError
from beehive_service.controller import (
    ApiAccount,
    ApiAccountCapability,
    ServiceController,
)
from beehive_service.model import Account
from beehive_service.model import SrvStatusType
from beehive.common.task_v2 import TaskError, task_step, run_sync_task
from beehive.common.task_v2.manager import task_manager
from typing import List, Type, Tuple, Any, Union, Dict
from .servicetask import ServiceTask


logger = logging.getLogger(__name__)


class CAPABILITY_TASK_SETTINGS(object):
    RETRY_CONTDOWN = 60
    RETRY_MAX = 99


class AddAccountCapabilityTask(ServiceTask):
    name = "add_account_capability"
    inner_type = "TASK"
    prefix = "celery-task-shared-"
    prefix_stack = "celery-task-stack-"
    expire = 3600
    entity_class: ApiObject = ApiAccount
    controller = None
    _current_capability = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = CAPABILITY_TASK_SETTINGS.RETRY_MAX
        self.default_retry_delay = CAPABILITY_TASK_SETTINGS.RETRY_CONTDOWN
        # self.steps = [
        #     AddAccountCapabilityTask.step_wait_if_building,
        #     AddAccountCapabilityTask.step_add_capability,
        #     AddAccountCapabilityTask.step_set_capability_status,
        # ]

    def get_account_and_capability(self, account_id, capability_id) -> Tuple[ApiAccount, ApiAccountCapability]:
        """get account an capability for this task

        :return: ApiAccount, ApiAccountCapability
        """
        account = self.controller.get_entity(ApiAccount, Account, account_id)
        self.set_data("account", account)

        capability: ApiAccountCapability = self.controller.get_capability(capability_id)
        self.set_data("capability", capability)

        return account, capability

    # @staticmethod
    # @task_step()
    # def step_wait_if_building(task: ServiceTask, step_id: str, params: dict, *args, **kvargs):
    #     """
    #     step 0:
    #     Check if there is no other capability for the account which is  in building status.
    #     if ok set this capability as building
    #
    #     :param options: input options
    #     :param data  dictionary {"capability", "uuid"}
    #     :return:
    #     """
    #     # get account and services list
    #     account, capability = task.get_account_and_capability(task, params)
    #
    #     # set account for next steps
    #     task.set_data('account', account)
    #     if not account.set_capability_building_only_if_none_building(capability.oid):
    #         task.logger.debug('Retry next search for account %s' % account.uuid)
    #         task.retry(countdown=CAPABILITY_TASK_SETTINGS.RETRY_CONTDOWN)
    #     return True, params

    def __get_creation_order(self, item_list: List[dict]) -> List[List[dict]]:
        """Analyze the list of services an their pre-requirement and produce the order in which they must be created
        :param item_list: a list of service description  dictionary [{'name':.., 'type':.., 'template':.., 'params': {},
                                                                      'require':{'name':.., 'type':..}, {},]
        :return: list of lists of nodes containing  the services definition in c
        """
        visit: List[List[dict]] = []
        nodes: List[dict] = []

        def find_service(service_name: str, service_type: str) -> Union[None, dict]:
            """
             serch for service in item_list
            :param service_name: string service name
            :param service_type: string service type
            :return:
            """
            for n in nodes:
                if n["data"].get("name", "") == service_name and n["data"].get("type", "") == service_type:
                    return n
            return None

        # create node for each service
        for service in item_list:
            node = {
                "dependant": [],  # the list of dependant services
                "required": None,  # the
                "data": service,  # the service definition
            }
            nodes.append(node)

        for node in nodes:
            req = node["data"].get("require", None)
            if req is not None:
                s = find_service(req["name"], req["type"])
                if s is not None:
                    node["required"] = s
                    node["required"]["dependant"].append(node)

        # roots level 0 the first services to be created
        level = []
        # the services in the levels
        level_item = []
        for node in nodes:
            if node["required"] is None:
                level.append(node)
                level_item.append(node["data"])
        # visit.append(level)
        visit.append(level_item)
        cursor = level

        while len(cursor) > 0:
            level = []
            level_item = []
            for r in cursor:
                for s in r["dependant"]:
                    level.append(s)
                    level_item.append(s["data"])
            if len(level) > 0:
                # visit.append(level)
                visit.append(level_item)
            cursor = level

        return visit

    # def add_service(self, step_id, account: ApiAccount, capability: ApiAccountCapability, service_description: dict) \
    #         -> bool:
    #     """
    #     Add service described by descripton to acccount
    #     :param task:
    #     :param account:
    #     :param capability:
    #     :param service_description: service description {'name':.., 'type':.., 'template':.., 'params': {},
    #                                                      'require':{'name':.., 'type':..}
    #     :return bool:
    #     """
    #     response = 'Create service %s for account %s' % (service_description['name'], account.name)
    #     account.add_service(service_description, syncrounous=True, parent_task=self)
    #
    #     return True

    def __get_service_state(self, uuid):
        try:
            service_inst = self.controller.get_service_instance(uuid)
            state = service_inst.status
            return state
        except:
            return None

    def __wait_for_service(self, uuid, delta=2, accepted_state=SrvStatusType.ACTIVE, maxtime=1200):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta: second between checks on service status
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """
        state = self.__get_service_state(uuid)
        elapsed = 0
        while state not in [SrvStatusType.ACTIVE, SrvStatusType.ERROR, "TIMEOUT"]:
            self.progress(msg="Wait for service %s" % uuid)
            sleep(delta)
            state = self.__get_service_state(uuid)
            elapsed += delta
            if elapsed > maxtime and state != accepted_state:
                state = "TIMEOUT"

        if state == SrvStatusType.ERROR:
            self.progress(msg="Wait for service %s - ERROR" % uuid)
            raise TaskError("Wait for service %s got error" % uuid)
        if state == "TIMEOUT":
            self.progress(msg="Wait for service %s - TIMEOUT" % uuid)
            raise TaskError("Wait for service %s got timeout" % uuid)

        self.progress(msg="Wait for service %s - STOP" % uuid)

    def __check_template(self, plugintype, template):
        if template is None:
            return None

        # get service def
        service_def, tot = self.controller.get_paginated_service_defs(
            plugintype=plugintype, filter_expired=False, name=template
        )

        if tot < 1 or tot > 1:
            raise TaskError("Error retrieving service definition %s - plugintype: %s" % (template, plugintype))

        return service_def[0].uuid

    def __create_core_service(self, account, name, service_definition_id):
        """Create core service in account capability

        :param name: service name
        :param service_definition_id: service definition id
        :return:
        """
        desc = "Account service %s" % name
        plugin = self.controller.add_service_type_plugin(
            service_definition_id,
            account.oid,
            name=name,
            desc=desc,
            instance_config={},
            sync=True,
        )
        prepared_sync_task = getattr(plugin, "active_task", None)
        if prepared_sync_task is not None:
            run_sync_task(prepared_sync_task, self, self.current_step_id)
        self.progress(msg="create core service %s" % name)
        return plugin

    def __create_simple_service(self, account, plugintype, name, template=None, params=None):
        if params is None:
            params = {}
        service_factory = {
            "ComputeImage": self.controller.api_client.create_vpcaas_image,
            "ComputeVPC": self.controller.api_client.create_vpcaas_vpc,
            "ComputeSecurityGroup": self.controller.api_client.create_vpcaas_sg,
            "ComputeSubnet": self.controller.api_client.create_vpcaas_subnet,
            "NetworkHealthMonitor": self.controller.api_client.create_netaas_health_monitor,
            "NetworkListener": self.controller.api_client.create_netaas_listener,
        }

        func = service_factory.get(plugintype)
        service_inst_uuid = func(account=str(account.oid), name=name, template=template, **params)
        self.__wait_for_service(service_inst_uuid)
        return service_inst_uuid

    def __exist_service_instance(self, account, plugintype, name):
        # get service inst
        service_inst, tot = self.controller.get_paginated_service_instances(
            plugintype=plugintype,
            filter_expired=False,
            account_id=account.oid,
            authorize=False,
            name=name,
        )
        if tot < 1:
            self.logger.warning("Error retrieving service instance %s" % name)
            return None
        if tot > 1:
            self.logger.warning("Error retrieving service instance %s" % name)
            return service_inst[0]
        return service_inst[0]

    # def __check_service_instance(self, service_inst):
    #     if service_inst.status != SrvStatusType.ACTIVE:
    #         self.logger.warning('Service %s is not in the right status' % service_inst.name)
    #         return False
    #     return True

    def add_service(self, account, service):
        """Add account service

        :param account: account
        :param service: {
                'name':.., the service name to be created
                'type':..,  the service plugin type
                'template':.., the service definition to bi used
                'params': {}, additional parameters
                'require':{'name':.., 'type':..}
            } the required service : the parent service in a service hierarchical tree
        :return {'service': service_name, 'response': 'Add service %s' % service_inst_uuid}:
        """
        res = {}
        try:
            service_name = service.get("name")
            res["service"] = service_name

            service_type = service.get("type")
            service_template = service.get("template", None)
            service_params = service.get("params", {})
            service_require = service.get("require", {})
            service_require_name = service_require.get("name", None)
            service_require_type = service_require.get("type", None)

            # check service already exists and in correct status
            service_inst = self.__exist_service_instance(account, service_type, service_name)
            if service_inst is not None:
                if service_inst.status != SrvStatusType.ACTIVE:
                    # delete service if not active
                    type_plugin = service_inst.get_service_type_plugin()
                    type_plugin.delete(force=True, sync=True)
                    prepared_sync_task = getattr(type_plugin, "active_task", None)
                    if prepared_sync_task is not None:
                        run_sync_task(prepared_sync_task, self, self.current_step_id)
                    self.progress(msg="delete service %s" % service_name)
                else:
                    self.progress(msg="service %s already exists" % service_name)
                    # res['status'] = service_inst.status
                    # res['response'] = 'Already exists'
                    return res
                # if self.__check_service_instance(service_inst) is True:
                #     res['response'] = "Alredy exists"
                #     raise TaskError('Service %s already exists' % service_name)
                # raise TaskError('Service %s already exists and status is not valid' % service_name)

            # check service requirements are satisfied
            if service_require_name is not None:
                # synchronous wait for ServiceInstance' s status
                service_inst_parent = self.__exist_service_instance(account, service_require_type, service_require_name)
                if service_inst_parent is None:
                    self.progress(msg="required service %s does not exist" % service_require_name)
                    # res['status'] = SrvStatusType.ERROR
                    # res['response'] = 'required service %s does not exist' % service_require_name
                    return res
                elif service_inst_parent.status != SrvStatusType.ACTIVE:
                    self.progress(msg="required service %s is not active" % service_require_name)
                    # res['status'] = service_inst_parent.status
                    # res['response'] = 'required service %s is not active' % service_require_name
                    return res

            # create service
            self.logger.info("add_service - service_type: %s" % service_type)
            if service_type in [
                "ComputeService",
                "DatabaseService",
                "StorageService",
                "AppEngineService",
                "NetworkService",
                "LoggingService",
                "MonitoringService",
            ]:
                service_def = self.__check_template(service_type, service_template)
                plugin = self.__create_core_service(account, service_name, service_def)
            else:
                service_def = self.__check_template(service_type, service_template)
                self.__create_simple_service(
                    account,
                    service_type,
                    service_name,
                    template=service_def,
                    params=service_params,
                )

        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise TaskError("service %s creation error: %s" % (service.get("name"), str(ex)))
        return True

    def add_definitions(self, accont: ApiAccount, definitions: List[str]):
        for definition in definitions:
            try:
                apidefinition = self.controller.check_service_definition(definition)
                self.controller.add_account_service_definition(
                    accont.model.id,
                    apidefinition.model.id,
                    account=accont,
                    servicedefinition=apidefinition,
                )
            except Exception as ex:
                self.logger.warning(ex)
                pass

    def failure(self, params, error):
        # get account and capability
        try:
            account_id = params.get("account")
            account, capability = self.get_account_and_capability(account_id, self._current_capability)
            account.set_capability_status(capability.oid, SrvStatusType.ERROR_CREATION)
        except ApiManagerError as ex:
            if ex.code == 404:
                self.logger.warning(ex)
            else:
                raise

    @staticmethod
    @task_step()
    def step_add_capability(task, step_id: str, params: dict, capability_id: str, *args, **kvargs):
        """Step add  capability to account
        first aff all add service definitions if any to account  this operation does not involves
        any resource.
        Then services described by the capability are created.
        al the operations are idempotents so thaat capabilities that partialy overlaps can be added
        to the same account without errors.
        If the account already has the service or the serivce defintion nothing is created.


        :param task: parent celery task
        :param str step_id: step id
        :param str capability: capability
        :param dict params: step params
        :return: True, params
        """
        account_id = params.get("account")
        task._current_capability = capability_id
        account: ApiAccount
        capability: ApiAccountCapability
        account, capability = task.get_account_and_capability(account_id, capability_id)

        account.set_capability_status(capability.oid, SrvStatusType.BUILDING)

        # add account service definitions
        definitions = capability.definitions
        task.add_definitions(account, definitions)
        # add services
        services: List[dict] = capability.services

        task.progress(msg="capability services: %s" % services)
        ordered_services: List[List[dict]] = task.__get_creation_order(services)
        # ordered_services.reverse()
        for service_list in ordered_services:
            task.logger.warning(service_list)
        res = None
        for service_list in ordered_services:
            for service in service_list:
                task.progress(msg="Scheduling check for %s" % service["name"])
                # task.get_session(reopen=True)
                res = task.add_service(account, service)

        # set account status
        account, capability = task.get_account_and_capability(account_id, capability_id)
        account.set_capability_status(capability.oid, SrvStatusType.ACTIVE)
        task.progress(msg="Ready to Set capability status for account  %s" % account.name)

        return True, params


task_manager.tasks.register(AddAccountCapabilityTask())
