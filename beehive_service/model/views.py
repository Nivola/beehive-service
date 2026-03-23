# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

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
