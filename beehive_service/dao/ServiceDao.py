# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


import inspect
import logging
from sqlalchemy import create_engine, exc, asc, text
from datetime import datetime, timedelta, date
from beehive.common.data import transaction, query
from beehive.common.model import (
    AbstractDbManager,
    PaginatedQueryGenerator,
    PermTag,
    PermTagEntity,
    BaseEntity,
    ENTITY,
)
from beehive_service.model import (
    Account,
    ApiBusinessObject,
    ServiceType,
    ServiceDefinition,
    ServiceInstance,
    ServicePluginType,
    ServiceMetricType,
    ServiceMetric,
    ServiceMetricTypeLimit,
    AppliedBundle,
    AccountServiceDefinition,
)
from beehive_service.model.base import Base, SrvPluginTypeCategory, SrvStatusType
from beehive_service.model.service_link_instance import ServiceLinkInstance
from beehive_service.model.service_task_interval import ServiceTaskInterval
from beehive_service.model.service_job_schedule import ServiceJobSchedule
from beehive_service.model.service_job import ServiceJob
from beehive_service.model.views import ServiceInstantConsume

from beehive_service.model.aggreagate_cost import AggregateCost, AggregateCostType
from beehive_service.model.service_instance import (
    ServiceInstanceConfig,
    ServiceTypePluginInstance,
)
from beehive_service.model.service_link import ServiceLink
from beehive_service.model.service_tag import (
    ServiceTag,
    ServiceTagWithInstance,
    ServiceTagCount,
    ServiceTagOccurrences,
)
from beehive_service.model.service_catalog import ServiceCatalog
from beehive_service.model.service_definition import ServiceConfig
from beehive_service.model.service_link_def import ServiceLinkDef
from beehive_service.model.service_process import ServiceProcess
from beehive_service.model.account_capability import (
    AccountCapabilityAssoc,
    AccountCapability,
)
from beehive_service.model.deprecated import (
    Agreement,
    Wallet,
    ReportCost,
    ServiceCostParam,
    CostType,
    MetricTypePluginType,
    ServicePriceList,
    DivisionsPrices,
    AccountsPrices,
    ServicePriceMetricThresholds,
    ServicePriceMetric,
)
from beehive_service.model.division import Division
from beehive_service.model.organization import Organization
from beehive_service.model.service_status import ServiceStatus
from beehive_service.model.monitoring_message import MonitoringMessage
from beehive_service.model.monitoring_parameter import MonitoringParameter
from sqlalchemy.orm.session import sessionmaker, Session
from sqlalchemy.orm.query import Query

from re import match
from beecell.db import ModelError
from sqlalchemy.sql.expression import and_, or_, column, distinct, case, delete
from beecell.simple import truncate, format_date
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.expression import text
from sqlalchemy.orm.util import aliased
from typing import List, Type, Tuple, Any, Union, Dict


serviceBase = Base


class ServiceDbManager(AbstractDbManager):
    """ """

    @staticmethod
    def generate_task_intervals_acquire_metrics():
        task = "acq_metric"
        delta_interval = 30
        name_prefix = "task_acqm"

        return ServiceDbManager.generate_task_interval(task, name_prefix, delta_interval)

    @staticmethod
    def populate(db_uri):
        """ """
        AbstractDbManager.create_table(db_uri)
        data = [
            ServiceStatus(id=1, name="ACTIVE"),
            ServiceStatus(id=2, name="BUILDING"),
            ServiceStatus(id=3, name="PENDING"),
            ServiceStatus(id=4, name="CREATED"),
            ServiceStatus(id=5, name="DELETING"),
            ServiceStatus(id=6, name="DELETED"),
            ServiceStatus(id=7, name="ERROR"),
            ServiceStatus(id=8, name="RELEASED"),
            ServiceStatus(id=9, name="DRAFT"),
            ServiceStatus(id=10, name="DEPRECATED"),
            ServiceStatus(id=11, name="EXPUNGING"),
            ServiceStatus(id=12, name="EXPUNGED"),
            ServiceStatus(id=13, name="SYNCHRONIZE"),
            ServiceStatus(id=14, name="UPDATING"),
            ServiceStatus(id=15, name="STARTING"),
            ServiceStatus(id=16, name="STOPPING"),
            ServiceStatus(id=17, name="STOPPED"),
            ServiceStatus(id=18, name="TERMINATED"),
            ServiceStatus(id=19, name="SHUTTING-DOWN"),
            ServiceStatus(id=20, name="UNKNOWN"),
            ServiceStatus(id=21, name="ERROR_CREATION"),
            ServiceStatus(id=22, name="CLOSED"),
            ServicePluginType(
                id=1,
                name_type="Dummy",
                objclass="beehive_service.plugins.dummy.controller.ApiDummySTContainer",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=2,
                name_type="Dummy",
                objclass="beehive_service.plugins.dummy.controller.ApiDummySTChild",
                category=None,
            ),
            ServicePluginType(
                id=3,
                name_type="Dummy",
                objclass="beehive_service.plugins.dummy.controller.ApiDummySTAsyncChild",
                category=None,
            ),
            ServicePluginType(
                id=4,
                name_type="Dummy",
                objclass="beehive_service.plugins.dummy.controller.ApiDummySTCamundaChild",
                category=None,
            ),
            ServicePluginType(
                id=5,
                name_type="ComputeService",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=6,
                name_type="ComputeInstance",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeInstance",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=7,
                name_type="ComputeImage",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeImage",
                category=None,
            ),
            ServicePluginType(
                id=8,
                name_type="ComputeVPC",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeVPC",
                category=None,
            ),
            ServicePluginType(
                id=9,
                name_type="ComputeSubnet",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeSubnet",
                category=None,
            ),
            ServicePluginType(
                id=10,
                name_type="ComputeSecurityGroup",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeSecurityGroup",
                category=None,
            ),
            ServicePluginType(
                id=11,
                name_type="ComputeVolume",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeVolume",
                category=None,
            ),
            ServicePluginType(
                id=12,
                name_type="ComputeKeyPairs",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeKeyPairs",
                category=None,
            ),
            ServicePluginType(
                id=13,
                name_type="ComputeLimits",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeLimits",
                category=None,
            ),
            ServicePluginType(
                id=14,
                name_type="ComputeAddress",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeAddress",
                category=None,
            ),
            ServicePluginType(
                id=15,
                name_type="DatabaseService",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=16,
                name_type="DatabaseInstance",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceInstance",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=17,
                name_type="DatabaseSchema",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceSchema",
                category=None,
            ),
            ServicePluginType(
                id=18,
                name_type="DatabaseUser",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceUser",
                category=None,
            ),
            ServicePluginType(
                id=19,
                name_type="DatabaseBackup",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceBackup",
                category=None,
            ),
            ServicePluginType(
                id=20,
                name_type="DatabaseLog",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceLog",
                category=None,
            ),
            ServicePluginType(
                id=21,
                name_type="DatabaseSnapshot",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceSnapshot",
                category=None,
            ),
            ServicePluginType(
                id=22,
                name_type="DatabaseTag",
                objclass="beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceTag",
                category=None,
            ),
            ServicePluginType(
                id=23,
                name_type="StorageService",
                objclass="beehive_service.plugins.storageservice.controller.ApiStorageService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=24,
                name_type="StorageEFS",
                objclass="beehive_service.plugins.storageservice.controller.ApiStorageEFS",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=25,
                name_type="ComputeTag",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeTag",
                category=None,
            ),
            ServicePluginType(
                id=26,
                name_type="AppEngineService",
                objclass="beehive_service.plugins.appengineservice.controller.ApiAppEngineService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=27,
                name_type="AppEngineInstance",
                objclass="beehive_service.plugins.appengineservice.controller.ApiAppEngineInstance",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=28,
                name_type="ComputeTemplate",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeTemplate",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=29,
                name_type="NetworkService",
                objclass="beehive_service_netaas.networkservice.controller.ApiNetworkService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=30,
                name_type="NetworkGateway",
                objclass="beehive_service_netaas.networkservice.controller.ApiNetworkGateway",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            # aggiunte mancavano rispetto al db
            ServicePluginType(
                id=31,
                name_type="VirtualService",
                objclass="beehive_service.entity.service_type.ApiServiceType",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=32,
                name_type="ComputeCustomization",
                objclass="beehive_service.plugins.computeservice.controller.ApiComputeCustomization",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            # per logging
            ServicePluginType(
                id=33,
                name_type="LoggingService",
                objclass="beehive_service.plugins.loggingservice.controller.ApiLoggingService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=34,
                name_type="LoggingSpace",
                objclass="beehive_service.plugins.loggingservice.controller.ApiLoggingSpace",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=35,
                name_type="LoggingInstance",
                objclass="beehive_service.plugins.loggingservice.controller.ApiLoggingInstance",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            # per monitoring
            ServicePluginType(
                id=36,
                name_type="MonitoringService",
                objclass="beehive_service.plugins.loggingservice.controller.ApiMonitoringService",
                category=SrvPluginTypeCategory.CONTAINER,
            ),
            ServicePluginType(
                id=37,
                name_type="MonitoringSpace",
                objclass="beehive_service.plugins.loggingservice.controller.ApiMonitoringSpace",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            ServicePluginType(
                id=38,
                name_type="MonitoringInstance",
                objclass="beehive_service.plugins.loggingservice.controller.ApiMonitoringInstance",
                category=SrvPluginTypeCategory.INSTANCE,
            ),
            CostType(
                id=AggregateCostType.CALC_OK_ID,
                name=AggregateCostType.CALC_OK,
                desc="AggregateCost calculated on daily metrics",
            ),
            CostType(
                id=AggregateCostType.NO_METRIC_ID,
                name=AggregateCostType.NO_METRIC,
                desc="No metrics found. Refill with AggregateCost of previous day",
            ),
            CostType(
                id=AggregateCostType.NO_PRICELIST_ID,
                name=AggregateCostType.NO_PRICELIST,
                desc="No price found for metric type",
            ),
        ]

        # task intervals acquire metrics
        data.extend(ServiceDbManager.generate_task_intervals_acquire_metrics())

        migrations = [
            {
                "statement": """
                create or replace view v_service_instant_consume as
                SELECT
                    MIN(sm.creation_date)  creation_date,
                    MIN(sm.modification_date)  modification_date,
                    null expiry_date,
                    MIN(sm.id) id,
                    ANY_VALUE(IFNULL(cpt.name_type, pt.name_type))  plugin_name,
                    mt.name metric_group_name,
                    sum(sm.value) metric_instant_value,
                    MIN(mt.measure_unit) metric_unit,
                    null metric_value,
                    IFNULL(sc.id, si.id) fk_service_instance_id,
                    MIN(si.fk_account_id) fk_account_id,
                    MIN(sm.fk_job_id) fk_job_id
                FROM
                    service_metric sm
                    inner join service_metric_type mt on sm.fk_metric_type_id = mt.id
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
                    INNER JOIN account ac ON ac.id = si.fk_account_id
                    -- plugin
                    INNER JOIN service_definition sd ON si.fk_service_definition_id = sd.id
                    INNER JOIN service_type st ON sd.fk_service_type_id = st.id
                    INNER JOIN service_plugin_type pt ON st.objclass  = pt.objclass
                    -- container
                    LEFT OUTER JOIN service_link_inst  li ON li.end_service_id  = si.id
                    LEFT OUTER JOIN service_instance sc ON li.start_service_id  = sc.id
                    LEFT OUTER JOIN service_definition scd ON sc.fk_service_definition_id = scd.id
                    LEFT OUTER JOIN service_type sct ON scd.fk_service_type_id = sct.id
                    LEFT OUTER JOIN service_plugin_type cpt ON sct.objclass  = cpt.objclass
                where sm.need_next = true
                GROUP BY IFNULL(sc.id, si.id), mt.name
                """
            },
            {
                "test": """select (COUNT(*)=0) from information_schema.COLUMNS
                         where TABLE_NAME = 'service_price_metric' and TABLE_SCHEMA= DATABASE()
                         and COLUMN_NAME = 'price_type' """,
                "statement": """ ALTER TABLE `service`.`service_price_metric` ADD COLUMN `price_type` VARCHAR(10) NOT NULL default 'SIMPLE' AFTER `time_unit` """,
            },
            {
                "test": """select (COUNT(*)=1) from information_schema.COLUMNS
                         where TABLE_NAME = 'service_price_metric' and TABLE_SCHEMA= DATABASE()
                         and COLUMN_NAME = 'params' """,
                "statement": """ ALTER TABLE `service`.`service_price_metric` DROP COLUMN `params` """,
            },
            # drop  v_aggr_cost_month
            {
                "test": """select COUNT(*)=1
                    from information_schema.TABLES
                    where TABLE_SCHEMA=database()
                        and TABLE_NAME = 'v_aggr_cost_month'
                        and TABLE_TYPE='BASE TABLE'""",
                "statement": " DROP TABLE IF EXISTS `v_aggr_cost_month`",
            },
            # create view v_aggr_cost_month
            {
                "test": """SELECT  COUNT(*)=0
                    from information_schema.TABLES
                    where TABLE_SCHEMA=database()
                        and TABLE_NAME = 'v_aggr_cost_month'
                        and TABLE_TYPE='VIEW'""",
                "statement": """ CREATE OR REPLACE VIEW `v_aggr_cost_month` AS select
                        `aggregate_cost`.`id` AS `id`,
                        `aggregate_cost`.`fk_metric_type_id` AS `fk_metric_type_id`,
                        `service_instance`.`fk_account_id` AS `fk_account_id`,
                        sum(`aggregate_cost`.`cost`) AS `cost`,
                        max(`aggregate_cost`.`fk_cost_type_id`) AS `fk_cost_type_id`,
                        substr(`aggregate_cost`.`period`, 1, 7) AS `period`,
                        now() AS `evaluation_date`
                    from
                        (`aggregate_cost`
                    join `service_instance` on
                        ((`aggregate_cost`.`fk_service_instance_id` = `service_instance`.`id`)))
                    group by
                        `aggregate_cost`.`id`,
                        `aggregate_cost`.`fk_metric_type_id`,
                        `service_instance`.`fk_account_id`,
                        substr(`aggregate_cost`.`period`, 1, 7) """,
            },
            {
                "test": "select (COUNT(*)=0) from information_schema.COLUMNS where TABLE_NAME = 'account' "
                "and TABLE_SCHEMA= DATABASE() and COLUMN_NAME = 'params'",
                "statement": "alter table account add column params text",
            },
            {
                "test": "select (COUNT(*)=0) from information_schema.COLUMNS "
                "where TABLE_NAME = 'service_plugin_type' and TABLE_SCHEMA= DATABASE() "
                "and COLUMN_NAME = 'category'",
                "statement": "ALTER TABLE service_plugin_type ADD COLUMN category VARCHAR(100) NULL AFTER objclass;",
            },
            {
                "test": "select (COUNT(*)=0) from information_schema.COLUMNS "
                "where TABLE_NAME = 'account_capabilities' and TABLE_SCHEMA= DATABASE() "
                "and COLUMN_NAME = 'plugin_name'",
                "statement": "alter table account_capabilities add column plugin_name varchar(100)",
            },
            {
                "test": "select (COUNT(*)=0) from information_schema.COLUMNS "
                "where TABLE_NAME = 'account_account_capabilities' and TABLE_SCHEMA= DATABASE() "
                "and COLUMN_NAME = 'status'",
                "statement": "alter table account_account_capabilities add column status varchar(20) "
                "default 'BUILDING'",
            },
            {
                "statement": "CREATE OR REPLACE VIEW v_instance_vert \
                    (\
                      root,\
                      inst1,\
                      inst2,\
                      inst3\
                    )\
                    AS  \
                    select si_root.id as root, \
                           l1.end_service_id as inst1,\
                           l2.end_service_id as inst2,\
                           l3.end_service_id as inst3\
                    from service_instance si_root \
                      left join service_link_inst l0 on l0.end_service_id= si_root.id\
                      left join service_link_inst l1 on        si_root.id= l1.start_service_id \
                      left join service_link_inst l2 on l1.end_service_id= l2.start_service_id \
                      left join service_link_inst l3 on l2.end_service_id= l3.start_service_id \
                    where l0.id is null"
            },
            {
                "statement": "CREATE OR REPLACE VIEW v_instance_horiz\
                (  parent, child, liv_par, liv_chi)\
                AS   \
                select distinct v.parent, v.child, v.liv_par, v.liv_chi\
                from (\
                    select  root as parent,  root as child,  0 as liv_par, 0 as liv_chi from v_instance_vert\
                    union all\
                    select  root as parent,  inst1 as child, 0 as liv_par, 1 as liv_chi from v_instance_vert\
                    union all\
                    select  root as parent,  inst2 as child, 0 as liv_par, 2 as liv_chi from v_instance_vert\
                    union all\
                    select  root as parent,  inst3 as child, 0 as liv_par, 3 as liv_chi from v_instance_vert\
                    union all\
                    select  inst1 as parent, inst1 as child, 1 as liv_par, 1 as liv_chi from v_instance_vert\
                    union all\
                    select  inst1 as parent, inst2 as child, 1 as liv_par, 2 as liv_chi from v_instance_vert\
                    union all\
                    select  inst1 as parent, inst3 as child, 1 as liv_par, 3 as liv_chi from v_instance_vert\
                    union all\
                    select  inst2 as parent, inst2 as child, 2 as liv_par, 2 as liv_chi from v_instance_vert\
                    union all\
                    select  inst2 as parent, inst3 as child, 2 as liv_par, 3 as liv_chi from v_instance_vert\
                    union all\
                    select  inst3 as parent, inst3 as child, 3 as liv_par, 3 as liv_chi from v_instance_vert\
                ) v\
                where v.parent is not null and v.child is not null"
            },
            {
                "statement": "CREATE OR REPLACE VIEW v_applied_bundle_acc\
                (\
                  acc_id,\
                  acc_name,\
                  metric_type_id,\
                  start_date,\
                  end_date,\
                  name,\
                  group_name,\
                  num_bundle,\
                  qta,\
                  limit_mt,\
                  measure_unit,\
                  value\
                ) as \
                select ac.id, \
                  ac.name, \
                  mt.id, \
                  pb.start_date, \
                  pb.end_date, \
                  mt.name,\
                  mt.group_name,\
                  SUM(case when pb.id is null then 0 else 1 end) as num_bundle, \
                  sum(pb.qta) as qta,\
                  max(mt_lim.name) as limit_mt,\
                  max(mt_lim.measure_unit) as measure_unit,\
                  SUM(coalesce(mtl.value, 0)) as value\
                from account ac\
                  left join applied_bundle pb on pb.fk_account_id = ac.id\
                  left join service_metric_type mt on mt.id = pb.fk_metric_type_id and mt.metric_type != 'CONSUME'\
                  left join service_metric_type_limit mtl on mtl.parent_id = mt.id \
                  left join service_metric_type mt_lim on mt_lim.id = mtl.fk_metric_type_id\
                group by ac.id, ac.name, pb.fk_metric_type_id, pb.start_date, pb.end_date"
            },
        ]
        try:
            engine = create_engine(db_uri)
            db_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
            session = db_session()
            for item in data:
                try:
                    session.merge(item)
                    # logger.info('Add item : %s' % item)
                    session.commit()
                except Exception:
                    session.rollback()
                    # logger.warn(ex)

            # logger.info('Populate tables on : %s' % (db_uri))

            # execute migration statements
            connection = engine.connect()
            for item in migrations:
                sql = item.get("test")
                test = True
                if sql is not None:
                    try:
                        result = connection.execute(sql)
                        row = result.fetchone()
                        test = bool(row[0])
                        result.close()
                    except Exception:
                        test = False
                else:
                    test = True
                if test:
                    sql = item.get("statement")
                    if sql is not None:
                        try:
                            result = connection.execute(sql)
                            result.close()
                        except Exception:
                            pass
            connection.close()
            del engine
        except exc.DBAPIError as ex:
            raise exc.DBAPIError(ex)

    @staticmethod
    def generate_task_interval(task, name_prefix, delta_interval):
        task_intervals = []

        start_date = datetime(1970, 1, 1, 00, 00, 00)
        end_date = datetime(1970, 1, 1, 00, 00, 00)

        for task_num in range(1, 49):
            end_date = end_date + timedelta(minutes=delta_interval)
            task_interval = ServiceTaskInterval(task, name_prefix + "_%s" % task_num, start_date, end_date, task_num)
            task_intervals.append(task_interval)
            start_date = start_date + timedelta(minutes=30)

        return task_intervals

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table"
        statements in raw SQL."""
        AbstractDbManager.create_table(db_uri)

        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=1;")
            serviceBase.metadata.create_all(engine)
            # logger.info('Create tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    @staticmethod
    def remove_table(db_uri):
        """Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        AbstractDbManager.remove_table(db_uri)

        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=0;")
            serviceBase.metadata.drop_all(engine)
            # logger.info('Remove tables from : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            # logger.error('', exc_info=1)
            raise Exception(e)

    def get_api_bo_paginated_entities(
        self, entity: Type[ENTITY], filters: List[str], *args, **kvargs
    ) -> Tuple[List[ENTITY], int]:
        if "filter_expired" in kvargs and kvargs.get("filter_expired") is not None:
            kvargs.update(filter_expiry_date=datetime.today())

        res, total = self.get_paginated_entities(entity, filters=filters, *args, **kvargs)
        return res, total

    def query_entities(
        self,
        entityclass: Type[ENTITY],
        session: Session,
        oid: Union[str, int] = None,
        objid: str = None,
        uuid: str = None,
        name: str = None,
        *args,
        **kvargs,
    ) -> Query:
        """Get model entities query

        :param entityclass: entity model class
        :param session: db session
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :return: list of entityclass
        :raises ModelError: raise :class:`ModelError`
        """
        if oid is not None:
            query = session.query(entityclass).filter_by(id=oid)
        elif objid is not None:
            query = session.query(entityclass).filter_by(objid=objid)
        elif uuid is not None:
            query = session.query(entityclass).filter_by(uuid=uuid)
        elif name is not None:
            query = session.query(entityclass).filter_by(name=name)
        else:
            msg = "No %s found" % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        query = query.filter_by(**kvargs)

        return query

    @query
    def get_entity(
        self,
        entityclass: Type[ENTITY],
        oid: Union[str, int],
        for_update: bool = False,
        *args,
        **kvargs,
    ) -> ENTITY:
        """Parse oid and get entity entity by name or by model id or by uuid
        :param active: is a boolean [optional]
        :param filter_expired: is a boolean [optional]
        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """

        filter_expired = False
        filter_expiry_date = datetime.today()
        active = None
        query = None

        if "active" in kvargs and kvargs.get("active") is not None:
            active = kvargs.pop("active")

        if "filter_expired" in kvargs and kvargs.get("filter_expired") is not None:
            filter_expired = kvargs.pop("filter_expired")

        session = self.get_session()

        # get obj by uuid
        if match("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(oid)):
            self.logger.debug2("Query %s by uuid: %s" % (entityclass.__name__, str(oid)))
            query = self.query_entities(entityclass, session, uuid=str(oid), *args, **kvargs)
        # get obj by id
        elif match("^\d+$", str(oid)):
            self.logger.debug2("Query %s by id: %s" % (entityclass.__name__, str(oid)))
            query = self.query_entities(entityclass, session, oid=oid, *args, **kvargs)
        # get obj by name
        elif match("[\-\w\d]+", str(oid)):
            self.logger.debug2("Query %s by name: %s" % (entityclass.__name__, str(oid)))
            query = self.query_entities(entityclass, session, name=oid, *args, **kvargs)
        else:
            raise ModelError("%s %s not found" % (entityclass, oid))

        if issubclass(entityclass, BaseEntity) == True:
            if active is not None:
                query = query.filter(entityclass.active == active)
            # expired
            if filter_expired is not None:
                if filter_expired is True:
                    query = query.filter(entityclass.expiry_date <= filter_expiry_date)
                else:
                    query = query.filter(
                        or_(
                            entityclass.expiry_date == None,
                            entityclass.expiry_date > filter_expiry_date,
                        )
                    )

        entity: ENTITY = None
        if for_update:
            entity = query.with_for_update().one_or_none()
            self.logger.debug2("Get %s FOR UPDATE : %s" % (entityclass.__name__, truncate(query)))
        else:
            entity = query.one_or_none()
        self.logger.debug2("Get %s %s" % (entityclass.__name__, oid))

        return entity

    ###################################
    ####  AccountServiceDefinition  ###
    ###################################
    @query
    def get_paginated_account_service_definitions(
        self,
        account_id: int = None,
        service_definition_id: int = None,
        plugintype: str = None,
        category: str = None,
        only_container: bool = False,
        *args,
        **kvargs,
    ) -> Tuple[List[AccountServiceDefinition], int]:
        """Get paginated AccountServiceDefinition.

        :param account_id:
        :param service_definition_id:
        :param plugintype:
        :param category:
        :param only_container:
        :param args:
        :param kvargs:
        :return: list of paginated ServiceJobSchedule
        :raises TransactionError: raise :class:`TransactionError`
        """
        kvargs["def_active"] = True
        kvargs["with_perm_tag"] = False

        if plugintype is not None or category is not None or only_container:
            joins = [  # table, alias, on, left, inner
                (
                    "service_definition",
                    "t4",
                    "t3.fk_service_definition_id=t4.id",
                    False,
                    True,
                ),
                ("service_type", "t5", "t4.fk_service_type_id=t5.id", False, True),
                ("service_plugin_type", "t6", "t5.objclass=t6.objclass", False, True),
            ]
            kvargs["run2"] = True
            kvargs["joins"] = joins
        else:
            joins = [  # table, alias, on, left, inner
                (
                    "service_definition",
                    "t4",
                    "t3.fk_service_definition_id=t4.id",
                    False,
                    True,
                )
            ]
            kvargs["run2"] = True
            kvargs["joins"] = joins

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        filters.append(PaginatedQueryGenerator.create_sqlfilter("def_active", column="active", alias="t4"))

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id", column="fk_account_id"))
            kvargs["account_id"] = account_id

        if service_definition_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_definition_id", column="fk_service_definition_id")
            )
            kvargs["service_definition_id"] = service_definition_id

        if plugintype is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("plugintype", column="name_type", alias="t6"))
            kvargs["plugintype"] = plugintype

        if category is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_category", column="service_category", alias="t6")
            )
            kvargs["service_category"] = category

        if only_container:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("category", column="category", alias="t6"))
            kvargs["category"] = "CONTAINER"

        kvargs.update(
            account_id=account_id,
            service_definition_id=service_definition_id,
            with_perm_tag=False,
        )

        res, total = self.get_api_bo_paginated_entities(AccountServiceDefinition, filters=filters, *args, **kvargs)
        return res, total

    #############################
    ### AccountCapabilityAssoc###
    #############################
    @query
    def get_bulding_capability_for_account(self, account_id: int) -> AccountCapabilityAssoc:
        session = self.get_session()
        assoc: AccountCapabilityAssoc = (
            session.query(AccountCapabilityAssoc)
            .filter_by(fk_account_id=account_id)
            .filter_by(status=SrvStatusType.BUILDING)
            .with_for_update()
            .first()
        )
        return assoc

    #############################
    ###    ServicePluginType  ###
    #############################
    @query
    def get_service_plugin_type(self, *args, **kvargs) -> List[ServicePluginType]:
        """Get plugin types used by service types

        :return:
        """
        session = self.get_session()
        query = session.query(ServicePluginType)

        if "plugintype" in kvargs and kvargs.get("plugintype") is not None:
            query = query.filter_by(name_type=kvargs.get("plugintype"))

        if "objclass" in kvargs and kvargs.get("objclass") is not None:
            query = query.filter_by(objclass=kvargs.get("objclass"))

        if "category" in kvargs and kvargs.get("category") is not None:
            query = query.filter_by(category=kvargs.get("category"))

        res: List[ServicePluginType] = query.all()
        return res

    @query
    def get_service_type(
        self,
        objclass: str = None,
        flag_container: str = None,
        status: str = None,
        plugintype: str = None,
        *args,
        **kvargs,
    ) -> ServiceType:
        session = self.get_session()
        if plugintype is not None:
            query = session.query(ServiceType, ServicePluginType)
            query = query.filter_by(name_type=plugintype)
        else:
            query = session.query(ServiceType)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if objclass is not None:
            query = query.filter_by(objclass=objclass)

        if flag_container is not None:
            query = query.filter_by(flag_container=flag_container)

        if status is not None:
            query = query.filter_by(status=status)

        tag: ServiceType = query.one_or_none()
        return tag

    @query
    def get_service_types(
        self,
        objclass: str = None,
        flag_container: str = None,
        status: str = None,
        plugintype: str = None,
        *args,
        **kvargs,
    ) -> List[ServiceType]:
        session = self.get_session()
        if plugintype is not None:
            query = session.query(ServiceType).join(ServicePluginType)
            query = query.filter(ServicePluginType.name_type == plugintype)
        else:
            query = session.query(ServiceType)

        query = self.add_base_entity_filters(query, *args, **kvargs)

        if objclass is not None:
            query = query.filter(ServiceType.objclass == objclass)

        if flag_container is not None:
            query = query.filter(ServiceType.flag_container == flag_container)

        if status is not None:
            query = query.filter(ServiceType.status == status)

        if "filter_expired" in kvargs and kvargs.get("filter_expired"):
            query = query.filter(ServiceType.active is True).filter(
                or_(
                    ServiceType.expiry_date is None,
                    ServiceType.expiry_date <= datetime.today(),
                )
            )

        res: List[ServiceType] = query.all()
        return res

    @query
    def get_paginated_service_types(
        self,
        objclass=None,
        flag_container=None,
        status=None,
        plugintype=None,
        type_ids=None,
        *args,
        **kvargs,
    ) -> Tuple[List[ServiceType], int]:
        """Get paginated ServiceType.

        :param objclass: class plugin implementation [optional]
        :param flag_container: boolean [optional]
        :param status: status [optional]
        :param plugintype: plugintype [optional]
        :param type_ids: type_ids [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceType
        :raises TransactionError: raise :class:`TransactionError`
        """
        tables = [("service_plugin_type", "t4")]

        filters: List[str] = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        filters.append("AND t3.objclass=t4.objclass")
        if plugintype is not None:
            filters.append("AND t4.name_type=:plugintype")

        if objclass is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("objclass"))

        if flag_container is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("flag_container"))

        if status is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("status"))

        if type_ids is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("type_ids", "id", op_comparison=" in "))

        kvargs.update(
            objclass=objclass,
            flag_container=flag_container,
            status=status,
            plugintype=plugintype,
            type_ids=type_ids,
        )

        res: List[ServiceType]
        total: int
        res, total = self.get_api_bo_paginated_entities(ServiceType, tables=tables, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def update_service_type(self, *args, **kvargs) -> ServiceType:
        """Update ServiceType.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceType`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res: ServiceType = self.update_entity(ServiceType, *args, **kvargs)
        return res

    #############################
    ###    ServiceCostParam   ###
    #############################
    @query
    def get_service_cost_param(
        self,
        fk_service_type_id=None,
        param_unit=None,
        param_definition=None,
        *args,
        **kvargs,
    ):
        session = self.get_session()
        query = session.query(ServiceCostParam)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_service_type_id is not None:
            query = query.filter_by(fk_service_type_id=fk_service_type_id)

        if param_definition is not None:
            query = query.filter_by(param_definition=param_definition)

        if param_unit is not None:
            query = query.filter_by(param_unit=param_unit)

        tag = query.one_or_none()
        return tag

    @query
    def get_service_cost_params(
        self,
        fk_service_type_id=None,
        param_unit=None,
        param_definition=None,
        *args,
        **kvargs,
    ):
        """Get all filtered ServiceCostParam.

        :param fk_service_type_id: id service [optional]
        :param param_unit: parameter unit format [optional]
        :param param_definition:  [optional]
        :return: list of ServiceCostParam
        :raises TransactionError: raise :class:`TransactionError`
        """

        session = self.get_session()
        query = session.query(ServiceCostParam)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_service_type_id is not None:
            query = query.filter_by(fk_service_type_id=fk_service_type_id)

        if param_unit is not None:
            query = query.filter_by(param_unit=param_unit)

        if param_definition is not None:
            query = query.filter_by(param_definition=param_definition)

        res = query.all()
        return res

    @query
    def get_paginated_service_cost_params(
        self,
        service_type_id=None,
        param_unit=None,
        param_definition=None,
        *args,
        **kvargs,
    ):
        """Get paginated ServiceCostParam.

        :param fk_service_type_id: id service [optional]
        :param param_unit: parameter unit format [optional]
        :param param_definition:  [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceCostParam
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        if service_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_type_id", "fk_service_type_id"))

        if param_unit is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("param_unit"))

        if param_definition is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("param_definition"))

        res, total = self.get_api_bo_paginated_entities(
            ServiceCostParam,
            filters=filters,
            service_type_id=service_type_id,
            param_unit=param_unit,
            param_definition=param_definition,
            with_perm_tag=False,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def update_service_cost_param(self, *args, **kvargs):
        """Update ServiceCostParam.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceCostParam`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceCostParam, *args, **kvargs)
        return res

    #############################
    #  Call delle stored procedure
    #############################
    # @transaction
    def call_smsmpopulate(self, transactlimit=10000):
        """
        call  stored procedure smsmpopulate .

        :return: None
        """
        session = self.get_session()
        self.logger.debug2("Calling  smsmpopulate( %d ) " % transactlimit)
        session.execute(text("call smsmpopulate(:param)"), {"param": transactlimit})

    # @transaction
    def call_dailyconsumes_by_account(self, account_id, period, jobid):
        """
        call
        PROCEDURE dailyconsumes_by_account( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
        :param int account_id:  id account
        :param string period: string describing period
        :param jobid: job id for string

        :return: None
        """
        session = self.get_session()
        self.logger.debug2("Calling  dailyconsumes_by_account(%d, '%s', %d)" % (account_id, period, jobid))

        session.execute(
            text("CALL dailyconsumes_by_account(:account_id, :period, :jobid)"),
            {"account_id": account_id, "period": period, "jobid": jobid},
        )

    # TODO verificare perche'
    # con TRANSACTION va in time out
    # la procedura gestisce i commit ed evita di avere transazioni troppo groosse che rischiano di mandar in crisi il DB
    # @transaction
    def call_dailyconsumes(self, period, jobid, launchasync=True):
        """
        call PROCEDURE dailyconsumes( in p_period varchar(10), in jobid  INTEGER )
        :param string period: string describing period
        :param jobid: job id for string
        :return: None
        """
        session = self.get_session()
        self.logger.debug2("Calling  dailyconsumes('%s', %d)" % (period, jobid))

        sql = "CALL dailyconsumes(:period, :jobid)"

        session.execute(text(sql), {"period": period, "jobid": jobid})

    # @transaction
    def call_dailycosts(self, period, jobid):
        """
        call PROCEDURE dailycosts(in p_period varchar(10), in jobid  INTEGER )
        :param string period: string describing period
        :param jobid: job id for string
        :return: None
        """
        session = self.get_session()
        self.logger.debug2("Calling  dailycosts('%s', %d)" % (period, jobid))

        session.execute(text("CALL dailycosts(:period, :jobid)"), {"period": period, "jobid": jobid})

    @query
    def monit_message_at(self, period: str = None) -> MonitoringMessage:
        if period is None:
            period = (date.today() - timedelta(days=1)).isoformat()
        session = self.get_session()
        query = session.query(MonitoringMessage).filter_by(period=period)
        res = query.one_or_none()
        return res

    @transaction
    def call_monitoring_proc(self) -> Tuple[str, str]:
        """
        call PROCEDURE monitoring procedure dailycosts(in p_period varchar(10), in jobid  INTEGER )
        CALL do_monit();
        SELECT msg, recipent FROM log_monit WHERE period = DATE_SUB(DATE(NOW()), INTERVAL 1 DAY);

        :return: str, str
        """

        session = self.get_session()
        self.logger.debug2("calling monitors cecks")
        session.execute(text("CALL do_monit()"))
        msg = self.monit_message_at()
        if msg is None:
            return None, None
        return msg.msg, msg.recipient

    #############################
    ###    ServiceProcess   ###
    #############################
    @query
    def get_dummy_process_id(self) -> int:
        session: Session = self.get_session()
        sqlstmnet = "select id from service_job limit 1"
        result = session.execute(text(sqlstmnet)).first()
        if result is None:
            return None
        return result.id

    @query
    def get_service_process(
        self,
        fk_service_type_id=None,
        method_key=None,
        process_key=None,
        *args,
        **kvargs,
    ):
        session = self.get_session()
        query = session.query(ServiceProcess)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_service_type_id is not None:
            query = query.filter_by(fk_service_type_id=fk_service_type_id)

        if method_key is not None:
            query = query.filter_by(method_key=method_key)

        if process_key is not None:
            query = query.filter_by(process_key=process_key)

        tag = query.one_or_none()
        return tag

    @query
    def get_service_processes(
        self,
        fk_service_type_id=None,
        method_key=None,
        process_key=None,
        *args,
        **kvargs,
    ):
        """Get all filtered ServiceProcess.

        :param service_type_id: id service type [optional]
        :param method_key: method key [optional]
        :param process_key:  camunda process key [optional]
        :return: list of ServiceProcess
        :raises TransactionError: raise :class:`TransactionError`
        """

        session = self.get_session()
        query = session.query(ServiceProcess)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_service_type_id is not None:
            query = query.filter_by(fk_service_type_id=fk_service_type_id)

        if method_key is not None:
            query = query.filter_by(method_key=method_key)

        if process_key is not None:
            query = query.filter_by(process_key=process_key)

        res = query.all()
        return res

    @query
    def get_paginated_service_processes(self, service_type_id=None, method_key=None, process_key=None, *args, **kvargs):
        """Get paginated ServiceProcess.

        :param service_type_id: id service type [optional]
        :param method_key: method key [optional]
        :param process_key:  camunda process key [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceProcess
        :raises TransactionError: raise :class:`TransactionError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if service_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_type_id", "fk_service_type_id"))

        if method_key is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("method_key"))

        if process_key is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("process_key"))
        kvargs["with_perm_tag"] = False
        res, total = self.get_api_bo_paginated_entities(
            ServiceProcess,
            filters=filters,
            service_type_id=service_type_id,
            method_key=method_key,
            process_key=process_key,
            *args,
            **kvargs,
        )

        return res, total

    @transaction
    def update_service_process(self, *args, **kvargs):
        """Update ServiceProcess.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceProcess`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceProcess, *args, **kvargs)
        return res

    #############################
    ###    ServiceDefinition  ###
    #############################
    @query
    def get_service_definition(
        self,
        service_type_id=None,
        status=None,
        parent_id=None,
        plugintype=None,
        *args,
        **kvargs,
    ) -> Union[ServiceDefinition, None]:
        """"""
        session = self.get_session()
        query = session.query(ServiceDefinition)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if service_type_id is not None:
            query = query.filter_by(service_type_id=service_type_id)

        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)

        if status is not None:
            query = query.filter_by(status=status)

        tag = query.one_or_none()
        return tag

    @query
    def get_service_definition_by_config(self, config_field, config_value, *args, **kvargs):
        """Get service definition by internal config

        :param config_value: config field value
        :param config_field: config field name
        """
        session = self.get_session()
        filter = "JSON_CONTAINS(`params`, '\"%s\"', '$.%s')=1" % (
            config_value,
            config_field,
        )
        query = session.query(ServiceDefinition).join(ServiceConfig.service_definition).filter(text(filter))
        res = query.all()
        self.logger.debug2("Get service definitions by %s=%s: %s" % (config_field, config_value, res))
        return res

    @query
    def get_service_definitions(
        self,
        service_type_id=None,
        status=None,
        plugintype=None,
        is_default=None,
        name=None,
        *args,
        **kvargs,
    ) -> List[ServiceDefinition]:
        """Get all filtered ServiceDefinition.

        :param name: definition name [optional]
        :param service_type_id: id service type[optional]
        :param status: status service definition[optional]
        :param plugintype: plugin type for service type [optional]
        :param is_default: if True check if already exists a default service def [optional]
        :return: list of ServiceDefinition
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceDefinition).filter(ServiceDefinition.status != SrvStatusType.DELETED)

        query = self.add_base_entity_filters(query, *args, **kvargs)

        if name is not None:
            query = query.filter_by(name=name)

        if service_type_id is not None:
            query = query.filter_by(service_type_id=service_type_id)

        if is_default is not None:
            query = query.filter_by(is_default=is_default)

        if status is not None:
            query = query.filter_by(status=status)

        if plugintype is not None:
            query = query.join(ServiceType).join(ServicePluginType).filter(ServicePluginType.name_type == plugintype)

        self.print_query(
            self.get_service_definitions,
            query,
            inspect.getargvalues(inspect.currentframe()),
        )

        res = query.all()
        self.logger.debug2("Service definitions: %s" % res)
        return res

    @query
    def get_paginated_service_definitions(
        self,
        service_type_id=None,
        status=None,
        parent_id=None,
        plugintype=None,
        flag_container=None,
        catalogs=None,
        *args,
        **kvargs,
    ):
        """Get paginated ServiceDefinition.

        :param service_type_id: id service [optional]
        :param status: service defintion status [optional]
        :param parent_id: parent service defintion id [optional]
        :param plugintype: plugin type name [optional]
        :param flag_container: if True select only definition with type that is a container [optional]
        :param catalogs: comma sepaarted list of service catalog ids [optional]
        :param service_definition_id_list: list of service definitions id [optional]
        :param service_definition_uuid_list: list of service definitions uuid [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceDefinition
        :raises TransactionError: raise :class:`TransactionError`
        """
        tables = [("service_type", "t4"), ("service_plugin_type", "t5")]

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        filters.append("AND t3.fk_service_type_id=t4.id")
        filters.append("AND t4.objclass=t5.objclass")
        if plugintype is not None:
            filters.append("AND t5.name_type=:plugintype")

        if catalogs is not None:
            tables.append(("catalog_definition", "t6"))
            filters.append("AND t3.id = t6.fk_service_definition_id")
            filters.append("AND t6.fk_service_catalog_id in :catalogs")
            kvargs["catalogs"] = [int(c) for c in catalogs.split(",")]
            kvargs["with_perm_tag"] = False

        if (
            kvargs.get("id", None) is None
            and kvargs.get("service_definition_id_list") is not None
            and len(kvargs.get("service_definition_id_list")) > 0
        ):
            filters.append(" AND t3.id IN :listServiceID ")
            kvargs.update(listServiceID=tuple(kvargs.pop("service_definition_id_list")))

        if (
            kvargs.get("uuid", None) is None
            and kvargs.get("service_definition_uuid_list") is not None
            and len(kvargs.get("service_definition_uuid_list")) > 0
        ):
            filters.append(" AND t3.uuid IN :listServiceUUID ")
            kvargs.update(listServiceUUID=tuple(kvargs.pop("service_definition_uuid_list")))

        if service_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_type_id", "fk_service_type_id"))

        if status is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("status"))

        if parent_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("parent_id"))

        if flag_container is not None:
            filters.append("AND t4.flag_container=:flag_container")

        res, total = self.get_api_bo_paginated_entities(
            ServiceDefinition,
            tables=tables,
            filters=filters,
            service_type_id=service_type_id,
            status=status,
            parent_id=parent_id,
            plugintype=plugintype,
            flag_container=flag_container,
            *args,
            **kvargs,
        )
        return res, total

    '''
    @query
    def get_paginated_service_definitions_orig(self, service_type_id=None,
                status=None, parent_id=None,
                *args, **kvargs):


        """Get paginated ServiceDefinition.

        :param service_type_id: id service [optional]
        :param param_unit: parameter unit format [optional]
        :param param_definition:  [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceDefinition
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters( *args, **kvargs)
        if service_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter('service_type_id', 'fk_service_type_id'))

        if status is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter('status'))

        if parent_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter('parent_id'))

        res, total = self.get_api_bo_paginated_entities(ServiceDefinition, filters=filters,
                                                 service_type_id=service_type_id,
                                                 status=status, parent_id=parent_id,
                                                 with_perm_tag=False, *args, **kvargs)
        return res, total'''

    @transaction
    def update_service_definition(self, *args, **kvargs):
        """Update ServiceDefinition.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceDefinition`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceDefinition, *args, **kvargs)
        return res

    #############################
    ###    ServiceConfig      ###
    #############################
    @query
    def get_service_config(self, service_definition_id=None, params_type=None, *args, **kvargs):
        """Get only one or none filtered ServiceConfig.

        :param service_definition_id: id service definition [optional]
        :param params_type: format type {JSON, XML, ...} [optional]
        :return: one of ServiceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceConfig)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if service_definition_id is not None:
            query = query.filter_by(service_definition_id=service_definition_id)

        if params_type is not None:
            query = query.filter_by(params_type=params_type)

        cfg = query.one_or_none()
        return cfg

    @query
    def get_service_configs(self, service_definition_id=None, params_type=None, *args, **kvargs):
        """Get all filtered ServiceConfig.

        :param service_definition_id: id service definition [optional]
        :param params_type: format type {JSON, XML, ...} [optional]
        :return: list of ServiceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceConfig)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if service_definition_id is not None:
            query = query.filter_by(fk_service_definition_id=service_definition_id)
        if params_type is not None:
            query = query.filter_by(params_type=params_type)

        res = query.all()
        return res

    @query
    def get_paginated_service_configs(self, service_definition_id=None, params_type=None, *args, **kvargs):
        """Get paginated ServiceConfig.

        :param service_definition_id: id service definition [optional]
        :param params_type: format type {JSON, XML, ...} [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        if service_definition_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_definition_id", "fk_service_definition_id")
            )
        if params_type is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("params_type"))
        kvargs["with_perm_tag"] = False
        res, total = self.get_api_bo_paginated_entities(
            ServiceConfig,
            filters=filters,
            service_definition_id=service_definition_id,
            params_type=params_type,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def update_service_config(self, *args, **kvargs):
        """Update ServiceConfig.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceConfig`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceConfig, *args, **kvargs)
        return res

    #############################
    ###    ServiceCatalog     ###
    #############################

    @query
    def get_service_catalog(self, *args, **kvargs):
        """Get only one or none filtered ServiceCatalog.

        :return: one of ServiceCatalog
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceCatalog)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        catalog = query.one_or_none()
        return catalog

    @query
    def get_service_catalogs(self, *args, **kvargs):
        """Get all filtered ServiceCatalog.

        :return: list of ServiceCatalog
        :raises TransactionError: raise :class:`TransactionError`
        """

        session = self.get_session()
        query = session.query(ServiceCatalog)
        query = self.add_base_entity_filters(query, *args, **kvargs)
        catalogs = query.all()
        return catalogs

    @query
    def get_paginated_service_catalogs(self, *args, **kvargs):
        """Get paginated ServiceCatalog.
        :param id_list: list of account id [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceCatalog
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "id_list" in kvargs and kvargs.get("id_list", None) is not None and len(kvargs.get("id_list")) > 0:
            filters.append(" AND t3.id IN :listID ")
            kvargs.update(listID=tuple(kvargs.pop("id_list")))

        res, total = self.get_api_bo_paginated_entities(ServiceCatalog, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def update_service_catalog(self, *args, **kvargs):
        """Update ServiceCatalog

        :param int oid: entity id. [optional]
        :return: :class:`ServiceCatalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceCatalog, *args, **kvargs)
        return res

    #############################
    ###    ServiceInstance    ###
    #############################
    @query
    def count_service_instances_by_accounts(self, accounts=None):
        session = self.get_session()
        query = session.query(
            ServiceInstance.account_id,
            func.count(ServiceInstance.id),
            ServiceType.flag_container,
        )
        query = (
            query.join(
                ServiceDefinition,
                ServiceDefinition.id == ServiceInstance.service_definition_id,
            )
            .join(ServiceType, ServiceDefinition.service_type_id == ServiceType.id)
            .join(ServicePluginType, ServicePluginType.objclass == ServiceType.objclass)
            .filter(ServiceInstance.expiry_date == None)
        )

        if accounts is not None:
            query = query.filter(ServiceInstance.account_id.in_(accounts))

        query = query.group_by(ServiceInstance.account_id).group_by(ServiceType.flag_container)

        res = query.all()

        index = {}
        for r in res:
            if r[2] is True:
                key = "core"
            else:
                key = "base"
            if r[0] in index:
                index[r[0]][key] = r[1]
            else:
                index[r[0]] = {key: r[1]}
        self.logger.debug2("Get service instance count: %s" % truncate(str(index)))
        return index

    @query
    def count_all_service_instances_by_accounts(self, accounts=None, plugintype=None):
        session = self.get_session()
        query = session.query(
            func.count(ServiceInstance.id),
            ServiceInstance.account_id,
            ServicePluginType.name_type,
            ServiceType.flag_container,
        )
        query = (
            query.join(
                ServiceDefinition,
                ServiceDefinition.id == ServiceInstance.service_definition_id,
            )
            .join(ServiceType, ServiceDefinition.service_type_id == ServiceType.id)
            .join(ServicePluginType, ServicePluginType.objclass == ServiceType.objclass)
            .filter(ServiceInstance.expiry_date == None)
        )

        if accounts is not None:
            query = query.filter(ServiceInstance.account_id in accounts)

        if plugintype is not None:
            query = query.filter(ServicePluginType.name_type == plugintype)

        res = (
            query.group_by(ServiceInstance.account_id)
            .group_by(ServicePluginType.name_type)
            .group_by(ServiceType.flag_container)
            .all()
        )
        self.logger.debug2("Get service instance count: %s" % res)
        return res

    @query
    def get_service_instance_from_resource(self, resource_uuid: str) -> ServiceInstance:
        session: Session = self.get_session()
        query: Query = (
            session.query(ServiceInstance)
            .filter(ServiceInstance.resource_uuid == resource_uuid)
            .filter(ServiceInstance.expiry_date == None)
            .order_by(ServiceInstance.id)
            .limit(1)
        )
        # res : ServiceInstance = query.one_or_none()
        res: ServiceInstance = query.first()
        return res

    @query
    def get_service_info_from_resource(self, resource_uuid: str) -> Union[Dict, None]:
        session: Session = self.get_session()
        query = """
            SELECT
                si.id service_id,
                si.uuid service_uuid ,
                a.id account_id,
                a.uuid  account_uuid,
                si.resource_uuid
            from
                service_instance si
                inner join account a ON a.id = si.fk_account_id
            where
                si.expiry_date is null
                and si.resource_uuid  = :resource_uuid
            order by si.id asc
            limit 1
        """

        params = {"resource_uuid": resource_uuid}
        result = session.execute(text(query), params).first()
        if result is None:
            return None
        return {
            "service_id": result[0].service_id,
            "service_uuid": result[0].service_uuid,
            "account_id": result[0].account_id,
            "account_uuid": result[0].account_uuid,
            "resource_uuid": result[0].resource_uuid,
        }

    @query
    def get_service_info_for_account(self, accountid: Union[int, str]) -> Union[Dict, None]:
        """get_service_info_for_account
        return a dictionary of dictionary contaynong service info for alla service in accounts
        the key are resource_uuid so in case of multiple  service implemented by the same resource
        only the first (by id) service is appears in the dictionary

             {
                "resource_uuid1": {
                    "service_id" : service_id,
                    "service_uuid" : service_uuid,
                    "account_id" : account_id,
                    "account_uuid" : account_uuid,
                    "resource_uuid": resource_uuid
                },
                "resource_uuid2": {
                    "service_id" : service_id,
                    "service_uuid" : service_uuid,
                    "account_id" : account_id,
                    "account_uuid" : account_uuid,
                    "resource_uuid": resource_uuid
                }
             }

        """
        session: Session = self.get_session()
        query = """
            SELECT
                si.id service_id,
                si.uuid service_uuid,
                a.id account_id,
                a.uuid  account_uuid,
                si.resource_uuid
            from
                service_instance si
                inner join account a ON a.id = si.fk_account_id
            where
                si.expiry_date is null
                and a.%s = :account_id
            order by si.id asc
            """
        if type(accountid) == int or str(accountid).isdigit():
            accountid = int(accountid)
            query = query % "id"
        else:
            query = query % "uuid"

        params = {"account_id": accountid}
        result = session.execute(text(query), params=params).all()
        if result is None:
            return None
        ret = {}
        for r in result:
            if not r.resource_uuid in ret:
                ret[r.resource_uuid] = {
                    "service_id": r.service_id,
                    "service_uuid": r.service_uuid,
                    "account_id": r.account_id,
                    "account_uuid": r.account_uuid,
                    "resource_uuid": r.resource_uuid,
                }
        return ret

    @query
    def get_service_info(self, id: int = -99, uuid: str = "", resource_uuid: str = "") -> Union[Dict, None]:
        """get_service_info
        query by id uuid or resource_uuid
        return a dictionary of dictionary contaynong service info for alla service in accounts
        the key are resource_uuid so in case of multiple  service implemented by the same resource
        only the first (by id) service is appears in the dictionary
        {
            "service_id" : service_id,
            "service_uuid" : service_uuid,
            "account_id" : account_id,
            "account_uuid" : account_uuid,
            "resource_uuid": resource_uuid
        }
        """
        session: Session = self.get_session()
        query = """
            SELECT
                si.id service_id,
                si.uuid service_uuid,
                a.id account_id,
                a.uuid account_uuid,
                si.resource_uuid resource_uuid
            from
                service_instance si
                inner join account a ON a.id = si.fk_account_id
            where
                si.expiry_date is null
            """
        params = None
        if id > 0:
            query += " and si.id = :parameter order by si.id asc limit 1"
            params = {"serviceid": id}
        elif uuid != "":
            query += " and si.uuid = :parameter order by si.id asc limit 1"
            params = {"parameter": uuid}
        elif resource_uuid != "":
            query += " and si.resource_uuid = :parameter order by si.id asc limit 1"
            params = {"parameter": resource_uuid}
        else:
            raise Exception("erro get_service_info need any key to query id or uuid or resource_uuid")

        result = session.execute(text(query), params=params).first()
        if result is None:
            return None
        else:
            return {
                "service_id": result.service_id,
                "service_uuid": result.service_uuid,
                "account_id": result.account_id,
                "account_uuid": result.account_uuid,
                "resource_uuid": result.resource_uuid,
            }

    @query
    def get_service_instance(
        self,
        fk_account_id=None,
        fk_service_definition_id=None,
        status=None,
        bpmn_process_id=None,
        resource_uuid=None,
        plugintype=None,
        *args,
        **kvargs,
    ):
        """Get only one or none filtered ServiceInstance.

        :param fk_account_id: id account [optional]
        :param fk_service_definition_id: id service definition [optional]
        :param status: instance status [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param plugintype: plugin service type related to service instance[optional]
        :return: one of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstance)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_account_id is not None:
            query = query.filter_by(account_id=fk_account_id)

        if fk_service_definition_id is not None:
            query = query.filter_by(fk_service_definition_id=fk_service_definition_id)

        if status is not None:
            query = query.filter_by(status=status)

        if bpmn_process_id is not None:
            query = query.filter_by(bpmn_process_id=bpmn_process_id)

        if resource_uuid is not None:
            query = query.filter_by(resource_uuid=resource_uuid)

        if plugintype is not None:
            self.logger.info("Join on ServicePluginType for plugintype=%s" % plugintype)
            query = (
                query.join(
                    ServiceDefinition,
                    ServiceDefinition.id == ServiceInstance.service_definition_id,
                )
                .join(ServiceType, ServiceDefinition.service_type_id == ServiceType.id)
                .join(
                    ServicePluginType,
                    ServicePluginType.objclass == ServiceType.objclass,
                )
                .filter(ServicePluginType.name_type == plugintype)
            )

        res = query.one_or_none()
        return res

    @query
    def make_query_service_instances(
        self,
        fk_account_id=None,
        fk_service_definition_id=None,
        status=None,
        plugintype=None,
        bpmn_process_id=None,
        resource_uuid=None,
        parent_id=None,
        service_name_list=None,
        service_uuid_list=None,
        service_id_list=None,
        account_id_list=None,
        resource_uuid_list=None,
        tags=None,
        *args,
        **kvargs,
    ):
        """Get all filtered ServiceInstance.
            make query to get service instance.

        :param fk_account_id: id account [optional]
        :param fk_service_definition_id: id service definition [optional]
        :param status: instance status [optional]
        :param plugintype: plugin type name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param parent_id: service instance parent id[optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param service_name_list: list of name service instance [optional]
        :param service_uuid_list: list of uuid service instance[optional]
        :param service_id_list: list of id service instance[optional]
        :param account_id_list: list of account id related to service instance[optional]
        :param resource_uuid_list: ist of resource uuid related to service instance[optional]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstance)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if service_name_list is not None:
            query = query.filter(ServiceInstance.name.in_(service_name_list))

        if service_uuid_list is not None:
            query = query.filter(ServiceInstance.uuid.in_(service_uuid_list))

        if service_id_list is not None:
            query = query.filter(ServiceInstance.id.in_(service_id_list))

        if fk_account_id is not None:
            query = query.filter_by(account_id=fk_account_id)

        if account_id_list is not None:
            query = query.filter(ServiceInstance.account_id.in_(account_id_list))

        if fk_service_definition_id is not None:
            query = query.filter_by(service_definition_id=fk_service_definition_id)

        if status is not None:
            query = query.filter_by(status=status)

        if bpmn_process_id is not None:
            query = query.filter_by(bpmn_process_id=bpmn_process_id)

        if resource_uuid is not None:
            query = query.filter_by(resource_uuid=resource_uuid)

        if resource_uuid_list is not None:
            query = query.filter(ServiceInstance.resource_uuid.in_(resource_uuid_list))

        if plugintype is not None:
            self.logger.warning("Join on ServicePluginType for plugintype=%s" % plugintype)
            query = (
                query.join(
                    ServiceDefinition,
                    ServiceDefinition.id == ServiceInstance.service_definition_id,
                )
                .join(ServiceType, ServiceDefinition.service_type_id == ServiceType.id)
                .join(
                    ServicePluginType,
                    ServicePluginType.objclass == ServiceType.objclass,
                )
            )

            query = query.filter(ServicePluginType.name_type == plugintype)

        if parent_id is not None:
            self.logger.warning("Join on ServiceLinkInstance for parent_id=%s" % parent_id)
            query = query.join(ServiceInstance.linkParent).filter(ServiceLinkInstance.start_service_id == parent_id)

        if tags is not None:
            self.logger.info("tags filter = %s" % tags)
            query = query.join(PermTag, PermTag.value.in_(tags))
            query = query.join(
                PermTagEntity,
                and_(
                    ServiceInstance.id == PermTagEntity.entity,
                    PermTagEntity.tag == PermTag.id,
                ),
            )

        # ATTENTION: not insert filter here !!
        # self.logger.warning('query get_service_instances=%s' %query)

        return query

    @query
    def count_service_instances(
        self,
        fk_account_id=None,
        fk_service_definition_id=None,
        status=None,
        plugintype=None,
        bpmn_process_id=None,
        resource_uuid=None,
        parent_id=None,
        service_name_list=None,
        service_uuid_list=None,
        service_id_list=None,
        account_id_list=None,
        resource_uuid_list=None,
        *args,
        **kvargs,
    ):
        """Count service instance using a filter.

        :param fk_account_id: id account [optional]
        :param fk_service_definition_id: id service definition [optional]
        :param status: instance status [optional]
        :param plugintype: plugin type name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param parent_id: service instance parent id[optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param service_name_list: list of name service instance [optional]
        :param service_uuid_list: list of uuid service instance[optional]
        :param service_id_list: list of id service instance[optional]
        :param account_id_list: list of account id related to service instance[optional]
        :param resource_uuid_list: ist of resource uuid related to service instance[optional]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        query = self.make_query_service_instances(
            fk_account_id=fk_account_id,
            fk_service_definition_id=fk_service_definition_id,
            status=status,
            plugintype=plugintype,
            bpmn_process_id=bpmn_process_id,
            resource_uuid=resource_uuid,
            parent_id=parent_id,
            service_name_list=service_name_list,
            service_uuid_list=service_uuid_list,
            service_id_list=service_id_list,
            account_id_list=account_id_list,
            resource_uuid_list=resource_uuid_list,
            *args,
            **kvargs,
        )
        res = query.count()
        self.logger.debug2("Get service instance count: %s" % res)
        return res

    @query
    def get_service_instances(
        self,
        fk_account_id=None,
        fk_service_definition_id=None,
        status=None,
        plugintype=None,
        bpmn_process_id=None,
        resource_uuid=None,
        parent_id=None,
        service_name_list=None,
        service_uuid_list=None,
        service_id_list=None,
        account_id_list=None,
        resource_uuid_list=None,
        *args,
        **kvargs,
    ):
        """Get all filtered ServiceInstance.

        :param fk_account_id: id account [optional]
        :param fk_service_definition_id: id service definition [optional]
        :param status: instance status [optional]
        :param plugintype: plugin type name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param parent_id: service instance parent id[optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param service_name_list: list of name service instance [optional]
        :param service_uuid_list: list of uuid service instance[optional]
        :param service_id_list: list of id service instance[optional]
        :param account_id_list: list of account id related to service instance[optional]
        :param resource_uuid_list: ist of resource uuid related to service instance[optional]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        query = self.make_query_service_instances(
            fk_account_id=fk_account_id,
            fk_service_definition_id=fk_service_definition_id,
            status=status,
            plugintype=plugintype,
            bpmn_process_id=bpmn_process_id,
            resource_uuid=resource_uuid,
            parent_id=parent_id,
            service_name_list=service_name_list,
            service_uuid_list=service_uuid_list,
            service_id_list=service_id_list,
            account_id_list=account_id_list,
            resource_uuid_list=resource_uuid_list,
            *args,
            **kvargs,
        )
        res = query.all()
        return res

    @query
    def get_paginated_service_instance_filter(
        self, *args, **kvargs
    ) -> Tuple[List[Tuple[str, str]], str, List[str], Dict[str, Any]]:
        """Get paginated ServiceInstance filter

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :param version: service version
        :param account_id: id account [optional]
        :param service_definition_id: id service definition [optional]
        :param status: instance status name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param plugintype: plugin type name [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param flag_container: if True show only container instances [optional]
        :param period_val_start: [optional]
        :param period_val_stop: [optional]
        :param service_name_list: list of services instances name [optional]
        :param service_uuid_list: list of services instances uuid [optional]
        :param service_id_list: list of services instances id [optional]
        :param account_id_list: list of accounts id related to services instances [optional]
        :param service_definition_id_list: list of service definitions id related to services instances [optional]
        :param resource_uuid_list: list of resources uuid related to services instances [optional]
        :param service_status_name_list: list of status names related to services instances [optional]
        :param servicetags: comma separated list of service tags [optional]. Search exactly the list of tags.
        :param servicetags_in: comma separated list of service tags [optional]. Search in the tag list.
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        tables = []
        custom_select = None

        self.logger.debug2("Get additional params: %s" % kvargs)

        period_val_start = kvargs.get("period_val_start", None)
        period_val_stop = kvargs.get("period_val_stop", None)
        account_id = kvargs.get("account_id", None)
        service_definition_id = kvargs.get("service_definition_id", None)
        status = kvargs.get("status", None)
        bpmn_process_id = kvargs.get("bpmn_process_id", None)
        resource_uuid = kvargs.get("resource_uuid", None)

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if period_val_start is not None:
            filters.append(" AND (t3.expiry_date >= :period_val_start  OR t3.expiry_date is null)")

        if period_val_stop is not None:
            filters.append(" AND t3.creation_date<= :period_val_stop")

        if (
            kvargs.get("uuid", None) is None
            and kvargs.get("service_uuid_list") is not None
            and len(kvargs.get("service_uuid_list")) > 0
        ):
            filters.append(" AND t3.uuid IN :listServiceUUID ")
            kvargs.update(listServiceUUID=tuple(kvargs.pop("service_uuid_list")))

        if (
            kvargs.get("name", None) is None
            and kvargs.get("service_name_list") is not None
            and len(kvargs.get("service_name_list")) > 0
        ):
            filters.append(" AND t3.name IN :listServiceName ")
            kvargs.update(listServiceName=tuple(kvargs.pop("service_name_list")))

        if (
            kvargs.get("id", None) is None
            and kvargs.get("service_id_list") is not None
            and len(kvargs.get("service_id_list")) > 0
        ):
            filters.append(" AND t3.id IN :listServiceID ")
            kvargs.update(listServiceID=tuple(kvargs.pop("service_id_list")))

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id", "fk_account_id"))
        elif (
            "account_id_list" in kvargs
            and kvargs.get("account_id_list", None) is not None
            and len(kvargs.get("account_id_list")) > 0
        ):
            filters.append(" AND t3.fk_account_id IN :listAccountID ")
            kvargs.update(listAccountID=tuple(kvargs.pop("account_id_list")))

        if service_definition_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_definition_id", "fk_service_definition_id ")
            )
        elif (
            "service_definition_id_list" in kvargs
            and kvargs.get("service_definition_id_list") is not None
            and len(kvargs.get("service_definition_id_list")) > 0
        ):
            filters.append(" AND t3.fk_service_definition_id IN :listServiceDefinitionID")
            kvargs.update(listServiceDefinitionID=tuple(kvargs.pop("service_definition_id_list")))

        if status is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("status"))
        elif (
            "service_status_name_list" in kvargs
            and kvargs.get("service_status_name_list") is not None
            and len(kvargs.get("service_status_name_list")) > 0
        ):
            filters.append(" AND t3.status IN :listStatusName ")
            kvargs.update(listStatusName=tuple(kvargs.pop("service_status_name_list")))

        if bpmn_process_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("bpmn_process_id"))

        if resource_uuid is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("resource_uuid"))
        elif (
            "resource_uuid_list" in kvargs
            and kvargs.get("resource_uuid_list") is not None
            and len(kvargs.get("resource_uuid_list")) > 0
        ):
            filters.append(" AND t3.resource_uuid IN :listServiceInstanceResourceUUID ")
            kvargs.update(listServiceInstanceResourceUUID=tuple(kvargs.pop("resource_uuid_list")))

        return tables, custom_select, filters, kvargs

    @query
    def get_paginated_service_instances(self, *args, **kvargs) -> Tuple[List[ServiceInstance], int]:
        """Get paginated ServiceInstance.

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :param version: service version
        :param account_id: id account [optional]
        :param service_definition_id: id service definition [optional]
        :param status: instance status name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param plugintype: plugin type name [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param flag_container: if True show only container instances [optional]
        :param period_val_start: [optional]
        :param period_val_stop: [optional]
        :param service_name_list: list of services instances name [optional]
        :param service_uuid_list: list of services instances uuid [optional]
        :param service_id_list: list of services instances id [optional]
        :param account_id_list: list of accounts id related to services instances [optional]
        :param service_definition_id_list: list of service definitions id related to services instances [optional]
        :param resource_uuid_list: list of resources uuid related to services instances [optional]
        :param service_status_name_list: list of status names related to services instances [optional]
        :param servicetags: comma separated list of service tags [optional]. Search exactly the list of tags.
        :param servicetags_in: comma separated list of service tags [optional]. Search in the tag list.
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        plugintype = kvargs.get("plugintype", None)
        flag_container = kvargs.get("flag_container", None)

        (
            tables,
            custom_select,
            filters,
            kvargs,
        ) = self.get_paginated_service_instance_filter(*args, **kvargs)

        if plugintype is not None:
            filters.append(" AND t3.fk_service_definition_id=t6.id")
            filters.append(" AND t6.fk_service_type_id=t4.id")
            filters.append(" AND t4.objclass=t5.objclass")
            filters.append(" AND t5.name_type=:plugintype")
            tables = [
                ("service_type", "t4"),
                ("service_plugin_type", "t5"),
                ("service_definition", "t6"),
            ]
            kvargs.update(plugintype=plugintype)

        elif flag_container is not None:
            filters.append(" AND t3.fk_service_definition_id=t6.id")
            filters.append(" AND t6.fk_service_type_id=t4.id")
            filters.append(" AND t4.flag_container = :flag_container ")
            tables = [("service_type", "t4"), ("service_definition", "t6")]
            kvargs.update(flag_container=flag_container)

        # manage tags
        servicetags_or = kvargs.get("servicetags_or", None)
        servicetags_and = kvargs.get("servicetags_and", None)
        if servicetags_or is not None or servicetags_and is not None:
            ## TODO FIX GROUP BY
            custom_select = (
                "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name) as tags "
                "FROM service_instance t1, service_tag t2, tag_instance t3 "
                "WHERE t3.fk_service_tag_id=t2.id and t3.fk_service_instance_id=t1.id "
                "and (t2.name in :servicetag_list) "
                "GROUP BY t1.id)"
            )
            if servicetags_and is not None:
                servicetags_and.sort()
                kvargs["servicetag_list"] = servicetags_and
                kvargs["servicetags"] = ",".join(servicetags_and)
                filters.append("AND t3.tags=:servicetags")
            elif servicetags_or is not None:
                kvargs["servicetag_list"] = servicetags_or

        res, total = self.get_api_bo_paginated_entities(
            ServiceInstance,
            filters=filters,
            tables=tables,
            custom_select=custom_select,
            *args,
            **kvargs,
        )
        return res, total

    @query
    def get_paginated_service_type_plugins(self, *args, **kvargs) -> Tuple[List[ServiceTypePluginInstance], int]:
        """Get paginated ServiceInstance.

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :param version: service version
        :param account_id: id account [optional]
        :param service_definition_id: id service definition [optional]
        :param status: instance status name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param plugintype: plugin type name [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param flag_container: if True show only container instances [optional]
        :param period_val_start: [optional]
        :param period_val_stop: [optional]
        :param service_name_list: list of services instances name [optional]
        :param service_uuid_list: list of services instances uuid [optional]
        :param service_id_list: list of services instances id [optional]
        :param account_id_list: list of accounts id related to services instances [optional]
        :param service_definition_id_list: list of service definitions id related to services instances [optional]
        :param resource_uuid_list: list of resources uuid related to services instances [optional]
        :param service_status_name_list: list of status names related to services instances [optional]
        :param servicetags: comma separated list of service tags [optional]. Search exactly the list of tags.
        :param servicetags_in: comma separated list of service tags [optional]. Search in the tag list.
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceInstance
        :raises TransactionError: raise :class:`TransactionError`
        """
        plugintype = kvargs.get("plugintype", None)
        flag_container = kvargs.get("flag_container", None)

        (
            tables,
            custom_select,
            filters,
            kvargs,
        ) = self.get_paginated_service_instance_filter(*args, **kvargs)

        select_fields = [
            "t4.id as type_id",
            "t4.objclass as objclass",
            "t3.tags as inst_tags",
            "t6.name as definition_name",
        ]

        filters.append(" AND t3.fk_service_definition_id=t6.id")
        filters.append(" AND t6.fk_service_type_id=t4.id")
        filters.append(" AND t4.objclass=t5.objclass")
        tables = [
            ("service_type", "t4"),
            ("service_plugin_type", "t5"),
            ("service_definition", "t6"),
        ]

        if plugintype is not None:
            filters.append(" AND t5.name_type = :plugintype ")

        if flag_container is not None:
            filters.append(" AND t4.flag_container = :flag_container ")

        # manage tags
        servicetags_or = kvargs.get("servicetags_or", None)
        servicetags_and = kvargs.get("servicetags_and", None)
        if servicetags_or is not None or servicetags_and is not None:
            ## TODO FIX GROUP BY
            custom_select = (
                "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name) as tags "
                "FROM service_instance t1, service_tag t2, tag_instance t3 "
                "WHERE t3.fk_service_tag_id=t2.id and t3.fk_service_instance_id=t1.id "
                "and (t2.name in :servicetag_list) "
                "GROUP BY t1.id)"
            )
            if servicetags_and is not None:
                servicetags_and.sort()
                kvargs["servicetag_list"] = servicetags_and
                kvargs["servicetags"] = ",".join(servicetags_and)
                filters.append("AND t3.tags=:servicetags")
            elif servicetags_or is not None:
                kvargs["servicetag_list"] = servicetags_or
        else:
            ## TODO FIX GROUP BY
            custom_select = (
                "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name) as tags "
                "FROM service_instance t1 "
                "left outer join tag_instance t3 ON t3.fk_service_instance_id=t1.id "
                "left outer join service_tag t2 ON t3.fk_service_tag_id=t2.id "
                "GROUP BY t1.id)"
            )

        res: List[ServiceTypePluginInstance]
        total: int
        res, total = self.get_api_bo_paginated_entities(
            ServiceTypePluginInstance,
            filters=filters,
            tables=tables,
            select_fields=select_fields,
            custom_select=custom_select,
            *args,
            **kvargs,
        )
        return res, total

    # @transaction
    def update_service_instance(self, *args, **kvargs):
        """Update ServiceInstance

        :param int oid: entity id. [optional]
        :return: :class:`ServiceInstance`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceInstance, *args, **kvargs)
        return res

    @query
    def get_service_tags(self, *args, **kvargs):
        """Get service tags.

        :param value: tag value [optional]
        :param value_list: tag value list [optional]
        :param service: service id
        :param service_list: service id list [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceTag paginated, total
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("tag_instance", "t4")]
        filters = ["AND t3.id=t4.fk_service_tag_id"]

        if "value" in kvargs and kvargs.get("value") is not None:
            filters.append(" AND name like :value ")
        elif "value_list" in kvargs and kvargs.get("value_list") is not None and len(kvargs.get("value_list")) > 0:
            filters.append(" AND name IN :listServiceTagsName ")
            kvargs.update(listServiceTagsName=tuple(kvargs.pop("value_list")))

        if "service" in kvargs and kvargs.get("service") is not None:
            filters.append("AND t4.fk_service_instance_id=:service")
        elif (
            "service_list" in kvargs and kvargs.get("service_list") is not None and len(kvargs.get("service_list")) > 0
        ):
            filters.append(" AND t4.fk_service_instance_id IN :listServiceId ")
            kvargs.update(listServiceId=tuple(kvargs.pop("service_list")))

        res, total = self.get_paginated_entities(ServiceTag, filters=filters, tables=tables, *args, **kvargs)

        return res, total

    def get_service_tags_idx(self, *args, **kvargs):
        """Get service tags idx.
        :param service_list: service id list [optional]
        """
        session = self.get_session()
        sql = [
            "select si.id as id, st.name as tag",
            "from tag_instance ti, service_tag st, service_instance si",
            "where ti.fk_service_tag_id = st.id",
            "  and si.id = ti.fk_service_instance_id",
            "  and si.fk_account_id IN :account_id_list",
        ]
        stmt = text(" ".join(sql))
        params = {"account_id_list": tuple(kvargs["account_id_list"])}
        query = session.execute(stmt, params)
        resp = query.all()
        ret = {}
        for r in resp:
            service_id = r.id
            if service_id not in ret:
                ret[service_id] = []
            ret[service_id].append(r.tag)
        return ret

    @query
    def get_service_tags_with_instance(self, *args, **kvargs):
        """Get service tags with tagged service instance

        :param value_list: tag value list [optional]
        :param service_list: list of services instances uuid [optional]
        :param plugintype_list: list of plugin type name [optional]
        :param account_id_list: list of account uuid [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceTagWithInstance paginated, total
        :raises QueryError: raise :class:`QueryError`
        """
        value_list = kvargs.pop("value_list", None)
        service_list = kvargs.pop("service_list", None)
        plugintype_list = kvargs.pop("plugintype_list", None)
        account_id_list = kvargs.get("account_id_list", None)

        tables = [
            ("tag_instance", "t4"),
            ("service_instance", "t5"),
            ("service_type", "t6"),
            ("service_plugin_type", "t7"),
            ("service_definition", "t8"),
        ]
        filters = [
            "AND t3.id=t4.fk_service_tag_id",
            "AND t4.fk_service_instance_id=t5.id",
            "AND t5.fk_service_definition_id=t8.id",
            "AND t8.fk_service_type_id=t6.id",
            "AND t6.objclass=t7.objclass",
        ]
        select_fields = ["t5.uuid as instance_uuid", "t7.objclass as instance_objclass"]

        if plugintype_list is not None and len(plugintype_list) > 0:
            filters.append("AND t7.name_type IN :listPluginType")
            kvargs.update(listPluginType=tuple(plugintype_list))
        if value_list is not None and len(value_list) > 0:
            filters.append("AND t3.name IN :listServiceTagsName")
            kvargs.update(listServiceTagsName=tuple(value_list))
        if service_list is not None and len(service_list) > 0:
            filters.append("AND t5.uuid IN :listServiceId")
            kvargs.update(listServiceId=tuple(service_list))
        if account_id_list is not None and len(account_id_list) > 0:
            filters.append(" AND t5.fk_account_id IN :listAccountID ")
            kvargs.update(listAccountID=tuple(kvargs.pop("account_id_list")))

        kvargs["field"] = "t3.id, t5.id"
        res, total = self.get_paginated_entities(
            ServiceTagWithInstance,
            filters=filters,
            tables=tables,
            select_fields=select_fields,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def add_service_tag(self, service, tag):
        """Add a tag to a service.

        :param service: Resource service instance
        :param tag: ResourceTag tag instance.
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        tags = service.tag
        if tag not in tags:
            tags.append(tag)
        self.logger.debug2("Add tag %s to service: %s" % (tag, service))
        return True

    @transaction
    def remove_service_tag(self, service, tag):
        """Remove a tag from a service.

        :param service Resource: service instance
        :param tag ResourceTag: tag instance.
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        tags = service.tag
        if tag in tags:
            tags.remove(tag)
        self.logger.debug2("Remove tag %s from service: %s" % (tag, service))
        return True

    #############################
    ### ServiceInstanceConfig ###
    #############################
    @query
    def get_service_instance_config(self, fk_service_instance_id=None, *args, **kvargs):
        """Get only one or none filtered ServiceInstanceConfig.

        :param fk_service_instance_id: id service instance [optional]
        :return: one of ServiceInstanceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstanceConfig)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_service_instance_id is not None:
            query = query.filter_by(fk_service_instance_id=fk_service_instance_id)

        cfg = query.one_or_none()
        return cfg

    @query
    def get_service_instance_configs(self, fk_service_instance_id=None, *args, **kvargs):
        """Get all filtered ServiceInstanceConfig.

        :param fk_service_instance_id: id service instance [optional]
        :return: list of ServiceInstanceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstanceConfig)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        res = query.all()
        return res

    @query
    def get_paginated_service_instance_configs(
        self,
        service_instance_id=None,
        service_instance_ids=None,
        with_perm_tag=True,
        *args,
        **kvargs,
    ):
        """Get paginated ServiceInstanceConfig.

        :param service_instance_id: id service instance [optional]
        :param service_instance_ids: id service instances [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceInstanceConfig
        :raises TransactionError: raise :class:`TransactionError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        if service_instance_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_instance_id", "fk_service_instance_id"))
        if service_instance_ids is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter(
                    "service_instance_ids",
                    "fk_service_instance_id",
                    op_comparison=" in ",
                )
            )

        res, total = self.get_api_bo_paginated_entities(
            ServiceInstanceConfig,
            filters=filters,
            service_instance_id=service_instance_id,
            service_instance_ids=service_instance_ids,
            with_perm_tag=with_perm_tag,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def update_service_instance_config(self, *args, **kvargs):
        """Update ServiceInstanceConfig

        :param int oid: entity id. [optional]
        :return: :class:`ServiceInstanceConfig`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceInstanceConfig, *args, **kvargs)
        return res

    #############################
    ###     AggregateCost     ###
    #############################

    @query
    def get_aggregate_costs(self, *args, **kvargs):
        """Get all filtered AggregateCost.

        :param aggregation_type: aggregation cost type [optional]
        :param period: aggregation period
        :param service_instance_id: id service instance [optional]
        :param evaluation_date_start: start evaluation date[optional]
        :param evaluation_date_end: end evaluation date [optional]
        :param flag_aggregated: id service instance [optional]
        :return: List of AggregateCost
        :raises TransactionError: raise :class:`TransactionError`
        """
        res, total = self.get_paginated_aggregate_costs(size=0, *args, **kvargs)
        return res

    @query
    def get_paginated_aggregate_costs(
        self,
        metric_type_id=None,
        service_instance_id=None,
        account_id=None,
        aggregation_type=None,
        period=None,
        cost_type_id=None,
        evaluation_date_start=None,
        evaluation_date_end=None,
        job_id=None,
        *args,
        **kvargs,
    ):
        """Get paginated AggregateCost.

        :param metric_type_id: metric type id [optional]
        :param service_instance_id: id service instance [optional]
        :param evaluation_date_start: start evaluation date[optional]
        :param evaluation_date_end: end evaluation date [optional]
        :param aggregation_type: id service instance [optional]
        :param period: aggregation period [optional]
        :param cost_type_id: cost type process generation [optional]
        :param job_id: id job creation [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of AggregateCost
        :raises TransactionError: raise :class:`TransactionError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if metric_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("metric_type_id", column="fk_metric_type_id"))

        if aggregation_type is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("aggregation_type"))

        if service_instance_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_instance_id", column="fk_service_instance_id")
            )

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id", column="fk_account_id"))

        if period is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("period"))

        if cost_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("cost_type_id", column="fk_cost_type_id"))

        if evaluation_date_start is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter(
                    "evaluation_date_start",
                    op_comparison=">=",
                    column="evaluation_date",
                )
            )

        if evaluation_date_end is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter(
                    "evaluation_date_end", op_comparison="<=", column="evaluation_date"
                )
            )

        if job_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("job_id", column="fk_job_id"))

        res, total = self.get_api_bo_paginated_entities(
            AggregateCost,
            filters=filters,
            metric_type_id=metric_type_id,
            evaluation_date_start=evaluation_date_start,
            evaluation_date_end=evaluation_date_end,
            aggregation_type=aggregation_type,
            service_instance_id=service_instance_id,
            account_id=account_id,
            period=period,
            cost_type_id=cost_type_id,
            job_id=job_id,
            with_perm_tag=False,
            *args,
            **kvargs,
        )
        self.logger.debug2("Get paginated aggregate costs: %s" % truncate(res))
        return res, total

    @transaction
    def update_aggregate_cost(self, *args, **kvargs):
        """Update AggregateCost

        :param int oid: entity id. [optional]
        :return: :class:`AggregateCost`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(AggregateCost, *args, **kvargs)
        return res

    @transaction
    def delete_batch_aggregate_cost(
        self,
        service_instance_id=None,
        aggregation_type=None,
        period=None,
        cost_type_id=None,
        evaluation_date_start=None,
        evaluation_date_end=None,
        job_id=None,
        metric_type_id=None,
        limit=100,
        *args,
        **kvargs,
    ):
        """Update AggregateCost

        :param service_instance_id: id service instance [optional]
        :param evaluation_date_start: start evaluation date[optional]
        :param evaluation_date_end: end evaluation date [optional]
        :param aggregation_type: aggregation type [optional]
        :param period: period [optional]
        :param cost_type_id: cost type generation [optional]
        :param metric_type_id: metric type [optional]
        #:param platform_id: platform [optional]
        :param job_id: job [optional]
        :return: List of ServiceMetricConsumeView
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AggregateCost)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if service_instance_id is not None:
            query = query.filter_by(service_instance_id=service_instance_id)

        if aggregation_type is not None:
            query = query.filter_by(aggregation_type=aggregation_type)

        if period is not None:
            query = query.filter_by(period=period)

        if cost_type_id is not None:
            query = query.filter_by(cost_type_id=cost_type_id)

        if job_id is not None:
            query = query.filter_by(job_id=job_id)

        # if platform_id is not None:
        #     query = query.filter_by(platform_id=platform_id)

        if metric_type_id is not None:
            query = query.filter_by(metric_type_id=metric_type_id)

        if evaluation_date_start is not None:
            query = query.filter(AggregateCost.evaluation_date.__ge__(evaluation_date_start))

        if evaluation_date_end is not None:
            query = query.filter(AggregateCost.evaluation_date.__le__(evaluation_date_end))
        num = query.count()

        if num >= limit:
            raise ModelError("Too many objects %s" % num, code=404)
        else:
            res = query.delete()

        return res

    @query
    def get_v_aggr_cost_month(self, account_id, metric_type_id=None, period=None, cost_type_id=None):
        """Get AggregateCost Monthly.

        :param account_id: account id [mandatory]
        :param metric_type_id: metric type id [optional]
        :param period: aggregation period [optional]
        :param cost_type_id: cost type process generation [optional]
        :return: list of AggregateCost grouped by month
        :raises TransactionError: raise :class:`TransactionError`
        """

        session = self.get_session()

        query = session.query(
            func.max(AggregateCost.metric_type_id).label("metric_type_id"),
            func.sum(AggregateCost.consumed).label("consumed"),
            func.sum(AggregateCost.cost).label("cost"),
            func.max(AggregateCost.cost_type_id).label("cost_type_id"),
            AggregateCost.account_id.label("account_id"),
            func.substr(AggregateCost.period, 1, 7).label("period"),
            func.current_timestamp().label("evaluation_date"),
        ).group_by(
            AggregateCost.metric_type_id,
            AggregateCost.account_id,
            func.substr(AggregateCost.period, 1, 7),
        )

        query = query.filter_by(aggregation_type="daily")
        query = query.filter_by(account_id=account_id)

        if metric_type_id is not None:
            query = query.filter_by(metric_type_id=metric_type_id)

        if period is not None:
            query = query.filter(func.substr(AggregateCost.period, 1, 7) == period)

        if cost_type_id is not None:
            query = query.filter_by(cost_type_id=cost_type_id)

        res = query.all()

        # generate AggregateCost
        return [
            AggregateCost(
                metric_type_id=row[0],
                consumed=row[1],
                cost=row[2],
                service_instance_id=None,
                account_id=row[4],
                aggregation_type="monthly",
                period=row[5],
                cost_type_id=row[3],
                evaluation_date=row[6],
                job_id=None,
            )
            for row in res
        ], len(res)

    #############################
    ###       ServiceLink     ###
    #############################

    @transaction
    def update_service_instlink(self, *args, **kvargs):
        """Update Service Instance Link

        :param int oid: entity id. [optional]
        :return: :class:`AggregateCost`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceLinkInstance, *args, **kvargs)
        return res

    @transaction
    def update_service_deflink(self, *args, **kvargs):
        """Update Service Definition Link

        :param int oid: entity id. [optional]
        :return: :class:`AggregateCost`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceLinkDef, *args, **kvargs)
        return res

    @query
    def get_service_link(self, model, fk_instance_start=None, fk_instance_end=None, *args, **kvargs):
        """Get only one or none filtered ServiceLink.

        :param fk_instance_start: instance start date [optional]
        :param fk_instance_end: instance start date [optional]
        :return: one of ServiceLink
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(model)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_instance_start is not None:
            query = query.filter_by(fk_instance_start=fk_instance_start)

        if fk_instance_end is not None:
            query = query.filter_by(fk_instance_end=fk_instance_end)

        cfg = query.one_or_none()
        return cfg

    @query
    def get_service_links(self, entityclass, *args, **kvargs):
        """Get links.
        :param entityclass: entity model class of link can be ServiceLinkInstance or ServiceLinkDef
        :param start_service_id: start service id [optional]
        :param end_service_id: end service id [optional]
        :param priority: link navigation priority
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceLink
        :raises QueryError: raise :class:`QueryError`
        """
        for key, value in kvargs.items():
            self.logger.debug2("get_service_links key=%s, value=%s" % (key, value))

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "start_service_id" in kvargs and kvargs.get("start_service_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("start_service_id"))
        if "end_service_id" in kvargs and kvargs.get("end_service_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("end_service_id"))
        if "priority" in kvargs and kvargs.get("priority") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("priority", "priority"))

        res, total = self.get_api_bo_paginated_entities(entityclass, filters=filters, *args, **kvargs)
        return res, total

    @query
    def get_service_links_2(
        self,
        model,
        fk_instance_start=None,
        fk_instance_end=None,
        priority=None,
        *args,
        **kvargs,
    ):
        """Get all filtered ServiceLink.

        :param fk_instance_start: instance start date [optional]
        :param fk_instance_end: instance start date [optional]
        :return: List of ServiceLink
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(model)
        query = self.add_base_entity_filters(query, *args, **kvargs)

        if fk_instance_start is not None:
            query = query.filter_by(fk_instance_start=fk_instance_start)

        if fk_instance_end is not None:
            query = query.filter_by(fk_instance_end=fk_instance_end)

        if priority is not None:
            query = query.filter_by(priority=priority)

        res = query.order_by(model.priority).all()
        return res

    @query
    def get_service_instance_parent(self, end_service_id, plugintype=None) -> ServiceInstance:
        """Get service instance parent

        :param end_service_id: instance start id
        :param plugintype: plugintype to filter the children instance
        :return: List of entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        query = (
            session.query(ServiceInstance)
            .join(
                ServiceLinkInstance,
                ServiceInstance.id == ServiceLinkInstance.start_service_id,
            )
            .filter(ServiceLinkInstance.end_service_id == end_service_id)
            .filter(ServiceInstance.status != SrvStatusType.DELETED)
        )
        if plugintype is not None:
            query = query.filter(ServicePluginType.name_type == plugintype)

        res = query.first()
        self.logger.debug2("Get service instance %s parent: %s" % (end_service_id, truncate(res)))

        return res

    @query
    def get_service_instance_parent_id(self, end_service_id) -> ServiceInstance:
        session = self.get_session()
        query = text(
            """
            SELECT sl.start_service_id FROM service_link_inst sl, service_instance s
            WHERE sl.end_service_id=:end_service_id AND sl.start_service_id=s.id AND s.status!="DELETED"
            LIMIT 1
            """
        )
        elem = session.execute(query, params={"end_service_id": end_service_id}).first()
        parent_id = None
        if elem is not None:
            parent_id = elem[0]
        self.logger.debug2("Get service instance %s parent id: %s" % (end_service_id, parent_id))
        return parent_id

    @query
    def get_service_instance_children(self, start_service_id, plugintype):
        """Get all filtered service instance.

        :param start_service_id: instance start id
        :param plugintype: plugintype to filter the children instance
        :return: List of entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        query = (
            session.query(ServiceInstance)
            .join(ServiceInstance.linkParent)
            .join(ServiceInstance.service_definition)
            .join(ServiceDefinition.service_type)
            .join(ServiceType.plugintype)
        )

        query = query.filter(ServiceLinkInstance.start_service_id == start_service_id).filter(
            ServiceInstance.status != SrvStatusType.DELETED
        )
        if plugintype is not None:
            query = query.filter(ServicePluginType.name_type == plugintype)

        res = query.all()
        self.logger.debug2("Get service instance %s children: %s" % (start_service_id, truncate(res)))

        return res

    @query
    def get_service_instance_for_update(self, start_service_id):
        """Get all filtered ServiceLink.

        :param start_service_id: instance start id
        :return: List of Entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstance).join(
            ServiceLinkInstance,
            ServiceLinkInstance.end_service_id == ServiceInstance.id,
        )
        query = query.filter(ServiceLinkInstance.start_service_id == start_service_id)

        res = query.order_by(asc(ServiceLinkInstance.priority)).with_for_update().all()

        return res

    #############################
    ###     Organization      ###
    #############################

    @transaction
    def add_organization(
        self,
        objid,
        name,
        org_type,
        service_status_id,
        desc="",
        version="1.0",
        ext_anag_id=None,
        attributes=None,
        hasvat=False,
        partner=False,
        referent=None,
        email=None,
        legalemail=None,
        postaladdress=None,
        active=True,
    ):
        """Add Organization.

        :param objid: str objid
        :param name: str organization name
        :param org_type: str organization type, takes  one of the followings value 'Private|Public'
        :param service_status_id: integer id service_status reference
        :param desc: str organization description
        :param ext_anag_id: str external client identification on the anagraphical database
        :param attributes: str
        :param hasvat: boolean
        :param partner: boolean
        :param representative: str name and surname representative
        :param email: str email address legal representative
        :param legalemail: str institutional email address for organization
        :param postaladdress: str postal address organization
        :param active:  boolean status of the entity. True is active
        :return: :class:`Organization`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.add_entity(
            Organization,
            objid,
            name,
            org_type,
            service_status_id,
            desc,
            version,
            ext_anag_id,
            attributes,
            hasvat,
            partner,
            referent,
            email,
            legalemail,
            postaladdress,
            active,
        )
        return res

    @transaction
    def update_organization(self, *args, **kvargs):
        """Update Organization.

        :param int oid: entity id. [optional]
        :param value str: tag value. [optional]
        :return: :class:`Organization`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Organization, *args, **kvargs)
        return res

    @transaction
    def delete_organization(self, *args, **kvargs):
        """Remove Organization.
        :param int oid: entity id. [optional]
        :return: :class:`Organization`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Organization, *args, **kvargs)
        return res

    @query
    def get_organizations(self, *args, **kvargs):
        """Get Organizations.

        :param id: organization id [optional]
        :param uuid: organization uuid [optional]
        :param objid: organization objid [optional]
        :param name: organization name [optional]
        :param version: organization version [optional]
        :param ext_anag_id: external client identification on the anagraphical database [optional]
        :param attributes: organization attributes [optional]
        :param org_type_id: organization type [optional]
        :param email: email to contact organization's referent  [optional]
        :param legalemail: istitutional organization email [optional]
        :param referent: name and surname of the organization's referent [opzional]
        :param service_status_id: id reference entity state [opzional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiry_date [optional]
        :param id_list: list of account id [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`Organization`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "ext_anag_id" in kvargs and kvargs.get("ext_anag_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("ext_anag_id"))
        if "attributes" in kvargs and kvargs.get("attributes") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("attributes"))
        if "org_type_id" in kvargs and kvargs.get("org_type_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("org_type_id"))
        if "email" in kvargs and kvargs.get("email") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("email"))
        if "legalemail" in kvargs and kvargs.get("legalemail") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("legalemail"))
        if "referent" in kvargs and kvargs.get("referent") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("referent"))
        if "service_status_id" in kvargs and kvargs.get("service_status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_status_id", "fk_service_status_id"))
        if "id_list" in kvargs and kvargs.get("id_list", None) is not None and len(kvargs.get("id_list")) > 0:
            filters.append(" AND t3.id IN :listID ")
            kvargs.update(listID=tuple(kvargs.pop("id_list")))
        res, total = self.get_api_bo_paginated_entities(Organization, filters=filters, *args, **kvargs)
        return res, total

    @query
    def count_organization(self):
        """Get organizations count.

        :raises QueryError: raise :class:`QueryError`
        """
        return self.count_entities(Organization)

    @transaction
    def add_division(
        self,
        objid,
        name,
        organization_id,
        service_status_id,
        desc,
        version,
        contact,
        email,
        postaladdress,
        active,
    ):
        """Add Division.

        :param objid str: objid
        :param name str: division name
        :param organization_id: organization id reference
        :param service_status_id integer: id service_status reference
        :param desc str: division description
        :param version str: version entity
        :param contact str: name and surname contact
        :param email str: email address contact
        :param postaladdress str: postal address division
        :param active  boolean: status of the entity. True is active
        :return: :class:`Division`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(
            Division,
            objid,
            name,
            organization_id,
            service_status_id,
            desc,
            version,
            contact,
            email,
            postaladdress,
            active,
        )

        return res

    @query
    def get_divs_prices(self, division_id, curr_date):
        """
        :param division_id: division oid
        :param end_date: Price_List end_date
        :return: DivisionsPrices object or None
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(DivisionsPrices)
        query = (
            query.filter(DivisionsPrices.division_id == division_id)
            .filter(
                or_(
                    DivisionsPrices.end_date.is_(None),
                    DivisionsPrices.end_date > curr_date,
                )
            )
            .filter(DivisionsPrices.start_date <= curr_date)
        )

        res = query.one_or_none()

        return res

    @query
    def get_account_prices(self, account_id, curr_date):
        """
        :param account_id: account oid
        :param end_date: Price_List end_date
        :return: AccountsPrices object or None
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AccountsPrices)
        query = (
            query.filter(AccountsPrices.account_id == account_id)
            .filter(
                or_(
                    AccountsPrices.end_date.is_(None),
                    AccountsPrices.end_date > curr_date,
                )
            )
            .filter(AccountsPrices.start_date <= curr_date)
        )
        res = query.one_or_none()

        return res

    @query
    def get_account_prices_by_pricelist(
        self,
        price_list_id,
    ):
        """
        :param pricelist_id: pricelist_id oid
        :return: AccountsPrices object or None
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AccountsPrices)
        query = query.filter(AccountsPrices.price_list_id == price_list_id)
        return query.limit(1).all()

    @query
    def get_division_prices_by_pricelist(self, price_list_id):
        """
        :param pricelist_id: pricelist_id oid
        :return: DivisionsPrices object or None
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AccountsPrices)
        query = query.filter(DivisionsPrices.price_list_id == price_list_id)
        return query.limit(1).all()

    @transaction
    def add_divs_prices(self, division_id, price_list_id):
        res = self.add_entity(DivisionsPrices, division_id, price_list_id, date.today())
        return res

    @transaction
    def add_account_prices(self, account_id, price_list_id):
        res = self.add_entity(AccountsPrices, account_id, price_list_id, date.today())
        return res

    @transaction
    def update_divs_prices(self, division_id, price_list_id, end_date):
        div_price = self.get_divs_prices(division_id, end_date)
        if div_price is not None:
            if div_price.price_list_id == int(price_list_id):
                self.logger.warn(
                    "update_divs_prices nothing todo division %d  pricelist %d" % (division_id, price_list_id)
                )
                return
            div_price.end_date = date.today()
            self.update(div_price)
        self.logger.warn("creating div_price division %d  pricelist %d" % (division_id, price_list_id))
        self.add_divs_prices(division_id, price_list_id)

    @transaction
    def update_account_prices(self, account_id, price_list_id, end_date):
        acc_price = self.get_account_prices(account_id, end_date)
        if acc_price is not None:
            if acc_price.price_list_id == int(price_list_id):
                return
            acc_price.end_date = date.today()
            self.update(acc_price)
        self.add_account_prices(account_id, price_list_id)

    @transaction
    def update_division(self, *args, **kvargs):
        """Update Division.

        :param int oid: entity id. [optional]
        :param value str: tag value. [optional]
        :return: :class:`Division`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Division, *args, **kvargs)
        return res

    @transaction
    def delete_division(self, *args, **kvargs):
        """Remove Division.
        :param int oid: entity id. [optional]
        :return: :class:`Division`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Division, *args, **kvargs)
        return res

    @query
    def get_divisions(self, *args, **kvargs):
        """Get Divisions.

        :param id: division id [optional]
        :param uuid: division  uuid [optional]
        :param objid: division objid [optional]
        :param name: division name [optional]
        :param version: division version [optional]
        :param contact: name and surname of the division contact [optional]
        :param email: email of Division's contact [optional]
        :param organization_id: id  reference organization [optional]
        :param organization_id_list: list of organization id [optional]
        :param service_status_id = id reference entity state [optional]
        :param price_list_id: id service Price List reference [optional]
        :param active = active
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiration_date [optional]
        :param id_list: list of account id [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`Division`
        :raises QueryError: raise :class:`QueryError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "contact" in kvargs and kvargs.get("contact") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("contact"))
        if "email" in kvargs and kvargs.get("email") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("email"))
        if "organization_id" in kvargs and kvargs.get("organization_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("organization_id", "fk_organization_id"))
        if "service_status_id" in kvargs and kvargs.get("service_status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_status_id", "fk_service_status_id"))
        if "price_list_id" in kvargs and kvargs.get("price_list_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("price_list_id", "fk_price_list_id"))
        if "id_list" in kvargs and kvargs.get("id_list", None) is not None and len(kvargs.get("id_list")) > 0:
            filters.append(" AND t3.id IN :listID ")
            kvargs.update(listID=tuple(kvargs.pop("id_list")))
        if (
            "organization_id_list" in kvargs
            and kvargs.get("organization_id_list", None) is not None
            and len(kvargs.get("organization_id_list")) > 0
        ):
            filters.append(" AND t3.fk_organization_id IN :organization_id_list ")
            kvargs.update(organization_id_list=tuple(kvargs.pop("organization_id_list")))
        res, total = self.get_api_bo_paginated_entities(Division, filters=filters, *args, **kvargs)
        return res, total

    @query
    def get_wallet_by_year(self, division_id, year):
        """
        :param division_id: division id
        :param year: year
        :return: Wallet object or None
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        query = session.query(Wallet)
        query = query.filter(Wallet.division_id == division_id).filter(Wallet.year == year)
        res = query.one_or_none()

        return res

    @transaction
    def add_wallet(
        self,
        objid,
        name,
        division_id,
        year,
        service_status_id,
        desc="",
        version="1.0",
        capital_total=0.0,
        capital_used=0.0,
        evaluation_date=None,
        active=True,
    ):
        """Add Wallet.

        :param objid str: objid
        :param name str: name of the entity
        :param division_id integer: division id reference
        :param year: reference year
        :param service_status_id integer: id service_status reference
        :param desc str: description of the entity
        :param version str: version of the entity
        :param capital_total float: amount of the total wallet capital
        :param capital_used float: amount of the consumed wallet capital
        :param evaluation_date str:  the last date of evaluation of the capital consumed
        :param active  boolean: status of the entity. True is active
        :return: :class:`wallet`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.add_entity(
            Wallet,
            objid,
            name,
            division_id,
            year,
            service_status_id,
            desc,
            version,
            capital_total,
            capital_used,
            evaluation_date,
            active,
        )

        return res

    @transaction
    def update_wallet(self, *args, **kvargs):
        """Update Wallet.

        :param int oid: entity id. [optional]
        :param TDB: TDB [optional]
        :return: :class:`Wallet`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Wallet, *args, **kvargs)
        return res

    @transaction
    def delete_wallet(self, *args, **kvargs):
        """Remove Wallet.
        :param int oid: entity id. [optional]
        :return: :class:`Wallet`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Wallet, *args, **kvargs)
        return res

    @query
    def get_wallets(self, *args, **kvargs):
        """Get Wallet.

        :param id: wallet id [optional]
        :param uuid: wallet  uuid [optional]
        :param objid: wallet objid [optional]
        :param name: wallet name [optional]
        :param version: wallet version [optional]

        :param capital_total float: amount of the total wallet capital
        :param capital_used float: amount of the consumed wallet capital
        :param evaluation_date str: email_support address contact

        :param year: year of competence
        :param division_id: id  reference division
        :param service_status_id = id reference entity state
        :param active = active
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiration_date [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`account`
        :raises QueryError: raise :class:`QueryError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        #         if 'filter_by_name' in kvargs and kvargs.get('filter_by_name') is not None:
        #             filters.append (PaginatedQueryGenerator.create_sqlfilter('filter_by_name',
        # 'name', op_comparison='like'))

        if "capital_total" in kvargs and kvargs.get("capital_total") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("capital_total"))
        if "capital_total_min_range" in kvargs and kvargs.get("capital_total_min_range") is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("capital_total_min_range", "capital_total", op_comparison=">=")
            )
        if "capital_total_max_range" in kvargs and kvargs.get("capital_total_max_range") is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("capital_total_max_range", "capital_total", op_comparison="<=")
            )
        if "capital_used" in kvargs and kvargs.get("capital_used") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("capital_used"))
        if "capital_used_min_range" in kvargs and kvargs.get("capital_used_min_range") is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("capital_used_min_range", "capital_used", op_comparison=">=")
            )
        if "capital_used_max_range" in kvargs and kvargs.get("capital_used_max_range") is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("capital_used_max_range", "capital_used", op_comparison="<=")
            )
        if "evaluation_date" in kvargs and kvargs.get("evaluation_date") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("evaluation_date"))

        curr_field = "evaluation_date_start"
        if curr_field in kvargs and kvargs.get(curr_field) is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("evaluation_date_start", "evaluation_date", op_comparison=">=")
            )
        curr_field = "evaluation_date_stop"
        if curr_field in kvargs and kvargs.get(curr_field) is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("evaluation_date_stop", "evaluation_date", op_comparison="<=")
            )

        if "division_id" in kvargs and kvargs.get("division_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("division_id", "fk_division_id"))

        if "service_status_id" in kvargs and kvargs.get("service_status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_status_id", "fk_service_status_id"))
        if "year" in kvargs and kvargs.get("year") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("year"))

        res, total = self.get_api_bo_paginated_entities(Wallet, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def add_agreement(
        self,
        objid,
        name,
        wallet_id,
        service_status_id,
        desc,
        active,
        version,
        amount,
        agreement_date_start,
        agreement_date_end,
    ):
        """Add Agreement.

        :param objid str: objid
        :param name str: name of the entity
        :param wallet_id integer: wallet id reference
        :param service_status_id integer: id service_status reference
        :param desc str: description of the entity
        :param version str: version of the entity
        :param amount float: amount of the agreement
        :param agreement_date_start: start date of the  agreement
        :param agreement_date_end: end date of the  agreement
        :param active  boolean: status of the entity. True is active
        :return: :class:`agreement`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.add_entity(
            Agreement,
            objid,
            name,
            wallet_id,
            service_status_id,
            desc,
            active,
            version,
            amount,
            agreement_date_start,
            agreement_date_end,
        )

        return res

    @transaction
    def update_agreement(self, *args, **kvargs):
        """Update Agreement.

        :param int oid: entity id [optional]
        :param TDB: TDB [optional]
        :return: :class:`Agreement`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.update_entity(Agreement, *args, **kvargs)
        return res

    @transaction
    def delete_agreement(self, *args, **kvargs):
        """Remove Agreement.
        :param int oid: entity id. [optional]
        :return: :class:`Agreement`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Agreement, *args, **kvargs)
        return res

    @query
    def get_agreements(self, *args, **kvargs):
        """Get Agreements.

        :param id: agreement id [optional]
        :param uuid: agreement  uuid [optional]
        :param objid: agreement objid [optional]
        :param name: agreement name [optional]
        :param version: agreement version [optional]

        :param division_id: division id [optional]
        :param division_ids: array division id [optional]
        :param wallet_id: id  reference wallet
        :param year: year of wallet

        :param amount float: amount of the agreement [optional]
        :param agreement_date_start: start date of the agreement [optional]
        :param agreement_date_end: end date of the agreement [optional]

        :param service_status_id = id reference entity state
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`account`
        :raises QueryError: raise :class:`QueryError`
        """

        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        tables = []

        if (
            ("year" in kvargs and kvargs.get("year") is not None)
            or ("wallet_id" in kvargs and kvargs.get("wallet_id")) is not None
            or ("division_id" in kvargs and kvargs.get("division_id") is not None)
            or (
                "division_ids" in kvargs
                and kvargs.get("division_ids") is not None
                and len(kvargs.get("division_ids")) > 0
            )
        ):
            tables = [("wallet", "t4")]

        if "amount" in kvargs and kvargs.get("amount") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("amount"))

        if "agreement_date_start" in kvargs and kvargs.get("agreement_date_start") is not None:
            kvargs["today"] = date.today()
            filters.append("AND coalesce(t3.agreement_date_end, :today) >= :agreement_date_start")

        if "agreement_date_end" in kvargs and kvargs.get("agreement_date_end") is not None:
            filters.append("AND t3.agreement_date_start <= :agreement_date_end")

        if "wallet_id" in kvargs and kvargs.get("wallet_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("wallet_id", "fk_wallet_id"))
            filters.append("AND t4.id = t3.fk_wallet_id")

        if "division_id" in kvargs and kvargs.get("division_id") is not None:
            filters.append("AND t4.fk_division_id = :division_id")

        if "division_ids" in kvargs and kvargs.get("division_ids") is not None:
            if len(kvargs.get("division_ids")) > 0:
                filters.append("AND t4.fk_division_id IN :division_ids")
            else:
                return [], 0

        if "year" in kvargs and kvargs.get("year") is not None:
            filters.append("AND t4.year_ref = :year")
            filters.append("AND t4.id = t3.fk_wallet_id")

        if "service_status_id" in kvargs and kvargs.get("service_status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_status_id", "fk_service_status_id"))

        res, total = self.get_api_bo_paginated_entities(
            Agreement,
            filters=filters,
            tables=tables,
            with_perm_tag=False,
            *args,
            **kvargs,
        )
        return res, total

    #########################
    # Account Capability CRUD
    # no remove solo cancellazioni logiche
    #########################
    @transaction
    def add_capability(self, objid, name, status, desc, version, params):
        """Create new AccountCapability"""
        res = self.add_entity(
            AccountCapability,
            objid,
            name,
            desc,
            active=True,
            version=version,
            status=status,
            params=params,
        )
        return res

    @transaction
    def update_capability(self, *args, **kvargs):
        """Update AccountCapability.

        :param int oid: entity id. [optional]
        :param TDB: TDB [optional]
        :return: :class:`Account`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.update_entity(AccountCapability, *args, **kvargs)
        return res

    @query
    def get_capabilities(self, *args, **kvargs):
        """Get AccountCapability.

        :param id: account id [optional]
        :param uuid: account  uuid [optional]
        :param objid: account objid [optional]
        :param name: account name [optional]
        :param version: account version [optional]
        :param status_id = id reference entity state
        :param active = active
        :param is_default:  boolean default flag

        :param modification_date: modification_date [optional]
        :param expiry_date: expiration_date [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`AccountCapability`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "status_id" in kvargs and kvargs.get("status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("status"))

        res, total = self.get_api_bo_paginated_entities(AccountCapability, filters=filters, *args, **kvargs)
        return res, total

    @query
    def get_account_capability(self, oid, for_update=False, *args, **kvargs):
        return self.get_entity(AccountCapability, oid, for_update=for_update, *args, **kvargs)

    #########################
    # Account CRUD
    #########################
    @query
    def get_account_by_pk(self, account_id):
        """
        :param account_id: account oid
        :return: Account object or None
        """
        session = self.get_session()
        query = session.query(Account).filter(Account.id == account_id)
        return query.one_or_none()

    @transaction
    def add_account(
        self,
        objid,
        name,
        division_id,
        service_status_id,
        desc,
        version,
        note,
        contact,
        email,
        email_support,
        email_support_link,
        active,
        params={},
        acronym="",
    ):
        """Add Account.

        :param objid str: objid
        :param name str: account name
        :param division_id: division id reference
        :param service_status_id integer: id service_status reference
        :param desc str: contact description
        :param version str: version entity
        :param contact str: name and surname contact
        :param email str: email address contact
        :param email_support str: email_support address contact
        :param email_support_link str: email_support_link for the account
        :param active  boolean: status of the entity. True is active
        :param params: custom params set as dictionary [optional]
        :param acronym: account acronym used with managed account
        :return: :class:`Account`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(
            Account,
            objid,
            name,
            division_id,
            service_status_id,
            desc,
            version,
            note,
            contact,
            email,
            email_support,
            email_support_link,
            active,
            params=params,
            acronym=acronym,
        )

        return res

    @transaction
    def update_account(self, *args, **kvargs):
        """Update Account.

        :param int oid: entity id. [optional]
        :param TDB: TDB [optional]
        :return: :class:`Account`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Account, *args, **kvargs)
        return res

    @transaction
    def delete_account(self, *args, **kvargs):
        """Remove Account.

        :param int oid: entity id. [optional]
        :return: :class:`Account`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Account, *args, **kvargs)
        return res

    @query
    def get_accounts(self, *args, **kvargs):
        """Get accounts.

        :param id: account id [optional]
        :param uuid: account  uuid [optional]
        :param objid: account objid [optional]
        :param name: account name [optional]
        :param version: account version [optional]
        :param email: email Account [optional]
        :param email_support: email support for Account [optional]
        :param email_support_link: email support link for Account[optional]
        :param division_id: id  reference division
        :param division_id_list: list of division id
        :param service_status_id = id reference entity state
        :param active = active
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiration_date [optional]
        :param id_list: list of account id [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :rtype: list of :class:`account`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if "contact" in kvargs and kvargs.get("contact") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("contact"))
        if "email" in kvargs and kvargs.get("email") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("email"))
        if "email_support" in kvargs and kvargs.get("email_support") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("email_support"))
        if "email_support_link" in kvargs and kvargs.get("email_support_link") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("email_support_link"))
        if "division_id" in kvargs and kvargs.get("division_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("division_id", "fk_division_id"))
        if (
            "division_id_list" in kvargs
            and kvargs.get("division_id_list", None) is not None
            and len(kvargs.get("division_id_list")) > 0
        ):
            filters.append(" AND t3.fk_division_id IN :division_id_list ")
            kvargs.update(division_id_list=tuple(kvargs.pop("division_id_list")))
        if "service_status_id" in kvargs and kvargs.get("service_status_id") is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("service_status_id", "fk_service_status_id"))
        if "id_list" in kvargs and kvargs.get("id_list", None) is not None and len(kvargs.get("id_list")) > 0:
            filters.append(" AND t3.id IN :listID ")
            kvargs.update(listID=tuple(kvargs.pop("id_list")))

        res, total = self.get_api_bo_paginated_entities(Account, filters=filters, *args, **kvargs)
        return res, total

    @query
    def get_paginated_report_costs(
        self,
        account_id=None,
        account_id_list=None,
        plugin_name=None,
        period=None,
        job_id=None,
        is_reported=None,
        period_start=None,
        period_end=None,
        *args,
        **kvargs,
    ):
        """Get paginated ReportCost.

        :param account_id: id account
        :param account_id_list: list id account
        :param period_start: start date of report [optional]
        :param period_end: end date of report [optional]
        :param plugin_name: name of plugin [optional]
        :param is_reported: True if report_date is not None [optional]
        :param job_id: task creation id [optional]
        :param period: period of report [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id", column="fk_account_id"))

        if account_id_list is not None and len(account_id_list) > 0:
            filters.append(" AND t3.fk_account_id IN :listAccountID ")
            kvargs.update(listAccountID=tuple(account_id_list))

        if plugin_name is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("plugin_name"))

        if period is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("period"))

        if job_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("job_id", column="fk_job_id"))

        if is_reported is not None:
            if is_reported:
                filters.append(" AND t3.report_date is not null ")
            else:
                filters.append(" AND t3.report_date is null ")

        if period_start is not None:
            filters.append(" AND t3.period >= :period_start")

        if period_end is not None:
            filters.append(" AND t3.period <= :period_end")

        kvargs.update(
            account_id=account_id,
            plugin_name=plugin_name,
            period=period,
            job_id=job_id,
            period_start=period_start,
            period_end=period_end,
            with_perm_tag=False,
        )

        res, total = self.get_api_bo_paginated_entities(ReportCost, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def update_report_costs(self, account_id, period_start, period_end, report_date=None):
        res, total = self.get_paginated_report_costs(
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            size=0,
        )
        for r in res:
            r.report_date = report_date

        self.bulk_save_entities(res)
        return total

    @transaction
    def add_service_catalog_def(self, catalog, definition) -> str:
        """Add definitions to service catalog

        :param catalog:
        :param definition:
        :return: the added definition uuid
        """
        catalog.service_definitions.append(definition)

        return definition.uuid

    @query
    def get_service_catalog_defs(self, oid):
        """Get service catalog definitions."""
        srv_catalog = self.get_entity(ServiceCatalog, oid)
        srv_defs = srv_catalog.model.service_definitions

        res = [r.id for r in srv_defs]
        return res

    @transaction
    def delete_service_catalog_def(self, catalog, definition):
        """Remove definitions from service catalog

        :param catalog:
        :param definition:
        :return:
        """
        catalog.service_definitions.remove(definition)

    ############################
    ###    ServiceMetric     ###
    ############################
    @query
    def get_service_metric(self, id):
        session = self.get_session()
        query = session.query(ServiceMetric).filter(ServiceMetric.id == id)

        metric = query.one_or_none()
        return metric

    @query
    def get_service_metrics(
        self,
        id=None,
        value=None,
        metric_type_id=None,
        metric_num=None,
        service_instance_id=None,
        job_id=None,
    ):
        session = self.get_session()
        query = session.query(ServiceMetric)

        if id is not None:
            query = query.filter(ServiceMetric.id == id)

        if value is not None:
            query = query.filter(ServiceMetric.value == value)

        if metric_type_id is not None:
            query = query.filter(ServiceMetric.metric_type_id == metric_type_id)

        if metric_num is not None:
            query = query.filter(ServiceMetric.metric_num == metric_num)

        if service_instance_id is not None:
            query = query.filter(ServiceMetric.service_instance_id == service_instance_id)

        if job_id is not None:
            query = query.filter(ServiceMetric.job_id == job_id)

        metrics = query.all()
        return metrics

    @query
    def get_paginated_service_metrics(
        self,
        metric_type_id=None,
        metric_num=None,
        service_instance_id=None,
        job_id=None,
        *args,
        **kvargs,
    ):
        """Get paginated ServiceMetric.

        :param value: instant consume [optional]
        :param metric_type_id: metric type [optional]
        :param metric_num: daily occurrency number [optional]
        :param service_instance_id: instance id [optional]
        :param job_id: task creation id [optional]
        :param status: status of metric elaboration [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ServiceMetric
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if metric_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("metric_type_id", column="fk_metric_type_id"))

        if metric_num is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("metric_num"))

        if service_instance_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_instance_id", column="fk_service_instance_id")
            )

        if job_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("job_id", column="fk_job_id"))

        kvargs.update(
            metric_type_id=metric_type_id,
            metric_num=metric_num,
            service_instance_id=service_instance_id,
            job_id=job_id,
        )

        res, total = self.get_api_bo_paginated_entities(ServiceMetric, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def update_service_metric(self, *args, **kvargs):
        """Update ServiceMetric.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceMetric`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceMetric, *args, **kvargs)
        return res

    @transaction
    def delete_service_metric(
        self,
        metric_type_id=None,
        metric_num=None,
        service_instance_id=None,
        job_id=None,
        start_date=None,
        end_date=None,
    ):
        session = self.get_session()
        query = session.query(ServiceMetric)

        if metric_type_id is not None:
            query = query.filter(ServiceMetric.metric_type_id == metric_type_id)

        if metric_num is not None:
            query = query.filter(ServiceMetric.metric_num == metric_num)

        if service_instance_id is not None:
            query = query.filter(ServiceMetric.service_instance_id == service_instance_id)

        if job_id is not None:
            query = query.filter(ServiceMetric.job_id == job_id)

        if start_date is not None:
            query = query.filter(ServiceMetric.creation_date >= start_date)

        if end_date is not None:
            query = query.filter(ServiceMetric.creation_date <= end_date)

        res = query.delete()

        return res

    #############################
    ###   ServiceMetricType   ###
    #############################
    @query
    def get_service_metric_types_dict(self, byname: bool = True) -> dict:
        """
        get_service_metric_types_dict
        return all service metrics in a ditionary having  tehe metricc name as key and metric id has value
        return {
            "name_1": 1,
            "name_2": 2,
            "name_n": n,
        }
        """
        session = self.get_session()
        sqlstmnt: str = """
        select
            smt.name ,
            smt.id
        from
            service_metric_type smt
        where
            smt.expiry_date is null
        """
        resp = session.execute(text(sqlstmnt)).all()
        ret = {}
        for r in resp:
            if byname:
                ret[r.name] = r.id
            else:
                ret[str(r.id)] = r.name

        return ret

    @query
    def get_service_metric_types_info(self, name: str = "", id: int = -99) -> Tuple[str, int]:
        """get_service_metric_types_info
        return a service metric type info by quering underlayng table by name or by id
        name and id ar optional b
        return ("name_1", 1)

        Args:
            name (str, optional): _description_. Defaults to "".
            id (int, optional): _description_. Defaults to -99.

        Returns:
            Tuple[str, int]: _description_
        """
        """
        get_service_metric_types_info
        """
        session = self.get_session()

        sqlstmnt: str = """
        select
            smt.name ,
            smt.id
        from
            service_metric_type smt
        where
            smt.expiry_date is null
            and smt.%s = :value
        """
        if name != "":
            resp = session.execute(text(sqlstmnt % "name"), params={"value": name}).first()
        else:
            resp = session.execute(text(sqlstmnt % "id"), params={"value": id}).first()
        if resp is None:
            return None, None
        else:
            return resp.name, resp.id

    @query
    def get_service_metric_types(
        self,
        id=None,
        name=None,
        group_name=None,
        metric_type=None,
        measure_unit=None,
        for_update=False,
    ):
        """get_service_metric_types

        :param id:
        :param name:
        :param group_name:
        :param metric_type:
        :param measure_unit:
        :param for_update:
        :return:
        """
        session = self.get_session()
        query = session.query(ServiceMetricType)
        if id is not None:
            query = query.filter(ServiceMetricType.id == id)
        else:
            if name is not None:
                query = query.filter(ServiceMetricType.name == name)

            if group_name is not None:
                query = query.filter(ServiceMetricType.group_name == group_name)

            if metric_type is not None:
                query = query.filter(ServiceMetricType.metric_type == metric_type)

            if measure_unit is not None:
                query = query.filter(ServiceMetricType.measure_unit == measure_unit)

        if for_update:
            query = query.with_for_update()
        return query.all()

    @query
    def get_paginated_service_metric_type(self, group_name=None, metric_type=None, status=None, *args, **kvargs):
        """Get paginated ServiceMetricType.
        :param group_name: metric type [optional]
        :param metric_type: metric type [optional]
        :param status: status[optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=10, 0 => no pagination]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ServiceMetricType
        :raises TransactionError: raise :class:`TransactionError`
        """

        # TBD: gestione filtri di ricerca
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        tables = []

        if group_name is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("group_name"))

        if metric_type is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("metric_type"))

        if status is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("status"))

        res, total = self.get_api_bo_paginated_entities(
            ServiceMetricType,
            tables=tables,
            filters=filters,
            group_name=group_name,
            metric_type=metric_type,
            status=status,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def update_service_metric_type(self, *args, **kvargs):
        """Update ServiceMetricType.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceMetricType`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceMetricType, *args, **kvargs)
        return res

    @transaction
    def delete_service_metric_type(self, id=None):
        session = self.get_session()
        query = session.query(ServiceMetricType)

        if id is not None:
            query = query.filter(ServiceMetricType.id == id)

        query.delete()
        return None

    ####################################
    ###   MetricTypePluginType       ###
    ####################################
    @query
    def get_metric_type_plugin_types(self, id=None, plugin_type_id=None, metric_type_id=None, for_update=False):
        session = self.get_session()
        query = session.query(MetricTypePluginType)
        if id is not None:
            query = query.filter(MetricTypePluginType.id == id)
        else:
            if plugin_type_id is not None:
                query = query.filter(MetricTypePluginType.plugin_type_id == plugin_type_id)

            if metric_type_id is not None:
                query = query.filter(MetricTypePluginType.metric_type_id == metric_type_id)

        if for_update:
            query = query.with_for_update()
        return query.all()

    @query
    def get_metric_type_plugin_type(self, plugin_type_id=None, metric_type_id=None):
        session = self.get_session()
        query = session.query(MetricTypePluginType)
        query = query.filter(MetricTypePluginType.plugin_type_id == plugin_type_id)
        query = query.filter(MetricTypePluginType.metric_type_id == metric_type_id)

        return query.one_or_none()

    ####################################
    ### ServiceMetricTypeLimits      ###
    ####################################
    @query
    def get_service_metric_type_limit(self, id=None, parent_id=None, metric_type_id=None, *args, **kvargs):
        session = self.get_session()
        query = session.query(ServiceMetricTypeLimit)

        if id is not None:
            query = query.filter_by(id=id)
        else:
            query = query.filter_by(parent_id=parent_id)
            query = query.filter_by(metric_type_id=metric_type_id)

        metric_type_limit = query.one_or_none()
        return metric_type_limit

    @query
    def get_service_metric_type_limits(self, name=None, id=None, parent_id=None, metric_type_id=None, *args, **kvargs):
        session = self.get_session()
        query = session.query(ServiceMetricTypeLimit)

        if id is not None:
            query = query.filter_by(id=id)

        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)

        if metric_type_id is not None:
            query = query.filter_by(metric_type_id=metric_type_id)

        if name is not None:
            query = query.filter_by(name=name)

        lists = query.all()
        return lists

    @transaction
    def delete_service_metric_type_limits(self, id=None, parent_id=None):
        session = self.get_session()
        query = session.query(ServiceMetricTypeLimit)

        if id is not None:
            query = query.filter(ServiceMetricTypeLimit.id == id)

        if parent_id is not None:
            query = query.filter(ServiceMetricTypeLimit.parent_id == parent_id)

        query.delete()

        return None

    @transaction
    def update_service_metric_type_limit(self, *args, **kvargs):
        """Update ServiceMetriTypeLimit.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceMetricTypeLimit`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceMetricTypeLimit, *args, **kvargs)
        return res

    ############################
    ###   AppliedBundle   ###
    ############################

    @transaction
    def add_applied_bundle(self, account_id, metric_type_id, start_date, end_date=None):
        """Add applied bundle .

        :param account_id:  account_id
        :param metric_type_id:  metric_type_id
        :param start_date: start_date
        :param end_date: end_date
        :return: :class:`AppliedBundle`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(
            AppliedBundle,
            account_id=account_id,
            metric_type_id=metric_type_id,
            start_date=start_date,
            end_date=end_date,
        )
        return res

    @transaction
    def update_applied_bundle(self, *args, **kvargs):
        """Update AppliedBundle.

        :param int id: entity id.
        :return: :class:`AppliedBundle`
        :raises TransactionError: raise :class:`TransactionError`
        """

        res = self.update_entity(AppliedBundle, *args, **kvargs)
        return res

    @transaction
    def delete_applied_bundle(self, account_id, id):
        """delete one filtered AppliedBundle.

        :param id: AppliedBundle id
        :return: None
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AppliedBundle)

        if account_id is not None:
            query = query.filter(AppliedBundle.account_id == account_id)
            query = query.filter(AppliedBundle.id == id)

        query.delete()
        return None

    @query
    def get_applied_bundle(self, account_id=None, id=None, *args, **kvargs):
        """Get only one or none filtered AppliedBundle.

        :param account_id: identifier account
        :param id: AppliedBundle id
        :return: one of AppliedBundle
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(AppliedBundle)

        if account_id is not None:
            query = session.query(AppliedBundle).filter(account_id=account_id)

        query = session.query(AppliedBundle).filter(AppliedBundle.id == id)

        res = query.one_or_none()
        return res

    @query
    def get_applied_bundle_list(
        self,
        id=None,
        account_id=None,
        metric_type_id=None,
        start_date=None,
        end_date=None,
        *args,
        **kvargs,
    ):
        session = self.get_session()
        query = session.query(AppliedBundle)

        if id is not None:
            query = query.filter_by(id=id)

        if account_id is not None:
            query = query.filter_by(account_id=account_id)

        if metric_type_id is not None:
            query = query.filter_by(metric_type_id=metric_type_id)

        if start_date is not None:
            query = query.filter_by(start_date=start_date)

        if end_date is not None:
            query = query.filter_by(end_date=end_date)

        lists = query.all()
        return lists

    @query
    def get_bundle_container(self, account_id, period_date):
        """Get bundle container

        :param account_id:
        :param period_date:
        :return:
        """
        session = self.get_session()
        query = session.query(ServiceMetricType.group_name).join(AppliedBundle)

        query = (
            query.filter(AppliedBundle.account_id == account_id)
            .filter(AppliedBundle.start_date <= period_date)
            .filter(
                or_(
                    AppliedBundle.end_date.is_(None),
                    AppliedBundle.end_date > period_date,
                )
            )
        )

        lists = query.distinct()
        return lists

    # @query
    # def get_bundle_consume(self, account_id, plugin_name, period):
    #     """Get flat daily consume
    #
    #     :param account_id: id account
    #     :param plugin_name: container plugin_name
    #     :param period: period string "yyyy-mm-dd"
    #     :return dict {metric_type_id: consume_value}
    #     """
    #     rc = aliased(ReportCost)
    #     mtl = aliased(ServiceMetricTypeLimit)
    #     session = self.get_session()
    #     query = session.query(rc.account_id, mtl.metric_type_id,
    #                           func.sum(mtl.value).label('value'))
    #     query = query.join(VAccountPlugin, and_(
    #         VAccountPlugin.account_id == rc.account_id, VAccountPlugin.plugin_name == plugin_name))
    #     query = query.filter(mtl.parent_id == rc.metric_type_id).\
    #         filter(rc.account_id == account_id).\
    #         filter(rc.period == period).filter(rc.plugin_name == plugin_name).\
    #         filter(VAccountPlugin.plugin_category == 'CONTAINER').\
    #         group_by(rc.account_id, mtl.metric_type_id)
    #
    #     # query = session.query(rc.account_id, mtl.metric_type_id, func.sum(mtl.value).label('value'))
    #     # query = query.join(Account).join(Account.capabilities)
    #     # query = query.filter(mtl.parent_id == rc.metric_type_id).\
    #     #     filter(rc.account_id == account_id).\
    #     #     filter(rc.period == period).filter(rc.plugin_name == plugin_name).\
    #     #     filter(AccountCapability.plugin_name == plugin_name).\
    #     #     group_by(rc.account_id, mtl.metric_type_id)
    #
    #     resp = query.all()
    #     consumes = {}
    #     if resp is not None:
    #         consumes = {r[1]: r[2] for r in resp}
    #
    #     return consumes

    @query
    def get_real_consume_daily(self, account_id, plugin_name, period):
        """Real daily resource consumption

        :param account_id: id account
        :param plugin_name: plugin name of a container services
        :param period: day in string "yyyy-mm-dd"
        :return list of dict [{'account_id': 1, 'metric_type_id': 108, 'consumed': 4.0},{...}]
        """
        session = self.get_session()

        resp = []
        services = []
        containers = []

        # get service container for plugin_name
        query = (
            session.query(ServiceInstance.id)
            .join(ServiceDefinition)
            .join(ServiceType)
            .join(ServicePluginType)
            .filter(ServiceInstance.account_id == account_id)
            .filter(ServicePluginType.name_type == plugin_name)
        )
        container = query.all()

        # get all service container childs
        if container is not None:
            containers = list(map(lambda x: x[0], container))
            query = session.query(ServiceLinkInstance.end_service_id).filter(
                ServiceLinkInstance.start_service_id.in_(containers)
            )
            services = query.all()

        if len(services) > 0:
            services = list(map(lambda x: x[0], services))
            services.extend(containers)
            query = session.query(
                AggregateCost.account_id,
                AggregateCost.metric_type_id,
                func.sum(AggregateCost.consumed).label("consumed"),
            ).join(ServiceInstance)

            query = (
                query.filter(AggregateCost.account_id == account_id)
                .filter(ServiceInstance.account_id == account_id)
                .filter(AggregateCost.period == period)
                .filter(ServiceInstance.id.in_(services))
                .group_by(ServiceInstance.account_id, AggregateCost.metric_type_id)
            )
            resp = query.all()
            # self.print_query(self.get_real_consume_daily, query, inspect.getargvalues(inspect.currentframe()))

        # query = session.query(AggregateCost.account_id,
        #                       AggregateCost.metric_type_id,
        #                       func.sum(AggregateCost.consumed).label('consumed')).\
        #     join(ServiceInstance).join(ServiceDefinition).join(ServiceType).join(ServicePluginType)
        #
        # query = query.filter(AggregateCost.account_id == account_id).\
        #     filter(AggregateCost.period == period).\
        #     filter(ServicePluginType.name_type == plugin_name).\
        #     group_by(AggregateCost.account_id, AggregateCost.metric_type_id)
        # resp = query.all()
        # self.print_query(self.get_real_consume_daily, query, inspect.getargvalues(inspect.currentframe()))
        consumes = []
        fields = ["account_id", "metric_type_id", "consumed"]
        for r in resp:
            consume = dict(zip(fields, list(r)))
            consumes.append(consume)
        self.logger.debug2("Get list instant consume: %s" % consumes)
        return consumes

    @query
    def get_flat_by_day(self, account_id, container, period_date):
        """get flat by day

        :param account_id:
        :param container:
        :param period_date:
        :return:
        """
        """
        select account_id, flat_id, count(distinct flat_id) as value
        from v_flat_consume
        where start_date <= DATE('2018-11-22')
          and DATE('2018-11-22')< end_date
          and flat_container = 'ComputeService'
          and account_id = 1
        group by account_id, flat_id;
        """
        session = self.get_session()
        params = {
            "account_id": account_id,
            "container": container,
            "period_date": period_date,
        }
        sql = [
            "select account_id, flat_id, count(distinct flat_id) as value",
            "from v_flat_consume",
            "where start_date <= :period_date",
            "  and end_date > :period_date",
            "  and flat_container = :container",
            "  and account_id = :account_id",
            "group by account_id, flat_id",
        ]
        smtp = text(" ".join(sql))
        query = session.query("account_id", "flat_id", "value").from_statement(smtp).params(**params)
        resp = query.all()

        flats = []
        fields = ["container_id", "flat_id", "value"]
        for r in resp:
            flat = dict(zip(fields, list(r)))
            flats.append(flat)
        self.logger.debug2("Get list instant consume: %s" % (flats))
        return flats

    # @query
    # def get_flat_metric_consume_by_day(self, account_id, container, period_date):
    #     """get_flat_metric_consume_by_day
    #
    #     :param account_id:
    #     :param container:
    #     :param period_date:
    #     :return:
    #     """
    #     session = self.get_session()
    #     query = session.query(VFlatConsume.account_id, VFlatConsume.flat_container, VFlatConsume.metric_id,
    #                           func.sum(VFlatConsume.value).label('value'))
    #
    #     query = query.filter(VFlatConsume.account_id == account_id).\
    #         filter(VFlatConsume.flat_container <= container).\
    #         filter(VFlatConsume.start_date <= period_date).\
    #         filter(or_(text(" %s%s" % (VFlatConsume.__tablename__, '.end_date is not null ')),
    #                    VFlatConsume.end_date > period_date)).\
    #         group_by(VFlatConsume.account_id,
    #                  VFlatConsume.flat_container, VFlatConsume.metric_id)
    #
    #     lists = query.all()
    #     return lists

    @query
    def get_report_cost(self, account_id, plugin_name, metric_type_id, period_date):
        """Get a single ReportCost to override

        :param account_id: flag default price list param
        :param default params base_entity
        :param plugin_name: plugin_name of container instance
        :param metric_type_id: key of metric type bundle
        :param period: sort order [default=DESC]
        :return: One or none ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ReportCost)

        query = (
            query.filter(ReportCost.account_id == account_id)
            .filter(ReportCost.plugin_name == plugin_name)
            .filter(ReportCost.metric_type_id == metric_type_id)
            .filter(ReportCost.period == period_date)
        )

        rc = query.one_or_none()
        return rc

    @query
    def get_report_cost_by_account(self, account_id, oid):
        """Get a single ReportCost

        :param account_id:
        :param oid: report cost id
        :return: One or none ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ReportCost)

        query = query.filter(ReportCost.account_id == account_id).filter(ReportCost.id == oid)

        rc = query.one_or_none()
        return rc

    @query
    def get_report_cost_monthly_by_account(self, account_id, year_month, plugin_name=None):
        """Get an aggregate ReportCost by month

        :param account_id:
        :param year_month: aggregation month
        :param plugin_name: plugin name
        :return: list of ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """
        is_rep_xpr = case(
            [
                (ReportCost.report_date != None, 1.0),
            ],
            else_=0.0,
        ).label("is_reported")

        session = self.get_session()
        query = session.query(
            ReportCost.account_id,
            ReportCost.plugin_name,
            ReportCost.metric_type_id,
            ServiceMetricType.name,
            ServiceMetricType.measure_unit,
            func.sum(ReportCost.value).label("value"),
            func.sum(ReportCost.cost).label("cost"),
            func.max(ReportCost.report_date).label("report_date"),
            func.avg(is_rep_xpr).label("is_reported"),
        )

        if plugin_name is not None:
            query = query.filter(ReportCost.plugin_name == plugin_name)

        query = (
            query.join(ServiceMetricType)
            .filter(ReportCost.account_id == account_id)
            .filter(ReportCost.period.like("%s%s" % (year_month, "%")))
            .group_by(
                ReportCost.account_id,
                ReportCost.plugin_name,
                ReportCost.metric_type_id,
                ServiceMetricType.name,
                ServiceMetricType.measure_unit,
            )
        )

        rc = query.all()
        rcs = []

        fields = [
            "account_id",
            "plugin_name",
            "metric_type_id",
            "name",
            "measure_unit",
            "value",
            "cost",
            "report_date",
            "is_reported",
        ]
        for r in rc:
            repcost = dict(zip(fields, list(r)))
            repcost["period"] = year_month
            # verify the reported data
            if r[8] != 1.0:
                repcost["report_date"] = None  # Last reported date in a month
                repcost["is_reported"] = False
            else:
                repcost["is_reported"] = True
                repcost["report_date"] = format_date(r[7])

            rcs.append(repcost)

        return rcs

    @query
    def get_report_cost_monthly_by_accounts(self, account_ids, start_date=None, end_date=None, plugin_name=None):
        """Get an aggregate ReportCost by month

        :param account_ids: array of account id
        :param start_date: aggregation start date  (optional)
        :param end_date: aggregation end date (optional)
        :param plugin_name: plugin name

        :return: list of ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """

        is_rep_xpr = case(
            [
                (ReportCost.report_date != None, 1.0),
            ],
            else_=0.0,
        ).label("is_reported")

        session = self.get_session()
        query = session.query(
            ReportCost.plugin_name,
            ReportCost.metric_type_id,
            ServiceMetricType.name,
            func.coalesce(ServiceMetricType.measure_unit, ""),
            func.sum(ReportCost.value).label("value"),
            func.sum(ReportCost.cost).label("cost"),
            func.max(ReportCost.report_date).label("report_date"),
            func.avg(is_rep_xpr).label("is_reported"),
        )

        if account_ids is not None:
            if len(account_ids) > 0:
                query = query.filter(ReportCost.account_id.in_(account_ids))
            else:
                return []

        if start_date is not None and end_date is not None:
            query = query.filter(ReportCost.period >= start_date)
            query = query.filter(ReportCost.period <= end_date)

        if plugin_name is not None:
            query = query.filter(ReportCost.plugin_name == plugin_name)

        query = query.join(ServiceMetricType)
        query = query.group_by(
            ReportCost.plugin_name,
            ReportCost.metric_type_id,
            ServiceMetricType.name,
            ServiceMetricType.measure_unit,
        )

        rc = query.all()
        rcs = []

        fields = [
            "plugin_name",
            "metric_type_id",
            "name",
            "measure_unit",
            "value",
            "cost",
            "report_date",
            "is_reported",
        ]
        for r in rc:
            repcost = dict(zip(fields, list(r)))
            repcost["period"] = "%s - %s" % (start_date, end_date)
            # verify the reported data
            if r[7] != 1.0:
                repcost["report_date"] = None  # Last reported date in a month
                repcost["is_reported"] = False
            else:
                repcost["is_reported"] = True
                repcost["report_date"] = format_date(r[6])
            rcs.append(repcost)

        return rcs

    @query
    def get_plugin_type_by_account(self, account_ids, category=None):
        pass

    #     session = self.get_session()

    #     query = session.query(func.distinct(VAccountPlugin.plugin_name).label('plugin_name')).\
    #         filter(VAccountPlugin.account_id.in_(account_ids))

    #     if category is not None:
    #         query = query.filter(VAccountPlugin.plugin_category == category)

    #     res = query.all()
    #     return [r[0] for r in res]

    @query
    def get_credit_by_authority_on_year(
        self,
        year,
        division_id=None,
        organization_id=None,
        division_id_list=None,
        organization_id_list=None,
    ):
        """Get aggregate Credit from Agreement for authority by year

        :param year: aggregation on year
        :param division_id: id division (optional)
        :param organization_id: id organization (optional)
        :param division_id_list : array of division id (optional)
        :param organization_id_list : array of organization id (optional)
        :return: amount of Agreements
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        query = session.query(func.coalesce(func.sum(Agreement.amount).label("amount"), 0.0))
        if division_id is not None:
            query = query.join(Wallet).filter(Wallet.division_id == division_id)

        if division_id_list is not None:
            if len(division_id_list) > 0:
                query = query.join(Wallet).filter(Wallet.division_id.in_(division_id_list))
            else:
                return 0.0
        if organization_id is not None:
            query = query.join(Wallet).join(Division).filter(Division.organization_id == organization_id)

        if organization_id_list is not None:
            if len(organization_id_list) > 0:
                query = query.join(Wallet).join(Division).filter(Division.organization_id.in_(organization_id_list))
            else:
                return 0.0

        query = query.filter(Agreement.service_status_id == 1).filter(Wallet.year == year)

        res = query.one_or_none()
        if res is not None and len(res) > 0:
            return res[0]
        return 0.0

    @query
    def get_cost_by_authority_on_period(
        self,
        period_start,
        period_end=None,
        account_id=None,
        division_id=None,
        organization_id=None,
        account_id_list=None,
        division_id_list=None,
        organization_id_list=None,
        plugin_name=None,
        reported=None,
    ):
        """Get an aggregate ReportCost by period

        :param account_id: id account (optional)
        :param division_id: id division (optional)
        :param organization_id: id organization (optional)
        :param account_id_list: array of account id (optional)
        :param division_id_list: array of division id (optional)
        :param organization_id_list: array of organization id (optional)
        :param period_start: aggregation period start
        :param period_end: aggregation period end (optional)
        :param plugin_name: plugin name (optional)
        :param reported: add filter with report date not null if true, report date is null if false. no filter otherwise

        :return: list of ReportCost
        :raises TransactionError: raise :class:`TransactionError`
        """

        is_rep_xpr = case(
            [
                (ReportCost.report_date != None, 1.0),
            ],
            else_=0.0,
        ).label("is_reported")

        session = self.get_session()
        query = session.query(func.sum(ReportCost.cost).label("cost"))

        if account_id_list is not None:
            if len(account_id_list) > 0:
                query = query.filter(ReportCost.account_id.in_(account_id_list))
            else:
                return 0.0

        if division_id is not None:
            query = query.join(Account)

        if division_id_list is not None:
            if len(division_id_list) > 0:
                query = query.join(Account)
                query = query.filter(Account.division_id.in_(division_id_list))
            else:
                return 0.0

        if organization_id is not None:
            query = query.join(Account).join(Division)

        if organization_id_list is not None:
            if len(organization_id_list) > 0:
                query = query.join(Account).join(Division)
                query = query.filter(Division.organization_id.in_(organization_id_list))
            else:
                return 0.0

        if plugin_name is not None:
            query = query.filter(ReportCost.plugin_name == plugin_name)

        if period_end is not None:
            query = query.filter(ReportCost.period <= period_end)

        if reported is not None:
            if reported:
                query = query.filter(is_rep_xpr == 1.0)
            else:
                query = query.filter(is_rep_xpr == 0.0)

        if period_start is not None:
            query = query.filter(ReportCost.period >= period_start)

        if account_id is not None:
            query = query.filter(ReportCost.account_id == account_id).group_by(ReportCost.account_id)

        if division_id is not None:
            query = query.filter(Account.division_id == division_id).group_by(Account.division_id)

        if organization_id is not None:
            query = query.filter(Division.organization_id == organization_id).group_by(Division.organization_id)

        rc = query.one_or_none()
        cost = 0.0
        if rc is not None and len(rc) > 0 and rc[0] is not None:
            cost = rc[0]
        return cost

    ############################
    ###   service_price_lis  ###
    ############################

    @query
    def get_service_price_list(self, id):
        session = self.get_session()
        query = session.query(ServicePriceList).filter(ServicePriceList.id == id)

        price_list = query.one_or_none()
        return price_list

    @query
    def get_service_price_lists(self, flag_default=None, *args, **kvargs):
        session = self.get_session()
        query = session.query(ServicePriceList)
        if flag_default is not None:
            query = query.filter_by(flag_default=flag_default)

        lists = query.all()
        return lists

    @query
    def get_paginated_service_price_lists(self, flag_default=None, *args, **kvargs):
        """Get paginated ServiceMetric.

        :param flag_default: flag default price list param
        :param default params base_entity
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ServicePriceList
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if flag_default is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("flag_default"))

        kvargs.update(flag_default=flag_default)

        res, total = self.get_api_bo_paginated_entities(ServicePriceList, filters=filters, *args, **kvargs)
        return res, total

    @transaction
    def update_service_price_list(self, *args, **kvargs):
        """Update ServicePriceList.

        :param int oid: entity id. [optional]
        :return: :class:`ServicePriceList`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServicePriceList, *args, **kvargs)
        return res

    ############################
    ### ServicePriceMetric   ###
    ############################
    @query
    def get_service_price_metric(self, id):
        session = self.get_session()
        query = session.query(ServicePriceMetric).filter(ServicePriceMetric.id == id)

        metric = query.one_or_none()
        return metric

    @query
    def get_service_price_metrics(self, metric_type_id=None, price_list_id=None, time_unit=None, *args, **kvargs):
        kvargs.update({"size": 0})  # no pagination
        res, total = self.get_paginated_service_price_metrics(
            metric_type_id, price_list_id, time_unit=time_unit, *args, **kvargs
        )
        return res

    @query
    def get_paginated_service_price_metrics(
        self, metric_type_id=None, price_list_id=None, time_unit=None, *args, **kvargs
    ):
        """Get paginated ServicePriceMetric.

        :param metric_type_id: metric type [optional]
        :param price_list_id: instance id [optional]

        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=10, 0 => no pagination]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ServicePriceMetric
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        tables = []

        if metric_type_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("metric_type_id", column="fk_metric_type_id"))

        if price_list_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("price_list_id", column="fk_price_list_id"))

        if time_unit is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("time_unit"))

        kvargs.update(
            metric_type_id=metric_type_id,
            price_list_id=price_list_id,
            time_unit=time_unit,
        )

        kvargs["with_perm_tag"] = False
        res, total = self.get_api_bo_paginated_entities(
            ServicePriceMetric, tables=tables, filters=filters, *args, **kvargs
        )
        return res, total

    @transaction
    def update_service_price_metric(self, *args, **kvargs):
        """Update ServicePriceMetric.

        :param int oid: entity id. [optional]
        :return: :class:`ServicePriceMetric`
        :raises TransactionError: raise :class:`TransactionError`
        """
        thresholds = kvargs.pop("thresholds", None)
        oid = self.update_entity(ServicePriceMetric, *args, **kvargs)
        if thresholds:
            self.logger.debug2("deleting thresholds %s" % oid)
            statement = delete(ServicePriceMetricThresholds).where(
                ServicePriceMetricThresholds.service_price_metric_id == oid
            )
            self.logger.debug2("deleting statemente %s " % statement)
            session = self.get_session()
            session.execute(statement)
            for theshold in thresholds:
                thr_pl = ServicePriceMetricThresholds(
                    from_ammount=theshold.get("ammount_from", 0),
                    till_ammount=theshold.get("ammount_till", None),
                    service_price_metric_id=oid,
                    price=theshold.get("price", 0.0),
                )
                self.add(thr_pl)

        return oid

    @transaction
    def purge_service_price_metric(self, entity):
        """hard delete of service price metric delete
        also thresholds ServicePriceMetric

        :raises TransactionError: raise :class:`TransactionError`
        """

        self.logger.debug2("Delete ServicePriceMetricThresholds for entity %s %s" % (entity.__class__.__name__, entity))
        statement = delete(ServicePriceMetricThresholds).where(
            ServicePriceMetricThresholds.service_price_metric_id == entity.id
        )
        session = self.get_session()
        session.execute(statement)

        self.purge(entity)

    @transaction
    def delete_service_price_metric(self, *args, **kvargs):
        """Delete ServicePriceMetric.

        :param int oid: entity id. [optional]
        :return: :class:`ServicePriceMetric`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(ServicePriceMetric, *args, **kvargs)
        return res

    #
    # job
    #
    def get_paginated_jobs(self, job=None, account_id=None, *args, **kvargs):
        """Get jobs

        :param job: job id. [optional]
        :param account_id: account id. [optional]
        :param size: max number of jobs [default=10]
        :param page: page of jobs [default=0]
        :return: list of ServiceJob instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        self.logger.warn(kvargs)
        if job is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("job"))

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id"))

        kvargs.update(job=job, account_id=account_id)
        res, total = self.get_api_bo_paginated_entities(ServiceJob, filters=filters, *args, **kvargs)

        self.logger.debug2("Get service job: %s" % truncate(res))
        return res, total

    def get_service_job_by_task_id(self, task_id):
        session = self.get_session()
        query = session.query(ServiceJob).filter(ServiceJob.task_id == task_id)

        job = query.one_or_none()
        return job

    @transaction
    def update_service_job(self, *args, **kvargs):
        """Update ServiceJob

        :param int oid: entity id
        :return: :class:`ServiceJob`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceJob, *args, **kvargs)
        return res

    ############################
    ### ServiceJobSchedule   ###
    ############################

    @query
    def get_service_job_schedule(self, oid):
        session = self.get_session()
        query = session.query(ServiceJobSchedule).filter(ServiceJobSchedule.id == oid)

        metric = query.one_or_none()
        return metric

    @query
    def get_paginated_service_job_schedules(self, job_name=None, schedule_type=None, *args, **kvargs):
        """Get paginated ServiceJobSchedule.

        :param job_name: job name to execute [optional]
        :param schedule_type: schedule type [optional]

        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=10, 0 => no pagination]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of paginated ServiceJobSchedule
        :raises TransactionError: raise :class:`TransactionError`
        """
        filters = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)

        if job_name is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("job_name", column="job_name"))

        if schedule_type is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("schedule_type", column="schedule_type"))

        kvargs.update(job_name=job_name, schedule_type=schedule_type)

        res, total = self.get_api_bo_paginated_entities(
            ServiceJobSchedule, filters=filters, with_perm_tag=False, *args, **kvargs
        )
        return res, total

    @transaction
    def update_service_job_schedule(self, *args, **kvargs):
        """Update ServiceJobSchedule.

        :param int oid: entity id. [optional]
        :return: :class:`ServiceSchedule`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceJobSchedule, *args, **kvargs)
        return res

    @query
    def get_task_intervals(self, execution_date=None, metric_num=None, task=None, *args, **kvargs):
        session = self.get_session()
        query = session.query(ServiceTaskInterval)

        if execution_date is not None:
            query = query.filter(
                ServiceTaskInterval.start_date <= execution_date,
                execution_date <= ServiceTaskInterval.end_date,
            )

        if metric_num is not None:
            query = query.filter_by(metric_num=metric_num)

        if task is not None:
            query = query.filter_by(task=task)

        query = self.add_base_entity_filters(query, *args, **kvargs)

        lists = query.all()
        return lists

    #
    # tags util
    #
    def order_query_servicetags(self, kvargs):
        """Order service tags by name

        :param kvargs: query params
        :return: kvargs updated
        """
        tags = kvargs.get("servicetags")
        tags = tags.split(",")
        tags.sort()
        kvargs["servicetag_list"] = tags
        kvargs["servicetags"] = ",".join(tags)
        return kvargs

    #
    # tags
    #
    @query
    def count_tags(self):
        """Get tags count.

        :return: tags number
        :raises QueryError: raise :class:`QueryError`
        """
        return self.count_entities(ServiceTag)

    @query
    def get_tags(self, *args, **kvargs):
        """Get tags.

        :param value: tag value [optional]
        :param value_list: tag value list [optional]
        :param objid: tag objid [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceTag
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if "value" in kvargs and kvargs.get("value") is not None:
            filters = ["AND name like :value"]
        elif "value_list" in kvargs and kvargs.get("value_list") is not None and len(kvargs.get("value_list")) > 0:
            filters.append(" AND name IN :listServiceTagsName ")
            kvargs.update(listServiceTagsName=tuple(kvargs.pop("value_list")))

        if "objid" in kvargs and kvargs.get("objid") is not None:
            filters.append(" AND objid like :objid ")

        tags, total = self.get_paginated_entities(ServiceTag, filters=filters, *args, **kvargs)
        services = self.get_tags_service_occurrences(*args, **kvargs)
        links = self.get_tags_link_occurrences(*args, **kvargs)
        res = []
        for tag in tags:
            res.append(ServiceTagOccurrences(tag, services.get(tag.id, 0), links.get(tag.id, 0)))

        return res, total

    @query
    def get_tags_service_occurrences(self, *args, **kvargs):
        """Get tags occurrences for service instances.

        :param value: tag value [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of tags with occurrences
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("tag_instance", "t4")]
        select_fields = ["count(t4.fk_service_instance_id) as count"]
        filters = ["AND t4.fk_service_tag_id=t3.id"]
        if "value" in kvargs and kvargs.get("value") is not None:
            filters.append("AND name like :value")
        elif "value_list" in kvargs and kvargs.get("value_list") is not None and len(kvargs.get("value_list")) > 0:
            filters.append(" AND t3.name IN :listServiceTagsName ")
            kvargs.update(listServiceTagsName=tuple(kvargs.pop("value_list")))

        res, total = self.get_paginated_entities(
            ServiceTagCount,
            tables=tables,
            select_fields=select_fields,
            filters=filters,
            *args,
            **kvargs,
        )
        return {i.id: i.count for i in res}

    @query
    def get_tags_link_occurrences(self, *args, **kvargs):
        """Get tags occurrences for links.

        :param value: tag value [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of tags with occurrences
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("tag_instance_link", "t4")]
        select_fields = ["count(t4.fk_service_link_id) as count"]
        filters = ["AND t4.fk_service_tag_id=t3.id"]
        if "value" in kvargs and kvargs.get("value") is not None:
            filters.append("AND name like :value")
        elif "value_list" in kvargs and kvargs.get("value_list") is not None and len(kvargs.get("value_list")) > 0:
            filters.append(" AND t3.name IN :listServiceTagsName ")
            kvargs.update(listServiceTagsName=tuple(kvargs.pop("value_list")))

        res, total = self.get_paginated_entities(
            ServiceTagCount,
            tables=tables,
            select_fields=select_fields,
            filters=filters,
            *args,
            **kvargs,
        )
        return {i.id: i.count for i in res}

    @transaction
    def add_tag(self, value, objid):
        """Add tag.

        :param value: str tag value.
        :param objid: str objid
        :return: :class:`ServiceTag`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(ServiceTag, value, objid)
        return res

    @transaction
    def update_tag(self, *args, **kvargs):
        """Update tag.

        :param int oid: entity id. [optional]
        :param value str: tag value. [optional]
        :return: :class:`ServiceTag`
        :raises TransactionError: raise :class:`TransactionError`
        """
        kvargs["name"] = kvargs.pop("value", None)
        res = self.update_entity(ServiceTag, *args, **kvargs)
        return res

    @transaction
    def delete_tag(self, *args, **kvargs):
        """Remove tag.
        :param int oid: entity id. [optional]
        :return: :class:`ServiceTag`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(ServiceTag, *args, **kvargs)
        return res

    #
    # link
    #
    @query
    def count_links(self):
        """Get links count.

        :return: links number
        :raises QueryError: raise :class:`QueryError`
        """
        return self.count_entities(ServiceLink)

    @query
    def is_linked(self, start_service, end_service):
        """Verifiy if two services are linked

        :param start_service: start service id
        :param end_service: end service id
        :return: list of :class:`ServiceLink`
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        res = session.query(ServiceLink).filter_by(start_service_id=start_service).filter_by(end_service_id=end_service)
        res = res.all()

        if len(res) == 0:
            return False

        return True

    @query
    def get_links(self, *args, **kvargs):
        """Get links.

        :param start_service: start service id [optional]
        :param end_service: end service id [optional]
        :param service: start or end service id [optional]
        :param type: link type or partial type with % as jolly character [optional]
        :param servicetags: list of tags comma separated. All tags in the list must be met [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceLink
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        custom_select = None
        if kvargs.get("start_service", None) is not None and kvargs.get("end_service", None) is not None:
            filters.append("AND (start_service_id=:start_service and end_service_id=:end_service)")
        elif kvargs.get("start_service", None) is not None:
            filters.append("AND start_service_id=:start_service")
        elif kvargs.get("end_service", None) is not None:
            filters.append("AND end_service_id=:end_service")
        elif kvargs.get("service", None) is not None:
            filters.append("AND (end_service_id=:service or start_service_id=:service)")
        if kvargs.get("type", None) is not None:
            filters.append("AND t3.type like :type")
        ## TODO FIX GROUP BY
        if kvargs.get("servicetags", None) is not None:
            custom_select = (
                "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name) as tags "
                "FROM service_link t1, service_tag t2, tag_instance_link t3 "
                "WHERE t3.fk_service_tag_id=t2.id and t3.fk_service_link_id=t1.id "
                "and (t2.name in :servicetag_list) "
                "GROUP BY t1.id ORDER BY t2.name)"
            )
            kvargs = self.order_query_servicetags(kvargs)
            filters.append("AND t3.tags=:servicetags")

        res, total = self.get_paginated_entities(
            ServiceLink, filters=filters, custom_select=custom_select, *args, **kvargs
        )
        return res, total

    @query
    def get_links_from_tags(self, *args, **kvargs):
        """Get links with all the of tags specified.

        :param service_tags: list of tags that links must have
        :return: list of Link instances
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("tags_Links", "t4"), ("service_tag", "t5")]
        select_fields = ["GROUP_CONCAT(t5.value) as tags"]
        filters = [
            "AND t4.fk_service_tag_id=t5.id",
            "AND t3.id=t4.fk_service_link_id",
            "AND t5.value IN :service_tags",
        ]
        res, total = self.get_paginated_entities(
            ServiceLink,
            filters=filters,
            select_fields=select_fields,
            tables=tables,
            *args,
            **kvargs,
        )
        return res, total

    @transaction
    def add_link(
        self,
        objid=None,
        name=None,
        ltype=None,
        start_service=None,
        end_service=None,
        attributes="",
    ):
        """Add link.

        :param objid:  link objid
        :param name:  link name
        :param ltype:  link type
        :param start_service: start service reference
        :param end_service: end service reference
        :param attributes: link attributes
        :return: :class:`ServiceLink`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(
            ServiceLink,
            objid,
            name,
            ltype,
            start_service,
            end_service,
            attributes=attributes,
        )
        return res

    @transaction
    def update_link(self, *args, **kvargs):
        """Update link.

        :param int oid: entity id. [optional]
        :param name: link name [optional]
        :param ltype: link type [optional]
        :param start_service: start_service id [optional]
        :param end_service: end_service id [optional]
        :param attributes: service attributes [optional]
        :return: :class:`ServiceLink`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(ServiceLink, *args, **kvargs)
        return res

    @transaction
    def delete_link(self, *args, **kvargs):
        """Remove link.
        :param int oid: entity id. [optional]
        :return: :class:`ServiceLink`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(ServiceLink, *args, **kvargs)
        return res

    @query
    def get_link_tags(self, link, *args, **kvargs):
        """Get link tags.

        :param link: link id
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of ServiceTag paginated, total
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("tag_instance_link", "t4")]
        filters = ["AND t3.id=t4.fk_service_tag_id", "AND t4.fk_service_link_id=:link"]
        res, total = self.get_paginated_entities(ServiceTag, filters=filters, tables=tables, link=link, *args, **kvargs)
        return res, total

    @transaction
    def add_link_tag(self, link, tag):
        """Add a tag to a link.

        :param link: ServiceLink: link instance
        :param tag: Tag: tag instance.
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        self.get_session()
        tags = link.tag
        if tag not in tags:
            tags.append(tag)
        self.logger.debug2("Add tag %s to link: %s" % (tag, link))
        return True

    @transaction
    def remove_link_tag(self, link, tag):
        """Remove a tag from a link.

        :param link: Service link instance
        :param tag: Tag tag instance.
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        tags = link.tag
        if tag in tags:
            tags.remove(tag)
        self.logger.debug2("Remove tag %s from link: %s" % (tag, link))
        return True

    #
    # service to link
    #
    @query
    def get_service_links_internal(self, service):
        """Get service links. Use this method for internal query without authorization.

        :param service: service id
        :return: ServiceLink instance list
        :raise QueryError:
        """
        session = self.get_session()
        res = (
            session.query(ServiceLink)
            .filter((ServiceLink.start_service_id == service) | (ServiceLink.end_service_id == service))
            .all()
        )
        self.logger.debug2("Get service %s links: %s" % (service, truncate(res)))
        return res

    @query
    def get_link_among_services_internal(self, start, end):
        """Get link among services. Use this method for internal query without authorization.

        :param start: start service id
        :param end: end service id
        :return: ServiceLink instance list
        :raise QueryError:
        """
        session = self.get_session()
        res = (
            session.query(ServiceLink)
            .filter((ServiceLink.start_service_id == start) & (ServiceLink.end_service_id == end))
            .one()
        )
        self.logger.debug2("Get link among service %s and %s: %s" % (start, end, truncate(res)))
        return res

    @query
    def get_linked_services(self, service=None, link_type=None, link_type_filter=None, *args, **kvargs):
        """Get linked services.

        :param service: service id
        :param link_type: link type
        :param link_type_filter: link type filter
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return:list of records
        :raise QueryError:
        """
        tables = [("service_link", "t4")]
        filters: List[str] = ApiBusinessObject.get_base_entity_sqlfilters(*args, **kvargs)
        filters.extend(
            [
                "AND (t4.start_service_id=:service OR t4.end_service_id=:service)",
                "AND (t4.start_service_id=t3.id OR t4.end_service_id=t3.id)",
                "AND t3.id!=:service",
            ]
        )
        if link_type is not None:
            filters.append("AND t4.type=:link_type")
        if link_type_filter is not None:
            filters.append("AND t4.type like :link_type_filter")

        res, total = self.get_api_bo_paginated_entities(
            ServiceInstance,
            filters=filters,
            service=service,
            link_type=link_type,
            link_type_filter=link_type_filter,
            tables=tables,
            *args,
            **kvargs,
        )
        self.logger.debug2("Get linked services: %s" % res)
        return res, total

    @query
    def get_instant_consumes(self, oid):
        """Get instant consume.

        :param int oid: account id
        :return: list of metrics object
        :raise QueryError:
        """
        session = self.get_session()
        params = {"oid": oid}
        sql1 = [
            "select v.parent as container_id, mc.metric_type_name as metric_type_name, smt.group_name as group_name, "
            "sum(mc.value) as value,",
            "max(mc.extraction_date) as extraction_date,",
            "max(pt.category )  as category,",
            "max(pt.name_type) as plugin_name,",
            "max(p1.id) as instance_id",
            "from service_instance i",
            "join v_instance_horiz v on v.child = i.id",
            "join service_instance p on p.id = v.parent",
            "join service_definition d on d.id = p.fk_service_definition_id",
            "join service_type t on t.id = d.fk_service_type_id",
            "join service_instance p1 on p1.id=v.child",
            "join service_definition d1 on d1.id = p1.fk_service_definition_id",
            "join service_type t1 on t1.id = d1.fk_service_type_id",
            "join service_plugin_type pt on pt.objclass=t1.objclass",
            "left join v_metric_consume mc on mc.service_instance_id = i.id",
            "join service_metric_type smt on smt.id=mc.metric_type_id",
            "join (select fk_service_instance_id, max(fk_job_id) as fk_job_id from service_metric group by "
            "fk_service_instance_id) as ljob on ljob.fk_job_id = mc.job_id",
            "where t.flag_container = true and p.active = 1 and p.fk_account_id=:oid ",
            "group by container_id, metric_type_name, group_name, extraction_date",
        ]
        smtp1 = text(" ".join(sql1))
        self.logger.warning("%s" % smtp1)
        # get all  metric of type consume
        sql2 = [
            "select container_id, metric_type_name, group_name, sum(value) as value, "
            "max(extraction_date) as extraction_date from (",
            "%s" % smtp1,
            ") as b",
            "group by b.container_id, b.metric_type_name, b.group_name",
        ]

        smtp2 = text(" ".join(sql2))
        query = (
            session.query(
                "container_id",
                "metric_type_name",
                "group_name",
                "value",
                "extraction_date",
            )
            .from_statement(smtp2)
            .params(**params)
        )
        res = query.all()

        # calculate istance metric, for example vm instance, database instance
        # ...
        sql2 = [
            "select container_id,  plugin_name as metric_type_name, max(group_name) as group_name, "
            "count(distinct instance_id) as value, max(extraction_date) as extraction_date from ( ",
            "%s" % smtp1,
            ") as b ",
            "where b.category = '%s' " % SrvPluginTypeCategory.INSTANCE,
            "and b.group_name in ( select name_type from service_plugin_type where category = '%s' ) "
            % SrvPluginTypeCategory.CONTAINER,
            "group by b.container_id, b.instance_id, b.category, b.plugin_name, b.group_name ",
        ]

        smtp2 = text(" ".join(sql2))
        query = (
            session.query(
                "container_id",
                "metric_type_name",
                "group_name",
                "value",
                "extraction_date",
            )
            .from_statement(smtp2)
            .params(**params)
        )
        res_instance = query.all()
        res.extend(res_instance)

        self.logger.debug2("Get list instant consume: %s" % (res))
        return res

    #################################
    ###   ServiceInstantConsume   ###
    #################################

    @query
    def get_service_instant_consume(self, id=None, *args, **kvargs):
        """Get a specific service instant consume.

        :param id: entity id
        :return: one of ServiceInstantConsume
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        query = session.query(ServiceInstantConsume).filter(ServiceInstantConsume.id == id)
        res = query.one_or_none()
        return res

    @query
    def get_service_instant_consumes(self, account_list_id, plugin_name=None, *args, **kvargs):
        """Get service instant consume record data grouped by account and plugin name.

        :param account_id_list: list of account id [optional
        :param plugin_name: plugin name [optional]
        :return: array of record ServiceInstantConsume data
        :raises TransactionError: raise :class:TransactionError
        """
        session = self.get_session()
        query = session.query(
            ServiceInstantConsume.plugin_name,
            ServiceInstantConsume.metric_group_name,
            ServiceInstantConsume.metric_unit,
            ServiceInstantConsume.metric_instant_value,
            ServiceInstantConsume.metric_value,
            ServiceInstantConsume.creation_date,
        ).filter(ServiceInstantConsume.account_id.in_(account_list_id))

        if plugin_name is not None:
            query = query.filter(ServiceInstantConsume.plugin_name == plugin_name)

        res = query.all()

        instance_consumes = []
        for r in res:
            item = {
                "plugin_name": r[0],
                "metric_group_name": r[1],
                "metric_unit": r[2],
                "metric_instant_value": r[3],
                "metric_value": r[4],
                "creation_date": r[5],
            }
            instance_consumes.append(item)
        self.logger.debug2("Get service instant consumes: %s" % instance_consumes)
        return instance_consumes

    @query
    def get_paginated_service_instant_consumes(
        self,
        id=None,
        plugin_name=None,
        group_name=None,
        organization_id=None,
        division_id=None,
        account_id=None,
        service_instance_id=None,
        job_id=None,
        for_update=False,
        *args,
        **kvargs,
    ):
        """Get a list of service instant consume.

        :param id: entity id [optional]
        :param plugin_name: service container plugin type name [optional]
        :param group_name:  metric group_name [optional]
        :param instant_value: metric instant value [optional]
        :param unit:  metric unit [optional]
        :param value:  metric group_name [optional]
        :param service_instance_id: id service instance [optional]
        :param account_id: id account [optional]
        :param division_id: id division [optional]
        :param organization_id: id organization [optional]
        :param organization_list_id: list organization id [optional]
        :param division_list_id: list division id [optional]
        :param account_list_id: list account id [optional]
        :param service_instance_list_id: list service instance id [optional]
        :param job_id: job id [optional]
        :param creation_date: service instant consume creation_date  [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: array of ServiceInstantConsume
        :raises TransactionError: raise :class:`TransactionError`
        """

        tables = []
        filters = []

        if account_id is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("account_id", column="fk_account_id"))
        elif (
            "account_id_list" in kvargs
            and kvargs.get("account_id_list", None) is not None
            and len(kvargs.get("account_id_list")) > 0
        ):
            filters.append(" AND t3.fk_account_id IN :account_id_list ")
            kvargs.update(account_id_list=tuple(kvargs.pop("account_id_list")))
            self.logger.warning("account_id_list=%s" % kvargs.get("account_id_list"))

        if service_instance_id is not None:
            filters.append(
                PaginatedQueryGenerator.create_sqlfilter("service_instance_id", column="fk_service_instance_id")
            )

        if plugin_name is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("plugin_name"))

        if group_name is not None:
            filters.append(PaginatedQueryGenerator.create_sqlfilter("group_name", column="metric_group_name"))

        kvargs["with_perm_tag"] = False
        kvargs.update(
            plugin_name=plugin_name,
            group_name=group_name,
            service_instance_id=service_instance_id,
            account_id=account_id,
            job_id=job_id,
        )

        res, total = self.get_api_bo_paginated_entities(
            ServiceInstantConsume, tables=tables, filters=filters, *args, **kvargs
        )

        return res, total
