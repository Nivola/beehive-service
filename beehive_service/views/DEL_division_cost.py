# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, GetApiObjectRequestSchema
from beehive_service.views import ServiceApiView
from flasgger.marshmallow_apispec import Schema
from marshmallow.fields import Field
from beecell.swagger import SwaggerHelper
from marshmallow import fields
from datetime import date
from beehive_service.controller import ApiWallet
from beecell.simple import format_date
from beehive_service.views.account_cost import ReportCostConsumeRequestSchema,\
    ReportCostConsumeResponseSchema

class ReportCostsDivisionRequestSchema(GetApiObjectRequestSchema):
    year = fields.String(required=False, context=u'query', example=u'2018', description=u'year filter')


class ReportCostsDivisionResponseSchema(Schema):
    name = fields.String(required=False, description=u'Division name')
    uuid = fields.String(required=False, description=u'Division uuid')
    credit_tot = fields.Float(required=True)
    credit_res = fields.Float(required=True)
    cost_tot = fields.Float(required=True)
    cost_reported = fields.Float(required=True)
    cost_unreported = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)


class ListCostsDivisionResponseSchema(Schema):
    costs = fields.Nested(ReportCostsDivisionResponseSchema, many=False, required=True, allow_none=False)


class CostsDivision(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ListCostsDivisionResponseSchema': ListCostsDivisionResponseSchema,
        u'ReportCostsDivisionRequestSchema': ReportCostsDivisionRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ReportCostsDivisionRequestSchema)
    parameters_schema = ReportCostsDivisionRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListCostsDivisionResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Report Cost Consume for a division
        Call this api to list all the cost and consume for a division
        """
        year = data.get(u'year', date.today().year)
        division = controller.get_division(oid)

        first_year_str = u'%s-01-01' %year
        last_year_str = u'%s-12-31' %year

        name = u''
        uuid = u''
        imp_rendicontato = 0.0
        imp_non_rendicontato = 0.0
        credit_tot = 0.0
        if division is not None:
            name = division.name
            uuid = division.uuid
            wallet = controller.get_wallet_by_year(division.oid, year, )
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

        division = controller.get_division(oid, active=True, filter_expired=False)
        res = division.get_report_costconsume(year_month, start_date, end_date, report_mode)

        resp = {u'reports': res}
        self.logger.warning(u'resp=%s' % resp)
        return resp


class DivisionCostAPI(ApiView):
    """DivisionAPI
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/divisions/<oid>/costs/report' % base, u'GET', ReportCostConsumes, {}),
            (u'%s/divisions/<oid>/costs/year_summary' % base, u'GET', CostsDivision, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
