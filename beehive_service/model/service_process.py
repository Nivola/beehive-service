# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, Integer, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from beehive_service.model import BaseApiBusinessObject
from beehive_service.model.base import Base


class ServiceProcess(BaseApiBusinessObject, Base):
    """ServiceProcess describe the association between service type and camunda processes.
    """
    __tablename__ = 'service_process'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    service_type_id = Column("fk_service_type_id",
                             Integer(), ForeignKey('service_type.id'))
    service_type = relationship(
        "ServiceType", back_populates="serviceProcesses")
    method_key = Column(String(80), nullable=False)
    process_key = Column(String(80), nullable=False)
    template = Column(Text(), nullable=False)

    def __init__(self, objid, name, service_type_id, method_key, process_key, template, desc='', active=True):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)

        self.method_key = method_key
        self.process_key = process_key
        self.service_type_id = service_type_id
        self.template = template

    def __repr__(self):
        return "<Model:ServiceProcess(%s, %s, %s, %s, %s, %s, %s)>" % (
            self.id, self.uuid, self.name, self.active, self.service_type_id, self.method_key, self.process_key)