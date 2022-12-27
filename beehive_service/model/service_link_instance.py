# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Index, Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from beehive.common.model import BaseEntity
from beehive_service.model import ApiBusinessObject
from beehive_service.model.base import Base


class ServiceLinkInstance(ApiBusinessObject, Base):
    """ServiceLinkInstance
    """
    __tablename__ = 'service_link_inst'
    __table_args__ = (Index('idx_srvlnkinst_1', 'start_service_id', 'end_service_id', unique=True),
                      {'mysql_engine': 'InnoDB'})
    start_service_id = Column(Integer(), ForeignKey('service_instance.id'))
    start_service = relationship(
        'ServiceInstance', foreign_keys=start_service_id, back_populates='linkChildren')
    end_service_id = Column(Integer(), ForeignKey('service_instance.id'))
    end_service = relationship('ServiceInstance', foreign_keys=end_service_id)
    attributes = Column(String(500))
    priority = Column(Integer(), nullable=True)

    def __init__(self, objid, name, start_service, end_service, priority=0, desc=None, attributes=''):
        if desc is None:
            desc = name
        BaseEntity.__init__(self, objid, name, desc, True)

        self.objid = objid
        self.start_service_id = start_service
        self.end_service_id = end_service
        self.attributes = attributes
        self.priority = priority

    def __repr__(self):
        return '<%s id=%s, uuid=%s, obid=%s, name=%s, start=%s, end=%s, priority=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid, self.name, self.start_service_id,
            self.end_service_id, self.priority)