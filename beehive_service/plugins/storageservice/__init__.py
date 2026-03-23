# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import TYPE_CHECKING, List
from beehive_service.plugins.storageservice.controller import (
    ApiStorageService,
    ApiStorageEFS,
)
from beehive_service.plugins.storageservice.views import StorageServiceAPI
from beehive_service.plugins.storageservice.views.efs import StorageEfsServiceAPI
from beehive_service.plugins.storageservice.views.efs_v2 import StorageEfsServiceV2API

if TYPE_CHECKING:
    from beehive_service.entity.service_type import ApiServiceTypeContainer
    from beehive_service.mod import ServiceModule

class StorageServicePlugin(object):

    def __init__(self, module: 'ServiceModule'):
        self.module = module
        self.st_plugins: List['ApiServiceTypeContainer'] = [
            ApiStorageService,
            ApiStorageEFS,
        ]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [StorageServiceAPI, StorageEfsServiceAPI, StorageEfsServiceV2API]
        self.module.set_apis(apis)
