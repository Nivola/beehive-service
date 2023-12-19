# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    SwaggerApiView,
    GetApiObjectRequestSchema,
)
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beecell.simple import format_date
from marshmallow.validate import OneOf

try:
    from dateutil.parser import relativedelta
except ImportError as ex:
    from dateutil import relativedelta


class GetReportCostParamsResponseSchema(Schema):
    id = fields.Integer(required=True, example=10)
    plugin_name = fields.String(required=True)
    report_date = fields.DateTime(required=False)
    is_reported = fields.Boolean(required=False)
    period = fields.String(required=True)
    value = fields.Decimal(required=True)
    cost = fields.Decimal(required=True)
    metric_type_id = fields.String(required=False)
    job_id = fields.Integer(required=False)


class GetReportCostResponseSchema(Schema):
    report = fields.Nested(GetReportCostParamsResponseSchema, required=True, allow_none=True)


class GetReportCostRequestSchema(GetApiObjectRequestSchema):
    rid = fields.String(required=True, description="id, uuid or name", context="path")


class GetReportCost(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetReportCostResponseSchema": GetReportCostResponseSchema,
        "GetReportCostRequestSchema": GetReportCostRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetReportCostRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetReportCostResponseSchema}})

    @staticmethod
    def report_info(model):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if model is None:
            return None

        info = {
            "id": model.id,
            "value": model.value,
            "cost": model.cost,
            "plugin_name": model.plugin_name,
            "metric_type_id": model.metric_type_id,
            "period": model.period,
            "report_date": format_date(model.report_date),
            "is_reported": model.report_date is not None,
            "job_id": model.job_id,
            "date": {
                "creation": format_date(model.creation_date),
                "modified": format_date(model.modification_date),
                "expiry": "",
            },
        }
        if model.expiry_date is not None:
            info["date"]["expiry"] = format_date(model.expiry_date)
        return info

    def get(self, controller, data, oid, rid, *args, **kwargs):
        report = controller.get_report_cost_by_account(oid, rid)
        return {"report": GetReportCost.report_info(report)}


class ListReportCostRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    oid = fields.String(required=True, description="id, uuid or name", context="path")
    plugin_name = fields.String(required=False, context="query")
    is_reported = fields.Boolean(required=False, context="query")  # True se report_data is not null
    period = fields.String(required=False, context="query")
    period_start = fields.String(required=False, context="query")
    period_end = fields.String(required=False, context="query")
    job_id = fields.Integer(required=False, allow_none=True, context="query")
    field = fields.String(
        validate=OneOf(["id", "period"], error="Field can be id, period"),
        description="enitities list order field. Ex. id, period",
        default="id",
        example="id",
        missing="id",
        context="query",
    )


class ListReportCostResponseSchema(PaginatedResponseSchema):
    reports = fields.Nested(GetReportCostParamsResponseSchema, many=True, required=True, allow_none=True)


class ListReportCost(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListReportCostResponseSchema": ListReportCostResponseSchema,
        "ListReportCostRequestSchema": ListReportCostRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListReportCostRequestSchema)
    parameters_schema = ListReportCostRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListReportCostResponseSchema}})
    response_schema = ListReportCostResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        reports, total = controller.get_report_list_by_account([oid], **data)
        res = [GetReportCost.report_info(report) for report in reports]
        res_dict = self.format_paginated_response(res, "reports", total, **data)
        return res_dict


class AccountCostAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/accounts/<oid>/costs" % base, "GET", ListReportCost, {}),
            ("%s/accounts/<oid>/cost/<rid>" % base, "GET", GetReportCost, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
