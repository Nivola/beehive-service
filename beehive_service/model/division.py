# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from beehive_service.model.base import Base, ApiBusinessObject

class Division(ApiBusinessObject, Base):
    """The Division
        a Accounts container
        some meaning at costs managmente and accounting
        has a soft link to a resource in the implementation layer idetifying a Account
        e.g. the default unnanmed Division, etc.
    """
    __tablename__ = 'division'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    contact = Column(String(100))
    email = Column(String(256))
    postaladdress = Column(String(255))

    organization_id = Column('fk_organization_id', Integer(
    ), ForeignKey('organization.id'), nullable=False)
    organization = relationship(
        "Organization", back_populates="divisions")  # ,lazy='dynamic')

    # the status for this Division
    service_status_id = Column(
        'fk_service_status_id', Integer, ForeignKey('service_status.id'))
    status = relationship(u"ServiceStatus")

    # ServicePriceList for this Division.
    price_list = relationship("ServicePriceList", secondary='division_pricelist',
                              secondaryjoin="and_((ServicePriceList.id==DivisionsPrices.price_list_id), "
                                            "and_((DivisionsPrices.start_date <= func.current_date()), "
                                            "or_(DivisionsPrices.end_date.is_(None), "
                                            "DivisionsPrices.end_date > func.current_date())))")

    # the list of Accounts for this Division
    accounts = relationship("Account",
                            back_populates="division",
                            primaryjoin="and_((Division.id==Account.division_id),"
                            "or_(Account.expiry_date==None, Account.expiry_date>=func.now()))",
                            lazy='dynamic')
    wallets = relationship("Wallet",
                           back_populates="division",
                           primaryjoin="and_((Division.id==Wallet.division_id), or_(Wallet.expiry_date==None, "
                                       "Wallet.expiry_date>=func.now()))",
                           lazy='dynamic')

    def __init__(self, objid, name, organization_id, service_status_id, desc='', version='1.0', contact=None,
                 email=None, postaladdress=None, active=False):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.organization_id = organization_id
        self.service_status_id = service_status_id
        self.contact = contact
        self.email = email
        self.postaladdress = postaladdress