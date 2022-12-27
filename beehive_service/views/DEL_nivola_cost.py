# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ServiceValidateDate
from beehive_service.views.account_cost import ReportCostConsumeResponseSchema
from beehive_service.service_util import __SRV_REPORT_COMPLETE_MODE__,\
    __SRV_REPORT_SUMMARY_MODE__, __SRV_REPORT_MODE__
from marshmallow.validate import OneOf
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from datetime import date
from beecell.simple import format_date

class ReportCostConsumeNivolaRequestSchema(ServiceValidateDate):
    year_month = fields.String(required=False, context=u'query', example=u'2018-12', description=u'report period')
    start_date = fields.DateTime(required=False, context=u'query', example=u'', description=u'report extraction start date')
    end_date = fields.DateTime(required=False, context=u'query', example=u'', description=u'report extraction start date')
    report_mode = fields.String(required=False, context=u'query', default=__SRV_REPORT_COMPLETE_MODE__,
                        missing=__SRV_REPORT_COMPLETE_MODE__, validate=OneOf(__SRV_REPORT_MODE__),
                        example=__SRV_REPORT_SUMMARY_MODE__, description=u'extraction report mode:%s' % __SRV_REPORT_MODE__)


class ReportCostConsumes(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ReportCostConsumeNivolaRequestSchema': ReportCostConsumeNivolaRequestSchema,
        u'ReportCostConsumeResponseSchema': ReportCostConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ReportCostConsumeNivolaRequestSchema)
    parameters_schema = ReportCostConsumeNivolaRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ReportCostConsumeResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        Report Cost Consume for Nivola
        Call this api to list all the cost and consume for Nivola
        """

        year_month = data.get(u'year_month', None)
        start_date = data.get(u'start_date', None)
        end_date = data.get(u'end_date', None)
        report_mode = data.get(u'report_mode')

        res = controller.get_report_costconsume_bynivola(year_month,start_date,end_date, report_mode)

        resp = {u'reports': res}
        self.logger.warning(u'resp=%s' % resp)
        return resp

class ReportCostNivolaRequestSchema(Schema):
    year = fields.String(required=False, context=u'query', example=u'2018', description=u'year filter')

class ReportCostNivolaResponseSchema(Schema):
    credit_tot = fields.Float(required=True)
    credit_res = fields.Float(required=True)
    cost_tot = fields.Float(required=True)
    cost_reported = fields.Float(required=True)
    cost_unreported = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)

class ListCostNivolaResponseSchema(Schema):
    costs = fields.Nested(ReportCostNivolaResponseSchema, many=False, required=True, allow_none=False)

class CostNivola(ServiceApiView):
    tags = [u'authority']
    definitions = {
        u'ListCostNivolaResponseSchema': ListCostNivolaResponseSchema,
        u'ReportCostNivolaRequestSchema': ReportCostNivolaRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ReportCostNivolaRequestSchema)
    parameters_schema = ReportCostNivolaRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListCostNivolaResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        Report Cost Consume for Nivola
        Call this api to list all the cost and consume for Nivola
        """
        year = data.get(u'year', date.today().year)
        first_year_str = u'%s-01-01' %year
        last_year_str = u'%s-12-01' %year

        credit_tot = controller.get_credit_nivola_by_year(year)
        imp_rendicontato = controller.get_cost_by_nivola_on_period(first_year_str, last_year_str, reported=True)
        imp_non_rendicontato = controller.get_cost_by_nivola_on_period(first_year_str, last_year_str, reported=False)

        imp_totale = imp_rendicontato + imp_non_rendicontato
        credit_res = credit_tot - imp_totale

        res = {
            u'extraction_date': format_date(date.today()),
            u'credit_tot': credit_tot,
            u'credit_res': credit_res,
            u'cost_tot': imp_totale,
            u'cost_reported': imp_rendicontato,
            u'cost_unreported': imp_non_rendicontato
        }

        resp = {u'costs': res}
        return resp



class NivolaCostAPI(ApiView):
    """Generic Service Object api routes:
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = u'nws'

        rules = [
            (u'%s/nivola/costs/report' % base, u'GET', ReportCostConsumes, {}),
            (u'%s/nivola/costs/year_summary' % base, u'GET', CostNivola, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
