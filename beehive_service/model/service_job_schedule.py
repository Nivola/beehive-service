# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sqlalchemy import Column, String, Boolean

from beecell.sqlalchemy.custom_sqltype import TextDictType
from beehive_service.model.base import Base, BaseEntity


class ServiceJobSchedule(BaseEntity, Base):
    """Service jobs

    :param objid: service objid.
    :param name: service job name.
    :param job_name: job name to schedule.
    :param schedule_type: schedule type crontab or timedelta.
    :param schdule_params: schedule params
    :param relative: relative schedule
    :param desc: description's job
    :param job_options: service job options.
    :param retry: boolean to activate retry policy
    :param retry_policy: retry policy of the job
    :param job_args: list of args
    :param job_kvargs: tuple of addictional arguments
    """

    __tablename__ = "service_job_schedule"
    __table_args__ = {"mysql_engine": "InnoDB"}

    job_name = Column(String(200))
    job_options = Column(TextDictType(), default={})
    job_args = Column(TextDictType(), default={})  # args
    job_kvargs = Column(TextDictType(), default={})  # kvargs
    schedule_type = Column(String(10))
    schedule_params = Column(TextDictType(), default={})
    relative = Column(Boolean(), default=False)
    retry = Column(Boolean(), default=False)
    retry_policy = Column(TextDictType(), default={})

    def __init__(
        self,
        objid,
        name,
        job_name,
        schedule_type,
        desc="",
        job_options=None,
        relative=False,
        schedule_params=None,
        retry=False,
        retry_policy=None,
        job_args=None,
        job_kvargs=None,
    ):
        if job_options is None:
            job_options = {}
        if schedule_params is None:
            schedule_params = {}
        if retry_policy is None:
            retry_policy = {}
        if job_args is None:
            job_args = {}
        if job_kvargs is None:
            job_kvargs = {}

        BaseEntity.__init__(self, objid, name, desc, True)

        self.job_name = job_name
        self.job_options = job_options
        self.schedule_type = schedule_type  # {'crontab', 'timedelta'}
        self.schedule_params = schedule_params
        self.relative = relative
        self.retry = retry
        self.retry_policy = retry_policy
        self.job_args = job_args
        self.job_kvargs = job_kvargs

    def __repr__(self):
        return "<ServiceJobSchedule id=%s, name=%s, job_name=%s,  schedule_type=%s>" % (
            self.id,
            self.name,
            self.job_name,
            self.schedule_type,
        )
