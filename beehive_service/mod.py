# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.module.basic.views.status import StatusAPI
from beehive.common.apimanager import ApiModule
from beehive_service.controller import ServiceController
from beehive_service.views.account_v2 import AccountV20API
from beehive_service.views.organization import OrganizationAPI
from beehive_service.views.service_instance_v2 import ServiceInstanceAPI
from beehive_service.views.legacy_service_instance import ServiceInstanceAPI as LegacyServiceInstanceAPI
from beehive_service.views.division import DivisionAPI
from beehive_service.views.capability import AccountCapabilityAPI
from beehive_service.views.account import AccountAPI
from beehive_service.views.service_link import ServiceInstanceLinkAPI
from beehive_service.views.service_tag import ServiceTagAPI
from beehive_service.views.service_type import ServiceTypeAPI
from beehive_service.views.service_definition import ServiceDefinitionAPI
from beehive_service.views.service_catalog import ServiceCatalogAPI
from beehive_service.views.service_process import ServiceProcessAPI
from beehive_service.plugins.view_aws import WrapperAwsAPI
from beehive_service.views.service_price_list import ServicePriceListAPI
from beehive_service.views.service_price_metric import ServicePriceMetricAPI
from beehive_service.views.service_metric import ServiceMetricAPI
from beehive_service.views.service_consume import ServiceConsumeAPI
from beehive_service.views.service_job_schedule import ServiceJobScheduleAPI
from beehive_service.views.service_portal import ServicePortalAPI
from beehive_service.views.account_cost import AccountCostAPI
from beehive_service.views.nivola import NivolaAPI


class ServiceModule(ApiModule):
    """Beehive Service Module
    """
    def __init__(self, api_manager):
        """ """
        self.name = 'ServiceModule'
        self.base_path = 'nws'

        ApiModule.__init__(self, api_manager, self.name)

        self.apis = [
            StatusAPI,
            OrganizationAPI,
            DivisionAPI,
            AccountAPI,
            AccountV20API,
            AccountCapabilityAPI,
            ServiceCatalogAPI,
            ServiceTypeAPI,
            ServiceDefinitionAPI,
            ServiceInstanceAPI,
            LegacyServiceInstanceAPI,
            ServiceProcessAPI,
            ServiceTagAPI,
            ServiceInstanceLinkAPI,
            WrapperAwsAPI,
            ServicePriceListAPI,
            ServicePriceMetricAPI,
            ServiceMetricAPI,
            ServiceConsumeAPI,
            ServiceJobScheduleAPI,
            ServicePortalAPI,
            AccountCostAPI,
            NivolaAPI,


            #questi moduli erano già commentati e non piu esposti
            # WalletAPI,
            # AccountV11API,
            # AgreementAPI,
            # ServicePluginTypeInstanceAPI,
            # ServiceInstCfgAPI,
            # ServiceCostParamAPI,
            # ServiceInstLinkAPI,
            # ServiceDefLinkAPI,
            # ServiceJobAPI,
            # ServiceMetricConsumeViewAPI,
            # DivisionCostAPI,
            # OrganizationCostAPI,
            # NivolaCostAPI
        ]
        self.api_plugins = {}
        self.controller = ServiceController(self)

    def get_controller(self):
        return self.controller

    def set_apis(self, apis):
        self.apis.extend(apis)
        # # self.api_plugins
        # for api in self.apis:
        #     self.logger.debug('Set apis: %s' % get_class_name(api))
