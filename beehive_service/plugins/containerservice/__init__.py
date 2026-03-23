# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive_service.plugins.containerservice.controller_service import ApiContainerService
from beehive_service.plugins.containerservice.controller_namespace import ApiNamespaceInstance
from beehive_service.plugins.containerservice.views import ContainerServiceAPI
from beehive_service.plugins.containerservice.views.namespace import NamespaceInstanceAPI


class ContainerServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [
            ApiContainerService,
            ApiNamespaceInstance,
        ]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [
            ContainerServiceAPI,
            NamespaceInstanceAPI,
        ]
        self.module.set_apis(apis)
