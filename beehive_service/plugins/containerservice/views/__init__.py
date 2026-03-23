# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.containerservice.controller_service import ApiContainerService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    CrudApiObjectResponseSchema,
    ApiManagerError,
    ApiView,
    CrudApiObjectTaskResponseSchema,
)
from beehive_service.controller import ApiServiceType, ServiceController


class DescribeContainerServiceRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        metadata={"description": "account ID of the instance owner"},
    )


class ContainerStateReasonResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, data_key="code", metadata={"description": "state code"})
    message = fields.String(
        required=False,
        allow_none=True,
        data_key="message",
        metadata={"description": "state message"},
    )


class ContainerSetResponseSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(
        required=True,
        metadata={"example": "2022-01-25T11:20:18Z", "description": "creation date"},
    )
    description = fields.String(required=True)
    state = fields.String(required=False, dump_default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=True)
    template = fields.String(required=True)
    template_name = fields.String(required=True)
    stateReason = fields.Nested(
        ContainerStateReasonResponseSchema,
        many=False,
        required=True,
        metadata={"description": "state description"},
    )
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribeContainerResponseInnerSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    containerSet = fields.Nested(ContainerSetResponseSchema, many=True, required=False, allow_none=True)
    containerTotal = fields.Integer(
        required=False,
        data_key="containerTotal",
        metadata={"example": "0", "description": "total container"},
    )


class DescribeContainerServiceResponseSchema(Schema):
    DescribeContainerResponse = fields.Nested(DescribeContainerResponseInnerSchema, required=True, many=False)


class DescribeContainerService(ServiceApiView):
    summary = "Get container service info"
    description = "Get container service info"
    tags = ["containerservice"]
    definitions = {
        "DescribeContainerServiceRequestSchema": DescribeContainerServiceRequestSchema,
        "DescribeContainerServiceResponseSchema": DescribeContainerServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeContainerServiceRequestSchema)
    parameters_schema = DescribeContainerServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeContainerServiceResponseSchema,
            }
        }
    )
    response_schema = DescribeContainerServiceResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiContainerService.plugintype,
        )
        container_set = [r.aws_info() for r in res]

        res = {
            "DescribeContainerResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "containerSet": container_set,
                "containerTotal": 1,
            }
        }
        return res


class CreateContainerServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, dump_default="")
    desc = fields.String(required=False, dump_default="")
    service_def_id = fields.String(required=True)
    resource_desc = fields.String(required=False, dump_default="")


class CreateContainerServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateContainerServiceApiRequestSchema, context="body")


class CreateContainerService(ServiceApiView):
    summary = "Create container service info"
    description = "Create container service info"
    tags = ["containerservice"]
    definitions = {
        "CreateContainerServiceApiRequestSchema": CreateContainerServiceApiRequestSchema,
        "CrudApiObjectTaskResponseSchema": CrudApiObjectTaskResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateContainerServiceApiBodyRequestSchema)
    parameters_schema = CreateContainerServiceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )

    def post(self, controller: ServiceController, data, *args, **kvargs):
        service_definition_id = data.pop("service_def_id")
        account_id = data.pop("owner_id")
        desc = data.pop("desc", "Container service account %s" % account_id)
        name = data.pop("name")

        self.logger.debug("+++++ CreateContainerService - post - service_definition_id: %s" % (service_definition_id))
        self.logger.debug("+++++ CreateContainerService - post - account_id: %s" % (account_id))
        self.logger.debug("+++++ CreateContainerService - post - name: %s" % (name))

        plugin = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            instance_config=data,
        )

        uuid = plugin.instance.uuid
        self.logger.debug("+++++ CreateContainerService - post - uuid: %s" % (uuid))

        taskid = getattr(plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class UpdateContainerServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        metadata={"description": "account ID of the instance owner"},
    )
    name = fields.String(required=False, dump_default="")
    desc = fields.String(required=False, dump_default="")
    service_def_id = fields.String(required=False, dump_default="")


class UpdateContainerServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateContainerServiceApiRequestParamSchema, context="body")


class UpdateContainerServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateContainerServiceApiRequestSchema, context="body")


class UpdateContainerService(ServiceApiView):
    summary = "Update container service info"
    description = "Update container service info"
    tags = ["containerservice"]
    definitions = {
        "UpdateContainerServiceApiRequestSchema": UpdateContainerServiceApiRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateContainerServiceApiBodyRequestSchema)
    parameters_schema = UpdateContainerServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, *args, **kvargs):
        data = data.get("serviceinst")

        def_id = data.get("service_def_id", None)
        account_id = data.get("owner_id")

        inst_services, tot = controller.get_paginated_service_instances(
            account_id=account_id,
            plugintype=ApiContainerService.plugintype,
            filter_expired=False,
        )
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError("Account %s has no container service associated" % account_id)

        # get service def
        if def_id is not None:
            plugin_root = ApiServiceType(controller).instancePlugin(None, inst=inst_service)
            plugin_root.change_definition(inst_service, def_id)

        return {"uuid": inst_service.uuid}


class DescribeAccountAttributesRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        metadata={"description": "account ID of the instance owner"},
    )


class DescribeAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True)


class DescribeAccountAttributeResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetResponseSchema, many=True, required=True)


class DescribeAccountAttributesResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(
        DescribeAccountAttributeResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeAccountAttributeSSItemResponseSchema(Schema):
    attributeValue = fields.Integer(required=False)
    nvlAttributeUsed = fields.Integer(required=False, data_key="nvl-attributeUsed")


class DescribeAccountAttributeSSValueSetResponseSchema(Schema):
    item = fields.Nested(DescribeAccountAttributeSSItemResponseSchema, required=False, many=False)


class DescribeAccountAttributeSetSSResponseSchema(Schema):
    attributeName = fields.String(required=False)
    nvlAttributeUnit = fields.String(required=False, data_key="nvl-attributeUnit")
    attributeValueSet = fields.Nested(DescribeAccountAttributeSSValueSetResponseSchema, many=True)


class DescribeAccountAttributeSSResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetSSResponseSchema, many=True, required=True)


class DescribeAccountAttributesSSResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeSSResponseSchema, many=False)


class DescribeAccountAttributes(ServiceApiView):
    summary = "Describes attributes of container service"
    description = "Describes attributes of container service"
    tags = ["containerservice"]
    definitions = {
        "DescribeAccountAttributesRequestSchema": DescribeAccountAttributesRequestSchema,
        "DescribeAccountAttributesSSResponseSchema": DescribeAccountAttributesSSResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAccountAttributesRequestSchema)
    parameters_schema = DescribeAccountAttributesRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeAccountAttributesSSResponseSchema,
            }
        }
    )
    response_schema = DescribeAccountAttributesSSResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiContainerService.plugintype,
        )
        if tot > 0:
            api_container_service: ApiContainerService = res[0]
            attribute_set = api_container_service.aws_get_attributes()
        else:
            raise ApiManagerError("Account %s has no container service associated" % data.get("owner_id"))

        res = {
            "DescribeAccountAttributesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "accountAttributeSet": attribute_set,
            }
        }
        return res


class DeleteContainerServiceResponseSchema(Schema):
    uuid = fields.String(required=True, metadata={"description": "Instance id"})
    taskid = fields.String(required=True, metadata={"description": "task id"})


class DeleteContainerServiceRequestSchema(Schema):
    instanceId = fields.String(
        required=True,
        allow_none=True,
        context="query",
        metadata={"description": "Instance uuid or name"},
    )


class DeleteContainerService(ServiceApiView):
    summary = "Terminate a container service"
    description = "Terminate a container service"
    tags = ["containerservice"]
    definitions = {
        "DeleteContainerServiceRequestSchema": DeleteContainerServiceRequestSchema,
        "DeleteContainerServiceResponseSchema": DeleteContainerServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteContainerServiceRequestSchema)
    parameters_schema = DeleteContainerServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DeleteContainerServiceResponseSchema,
            }
        }
    )

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop("instanceId")

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiContainerService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


# class DescribeAvailabilityZonesRequestSchema(Schema):
#     owner_id = fields.String(
#         required=True,
#         allow_none=False,
#         context="query",
#         data_key="owner-id",
#         description="account ID of the instance owner",
#     )


# class AvailabilityZoneMessageResponseSchema(Schema):
#     message = fields.String(
#         required=False,
#         allow_none=True,
#         description="message about the Availability Zone",
#     )


# class DescribeAvailabilityZonesItemResponseSchema(Schema):
#     zoneName = fields.String(required=False, allow_none=True, description="name of the Availability Zone")
#     zoneState = fields.String(required=False, allow_none=True, description="state of the Availability Zone")
#     regionName = fields.String(required=False, allow_none=True, description="name of the region")
#     messageSet = fields.Nested(
#         AvailabilityZoneMessageResponseSchema,
#         required=False,
#         many=True,
#         allow_none=False,
#     )


# class DescribeAvailabilityZonesApi1ResponseSchema(Schema):
#     requestId = fields.String(required=True)
#     availabilityZoneInfo = fields.Nested(
#         DescribeAvailabilityZonesItemResponseSchema,
#         required=True,
#         many=True,
#         allow_none=False,
#     )
#     xmlns = fields.String(required=False, data_key="__xmlns")


# class DescribeAvailabilityZonesResponseSchema(Schema):
#     DescribeAvailabilityZonesResponse = fields.Nested(
#         DescribeAvailabilityZonesApi1ResponseSchema,
#         required=True,
#         many=False,
#         allow_none=False,
#     )


# class DescribeAvailabilityZonesResponse(ServiceApiView):
#     summary = "Describes zone and region attribute for compute service"
#     description = "Describes zone and region attribute for compute service"
#     tags = ["computeservice"]
#     definitions = {
#         "DescribeAvailabilityZonesRequestSchema": DescribeAvailabilityZonesRequestSchema,
#         "DescribeAvailabilityZonesResponseSchema": DescribeAvailabilityZonesResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(DescribeAvailabilityZonesRequestSchema)
#     parameters_schema = DescribeAvailabilityZonesRequestSchema
#     responses = SwaggerApiView.setResponses(
#         {
#             200: {
#                 "description": "success",
#                 "schema": DescribeAvailabilityZonesResponseSchema,
#             }
#         }
#     )
#     response_schema = DescribeAvailabilityZonesResponseSchema

#     def get(self, controller, data, *args, **kvargs):
#         # get instances list
#         res, tot = controller.get_service_type_plugins(
#             account_id_list=[data.get("owner_id")],
#             plugintype=ApiContainerService.plugintype,
#         )
#         if tot > 0:
#             avzs = res[0].aws_get_availability_zones()
#         else:
#             raise ApiManagerError(
#                 "Account %s has no compute instance associated" % data.get("owner_id"),
#                 code=404,
#             )

#         res = {
#             "DescribeAvailabilityZonesResponse": {
#                 "__xmlns": self.xmlns,
#                 "requestId": operation.id,
#                 "availabilityZoneInfo": avzs,
#             }
#         }
#         return res


class ContainerServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/containerservices" % base, "GET", DescribeContainerService, {}),
            ("%s/containerservices" % base, "POST", CreateContainerService, {}),
            ("%s/containerservices" % base, "PUT", UpdateContainerService, {}),
            ("%s/containerservices" % base, "DELETE", DeleteContainerService, {}),
            (
                "%s/containerservices/describeaccountattributes" % base,
                "GET",
                DescribeAccountAttributes,
                {},
            ),
            # (
            #     "%s/containerservices/describeavailabilityzones" % base,
            #     "GET",
            #     DescribeAvailabilityZonesResponse,
            #     {},
            # ),
        ]

        ApiView.register_api(module, rules, **kwargs)
