# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive_service.plugins.appengineservice.views import AppengineServiceAPI
from beehive_service.plugins.appengineservice.controller import (
    ApiAppEngineService,
    ApiAppEngineInstance,
)
from beehive_service.plugins.appengineservice.views.instance import AppEngineInstanceAPI
from beehive_service.mod import ServiceModule


class AppEngineServicePlugin(object):
    def __init__(self, module: ServiceModule):
        self.module = module
        self.st_plugins = [ApiAppEngineService, ApiAppEngineInstance]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [AppengineServiceAPI, AppEngineInstanceAPI]
        self.module.set_apis(apis)
