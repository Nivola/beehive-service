# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from beehive_service.model.base import Base, BaseEntity, ApiBusinessObject


class ServiceTag(ApiBusinessObject, Base):
    __tablename__ = "service_tag"
    __table_args__ = {"mysql_engine": "InnoDB"}

    name = Column(String(100), unique=False)
    # instances = relationship("ServiceInstance", lazy='dynamic', secondary="tag_instance",
    #                          secondaryjoin="ServiceInstance.id==tag_instance.c.fk_service_instance_id",
    #                          passive_deletes=True)

    # the account to which the ServiceTag belong
    account_id = Column("fk_account_id", Integer(), ForeignKey("account.id"), nullable=False)

    def __init__(self, name, objid, account_id, desc="", active=True):
        """Create new tag

        :param value: tag value
        """
        BaseEntity.__init__(self, objid, name, desc, active)
        self.account_id = account_id


class ServiceTagWithInstance(ApiBusinessObject, declarative_base()):
    __tablename__ = "service_tag"

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
    __tablename__ = "service_tag"

    id = Column(Integer, primary_key=True)
    count = Column(Integer)


class ServiceTagOccurrences(declarative_base()):
    __tablename__ = "service_tag"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())
    account_id = Column("fk_account_id", Integer(), ForeignKey("account.id"), nullable=False)
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
        self.account_id = tag.account_id
        self.services = services
        self.links = links
