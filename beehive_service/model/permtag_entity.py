# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sqlalchemy import Column, Integer, String, UniqueConstraint

from beehive_service.model.base import Base


class PermTagEntity(Base):
    __tablename__ = "perm_tag_entity"
    __table_args__ = {"mysql_engine": "InnoDB"}
    # `id` int(11) NOT NULL AUTO_INCREMENT,
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    # `tag` int(11) DEFAULT NULL,
    tag = Column(Integer, nullable=True)
    # `entity` int(11) DEFAULT NULL,
    entity = Column(Integer, nullable=True)
    type = Column(String(200))
    # `type` varchar(200) COLLATE latin1_general_ci DEFAULT NULL,
    UniqueConstraint("tag", "entity", name="idx_tag_entity")
