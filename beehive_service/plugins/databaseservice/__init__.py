# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.plugins.databaseservice.controller import (
    ApiDatabaseServiceInstance,
    ApiDatabaseService,
)
from beehive_service.plugins.databaseservice.views import DatabaseServiceAPI
from beehive_service.plugins.databaseservice.views.instance import DatabaseInstanceAPI
from beehive_service.plugins.databaseservice.views.instance_v2 import (
    DatabaseInstanceV2API,
)


class DatabaseServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [ApiDatabaseService, ApiDatabaseServiceInstance]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [
            DatabaseServiceAPI,
            DatabaseInstanceAPI,
            DatabaseInstanceV2API,
        ]
        self.module.set_apis(apis)
