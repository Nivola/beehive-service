# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sqlalchemy import Column, Integer, String, DateTime

from beehive.common.model import AuditData
from beehive_service.model.base import Base


class ServiceTaskInterval(Base, AuditData):
    """Service daily task interval execution

    :param task: service task.
    :param name: service job name.
    :param desc: description's job
    :param start_date: start interval
    :param end_date: end interval
    :param task_num: numerator task execution
    """

    __tablename__ = "service_task_interval"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    task = Column(String(200))
    name = Column(String(200))
    start_date = Column(DateTime(), nullable=False)
    end_date = Column(DateTime(), nullable=False)
    task_num = Column(Integer, nullable=False)

    def __init__(self, task, name, start_date, end_date, task_num):
        AuditData.__init__(self)

        self.task = task
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.task_num = task_num

    def __repr__(self):
        return "<ServiceTaskInterval task=%s, start=%s, end=%s, task_num=%s>" % (
            self.task,
            self.start_date,
            self.end_date,
            self.task_num,
        )
