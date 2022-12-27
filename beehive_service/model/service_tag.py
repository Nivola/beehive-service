# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from beehive_service.model.base import Base, BaseEntity, ApiBusinessObject


class ServiceTag(ApiBusinessObject, Base):
    __tablename__ = 'service_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    name = Column(String(100), unique=True)
    # instances = relationship("ServiceInstance", lazy='dynamic', secondary="tag_instance",
    #                          secondaryjoin="ServiceInstance.id==tag_instance.c.fk_service_instance_id",
    #                          passive_deletes=True)

    def __init__(self, name, objid, desc='', active=True):
        """Create new tag

        :param value: tag value
        """
        BaseEntity.__init__(self, objid, name, desc, active)


class ServiceTagWithInstance(ApiBusinessObject, declarative_base()):
    __tablename__ = 'service_tag'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())
    version = Column(String(100))
    instance_uuid = Column(String(100), unique=True, primary_key=True)
    instance_objclass = Column(String(400), unique=True)


class ServiceTagCount(declarative_base()):
    __tablename__ = 'service_tag'

    id = Column(Integer, primary_key=True)
    count = Column(Integer)


class ServiceTagOccurrences(declarative_base()):
    __tablename__ = 'service_tag'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())
    services = Column(Integer)
    links = Column(Integer)
    version = Column(String(100))

    def __init__(self, tag, services, links):
        self.id = tag.id
        self.uuid = tag.uuid
        self.objid = tag.objid
        self.name = tag.name
        self.desc = tag.desc
        self.active = tag.active
        self.creation_date = tag.creation_date
        self.modification_date = tag.modification_date
        self.expiry_date = tag.expiry_date
        self.services = services
        self.links = links
