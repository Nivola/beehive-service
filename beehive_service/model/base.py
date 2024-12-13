# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base

from beehive.common.model import BaseEntity, PaginatedQueryGenerator


class Action(object):
    USE = "use"
    CREATE = "create"
    DELETE = "delete"
    UPDATE = "update"
    VIEW = "view"


class SrvPluginTypeCategory(object):
    CONTAINER = "CONTAINER"
    INSTANCE = "INSTANCE"


class ServiceCategory(object):
    cpaas = "cpaas"
    dbaas = "dbaas"
    dummy = "dummy"
    network = "netaas"
    paas = "paas"
    staas = "staas"
    todo = "todo"
    virtual = "virt"
    logaas = "laas"
    monitaas = "maas"


class SrvStatusType(object):
    # VERIFICATI
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CREATED = "CREATED"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ACTIVE = "ACTIVE"
    DELETING = "DELETING"
    DELETED = "DELETED"
    UPDATING = "UPDATING"
    ERROR = "ERROR"
    ERROR_CREATION = "ERROR_CREATION"

    # DA VERIFICARE
    BUILDING = "BUILDING"
    DEPRECATED = "DEPRECATED"
    RELEASED = "RELEASED"
    EXPUNGING = "EXPUNGING"
    EXPUNGED = "EXPUNGED"
    SYNCHRONIZE = "SYNCHRONIZE"
    TERMINATED = "TERMINATED"
    SHUTTINGDOWN = "SHUTTING-DOWN"
    UNKNOWN = "UNKNOWN"


class ParamType(object):
    FLOAT = "float"
    INTEGER = "integer"
    STRING = "string"
    DATETIME = "datetime"
    DATE = "date"
    BOOLEAN = "boolean"


class ConfParamType(object):
    JSON = "json"
    XML = "xml"


class OrgType(object):
    PUBLIC = "Public"
    PRIVATE = "Private"


Base = declarative_base()


class BaseApiBusinessObject(BaseEntity):
    """Column of common audit
    from BaseEntity:

        id:    priamary key
        uuid:  alternate key (Unique)
        objid:  permsion key acording to authorization hierarcy
        desc:  brief description
        active: active status
    from AuditData
        creation_date: creation date
        modification_date: modification date
        expiry_date: expiry date
    overiden
        name:  mnemonic key not unique   = Column(String(100), unique=True)

    """

    # overwrite  unique=false
    name = Column(String(100), unique=False)

    def __init__(self, objid: str, name: str, desc: str, active: bool):
        BaseEntity.__init__(self, objid, name, desc, active)

    @staticmethod
    def get_base_entity_sqlfilters(*args, **kvargs):
        filters = BaseEntity.get_base_entity_sqlfilters(*args, **kvargs)

        return filters


class ApiBusinessObject(BaseApiBusinessObject):
    """Column of common audit"""

    # version attribute
    version = Column(String(100), nullable=False, default="1.0")

    def __init__(self, objid: str, name: str, desc: str, active, version):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)
        self.version = version

    @staticmethod
    def get_base_entity_sqlfilters(*args, **kvargs):
        filters = BaseApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field("version", kvargs))

        return filters
