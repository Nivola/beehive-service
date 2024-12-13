# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from .servicetask import ServiceTask
from beehive_service.controller import ServiceController, ApiAccount
from beehive_service.model import ServiceJob, Account, ServiceInstance
from beehive_service.entity.service_type import ApiServiceTypeContainer
from beehive.common.task.job import task_local
from beehive_service.controller import ApiServiceType
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive.common.task_v2 import task_step
from beehive.common.task_v2.manager import task_manager
from datetime import datetime, timedelta, date
from beecell.simple import id_gen
from beehive_service.model import ServiceMetric, SrvStatusType, ServiceMetricType
from beehive_service.service_util import ServiceUtil
from typing import List, Type, Tuple, Any, Union, Dict


#
# Metrics And Consumes Tasks
#
class AcquireMetricTask(ServiceTask):
    entity_class = ApiAccount
    name = "acquire_metric_task"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.steps = [
            AcquireMetricTask.acquire_service_metrics_step,
            AcquireMetricTask.finalize_metrics_acquisition_step,
        ]

    def get_service_instance_by_account(self, account_id):
        """Get service instance by account id.

        :param int account_id: service account_id
        :return: ervice instance
        :raise ApiManagerError:
        """
        services = task_local.controller.get_service_instances(fk_account_id=account_id)
        return services

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.

        :param exc: The exception raised by the task.
        :param task_id: Unique id of the failed task.
        :param args: Original arguments for the task that failed.
        :param kwargs: Original keyword arguments for the task that failed.
        :param einfo: ExceptionInfo instance, containing the traceback.
        :return: The return value of this handler is ignored.
        """
        if not self.has_session():
            self.get_session(False)

        controller: ServiceController = self.controller
        if controller is not None and controller.manager is not None:
            servicejob: ServiceJob = controller.manager.get_service_job_by_task_id(task_id)
            if servicejob is not None:
                servicejob.status = "FAILURE"
                servicejob.last_error = str(exc)
                controller.manager.update(servicejob)

        self.logger.warn(exc)
        self.logger.warn(einfo)

        return ServiceTask.on_failure(self, exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Run by the worker if the task executes successfully.

        :param retval: The return value of the task.
        :param task_id: Unique id of the executed task.
        :param args: Original arguments for the executed task.
        :param kwargs: Original keyword arguments for the executed task.
        :return:
        """
        if not self.has_session():
            self.get_session(False)

        controller: ServiceController = self.controller
        servicejob: ServiceJob = controller.manager.get_service_job_by_task_id(task_id)

        if servicejob is not None:
            if servicejob.status != "FAILURE":
                servicejob.status = "SUCCESS"

                controller.manager.update(servicejob)

        return ServiceTask.on_success(self, retval, task_id, args, kwargs)

    def acquire_metrics_by_account(
        self,
        account_id: int,
        current_job_id: int,
        metric_num: int,
        metric_dict: dict,
        instance_id: int = None,
        plugintype: str = None,
    ) -> bool:
        """Acquire resource metrics by account.

        :param plugintype:
        :param instance_id:
        :param metric_dict:
        :param metric_num:
        :param str account_id: account id
        :param current_job_id: current job id
        :dict sharedarea: input params
        :return:
        """
        # get container
        controller = self.controller

        def compute_service_id_from_resource(acc_id: int, res_uuid: str, cont_id: int) -> Tuple[int, int]:
            service_id: int = cont_id
            service_plugin_type_id = None
            try:
                if res_uuid is not None:
                    inst_from_resource: ServiceInstance
                    inst_from_resource = controller.manager.get_service_instance(
                        fk_account_id=acc_id, resource_uuid=res_uuid
                    )
                    if inst_from_resource is None:
                        raise Exception("05 Resource %s has not service instance associated" % res_uuid)
                    self.logger.debug(
                        "05 Resource {} has service instance {}associated".format(res_uuid, inst_from_resource.uuid)
                    )

                    if inst_from_resource is not None:
                        service_id = inst_from_resource.id

                        # search plugin_type id of instance
                        api_instance = ServiceUtil.instanceApi(controller, ApiServiceInstance, inst_from_resource)
                        plugin = api_instance.instancePlugin(None, inst=api_instance)
                        if plugin is not None:
                            service_plugin_type_id = plugin.model.plugintype.id

            except Exception as ex:
                self.logger.error("05 No instance_id detected for resource {} ".format(cs.get("uuid")))
            return service_id, service_plugin_type_id

        def compute_metric_type_id(
            metric_name: str,
            metric_measure_type: str,
            metric_group_name: str,
            metric_unit: str,
        ) -> int:
            type_id: int = metric_dict.get(metric_name, None)

            mtp = None
            # check if MetricType exist
            if type_id is None:
                # Insert new ServiceMetricType
                objid = id_gen()
                mtnew = ServiceMetricType(
                    objid,
                    metric_name,
                    metric_measure_type,
                    group_name=metric_group_name,
                    measure_unit=metric_unit,
                )

                metric_type_new = controller.add_service_metric_type_base(mtnew)
                self.logger.debug("06 Create new Metric Type {} {}".format(metric_type_new.name, metric_type_new.id))

                type_id = metric_type_new.id

                metric_dict.update({metric_name: metric_type_id})
            # no deprecated metric_type_plugin_type
            # check if the association between metric_type and plugin_type exist
            # mtp = controller.manager.get_metric_type_plugin_type(plugin_type_id, metric_type_id)
            # if mtp is None and plugin_type_id is not None and metric_type_id is not None:
            #     # association between metric_type and plugin_type not found
            #     # add association metric_type plugin_type
            #     controller.add_metric_type_plugin_type(plugin_type_id, metric_type_id)

            return type_id

        try:
            self.logger.debug("01 Get resource for account {}".format(account_id))
            service_status_list_active = [
                SrvStatusType.STOPPING,
                SrvStatusType.STOPPED,
                SrvStatusType.ACTIVE,
                SrvStatusType.DELETING,
                SrvStatusType.UPDATING,
            ]
            container_srvs: List[ServiceInstance]
            total: int
            container_srvs, total = controller.get_paginated_service_instances(
                account_id=account_id,
                id=instance_id,
                plugintype=plugintype,
                flag_container=True,
                service_status_name_list=service_status_list_active,
                filter_expired=False,
                authorize=False,
                size=0,
            )
            self.logger.debug(
                "03 Acquire metrics for %s instances on account %s and instance %s".format(
                    len(container_srvs), account_id, instance_id
                )
            )

            metrics = []
            self.logger.debug("01 Get resource quota on account {}".format(account_id))
            for container in container_srvs:
                try:
                    plugin_container: ApiServiceTypeContainer
                    plugin_container = ApiServiceType(controller).instancePlugin(None, container)
                    metrics_resource = plugin_container.acquire_metric(container.resource_uuid)
                    self.logger.debug("04 acquire metrics for container {} {}".format(container.uuid, container.name))

                    for cs in metrics_resource:
                        # for any metric find service_id association
                        resource_uuid: str = cs.get("uuid", None)
                        srv_id: int
                        plugin_type_id: int
                        srv_id, plugin_type_id = compute_service_id_from_resource(
                            account_id, resource_uuid, container.oid
                        )
                        # SAVE metrics;
                        for m in cs.get("metrics", []):
                            # decode instance id from resource_uuid
                            name = m.get("key")
                            unit = m.get("unit")
                            measure_type = m.get("type")
                            metric_type_id = compute_metric_type_id(
                                name, measure_type, container.getPluginTypeName(), unit
                            )
                            metric = (
                                m.get("value"),
                                metric_type_id,
                                metric_num,
                                srv_id,
                                resource_uuid,
                            )
                            metrics.append(metric)

                except Exception as ex:
                    self.logger.error(
                        "Exception occurred: {} while acquiring metrics for {} container".format(
                            ex, account_id, container
                        )
                    )

            res = 0
            if len(metrics) > 0:
                self.logger.debug("07 add metrics")

                # generate orm entities for metrics
                metrics = [
                    ServiceMetric(
                        value=m[0],
                        metric_type_id=m[1],
                        metric_num=m[2],
                        service_instance_id=m[3],
                        resource_uuid=m[4],
                        job_id=current_job_id,
                    )
                    for m in metrics
                ]
                # Insert aggregate cost batch
                controller.manager.bulk_save_entities(metrics)
                res = len(metrics)
                self.logger.debug("07 add metrics: {}".format(res))

        except Exception as ex:
            self.logger.error("Exception occurred: {} while acquiring metrics for {}".format(ex, account_id))

        return res

    @staticmethod
    @task_step()
    def acquire_service_metrics_step(task, step_id: str, params: dict = None, *args, **kvargs):
        """Acquire instant service metrics

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """
        if params is None:
            params = {}

        def compute_metric_survey_number() -> int:
            execution_date: datetime = datetime.today().replace(year=1970, month=1, day=1)
            task_interval = controller.get_task_intervals(execution_date=execution_date, task="acq_metric")
            metric_num: int = 0
            if task_interval is not None and len(task_interval) > 0:
                metric_num = task_interval[0].task_num
            return metric_num

        controller: ServiceController = task.controller

        # set params as shared data

        metric_num = params.get("metric_num", None)
        if metric_num is None:
            metric_num = compute_metric_survey_number()

        task.logger.info("Acquire metric num: %s " % metric_num)

        obj_id = params.get("objid", None)
        if obj_id is not None and obj_id == "*":
            obj_id = None

        # get accounts
        accounts: List[Account]
        total_acc: int
        accounts, total_acc = controller.manager.get_accounts(
            objid=obj_id, size=0, with_perm_tag=False, filter_expired=False, active=True
        )

        task.logger.info("Acquire metric got {} accounts".format(total_acc))

        # make dict metric type {name: id}
        metric_types: List[ServiceMetricType]
        metric_types = controller.manager.get_service_metric_types()
        mtype = {mt.name: mt.id for mt in metric_types}

        # log job
        current_job = controller.add_job(task.request.id, "acquire_service_metrics", params)

        task.logger.info("Get accounts total: %s" % total_acc)
        for account in accounts:
            params["account_id"] = account.id
            task.acquire_metrics_by_account(account.id, current_job.id, metric_num, mtype)
            task.logger.info("Generate task for acquire metric for account {}".format(account))

        return True, params

    @staticmethod
    @task_step()
    def finalize_metrics_acquisition_step(task: ServiceTask, step_id: str, params: dict, *args, **kvargs):
        """Finalize the metrics acquistion by computing the next acqusition id

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """
        task.logger.debug("FinalizeMetricAcquisition calling stored procedure")
        controller = task.controller
        controller.manager.call_smsmpopulate(10000)
        task.logger.debug("FinalizeMetricAcquisition done")

        return True, params


class GenerateDailyConsumesTask(ServiceTask):
    entity_class = ApiAccount
    name = "generate_daily_consumes_task"
    inner_type = "TASK"
    prefix = "celery-task-shared-"
    prefix_stack = "celery-task-stack-"
    expire = 3600
    controller: ServiceController = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.steps = [
            GenerateDailyConsumesTask.step_generate_daily_consumes,
        ]

    @staticmethod
    @task_step()
    def step_generate_daily_consumes(task: ServiceTask, step_id: str, params: dict, *args, **kvargs):
        """Generate aggregate costs entities

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """

        task.logger.debug("job_aggregate_costs: start")
        controller = task.controller

        period = params.get("period")
        if period is None:
            yesterday = date.today() - timedelta(days=1)
            period = yesterday.strftime("%Y-%m-%d")

        task.logger.debug("a. Generate Daily Consumes for  {}".format(period))
        current_job = controller.add_job(task.request.id, "Daily_Costs", params)
        controller.manager.call_dailycosts(period, current_job.id)
        return True, params


task_manager.tasks.register(GenerateDailyConsumesTask())
task_manager.tasks.register(AcquireMetricTask())
