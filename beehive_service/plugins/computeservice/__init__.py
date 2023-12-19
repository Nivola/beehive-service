# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from .controller import ApiComputeService
from beehive_service.plugins.computeservice.views import ComputeServiceAPI
from beehive_service.plugins.computeservice.views.image import ComputeImageAPI
from beehive_service.plugins.computeservice.views.keypair import ComputeKeyPairAPI
from beehive_service.plugins.computeservice.views.securitygroup import (
    ComputeSecurityGroupAPI,
)
from beehive_service.plugins.computeservice.views.subnet import ComputeSubnetAPI
from beehive_service.plugins.computeservice.views.instance import ComputeInstanceAPI
from beehive_service.plugins.computeservice.views.vpc import ComputeVpcAPI
from beehive_service.plugins.computeservice.views.tag import ComputeTagAPI
from beehive_service.plugins.computeservice.views.volume import ComputeVolumeAPI
from beehive_service.plugins.computeservice.views.volume_v2 import ComputeVolumeV20API
from beehive_service.plugins.computeservice.views.customization import (
    ComputeCustomizationAPI,
)
from beehive_service.plugins.computeservice.views.instance_v2 import (
    ComputeInstanceV2API,
)
from .views.instance_backup import ComputeInstanceBackupAPI


class ComputeServicePlugin(object):
    def __init__(self, module):
        self.module = module

    def init(self):
        service = ApiComputeService(self.module.get_controller())
        service.init_object()

    def register(self):
        apis = [
            ComputeServiceAPI,
            ComputeImageAPI,
            ComputeInstanceAPI,
            ComputeInstanceV2API,
            ComputeInstanceBackupAPI,
            ComputeVpcAPI,
            ComputeTagAPI,
            ComputeKeyPairAPI,
            ComputeSecurityGroupAPI,
            ComputeSubnetAPI,
            ComputeVolumeAPI,
            ComputeVolumeV20API,
            ComputeCustomizationAPI,
        ]
        self.module.set_apis(apis)
