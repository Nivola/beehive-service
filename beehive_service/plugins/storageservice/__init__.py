# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive_service.plugins.storageservice.controller import ApiStorageService, ApiStorageEFS
from beehive_service.plugins.storageservice.views import StorageServiceAPI
from beehive_service.plugins.storageservice.views.efs import StorageEfsServiceAPI


class StorageServicePlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [ApiStorageService, ApiStorageEFS]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = [
            StorageServiceAPI,
            StorageEfsServiceAPI
        ]
        self.module.set_apis(apis)
