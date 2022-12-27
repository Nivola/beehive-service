# # SPDX-License-Identifier: EUPL-1.2
# #
# (C) Copyright 2018-2022 CSI-Piemonte
# TODO delete this file
# TODO delete this file
# non usato nel plugin
# from beehive.common.apimanager import ApiView
# from beehive_service.plugins.computeservice.views import CreateComputeService, DescribeComputeService, \
#     UpdateComputeService
# from beehive_service.plugins.computeservice.views.subnet import DescribeSubnets, CreateSubnet
# from beehive_service.plugins.computeservice.views.tag import DescribeTags, CreateTags, DeleteTags
# from beehive_service.plugins.computeservice.views.image import DescribeImages, CreateImage
# from beehive_service.plugins.computeservice.views.keypair import DescribeKeyPairs, ImportKeyPair, CreateKeyPair, \
#     DeleteKeyPair
# from beehive_service.plugins.computeservice.views.vpc import DescribeVpcs, CreateVpc
# from beehive_service.plugins.computeservice.views.securitygroup import DescribeSecurityGroups, \
#     CreateSecurityGroup, DeleteSecurityGroup, AuthorizeSecurityGroupIngress, \
#     AuthorizeSecurityGroupEgress, RevokeSecurityGroupIngress, RevokeSecurityGroupEgress, PatchSecurityGroup
#
#
# class ComputeServiceAPI(ApiView):
#     @staticmethod
#     def register_api(module):
#         base = u'nws'
#         rules = [
#             # image
#             (u'%s/computeservices/image/describeimages' % base, u'GET', DescribeImages, {}),
#             (u'%s/computeservices/image/createimage' % base, u'POST', CreateImage, {}),
#
#             # keypair
#             (u'%s/computeservices/keypair/describekeypairs' % base, u'GET', DescribeKeyPairs, {}),
#             (u'%s/computeservices/keypair/importkeypair' % base, u'GET', ImportKeyPair, {}),
#             (u'%s/computeservices/keypair/createkeypair' % base, u'GET', CreateKeyPair, {}),
#             (u'%s/computeservices/keypair/deletekeypair' % base, u'GET', DeleteKeyPair, {}),
#
#             # secutitygroup
#             (u'%s/computeservices/securitygroup/deletesecuritygroup' % base, u'DELETE', DeleteSecurityGroup, {}),
#             (u'%s/computeservices/securitygroup/createsecuritygroup' % base, u'POST', CreateSecurityGroup, {}),
#             (u'%s/computeservices/securitygroup/patchsecuritygroup' % base, u'PATCH', PatchSecurityGroup, {}),
#             (u'%s/computeservices/securitygroup/describesecuritygroups' % base, u'GET', DescribeSecurityGroups, {}),
#             (u'%s/computeservices/securitygroup/authorizesecuritygroupingress' % base, u'POST',
#              AuthorizeSecurityGroupIngress, {}),
#             (u'%s/computeservices/securitygroup/authorizesecuritygroupegress' % base, u'POST',
#              AuthorizeSecurityGroupEgress, {}),
#             (u'%s/computeservices/securitygroup/revokesecuritygroupingress' % base, u'DELETE',
#              RevokeSecurityGroupIngress, {}),
#             (u'%s/computeservices/securitygroup/revokesecuritygroupegress' % base, u'DELETE',
#              RevokeSecurityGroupEgress, {}),
#
#             # subnet
#             (u'%s/computeservices/subnet/describesubnets' % base, u'GET', DescribeSubnets, {}),
#             (u'%s/computeservices/subnet/createsubnet' % base, u'POST', CreateSubnet, {}),
#         ]
#
#         ApiView.register_api(module, rules)
