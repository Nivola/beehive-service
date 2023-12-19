# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 Regione Piemonte


from beehive.common.apimanager import ApiView
from beehive_service_netaas.networkservice.views.subnet import (
    CreateSubnet,
    DescribeSubnets,
)


class DescribeSubnets10(DescribeSubnets):
    pass


class CreateSubnet10(CreateSubnet):
    pass


class ComputeSubnetAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            (
                "%s/computeservices/subnet/describesubnets" % base,
                "GET",
                DescribeSubnets10,
                {},
            ),
            (
                "%s/computeservices/subnet/createsubnet" % base,
                "POST",
                CreateSubnet10,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
