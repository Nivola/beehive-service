# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from beehive_service.model import ApiBusinessObject
from beehive_service.model.base import Base


class Organization(ApiBusinessObject, Base):
    """ The Organization
        has a soft link to a resource in the implementation layer
        e.g. the service provider or a
    """
    __tablename__ = 'organization'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # Organization type {Public, Private}
    org_type = Column(String(10), nullable=False)

    service_status_id = Column(
        'fk_service_status_id', Integer, ForeignKey('service_status.id'))
    status = relationship("ServiceStatus")
    divisions = relationship("Division", back_populates="organization", lazy='dynamic',
                             primaryjoin="and_((Organization.id==Division.organization_id), "
                                         "or_(Division.expiry_date==None, Division.expiry_date>=func.now()))")

    # external client identification on the anagraphical database
    ext_anag_id = Column(String(32))
    # managment attributes json encoded
    # in order to implements managments logics and  accounting
    attributes = Column(Text)
    # esenzione iva    si/no
    hasvat = Column(Boolean())
    # consorziato    si/no
    partner = Column(Boolean())
    # name and surname of the organization's referent str
    referent = Column(String(100))
    # _email to contact organization's referent str
    email = Column(String(256))
    # istitutional organization email
    legalemail = Column(String(256))
    # istitutional organization postal address
    postaladdress = Column(String(256))

    def __init__(self, objid, name, org_type, service_status_id, desc='', version='1.0', ext_anag_id=None,
                 attributes=None, hasvat=False, partner=False, referent=None, email=None, legalemail=None,
                 postaladdress=None, active=False):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)
        self.org_type = org_type
        self.service_status_id = service_status_id
        self.ext_anag_id = ext_anag_id
        self.attributes = attributes
        self.hasvat = hasvat
        self.partner = partner
        self.referent = referent
        self.email = email
        self.legalemail = legalemail
        self.postaladdress = postaladdress
        self.active = active

    def __repr__(self):
        return '<%s id=%s, uuid=%s, objid=%s, name=%s, active=%s, service_status_id=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid, self.name, self.active, self.service_status_id)