# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from datetime import datetime

from sqlalchemy import Index, Column, Integer, ForeignKey, Float, DateTime, String
from sqlalchemy.orm import relationship

from beehive.common.model import AuditData
from beehive_service.model.base import Base


class AggregateCost(AuditData, Base):
    """AggregateCost contain flat and consume for Containers"""

    def __init__(
        self,
        metric_type_id,
        consumed,
        cost,
        service_instance_id,
        account_id,
        aggregation_type,
        period,
        cost_type_id,
        evaluation_date=datetime.today(),
        job_id=None,
    ):
        AuditData.__init__(self)

        self.metric_type_id = metric_type_id
        self.consumed = consumed
        self.cost = cost
        self.evaluation_date = evaluation_date
        self.service_instance_id = service_instance_id
        self.account_id = account_id
        self.aggregation_type = aggregation_type
        self.period = period
        self.job_id = job_id
        self.cost_type_id = cost_type_id

    __tablename__ = "aggregate_cost"
    __table_args__ = (
        Index(
            "udx_aggregate_cost_1",
            "fk_service_instance_id",
            "fk_account_id",
            "aggregation_type",
            "period",
            "fk_metric_type_id",
            unique=True,
        ),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True)
    metric_type_id = Column("fk_metric_type_id", Integer(), ForeignKey("service_metric_type.id"))
    consumed = Column(Float(), nullable=False)
    # Unitary service instance cost
    cost = Column(Float(), nullable=False)
    evaluation_date = Column(DateTime, nullable=False)
    service_instance_id = Column(
        "fk_service_instance_id",
        Integer(),
        ForeignKey("service_instance.id"),
        nullable=True,
    )
    account_id = Column("fk_account_id", Integer(), ForeignKey("account.id"), nullable=True)
    job_id = Column("fk_job_id", Integer(), ForeignKey("service_job.id"))
    aggregation_type = Column(String(20), nullable=False)
    period = Column(String(10), nullable=False)
    cost_type_id = Column("fk_cost_type_id", Integer(), ForeignKey("cost_type.id"), nullable=False)
    cost_type = relationship("CostType")

    def __repr__(self):
        if "daily" == self.aggregation_type:
            return (
                "<Model:AggregateCost daily (id:%s, type=%s, consumed:%s, cost:%s, eval_date:%s, inst_id:%s, "
                "cost_type_id:%s)>"
                % (
                    self.id,
                    self.metric_type_id,
                    self.consumed,
                    self.cost,
                    self.evaluation_date,
                    self.service_instance_id,
                    self.cost_type_id,
                )
            )
        else:
            return (
                "<Model:AggregateCost monthly (id:%s, type=%s, consumed:%s, cost:%s, eval_date:%s, acc_id:%s, "
                "cost_type_id:%s)>"
                % (
                    self.id,
                    self.metric_type_id,
                    self.consumed,
                    self.cost,
                    self.evaluation_date,
                    self.account_id,
                    self.cost_type_id,
                )
            )


class AggregateCostType:
    CALC_OK = "CALC_OK"
    NO_METRIC = "NO_METRIC"
    NO_PRICELIST = "NO_PRICELIST"

    CALC_OK_ID = 1
    NO_METRIC_ID = 2
    NO_PRICELIST_ID = 3
