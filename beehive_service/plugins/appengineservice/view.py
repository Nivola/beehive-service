# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
# TODO Delete this file
# deprecato sono attualmetee caricati beehive_service.plugins.appengineservice.views.AppengineServiceAPI
# e beehive_service.plugins.appengineservice.views.instance.AppEngineInstanceAPI


# from beehive.common.apimanager import ApiView
# from beehive_service.plugins.appengineservice.views import CreateAppengineService
# from beehive_service.plugins.appengineservice.views.instance import DescribeAppInstances, RunInstances, StartInstances, \
#     StopInstances, TerminateInstances
#
# class AppEngineServiceAPI(ApiView):
#     @staticmethod
#     def register_api(module,rules=None, version=None):
#         base = u'nws'
#         rules = [
#             # main service
#             (u'%s/appengineservices' % base, u'POST', CreateAppengineService, {}),
#
#             # instance
#             (u'%s/appengineservices/instance/describeinstances' % base, u'GET', DescribeInstances, {}),
#             (u'%s/appengineservices/instance/runinstances' % base, u'POST', RunInstances, {}),
#             (u'%s/appengineservices/instance/startinstances' % base, u'GET', StartInstances, {}),
#             (u'%s/appengineservices/instance/stopinstances' % base, u'GET', StopInstances, {}),
#             (u'%s/appengineservices/instance/terminateinstances' % base, u'DELETE', TerminateInstances, {}),
#         ]
#
#         ApiView.register_api(module, rules)
