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
from beehive_service.model import Division, Organization
from beehive_service.plugins.computeservice.controller import ApiComputeService
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    SwaggerApiView,
    ApiView,
)
from beehive_service.plugins.monitoringservice.controller import (
    ApiMonitoringService,
)
from beehive_service.plugins.monitoringservice.controller_alert import (
    ApiMonitoringAlert,
)
from beehive.common.data import operation


class CreateAlertApiParamRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        example="1",
        data_key="owner-id",
        description="account id or uuid associated to compute zone",
    )
    AvailabilityZone = fields.String(required=True, example="", description="availability zone")
    Name = fields.String(required=False, example="test", missing=None, description="alert name")
    AdditionalInfo = fields.String(required=False, example="test", missing=None, description="alert description")
    definition = fields.String(
        required=False,
        example="monitoring.alert.xxx",
        description="service definition of the alert",
    )
    norescreate = fields.Boolean(
        required=False,
        allow_none=True,
        description="don't create physical resource of the alert",
    )


class CreateAlertApiRequestSchema(Schema):
    alert = fields.Nested(CreateAlertApiParamRequestSchema, context="body")


class CreateAlertApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateAlertApiRequestSchema, context="body")


class CreateAlertApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, example="", allow_none=True)
    alertId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="alert id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class CreateAlertApiResponseSchema(Schema):
    CreateAlertResponse = fields.Nested(CreateAlertApiResponse1Schema, required=True, many=False, allow_none=False)


class CreateAlert(ServiceApiView):
    summary = "Create monitoring alert"
    description = "Create monitoring alert"
    tags = ["monitoringservice"]
    definitions = {
        "CreateAlertApiResponseSchema": CreateAlertApiResponseSchema,
        "CreateAlertApiRequestSchema": CreateAlertApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateAlertApiBodyRequestSchema)
    parameters_schema = CreateAlertApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CreateAlertApiResponseSchema}})
    response_schema = CreateAlertApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        self.logger.debug("CreateAlert post - begin")
        inner_data = data.get("alert")

        service_definition_id = inner_data.get("definition")  # es. monitoring.alert.default2
        account_id = inner_data.get("owner_id")
        name = inner_data.get("Name", None)
        availability_zone = inner_data.get("AvailabilityZone", None)
        desc = inner_data.get("AdditionalInfo", None)

        # check account
        account: ApiAccount
        parent_plugin: ApiMonitoringService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiMonitoringService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        self.logger.debug("CreateAlert - triplet: %s" % triplet)

        if name is None:
            name = "Alert-%s" % availability_zone
            desc = triplet

        data.update({"triplet": triplet})
        data.update({"organization": org.name})
        data.update({"division": div.name})
        data.update({"account": account.name})
        data.update({"availability_zone": availability_zone})

        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiMonitoringAlert.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)
        self.logger.debug("CreateAlert - service_definition: %s" % service_definition)

        plugin: ApiMonitoringAlert
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
            "CreateAlertResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "alertId": plugin.instance.uuid,
                "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class DeleteAlertApiRequestSchema(Schema):
    AlertId = fields.String(
        required=False,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="alert id",
        context="query",
    )


class DeleteAlertApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, example="", description="operation id")
    alertId = fields.String(
        required=False,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="alert id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class DeleteAlertApiResponseSchema(Schema):
    DeleteAlertResponse = fields.Nested(DeleteAlertApiResponse1Schema, required=True, many=False, allow_none=False)


class DeleteAlert(ServiceApiView):
    summary = "Delete monitoring alert"
    description = "Delete monitoring alert"
    tags = ["monitoringservice"]
    definitions = {
        "DeleteAlertApiRequestSchema": DeleteAlertApiRequestSchema,
        "DeleteAlertApiResponseSchema": DeleteAlertApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteAlertApiRequestSchema)
    parameters_schema = DeleteAlertApiRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "no response", "schema": DeleteAlertApiResponseSchema}}
    )
    response_schema = DeleteAlertApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        alert_id = data.get("AlertId")
        type_plugin = controller.get_service_type_plugin(alert_id)
        type_plugin.delete()

        res = {
            "DeleteAlertResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "alertId": type_plugin.instance.uuid,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class MonitoringAlertStateReasonResponseSchema(Schema):
    nvl_code = fields.Integer(
        required=False,
        allow_none=True,
        example="",
        description="state code",
        data_key="nvl-code",
    )
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state message",
        data_key="nvl-message",
    )


class MonitoringAlertItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="id of the alert",
    )
    name = fields.String(required=True, example="test", description="name of the alert")
    creationDate = fields.DateTime(required=True, example="2022-01-25T11:20:18Z", description="creation date")
    description = fields.String(required=True, example="test", description="description of the alert")
    ownerId = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="account id of the owner of the alert",
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        example="test",
        description="account name of the owner of the alert",
    )
    state = fields.String(
        required=True,
        example="available",
        description="state of the alert",
        data_key="state",
    )
    stateReason = fields.Nested(
        MonitoringAlertStateReasonResponseSchema,
        many=False,
        required=True,
        description="state alert description",
    )
    templateId = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="id of the alert template",
    )
    templateName = fields.String(required=True, example="test", description="name of the alert template")
    users_email = fields.List(fields.String)
    user_severities = fields.List(fields.String)
    resource_uuid = fields.String(required=False)


class DescribeMonitoringAlerts1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True, allow_none=True)
    alertInfo = fields.Nested(
        MonitoringAlertItemParameterResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )
    alertTotal = fields.Integer(
        required=False,
        example="0",
        descriptiom="total monitoring instance",
        data_key="alertTotal",
    )


class DescribeAlertsResponseSchema(Schema):
    DescribeAlertsResponse = fields.Nested(DescribeMonitoringAlerts1ResponseSchema, required=True, many=False)


class DescribeAlertsRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account id",
    )
    AlertName = fields.String(required=False, description="alert name", context="query")
    alert_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="alert-id.N",
        description="list of alert id",
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


class DescribeAlerts(ServiceApiView):
    summary = "Describe monitoring alert"
    description = "Describe monitoring alert"
    tags = ["monitoringservice"]
    definitions = {
        "DescribeAlertsRequestSchema": DescribeAlertsRequestSchema,
        "DescribeAlertsResponseSchema": DescribeAlertsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAlertsRequestSchema)
    parameters_schema = DescribeAlertsRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": DescribeAlertsResponseSchema}})
    response_schema = DescribeAlertsResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        monitoring_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("alert_id_N", [])
        self.logger.debug("DescribeAlerts get - instance_id_list: %s" % instance_id_list)

        # get instance name
        instance_name_list = data.get("AlertName", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]
        self.logger.debug("DescribeAlerts get - instance_name_list: %s" % instance_name_list)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            service_id_list=monitoring_id_list,
            account_id_list=account_id_list,
            plugintype=ApiMonitoringAlert.plugintype,
            **data_search,
        )
        instances_set = []
        for r in res:
            r: ApiMonitoringAlert
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = "0"
        else:
            next_token = str(data_search["page"] + 1)

        res = {
            "DescribeAlertsResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "next_token": next_token,
                "alertInfo": instances_set,
                "alertTotal": total,
            }
        }
        return res


class UpdateUsersAlertApi1ResponseSchema(Schema):
    xmlns = fields.String(
        required=False,
        data_key="__xmlns",
        example="https://nivolapiemonte.it/XMLdoc/2022-05-16/alert/",
    )
    Return = fields.Boolean(required=True, example=True, allow_none=False, data_key="return")
    requestId = fields.String(required=True, example="alertXX-3525-4f95-880d-479acdb463a4", allow_none=True)
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        description="active task id",
    )


class UpdateUsersAlertApiResponseSchema(Schema):
    UpdateAlertUsersResponse = fields.Nested(
        UpdateUsersAlertApi1ResponseSchema, required=True, many=False, allow_none=False
    )


class UpdateUsersAlertApiRequestSchema(Schema):
    AlertId = fields.String(required=True, description="monitoring alert id", context="query")
    UsersEmail = fields.String(required=True, description="users email of monitoring alert", context="query")
    Severity = fields.String(required=True, description="severity of monitoring alert", context="query")


class UpdateUsersAlertApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateUsersAlertApiRequestSchema, context="body")


class UpdateUsersAlert(ServiceApiView):
    summary = "Update users in a zabbix alert"
    description = "Update users in a zabbix alert"
    tags = ["monitoringservice"]
    definitions = {
        "UpdateUsersAlertApiRequestSchema": UpdateUsersAlertApiRequestSchema,
        "UpdateUsersAlertApiResponseSchema": UpdateUsersAlertApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateUsersAlertApiBodyRequestSchema)
    parameters_schema = UpdateUsersAlertApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": UpdateUsersAlertApiResponseSchema}}
    )
    response_schema = UpdateUsersAlertApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        oid = data.get("AlertId")
        type_plugin: ApiMonitoringAlert = controller.get_service_type_plugin(oid, plugin_class=ApiMonitoringAlert)

        # check account
        account: ApiAccount
        parent_plugin: ApiMonitoringService
        account, parent_plugin = self.check_parent_service(
            controller, type_plugin.instance.account_id, plugintype=ApiMonitoringService.plugintype
        )

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        self.logger.debug("UpdateUsersAlert - triplet: %s" % triplet)

        users_email = data.get("UsersEmail")
        severity = data.get("Severity")
        return_value = type_plugin.update_users(triplet, users_email, severity)

        res = {
            "UpdateAlertUsersResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class DescribeAlertUserSeverityResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, allow_none=True)
    user_severities = fields.List(fields.String(), required=True, description="List of severity")


class DescribeAlertUserSeverityResponseSchema(Schema):
    DescribeAlertUserSeverityResponse = fields.Nested(
        DescribeAlertUserSeverityResponse1Schema, required=True, many=False
    )


class DescribeAlertUserSeverity(ServiceApiView):
    summary = "Describe monitoring alert"
    description = "Describe monitoring alert"
    tags = ["monitoringservice"]
    definitions = {
        # "DescribeAlertsRequestSchema": DescribeAlertsRequestSchema,
        "DescribeAlertUserSeverityResponseSchema": DescribeAlertUserSeverityResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAlertsRequestSchema)
    parameters_schema = DescribeAlertsRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeAlertUserSeverityResponseSchema}}
    )
    response_schema = DescribeAlertUserSeverityResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        uri = "/v1.0/nrs/provider/monitoring_thresholds/user/severities"
        res = controller.api_client.admin_request("resource", uri, "get")
        user_severities = res.get("user_severities")

        res = {
            "DescribeAlertUserSeverityResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "user_severities": user_severities,
            }
        }
        return res


class MonitoringAlertServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/monitoringservices/alerts"
        rules = [
            ("%s/createalert" % base, "POST", CreateAlert, {}),
            ("%s/deletealert" % base, "DELETE", DeleteAlert, {}),
            ("%s/describealerts" % base, "GET", DescribeAlerts, {}),
            ("%s/updatealertusers" % base, "PUT", UpdateUsersAlert, {}),
            ("%s/describealertuserseverity" % base, "GET", DescribeAlertUserSeverity, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
