# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging

from beehive_service.model.base import ApiBusinessObject, Base, BaseApiBusinessObject, SrvStatusType, ParamType, OrgType
from beehive_service.model.account import Account, AccountServiceDefinition
from beehive_service.model.account_capability import AccountCapability, AccountCapabilityAssoc
from beehive_service.model.aggreagate_cost import AggregateCost, AggregateCostType
from beehive_service.model.deprecated import AccountsPrices, Agreement,AppliedBundle,DivisionsPrices
from beehive_service.model.division import Division
from beehive_service.model.monitoring_message import MonitoringMessage
from beehive_service.model.monitoring_parameter import MonitoringParameter
from beehive_service.model.organization import Organization
from beehive_service.model.permtag import PermTag
from beehive_service.model.permtag_entity import PermTagEntity
from beehive_service.model.service_catalog import ServiceCatalog
from beehive_service.model.service_definition import ServiceDefinition, ServiceConfig
from beehive_service.model.service_instance import ServiceInstance #,tags_links
from beehive_service.model.service_job import ServiceJob
from beehive_service.model.service_job_schedule import ServiceJobSchedule
from beehive_service.model.service_link import ServiceLink
from beehive_service.model.service_link_def import ServiceLinkDef
from beehive_service.model.service_link_instance import ServiceLinkInstance
from beehive_service.model.service_metric import ServiceMetric
from beehive_service.model.service_metric_type import ServiceMetricType, MetricType
from beehive_service.model.service_metric_type_limit import ServiceMetricTypeLimit
from beehive_service.model.service_plugin_type import ServicePluginType
from beehive_service.model.service_process import ServiceProcess
from beehive_service.model.service_status import  ServiceStatus
from beehive_service.model.service_tag import ServiceTag, ServiceTagWithInstance, ServiceTagOccurrences
from beehive_service.model.service_task_interval import ServiceTaskInterval
from beehive_service.model.service_type import ServiceType

logger = logging.getLogger(__name__)
