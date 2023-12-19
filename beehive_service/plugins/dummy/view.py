# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    CrudApiObjectResponseSchema,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    ApiManagerWarning,
    PaginatedRequestQuerySchema,
)
from flasgger import fields, Schema
from beehive_service.views.service_type import (
    ListServiceType,
    CreateServiceType,
    GetServiceType,
)
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectResponseSchema,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
)

from beecell.swagger import SwaggerHelper
from beehive_service.views.service_instance import (
    UpdateServiceInstance,
    DeleteServiceInstance,
    GetServiceInstance,
)
from beehive_service.plugins.dummy.controller import ApiDummySTChild


###################################
#   Service Type Container Dummy
###################################
class InfoSTContainer(GetServiceInstance):
    """ """

    tags = ["servicedummy"]


## create
class CreateSTContainerDummyParamRequestSchema(Schema):
    pass


class CreateSTContainerDummyRequestSchema(Schema):
    servicetype = fields.Nested(CreateSTContainerDummyParamRequestSchema, context="body")


class CreateSTContainerDummyBodyRequestSchema(Schema):
    body = fields.Nested(CreateSTContainerDummyRequestSchema, context="body")


class CreateSTContainerDummy(CreateServiceType):
    """ """

    tags = ["servicedummy"]
    #     definitions = {
    #         'CreateSTContainerDummyRequestSchema': CreateSTContainerDummyRequestSchema,
    #         'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    #     }
    #     parameters = SwaggerHelper().get_parameters(CreateSTContainerDummyBodyRequestSchema)
    #     parameters_schema = CreateSTContainerDummyRequestSchema
    #     responses = ServiceApiView.setResponses({
    #         201: {
    #             'description': 'success',
    #             'schema': CrudApiObjectResponseSchema
    #         }
    #     })

    def getObjClass(self):
        self.logger.debug("CreateSTContainerDummy getObjClass")
        return "beehive_service.plugins.dummy.controller.ApiDummySTContainer"


#     def post(self, controller, data, *args, **kwargs):
# #         resp = controller.add_service_type(**data.get('servicetype'))
#         resp = None
#         return ({'uuid':resp}, 201)


class ListSTChildrenRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    pass


class ListSTChildrenParamsResponseSchema(ApiServiceObjectResponseSchema):
    status = fields.String(required=False, allow_none=True)
    objclass = fields.String(required=True, allow_none=False)
    flag_container = fields.Boolean(required=True, allow_none=False)


class ListSTChildrenResponseSchema(Schema):
    servicetype = fields.Nested(ListSTChildrenParamsResponseSchema, required=True)


class ListSTChildrenDummy(ServiceApiView):
    """ """

    tags = ["servicedummy"]
    definitions = {
        "ListSTChildrenResponseSchema": ListSTChildrenResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = ListSTChildrenRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListSTChildrenResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        """ """
        plugin_container = self.instancePlugin(oid)
        if plugin_container.flag_container is True:
            return (plugin_container.getResourceInfo(plugin_container.oid), 200)
        else:
            ## generare una Exception per Warning
            raise ApiManagerWarning(
                "The entity %s is not a container instance [oid: %s] " % (plugin_container.name, plugin_container.id)
            )


class UpdateSTDummyContainer(UpdateServiceInstance):
    """ """

    tags = ["servicedummy"]


class DeleteSTDummyContainer(DeleteServiceInstance):
    """ """

    tags = ["servicedummy"]


###################################
#   Service Type Child Dummy
###################################
class CreateSTChildDummy(CreateServiceType):
    tags = ["servicedummy"]

    def getObjClass(self):
        return "beehive_service.plugins.dummy.controller.ApiDummySTChild"


class InfoSTChildDummy(GetServiceInstance):
    tags = ["servicedummy"]


class UpdateChildDummy(UpdateServiceInstance):
    tags = ["servicedummy"]


class DeleteChildDummy(DeleteServiceInstance):
    tags = ["servicedummy"]


## cmd
class ExecuteCMDSyncDummyParamRequestSchema(Schema):
    param = fields.String(required=False, allow_none=True)


class ExecuteCMDSyncDummyRequestSchema(Schema):
    servicedummy = fields.Nested(ExecuteCMDSyncDummyParamRequestSchema)


class ExecuteCMDSyncDummyBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(ExecuteCMDSyncDummyRequestSchema, context="body")


class ExecuteCMDSyncDummy(ServiceApiView):
    tags = ["servicedummy"]
    definitions = {
        "ExecuteCMDSyncDummyRequestSchema": ExecuteCMDSyncDummyRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ExecuteCMDSyncDummyBodyRequestSchema)
    parameters_schema = ExecuteCMDSyncDummyRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        data = data.get("servicedummy")
        plugin_ch = ApiDummySTChild(controller).instancePlugin(oid)
        resp = None
        if isinstance(plugin_ch, ApiDummySTChild):
            resp = plugin_ch.execCMD(oid)
        else:
            raise ApiManagerWarning("Method not allowed <execCMD>!")

        return ({"uuid": resp}, 200)


class ExecuteCMDAsyncDummy(ServiceApiView):
    tags = ["servicedummy"]


class DummySTPlugin(ApiView):
    """DummySTPlugin"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/dummystcontainer/<oid>" % base, "GET", InfoSTContainer, {}),
            ("%s/dummystcontainer" % base, "POST", CreateSTContainerDummy, {}),
            ("%s/dummystcontainer/<oid>/list" % base, "GET", ListSTChildrenDummy, {}),
            ("%s/dummystcontainer/<oid>" % base, "PUT", UpdateSTDummyContainer, {}),
            ("%s/dummystcontainer/<oid>" % base, "DELETE", DeleteSTDummyContainer, {}),
            ("%s/dummystchild/<oid>" % base, "GET", InfoSTChildDummy, {}),
            ("%s/dummystchild" % base, "POST", CreateSTChildDummy, {}),
            ("%s/dummystchild/<oid>" % base, "PUT", UpdateChildDummy, {}),
            ("%s/dummystchild/<oid>" % base, "DELETE", DeleteChildDummy, {}),
            ("%s/dummystchild/<oid>/cmd" % base, "PUT", ExecuteCMDSyncDummy, {}),
            (
                "%s/dummystchild/<oid>/asinc/cmd" % base,
                "POST",
                ExecuteCMDAsyncDummy,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
