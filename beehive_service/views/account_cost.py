# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, ApiObjectRequestFiltersSchema, \
    PaginatedRequestQuerySchema, PaginatedResponseSchema, SwaggerApiView, \
    GetApiObjectRequestSchema
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
    id = fields.Integer(required=True,  example=10)
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
    rid = fields.String(required=True, description='id, uuid or name', context='path')


class GetReportCost(ServiceApiView):
    tags = ['service']
    definitions = {
        'GetReportCostResponseSchema': GetReportCostResponseSchema,
        'GetReportCostRequestSchema': GetReportCostRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(GetReportCostRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetReportCostResponseSchema
        }
    })
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
            'id': model.id,
            'value': model.value,
            'cost': model.cost,
            'plugin_name': model.plugin_name,
            'metric_type_id': model.metric_type_id,
            'period': model.period,
            'report_date': format_date(model.report_date),
            'is_reported': model.report_date is not None,
            'job_id': model.job_id,
            'date': {
                'creation': format_date(model.creation_date),
                'modified': format_date(model.modification_date),
                'expiry': ''
                }
            }
        if model.expiry_date is not None:
            info['date']['expiry'] = format_date(model.expiry_date)
        return info

    def get(self, controller, data, oid, rid, *args, **kwargs):
        report = controller.get_report_cost_by_account(oid, rid)
        return {'report': GetReportCost.report_info(report)}


class ListReportCostRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                  PaginatedRequestQuerySchema):
    oid = fields.String(required=True, description='id, uuid or name', context='path')
    plugin_name = fields.String(required=False, context='query')
    is_reported = fields.Boolean(required=False, context='query')  # True se report_data is not null
    period = fields.String(required=False, context='query')
    period_start = fields.String(required=False, context='query')
    period_end = fields.String(required=False, context='query')
    job_id = fields.Integer(required=False, allow_none=True, context='query')
    field = fields.String(validate=OneOf(['id', 'period'], error='Field can be id, period'),
                          description='enitities list order field. Ex. id, period',
                          default='id', example='id', missing='id', context='query')


class ListReportCostResponseSchema(PaginatedResponseSchema):
    reports = fields.Nested(GetReportCostParamsResponseSchema, many=True, required=True, allow_none=True)


class ListReportCost(ServiceApiView):
    tags = ['service']
    definitions = {
        'ListReportCostResponseSchema': ListReportCostResponseSchema,
        'ListReportCostRequestSchema': ListReportCostRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListReportCostRequestSchema)
    parameters_schema = ListReportCostRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListReportCostResponseSchema
        }
    })
    response_schema = ListReportCostResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        reports, total = controller.get_report_list_by_account([oid], **data)
        res = [GetReportCost.report_info(report) for report in reports]
        res_dict = self.format_paginated_response(res, 'reports', total, **data)
        return res_dict


# class UpdateReportCostParamRequestSchema(Schema):
#     value = fields.Decimal(required=False)
#     cost = fields.Decimal(required=False)
#
#
# class UpdateReportCostRequestSchema(Schema):
#     report = fields.Nested(UpdateReportCostParamRequestSchema)
#
#
# class UpdateReportCostBodyRequestSchema(GetApiObjectRequestSchema):
#     body = fields.Nested(UpdateReportCostRequestSchema, context='body')
#
#
# class UpdateReportCost(ServiceApiView):
#     tags = ['service']
#     definitions = {
#          'UpdateReportCostRequestSchema':UpdateReportCostRequestSchema,
#          'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
#     }
#     parameters = SwaggerHelper().get_parameters(UpdateReportCostBodyRequestSchema)
#     parameters_schema = UpdateReportCostRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#              'description': 'success',
#              'schema': CrudApiObjectResponseSchema
#          }
#     })
#
#     @transaction
#     def put(self, controller, data, oid, rid, *args, **kwargs):
#         srv_rc = controller.get_report_cost_by_account(oid, rid)
#         data = data.get('report')
#         resp = srv_rc.update(**data)
#         return ({'uuid':resp}, 200)


# class CreateReportCost(ServiceApiView):
#     pass
#
#
# class DeleteReportCost(ServiceApiView):
#     tags = ['service']
#     definitions = {}
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = ServiceApiView.setResponses({
#         204: {
#             'description': 'no response'
#         }
#     })
#
#     def delete(self, controller, data, oid, rid, *args, **kwargs):
#         """
#         Delete report cost object
#         Call this api to delete an report cost object.
#         """
#         rc = controller.get_report_cost_by_account(oid, rid)
#         resp = rc.delete()
#         return resp, 204


# # # list
# class GetReportCostMontlyParamsResponseSchema(Schema):
# #     id = fields.Integer(required=True,  example=10)
#     plugin_name = fields.String(required=True)
#     report_date = fields.DateTime(required=False)
#     is_reported = fields.Boolean(required=True)
#     period = fields.String(required=True)
#     value = fields.Decimal(required=True)
#     cost = fields.Decimal(required=True)
#     metric_type_id = fields.String(required=True)
#     name = fields.String(required=True)
#     measure_unit = fields.String(required=False)
# #     job_id = fields.Integer(required=False)
#
#
# class ListReportCostMontlyRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema):
#     plugin_name = fields.String(required=False, context='query')
#     is_reported = fields.Boolean(required=False, context='query')  # True se report_data is not null
#
#
# class ListReportCostMontlyResponseSchema(Schema):
#     reports = fields.Nested(GetReportCostMontlyParamsResponseSchema,
#                                   many=True, required=True, allow_none=True)
#
#
# class ListReportCostMontly(ServiceApiView):
#     tags = ['service']
#     definitions = {
#         'ListReportCostMontlyResponseSchema': ListReportCostMontlyResponseSchema,
#         'ListReportCostMontlyRequestSchema': ListReportCostMontlyRequestSchema
#     }
#     parameters = SwaggerHelper().get_parameters(ListReportCostMontlyRequestSchema)
#     parameters_schema = ListReportCostMontlyRequestSchema
#     responses = SwaggerApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ListReportCostMontlyResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, period, *args, **kwargs):
#         reports = controller.get_report_cost_monthly_by_account(oid, period, **data)
#         return {'reports': reports}


# ## ReportCostConsume
# class ReportCostConsumeRequestSchema(GetApiObjectRequestSchema):
#     year_month = fields.String(required=False, context='query', example='2018-12', description='report period')
#     start_date = fields.DateTime(required=False, context='query', example='',
#                                  description='report extraction start date')
#     end_date = fields.DateTime(required=False, context='query', example='',
#                                description='report extraction start date')
#     report_mode = fields.String(required=False, context='query', default=__SRV_REPORT_COMPLETE_MODE__,
#                                 missing=__SRV_REPORT_COMPLETE_MODE__, validate=OneOf(__SRV_REPORT_MODE__),
#                                 example=__SRV_REPORT_SUMMARY_MODE__,
#                                 description='extraction report mode:%s' % __SRV_REPORT_MODE__)

#     @validates_schema
#     def validate_date_parameters(self, data):
#         '''
#         '''
#         date_is_not_valid = True
#         start_date = data.get('start_date', None)
#         end_date = data.get('end_date', None)
#
#         if start_date is not None and end_date is not None:
#
#             if start_date.year <> end_date.year:
#                 raise ValidationError(
#                     'Param start_date %s and end_date %s can be refer the same year' % (start_date, end_date))
#
#             if start_date.year > end_date.year:
#                 raise ValidationError(
#                     'Param start_date %s and end_date %s are not in a valid range' % (start_date, end_date))
#
#             date_is_not_valid = False
#
#         if data.get('year_month', None) is None and date_is_not_valid:
#             raise ValidationError('Param year_month or start_date and end_date cannot be None')


# class ReportCostConsumeItemDetailResponseSchema(Schema):
#     metric_type_id = fields.Integer(required=True)
#     amount = fields.Float(required=True)
#     name = fields.String(required=True)
#     unit = fields.String(required=True)
#     qta = fields.Float(required=True)
#
#
# class ReportCostConsumeItemResponseSchema(Schema):
#     metrics = fields.Nested(ReportCostConsumeItemDetailResponseSchema, many=True, allow_none=False)
#     total = fields.Float(required=True)
#     day = fields.String(required=True)
#
#
# class ReportCostConsumeServiceContainerResponseSchema(Schema):
#     details = fields.Nested(ReportCostConsumeItemResponseSchema, many=True, allow_none=True)
#     total = fields.Float(required=True)
#     name = fields.String(required=False)
#     plugin_name = fields.String(required=False)
#     summary_consume = fields.Nested(ReportCostConsumeItemDetailResponseSchema, many=True, allow_none=False)
#
#
# class ReportCostCreditResponseSchema(Schema):
#     initial = fields.Float(required=True)
#     accounted = fields.Float(required=True)
#     remaining_pre = fields.Float(required=True)
#     consume_period = fields.Float(required=True)
#     remaining_post = fields.Float(required=True)
#
#
# class ReportCostConsumePeriodResponseSchema(Schema):
#     start_date = fields.Date(required=True)
#     end_date = fields.Date(required=True)
#
#
# class ReportCreditCompositionItemResponseSchema(Schema):
#     agreement_date_start = fields.Date(required=True)
#     agreement_date_end = fields.Date(required=False, allow_none=True)
#     agreement_amount = fields.Float(required=True)
#     agreement = fields.String(required=True)
#     agreement_id = fields.String(required=True)
#
#
# class ReportCreditCompositionResponseSchema(Schema):
#     total_amount = fields.Float(required=True)
#     agreements = fields.Nested(ReportCreditCompositionItemResponseSchema, required=False, many=True, allow_none=True)
#
#
# class CompleteReportCostConsumeItemResponseSchema(Schema):
#     organization = fields.String(required=True)
#     organization_id = fields.String(required=True)
#     division = fields.String(required=True)
#     division_id = fields.String(required=True)
#     account = fields.String(required=True)
#     account_id = fields.String(required=True)
#     postal_address = fields.String(required=False)
#     referent = fields.String(required=False)
#     email = fields.String(required=False)
#     hasvat = fields.Boolean(required=True)
#     date_report = fields.Date(required=True)
#     credit_composition = fields.Nested(ReportCreditCompositionResponseSchema, many=False, required=False,
#                                        allow_none=False)
#     period = fields.Nested(ReportCostConsumePeriodResponseSchema, many=False, required=True, allow_none=False)
#     services = fields.Nested(ReportCostConsumeServiceContainerResponseSchema, many=True, allow_none=False)
#     amount = fields.Float(required=True)
#     credit_summary = fields.Nested(ReportCostCreditResponseSchema, required=True, many=False, allow_none=False)
#
#
# class ReportCostConsumeResponseSchema(Schema):
#     reports = fields.Nested(CompleteReportCostConsumeItemResponseSchema, many=False, required=True, allow_none=True)
#
#
# class ReportCostConsumes(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'ReportCostConsumeRequestSchema': ReportCostConsumeRequestSchema,
#         'ReportCostConsumeResponseSchema': ReportCostConsumeResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(ReportCostConsumeRequestSchema)
#     parameters_schema = ReportCostConsumeRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ReportCostConsumeResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         Report Cost Consume for an account
#         Call this api to list all the cost and consume for an account
#         """
#
#         year_month = data.get('year_month', None)
#         start_date = data.get('start_date', None)
#         end_date = data.get('end_date', None)
#         report_mode = data.get('report_mode')
#
#         account = controller.get_account(oid, filter_expired=False)
#         res = account.get_report_costconsume(year_month, start_date, end_date, report_mode)
#
#         resp = {'reports': res}
#         return resp
#
#
# class SetReportedMonthCostConsumesRsponseSchema(CrudApiObjectResponseSchema):
#     updated = fields.Integer(required=True, description='records updated')
#
#
# class SetReportedMonthCostConsumesRequestSchema(Schema):
#     month = fields.String(required=True, description='month as 2018-11', context='request')
#
#
# class SetReportedMonthCostConsumesBodyRequestSchema(GetApiObjectRequestSchema):
#     body = fields.Nested(SetReportedMonthCostConsumesRequestSchema, context='body')
#
#
# class SetReportedMonthCostConsumes(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'SetReportedMonthCostConsumesRequestSchema': SetReportedMonthCostConsumesRequestSchema,
#         'SetReportedMonthCostConsumesRsponseSchema': SetReportedMonthCostConsumesRsponseSchema
#     }
#     parameters = SwaggerHelper().get_parameters(SetReportedMonthCostConsumesBodyRequestSchema)
#     parameters_schema = SetReportedMonthCostConsumesRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': SetReportedMonthCostConsumesRsponseSchema
#         }
#     })
#
#     def put(self, controller, data, oid, *args, **kwargs):
#         """
#             Update a applied bundle object for an account object
#             Call this api to update a applied bundle for an accolunt object
#         """
#         year_month = data.get('month')
#         account = controller.get_account(oid)
#         first_month_str = '%s-01' % year_month
#         last_month = parse('%s-01' % year_month) + relativedelta.relativedelta(months=1) - relativedelta.relativedelta(
#             days=1)
#         last_month_str = format_date(last_month, '%Y-%m-%d')
#
#         if data.get('reported'):
#             resp = controller.set_reported_reportcosts(account.oid, period_start=first_month_str,
#                                                        period_end=last_month_str)
#         else:
#             resp = controller.set_unreported_reportcosts(account.oid, period_start=first_month_str,
#                                                          period_end=last_month_str)
#         return {'uuid': account.uuid, 'updated': resp}, 200
#
#
# class ReportCostsAccountRequestSchema(GetApiObjectRequestSchema):
#     year = fields.String(required=True, context='query', example='2018', description='year filter')
#
#
# class ReportCostsAccountResponseSchema(Schema):
#     name = fields.String(required=False, description='Account name')
#     uuid = fields.String(required=False, example='4cdf0ea4-159a-45aa-96f2-708e461130e1',
#                          description='Account uuid')
#     cost_tot = fields.Float(required=True)
#     cost_reported = fields.Float(required=True)
#     cost_unreported = fields.Float(required=True)
#     extraction_date = fields.DateTime(required=True)
#
#
# class ListCostsAccountResponseSchema(Schema):
#     costs = fields.Nested(ReportCostsAccountResponseSchema, many=False, required=True, allow_none=False)
#
#
# class CostsAccount(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'ListCostsAccountResponseSchema': ListCostsAccountResponseSchema,
#         'ReportCostsAccountRequestSchema': ReportCostsAccountRequestSchema
#     }
#     parameters = SwaggerHelper().get_parameters(ReportCostsAccountRequestSchema)
#     parameters_schema = ReportCostsAccountRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ListCostsAccountResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         Report Cost Consume for an account
#         Call this api to list all the cost and consume for an account
#         """
#         year = data.get('year')
#         account = controller.get_account(oid)
#
#         first_year_str = '%s-01-01' % year
#         last_year_str = '%s-12-01' % year
#
#         name = ''
#         uuid = ''
#         imp_rendicontato = 0.0
#         imp_non_rendicontato = 0.0
#         if account is not None:
#             name = account.name
#             uuid = account.uuid
#
#             imp_rendicontato = controller.get_cost_by_account_on_period(account.oid, first_year_str, last_year_str,
#                                                                         reported=True)
#             imp_non_rendicontato = controller.get_cost_by_account_on_period(account.oid, first_year_str, last_year_str,
#                                                                             reported=False)
#
#         imp_totale = imp_rendicontato + imp_non_rendicontato
#
#         res = {
#             'name': name,
#             'uuid': uuid,
#             'extraction_date': format_date(date.today()),
#             'cost_tot': imp_totale,
#             'cost_reported': imp_rendicontato,
#             'cost_unreported': imp_non_rendicontato
#         }
#
#         resp = {'costs': res}
#         return resp


class AccountCostAPI(ApiView):
    """ServiceInstance api routes:
    """

    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/accounts/<oid>/costs' % base, 'GET', ListReportCost, {}),
            ('%s/accounts/<oid>/cost/<rid>' % base, 'GET', GetReportCost, {}),
            # ('%s/accounts/<oid>/report_cost' % base, 'POST', CreateReportCost, {}),
            # ('%s/accounts/<oid>/report_cost/<rid>' % base, 'PUT', UpdateReportCost, {}),
            # ('%s/accounts/<oid>/report_cost/<rid>' % base, 'DELETE', DeleteReportCost, {}),
            # ('%s/accounts/<oid>/report_costs/monthly/<period>' % base, 'GET', ListReportCostMontly, {}),

            # ('%s/accounts/<oid>/costs/report' % base, 'GET', ReportCostConsumes, {}),
            # ('%s/accounts/<oid>/costs/reported' % base, 'PUT', SetReportedMonthCostConsumes, {'reported': True}),
            # ('%s/accounts/<oid>/costs/unreported' % base, 'PUT', SetReportedMonthCostConsumes, {'reported': False}),
            # ('%s/accounts/<oid>/costs/year_summary' % base, 'GET', CostsAccount, {}),

        ]

        ApiView.register_api(module, rules, **kwargs)
