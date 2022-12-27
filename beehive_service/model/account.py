# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null

from beecell.sqlalchemy.custom_sqltype import TextDictType
# from beehive_service.model import ApiBusinessObject
from beehive_service.model.base import Base, ApiBusinessObject
from beehive_service.model.account_capability import AccountCapability
from beehive_service.model.service_status import ServiceStatus
from beehive_service.model.division import Division
from beehive_service.model.service_definition import ServiceDefinition


class Account(ApiBusinessObject, Base):
    """The Account has a soft link to a resource in the implementation layer identifying a Account e.g. the default
    unnanmed Division, etc.
    """
    __tablename__ = 'account'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    acronym = Column(String(10))
    note = Column(String(500))
    contact = Column(String(100))
    email = Column(String(256))
    email_support = Column(String(256))
    email_support_link = Column(String(256))
    division_id = Column('fk_division_id', Integer(),
                         ForeignKey('division.id'), nullable=False)
    # ,lazy='dynamic')
    division: Division = relationship("Division", back_populates="accounts")
    service_instances = relationship(
        "ServiceInstance",
        back_populates="account",
        primaryjoin="and_((Account.id==ServiceInstance.account_id), "
        "or_(ServiceInstance.expiry_date==None, "
        "ServiceInstance.expiry_date>=func.now()))")  # ,lazy='dynamic')

    # the status for this Account
    service_status_id = Column(
        'fk_service_status_id', Integer, ForeignKey('service_status.id'))
    status: ServiceStatus = relationship("ServiceStatus")

    applied_bundles = relationship(
        'AppliedBundle', foreign_keys='AppliedBundle.account_id')

    # Config params in json format
    params = Column(TextDictType(), default={})

    # ServicePriceList activated for this Account.
    price_list = relationship("ServicePriceList", secondary='account_pricelist',
                              secondaryjoin="and_((ServicePriceList.id==AccountsPrices.price_list_id), "
                                            "and_((AccountsPrices.start_date <= func.current_date()), "
                                            "or_(AccountsPrices.end_date.is_(None), "
                                            "AccountsPrices.end_date > func.current_date())))")

    # capabilities  Capabilities activated for this Account.
    capabilities = relationship("AccountCapabilityAssoc")

    def __init__(self, objid, name, division_id, service_status_id, desc='', version='1.0', note=None, contact=None,
                 email=None, email_support=None, email_support_link=None, active=False, params=None, acronym=None):
        if params is None:
            params = {}
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.note = note
        self.contact = contact
        self.email = email
        self.email_support = email_support
        self.email_support_link = email_support_link
        self.division_id = division_id
        self.service_status_id = service_status_id
        self.params = params
        self.acronym = acronym

    def capabilities_list(self):
        """return a list of capabilities  association description (name, plugin_name) and association status (status)
        for the account

        :return: list of dictionary {"name", "plugin_name", "status"}
        """
        return map(lambda capa: capa.association_dict(), self.capabilities)

    def __repr__(self):
        return '<%s id=%s, uuid=%s, objid=%s, name=%s, active=%s, service_status_id=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid,
            self.name, self.active, self.service_status_id)


class AccountServiceDefinition(ApiBusinessObject, Base):
    __tablename__ = 'account_service_definition'
    __table_args__ = (Index('ix_account_service_definition', 'fk_service_definition_id', 'fk_account_id', unique=True),
                      {'mysql_engine': 'InnoDB'})

    """ The realation among the account and his service definitions
    """
    account_id: int = Column('fk_account_id', Integer,
                             ForeignKey('account.id'))
    account: Account = relationship("Account")
    service_definition_id: int = Column(
        'fk_service_definition_id', Integer, ForeignKey('service_definition.id'))
    service_definition: ServiceDefinition = relationship("ServiceDefinition")

    def __init__(self, objid: str, account_id: int, service_definition_id: int,
                 active: bool = True, name: str = None, desc: str = '', version: str = '1.0', ):
        if name is None:
            name = f'Acc{account_id}-SD{service_definition_id}'

        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.account_id = account_id
        self.service_definition_id = service_definition_id

    def __repr__(self):
        return '<%s id=%s, uuid=%s, objid=%s, name=%s, active=%s, account=%s definition=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid,
            self.name, self.active, self.account_id, self.service_definition_id)
