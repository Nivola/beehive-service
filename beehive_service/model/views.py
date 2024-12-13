# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, select, func, join
from sqlalchemy.orm import relationship, aliased
from beehive.common.model import AuditData, view
from beehive_service.model.account import Account
from beehive_service.model.service_metric_type_limit import ServiceMetricTypeLimit
from beehive_service.model.service_metric_type import ServiceMetricType
from beehive_service.model.deprecated import AppliedBundle
from beehive_service.model.service_instance import ServiceInstance
from beehive_service.model.service_plugin_type import ServicePluginType
from beehive_service.model.service_definition import ServiceDefinition
from beehive_service.model.service_type import ServiceType
from beehive_service.model.service_metric import ServiceMetric
from beehive_service.model.base import Base


class ServiceInstantConsume(AuditData, Base):
    """ServiceInstantConsume describes the  instant consume for a service container."""

    __tablename__ = "v_service_instant_consume"

    def __init__(
        self,
        plugin_name,
        group_name,
        instant_value,
        unit,
        value,
        service_instance_id,
        account_id,
        job_id,
        creation_date=None,
    ):
        AuditData.__init__(self, creation_date=creation_date)

        self.plugin_name = plugin_name
        self.metric_group_name = group_name
        self.metric_instant_value = instant_value
        self.metric_unit = unit
        self.metric_value = value
        self.service_instance_id = service_instance_id
        self.account_id = account_id
        self.job_id = job_id

    id = Column(Integer, primary_key=True)
    plugin_name = Column(String(100))
    metric_group_name = Column(String(50), nullable=False)
    metric_instant_value = Column(Float, nullable=False, default=0.00)
    metric_unit = Column(String(40), nullable=False)
    metric_value = Column(Float, nullable=False, default=0.00)

    service_instance_id = Column(
        "fk_service_instance_id",
        Integer(),
        ForeignKey("service_instance.id"),
        nullable=False,
    )
    service_instance = relationship("ServiceInstance")
    account_id = Column("fk_account_id", Integer(), ForeignKey("account.id"), nullable=False)
    account = relationship("Account")
    job_id = Column("fk_job_id", Integer(), ForeignKey("service_job.id"), nullable=False)

    def __repr__(self):
        return (
            "<Model:ServiceInstanteConsume(id=%s, plugin_name=%s, service_instance_id=%s, account_id=%s, "
            "metric_group_name=%s, metric_instant_value=%s, metric_value=%s)>"
            % (
                self.id,
                self.plugin_name,
                self.service_instance_id,
                self.account_id,
                self.metric_group_name,
                self.metric_instant_value,
                self.metric_value,
            )
        )


# class VFlatConsume(Base):
#     """"""
#     __view__ = True
#     __tablename__ = 'v_flat_consume'
#
#     mt = aliased(ServiceMetricType)
#     mtl = aliased(ServiceMetricTypeLimit)
#     mtc = aliased(ServiceMetricType)
#     __table__ = view('v_flat_consume', Base.metadata,
#                      select([Account.id.label('account_id'),
#                              Account.name.label('account_name'),
#                              AppliedBundle.id.label('appl_id'),
#                              AppliedBundle.start_date,
#                              AppliedBundle.end_date,
#                              mt.id.label('flat_id'),
#                              mt.name.label('flat_name'),
#                              mt.group_name.label('flat_container'),
#                              mt.metric_type.label('flat_type'),
#                              mtc.id.label('metric_id'),
#                              mtc.name.label('metric_name'),
#                              func.sum(mtl.value).label('value'),
#                              mtc.measure_unit,
#                              func.current_timestamp().label('evaluation_date')
#                              ]).select_from(
#                          join(Account,
#                               join(AppliedBundle,
#                                    join(mt,
#                                         join(mtl, mtc,
#                                              mtc.id == mtl.metric_type_id, isouter=True),
#                                         mt.id == mtl.parent_id, isouter=True),
#                                    AppliedBundle.metric_type_id == mt.id, isouter=True),
#                               Account.id == AppliedBundle.account_id, isouter=True))
#                      .group_by(Account.id, Account.name, mt.id, AppliedBundle.id, AppliedBundle.start_date,
#                                AppliedBundle.end_date, mt.name, mt.group_name, mt.metric_type, mtc.id, mtc.name,
#                                mtc.measure_unit))

#     __table_args__ = {'primary_key': [__table__.c.appl_id, __table__.c.metric_id], 'mysql_engine': 'InnoDB'}
#
#     def __init__(self, account_id, account_name, appl_id, flat_id, flat_name, flat_container, flat_type, metric_id,
#                  metric_name, measure_unit, value, start_date, end_date=None, evaluation_date=datetime.today()):
#         self.account_id = account_id
#         self.account_name = account_name
#         self.appl_id = appl_id
#         self.start_date = start_date
#         self.end_date = end_date
#         self.flat_id = flat_id
#         self.flat_name = flat_name
#         self.flat_container = flat_container
#         self.flat_type = flat_type
#         self.metric_id = metric_id
#         self.metric_name = metric_name
#         self.measure_unit = measure_unit
#         self.value = value
#         self.evaluation_date = evaluation_date
#
#     def __repr__(self):
#         return '<Model:VFlatConsume(account_id:%s, account_name=%s, container:%s, eval_date:%s, flat_name:%s, ' \
#                'mt_limit_name:%s, value:%s)>' % (self.account_id, self.account_name, self.flat_container,
#                                                  self.evaluation_date, self.flat_name, self.metric_name, self.value)


# class VAccountPlugin(Base):
#     """"""
#     __view__ = True
#     __tablename__ = 'v_account_plugin'
#
#     __table__ = view('v_account_plugin', Base.metadata,
#                      select([ServiceInstance.account_id.label('account_id'),
#                              ServiceInstance.id.label('inst_id'),
#                              ServiceInstance.uuid.label('inst_uuid'),
#                              ServiceInstance.name.label('inst_name'),
#                              ServiceInstance.status.label('inst_status'),
#                              ServicePluginType.category.label(
#                                  'plugin_category'),
#                              ServicePluginType.name_type.label('plugin_name')
#                              ]).select_from(join(ServiceInstance, join(ServiceDefinition, join(ServiceType,
#                                                                                                ServicePluginType)))))
#
#     __table_args__ = {'primary_key': [__table__.c.inst_id], 'mysql_engine': 'InnoDB'}
#
#     def __init__(self, account_id, account_name, inst_id, inst_uuid, inst_name, inst_status, plugin_category,
#                  plugin_name):
#         self.account_id = account_id
#         self.account_name = account_name
#         self.inst_id = inst_id
#         self.inst_uuid = inst_uuid
#         self.inst_name = inst_name
#         self.inst_status = inst_status
#         self.plugin_category = plugin_category
#         self.plugin_name = plugin_name
#
#     def __repr__(self):
#         return '<Model:VAccountPlugin(account_id:%s, account_name=%s, inst_id:%s, inst_name:%s, plugin_name:%s, ' \
#                'plugin_category:%s)>' % (
#                    self.account_id, self.account_name,
#                    self.inst_id, self.inst_name,
#                    self.plugin_name, self.plugin_category)


# class ServiceMetricConsumeView(Base):
#     """
#     """
#     __view__ = True
#     __tablename__ = 'v_metric_consume'
#     __table__ = view('v_metric_consume', Base.metadata, selectable=select([ServiceMetric.id.label('id'),
#                                                                            ServiceMetric.metric_type_id.label(
#                                                                                'metric_type_id'),
#                                                                            ServiceMetricType.name.label(
#                                                                                'metric_type_name'),
#                                                                            ServiceMetric.value.label(
#                                                                                'value'),
#                                                                            ServiceMetric.metric_num.label(
#                                                                                'metric_num'),
#                                                                            ServiceMetric.creation_date.label(
#                                                                                'extraction_date'),
#                                                                            ServiceMetric.service_instance_id.label(
#         'service_instance_id'),
#         Account.id.label('account_id'),
#         ServiceMetric.job_id.label('job_id'),
#     ]).select_from(join(join(join(ServiceMetric, ServiceMetricType), ServiceInstance), Account)))
#     __table_args__ = {'primary_key': [__table__.c.id], 'mysql_engine': 'InnoDB'}
#
#     def __init__(self, metric_type_id, metric_type_name, value, metric_num, extraction_date, service_instance_id,
#                  account_id, job_id):
#         self.metric_type_id = metric_type_id
#         self.metric_type_name = metric_type_name
#         self.value = value
#         self.metric_num = metric_num
#         self.extraction_date = extraction_date
#         self.service_instance_id = service_instance_id
#         self.account_id = account_id
#         self.job_id = job_id
#
#     def __repr__(self):
#         return '<ServiceMetricCostView type=%s, name=%s, value=%s,  date=%s>' % (
#             self.metric_type_id, self.metric_type_name, self.value, self.extraction_date)
