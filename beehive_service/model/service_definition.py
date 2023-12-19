# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


from sqlalchemy import Column, Integer, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship

from beecell.sqlalchemy.custom_sqltype import TextDictType
from beehive_service.model.base import (
    Base,
    SrvStatusType,
    ConfParamType,
    ApiBusinessObject,
)
from beehive_service.model.service_type import ServiceType
from typing import List


class ServiceConfig:
    pass


class ServiceLinkDef:
    pass


class ServiceDefinition(ApiBusinessObject, Base):
    """ServiceDefinition is an entry in a service catalog. It is a specialization of a ServiceType so his config
    overides and extend the ServiceType config. It is e.g. Tiny Vpc (on a specific stack)
    """

    __tablename__ = "service_definition"
    __table_args__ = {"mysql_engine": "InnoDB"}

    service_type_id = Column("fk_service_type_id", Integer(), ForeignKey("service_type.id"))
    service_type: ServiceType = relationship("ServiceType")
    status = Column(
        "status",
        String(20),
        ForeignKey("service_status.name"),
        default=SrvStatusType.DRAFT,
        nullable=False,
    )
    is_default = Column("is_default", Boolean(), default=False)
    linkParent: ServiceLinkDef = relationship(
        "ServiceLinkDef",
        primaryjoin="and_((ServiceLinkDef.end_service_id==ServiceDefinition.id), "
        "or_(ServiceLinkDef.expiry_date==None, "
        "ServiceLinkDef.expiry_date>=func.now()))",
        back_populates="end_service",
        single_parent=True,
    )
    linkChildren: List[ServiceLinkDef] = relationship(
        "ServiceLinkDef",
        primaryjoin="and_((ServiceLinkDef.start_service_id==ServiceDefinition.id),"
        "or_(ServiceLinkDef.expiry_date==None, "
        "ServiceLinkDef.expiry_date>=func.now()))",
        back_populates="start_service",
        lazy="dynamic",
    )

    config_params: List[ServiceConfig] = relationship(
        "ServiceConfig",
        back_populates="service_definition",
        primaryjoin="and_(and_((ServiceDefinition.id==ServiceConfig.service_definition_id), "
        "or_(ServiceConfig.expiry_date==None, "
        "ServiceConfig.expiry_date>=func.now())), ServiceConfig.active == True)",
    )

    def __init__(
        self,
        objid,
        name,
        desc,
        service_type_id,
        active=True,
        version="1.0",
        status=SrvStatusType.RELEASED,
        is_default=False,
    ):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)
        self.service_type_id = service_type_id
        self.status = status
        self.is_default = is_default

    def __repr__(self):
        return "<Model:ServiceDefinition(id:%s, objid:%s, name:%s)>" % (
            self.id,
            self.objid,
            self.name,
        )


class ServiceConfig(ApiBusinessObject, Base):
    """ServiceConfig contain a specific configuration params
    for a ServiceDefinition to extend the ServiceType config

    There is only one active ServiceConfig for each ServiceDefinition
    """

    __tablename__ = "service_config"
    __table_args__ = {"mysql_engine": "InnoDB"}

    service_definition_id = Column("fk_service_definition_id", Integer(), ForeignKey("service_definition.id"))
    service_definition = relationship("ServiceDefinition", back_populates="config_params")
    # Config params in json format
    params = Column(TextDictType(), default={})
    # JSON, YAML, ... (Da copire)
    params_type = Column(String(20))

    def __init__(
        self,
        objid,
        name,
        service_definition_id,
        params="{}",
        params_type=ConfParamType.JSON,
        desc="",
        active=True,
        version="1.0",
    ):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.service_definition_id = service_definition_id
        self.params = params
        self.params_type = params_type

    def __repr__(self):
        return "<Model:ServiceConfig(id:%s, srvDefId:%s, name:%s, desc:%s, params:%s, params_type:%s)>" % (
            self.id,
            self.service_definition_id,
            self.name,
            self.desc,
            self.params,
            self.params_type,
        )
