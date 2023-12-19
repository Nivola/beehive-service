# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive_service.entity.service_type import (
    ApiServiceTypeContainer,
    ApiServiceType,
    ApiServiceTypePlugin,
    AsyncApiServiceTypePlugin,
)


class ApiDummySTContainer(ApiServiceTypeContainer):
    plugintype = "DummyService"
    objuri = "dummystcontainer"
    objname = "dummystcontainer"
    objdesc = "DummySTContainer"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypeContainer.__init__(self, *args, **kvargs)

        self.child_classes = [ApiDummySTChild]

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypeContainer.info(self)
        return info

    # def get_flagContainer(self):
    #     return True
    #
    # def getResourceInfo(self, instance):
    #     """
    #     """
    #     return super(ApiDummySTContainer, self).getResourceInfo(instance)
    #
    # def createResourceInstance(self, instance):
    #     self.logger.warn('RES _________1________________________  ')
    #     data = self.prepareResourceAddParams(
    #         instance, 'beehive_resource.plugins.dummy.controller.DummySyncResource', res_type='resDummy')
    #     res = self.controller.api_client.admin_request('resource', '/v1.0/nrs/entities', 'post', data=data,
    #                                                    other_headers=None)
    #
    #     return res.get('uuid'), None
    #
    # def get_service_types_children(self):
    #     pass
    #
    # def updateResource(self, instance, *args, **kwargs):
    #     # TODO updateResource: management data resource to update
    #     data = {
    #         'resource': kwargs
    #     }
    #     res = self.controller.api_client.admin_request('resource',
    #                                                    '/v1.0/nrs/entities/%s' % instance.resource_uuid,
    #                                                    'put', data=data
    #                                                    )
    #     return res
    #
    # def deleteResource(self, instance, *args, **kwargs):
    #     res = self.controller.api_client.admin_request('resource',
    #                                                    '/v1.0/nrs/entities/%s' % instance.resource_uuid,
    #                                                    'delete'
    #                                                    )
    #     return res
    #
    # def listResource(self, instance, *args, **kwargs):
    #     # TODO listResource: management data to filter resource
    #     data = {
    #         'uuid': instance.resource_uuid,
    #     }
    #     res = self.controller.api_client.admin_request('resource',
    #                                                    '/v1.0/nrs/entities',
    #                                                    'get', data=data
    #                                                    )
    #     # TODO listResource: management data resource to return
    #     return res


# class ApiDummySTContainerCamunda(ApiDummySTContainer):
#     #     objdef = 'DummySTContainer'
#     objuri = 'dummystcontainercamunda'
#     objname = 'dummystcontainercamunda'
#     objdesc = 'DummySTContainerCamunda'
#
#     def __init__(self, *args, **kvargs):
#         """ """
#         ApiDummySTContainer.__init__(self, *args, **kvargs)
#
#         self.flag_async = True
#         self.child_classes = [
#             ApiDummySTChild
#         ]
#
#     def createResourceInstance(self, instance):
#         data = self.prepareResourceAddParams(instance, 'beehive_resource.plugins.dummy.controller.DummySyncResource',
#                                              res_type='resDummy')
#
#         process_key = 'dummy_resource'
#         # TODO call camunda da fare
#         process_id = self.camunda_engine.process_instance_start_processkey(self, process_key, variables=data)
#
#         upd_data = {'bpmn_process_id': process_id}
#
#         instance.update(**upd_data)
#
#         self.logger.info('Resource ApiDummySTChild asynchronous...! %s' % process_id)
#
#         return None, process_id


class ApiDummySTChild(ApiServiceTypePlugin):
    plugintype = "DummyServiceSyncChild"
    objuri = "dummystchild"
    objname = "dummystchild"
    objdesc = "DummySTChild"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.resourceInfo = None

        self.child_classes = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({"resourceInfo": "resourceInfo DummySTChild default value"})
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    # def execCMD(self, oid):
    #     self.logger.info('exec cmd on %s' % oid)
    #
    # def getResourceInfo(self, instance):
    #     """
    #
    #     """
    #     self.logger.warning('ApiDummySTChild.getResourceInfo START')
    #     resource_info = self.controller.api_client.admin_request('resource',
    #                                                              '/v1.0/nrs/entities/%s' % instance.resource_uuid,
    #                                                              'get')
    #     info = {
    #         'service_info': instance.detail(),
    #         'resource_info': resource_info
    #     }
    #     self.logger.warning('ApiDummySTChild.getResourceInfo END info=%s' % info)
    #     return info
    #
    # def createResourceInstance(self, instance):
    #     self.logger.info('createResourceInstance of ApiDummySTChild  ...')
    #     data = self.prepareResourceAddParams(instance, 'beehive_resource.plugins.dummy.controller.DummySyncResource')
    #
    #     res = self.controller.api_client.admin_request('resource', '/v1.0/nrs/entities', 'post', data=data,
    #                                                    other_headers=None)
    #     self.logger.info('Resource ApiDummySTChild created! %s' % res)
    #     return res.get('uuid'), None
    #
    # def transformParamResource(self, oid):
    #     self.logger.info('transformParamResource of ApiDummySTChild')
    #
    # def updateResource(self, instance, *args, **kwargs):
    #     data = {
    #         'resource': kwargs
    #     }
    #     res = self.controller.api_client.admin_request('resource',
    #                                                    '/v1.0/nrs/entities/%s' % instance.resource_uuid,
    #                                                    'put', data=data
    #                                                    )
    #     return res
    #
    # def deleteResource(self, instance, *args, **kwargs):
    #     data = {'uuid': instance.resource_uuid}
    #     res = self.controller.api_client.admin_request('resource',
    #                                                    '/v1.0/nrs/entities/%s' % instance.resource_uuid,
    #                                                    'delete', data=data
    #                                                    )
    #     return res


class ApiDummySTAsyncChild(AsyncApiServiceTypePlugin):
    plugintype = "DummyServiceAsyncChild"
    objuri = "dummystchild"
    objname = "dummystchild"
    objdesc = "DummySTAsyncChild"

    def __init__(self, *args, **kvargs):
        """ """

        ApiDummySTChild.__init__(self, *args, **kvargs)
        self.resourceInfo = None

        self.child_classes = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({"resourceInfo": "resourceInfo DummySTAsyncChild"})
        return info

    # def execCMD(self, oid):
    #     self.logger.info('exec cmd on %s' % oid)
    #
    # def createResourceInstance(self, instance):
    #     self.logger.info('createResourceInstance of ApiDummySTChild  ...')
    #
    #     data = self.prepareResourceAddParams(instance,
    #                                          'beehive_resource.plugins.dummy.controller.DummyAsyncResource')
    #
    #     res = self.controller.api_client.admin_request(
    #         'resource', '/v1.0/nrs/entities', 'post', data=data,
    #         other_headers=None)
    #
    #     self.logger.info('Resource ApiDummySTChild asynchronous...! %s' % res['uuid'])
    #
    #     # self.wait_resource(res['uuid'], delta=1)
    #     self.wait_job(res, '', delta=1, maxtime=180)
    #     self.logger.info('... created! %s' % res)
    #
    #     return res.get('uuid'), None
    #
    # def transformParamResource(self, oid):
    #     self.logger.info('transformParamResource of ApiDummySTChildAsync')


# class ApiDummySTCamundaChild(ApiDummySTChild):
#     #     objdef = 'DummySTContainer.DummySTChild'
#     objuri = 'dummystchild'
#     objname = 'dummystchild'
#     objdesc = 'DummySTCamundaChild'
#
#     def __init__(self, *args, **kvargs):
#         """ """
#
#         ApiDummySTChild.__init__(self, *args, **kvargs)
#         self.resourceInfo = None
#         self.flag_async = True
#
#         self.child_classes = [
#         ]
#
#     def info(self):
#         """Get object info
#
#         :return: Dictionary with object info.
#         :rtype: dict
#         :raises ApiManagerError: raise :class:`.ApiManagerError`
#         """
#         info = ApiServiceType.info(self)
#         info.update({
#             'resourceInfo': 'resourceInfo DummySTCamundaChild'
#         })
#         return info
#
#     def execCMD(self, oid):
#         self.logger.info('exec cmd on %s' % oid)
#
#     def createResourceInstance(self, instance):
#         self.logger.info('createResourceInstance of DummySTCamundaChild  ...')
#
#         data = self.prepareResourceAddParams(instance,
#                                              'beehive_resource.plugins.dummy.controller.DummyAsyncResource')
#
#         # Find process_key
#         process_key = self.get_bpmn_process_key(instance, ApiServiceType.PROCESS_KEY_CREATION)
#
#         try:
#             res = self.camunda_engine.process_instance_start_processkey(process_key, variables=data)
#             self.logger.debug('Call Camunda call: %s' % res)
#             process_id = res.get('id')
#
#             upd_data = {'bpmn_process_id': process_id}
#
#             instance.update(**upd_data)
#
#             self.logger.debug('Resource ApiDummySTChild asynchronous...! %s' % process_id)
#         except RemoteException as ex:
#             self.logger.warn('Resource ApiDummySTChild asynchronous...! %s' % str(ex))
#             raise ApiManagerWarning(ex)
#         return None, process_id
#
#     def transformParamResource(self, oid):
#         self.logger.info('transformParamResource of ApiDummySTCamundaChild')
