# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import ApiView, GetApiObjectRequestSchema
from beehive_service.views import ServiceApiView
from flasgger.marshmallow_apispec import Schema
from marshmallow.fields import Field
from beecell.swagger import SwaggerHelper
from marshmallow import fields
from datetime import date
from beehive_service.controller import ApiWallet
from beecell.simple import format_date
from beehive_service.views.account_cost import (
    ReportCostConsumeRequestSchema,
    ReportCostConsumeResponseSchema,
)


class ReportCostsDivisionRequestSchema(GetApiObjectRequestSchema):
    year = fields.String(required=False, context="query", example="2018", description="year filter")


class ReportCostsDivisionResponseSchema(Schema):
    name = fields.String(required=False, description="Division name")
    uuid = fields.String(required=False, description="Division uuid")
    credit_tot = fields.Float(required=True)
    credit_res = fields.Float(required=True)
    cost_tot = fields.Float(required=True)
    cost_reported = fields.Float(required=True)
    cost_unreported = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)


class ListCostsDivisionResponseSchema(Schema):
    costs = fields.Nested(ReportCostsDivisionResponseSchema, many=False, required=True, allow_none=False)


class CostsDivision(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ListCostsDivisionResponseSchema": ListCostsDivisionResponseSchema,
        "ReportCostsDivisionRequestSchema": ReportCostsDivisionRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ReportCostsDivisionRequestSchema)
    parameters_schema = ReportCostsDivisionRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListCostsDivisionResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for a division
        Call this api to list all the cost and consume for a division
        """
        year = data.get("year", date.today().year)
        division = controller.get_division(oid)

        first_year_str = "%s-01-01" % year
        last_year_str = "%s-12-31" % year

        name = ""
        uuid = ""
        imp_rendicontato = 0.0
        imp_non_rendicontato = 0.0
        credit_tot = 0.0
        if division is not None:
            name = division.name
            uuid = division.uuid
            wallet = controller.get_wallet_by_year(
                division.oid,
                year,
            )
            if wallet is not None and ApiWallet.ST_CLOSED == wallet.service_status_id:
                credit_tot = wallet.capital_total
                imp_rendicontato = wallet.capital_used
            else:
                credit_tot = division.get_credit_by_year(year)
                imp_rendicontato = division.get_cost_by_period(first_year_str, last_year_str, reported=True)
                imp_non_rendicontato = division.get_cost_by_period(first_year_str, last_year_str, reported=False)

        imp_totale = imp_rendicontato + imp_non_rendicontato
        credit_res = credit_tot - imp_totale

        res = {
            "name": name,
            "uuid": uuid,
            "extraction_date": format_date(date.today()),
            "credit_tot": credit_tot,
            "credit_res": credit_res,
            "cost_tot": imp_totale,
            "cost_reported": imp_rendicontato,
            "cost_unreported": imp_non_rendicontato,
        }

        resp = {"costs": res}
        return resp


class ReportCostConsumes(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ReportCostConsumeRequestSchema": ReportCostConsumeRequestSchema,
        "ReportCostConsumeResponseSchema": ReportCostConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ReportCostConsumeRequestSchema)
    parameters_schema = ReportCostConsumeRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ReportCostConsumeResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for a division
        Call this api to list all the cost and consume for a division
        """

        year_month = data.get("year_month", None)
        start_date = data.get("start_date", None)
        end_date = data.get("end_date", None)
        report_mode = data.get("report_mode")

        division = controller.get_division(oid, active=True, filter_expired=False)
        res = division.get_report_costconsume(year_month, start_date, end_date, report_mode)

        resp = {"reports": res}
        self.logger.warning("resp=%s" % resp)
        return resp


class DivisionCostAPI(ApiView):
    """DivisionAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/divisions/<oid>/costs/report" % base, "GET", ReportCostConsumes, {}),
            ("%s/divisions/<oid>/costs/year_summary" % base, "GET", CostsDivision, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
