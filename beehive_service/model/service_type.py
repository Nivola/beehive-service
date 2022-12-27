# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Index, Column, String, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from beehive_service.model.base import Base, SrvStatusType, ApiBusinessObject, ServiceCategory
from beehive_service.model.service_plugin_type import ServicePluginType

class ServiceType(ApiBusinessObject, Base):
    """ServiceType. e.g. Abstract Vpc, Abstract Dbaas
    """
    __tablename__ = 'service_type'
    __table_args__ = (
        Index('idx_srvtyp_name_version', "name", "version", unique=True),
        {'mysql_engine': 'InnoDB'}
    )

    plugintype : ServicePluginType = relationship(
        'ServicePluginType', primaryjoin="and_(ServiceType.objclass==ServicePluginType.objclass)")
    costParams = relationship(
        "ServiceCostParam",
        back_populates="service_type",
        primaryjoin="and_((ServiceType.id==ServiceCostParam.service_type_id), "
                    "or_(ServiceCostParam.expiry_date==None, ServiceCostParam.expiry_date>=func.now()))")
    serviceProcesses = relationship(
        "ServiceProcess",
        back_populates="service_type",
        primaryjoin="and_((ServiceType.id==ServiceProcess.service_type_id), "
                    "or_(ServiceProcess.expiry_date==None, ServiceProcess.expiry_date>=func.now()))",
        lazy='dynamic')
    status: str = Column('status', String(20), ForeignKey('service_status.name'), default=SrvStatusType.DRAFT,
                    nullable=False)
    objclass: str = Column(String(200), ForeignKey(
        'service_plugin_type.objclass'), nullable=True)
    flag_container: bool = Column(Boolean, nullable=False, default=False)
    template_cfg: str = Column(Text(), nullable=False)

    def __init__(self, objid, name, desc, objclass, flag_container, template_cfg=None, active=False,
                 status=SrvStatusType.DRAFT, version='1.0', category=ServiceCategory.todo):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)
        self.status = status
        self.objclass = objclass
        self.flag_container = flag_container
        self.template_cfg = template_cfg

    def __repr__(self):
        return "<Model:ServiceType(%s, %s, %s, %s, %s, %s)>" % (
            self.id, self.uuid, self.name, self.version, self.active, self.status)