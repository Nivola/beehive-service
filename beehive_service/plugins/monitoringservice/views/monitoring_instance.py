# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte

import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from six import ensure_text
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.plugins.computeservice.controller import (
    ApiComputeService,
    ApiComputeInstance,
)
from beehive_service.views import NotEmptyString, ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiManagerError,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    PaginatedRequestQuerySchema,
    ApiView,
    ApiManagerWarning,
)
from beehive_service.plugins.monitoringservice.controller import (
    ApiMonitoringService,
    ApiMonitoringInstance,
)
from beehive.common.data import operation
from beecell.types.type_string import validate_string


class CreateMonitoringInstanceApiParamRequestSchema(Schema):
    ComputeInstanceId = fields.String(required=True, description="compute instance id")
    owner_id = fields.String(
        required=True,
        example="1",
        data_key="owner-id",
        description="account id or uuid associated to compute zone",
    )
    InstanceType = NotEmptyString(required=False, description="service definition of the instance")
    norescreate = fields.Boolean(required=False, allow_none=True, description="don't create physical resource")


class CreateMonitoringInstanceApiRequestSchema(Schema):
    instance = fields.Nested(CreateMonitoringInstanceApiParamRequestSchema, context="body")


class CreateMonitoringInstanceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateMonitoringInstanceApiRequestSchema, context="body")


class CreateMonitoringInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class CreateMonitoringInstanceApiResponseSchema(Schema):
    CreateMonitoringInstanceResponse = fields.Nested(
        CreateMonitoringInstanceApiResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateMonitoringInstance(ServiceApiView):
    summary = "Create monitoring instance"
    description = "Create monitoring instance"
    tags = ["monitoringservice"]
    definitions = {
        "CreateMonitoringInstanceApiResponseSchema": CreateMonitoringInstanceApiResponseSchema,
        "CreateMonitoringInstanceApiRequestSchema": CreateMonitoringInstanceApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateMonitoringInstanceApiBodyRequestSchema)
    parameters_schema = CreateMonitoringInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": CreateMonitoringInstanceApiResponseSchema,
            }
        }
    )
    response_schema = CreateMonitoringInstanceApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        inner_data = data.get("instance")
        service_definition_id = inner_data.get("InstanceType", None)
        account_id = inner_data.get("owner_id")
        compute_instance_id = inner_data.get("ComputeInstanceId")
        norescreate = inner_data.get("norescreate")

        # check account
        account: ApiAccount
        parent_plugin: ApiMonitoringService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiMonitoringService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # check compute instance
        compute_service_instance = controller.check_service_instance(
            compute_instance_id, ApiComputeInstance, account=account.oid
        )
        data["ComputeInstanceId"] = compute_service_instance.uuid

        # fix compute instance name
        name_instance: str = ""
        for element in compute_service_instance.name:
            if validate_string(element, validation_string=r"[^a-zA-Z0-9\-]") is False:  # without dot!
                name_instance += "-"
            else:
                name_instance += element

        name = "MonitoringInstance-%s" % name_instance
        desc = "MonitoringInstance of %s" % compute_service_instance.name

        data["norescreate"] = norescreate

        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiMonitoringInstance.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)

        plugin: ApiMonitoringInstance
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
            name_max_length=60,
        )

        res = {
            "CreateMonitoringInstanceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceId": plugin.instance.uuid,
                "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class DeleteMonitoringInstanceApiRequestSchema(Schema):
    InstanceId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
        context="query",
    )


class DeleteMonitoringInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceId = fields.String(
        required=False,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class DeleteMonitoringInstanceApiResponseSchema(Schema):
    DeleteInstanceResponse = fields.Nested(DeleteMonitoringInstanceApiResponse1Schema, required=True, allow_none=False)


class DeleteMonitoringInstance(ServiceApiView):
    summary = "Delete monitoring instance"
    description = "Delete monitoring instance"
    tags = ["monitoringservice"]
    definitions = {
        "DeleteMonitoringInstanceApiRequestSchema": DeleteMonitoringInstanceApiRequestSchema,
        "DeleteMonitoringInstanceApiResponseSchema": DeleteMonitoringInstanceApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteMonitoringInstanceApiRequestSchema)
    parameters_schema = DeleteMonitoringInstanceApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "no response",
                "schema": DeleteMonitoringInstanceApiResponseSchema,
            }
        }
    )
    response_schema = DeleteMonitoringInstanceApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.get("InstanceId")
        type_plugin: ApiMonitoringInstance
        type_plugin = controller.get_service_type_plugin(instance_id)
        if isinstance(type_plugin, ApiMonitoringInstance):
            type_plugin.delete()
        else:
            raise ApiManagerError("Instance is not a MonitoringInstance")

        res = {
            "DeleteInstanceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceId": type_plugin.instance.uuid,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        self.logger.debug("DeleteMonitoringInstance delete - end")
        return res, 202


class MonitoringInstanceStateReasonResponseSchema(Schema):
    nvl_code = fields.Integer(required=False, allow_none=True, description="state code", data_key="nvl-code")
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state message",
        data_key="nvl-message",
    )


class MonitoringInstanceItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="id of the instance",
    )
    name = fields.String(required=True, example="test", description="name of the instance")
    creationDate = fields.DateTime(required=True, example="2022-01-25T11:20:18Z", description="creation date")
    description = fields.String(required=True, example="test", description="description of the instance")
    ownerId = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="account id of the owner of the instance",
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        example="test",
        description="account name of the owner of the instance",
    )
    state = fields.String(
        required=True,
        example="available",
        description="state of the instance",
        data_key="state",
    )
    stateReason = fields.Nested(
        MonitoringInstanceStateReasonResponseSchema,
        many=False,
        required=True,
        description="state description",
    )
    computeInstanceId = fields.String(required=False, allow_none=True)
    modules = fields.Dict(required=False, default={}, allow_none=True)


class DescribeMonitoringInstances1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceInfo = fields.Nested(
        MonitoringInstanceItemParameterResponseSchema,
        many=True,
        required=False,
    )
    nvl_instanceTotal = fields.Integer(
        required=False,
        example="0",
        descriptiom="total monitoring instance",
        data_key="nvl-instanceTotal",
    )


class DescribeMonitoringInstancesResponseSchema(Schema):
    DescribeMonitoringInstancesResponse = fields.Nested(
        DescribeMonitoringInstances1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeMonitoringInstancesRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account id",
    )
    InstanceName = fields.String(required=False, description="monitoring instance name", context="query")
    instance_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-id.N",
        description="list of monitoring instance id",
    )
    MaxItems = fields.Integer(
        required=False,
        missing=100,
        validation=Range(min=1),
        context="query",
        description="max number elements to return in the response",
    )
    Marker = fields.String(
        required=False,
        missing="0",
        example="",
        description="pagination token",
        context="query",
    )


class DescribeMonitoringInstances(ServiceApiView):
    summary = "Describe monitoring"
    description = "Describe monitoring"
    tags = ["monitoringservice"]
    definitions = {
        "DescribeMonitoringInstancesRequestSchema": DescribeMonitoringInstancesRequestSchema,
        "DescribeMonitoringInstancesResponseSchema": DescribeMonitoringInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeMonitoringInstancesRequestSchema)
    parameters_schema = DescribeMonitoringInstancesRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeMonitoringInstancesResponseSchema,
            }
        }
    )
    response_schema = DescribeMonitoringInstancesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        self.logger.debug("DescribeMonitoringInstances get - begin")
        monitoring_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        account_id_list = data.get("owner_id_N", [])
        instance_id_list = data.get("instance_id_N", [])
        instance_name_list = data.get("InstanceName", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            service_id_list=monitoring_id_list,
            account_id_list=account_id_list,
            plugintype=ApiMonitoringInstance.plugintype,
            **data_search,
        )

        instances_set = []
        for r in res:
            r: ApiMonitoringInstance
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = "0"
        else:
            next_token = str(data_search["page"] + 1)

        res = {
            "DescribeMonitoringInstancesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "next_token": next_token,
                "instanceInfo": instances_set,
                "nvl-instanceTotal": total,
            }
        }
        return res


class MonitoringInstanceServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, version=None, **kwargs):
        base = module.base_path + "/monitoringservices"
        rules = [
            ("%s/instance/createinstance" % base, "POST", CreateMonitoringInstance, {}),
            (
                "%s/instance/deleteteinstance" % base,
                "DELETE",
                DeleteMonitoringInstance,
                {},
            ),
            (
                "%s/instance/describeinstances" % base,
                "GET",
                DescribeMonitoringInstances,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
