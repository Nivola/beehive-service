# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from beehive_service.plugins.monitoringservice.controller import ApiMonitoringInstance, ApiMonitoringService
from beehive_service.plugins.monitoringservice.controller import ApiMonitoringFolder
from beehive_service.plugins.monitoringservice.views import MonitoringServiceAPI
from beehive_service.plugins.monitoringservice.views.folder import MonitoringFolderServiceAPI
from beehive_service.plugins.monitoringservice.views.monitoring_instance import MonitoringInstanceServiceAPI


class MonitoringServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [
            ApiMonitoringService, 
            ApiMonitoringFolder,
            ApiMonitoringInstance
        ]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [
            MonitoringServiceAPI,
            MonitoringFolderServiceAPI,
            MonitoringInstanceServiceAPI
        ]
        self.module.set_apis(apis)
