# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from sqlalchemy import Column, String, Text

from beehive_service.model.base import Base


class MonitoringMessage(Base):
    """
    TABLE IF NOT EXISTS log_monit (
    period  varchar(10) NOT NULL,
    msg TEXT,
    recipent TEXT,
    PRIMARY KEY (period)
    );
    messaggio di monitoraggio
    """
    __tablename__ = 'log_monit'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    period = Column(String(10), primary_key=True, nullable=False)
    msg = Column(Text, nullable=True)
    recipient = Column(Text, nullable=True)