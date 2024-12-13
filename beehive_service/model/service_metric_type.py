# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import enum

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from beehive_service.model import BaseApiBusinessObject
from beehive_service.model.base import Base, SrvStatusType


class MetricType(enum.Enum):
    NUMBER = 1
    ON_OFF = 2
    CONSUME = 3
    BUNDLE = 4
    OPT_BUNDLE = 5
    PROF_SERVICE = 6
    UNKNOWN = 7


class ServiceMetricType(BaseApiBusinessObject, Base):
    """ServiceMetricType describe the service metric type functionality."""

    __tablename__ = "service_metric_type"
    __table_args__ = {"mysql_engine": "InnoDB"}

    group_name = Column(String(50))
    metric_type = Column("metric_type", String(40), nullable=False)
    measure_unit = Column("measure_unit", String(40), nullable=True)
    status = Column(
        "status",
        String(20),
        ForeignKey("service_status.name"),
        default=SrvStatusType.DRAFT,
        nullable=False,
    )
    limits = relationship("ServiceMetricTypeLimit", foreign_keys="ServiceMetricTypeLimit.parent_id")

    def __init__(
        self,
        objid,
        name,
        metric_type,
        group_name=None,
        desc=None,
        measure_unit=None,
        active=True,
        status=SrvStatusType.DRAFT,
    ):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)

        if desc is None:
            self.desc = name

        if group_name is None:
            self.group_name = name
        else:
            self.group_name = group_name

        self.metric_type = metric_type
        self.measure_unit = measure_unit
        self.status = status

    def __repr__(self):
        if self.measure_unit is None:
            unit = ""
        else:
            unit = self.measure_unit

        return "<ServiceMetricType: id:%s, name:%s, desc:%s, metric_type:%s, unit:%s, group_name:%s>" % (
            self.id,
            self.name,
            self.desc,
            self.metric_type,
            unit,
            self.group_name,
        )
