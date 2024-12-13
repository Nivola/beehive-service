# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import ujson as json
from sqlalchemy import (
    Table,
    Column,
    Integer,
    ForeignKey,
    String,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship

# from beehive_service.model import ApiBusinessObject
from beehive_service.model.base import Base, SrvStatusType, ApiBusinessObject
from beehive_service.model import logging

# Many-to-Many Relationship among Account and AccountCapability
account_account_capabilities = Table(
    "account_account_capabilities",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("fk_account_id", Integer(), ForeignKey("account.id")),
    Column("fk_account_capabilities", Integer(), ForeignKey("account_capabilities.id")),
    Column("status", String(20), default=SrvStatusType.BUILDING, nullable=False),
    UniqueConstraint(
        "fk_account_id",
        "fk_account_capabilities",
        name="idx_account_account_capabilities",
    ),
    mysql_engine="InnoDB",
)


class AccountCapabilityAssoc(Base):
    """Association between account  and accountCapabilities
    https://docs.sqlalchemy.org/en/latest/orm/basic_relationships.html
    """

    __table__ = account_account_capabilities

    # id =  account_account_capabilities.c.id
    fk_account_id = __table__.c.fk_account_id
    fk_capability = __table__.c.fk_account_capabilities
    status = __table__.c.status
    capability = relationship("AccountCapability")

    def __init__(self, account_id, capability_id, status):
        self.fk_account_id = account_id
        self.fk_capability = capability_id
        self.status = status

    def association_seq(self):
        return (
            self.capability.name,
            self.capability.plugin_name,
            self.status,
        )

    def association_dict(self):
        try:
            params = json.loads(self.capability.params)
        except Exception:
            params = {}
        return {
            "name": self.capability.name,
            "params": params,
            # u"plugin_name": self.capability.plugin_name,
            "description": self.capability.desc,
            "status": self.status,
        }

    def __repr__(self):
        return "<Model:AccountAccountCapability(id:%s, account:%s, capability:%s status:%s)>" % (
            self.id,
            self.fk_account_id,
            self.fk_capability,
            self.status,
        )


class AccountCapability(ApiBusinessObject, Base):
    """Account Capabilities are descriptions of base service to be created in order to enable the account to a set of
    services (types)
    """

    __tablename__ = "account_capabilities"
    __table_args__ = {"mysql_engine": "InnoDB"}

    status = Column(
        "status",
        String(20),
        ForeignKey("service_status.name"),
        default=SrvStatusType.ACTIVE,
        nullable=False,
    )
    # overide name  is unique
    name = Column(String(100), unique=True)
    plugin_name = Column(String(100))
    # Config params in json format
    params = Column(Text(), default={})

    def __init__(
        self,
        objid,
        name,
        desc,
        plugin_name="ComputeService",
        active=True,
        version="1.0",
        status=SrvStatusType.ACTIVE,
        params="{}",
    ):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)
        self.status = status
        self.params = params
        self.plugin_name = plugin_name

    def __repr__(self):
        return "<Model:AccountCapability(id:%s, objid:%s, name:%s)>" % (
            self.id,
            self.objid,
            self.name,
        )
