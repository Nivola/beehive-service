# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, Integer, String

from beehive_service.model.base import Base


class ServiceStatus(Base):
    """ServiceStatus"""

    __tablename__ = "service_status"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    desc = Column(String(250, convert_unicode=True), default="")

    def __init__(self, id, name, desc=None):
        self.id = id
        self.name = name
        self.desc = desc
        if desc is None:
            self.desc = name

    def __repr__(self):
        return "<Model:%s  (%s, %s)>" % (self.__class__, self.id, self.desc)
