# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from gevent import sleep
from beehive.common.task.job import Job, JobTask, task_local, job_task, job, JobError
from beehive.common.task.util import end_task, start_task
from beehive.common.task.manager import task_manager
from beehive.common.data import operation
from beehive.common.apimanager import ApiManagerError, ApiManagerWarning
from beecell.simple import id_gen
from beehive_service.controller import ApiAccount
from beehive_service.model import Account
from beehive_service.model import SrvStatusType, ServiceJob as ServiceJobModel
from .common import MAX_CONCURRENT_TASKS_CELERY
from .metrics import AbstractServiceTask


class ACJobSettings(object):
    RETRY_CONTDOWN = 10
    RETRY_MAX = 99


class CapabilityJob(Job, AbstractServiceTask):
    """ServiceJob class. Use this class for task that execute create, update and delete of resources and childs.

    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    :example:

        .. code-block:: python

            @task_manager.task(bind=True, base=SeviceJob)
            @job(entity_class=OpenstackRouter, name='insert')
            def prova(self, objid, **kvargs):
                pass
    """

    abstract = True


class CapabilityJobTask(JobTask, AbstractServiceTask):
    """ServiceJobTask class. Use this class for task that execute create, update and delete of resources and childs.

    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    :example:

        .. code-block:: python

            @task_manager.task(bind=True, base=ServiceJobTask)
            @jobtask()
            def prova(self, options):
                pass
    """

    abstract = True
    throws = (ApiManagerError, ApiManagerWarning)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.

        :param exc: The exception raised by the task.
        :param task_id: Unique id of the failed task.
        :param args: Original arguments for the task that failed.
        :param kwargs: Original keyword arguments for the task that failed.
        :param einfo: ExceptionInfo instance, containing the traceback.
        :return: The return value of this handler is ignored.
        """
        JobTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        self.get_session()

        # get container
        module = self.app.api_manager.modules["ServiceModule"]
        controller = module.get_controller()

        job = controller.manager.get_service_job_by_task_id(task_id)
        if job is not None:
            job.status = "FAILURE"
            job.last_error = str(exc)
            controller.manager.update(job)

        self.call_callback(onfailure=True)

        self.release_session()

    def register_callback(self, callback=None, onfailure=True):
        """Register a callback collable in case of success or failure

        :param callback:  a closure to be called
        :param onfailure: if true call on failure otherwise call on success
        :return:
        """
        if onfailure:
            setattr(self, "CB_ON_FAIL_CLOSURE", callback)
        else:
            setattr(self, "CB_ON_SUCC_CLOSURE", callback)

    def call_callback(self, onfailure=True):
        """Search for registered callback and execute them

        :param onfailure: if true call an failure  call back otherwise call on success call back
        :return:
        """
        if onfailure:
            call_back = getattr(self, "CB_ON_FAIL_CLOSURE", None)
        else:
            call_back = getattr(self, "CB_ON_SUCC_CLOSURE", None)
        if callable(call_back):
            call_back()

    def on_success(self, retval, task_id, args, kwargs):
        """Run by the worker if the task executes successfully.

        :param retval: The return value of the task.
        :param task_id: Unique id of the executed task.
        :param args: Original arguments for the executed task.
        :param kwargs: Original keyword arguments for the executed task.
        :return:
        """
        JobTask.on_success(self, retval, task_id, args, kwargs)
        self.get_session()

        # get container
        module = self.app.api_manager.modules["ServiceModule"]
        controller = module.get_controller()
        controller.logger = self.logger

        job = controller.manager.get_service_job_by_task_id(task_id)
        if job is not None and job.status != "FAILURE":
            job.status = "SUCCESS"
            controller.manager.update(job)
        self.call_callback(onfailure=False)

        self.release_session()

    def persist_job(self, name="", account_id=None, data=None):
        # open db session
        # self.get_session()

        module = self.app.api_manager.modules["ServiceModule"]
        controller = module.get_controller()

        # persist job_tasks
        job_record = ServiceJobModel(
            objid=id_gen(),
            job=task_local.opid,
            name=name,
            account_id=account_id,
            task_id=self.request.id,
            params=data,
        )
        controller.manager.add(job_record)

        return job_record

    def get_service_state(self, uuid):
        try:
            self.controller.emptytransaction()
            service_inst = self.controller.get_service_instance(uuid)
            state = service_inst.status
            # self.progress(u'Get service %s status: %s' % (uuid, state))
            return state
        except Exception:
            return "DELETED"

    def wait_for_service(self, uuid, delta=5, accepted_state=SrvStatusType.ACTIVE, maxtime=600):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta:
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """
        self.get_session(reopen=True)
        self.progress("Wait for service %s - START" % uuid)

        TIMEOUT = "TIMEOUT"

        state = self.get_service_state(uuid)
        elapsed = 0
        while state not in [
            SrvStatusType.ACTIVE,
            SrvStatusType.ERROR,
            SrvStatusType.DELETED,
            TIMEOUT,
        ]:
            self.progress("Wait for service %s" % uuid)
            sleep(delta)
            state = self.get_service_state(uuid)
            elapsed += delta
            if elapsed > maxtime and state != accepted_state:
                state = TIMEOUT

        if state == SrvStatusType.ERROR:
            self.progress("Wait for service %s - ERROR" % uuid)
            raise JobError("Wait for service %s got error" % uuid)
        if state == TIMEOUT:
            self.progress("Wait for service %s - TIMEOUT" % uuid)
            raise JobError("Wait for service %s got timeout" % uuid)

        self.progress("Wait for service %s - STOP" % uuid)


def get_creation_order(item_list):
    """Analyze the list of services an their pre-requirement and produce the order in which they must be created

    :param item_list: a list of service description  dictionary [{u'name':.., u'type':.., u'template':.., u'params': {},
                                                                  u'require':{u'name':.., u'type':..}, {},]
    :return: list of lists of nodes containing  the services definition in c
    """
    visit = []
    nodes = []

    def find_service(service_name, service_type):
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


@task_manager.task(bind=True, base=CapabilityJobTask)
@job_task()
def task_add_service(self, options, data):
    """Add service (service_description) to account_id

    :param options: input params
    :param data: input data
    :param data.uuid: account uuid
    :param data.service: service description {u'name':.., u'type':.., u'template':.., u'params': {},
                                              u'require':{u'name':.., u'type':..}
    :shared_area: shared task data
    :param shared_area.capability:
    :return:
    """
    # open db session
    self.get_session(reopen=True)
    self.set_operation_perms(self.get_super_admin_perms())

    if not getattr(operation, "id", False):
        operation.id = id_gen()

    # disable authorization stuff
    operation.authorize = False

    service_description = data.get("service", {})
    account_uuid = data.get("uuid", {})

    # get params from shared data
    params = self.get_shared_data()
    capability_oid = params.get("capability", None)
    service_name = service_description["name"]

    self.progress(
        "Create service %s  for  capability %s account uuid %s" % (service_name, capability_oid, account_uuid)
    )

    # get container
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    account = controller.get_entity(ApiAccount, Account, account_uuid)

    # persist job_tasks
    # self.persist_job(name=u'AddService.%s' % service_name, account_id=account.model.id, data=data)

    if capability_oid is not None:
        #  register on failure callback in order to set error status
        def callback():
            operation.authorize = False
            self.get_session()
            account = controller.get_entity(ApiAccount, Account, account_uuid)
            account.set_capability_status(capability_oid, SrvStatusType.ERROR_CREATION)
            self.release_session()

        self.register_callback(callback=callback, onfailure=True)

        # def succescallback():
        #     pass
        # self.register_callback(callback=succescallback, onfailure=False)

    response = "Create service %s for account  %s" % (
        service_description["name"],
        account.name,
    )
    self.progress(response)

    # no more result res=account.add_service(service_description)
    account.add_service(service_description, syncrounous=True, parent_task=self)

    return True


@task_manager.task(bind=True, base=CapabilityJobTask)
@job_task()
def task_set_capability_status(self, options, data):
    """Add service (service_description) to account_id

    :param options: input options
    :param data  dictionary {"capability", "uuid"}
    :return:
    """
    # open db session
    self.get_session()
    self.set_operation_perms(self.get_super_admin_perms())
    operation.authorize = False

    if not getattr(operation, "id", False):
        operation.id = id_gen()

    capability_oid = data.get("capability", None)
    uuid = data.get("uuid", {})

    self.logger.debug("Setting Capability  %s status  for account_id %s" % (capability_oid, uuid))

    self.progress("Start Setting Capability %s status for account uuid %s" % (capability_oid, uuid))

    # get business context
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    account = controller.get_entity(ApiAccount, Account, uuid)

    self.progress("Ready to Set capability status for account  %s" % account.name)

    account.set_capability_status(capability_oid, SrvStatusType.ACTIVE)

    # persist job_tasks
    # self.persist_job(name=u"SetCapabilityStatus", account_id=account.model.id, data=data)

    return 0


@task_manager.task(bind=True, base=CapabilityJobTask, max_retries=ACJobSettings.RETRY_MAX)
@job_task()
def task_wait_if_building(self, options, data):
    """Check if there is no other capability for the account which is  in building status.

    :param options: input options
    :param data  dictionary {"capability", "uuid"}
    :return:
    """
    # open db session deltatime = 10
    self.get_session()
    self.set_operation_perms(self.get_super_admin_perms())
    operation.authorize = False
    if not getattr(operation, "id", False):
        operation.id = id_gen()

    # get container
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    controller.logger = self.logger
    # # set params as shared data
    # params =self.get_shared_data()

    # get account and services list
    capability_oid = data.get("capability", None)
    account_uuid = data.get("uuid", None)

    self.logger.debug("search for account %s" % account_uuid)
    account = controller.get_entity(ApiAccount, Account, account_uuid)

    if account.set_capability_building_only_if_none_building(capability_oid):
        return
    else:
        self.logger.debug("Retry next search for account %s" % account_uuid)
        self.retry(countdown=ACJobSettings.RETRY_CONTDOWN)


@task_manager.task(bind=True, base=CapabilityJob)
@job(entity_class=ApiAccount, name="job_add_capability", delta=3)
def job_add_capability(self, account_id, params):
    """Init Account services. Add capability using task_wait_if_building

    :param account_id: account id
    :param params: input params
    """
    # open db session
    self.get_session()
    self.set_operation_perms(self.get_super_admin_perms())
    operation.authorize = False
    if not getattr(operation, "id", False):
        operation.id = id_gen()

    # get container
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    # controller.logger = self.logger
    # set params as shared data
    self.set_shared_data(params)

    self.logger.info("Set shared area")
    # get account and services list
    account_uuid = params.get("uuid", None)
    capability_oid = params.get("capability", None)

    self.logger.debug("search for account %s" % account_uuid)
    account = controller.get_entity(ApiAccount, Account, account_uuid)

    capability = self.controller.get_capability(capability_oid)

    services = capability.services

    self.logger.debug("Job Add   %s , %s Capability  %s" % (account_id, account.name, str(services)))
    ordered_services = get_creation_order(services)
    ordered_services.reverse()

    ops = self.get_options()

    tasks = [
        end_task,
        [
            task_set_capability_status.signature(
                (ops, {"uuid": account_uuid, "capability": capability_oid}),
                immutable=True,
                queue=task_manager.conf.TASK_DEFAULT_QUEUE,
            )
        ],
    ]

    for service_list in ordered_services:
        parallel_group = []
        for service in service_list:
            # self.update_job(u'PROGRESS', msg=u'Scheduling check for %s ' % service[u'name'])
            self.logger.debug("Scheduling check for %s " % service["name"])
            parallel_group.append(
                task_add_service.signature(
                    (ops, {"uuid": account_uuid, "service": service}),
                    immutable=True,
                    queue=task_manager.conf.TASK_DEFAULT_QUEUE,
                )
            )
            if len(parallel_group) >= MAX_CONCURRENT_TASKS_CELERY:
                self.logger.info("block of tasks n.%s" % (len(parallel_group) - 1))
                tasks.append(parallel_group)
                parallel_group = []
        tasks.append(parallel_group)

    tasks.append(
        [
            task_wait_if_building.signature(
                (ops, {"uuid": account_uuid, "capability": capability_oid}),
                immutable=True,
                queue=task_manager.conf.TASK_DEFAULT_QUEUE,
            )
        ]
    )
    tasks.append(start_task)

    Job.create(tasks, ops).delay()

    self.logger.info("Job init services launched for account %s" % account_uuid)
    return True


@task_manager.task(bind=True, base=CapabilityJob)
@job(entity_class=ApiAccount, name="job_add_capability", delta=3)
def job_add_capability_nowait(self, account_id, params):
    """Init Account services

    :param self:
    :param account_id: account id
    :param params:
    """
    # open db session
    self.get_session()
    self.set_operation_perms(self.get_super_admin_perms())
    operation.authorize = False
    if not getattr(operation, "id", False):
        operation.id = id_gen()

    # get container
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    # controller.logger = self.logger
    # set params as shared data
    self.set_shared_data(params)

    self.logger.info("Set shared area")
    # get account and services list
    account_uuid = params.get("uuid", None)
    capability_oid = params.get("capability", None)

    self.logger.debug("search for account %s" % account_uuid)
    account = controller.get_entity(ApiAccount, Account, account_uuid)

    account.set_capability_status(capability_oid, SrvStatusType.BUILDING)

    capability = self.controller.get_capability(capability_oid)

    services = capability.services

    self.logger.debug("Job Add   %s , %s Capability  %s" % (account_id, account.name, str(services)))

    ordered_services = get_creation_order(services)
    ordered_services.reverse()

    ops = self.get_options()

    tasks = [
        end_task,
        [
            task_set_capability_status.signature(
                (ops, {"uuid": account_uuid, "capability": capability_oid}),
                immutable=True,
                queue=task_manager.conf.TASK_DEFAULT_QUEUE,
            )
        ],
    ]

    for service_list in ordered_services:
        parallel_group = []
        for service in service_list:
            # self.update_job(u'PROGRESS', msg=u'Scheduling check for %s ' % service[u'name'])
            self.logger.debug("Scheduling check for %s " % service["name"])
            parallel_group.append(
                task_add_service.signature(
                    (ops, {"uuid": account_uuid, "service": service}),
                    immutable=True,
                    queue=task_manager.conf.TASK_DEFAULT_QUEUE,
                )
            )
            if len(parallel_group) >= MAX_CONCURRENT_TASKS_CELERY:
                self.logger.info("block of tasks n.%s" % (len(parallel_group) - 1))
                tasks.append(parallel_group)
                parallel_group = []

        tasks.append(parallel_group)

    tasks.append(start_task)

    Job.create(tasks, ops).delay()

    self.logger.info("Job init services launched for account %s" % account_uuid)
    return True


@task_manager.task(bind=True, base=CapabilityJob)
@job(entity_class=ApiAccount, name="job_init_account", delta=3)
def job_init_account(self, account_id, params):
    """Deprecato  use add_capability. Initialize Account services

    :param self: account id
    :param account_id: account id
    :param params: input params
    """
    # open db session
    self.get_session()
    self.set_operation_perms(self.get_super_admin_perms())

    if not getattr(operation, "id", False):
        operation.id = id_gen()
    operation.authorize = False
    # get container
    module = self.app.api_manager.modules["ServiceModule"]
    controller = module.get_controller()
    controller.logger = self.logger
    # set params as shared data
    self.set_shared_data(params)

    self.logger.info("Set shared area")
    # get account and services list
    account_uuid = params.get("uuid", None)

    capability_oid = params.get("capability", None)
    self.logger.debug(":get capability ::::: %s" % str(capability_oid))
    capability = controller.get_capability(capability_oid)
    services = getattr(capability, "params", {}).get("services", [])

    self.logger.debug("search for account %s" % account_uuid)
    account = controller.get_entity(ApiAccount, Account, account_uuid)

    self.logger.debug("Job Init account %s , %s services  %s" % (account_id, account.name, str(services)))

    ordered_services = get_creation_order(services)
    ordered_services.reverse()

    ops = self.get_options()

    tasks = [
        end_task,
        task_set_capability_status.signature(
            (ops, {"uuid": account_uuid, "capability": capability}),
            immutable=True,
            queue=task_manager.conf.TASK_DEFAULT_QUEUE,
        ),
    ]
    for service_list in ordered_services:
        parallel_group = []

        for service in service_list:
            self.update_job("PROGRESS", msg="Scheduling check for %s " % service["name"])
            parallel_group.append(
                task_add_service.signature(
                    (
                        ops,
                        {
                            "uuid": account_uuid,
                            "capability": capability_oid,
                            "service": service,
                        },
                    ),
                    immutable=True,
                    queue=task_manager.conf.TASK_DEFAULT_QUEUE,
                )
            )
            if len(parallel_group) >= MAX_CONCURRENT_TASKS_CELERY:
                self.logger.info("block of tasks n.%s" % (len(parallel_group) - 1))
                tasks.append(parallel_group)
                parallel_group = []

        tasks.append(parallel_group)
    tasks.append(start_task)
    Job.create(tasks, ops).delay()

    self.logger.info("Job init services launched for account %s" % account_uuid)
    return True
