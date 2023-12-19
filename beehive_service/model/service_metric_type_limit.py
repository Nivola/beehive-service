# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sqlalchemy import Index, Column, Integer, String, Float, ForeignKey

from beehive_service.model.base import Base


class ServiceMetricTypeLimit(Base):
    """Service metric type limit"""

    __tablename__ = "service_metric_type_limit"
    __table_args__ = (
        Index("udx_srv_metric_type_limit_1", "parent_id", "fk_metric_type_id", unique=True),
        Index("udx_srv_metric_type_limit_2", "parent_id", "name", unique=True),
        {"mysql_engine": "InnoDB"},
    )

    def __init__(self, name, parent_id, metric_type_id, value=0.00, desc=""):
        self.name = name
        self.desc = desc
        self.value = value
        self.parent_id = parent_id
        self.metric_type_id = metric_type_id

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    desc = Column(String(255))
    value = Column(Float(), nullable=False)
    parent_id = Column("parent_id", Integer(), ForeignKey("service_metric_type.id"), nullable=False)
    metric_type_id = Column(
        "fk_metric_type_id",
        Integer(),
        ForeignKey("service_metric_type.id"),
        nullable=False,
    )

    def __repr__(self):
        return "<%s id=%s, name=%s, value=%s, parent_id=%s, metric_type_id=%s>" % (
            self.__class__.__name__,
            self.id,
            self.name,
            self.value,
            self.parent_id,
            self.metric_type_id,
        )
