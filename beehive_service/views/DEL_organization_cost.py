# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, GetApiObjectRequestSchema
from beehive_service.views import ServiceApiView
from beehive_service.views.account_cost import ReportCostConsumeResponseSchema, \
    ReportCostConsumeRequestSchema
from beecell.swagger import SwaggerHelper
from beecell.simple import format_date
from datetime import date
from marshmallow import fields
from marshmallow.schema import Schema


class ReportCostOrganizationRequestSchema(GetApiObjectRequestSchema):
    year = fields.String(required=False, context=u'query', example=u'2018', description=u'year filter')


class ReportCostOrganizationResponseSchema(Schema):
    name = fields.String(required=False, description=u'Organization name')
    uuid = fields.String(required=False, description=u'Organization uuid')
    credit_tot = fields.Float(required=True)
    credit_res = fields.Float(required=True)
    cost_tot = fields.Float(required=True)
    cost_reported = fields.Float(required=True)
    cost_unreported = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)


class ListCostOrganizationResponseSchema(Schema):
    costs = fields.Nested(ReportCostOrganizationResponseSchema, many=False, required=True, allow_none=False)


class CostOrganization(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ListCostOrganizationResponseSchema': ListCostOrganizationResponseSchema,
        u'ReportCostOrganizationRequestSchema': ReportCostOrganizationRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ReportCostOrganizationRequestSchema)
    parameters_schema = ReportCostOrganizationRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListCostOrganizationResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for an organization
        Call this api to list all the cost and consume for an organization
        """
        year = data.get(u'year', date.today().year)
        organization = controller.get_organization(oid)

        first_year_str = u'%s-01-01' % year
        last_year_str = u'%s-12-01' % year

        name = u''
        uuid = u''
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
            u'name': name,
            u'uuid': uuid,
            u'extraction_date': format_date(date.today()),
            u'credit_tot': credit_tot,
            u'credit_res': credit_res,
            u'cost_tot': imp_totale,
            u'cost_reported': imp_rendicontato,
            u'cost_unreported': imp_non_rendicontato
        }

        resp = {u'costs': res}
        return resp


class ReportCostConsumes(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ReportCostConsumeRequestSchema': ReportCostConsumeRequestSchema,
        u'ReportCostConsumeResponseSchema': ReportCostConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ReportCostConsumeRequestSchema)
    parameters_schema = ReportCostConsumeRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ReportCostConsumeResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for a division
        Call this api to list all the cost and consume for a division
        """

        year_month = data.get(u'year_month', None)
        start_date = data.get(u'start_date', None)
        end_date = data.get(u'end_date', None)
        report_mode = data.get(u'report_mode')

        organization = controller.get_organization(oid, active=True, filter_expired=False)
        res = organization.get_report_costconsume(year_month, start_date, end_date, report_mode)

        resp = {u'reports': res}
        self.logger.warning(u'resp=%s' % resp)
        return resp


class OrganizationCostAPI(ApiView):
    """OrganizationAPI
    """

    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/organizations/<oid>/costs/report' % base, u'GET', ReportCostConsumes, {}),
            (u'%s/organizations/<oid>/costs/year_summary' % base, u'GET', CostOrganization, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
