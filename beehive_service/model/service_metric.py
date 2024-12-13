# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from beehive.common.model import AuditData
from beehive_service.model.base import Base


class ServiceMetric(AuditData, Base):
    """ServiceMetric describe the service type functionality."""

    __tablename__ = "service_metric"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    value = Column(Float, nullable=False, default=0.00)
    metric_type_id = Column("fk_metric_type_id", Integer(), ForeignKey("service_metric_type.id"))
    metric_type = relationship("ServiceMetricType")
    metric_num = Column(Integer(), nullable=False)
    service_instance_id = Column("fk_service_instance_id", Integer(), ForeignKey("service_instance.id"))
    job_id = Column("fk_job_id", Integer(), ForeignKey("service_job.id"))
    resource_uuid = Column(String(50), nullable=True)

    def __init__(
        self,
        value,
        metric_type_id,
        metric_num,
        service_instance_id,
        job_id,
        resource_uuid=None,
        creation_date=None,
    ):
        AuditData.__init__(self, creation_date=creation_date)

        self.value = value
        self.metric_type_id = metric_type_id
        self.metric_num = metric_num
        self.service_instance_id = service_instance_id
        self.resource_uuid = resource_uuid
        self.job_id = job_id

    def __repr__(self):
        return "<Model:ServiceMetric(id=%s, value=%s, type=%s)>" % (
            self.id,
            self.value,
            self.metric_type_id,
        )
