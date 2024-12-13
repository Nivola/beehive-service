# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from flasgger import fields, Schema
from beehive.common.data import operation
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.databaseservice import ApiDatabaseService
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


class DescribeDatabaseServiceRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        description="account ID of the instance owner",
    )


class StateReasonResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, description="reason code for the state change")
    message = fields.String(required=False, allow_none=True, description="message for the state change")


class DatabaseSetSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(required=False, allow_none=True, description="date creation")
    description = fields.String(required=False)
    state = fields.String(required=False, default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=False)
    template = fields.String(required=True)
    template_name = fields.String(required=False)
    stateReason = fields.Nested(
        StateReasonResponseSchema,
        many=False,
        required=False,
        allow_none=False,
        description="array of status reason",
    )
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribeDatabaseResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, description="request id")
    databaseSet = fields.Nested(DatabaseSetSchema, required=False, many=True, allow_none=True)
    databaseTotal = fields.Integer(required=False)


class DescribeDatabaseServiceResponseSchema(Schema):
    DescribeDatabaseResponse = fields.Nested(
        DescribeDatabaseResponseSchema, required=True, many=False, allow_none=False
    )


class DescribeDatabaseService(ServiceApiView):
    summary = "Get database service info"
    description = "Get database service info"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDatabaseServiceRequestSchema": DescribeDatabaseServiceRequestSchema,
        "DescribeDatabaseServiceResponseSchema": DescribeDatabaseServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDatabaseServiceRequestSchema)
    parameters_schema = DescribeDatabaseServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDatabaseServiceResponseSchema,
            }
        }
    )
    response_schema = DescribeDatabaseServiceResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiDatabaseService.plugintype,
        )
        database_set = [r.aws_info() for r in res]

        res = {
            "DescribeDatabaseResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "databaseSet": database_set,
                "databaseTotal": 1,
            }
        }
        return res


class CreateDatabaseServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, default="")
    desc = fields.String(required=False, default="")
    service_def_id = fields.String(required=True, example="")
    resource_desc = fields.String(required=False, default="")


class CreateDatabaseServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateDatabaseServiceApiRequestSchema, context="body")


class CreateDatabaseService(ServiceApiView):
    summary = "Create database service info"
    description = "Create database service info"
    tags = ["databaseservice"]
    definitions = {
        "CreateDatabaseServiceApiRequestSchema": CreateDatabaseServiceApiRequestSchema,
        "CrudApiObjectTaskResponseSchema": CrudApiObjectTaskResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDatabaseServiceApiBodyRequestSchema)
    parameters_schema = CreateDatabaseServiceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kvargs) -> dict:
        service_definition_id = data.pop("service_def_id")
        account_id = data.pop("owner_id")
        desc = data.pop("desc", "Database service account %s" % account_id)
        name = data.pop("name")

        plugin = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            instance_config=data,
        )

        uuid = plugin.instance.uuid
        taskid = getattr(plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class UpdateDatabaseServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        description="account ID of the instance owner",
    )
    # params_resource = fields.String(required=False, default='{}')
    name = fields.String(required=False, default="")
    desc = fields.String(required=False, default="")
    service_def_id = fields.String(required=False, default="")


class UpdateDatabaseServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateDatabaseServiceApiRequestParamSchema, context="body")


class UpdateDatabaseServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateDatabaseServiceApiRequestSchema, context="body")


class UpdateDatabaseService(ServiceApiView):
    summary = "Update database service info"
    description = "Update database service info"
    tags = ["databaseservice"]
    definitions = {
        "UpdateDatabaseServiceApiRequestSchema": UpdateDatabaseServiceApiRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateDatabaseServiceApiBodyRequestSchema)
    parameters_schema = UpdateDatabaseServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, *args, **kvargs):
        data = data.get("serviceinst")

        def_id = data.get("service_def_id", None)
        account_id = data.get("owner_id")

        inst_services, tot = controller.get_paginated_service_instances(
            account_id=account_id,
            plugintype=ApiDatabaseService.plugintype,
            filter_expired=False,
        )
        if tot > 0:
            inst_service = inst_services[0]
        else:
            raise ApiManagerError("Account %s has no database instance associated" % account_id)

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


# AHMAD NSP-484 -begin
class DescribeAccountAttributeDBSItemResponseSchema(Schema):
    attributeValue = fields.Integer(required=False)
    nvlAttributeUsed = fields.Integer(required=False, data_key="nvl-attributeUsed")


class DescribeAccountAttributeDBSValueSetResponseSchema(Schema):
    item = fields.Nested(DescribeAccountAttributeDBSItemResponseSchema, required=False, many=False)


class DescribeAccountAttributeSetDBSResponseSchema(Schema):
    attributeName = fields.String(required=False)
    nvlAttributeUnit = fields.String(required=False, data_key="nvl-attributeUnit")
    attributeValueSet = fields.Nested(DescribeAccountAttributeDBSValueSetResponseSchema, many=True)


class DescribeAccountAttributeDBSResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(DescribeAccountAttributeSetDBSResponseSchema, many=True, required=True)


class DescribeAccountAttributesDBSResponseSchema(Schema):
    DescribeAccountAttributesResponse = fields.Nested(DescribeAccountAttributeDBSResponseSchema, many=False)


# AHMAD NSP-484 -end


class DescribeAccountAttributes(ServiceApiView):
    summary = "Describes attributes of database service"
    description = "Describes attributes of database service"
    tags = ["databaseservice"]
    definitions = {
        "DescribeAccountAttributesRequestSchema": DescribeAccountAttributesRequestSchema,
        "DescribeAccountAttributesDBSResponseSchema": DescribeAccountAttributesDBSResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAccountAttributesRequestSchema)
    parameters_schema = DescribeAccountAttributesRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeAccountAttributesDBSResponseSchema,
            }
        }
    )
    response_schema = DescribeAccountAttributesDBSResponseSchema

    def get(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiDatabaseService.plugintype,
        )
        if tot > 0:
            attribute_set = res[0].aws_get_attributes()
        else:
            raise ApiManagerError(
                "Account %s has no database instance associated" % data.get("owner_id"),
                code=404,
            )

        res = {
            "DescribeAccountAttributesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "accountAttributeSet": attribute_set,
            }
        }
        return res


class ModifyAccountAttributeBodyRequestSchema(Schema):
    owner_id = fields.String(required=True)
    quotas = fields.Dict(required=True, example="")


class ModifyAccountAttributesBodyRequestSchema(Schema):
    body = fields.Nested(ModifyAccountAttributeBodyRequestSchema, context="body")


class ModifyAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True, example="")


class ModifyAccountAttributeResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    accountAttributeSet = fields.Nested(ModifyAccountAttributeSetResponseSchema, many=True, required=True)


class ModifyAccountAttributesResponseSchema(Schema):
    ModifyAccountAttributesResponse = fields.Nested(
        ModifyAccountAttributeResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class ModifyAccountAttributes(ServiceApiView):
    summary = "Modify attributes of database service"
    description = "Modify attributes of database service"
    tags = ["databaseservice"]
    definitions = {
        "ModifyAccountAttributeBodyRequestSchema": ModifyAccountAttributeBodyRequestSchema,
        "ModifyAccountAttributesResponseSchema": ModifyAccountAttributesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ModifyAccountAttributesBodyRequestSchema)
    parameters_schema = ModifyAccountAttributeBodyRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeAccountAttributesResponseSchema,
            }
        }
    )
    response_schema = ModifyAccountAttributesResponseSchema

    def put(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiDatabaseService.plugintype,
        )
        if tot > 0:
            res[0].set_attributes(data.get("quotas"))
            attribute_set = [{"uuid": res[0].instance.uuid}]
        else:
            raise ApiManagerError(
                "Account %s has no database instance associated" % data.get("owner_id"),
                code=404,
            )

        res = {
            "ModifyAccountAttributesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "": attribute_set,
            }
        }
        return res


class DeleteDatabaseServiceResponseSchema(Schema):
    uuid = fields.String(required=True, description="Instance id")
    taskid = fields.String(required=True, description="task id")


class DeleteDatabaseServiceRequestSchema(Schema):
    instanceId = fields.String(
        required=True,
        allow_none=True,
        context="query",
        description="Instance uuid or name",
    )


class DeleteDatabaseService(ServiceApiView):
    summary = "Terminate a database service"
    description = "Terminate a database service"
    tags = ["databaseservice"]
    definitions = {
        "DeleteDatabaseServiceRequestSchema": DeleteDatabaseServiceRequestSchema,
        "DeleteDatabaseServiceResponseSchema": DeleteDatabaseServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteDatabaseServiceRequestSchema)
    parameters_schema = DeleteDatabaseServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": DeleteDatabaseServiceResponseSchema}}
    )
    response_schema = DeleteDatabaseServiceResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop("instanceId")

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiDatabaseService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class DatabaseServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/databaseservices" % base, "GET", DescribeDatabaseService, {}),
            ("%s/databaseservices" % base, "POST", CreateDatabaseService, {}),
            ("%s/databaseservices" % base, "PUT", UpdateDatabaseService, {}),
            ("%s/databaseservices" % base, "DELETE", DeleteDatabaseService, {}),
            (
                "%s/databaseservices/describeaccountattributes" % base,
                "GET",
                DescribeAccountAttributes,
                {},
            ),
            (
                "%s/databaseservices/modifyaccountattributes" % base,
                "PUT",
                ModifyAccountAttributes,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
