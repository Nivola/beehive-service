# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.assert_util import AssertUtil
from beehive_service.model.base import SrvStatusType

__SITE_NAMES__ = ["SiteTorino01", "SiteTorino02", "SiteVercelli03", "SiteTorino05", "SiteGenova06"]

__PLATFORM_NAME__ = ["OpenStack", "VMWare"]
__PLATFORM_ID__ = ["10", "20"]
__PRICE_TIME_UNIT__ = ["YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND"]
__PRICE_TYPE__ = ["SIMPLE", "SLICE", "THRESHOLD"]
__ARCHITECTURE__ = ["i386", "x86_64"]
__SCHEDULE_TYPE__ = ["crontab", "timedelta"]
__REGEX_AWS_SG_NAME_AND_DESC__ = "^[a-zA-Z0-9 ._\-:\/\(\)#,@+=&;{}!$\*]{1,255}$"
__REGEX_PORT_RANGE__ = (
    "^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|"
    "([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4})|(-1))$"
)
__RULE_GROUP_INGRESS__ = "RULE_GROUP_INGRESS"
__RULE_GROUP_EGRESS__ = "RULE_GROUP_EGRESS"
__SRV_STORAGE_PROTOCOL_TYPE__ = ["NFS", "CIFS"]
__SRV_STORAGE_PROTOCOL_TYPE_NFS__ = "NFS"
__SRV_STORAGE_PROTOCOL_TYPE_CIFS__ = "CIFS"
# __SRV_STORAGE_PREFIX_SHARE_PROTOCOL_DEFAULT__ = "netapp" # non usato
__SRV_STORAGE_PROTOCOL_TYPE_DEFAULT__ = __SRV_STORAGE_PROTOCOL_TYPE_NFS__
__SRV_STORAGE_PERFORMANCE_MODE__ = ["generalPurpose", "localPurpose"]
__SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__ = "generalPurpose"
__SRV_AWS_STORAGE_STATUS__ = [
    "creating",
    "available",
    "deleting",
    "deleted",
    "unknown",
    "error",
]
__SRV_DEFAULT_STORAGE_EFS__ = "--DEFAULT--storage-efs--"
__SRV_STORAGE_GRANT_ACCESS_LEVEL__ = ["RW", "rw", "RO", "ro"]
__SRV_STORAGE_GRANT_ACCESS_LEVEL_RW_UPPER__ = "RW"
__SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_UPPER__ = "RO"
__SRV_STORAGE_GRANT_ACCESS_LEVEL_RW_LOWER__ = "rw"
__SRV_STORAGE_GRANT_ACCESS_LEVEL_RO_LOWER__ = "ro"
__SRV_STORAGE_GRANT_ACCESS_TYPE__ = ["IP", "ip", "CERT", "cert", "USER", "user"]
__SRV_STORAGE_GRANT_ACCESS_TYPE_IP_UPPER__ = "IP"
__SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_UPPER__ = "CERT"
__SRV_STORAGE_GRANT_ACCESS_TYPE_USER_UPPER__ = "USER"
__SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__ = "ip"
__SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__ = "cert"
__SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__ = "user"
__REGEX_SHARE_GRANT_ACCESS_TO_USER__ = "^[A-Za-z0-9;_\`'\-\.\{\}\[\]]{4,32}$"
__REGEX_SHARE_GRANT_ACCESS_TO_CERT__ = "^[a-zA-Z0-9]{1,64}$"
__SRV_AWS_TAGS_RESOURCE_TYPE__ = [
    "customer-gateway",
    "dhcp-options",
    "image",
    "instance",
    "internet-gateway",
    "network-acl",
    "network-interface",
    "reserved-instances",
    "route-table",
    "snapshot",
    "spot-instances-request",
    "subnet",
    "security-group",
    "volume",
    "vpc",
    "vpn-connection",
    "vpn-gateway",
]
__SRV_AWS_TAGS_RESOURCE_TYPE_INSTANCE__ = "instance"
__SRV_MODULE_BASE_PREFIX__ = "nws"
__AGGREGATION_COST_TYPE__ = ["daily", "monthly"]
__SRV_PORTAL_USER_ROLE_TYPE__ = ["portal", "backoffice", "all"]
__SRV_PORTAL_FILTER_SERVICE_OBJECT_TYPE__ = [
    "organization",
    "division",
    "account",
    "catalog",
]
__SRV_METRICTYPE_CONSUME__ = "CONSUME"
__SRV_METRICTYPE_BUNDLE__ = "BUNDLE"
__SRV_METRICTYPE_OPT_BUNDLE__ = "OPT_BUNDLE"
__SRV_METRICTYPE_PROF_SERVICE__ = "PROF_SERVICE"
__SRV_METRICTYPE__ = ["CONSUME", "BUNDLE", "OPT_BUNDLE", "PROF_SERVICE"]
__SRV_REPORT_MODE__ = ["SUMMARY", "COMPLETE"]
__SRV_REPORT_SUMMARY_MODE__ = "SUMMARY"
__SRV_REPORT_COMPLETE_MODE__ = "COMPLETE"
__SRV_DEFAULT_KEYPAIR_TYPE__ = "--DEFAULT--keypair--"
__SRV_DEFAULT_IMAGE_TYPE__ = "--DEFAULT--image"
__SRV_DEFAULT_VPC_TYPE__ = "--DEFAULT--vpc"
__SRV_DEFAULT_TEMPLATE_TYPE__ = "--DEFAULT--template"
__SRV_INSTANCE_TEMPLATE_STATUS__ = [
    "pending",
    "available",
    "invalid",
    "deregistered",
    "transient",
    "failed",
    "error",
]
__SRV_SERVICE_CATEGORY__ = [
    "dummy",
    "cpaas",
    "dbaas",
    "staas",
    "plaas",
    "netaas",
    "laas",
    "maas",
]
__SRV_PLUGIN_CATEGORY__ = [
    "CONTAINER",
    "INSTANCE",
]
__SRV_PLUGIN_TYPE__ = [
    "Dummy",
    "ComputeService",
    "ComputeInstance",
    "ComputeImage",
    "ComputeVPC",
    "ComputeSubnet",
    "ComputeSecurityGroup",
    "ComputeVolume",
    "ComputeKeyPairs",
    "ComputeLimits",
    "ComputeAddress",
    "DatabaseService",
    "DatabaseInstance",
    "DatabaseSchema",
    "DatabaseUser",
    "DatabaseBackup",
    "DatabaseLog",
    "DatabaseSnapshot",
    "DatabaseTag",
    "StorageService",
    "StorageEFS",
    "ComputeTag",
    "AppEngineService",
    "AppEngineInstance",
    "ComputeTemplate",
    "NetworkService",
    "NetworkGateway",
    "NetworkHealthMonitor",
    "NetworkTargetGroup",
    "NetworkLoadBalancer",
    "NetworkSshGateway",
    "VirtualService",
    "ComputeCustomization",
    "LoggingService",
    "LoggingSpace",
    "LoggingInstance",
    "MonitoringService",
    "MonitoringFolder",
    "MonitoringInstance",
]


class ServiceUtil(object):
    @staticmethod
    def instance_api(controller, api_class, model):
        """Get controller apiObject extended class instance from orm model

        :param controller:
        :param plugin_class:
        :param model:
        :return:
        """
        api_list = []

        if model is None:
            api = api_class(controller)
            return api

        if isinstance(model, list):
            for e in model:
                api = api_class(
                    controller,
                    oid=e.id,
                    objid=e.objid,
                    name=e.name,
                    desc=e.desc,
                    active=e.active,
                    model=e,
                )
                api_list.append(api)
            return api_list
        else:
            api = None
            if model is not None:
                api = api_class(
                    controller,
                    oid=model.id,
                    objid=model.objid,
                    name=model.name,
                    desc=model.desc,
                    active=model.active,
                    model=model,
                )
            return api

    @staticmethod
    def get_plugin_instance(controller, plugin_class, model):
        """Get ServiceType plugin instance

        :param controller:
        :param plugin_class:
        :param model:
        :return:
        """
        api = ServiceUtil.instance_api(controller, plugin_class, model)
        return api

    @staticmethod
    def instanceApi(controller, apiClass, entity):
        """
        :DEPRECATED:
        :param controller:
        :param apiClass:
        :param entity:
        :return:
        """
        AssertUtil.assert_is_not_none(apiClass)
        AssertUtil.assert_is_not_none(controller)
        api_list = []

        if entity is None:
            api = apiClass(controller)
            return api

        if isinstance(entity, list):
            for e in entity:
                api = apiClass(
                    controller,
                    oid=e.id,
                    objid=e.objid,
                    name=e.name,
                    desc=e.desc,
                    active=e.active,
                    model=e,
                )
                api_list.append(api)
            return api_list
        else:
            api = None
            if entity is not None:
                api = apiClass(
                    controller,
                    oid=entity.id,
                    objid=entity.objid,
                    name=entity.name,
                    desc=entity.desc,
                    active=entity.active,
                    model=entity,
                )
        return api

    @staticmethod
    def creation_in_progress(instance):
        """check if the creation is in progress

        :return: True the creation is in progress, False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return (instance.status == SrvStatusType.DRAFT and instance.bpmn_process_id is not None) or (
            instance.status == SrvStatusType.PENDING
        )

    @staticmethod
    def start_in_progress(instance):
        """check if the creation is in progress

        :return: True the creation is in progress, False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return instance.model.status == SrvStatusType.STARTING

    @staticmethod
    def is_draft(instance):
        """check if is draft

        :return: True the state is DRAFT and , False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return instance.status == SrvStatusType.DRAFT and not ServiceUtil.creation_in_progress(instance)

    @staticmethod
    def is_created(instance):
        """check if is created

        :return: True the state is DRAFT and , False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return instance.model.status == SrvStatusType.CREATED or instance.model.status == SrvStatusType.ACTIVE

    @staticmethod
    def is_visible(instance):
        """check if is draft

        :return: True the state is DRAFT and , False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return ServiceUtil.check_status(instance, SrvStatusType.ACTIVE) or ServiceUtil.check_status(
            instance, SrvStatusType.STOPPED
        )

    @staticmethod
    def is_active(instance):
        """check if is active

        :return: True the state is ACTIVE,STOPPING,DELETING,STOPPED,UPDATING and , False otherwise.
        :rtype: boolean
        """
        AssertUtil.assert_is_not_none(instance)
        return instance.status in [
            SrvStatusType.ACTIVE,
            SrvStatusType.STOPPING,
            SrvStatusType.DELETING,
            SrvStatusType.STOPPED,
            SrvStatusType.UPDATING,
        ]

    @staticmethod
    def check_status(instance, status):
        AssertUtil.assert_is_not_none(instance)
        AssertUtil.assert_is_not_none(status)
        return instance.status == status
