# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index, String, Text, Boolean, Table
from sqlalchemy.orm import relationship

from beehive.common.model import AuditData
from beehive_service.model.base import Base, BaseApiBusinessObject, ApiBusinessObject


class Agreement(ApiBusinessObject, Base):
    """Accordo di servizio per il popolamento del portfolio
    """
    __tablename__ = 'agreement'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # the Wallet  related to this Agreement
    wallet_id = Column('fk_wallet_id', Integer(),
                       ForeignKey('wallet.id'), nullable=False)
    wallet = relationship('Wallet', back_populates="agreements")
    service_status_id = Column(
        'fk_service_status_id', Integer, ForeignKey('service_status.id'))
    status = relationship("ServiceStatus")
    amount = Column(Float, nullable=False, default=0.00)
    agreement_date_start = Column(Date(), nullable=False)
    agreement_date_end = Column(Date(), nullable=True)

    def __init__(self, objid, name, wallet_id, service_status_id, desc='', active=True, version='1.0', amount=0.00,
                 agreement_date_start=None, agreement_date_end=None):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.wallet_id = wallet_id
        self.service_status_id = service_status_id
        self.amount = amount
        self.agreement_date_start = agreement_date_start
        self.agreement_date_end = agreement_date_end

        if agreement_date_start is None:
            self.agreement_date_start = self.creation_date


class Wallet(ApiBusinessObject, Base):
    """Il portfolio e' legato alla divisione ed e' fondamentale per il billing, lavora con un meccanismo di erosione
    del credito. Col portfolio a 0 non e' possibile creare account.
    """
    __tablename__ = 'wallet'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # the Division this Wallet belong
    division_id = Column('fk_division_id', Integer(),
                         ForeignKey('division.id'), nullable=False)
    division = relationship("Division", back_populates="wallets")
    agreements = relationship("Agreement", back_populates="wallet",
                              primaryjoin="and_((Wallet.id==Agreement.wallet_id), or_(Agreement.expiry_date==None, "
                              "Agreement.expiry_date>=func.now()))", lazy='dynamic')
    service_status_id = Column(
        'fk_service_status_id', Integer, ForeignKey('service_status.id'))
    status = relationship("ServiceStatus")
    capital_total = Column(Float, nullable=False, default=0.00)
    capital_used = Column(Float, nullable=False, default=0.00)
    evaluation_date = Column(DateTime())
    year = Column('year_ref', Integer, nullable=False)

    def __init__(self, objid, name, division_id, year, service_status_id, desc='', version='1.0', capital_total=0.00,
                 capital_used=0.00, evaluation_date=None, active=True):
        ApiBusinessObject.__init__(self, objid, name, desc, active, version)

        self.capital_total = capital_total
        self.capital_used = capital_used
        self.evaluation_date = evaluation_date
        self.division_id = division_id
        self.service_status_id = service_status_id
        self.year = year

    def __repr__(self):
        return '<%s id=%s, uuid=%s, objid=%s, name=%s, active=%s, service_status_id=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid, self.name, self.active, self.service_status_id)


class AppliedBundle(Base):
    """Bundles applied from an account by date.
    """
    __tablename__ = 'applied_bundle'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    account_id = Column('fk_account_id', Integer(), ForeignKey('account.id'), nullable=False)
    metric_type_id = Column('fk_metric_type_id', Integer(), ForeignKey('service_metric_type.id'), nullable=False)
    start_date = Column(DateTime(), nullable=False)
    end_date = Column(DateTime(), nullable=True)
    # account = relationship('Account')
    metric_type = relationship('ServiceMetricType')

    def __init__(self, account_id, metric_type_id, start_date, end_date=None):
        self.account_id = account_id
        self.metric_type_id = metric_type_id
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return "<Model:AppliedBundle(%s, %s, %s, %s, %s)>" % (
            self.id, self.account_id, self.metric_type_id, self.start_date, self.end_date)


class ReportCost(AuditData, Base):
    """ReportCost describe costs flat or consume for report daily.
    """
    __tablename__ = 'report_cost'
    __table_args__ = (Index('udx_report_cost_1', 'fk_account_id', 'plugin_name', 'fk_metric_type_id', 'period',
                            unique=True), {'mysql_engine': 'InnoDB'})

    def __init__(self, account_id, plugin_name, metric_type_id, period, value, cost, job_id, report_date=None,
                 creation_date=None, note=''):
        AuditData.__init__(self, creation_date=creation_date)

        self.account_id = account_id
        self.plugin_name = plugin_name
        self.value = value
        self.cost = cost
        self.metric_type_id = metric_type_id
        self.period = period
        self.note = note
        self.report_date = report_date
        self.job_id = job_id

    id = Column(Integer, primary_key=True)
    account_id = Column('fk_account_id', Integer(),
                        ForeignKey('account.id'), nullable=False)
    plugin_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False, default=0.00)
    cost = Column(Float, nullable=False, default=0.00)
    # period = Column(String(10), nullable=False)
    metric_type_id = Column('fk_metric_type_id', Integer(),
                            ForeignKey('service_metric_type.id'))
    metric_type = relationship('ServiceMetricType')
    note = Column(Text())
    report_date = Column(DateTime())
    period = Column(String(10), nullable=False)
    job_id = Column('fk_job_id', Integer(), ForeignKey('service_job.id'))

    def __repr__(self):
        return '<Model:ReportCost(account_id=%s, value=%s, cost=%s, type=%s, period=%s, report_date=%s, ' \
               'plugin_name=%s, metric_type_id=%s)>' % (
                   self.account_id, self.value, self.cost, self.metric_type_id, self.period, self.report_date,
                   self.plugin_name, self.metric_type_id is not None)


class ServiceCostParam(BaseApiBusinessObject, Base):
    """ServiceCostParam describe the service type functionality.
    """
    __tablename__ = 'service_cost_param'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    # Measure unit (Ex: Gb, Mb, Processor N., etc.)
    param_unit = Column(String(20, convert_unicode=True),
                        nullable=True, default='')
    # Parameter regexp format
    param_definition = Column(
        String(250, convert_unicode=True), nullable=False, default='')
    service_type_id = Column("fk_service_type_id",
                             Integer(), ForeignKey('service_type.id'))
    service_type = relationship("ServiceType", back_populates="costParams")

    def __init__(self, objid, name, param_unit,  param_definition, service_type_id, desc='', active=True):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)

        self.param_unit = param_unit
        self.param_definition = param_definition
        self.service_type_id = service_type_id

    def __repr__(self):
        return "<Model:ServiceCostParam(%s, %s, %s, %s)>" % (self.id, self.uuid, self.name, self.active)


class CostType(Base):
    """CostType describe the cost generation process.
    """
    __tablename__ = 'cost_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def __init__(self, id, name, desc=None):
        self.id = id
        self.name = name
        if desc is None:
            self.desc = name
        else:
            self.desc = desc

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    desc = Column(String(255))

    def __repr__(self):
        return "<CostType: id:%s, name:%s, desc:%s>" % (self.id, self.name, self.desc)


class MetricTypePluginType(Base, AuditData):
    """MetricTypePluginType describe witch metric type generate each plugin type.
    """
    __tablename__ = 'metric_type_plugin_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def __init__(self, plugin_type_id, metric_type_id):
        AuditData.__init__(self)

        self.metric_type_id = metric_type_id
        self.plugin_type_id = plugin_type_id

    id = Column(Integer, primary_key=True)
    plugin_type_id = Column('fk_plugin_type_id', Integer(),
                            ForeignKey('service_plugin_type.id'))
    metric_type_id = Column('fk_metric_type_id', Integer(),
                            ForeignKey('service_metric_type.id'))

    def __repr__(self):
        return "<MetricTypePluginType: id:%s, metric_type_id:%s, plugin_type_id:%s>" % \
               (self.id, self.metric_type_id, self.plugin_type_id)


class ServicePriceList(BaseApiBusinessObject, Base):
    """ServicePriceList describe the service type functionality.
    """
    __tablename__ = 'service_pricelist'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    flag_default = Column('flag_default', Boolean(), default=False)

    metrics_prices = relationship(
        "ServicePriceMetric",
        back_populates="price_list",
        primaryjoin="and_((ServicePriceList.id==ServicePriceMetric.price_list_id), "
                    "or_(ServicePriceMetric.expiry_date==None, ServicePriceMetric.expiry_date>=func.now()))",
                    lazy='dynamic')

    def __init__(self, objid, name, flag_default=False, desc='', active=True):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)
        self.flag_default = flag_default

    def __repr__(self):
        return "<Model:ServicePriceList(%s, %s, %s, %s, %s)>" % (
            self.id, self.uuid, self.name, self.active, self.flag_default)


class DivisionsPrices(AuditData, Base):
    """DivisionsPrices describe the relation from Division and Pricelist
    """
    __tablename__ = 'division_pricelist'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    division_id = Column('fk_division_id', Integer,
                         ForeignKey('division.id'), nullable=False)
    price_list_id = Column('fk_price_list_id', Integer, ForeignKey(
        'service_pricelist.id'), nullable=False)
    start_date = Column(DateTime(), nullable=False)
    end_date = Column(DateTime(), nullable=True)

    def __init__(self,  division_id, price_list_id, start_date, end_date=None):
        AuditData.__init__(self)
        self.division_id = division_id
        self.price_list_id = price_list_id
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return '<Model:DivisionsPrices(%s, %s, %s, %s, %s)>' % (
            self.id, self.division_id, self.price_list_id, self.start_date, self.end_date)


class AccountsPrices(AuditData, Base):
    """AccountsPrices describe the the relation from Account and Pricelist
    """
    __tablename__ = 'account_pricelist'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def __init__(self, account_id, price_list_id, start_date, end_date=None):
        AuditData.__init__(self)
        self.price_list_id = price_list_id
        self.account_id = account_id
        self.start_date = start_date
        self.end_date = end_date

    id = Column(Integer, primary_key=True)
    price_list_id = Column('fk_price_list_id', Integer, ForeignKey(
        'service_pricelist.id'), nullable=False)
    account_id = Column('fk_account_id', Integer,
                        ForeignKey('account.id'), nullable=False)
    start_date = Column(DateTime(), nullable=False)
    end_date = Column(DateTime(), nullable=True)

    def __repr__(self):
        return "<Model:AccountsPrices(%s, %s, %s, %s, %s)>" % (
            self.id, self.account_id, self.price_list_id, self.start_date, self.end_date)


class ServicePriceMetricThresholds(Base):
    """Service metric type limit
    """
    __tablename__ = 'service_price_metric_thresholds'
    __table_args__ = (Index('udx_service_price_metric_threshold', 'from_ammount', 'fk_service_price_metric_id',
                            unique=True), {'mysql_engine': 'InnoDB'})

    id = Column(Integer, primary_key=True)
    price = Column(Float, nullable=False, default=0.00)
    from_ammount = Column(Float, nullable=False, default=0.00)
    till_ammount = Column(Float, nullable=True)
    service_price_metric_id = Column('fk_service_price_metric_id', Integer(), ForeignKey('service_price_metric.id'),
                                     nullable=False)

    def __init__(self, from_ammount, service_price_metric_id, till_ammount=None, price=0.00):
        self.from_ammount = from_ammount
        self.till_ammount = till_ammount
        self.service_price_metric_id = service_price_metric_id
        self.price = price

    def __repr__(self):
        return '<%s id=%s, from_ammount=%s ,till_ammount=%s ,service_price_metric_id=%s,price=%s >' % (
            self.__class__.__name__,
            self.id,
            self.from_ammount,
            self.till_ammount,
            self.service_price_metric_id,
            self.price)


class ServicePriceMetric(BaseApiBusinessObject, Base):
    """ServicePriceMetric describe the service type functionality.
    """
    __tablename__ = 'service_price_metric'
    __table_args__ = (Index('udx_price_metric_1', u"fk_price_list_id", u"fk_metric_type_id", unique=True),
                      {'mysql_engine': 'InnoDB'})

    price = Column(Float, nullable=False, default=0.00)
    # {'YEAR', 'MONTH', 'DAY', 'HOUR', 'DAY', 'MINUTE', 'SECOND'}
    time_unit = Column(String(10), nullable=False)
    # {'SIMPLE', 'SLICE', 'THRESHOLD'}
    price_type = Column(String(10), nullable=False)
    metric_type_id = Column('fk_metric_type_id', Integer(),
                            ForeignKey('service_metric_type.id'))
    price_list_id = Column('fk_price_list_id', Integer(),
                           ForeignKey('service_pricelist.id'))
    price_list = relationship(
        "ServicePriceList", back_populates="metrics_prices")
    thresholds = relationship(
        'ServicePriceMetricThresholds', backref='fk_service_price_metric_id')

    def __init__(self, objid, name, price, time_unit, metric_type_id, price_list_id, desc='', active=True,
                 price_type='SIMPLE'):
        BaseApiBusinessObject.__init__(self, objid, name, desc, active)
        self.price = price
        self.time_unit = time_unit
        self.metric_type_id = metric_type_id
        self.price_list_id = price_list_id
        self.price_type = price_type

    def __repr__(self):
        return "<Model:ServicePriceMetric(%s, %s, %s, %s, %s)>" % (
            self.id, self.uuid, self.name, self.price_type, self.active)


AggregateCostMonth = Table(
    'v_aggr_cost_month',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('fk_metric_type_id', Integer(),
           ForeignKey('service_metric_type.id')),
    Column('fk_account_id', Integer(), ForeignKey('account.id')),
    Column('cost', Integer()),
    Column('fk_cost_type_id', Integer(), ForeignKey('cost_type.id')),
    Column('period', String(10)),
    Column('evaluation_date', DateTime()),
    mysql_engine='InnoDB')
