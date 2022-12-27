# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 Regione Piemonte

from beehive.common.apimanager import ApiView
from beehive_service_netaas.networkservice.views.securitygroup import AuthorizeSecurityGroupEgress, AuthorizeSecurityGroupIngress, CreateSecurityGroup, DeleteSecurityGroup, DescribeSecurityGroups, PatchSecurityGroup, RevokeSecurityGroupEgress, RevokeSecurityGroupIngress


class DeleteSecurityGroup10(DeleteSecurityGroup):
    pass
class CreateSecurityGroup10(CreateSecurityGroup):
    pass
class PatchSecurityGroup10(PatchSecurityGroup):
    pass
class DescribeSecurityGroups10(DescribeSecurityGroups):
    pass

class AuthorizeSecurityGroupIngress10(AuthorizeSecurityGroupIngress):
    pass
class AuthorizeSecurityGroupEgress10(AuthorizeSecurityGroupEgress):
    pass
class RevokeSecurityGroupIngress10(RevokeSecurityGroupIngress):
    pass
class RevokeSecurityGroupEgress10(RevokeSecurityGroupEgress):
    pass

class ComputeSecurityGroupAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/computeservices/securitygroup/deletesecuritygroup' % base, 'DELETE', DeleteSecurityGroup10, {}),
            ('%s/computeservices/securitygroup/createsecuritygroup' % base, 'POST', CreateSecurityGroup10, {}),
            ('%s/computeservices/securitygroup/patchsecuritygroup' % base, 'PATCH', PatchSecurityGroup10, {}),
            ('%s/computeservices/securitygroup/describesecuritygroups' % base, 'GET', DescribeSecurityGroups10, {}),
            ('%s/computeservices/securitygroup/authorizesecuritygroupingress' % base, 'POST',
             AuthorizeSecurityGroupIngress10, {}),
            ('%s/computeservices/securitygroup/authorizesecuritygroupegress' % base, 'POST',
             AuthorizeSecurityGroupEgress10, {}),
            ('%s/computeservices/securitygroup/revokesecuritygroupingress' % base, 'DELETE',
             RevokeSecurityGroupIngress10, {}),
            ('%s/computeservices/securitygroup/revokesecuritygroupegress' % base, 'DELETE',
             RevokeSecurityGroupEgress10, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
