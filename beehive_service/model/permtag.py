# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, Integer, String, DateTime

from beehive_service.model.base import Base


class PermTag(Base):
    __tablename__ = "perm_tag"
    __table_args__ = {"mysql_engine": "InnoDB"}
    #   `id` int(11) NOT NULL AUTO_INCREMENT,
    id = Column(Integer, primary_key=True)
    #   `value` varchar(100) COLLATE latin1_general_ci DEFAULT NULL,
    # COLLATE latin1_general_ci DEFAULT NULL,
    value = Column(String(100), nullable=True)
    #   `explain` varchar(400) COLLATE latin1_general_ci DEFAULT NULL,
    explain = Column(String(400), nullable=True)
    #   `creation_date` datetime DEFAULT NULL,
    creation_date = Column(DateTime, nullable=True, autoincrement=False)
