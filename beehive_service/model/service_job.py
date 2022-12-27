# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Index, Column, String, Integer, Text

from beecell.sqlalchemy.custom_sqltype import TextDictType
from beehive_service.model.base import Base, BaseEntity, BaseApiBusinessObject


class ServiceJob(BaseApiBusinessObject, Base):
    """Add Service job

    :param objid: service objid.
    :param job: service job id.
    :param name: service job name.
    :param account_id: id of the account associated.
    :param desc: description's job
    :param params: service job params.
    """
    __tablename__ = 'service_job'
    __table_args__ = (Index('udx_service_job_1', 'task_id',
                            unique=True), {'mysql_engine': 'InnoDB'})

    job = Column(String(200))
    params = Column(TextDictType(), default={})
    account_id = Column('fk_account_id', Integer(), nullable=True)
    # account_id = Column('fk_account_id', Integer(), ForeignKey('account.id'), nullable=False)
    # account = relationship("Account")
    task_id = Column(String(50), nullable=False)
    last_error = Column(Text)
    status = Column(String(50), nullable=False)

    def __init__(self, objid: str, job: str, name: str, account_id: int, task_id: str, desc='', params=None):
        if params is None:
            params = {}
        BaseEntity.__init__(self, objid, name, desc, True)

        self.job = job
        self.account_id = account_id
        self.params = params
        self.task_id = task_id
        self.last_error = ''
        self.status = 'RUNNING'

    def __repr__(self):
        return '<ServiceJob id=%s, job=%s, name=%s, account=%s, last_error=%s>' % \
               (self.id, self.job, self.name, self.account_id, self.last_error)