# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from sqlalchemy import Column, String, Text, Float

from beehive_service.model.base import Base


class MonitoringParameter(Base):
    """
    TABLE IF NOT EXISTS parameter_monitoring (
    parameter VARCHAR(50) NOT NULL,
    tval TEXT,
    nval REAL
    PRIMARY KEY (parameter)
    );
    Configurazione del monitoraggio
    """
    __tablename__ = 'parameter_monitoring'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    parameter = Column(String(50), primary_key=True, nullable=False)
    tval = Column(Text, nullable=True)
    nval = Column(Float, nullable=True)
