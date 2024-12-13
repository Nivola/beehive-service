# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from beehive_service.model.base import Base, ApiBusinessObject


class ServiceCatalog(ApiBusinessObject, Base):
    """Catalog to link ServiceDefinition to the account"""

    __tablename__ = "service_catalog"
    __table_args__ = {"mysql_engine": "InnoDB"}

    service_definitions = relationship(
        "ServiceDefinition",
        secondary="catalog_definition",
        secondaryjoin="and_((ServiceDefinition.id==catalog_definition."
        "c.fk_service_definition_id),or_(ServiceDefinition."
        "expiry_date==None, ServiceDefinition.expiry_date>=func.now()))",
    )

    def __init__(self, objid, name, desc="", active=True, version="1.0"):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

    def __repr__(self):
        return "<Model:ServiceCatalog(id:%s, objid:%s, name:%s)>" % (
            self.id,
            self.objid,
            self.name,
        )


# Many-to-Many Relationship among SeviceCatalog and ServiceDefinition
catalog_definition = Table(
    "catalog_definition",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("fk_service_catalog_id", Integer(), ForeignKey("service_catalog.id")),
    Column("fk_service_definition_id", Integer(), ForeignKey("service_definition.id")),
    UniqueConstraint("fk_service_catalog_id", "fk_service_definition_id", name="idx_cat_def"),
    mysql_engine="InnoDB",
)
