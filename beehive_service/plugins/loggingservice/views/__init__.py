# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2024 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.loggingservice.controller import ApiLoggingService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    CrudApiObjectResponseSchema,
    ApiManagerError,
    ApiView,
    CrudApiObjectTaskResponseSchema,
)
from beehive_service.controller import ApiServiceType


class DescribeLoggingServiceRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        description="account ID of the instance owner",
    )


class LoggingStateReasonResponseSchema(Schema):
    code = fields.Integer(
        required=False,
        allow_none=True,
        example="",
        description="state code",
        data_key="code",
    )
    message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state message",
        data_key="message",
    )


class LoggingSetResponseSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(required=True, example="2022-01-25T11:20:18Z", description="creation date")
    description = fields.String(required=True)
    state = fields.String(required=False, default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=True)
    template = fields.String(required=True)
    template_name = fields.String(required=True)
    stateReason = fields.Nested(
        LoggingStateReasonResponseSchema,
        many=False,
        required=True,
        description="state description",
    )
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribeLoggingResponseInnerSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    loggingSet = fields.Nested(LoggingSetResponseSchema, many=True, required=False, allow_none=True)
    loggingTotal = fields.Integer(
        required=False,
        example="0",
        descriptiom="total logging",
        data_key="loggingTotal",
    )


class DescribeLoggingServiceResponseSchema(Schema):
    DescribeLoggingResponse = fields.Nested(DescribeLoggingResponseInnerSchema, required=True, many=False)


class DescribeLoggingService(ServiceApiView):
    summary = "Get logging service info"
    description = "Get logging service info"
    tags = ["loggingservice"]
    definitions = {
        "DescribeLoggingServiceRequestSchema": DescribeLoggingServiceRequestSchema,
        "DescribeLoggingServiceResponseSchema": DescribeLoggingServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeLoggingServiceRequestSchema)
    parameters_schema = DescribeLoggingServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeLoggingServiceResponseSchema,
            }
        }
    )
    response_schema = DescribeLoggingServiceResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiLoggingService.plugintype,
        )
        logging_set = [r.aws_info() for r in res]

        res = {
            "DescribeLoggingResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "loggingSet": logging_set,
                "loggingTotal": 1,
            }
        }
        return res


class CreateLoggingServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default="")
    desc = fields.String(required=False, default="")
    service_def_id = fields.String(required=True, example="")
    resource_desc = fields.String(required=False, default="")


class CreateLoggingServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateLoggingServiceApiRequestSchema, context="body")


class CreateLoggingService(ServiceApiView):
    summary = "Create logging service info"
    description = "Create logging service info"
    tags = ["loggingservice"]
    definitions = {
        "CreateLoggingServiceApiRequestSchema": CreateLoggingServiceApiRequestSchema,
        "CrudApiObjectTaskResponseSchema": CrudApiObjectTaskResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateLoggingServiceApiBodyRequestSchema)
    parameters_schema = CreateLoggingServiceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )

    def post(self, controller, data, *args, **kvargs):
        service_definition_id = data.pop("service_def_id")
        account_id = data.pop("owner_id")
        desc = data.pop("desc", "Logging service account %s" % account_id)
        name = data.pop("name")

        self.logger.debug("+++++ CreateLoggingService - post - service_definition_id: %s" % (service_definition_id))
        self.logger.debug("+++++ CreateLoggingService - post - account_id: %s" % (account_id))
        self.logger.debug("+++++ CreateLoggingService - post - name: %s" % (name))

        plugin = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            instance_config=data,
        )

        uuid = plugin.instance.uuid
        self.logger.debug("+++++ CreateLoggingService - post - uuid: %s" % (uuid))

        taskid = getattr(plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class UpdateLoggingServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        description="account ID of the instance owner",
    )
    name = fields.String(required=False, default="")
    desc = fields.String(required=False, default="")
    service_def_id = fields.String(required=False, default="")


class UpdateLoggingServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateLoggingServiceApiRequestParamSchema, context="body")


class UpdateLoggingServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateLoggingServiceApiRequestSchema, context="body")


class UpdateLoggingService(ServiceApiView):
    summary = "Update logging service info"
    description = "Update logging service info"
    tags = ["loggingservice"]
    definitions = {
        "UpdateLoggingServiceApiRequestSchema": UpdateLoggingServiceApiRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateLoggingServiceApiBodyRequestSchema)
    parameters_schema = UpdateLoggingServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, *args, **kvargs):
        data = data.get("serviceinst")

        def_id = data.get("service_def_id", None)
        account_id = data.get("owner_id")

        inst_services, tot = controller.get_paginated_service_instances(
            account_id=account_id,
            plugintype=ApiLoggingService.plugintype,
            filter_expired=False,
        )
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError("Account %s has no logging service associated" % account_id)

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
        description="account ID of the instance owner",
    )


class DescribeAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True, example="")


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
    summary = "Describes attributes of logging service"
    description = "Describes attributes of logging service"
    tags = ["loggingservice"]
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
            plugintype=ApiLoggingService.plugintype,
        )
        if tot > 0:
            api_logging_service: ApiLoggingService = res[0]
            attribute_set = api_logging_service.aws_get_attributes()
        else:
            raise ApiManagerError("Account %s has no logging service associated" % data.get("owner_id"))

        res = {
            "DescribeAccountAttributesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "accountAttributeSet": attribute_set,
            }
        }
        return res


class DeleteLoggingServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description="Instance id")
    taskid = fields.String(required=True, description="task id")


class DeleteLoggingServiceRequestSchema(Schema):
    instanceId = fields.String(
        required=True,
        allow_none=True,
        context="query",
        description="Instance uuid or name",
    )


class DeleteLoggingService(ServiceApiView):
    summary = "Terminate a logging service"
    description = "Terminate a logging service"
    tags = ["loggingservice"]
    definitions = {
        "DeleteLoggingServiceRequestSchema": DeleteLoggingServiceRequestSchema,
        "DeleteLoggingServiceResponseSchema": DeleteLoggingServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteLoggingServiceRequestSchema)
    parameters_schema = DeleteLoggingServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DeleteLoggingServiceResponseSchema}}
    )

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop("instanceId")

        type_plugin: ApiLoggingService = controller.get_service_type_plugin(instance_id, plugin_class=ApiLoggingService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class LoggingServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/loggingservices" % base, "GET", DescribeLoggingService, {}),
            ("%s/loggingservices" % base, "POST", CreateLoggingService, {}),
            ("%s/loggingservices" % base, "PUT", UpdateLoggingService, {}),
            ("%s/loggingservices" % base, "DELETE", DeleteLoggingService, {}),
            (
                "%s/loggingservices/describeaccountattributes" % base,
                "GET",
                DescribeAccountAttributes,
                {},
            ),
            # ('%s/loggingservices/modifyaccountattributes' % base, 'PUT', ModifyAccountAttributes, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
