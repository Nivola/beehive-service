# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive_service.plugins.loggingservice.controller import (
    ApiLoggingInstance,
    ApiLoggingService,
)
from beehive_service.plugins.loggingservice.controller import ApiLoggingSpace
from beehive_service.plugins.loggingservice.views import LoggingServiceAPI
from beehive_service.plugins.loggingservice.views.space import LoggingSpaceServiceAPI
from beehive_service.plugins.loggingservice.views.logging_instance import (
    LoggingInstanceServiceAPI,
)


class LoggingServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [ApiLoggingService, ApiLoggingSpace, ApiLoggingInstance]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [LoggingServiceAPI, LoggingSpaceServiceAPI, LoggingInstanceServiceAPI]
        self.module.set_apis(apis)
