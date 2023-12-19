# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from beehive_service.model.base import Base, ServiceCategory


class ServicePluginType(Base):
    """PluginType"""

    __tablename__ = "service_plugin_type"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    name_type: str = Column(String(100), nullable=False)
    objclass: str = Column(String(200), unique=True, nullable=False)
    category: str = Column(String(100), nullable=True)
    metric_types = relationship(
        "ServiceMetricType",
        lazy="dynamic",
        secondary="metric_type_plugin_type",
        secondaryjoin="ServiceMetricType.id==metric_type_plugin_type.c.fk_metric_type_id",
    )
    service_category: str = Column("service_category", String(20), default="", nullable=True)

    def __init__(
        self,
        id,
        name_type,
        objclass,
        category=None,
        service_category: str = ServiceCategory.todo,
    ):
        self.id = id
        self.name_type = name_type
        self.objclass = objclass
        self.category = category
        self.service_category = service_category

    def __repr__(self):
        return "<%s id=%s, type=%s, objclass=%s>" % (
            self.__class__.__name__,
            self.id,
            self.name_type,
            self.objclass,
        )
