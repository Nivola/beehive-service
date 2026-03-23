# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
# from beecell.util import ensure_text
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.model import Division, Organization
from beehive_service.plugins.computeservice.controller import ApiComputeService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiManagerError,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    PaginatedRequestQuerySchema,
    ApiView,
    ApiManagerWarning,
)
from beehive_service.plugins.loggingservice.controller import (
    ApiLoggingService,
    ApiLoggingSpace,
)
from beehive.common.assert_util import AssertUtil
from beehive_service.service_util import (
    __SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__,
    __SRV_STORAGE_PERFORMANCE_MODE__,
    __SRV_AWS_STORAGE_STATUS__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE__,
    __SRV_STORAGE_GRANT_ACCESS_LEVEL__,
    __REGEX_SHARE_GRANT_ACCESS_TO_USER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__,
)
from ipaddress import IPv4Address, AddressValueError
from beehive.common.data import operation


class CreateSpaceApiParamRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        data_key="owner-id",
        metadata={"example": "1", "description": "account id or uuid associated to compute zone"},
    )
    Name = fields.String(required=False, load_default=None, metadata={"example": "test", "description": "space name"})
    AdditionalInfo = fields.String(
        required=False,
        load_default=None,
        metadata={"example": "test", "description": "space description"},
    )
    definition = fields.String(
        required=False,
        metadata={"example": "logging.space.xxx", "description": "service definition of the space"},
    )
    norescreate = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "don't create physical resource of the space"},
    )


class CreateSpaceApiRequestSchema(Schema):
    space = fields.Nested(CreateSpaceApiParamRequestSchema, context="body")


class CreateSpaceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateSpaceApiRequestSchema, context="body")


class CreateSpaceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    spaceId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "space id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
    )


class CreateSpaceApiResponseSchema(Schema):
    CreateSpaceResponse = fields.Nested(CreateSpaceApiResponse1Schema, required=True, many=False, allow_none=False)


class CreateSpace(ServiceApiView):
    summary = "Create logging space"
    description = "Create logging space"
    tags = ["loggingservice"]
    definitions = {
        "CreateSpaceApiResponseSchema": CreateSpaceApiResponseSchema,
        "CreateSpaceApiRequestSchema": CreateSpaceApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateSpaceApiBodyRequestSchema)
    parameters_schema = CreateSpaceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CreateSpaceApiResponseSchema}})
    response_schema = CreateSpaceApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        self.logger.debug("CreateSpace post - begin")
        inner_data = data.get("space")

        service_definition_id = inner_data.get("definition")  # es. logging.space.default2
        account_id = inner_data.get("owner_id")
        name = inner_data.get("Name", None)
        desc = inner_data.get("AdditionalInfo", None)

        # check account
        account: ApiAccount
        parent_plugin: ApiLoggingService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiLoggingService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        # self.logger.debug('CreateSpace - triplet: %s' % triplet)

        if name is None:
            name = "DefaultSpace"
            desc = triplet

        data.update({"triplet": triplet})

        if service_definition_id is None:
            # self.logger.debug('CreateSpace - ApiLoggingSpace.plugintype: %s' % ApiLoggingSpace.plugintype)
            service_definition = controller.get_default_service_def(ApiLoggingSpace.plugintype)
        else:
            # self.logger.debug('CreateSpace - service_definition_id: %s' % service_definition_id)
            service_definition = controller.get_service_def(service_definition_id)
        self.logger.debug("CreateSpace - service_definition: %s" % service_definition)

        plugin: ApiLoggingSpace
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        res = {
            "CreateSpaceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "spaceId": plugin.instance.uuid,
                "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class DeleteSpaceApiRequestSchema(Schema):
    SpaceId = fields.String(
        required=False,
        context="query",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "space id"},
    )


class DeleteSpaceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, metadata={"description": "operation id"})
    spaceId = fields.String(
        required=False,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "space id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
    )


class DeleteSpaceApiResponseSchema(Schema):
    DeleteSpaceResponse = fields.Nested(DeleteSpaceApiResponse1Schema, required=True, many=False, allow_none=False)


class DeleteSpace(ServiceApiView):
    summary = "Delete logging space"
    description = "Delete logging space"
    tags = ["loggingservice"]
    definitions = {
        "DeleteSpaceApiRequestSchema": DeleteSpaceApiRequestSchema,
        "DeleteSpaceApiResponseSchema": DeleteSpaceApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteSpaceApiRequestSchema)
    parameters_schema = DeleteSpaceApiRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "no response", "schema": DeleteSpaceApiResponseSchema}}
    )
    response_schema = DeleteSpaceApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        space_id = data.get("SpaceId")
        type_plugin: ApiLoggingSpace
        type_plugin = controller.get_service_type_plugin(space_id)

        if isinstance(type_plugin, ApiLoggingSpace):
            type_plugin.delete()
        else:
            raise ApiManagerError("Instance is not a LoggingSpace")

        self.logger.debug("+++++ DeleteSpace delete - type_plugin: %s" % type(type_plugin))

        res = {
            "DeleteSpaceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "spaceId": type_plugin.instance.uuid,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class LoggingSpaceStateReasonResponseSchema(Schema):
    nvl_code = fields.Integer(
        required=False,
        allow_none=True,
        data_key="nvl-code",
        metadata={"description": "state code"},
    )
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-message",
        metadata={"description": "state message"},
    )


class LoggingSpaceEndpointResponseSchema(Schema):
    home = fields.String(
        required=True,
        metadata={"example": "https://localhost/s/prova/app/home#/", "description": "space home endpoint"},
    )
    discover = fields.String(
        required=True,
        metadata={"example": "https://localhost/s/prova/app/discover#/", "description": "space discover view endpoint"},
    )


class LoggingSpaceDashboardResponseSchema(Schema):
    dashboardId = fields.String(
        required=True,
        metadata={"example": "c6772ba4-0fc2-493b-86a3-6edf717cb2ff", "description": "id of the dashboard"},
    )
    dashboardTitle = fields.String(
        required=True,
        metadata={"example": "[Filebeat MySQL] Overview ECS", "description": "name of the dashboard"},
    )
    dashboardVersion = fields.String(
        required=True,
        metadata={"example": "WzE3Mjk0MTksMTRd", "description": "dashboard version"},
    )
    dashboardScore = fields.Int(required=True, metadata={"example": 1, "description": "dashboard score"})
    modificationDate = fields.String(
        required=True,
        metadata={"example": "2022-01-25T10:21:26.772Z", "description": "dashboard modification date"},
    )
    endpoint = fields.String(
        required=True,
        metadata={"description": "space dashboard endpoint", "example": "https://localhost/s/prova/app/dashboards#/view/dusnawiu7cnsdiu"},
    )


class LoggingSpaceItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "id of the space"},
    )
    name = fields.String(required=True, metadata={"example": "test", "description": "name of the space"})
    creationDate = fields.DateTime(
        required=True,
        metadata={"example": "2022-01-25T11:20:18Z", "description": "creation date"},
    )
    description = fields.String(required=True, metadata={"example": "test", "description": "description of the space"})
    ownerId = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "account id of the owner of the space"},
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        metadata={"example": "test", "description": "account name of the owner of the space"},
    )
    state = fields.String(
        required=True,
        data_key="state",
        metadata={"example": "available", "description": "state of the space"},
    )
    stateReason = fields.Nested(
        LoggingSpaceStateReasonResponseSchema,
        many=False,
        required=True,
        metadata={"description": "state description"},
    )
    templateId = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "id of the space template"},
    )
    templateName = fields.String(
        required=True,
        metadata={"example": "test", "description": "name of the space template"},
    )
    endpoints = fields.Nested(LoggingSpaceEndpointResponseSchema, many=False, required=True)
    dashboards = fields.Nested(LoggingSpaceDashboardResponseSchema, many=True, required=True)


class DescribeLoggingSpaces1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True, allow_none=True)
    spaceInfo = fields.Nested(LoggingSpaceItemParameterResponseSchema, many=True, required=False, allow_none=True)

    spaceTotal = fields.Integer(
        required=False,
        data_key="spaceTotal",
        metadata={"example": "0", "description": "total logging instance"},
    )


class DescribeSpacesResponseSchema(Schema):
    DescribeSpacesResponse = fields.Nested(DescribeLoggingSpaces1ResponseSchema, required=True, many=False)


class DescribeSpacesRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account id"},
    )

    SpaceName = fields.String(required=False, context="query", metadata={"description": "space name"})

    space_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="space-id.N",
        metadata={"description": "list of space id"},
    )

    MaxItems = fields.Integer(
        required=False,
        load_default=100,
        validation=Range(min=1),
        context="query",
        metadata={"description": "max number elements to return in the response"},
    )

    Marker = fields.String(
        required=False,
        load_default="0",
        context="query",
        metadata={"description": "pagination token"},
    )


class DescribeSpaces(ServiceApiView):
    summary = "Describe logging space"
    description = "Describe logging space"
    tags = ["loggingservice"]
    definitions = {
        "DescribeSpacesRequestSchema": DescribeSpacesRequestSchema,
        "DescribeSpacesResponseSchema": DescribeSpacesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeSpacesRequestSchema)
    parameters_schema = DescribeSpacesRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": DescribeSpacesResponseSchema}})
    response_schema = DescribeSpacesResponseSchema

    def get(self, controller, data, *args, **kwargs):
        logging_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        # check Account
        # account_id_list, zone_list = self.get_account_list(controller, data, ApiLoggingService)
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("space_id_N", [])
        self.logger.debug("DescribeSpaces get - instance_id_list: %s" % instance_id_list)

        # get instance name
        instance_name_list = data.get("SpaceName", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]
        self.logger.debug("DescribeSpaces get - instance_name_list: %s" % instance_name_list)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            service_id_list=logging_id_list,
            account_id_list=account_id_list,
            plugintype=ApiLoggingSpace.plugintype,
            **data_search,
        )
        instances_set = []
        for r in res:
            r: ApiLoggingSpace
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = "0"
        else:
            next_token = str(data_search["page"] + 1)

        res = {
            "DescribeSpacesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "next_token": next_token,
                "spaceInfo": instances_set,
                "spaceTotal": total,
            }
        }
        return res


class SyncUsersSpaceApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    Return = fields.Boolean(required=True, allow_none=False, data_key="return", metadata={"example": True})
    requestId = fields.String(required=True, allow_none=True)
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        metadata={"description": "active task id"},
    )


class SyncUsersSpaceApiResponseSchema(Schema):
    SyncSpaceUsersResponse = fields.Nested(
        SyncUsersSpaceApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class SyncUsersSpaceApiRequestSchema(Schema):
    SpaceId = fields.String(required=False, context="query", metadata={"description": "logging space id"})


class SyncUsersSpaceApiBodyRequestSchema(Schema):
    body = fields.Nested(SyncUsersSpaceApiRequestSchema, context="body")


class SyncUsersSpace(ServiceApiView):
    summary = "Syncronize users in a kibana space"
    description = "Syncronize users in a kibana space"
    tags = ["loggingservice"]
    definitions = {
        "SyncUsersSpaceApiRequestSchema": SyncUsersSpaceApiRequestSchema,
        "SyncUsersSpaceApiResponseSchema": SyncUsersSpaceApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(SyncUsersSpaceApiBodyRequestSchema)
    parameters_schema = SyncUsersSpaceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": SyncUsersSpaceApiResponseSchema}}
    )
    response_schema = SyncUsersSpaceApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        oid = data.get("SpaceId")
        type_plugin: ApiLoggingSpace = controller.get_service_type_plugin(oid, plugin_class=ApiLoggingSpace)
        return_value = type_plugin.sync_users()

        res = {
            "SyncSpaceUsersResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class DescribeSpaceConfigApiV2RequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id of the instance type owner"},
    )


class DescribeSpaceConfigParamsApiV2ResponseSchema(Schema):
    name = fields.String(
        required=True,
        metadata={"example": "filebeat-aws", "description": "name of the monitoring configuration"},
    )
    title = fields.String(
        required=True,
        metadata={"example": "Filebeat AWS", "description": "title of the monitoring configuration"},
    )
    default = fields.Boolean(required=False, metadata={"description": "dashboard created at space creation"})


class DescribeSpaceConfigApi1V2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    logConfigSet = fields.Nested(DescribeSpaceConfigParamsApiV2ResponseSchema, many=True, allow_none=False)
    logConfigTotal = fields.Integer(
        required=True,
        metadata={"example": 10, "description": "Total number of configuration available"},
    )


class DescribeSpaceConfigApiV2ResponseSchema(Schema):
    DescribeSpaceConfigResponse = fields.Nested(
        DescribeSpaceConfigApi1V2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeSpaceConfig(ServiceApiView):
    summary = "List of monitoring instance confs"
    description = "List of monitoring instance confs"
    tags = ["loggingservice"]
    definitions = {
        "DescribeSpaceConfigApiV2RequestSchema": DescribeSpaceConfigApiV2RequestSchema,
        "DescribeSpaceConfigApiV2ResponseSchema": DescribeSpaceConfigApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeSpaceConfigApiV2RequestSchema)
    parameters_schema = DescribeSpaceConfigApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeSpaceConfigApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeSpaceConfigApiV2ResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        # account_id = data.pop("owner_id")
        # account = controller.get_account(account_id)
        service_definition = controller.get_default_service_def(ApiLoggingSpace.plugintype)
        self.logger.debug("+++++ DescribeSpaceConfig - service_definition: %s" % service_definition)

        dashboard = service_definition.get_config("dashboard")
        self.logger.debug("+++++ DescribeSpaceConfig - dashboard: %s" % dashboard)

        res_type_set = []
        log_confs_total = 0
        for dashboard_item in dashboard:
            name = None
            if "name" in dashboard_item:
                name = dashboard_item["name"]
            title = dashboard_item["title"]

            default = False
            if "default" in dashboard_item:
                default = dashboard_item["default"]
            item = {"name": name, "title": title, "default": default}
            res_type_set.append(item)
            log_confs_total += 1

        res_type_set.sort(key=lambda x: x.get("title"))

        res = {
            "DescribeSpaceConfigResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "logConfigSet": res_type_set,
                "logConfigTotal": log_confs_total,
            }
        }
        return res


class EnableDashConfigApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    Return = fields.Boolean(required=True, allow_none=False, data_key="return", metadata={"example": True})
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        metadata={"description": "active task id"},
    )


class EnableDashConfigApiResponseSchema(Schema):
    EnableDashConfigResponse = fields.Nested(
        EnableDashConfigApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class EnableDashConfigApiRequestSchema(Schema):
    SpaceId = fields.String(required=False, context="query", metadata={"description": "logging space id"})
    Config = fields.String(required=False, metadata={"example": "Filebeat Apache", "description": "name of dashboard"})


class EnableDashConfigApiBodyRequestSchema(Schema):
    body = fields.Nested(EnableDashConfigApiRequestSchema, context="body")


class EnableDashConfig(ServiceApiView):
    summary = "Enable logging config in a space"
    description = "Enable logging config in a space"
    tags = ["loggingservice"]
    definitions = {
        "EnableDashConfigApiRequestSchema": EnableDashConfigApiRequestSchema,
        "EnableDashConfigApiResponseSchema": EnableDashConfigApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(EnableDashConfigApiBodyRequestSchema)
    parameters_schema = EnableDashConfigApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": EnableDashConfigApiResponseSchema}}
    )
    response_schema = EnableDashConfigApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        # get service definition with engine configuration
        conf = data.get("Config")
        oid = data.get("SpaceId")

        service_definition = controller.get_default_service_def(ApiLoggingSpace.plugintype)
        self.logger.debug("+++++ EnableDashConfig - service_definition: %s" % service_definition)

        dashboard = service_definition.get_config("dashboard")
        self.logger.debug("+++++ EnableDashConfig - dashboard: %s" % dashboard)
        def_config = service_definition.get_main_config().params
        self.logger.debug("+++++ EnableDashConfig - def_config: %s" % def_config)

        dashboard_item_selected = None
        for dashboard_item in dashboard:
            name = dashboard_item["name"]
            if name == conf:
                dashboard_item_selected = dashboard_item

        if dashboard_item_selected is None:
            raise ApiManagerError("Conf %s was not found" % conf)

        type_plugin: ApiLoggingSpace = controller.get_service_type_plugin(oid, plugin_class=ApiLoggingSpace)
        account_id = type_plugin.instance.account_id

        # check account
        account: ApiAccount
        parent_plugin: ApiLoggingService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiLoggingService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        self.logger.debug("+++++ EnableDashConfig - triplet: %s" % triplet)

        data = {}
        data.update({"resource_space_id": type_plugin.resource_uuid})
        data.update({"triplet": triplet})
        # data.update({"organization": org.name})
        # data.update({"division": div.name})
        # data.update({"account": account.name})

        return_value = type_plugin.enable_dash_config(def_config, dashboard_item_selected, data)

        res = {
            "EnableDashConfigResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class DisableDashConfigApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    Return = fields.Boolean(required=True, allow_none=False, data_key="return", metadata={"example": True})
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        metadata={"description": "active task id"},
    )


class DisableDashConfigApiResponseSchema(Schema):
    DisableDashConfigResponse = fields.Nested(
        DisableDashConfigApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DisableDashConfigApiRequestSchema(Schema):
    SpaceId = fields.String(required=False, context="query", metadata={"description": "logging space id"})
    Config = fields.String(required=False, metadata={"example": "LinResource", "description": "name of dashboard"})


class DisableDashConfigApiBodyRequestSchema(Schema):
    body = fields.Nested(DisableDashConfigApiRequestSchema, context="body")


class DisableDashConfig(ServiceApiView):
    summary = "Disable logging config in a space"
    description = "Disable logging config in a space"
    tags = ["loggingservice"]
    definitions = {
        "DisableDashConfigApiRequestSchema": DisableDashConfigApiRequestSchema,
        "DisableDashConfigApiResponseSchema": DisableDashConfigApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DisableDashConfigApiBodyRequestSchema)
    parameters_schema = DisableDashConfigApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": DisableDashConfigApiResponseSchema}}
    )
    response_schema = DisableDashConfigApiResponseSchema

    def put(self, controller: ServiceController, data, *args, **kwargs):
        # get service definition with engine configuration
        conf = data.get("Config")
        oid_space = data.get("SpaceId")

        service_definition = controller.get_default_service_def(ApiLoggingSpace.plugintype)
        self.logger.debug("+++++ DisableDashConfig - service_definition: %s" % service_definition)

        dashboard = service_definition.get_config("dashboard")
        self.logger.debug("+++++ DisableDashConfig - dashboard: %s" % dashboard)
        def_config = service_definition.get_main_config().params
        self.logger.debug("+++++ DisableDashConfig - def_config: %s" % def_config)

        dashboard_item_selected = None
        for dashboard_item in dashboard:
            name = dashboard_item["name"]
            if name == conf:
                dashboard_item_selected = dashboard_item

        if dashboard_item_selected is None:
            raise ApiManagerError("Conf %s was not found" % conf)

        # get instances list
        data_search = {}
        res, total = controller.get_service_type_plugins(
            service_uuid_list=[oid_space],
            service_name_list=[],
            service_id_list=[],
            account_id_list=[],
            plugintype=ApiLoggingSpace.plugintype,
            **data_search,
        )
        instances_set = None
        for r in res:
            r: ApiLoggingSpace
            instances_set = r.aws_info()

        # check space has dashboard
        b_dashboard_present = False
        dashboards = instances_set["dashboards"]
        for dashboard in dashboards:
            dashboardTitle: str = dashboard["dashboardTitle"]
            if dashboardTitle.find(dashboard_item_selected["title"]) != -1:
                b_dashboard_present = True

        if not b_dashboard_present:
            raise ApiManagerError("Space haven't dashboard %s" % dashboard_item_selected["title"])

        type_plugin_space: ApiLoggingSpace = controller.get_service_type_plugin(oid_space, plugin_class=ApiLoggingSpace)
        account_id = type_plugin_space.instance.account_id

        # check account
        account: ApiAccount
        parent_plugin: ApiLoggingService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiLoggingService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # # get parent division
        # div: Division = controller.manager.get_entity(Division, account.division_id)
        # # get parent organization
        # org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        # triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        # self.logger.debug("+++++ DisableDashConfig - triplet: %s" % triplet)

        data = {}
        data.update({"resource_space_id": type_plugin_space.resource_uuid})
        # data.update({"triplet": triplet})
        # data.update({"organization": org.name})
        # data.update({"division": div.name})
        # data.update({"account": account.name})

        return_value = type_plugin_space.disable_dash_config(def_config, dashboard_item_selected, data)

        res = {
            "DisableDashConfigResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin_space.active_task,
            }
        }
        return res, 202


class LoggingSpaceServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/loggingservices/spaces"
        rules = [
            ("%s/createspace" % base, "POST", CreateSpace, {}),
            ("%s/deletespace" % base, "DELETE", DeleteSpace, {}),
            ("%s/describespaces" % base, "GET", DescribeSpaces, {}),
            ("%s/syncspaceusers" % base, "PUT", SyncUsersSpace, {}),
            ("%s/describespaceconfig" % base, "GET", DescribeSpaceConfig, {}),
            ("%s/enabledashconfig" % base, "PUT", EnableDashConfig, {}),
            ("%s/disabledashconfig" % base, "PUT", DisableDashConfig, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
