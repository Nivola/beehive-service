# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, Integer, ForeignKey, JSON, Text, String, Table
from sqlalchemy.orm import relationship, backref

from beecell.sqlalchemy.custom_sqltype import TextDictType
from beehive_service.model.base import Base, SrvStatusType, ApiBusinessObject, BaseApiBusinessObject
from beehive_service.model.service_link_instance import ServiceLinkInstance


# Many-to-Many Relationship among ServiceTag and ServiceInstance (Instances)
tag_instance = Table(
    'tag_instance',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('fk_service_tag_id', Integer(), ForeignKey('service_tag.id')),
    Column('fk_service_instance_id', Integer(),
           ForeignKey('service_instance.id')),
    mysql_engine='InnoDB')


class ServiceInstance(ApiBusinessObject, Base):
    """ ServiceInstance  is a service defined in a tenant has a soft link to a resource in the implementation layer
    e.g. a VPC, or a Dbaas...
    """
    __tablename__ = 'service_instance'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # the account to which the ServiceInstance belong
    account_id = Column('fk_account_id', Integer(),
                        ForeignKey('account.id'), nullable=False)
    account = relationship('Account', back_populates='service_instances')
    tag = relationship('ServiceTag', secondary=tag_instance,
                       backref=backref('service_instance', lazy='dynamic'))
    service_definition_id = Column(
        'fk_service_definition_id', Integer(), ForeignKey('service_definition.id'))
    service_definition = relationship('ServiceDefinition')
    linkChildren = relationship('ServiceLinkInstance',
                                primaryjoin='and_((ServiceLinkInstance.start_service_id==ServiceInstance.id), '
                                            'or_(ServiceLinkInstance.expiry_date==None, '
                                            'ServiceLinkInstance.expiry_date>=func.now()))',
                                back_populates='start_service',
                                order_by=lambda: ServiceLinkInstance.priority,
                                lazy='dynamic')
    linkParent = relationship('ServiceLinkInstance',
                              primaryjoin='and_((ServiceLinkInstance.end_service_id==ServiceInstance.id), '
                                          'or_(ServiceLinkInstance.expiry_date==None, '
                                          'ServiceLinkInstance.expiry_date>=func.now()))',
                              back_populates='end_service',
                              single_parent=True)

    config = relationship('ServiceInstanceConfig',
                          primaryjoin='and_(and_((ServiceInstance.id==ServiceInstanceConfig.service_instance_id), '
                                      'or_(ServiceInstanceConfig.expiry_date==None, '
                                      'ServiceInstanceConfig.expiry_date>=func.now())), '
                                      'ServiceInstanceConfig.active == True)',
                          back_populates='service_instance',
                          lazy='dynamic')
    # tags = relationship('ServiceTag', lazy='dynamic', secondary='tag_instance',
    #                     secondaryjoin='ServiceTag.id==tag_instance.c.fk_service_tag_id')
    params = Column(JSON)
    last_error = Column(Text)
    bpmn_process_id = Column(String(100))
    resource_uuid = Column(String(50), nullable=True)

    # ServiceInstance status
    status = Column('status', String(20), ForeignKey('service_status.name'), default=SrvStatusType.DRAFT,
                    nullable=False)

    def __init__(self, objid, name, account_id, service_definition_id, desc='', active=True,
                 status=SrvStatusType.RELEASED, version='1.0', bpmn_process_id=None, resource_uuid=None):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.account_id = account_id
        self.service_definition_id = service_definition_id
        self.bpmn_process_id = bpmn_process_id
        self.status = status
        self.resource_uuid = resource_uuid
        self.last_error = ''

    def __repr__(self):
        return '<ServiceInstance(%s, %s, %s)>' % (self.id, self.objid, self.name)


class ServiceInstanceConfig(BaseApiBusinessObject, Base):
    """ ServiceInstanceConfig contain a specific configuration params for a specific ServiceInstance
    """
    __tablename__ = 'service_instance_config'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    json_cfg = Column(TextDictType(), default={})
    service_instance_id = Column('fk_service_instance_id', Integer(), ForeignKey('service_instance.id'))
    service_instance = relationship("ServiceInstance", back_populates="config")

    def __init__(self, objid, name, service_instance_id, json_cfg='{}', desc='', active=True):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)

        self.json_cfg = json_cfg
        self.service_instance_id = service_instance_id

    def __repr__(self):
        return '<ServiceInstanceConfig(%s, %s, %s)>' % (self.id, self.name, self.service_instance_id)


class ServiceTypePluginInstance(ServiceInstance):
    type_id = Column(Integer)
    objclass = Column(String(200))
    inst_tags = Column(String(200))
    definition_name = Column(String(200))
