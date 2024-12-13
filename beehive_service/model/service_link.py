# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship, backref

# from beehive.common.model import BaseEntity
from beehive_service.model.base import Base, BaseEntity


# Many-to-Many Relationship among tags and services
tags_links = Table(
    "tag_instance_link",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("fk_service_tag_id", Integer(), ForeignKey("service_tag.id")),
    Column("fk_service_link_id", Integer(), ForeignKey("service_link.id")),
    mysql_engine="InnoDB",
)


class ServiceLink(Base, BaseEntity):
    __tablename__ = "service_link"
    __table_args__ = {"mysql_engine": "InnoDB"}

    type = Column(String(20), nullable=False)
    start_service_id = Column(Integer(), ForeignKey("service_instance.id"))
    start_service = relationship("ServiceInstance", foreign_keys=start_service_id)
    end_service_id = Column(Integer(), ForeignKey("service_instance.id"))
    end_service = relationship("ServiceInstance", foreign_keys=end_service_id)
    attributes = Column(String(500))
    tag = relationship(
        "ServiceTag",
        secondary=tags_links,
        backref=backref("service_link", lazy="dynamic"),
    )

    def __init__(self, objid, name, ltype, start_service, end_service, attributes=""):
        BaseEntity.__init__(self, objid, name, name, True)
        self.type = ltype
        self.objid = objid
        self.start_service_id = start_service
        self.end_service_id = end_service
        self.attributes = attributes

    def __repr__(self):
        return "<%s id=%s, uuid=%s, obid=%s, name=%s, type=%s, start=%s, end=%s>" % (
            self.__class__.__name__,
            self.id,
            self.uuid,
            self.objid,
            self.name,
            self.type,
            self.start_service_id,
            self.end_service_id,
        )
