# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.task.job import Job, JobTask, task_local, job_task, job
from beehive.common.task.util import end_task, start_task, join_task
from beehive_service.controller import ApiAccount, ApiServiceType
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.model import ServiceInstantConsume

from beehive.common.task.manager import task_manager
from datetime import datetime, timedelta, date
from dateutil import relativedelta
from beecell.simple import id_gen
from beehive.common.data import operation
from beehive_service.model import ServiceMetric, AggregateCost,\
    ServiceMetricConsumeView, AggregateCostType, SrvStatusType,\
    ServiceJob as ServiceJobModel, ServiceMetricType, ReportCost
from beehive.common.apimanager import ApiManagerWarning, ApiManagerError
from sqlalchemy.sql.expression import false
from beehive_service.service_util import ServiceUtil
from .common import logger, MAX_CONCURRENT_TASKS_CELERY


#
# ServiceJob
#
class AbstractServiceTask(object):
    def __init__(self, *args, **kwargs):
        Job.__init__(self, *args, **kwargs)

    def get_service_instance_by_account(self, account_id):
        """Get service instance by account id.

        :param int account_id: service account_id
        :return: ervice instance
        :raise ApiManagerError:
        """
        services = task_local.controller.get_service_instances(
            fk_account_id=account_id)
        return services

    def set_operation_perms(self, perms):
        operation.perms = perms

    def get_super_admin_perms(self,):
        # (0-pid, 1-oid, 2-type, 3-definition, 4-objid, 5-aid, 6-action)
        return [
            (1, 1, u'service', u'Organization', u'*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division', u'*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account', u'*//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance', u'*//*//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
             u'*//*//*//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
             u'*//*//*//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceLink', u'*//*//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceTag', u'*//*//*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceType', u'*', 1, u'*'),
            (1, 1, u'service', u'ServiceType.ServiceCostParam', u'*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceType.ServiceDefinition', u'*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceType.ServiceDefinition.ServiceConfig', u'*//*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceType.ServiceDefinition.ServiceLinkDef', u'*//*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceType.ServiceProcess', u'*//*', 1, u'*'),
            (1, 1, u'service', u'ServiceCatalog', u'*', 1, u'*'),
            (1, 1, u'service', u'AccountCapability', u'*', 1, u'*'),
        ]

    def get_account_master_perms(self, objid):
        # (0-pid, 1-oid, 2-type, 3-definition, 4-objid, 5-aid, 6-action)
        return [
            (1, 1, u'service', u'Organization.Division.Account', objid, 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance', objid + u'//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
             objid + u'//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
             objid + u'//*//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceLink', objid + u'//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceTag', objid + u'//*', 1, u'*'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceLink', u'*//*//*//*', 1, u'view'),
            (1, 1, u'service', u'Organization.Division.Account.ServiceTag', u'*//*//*//*', 1, u'view'),
            (1, 1, u'service', u'AccountCapability', u'*', 1, u'view'),
        ]


class ServiceJob(Job, AbstractServiceTask):
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


class ServiceJobTask(JobTask, AbstractServiceTask):
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
        self.get_session()

        # get container
        module = self.app.api_manager.modules[u'ServiceModule']
        controller = module.get_controller()

        job = controller.manager.get_service_job_by_task_id(task_id)
        if job is not None:
            job.status = u'FAILURE'
            job.last_error = str(exc)
            controller.manager.update(job)

        JobTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        # get params from shared data
        params = self.get_shared_data()
        self.get_session()

        self.logger.warn(u'params= %s' % params)
        self.logger.warn(exc)
        self.logger.warn(einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Run by the worker if the task executes successfully.

        :param retval: The return value of the task.
        :param task_id: Unique id of the executed task.
        :param args: Original arguments for the executed task.
        :param kwargs: Original keyword arguments for the executed task.
        :return:
        """
        self.get_session()

        # get container
        module = self.app.api_manager.modules[u'ServiceModule']
        controller = module.get_controller()
        controller.logger = self.logger

        job = controller.manager.get_service_job_by_task_id(task_id)
        if job is not None:
            if job.status != u'FAILURE':
                job.status = u'SUCCESS'

                controller.manager.update(job)
                return JobTask.on_success(self, retval, task_id, args, kwargs)


## acquiszione delle metriche o consumei istantanei
@task_manager.task(bind=True, base=ServiceJob)
@job(entity_class=ApiAccount, name=u'metrics.acquire', delta=2)
def acquire_service_metrics(self, objid, params):
    """Acquire instant service metrics

    :param str objid: resource objdef
    :param dict params input params
    :return: True
    """

    # open db session
    self.get_session()

    # get controller
    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    # set params as shared data
    self.logger.info(u'Get shared area')

    metric_num = params.get(u'metric_num')
    execution_date = datetime.today().replace(year=1970, month=1, day=1)

    if metric_num is None:
        task_interval = controller.get_task_intervals(
            execution_date=execution_date, task=u'acq_metric')
        if task_interval is not None and len(task_interval) > 0:
            metric_num = task_interval[0].task_num
            params[u'metric_num'] = metric_num
        else:
            metric_num = 0
            params[u'metric_num'] = metric_num
    self.logger.info(u'Acquire metric num: %s for date: %s' % (metric_num, execution_date))
    ops = self.get_options()

    res = {}

    if objid is not None and objid == u'*':
        objid = None

    # get accounts
    accounts, total_acc = controller.manager.get_accounts(objid=objid, size=0, with_perm_tag=False,
                                                          filter_expired=False, active=True)

    # make dict metric type {name: id}
    metric_types = controller.manager.get_service_metric_types()
    mtype = {mt.name: mt.id for mt in metric_types}

    params[u'mtype_dict'] = mtype
    self.set_shared_data(params)

    # prepare tasks for current job from bottom in reverse order
    serial_tasks = [end_task]
    serial_tasks.append(finalize_metrics_acquisition)

    # log job
    current_job = controller.add_job(task_local.opid, u'acquire_service_metrics', params)

    # prepare parallel tasks
    parallel_tasks = []
    self.logger.info(u'Get accounts total: %s' % total_acc)
    for account in accounts:
        params[u'account_id'] = account.id
        parallel_tasks.append(acquire_metrics_by_account.signature((ops, account.id, current_job.id), immutable=True,
                                                                   queue=task_manager.conf.TASK_DEFAULT_QUEUE))
        self.logger.info(
            u'Generate task for acquire metric for account %s' % account)
        if len(parallel_tasks) >= MAX_CONCURRENT_TASKS_CELERY:
            self.logger.info(u'block of tasks n.%s' % (len(serial_tasks)-1))
            serial_tasks.append(parallel_tasks)
            serial_tasks.append(join_task)
            parallel_tasks = []

    if len(parallel_tasks) > 0:
        serial_tasks.append(parallel_tasks)
        serial_tasks.append(join_task)

    serial_tasks.append(start_task)

    # create and start job workflow
    Job.create(serial_tasks, ops).delay()

    return res


##  calcolo dei consumi gionalieri e costi giornalieri
@task_manager.task(bind=True, base=ServiceJob)
@job(entity_class=ApiAccount, name=u'job_aggregate_costs', delta=2)
def generate_aggregate_costs(self, objid, params):
    """Generate aggregate costs entities

    :param str objid: resource objid
    :param dict params: input params
    :return: True
    """
    self.logger.info(u'job_aggregate_costs: start')
    self.logger.info(u'job_aggregate_costs params: %s' % params)
    # open db session
    self.get_session()
    operation.id = id_gen()

    # get controller
    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    aggregation_type = params.get(u'aggregation_type')
    # default  aggregation is daily
    if aggregation_type is None:
        aggregation_type = u'daily'

    # start_period = None
    # default period is yesterday
    period = params.get(u'period')
    if period is None:
        if u'daily' == aggregation_type:
            yesterday = date.today() - timedelta(days=1)
            start_period = yesterday
            period = yesterday.strftime(u"%Y-%m-%d")
        elif u'monthly' == aggregation_type:
            firstOfMonth = date.today().replace(day=1)
            lastmonth = firstOfMonth - relativedelta.relativedelta(months=1)
            start_period = lastmonth
            period = lastmonth.strftime(u"%Y-%m")
        params[u'period'] = period
    else:
        if u'daily' == aggregation_type:
            start_period = datetime.strptime(period, u'%Y-%m-%d')
        elif u'monthly' == aggregation_type:
            start_period = datetime.strptime(period+u'-01', u'%Y-%m')

    self.logger.info(u'Generate Aggregate costs %s for date: %s' % (aggregation_type, period))

    ops = self.get_options()

    if objid is not None and objid == u'*':
        objid = None
    params[u'period'] = period
    self.set_shared_data(params)

    # log job
    current_job = controller.add_job(task_local.opid, u'generate_aggregate_costs', params)

    # create and start job workflow
    if u'daily' == aggregation_type:
        serial_tasks = [
            end_task,
            [compute_daily_costs.signature((ops, period, current_job.id), immutable=True,
                                           queue=task_manager.conf.TASK_DEFAULT_QUEUE)],
            start_task]
        Job.create(serial_tasks, ops).delay()
    else:
        serial_tasks = [end_task, start_task]
        Job.create(serial_tasks, ops).delay()

    self.logger.info(u'job_aggregate_costs: end')
    return True


@task_manager.task(bind=True, base=ServiceJobTask)
@job_task(synchronous=False)
def acquire_metrics_by_account(self, options, account_id, current_job_id):
    """Acquire resource metrics by account.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param str account_id: account id
    :param current_job_id: current job id
    :dict sharedarea: input params
    :return:
    """
    self.progress(u'01 Get resource objdef %s' % account_id)

    # get params from shared data
    params = self.get_shared_data()
    self.progress(u'02 Get shared area')
    instance_id = params.get(u'service_instance_id')
    # open db session
    operation.perms = []
    self.get_session()

    # get container
    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    # job = ServiceJobModel(objid=id_gen(), job=task_local.opid, name=u"AcquireMetric", account_id=account_id,
    #                       task_id=self.request.id, params=params)
    # controller.manager.add(job)
    # job_id = job.id
    plugintype = params.get(u'plugintype', None)

    service_status_list_active = [
        SrvStatusType.STOPPING,
        SrvStatusType.STOPPED,
        SrvStatusType.ACTIVE,
        SrvStatusType.DELETING,
        SrvStatusType.UPDATING
    ]

    container_srvs, total = controller.get_paginated_service_instances(
        account_id=account_id,
        id=instance_id,
        plugintype=plugintype,
        flag_container=True,
        service_status_name_list=service_status_list_active,
        filter_expired=False,
        authorize=False, size=0)

    self.progress(u'03 Acquire metrics for %s instances on account %s and instance %s' %
                  (len(container_srvs), account_id, instance_id))

    metric_num = params.get(u'metric_num', 1)
    mtype = params.get(u'mtype_dict', {})

    metrics = []

    self.progress(u'01 Get resource quota on account %s' % account_id)

    for container in container_srvs:
        pluginContainer = ApiServiceType(controller).instancePlugin(None, container)
        metrics_resource = pluginContainer.acquire_metric(container.resource_uuid)
        self.progress(u'04 acquire metrics for container %s %s' % (container.uuid, container.name))

        for cs in metrics_resource:
            # for any metric find service_id association
            srv_id = container.oid
            plugin_type_id = None
            try:
                if cs.get(u'uuid', None) is not None:
                    inst_from_resource = controller.manager.get_service_instance(fk_account_id=account_id,
                                                                                 resource_uuid=cs.get(u'uuid'))
                    if inst_from_resource is None:
                        raise Exception(u'05 Resource %s has not service instance associated' % cs.get(u'uuid'))
                    self.progress((u'05 Resource %s has service instance %s associated' %
                                   (cs.get(u'uuid'), inst_from_resource.uuid)))

                    if inst_from_resource is not None:
                        srv_id = inst_from_resource.id

                        # search plugin_type id of instance
                        api_instance = ServiceUtil.instanceApi(controller, ApiServiceInstance, inst_from_resource)
                        plugin = api_instance.instancePlugin(None, inst=api_instance)
                        if plugin is not None:
                            plugin_type_id = plugin.model.plugintype.id

            except Exception as ex:
                logger.warn(ex)
                self.progress(u'05 No instance_id detected for resource %s ' % cs.get(u'uuid'))

            # SAVE metrics;
            for m in cs.get(u'metrics', []):
                # decode instance id from resource_uuid
                name = m.get(u'key')
                unit = m.get(u'unit')
                typem = m.get(u'type')
                metric_type_id = mtype.get(name, None)

                mtp = None
                # check if MetricType exist
                if metric_type_id is None:
                    # Insert new ServiceMetricType
                    objid = id_gen()
                    mtnew = ServiceMetricType(objid, name, typem,
                                              group_name=container.getPluginTypeName(),
                                              # desc=u'invalid metric type',
                                              measure_unit=unit)

                    metric_type_new = controller.add_service_metric_type_base(mtnew)
                    self.progress(u'06 Create new Metric Type %s %s' % (metric_type_new.name, metric_type_new.id))

                    metric_type_id = metric_type_new.id

                    new_mt_dict = {name: metric_type_id}
                    mtype.update(new_mt_dict)

                else:
                    # check if the association between metric_type and plugin_type exist
                    mtp = controller.manager.get_metric_type_plugin_type(plugin_type_id, metric_type_id)

                if mtp is None and plugin_type_id is not None and metric_type_id is not None:
                    # association between metric_type and plugin_type not found

                    # add association metric_type plugin_type
                    controller.add_metric_type_plugin_type(plugin_type_id, metric_type_id)
                else:
                    logger.warn(u'Params not found:  plugin_type_id=%s, metric_type_id=%s' %
                                (plugin_type_id, metric_type_id))

                metric = (m.get(u'value'), metric_type_id, metric_num, srv_id)
                metrics.append(metric)

    res = 0
    if len(metrics) > 0:
        self.progress(u'07 add metrics')

        # generate orm entities for metrics
        metrics = [ServiceMetric(value=m[0], metric_type_id=m[1], metric_num=m[2], service_instance_id=m[3],
                                 job_id=current_job_id) for m in metrics]

        # Insert aggregate cost batch
        self.get_session(reopen=True)
        controller.manager.bulk_save_entities(metrics)
        res = len(metrics)
        self.progress(u'07 add metrics: %s' % res)

    return res


@task_manager.task(bind=True, base=ServiceJobTask)
@job_task(synchronous=False)
def finalize_metrics_acquisition(self, options):
    """Finalize the metrics acquistion by computing the next acqusition id

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :str account: account id
    :dict sharedarea: input params
    :return:
    """

    # get params from shared data
    params = self.get_shared_data()
    self.progress(u'FinalizeMetricAcquisition 01 calling stored procedure')

    # open db session
    operation.perms = []
    self.get_session()

    # get container
    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    # job = ServiceJobModel(objid=id_gen(), job=task_local.opid, name=u"FinalizeMetricAcquisition", account_id=None,
    #                       task_id=self.request.id, params=params)
    # controller.manager.add(job)
    # job_id = job.id

    # self.get_session(reopen=True)
    controller.manager.call_smsmpopulate(10000)

    self.progress(u'FinalizeMetricAcquisition 02 done')

    return None


@task_manager.task(bind=True, base=ServiceJobTask)
@job_task(synchronous=False)
def compute_daily_costs(self, options, period, current_job_id):
    """Call stored procedure  dailyconsumes
    in order to compute daily consume and costs

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param period: period
    :param current_job_id: current job id
    :dict sharedarea: input params
    :return:
    """

    # get params from shared data
    params = self.get_shared_data()
    self.progress(u'ComputeDaily 01 calling stored procedure')

    # open db session
    operation.perms = []
    self.get_session()

    # get container
    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    # current_job = ServiceJobModel(objid=id_gen(), job=task_local.opid, name=u"ComputeDaily", account_id=None,
    #                               task_id=self.request.id, params=params)
    # controller.manager.add(job)

    controller.manager.call_dailyconsumes(period, current_job_id)

    return None


## non usato per ora forse per calcoi parziali
@task_manager.task(bind=True, base=ServiceJobTask)
@job_task(synchronous=False)
def generate_daily_consume_by_account(self, options, account_id):
    """Generate daily consumes by account.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :param str account_id: account id
    :dict sharedarea: input params
    :return: num of aggregate consume generated (num_aggr_consume)
    """
    self.progress(u'a. Generate Daily Consumes on account_id %s' % account_id)

    # get params from shared data
    params = self.get_shared_data()
    self.progress(u'b. Get shared area')

    # open db session
    operation.perms = []
    self.get_session()

    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    current_job = ServiceJobModel(objid=id_gen(), job=task_local.opid,
                          name=u"Daily_Comsumes",
                          account_id=account_id,
                          task_id=self.request.id,
                          params=params)
    controller.manager.add(current_job)

    period = params.get(u'period')

    controller.manager.call_dailyconsumes_by_account(account_id, period, current_job.id)
    return None

## non usato per ora forse per calcoi parziali
@task_manager.task(bind=True, base=ServiceJobTask)
@job_task(synchronous=False)
def generate_daily_costs(self, options):
    """Generate daily consumes by account.

    :param tupla options: Task config params. (class_name, objid, job, job id, start time, time before new query, user)
    :str account_id: account id
    :dict sharedarea: input params
    :return: num of aggregate consume generated (num_aggr_consume)
    """

    operation.perms = []
    self.get_session()

    # get params from shared data
    params = self.get_shared_data()
    period = params.get(u'period')

    self.progress(u'a. Generate Daily Costs for  %s' % period)

    module = self.app.api_manager.modules[u'ServiceModule']
    controller = module.get_controller()

    currentjob = ServiceJobModel(objid=id_gen(), job=task_local.opid, name=u"Daily_Costs",
                                 account_id=None, task_id=self.request.id, params=params)
    controller.manager.add(currentjob)

    controller.manager.call_dailycosts(period, currentjob.id)
    return None
