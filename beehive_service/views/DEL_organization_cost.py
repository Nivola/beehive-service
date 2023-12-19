# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.apimanager import ApiView, GetApiObjectRequestSchema
from beehive_service.views import ServiceApiView
from beehive_service.views.account_cost import (
    ReportCostConsumeResponseSchema,
    ReportCostConsumeRequestSchema,
)
from beecell.swagger import SwaggerHelper
from beecell.simple import format_date
from datetime import date
from marshmallow import fields
from marshmallow.schema import Schema


class ReportCostOrganizationRequestSchema(GetApiObjectRequestSchema):
    year = fields.String(required=False, context="query", example="2018", description="year filter")


class ReportCostOrganizationResponseSchema(Schema):
    name = fields.String(required=False, description="Organization name")
    uuid = fields.String(required=False, description="Organization uuid")
    credit_tot = fields.Float(required=True)
    credit_res = fields.Float(required=True)
    cost_tot = fields.Float(required=True)
    cost_reported = fields.Float(required=True)
    cost_unreported = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)


class ListCostOrganizationResponseSchema(Schema):
    costs = fields.Nested(
        ReportCostOrganizationResponseSchema,
        many=False,
        required=True,
        allow_none=False,
    )


class CostOrganization(ServiceApiView):
    tags = ["authority"]
    definitions = {
        "ListCostOrganizationResponseSchema": ListCostOrganizationResponseSchema,
        "ReportCostOrganizationRequestSchema": ReportCostOrganizationRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ReportCostOrganizationRequestSchema)
    parameters_schema = ReportCostOrganizationRequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": ListCostOrganizationResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for an organization
        Call this api to list all the cost and consume for an organization
        """
        year = data.get("year", date.today().year)
        organization = controller.get_organization(oid)

        first_year_str = "%s-01-01" % year
        last_year_str = "%s-12-01" % year

        name = ""
        uuid = ""
        imp_rendicontato = 0.0
        imp_non_rendicontato = 0.0
        credit_tot = 0.0
        if organization is not None:
            name = organization.name
            uuid = organization.uuid
            credit_tot = organization.get_credit_by_year(year)
            imp_rendicontato = organization.get_cost_by_period(first_year_str, last_year_str, reported=True)
            imp_non_rendicontato = organization.get_cost_by_period(first_year_str, last_year_str, reported=False)

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

        organization = controller.get_organization(oid, active=True, filter_expired=False)
        res = organization.get_report_costconsume(year_month, start_date, end_date, report_mode)

        resp = {"reports": res}
        self.logger.warning("resp=%s" % resp)
        return resp


class OrganizationCostAPI(ApiView):
    """OrganizationAPI"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            (
                "%s/organizations/<oid>/costs/report" % base,
                "GET",
                ReportCostConsumes,
                {},
            ),
            (
                "%s/organizations/<oid>/costs/year_summary" % base,
                "GET",
                CostOrganization,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
