# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

# from .view import DummySTPlugin
from .controller import ApiDummySTContainer


class DummyPlugin(object):
    def __init__(self, module):
        self.module = module
        self.st_plugins = [ApiDummySTContainer]

    def init(self):
        for srv in self.st_plugins:
            service = srv(self.module.get_controller())
            service.init_object()

    def register(self):
        apis = []
        self.module.set_apis(apis)
