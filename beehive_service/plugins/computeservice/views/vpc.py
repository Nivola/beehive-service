# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 Regione Piemonte


from beehive.common.apimanager import ApiView
from beehive_service_netaas.networkservice.views.vpc import CreateVpc, DescribeVpcs


class DescribeVpcs10(DescribeVpcs):
    pass


class CreateVpc10(CreateVpc):
    pass


class ComputeVpcAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/computeservices/vpc"
        rules = [
            ("%s/describevpcs" % base, "GET", DescribeVpcs10, {}),
            ("%s/createvpc" % base, "POST", CreateVpc10, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
