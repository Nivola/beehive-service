# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import TYPE_CHECKING, List
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    CrudApiObjectResponseSchema,
    ApiManagerError,
    ApiView,
    CrudApiObjectTaskResponseSchema,
)
from beehive.common.data import operation
from beehive_service.entity.service_type import ApiServiceType
from beehive_service.plugins.storageservice.controller import ApiStorageService
from beehive_service.views import ServiceApiView
from beehive_service.views.service_plugin import (
    DescribePluginServiceRequestSchema,
    PluginResponseSchema,
    DescribePluginServiceResponseSchema,
    DescribePluginApiResponseSchema,
    CreatePluginServiceApiRequestSchema,
    CreatePluginServiceApiBodyRequestSchema,
    UpdatePluginServiceApiRequestSchema,
    UpdatePluginServiceApiBodyRequestSchema
)
if TYPE_CHECKING:
    from beehive_service.controller import ServiceController


class DescribeStorageServiceRequestSchema(DescribePluginServiceRequestSchema):
    pass


class DescribeStorageServiceResponseSchema(DescribePluginServiceResponseSchema):
    pluginSet = fields.Nested(PluginResponseSchema, data_key="storageSet", many=True, required=False)
    pluginTotal = fields.Integer(required=False, data_key="storageTotal")


class DescribeStorageApiResponseSchema(DescribePluginApiResponseSchema):
    DescribePluginResponse = fields.Nested(
        DescribeStorageServiceResponseSchema,
        data_key="DescribeStorageResponse",
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeStorageService(ServiceApiView):
    summary = "Get storage service info"
    description = "Get storage service info"
    tags = ["storageservice"]
    definitions = {
        "DescribeStorageServiceRequestSchema": DescribeStorageServiceRequestSchema,
        "DescribeStorageApiResponseSchema": DescribeStorageApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeStorageServiceRequestSchema)
    parameters_schema = DescribeStorageServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeStorageApiResponseSchema,
            }
        }
    )
    response_schema = DescribeStorageApiResponseSchema

    def get(self, controller: 'ServiceController', data, *args, **kvargs):
        # get instances list
        res: List['ApiStorageService']
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiStorageService.plugintype,
        )
        storage_set = [r.aws_info() for r in res]

        res = {
            "DescribeStorageResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "storageSet": storage_set,
                "storageTotal": tot,
            }
        }
        return res


class CreateStorageService(ServiceApiView):
    summary = "Create storage service info"
    description = "Create storage service info"
    tags = ["storageservice"]
    definitions = {
        "CreatePluginServiceApiRequestSchema": CreatePluginServiceApiRequestSchema,
        "CrudApiObjectTaskResponseSchema": CrudApiObjectTaskResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreatePluginServiceApiBodyRequestSchema)
    parameters_schema = CreatePluginServiceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def post(self, controller: 'ServiceController', data, *args, **kvargs):
        service_definition_id = data.pop("service_def_id")
        account_id = data.pop("owner_id")
        desc = data.pop("desc", "Storage service account %s" % account_id)
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


class UpdateStorageService(ServiceApiView):
    summary = "Update storage service info"
    description = "Update storage service info"
    tags = ["storageservice"]
    definitions = {
        "UpdatePluginServiceApiRequestSchema": UpdatePluginServiceApiRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdatePluginServiceApiBodyRequestSchema)
    parameters_schema = UpdatePluginServiceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller: 'ServiceController', data, *args, **kvargs):
        data = data.get("serviceinst")

        def_id = data.get("service_def_id", None)
        account_id = data.get("owner_id")

        inst_services, tot = controller.get_paginated_service_instances(
            account_id=account_id,
            plugintype=ApiStorageService.plugintype,
            filter_expired=False,
        )
        if tot==0:
            raise ApiManagerError(f"Account {account_id} has no storage instance associated")
        if tot > 0:
            # do strict ==0 check?
            inst_service = inst_services[0]

        # get service def
        if def_id is not None:
            plugin_root: 'ApiStorageService' = ApiServiceType(controller).instancePlugin(None, inst=inst_service)
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


# AHMAD NSP-484 -begin
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


# AHMAD NSP-484 -end


class DescribeAccountAttributes(ServiceApiView):
    summary = "Describes attributes of storage service"
    description = "Describes attributes of storage service"
    tags = ["storageservice"]
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
        res: List[ApiStorageService]
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiStorageService.plugintype,
        )
        if tot > 0:
            attribute_set = res[0].aws_get_attributes()
        else:
            raise ApiManagerError(
                "Account %s has no storage instance associated" % data.get("owner_id"),
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
    quotas = fields.Dict(required=True)


class ModifyAccountAttributesBodyRequestSchema(Schema):
    body = fields.Nested(ModifyAccountAttributeBodyRequestSchema, context="body")


class ModifyAccountAttributeSetResponseSchema(Schema):
    uuid = fields.String(required=True)


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
    summary = "Modify attributes of storage service"
    description = "Modify attributes of storage service"
    tags = ["storageservice"]
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
    response_schema = DescribeAccountAttributesResponseSchema

    def put(self, controller, data, *args, **kvargs):
        # get instances list
        res, tot = controller.get_service_type_plugins(
            account_id_list=[data.get("owner_id")],
            plugintype=ApiStorageService.plugintype,
        )
        if tot > 0:
            res[0].set_attributes(data.get("quotas"))
            attribute_set = [{"uuid": res[0].instance.uuid}]
        else:
            raise ApiManagerError(
                "Account %s has no storage instance associated" % data.get("owner_id"),
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


class DeleteStorageServiceResponseSchema(Schema):
    uuid = fields.String(required=True, metadata={"description": "Instance id"})
    taskid = fields.String(required=True, metadata={"description": "task id"})


class DeleteStorageServiceRequestSchema(Schema):
    instanceId = fields.String(
        required=True,
        allow_none=True,
        context="query",
        metadata={"description": "Instance uuid or name"},
    )


class DeleteStorageService(ServiceApiView):
    summary = "Terminate a storage service"
    description = "Terminate a storage service"
    tags = ["storageservice"]
    definitions = {
        "DeleteStorageServiceRequestSchema": DeleteStorageServiceRequestSchema,
        "DeleteStorageServiceResponseSchema": DeleteStorageServiceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteStorageServiceRequestSchema)
    parameters_schema = DeleteStorageServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DeleteStorageServiceResponseSchema}}
    )
    response_schema = DeleteStorageServiceResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop("instanceId")

        type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiStorageService)
        type_plugin.delete()

        uuid = type_plugin.instance.uuid
        taskid = getattr(type_plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 202


class StorageServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, version=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/storageservices" % base, "GET", DescribeStorageService, {}),
            ("%s/storageservices" % base, "POST", CreateStorageService, {}),
            ("%s/storageservices" % base, "PUT", UpdateStorageService, {}),
            ("%s/storageservices" % base, "DELETE", DeleteStorageService, {}),
            (
                "%s/storageservices/describeaccountattributes" % base,
                "GET",
                DescribeAccountAttributes,
                {},
            ),
            (
                "%s/storageservices/modifyaccountattributes" % base,
                "PUT",
                ModifyAccountAttributes,
                {},
            ),
        ]
        ApiView.register_api(module, rules, **kwargs)
