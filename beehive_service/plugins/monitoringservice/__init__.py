# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.plugins.monitoringservice.controller import (
    ApiMonitoringInstance,
    ApiMonitoringService,
    ApiMonitoringFolder,
)
from beehive_service.plugins.monitoringservice.controller_alert import ApiMonitoringAlert
from beehive_service.plugins.monitoringservice.views import MonitoringServiceAPI
from beehive_service.plugins.monitoringservice.views.folder import (
    MonitoringFolderServiceAPI,
)
from beehive_service.plugins.monitoringservice.views.alert import MonitoringAlertServiceAPI
from beehive_service.plugins.monitoringservice.views.monitoring_instance import (
    MonitoringInstanceServiceAPI,
)


class MonitoringServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [
            ApiMonitoringService,
            ApiMonitoringFolder,
            ApiMonitoringInstance,
            ApiMonitoringAlert,
        ]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [
            MonitoringServiceAPI,
            MonitoringFolderServiceAPI,
            MonitoringInstanceServiceAPI,
            MonitoringAlertServiceAPI,
        ]
        self.module.set_apis(apis)
