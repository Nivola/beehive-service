# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import  PaginatedRequestQuerySchema, PaginatedResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema, SwaggerApiView, ApiView, ApiObjectResponseDateSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectResponseSchema, \
    ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema
from marshmallow.validate import OneOf
from beecell.simple import format_date
from beehive_service.controller import ApiAccount
from beehive.common.task_v2 import prepare_or_run_task
from datetime import datetime
from beehive_service.model.service_metric_type import ServiceMetricType, MetricType
from beehive_service.model.service_metric_type_limit import  ServiceMetricTypeLimit
from beehive_service.model.base import  SrvStatusType
from beehive.common.assert_util import AssertUtil
from beehive_service.service_util import __SRV_METRICTYPE__


# # get
class GetServiceMetricParamsResponseSchema(Schema):
    id = fields.Integer(required=True,  example=10)
    value = fields.Float(required=True)
    metric_type = fields.String(required=True)
    metric_num = fields.Integer(required=True)
    service_instance_id = fields.Integer(required=True)
    job_id = fields.Integer(required=False)
    date = fields.Nested(ApiObjectResponseDateSchema, required=True)


class GetServiceMetricResponseSchema(Schema):
    metric = fields.Nested(GetServiceMetricParamsResponseSchema, required=True, allow_none=True)


class GetServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServiceMetricResponseSchema': GetServiceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServiceMetricResponseSchema
        }
    })
    response_schema = GetServiceMetricResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        metric = controller.get_service_metric(oid)
        return {u'metric':GetServiceMetric.metric_info(metric)}

    @staticmethod
    def metric_info(model):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if model is None:
            return None

        info = {
            u'id': model.id,
            u'value' : model.value,
            u'metric_num' : model.metric_num,
            u'metric_type' : model.metric_type.name,
            u'service_instance_id' : model.service_instance_id,
            u'job_id' : model.job_id,
            u'date': {
                u'creation': format_date(model.creation_date),
                u'modified': format_date(model.modification_date),
                u'expiry': u''
                }
            }
        if model.expiry_date is not None:
            info[u'date'][u'expiry'] = format_date(model.expiry_date)
        return info


# # list
class ListServiceMetricRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                     PaginatedRequestQuerySchema):
    metric_type = fields.String(required=False, context=u'query')
    metric_num = fields.Integer(required=False, context=u'query')
    service_instance_id = fields.Integer(required=False, context=u'query')
    job_id = fields.Integer(required=False, context=u'query')
    creation_date = fields.DateTime(required=False, context=u'query')


class ListServiceMetricResponseSchema(PaginatedResponseSchema):
    metrics = fields.Nested(GetServiceMetricParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServiceMetricResponseSchema': ListServiceMetricResponseSchema,
        u'ListServiceMetricRequestSchema': ListServiceMetricRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServiceMetricRequestSchema)
    parameters_schema = ListServiceMetricRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServiceMetricResponseSchema
        }
    })
    response_schema = ListServiceMetricResponseSchema

    def get(self, controller, data, *args, **kwargs):
        service_metric, total = controller.get_service_metrics(**data)
        res = [GetServiceMetric.metric_info(metric) for metric in service_metric]
        res_dict = self.format_paginated_response(res, u'metrics', total, **data)
        return res_dict


# # create
class CreateServiceMetricParamRequestSchema(Schema):
    value = fields.Float(required=True)
    metric_type_id = fields.Integer(required=True)
    metric_num = fields.Integer(required=True)
    service_instance_oid = fields.String(required=True)
    job_id = fields.Integer(required=True)
    creation_date = fields.DateTime(required=True)


class CreateServiceMetricRequestSchema(Schema):
    metric = fields.Nested(CreateServiceMetricParamRequestSchema, context=u'body')


class CreateServiceMetricBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceMetricRequestSchema, context=u'body')


class CreateServiceMetricResponseSchema(Schema):
    id = fields.Integer(required=True)


class CreateServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateServiceMetricRequestSchema': CreateServiceMetricRequestSchema,
        u'CreateServiceMetricResponseSchema':CreateServiceMetricResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceMetricBodyRequestSchema)
    parameters_schema = CreateServiceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateServiceMetricResponseSchema
        }
    })
    response_schema = CreateServiceMetricResponseSchema

    def post(self, controller, data, *args, **kwargs):
        data = data.get(u'metric')

        resp = controller.add_service_metric(**data)
        return ({u'id':resp}, 201)


# # acquire metric
class AcquireServiceMetricParamRequestSchema(Schema):
    account_id = fields.String(required=False, allow_none = True)
    metric_type_id = fields.Integer(required=False, allow_none = True)
    service_instance_id = fields.String(required=False, allow_none = True)


class AcquireServiceMetricRequestSchema(Schema):
    acquire_metric = fields.Nested(AcquireServiceMetricParamRequestSchema, context=u'body')


class AcquireServiceMetricBodyRequestSchema(Schema):
    body = fields.Nested(AcquireServiceMetricRequestSchema, context=u'body')


class AcquireServiceMetricResponseSchema(Schema):
    job_id = fields.String(required=True)


class AcquireServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'AcquireServiceMetricRequestSchema': AcquireServiceMetricRequestSchema,
        u'AcquireServiceMetricResponseSchema':AcquireServiceMetricResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(AcquireServiceMetricBodyRequestSchema)
    parameters_schema = AcquireServiceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        202: {
            u'description': u'success',
            u'schema': AcquireServiceMetricResponseSchema
        }
    })
    response_schema = AcquireServiceMetricResponseSchema

    def post(self, controller, data, *args, **kwargs):
        params = data.get(u'acquire_metric', {})
        params['steps'] = []
        #  metric_type_id    account_id  service_instance_id

        # ensure that service_instance_id is the int id not uuid
        controller.resolve_fk_id(u'service_instance_id', controller.get_service_instance, params,
                                 new_key=u'service_instance_id' )
        oid = params.pop(u'account_id', None)
        account: ApiAccount = None
        account_objid: str
        if oid is not None:
            account = controller.get_account(oid)
            account_objid = account.objid
        else:
            account = ApiAccount(controller)
            account_objid = None
        params['objid'] = account_objid
        params['oid'] = account.oid
        # from beehive_service.task_v2.metrics import AcquireMetricTask
        task, status = prepare_or_run_task(
            account,
            'beehive_service.task_v2.metrics.acquire_metric_task',
            params,
            sync=False)
        self.logger.info('Start job job_acquire_service_metrics {}'.format(task) )

        return {'job_id': task['taskid']}, status


# # acquire quota
"""
class AcquireQuotaServiceMetricParamRequestSchema(Schema):
    account_id = fields.String(required=False, allow_none = True)
    service_instance_id = fields.String(required=False, allow_none = True)


class AcquireQuotaServiceMetricRequestSchema(Schema):
    acquire_quota = fields.Nested(AcquireQuotaServiceMetricParamRequestSchema, context=u'body')


class AcquireQuotaServiceMetricBodyRequestSchema(Schema):
    body = fields.Nested(AcquireQuotaServiceMetricRequestSchema, context=u'body')


class AcquireQuotaServiceMetricResponseSchema(Schema):
    job_id = fields.String(required=True)


class AcquireQuotaServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'AcquireQuotaServiceMetricRequestSchema': AcquireQuotaServiceMetricRequestSchema,
        u'AcquireQuotaServiceMetricResponseSchema':AcquireQuotaServiceMetricResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(AcquireQuotaServiceMetricBodyRequestSchema)
    parameters_schema = AcquireQuotaServiceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': AcquireQuotaServiceMetricResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        params = data.get(u'acquire_quota')
        controller.resolve_fk_id(u'service_instance_id', controller.get_service_instance, params,
                                 new_key=u'service_instance_id' )
        oid = params.get(u'account_id', None)
        account = None
        if oid is not None:
            account = controller.get_account(oid)
            account_objid = account.objid
        else:
            account = ApiAccount(controller)
            account_objid = None

        task = signature(u'beehive_service.task.metrics.acquire_service_quotas', (account_objid, params),
                         app=task_manager, queue=account.celery_broker_queue)
        self.logger.info(u'task created %s' % task)

        job = task.apply_async()
        self.logger.info(u'Start job job_acquire_service_quotas %s' % job.id)

        return {u'job_id': job.id}, 201
"""


class DeleteServiceMetricParamRequestSchema(Schema):
    metric_oid = fields.String(required=False)
    metric_type_id = fields.Integer(required=False)
    metric_num = fields.Integer(required=False)
    service_instance_oid = fields.String(required=False)
    job_id = fields.String(required=False)
    start_date = fields.DateTime(required=False)
    end_date = fields.DateTime(required=False)


class DeleteServiceMetricRequestSchema(Schema):
    metric = fields.Nested(DeleteServiceMetricParamRequestSchema)


class DeleteServiceMetricBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteServiceMetricRequestSchema, context=u'body')


class DeleteServiceMetricResponseSchema(Schema):
    deleted = fields.Integer(required=True, allow_none=True)


class DeleteServiceMetric(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'DeleteServiceMetricRequestSchema':DeleteServiceMetricRequestSchema,
        u'DeleteServiceMetricResponseSchema':DeleteServiceMetricResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteServiceMetricBodyRequestSchema)
    parameters_schema = DeleteServiceMetricRequestSchema
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response',
            u'schema': DeleteServiceMetricResponseSchema
        }
    })
    response_schema = DeleteServiceMetricResponseSchema

    @transaction
    def delete(self, controller, data, *args, **kwargs):
        resp = controller.delete_service_metric(**data.get(u'metric'))

        return {u'deleted': resp.id}, 204


###########  ServiceMetricsType   ##############
class ServiceMetricTypeLimitParamRequestSchema(Schema):
    name = fields.String(required=True, example=u'vpc-bundle-bronze',  description=u'service metrics type limit name')
    desc = fields.String(required=False, example=u'vpc bundle bronze', default=u'', missing=u'', allow_none=True,
                         description=u'service metrics type limit description')
    value = fields.Float(required=True, example=u'0.00', description=u'service metrics type limit value')
    metric_type_id = fields.String(required=True, example=u'10', description=u'service metrics type id')


# # create
class CreateServiceMetricTypeParamRequestSchema(Schema):
    name = fields.String(required=True, example=u'GBRam',  description=u'service metrics type name')
    desc = fields.String(required=False, example=u'Gb Ram', default=u'', missing=u'', allow_none=True,
                         description=u'service metrics type description')
    metric_type = fields.String(required=True, example=u'BUNDLE', validate=OneOf(__SRV_METRICTYPE__),
                                description=u'service metrics type description. Can be one of the following value: '
                                            u'CONSUME|BUNDLE|OPTIONAL_BUNDLE|PROFESSIONAL_SERVICE|UNKNOWN')
    group_name = fields.String(required=False, example=u'cpaas', default=u'UNKNOWN', missing=u'UNKNOWN',
                               description=u'service metrics type group')
    measure_unit = fields.String(required=False, example=u'Gb', default=u'None', missing=u'None',
                                 description=u'service metrics type unit')
    limits = fields.Nested(ServiceMetricTypeLimitParamRequestSchema, required=False, many=True, allow_none=True)
    status = fields.String(required=False, example=u'ACTIVE', default=u'DRAFT', missing=u'DRAFT',
                           description=u'service metrics type status: ACTIVE|DRAFT')


class CreateServiceMetricTypeRequestSchema(Schema):
    metric_type = fields.Nested(CreateServiceMetricTypeParamRequestSchema, context=u'body')


class CreateServiceMetricTypeBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceMetricTypeRequestSchema, context=u'body')


class CreateServiceMetricTypeResponseSchema(Schema):
    id = fields.Integer(required=True)


class CreateServiceMetricType(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateServiceMetricTypeRequestSchema': CreateServiceMetricTypeRequestSchema,
        u'CreateServiceMetricTypeResponseSchema':CreateServiceMetricTypeResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceMetricTypeBodyRequestSchema)
    parameters_schema = CreateServiceMetricTypeRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateServiceMetricTypeResponseSchema
        }
    })
    response_schema = CreateServiceMetricTypeResponseSchema

    def post(self, controller, data, *args, **kwargs):
        '''
        '''

        data = data.get(u'metric_type')
        limits = data.pop(u'limits', [])

        uuid = controller.add_service_metric_type(limits=limits, **data)
        return {u'uuid':uuid}, 201


# # get
class GetServiceMetricTypeLimitParamsResponseSchema (Schema):
    id = fields.Integer(required=True, example=u'1',  description=u'service metrics type limit id')
    name = fields.String(required=True, example=u'vpc-bundle-bronze',  description=u'service metrics type limit name')
    desc = fields.String(required=False, example=u'vpc bundle bronze', default=u'', missing=u'',
                         description=u'service metrics type limit description')
    value = fields.Float(required=True, example=u'0.00', description=u'service metrics type limit value')
    metric_type_id = fields.String(required=True, example=u'10', description=u'service metrics type id')


class GetServiceMetricTypeParamsResponseSchema(ApiServiceObjectResponseSchema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    group_name = fields.String(required=False)
    metric_type = fields.String(required=True)
    desc = fields.String(required=False)
    measure_unit = fields.String(required=False)
    limits = fields.Nested(GetServiceMetricTypeLimitParamsResponseSchema, required=False, many=True, allow_none=True)


class GetServiceMetricTypeResponseSchema(Schema):
    metric_type = fields.Nested(GetServiceMetricTypeParamsResponseSchema, required=True, allow_none=True)


class GetServiceMetricType(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServiceMetricTypeResponseSchema': GetServiceMetricTypeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServiceMetricTypeResponseSchema
        }
    })
    response_schema = GetServiceMetricTypeResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        mt = controller.get_service_metric_type(oid)
        res = {u'metric_type': GetServiceMetricType.metric_type_info(mt)}
        return res

    @staticmethod
    def metric_type_limit_info(mtl):
        return {
            u'id': mtl.id,
            u'name': mtl.name,
            u'desc': mtl.desc,
            u'value': mtl.value,
            u'parent_id': mtl.parent_id,
            u'metric_type_id': mtl.metric_type_id,
        }

    @staticmethod
    def metric_type_info(mt):
        mtls_info = []
        for mtl in mt.limits:
            mtls_info.append(GetServiceMetricType.metric_type_limit_info(mtl))

        mt_detail = mt.detail()
        mt_detail[u'limits'] = mtls_info

        return mt_detail


# # list
class ListServiceMetricTypeRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                         PaginatedRequestQuerySchema):
    group_name = fields.String(Required=False, context=u'query')
    metric_type = fields.String(Required=False, context=u'query')
    status = fields.String(Required=False, context=u'query')


class ListServiceMetricTypeResponseSchema(Schema):
    metric_types = fields.Nested(GetServiceMetricTypeParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceMetricType(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServiceMetricTypeResponseSchema': ListServiceMetricTypeResponseSchema,
        u'ListServiceMetricTypeRequestSchema': ListServiceMetricTypeRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListServiceMetricTypeRequestSchema)
    parameters_schema = ListServiceMetricTypeRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServiceMetricTypeResponseSchema
        }
    })
    response_schema = ListServiceMetricTypeResponseSchema

    def get(self, controller, data, *args, **kwargs):
        metric_types, total = controller.get_paginated_service_metric_type(**data)
        res = [GetServiceMetricType.metric_type_info(r) for r in metric_types]
        return self.format_paginated_response(res, u'metric_types', total, **data)


# # update
class UpdateServiceMetricTypeLimitParamRequestSchema(Schema):
    name = fields.String(required=False, example=u'vpc-bundle-bronze',  description=u'service metrics type limit name')
    desc = fields.String(required=False, example=u'vpc bundle bronze', default=u'', missing=u'',
                         description=u'service metrics type limit description')
    value = fields.Float(required=False, example=u'0.00', description=u'service metrics type limit value')
    metric_type_id = fields.String(required=True, example=u'10', description=u'service metrics type id')


class UpdateServiceMetricTypeParamRequestSchema(Schema):
    name = fields.String(required=False, example=u'GBRam',  description=u'service metrics type name')
    desc = fields.String(required=False, example=u'Gb Ram', description=u'service metrics type description')
    metric_type = fields.String(required=False, example=u'BUNDLE', validate=OneOf(__SRV_METRICTYPE__),
                                description=u'service metrics type description. Can be one of the following value: '
                                            u'CONSUME|BUNDLE|OPT_BUNDLE|PROF_SERVICE|UNKNOWN')
    status = fields.String(required=False, example=u'DRAFT',  description=u'service metrics type status. Status can be '
                                                                          u'one of the following value: DRAFT|ACTIVE')
    group_name = fields.String(required=False, example=u'cpaas', description=u'service metrics type group')
    measure_unit = fields.String(required=False, example=u'Gb', description=u'service metrics type unit')
    limits = fields.Nested(UpdateServiceMetricTypeLimitParamRequestSchema, required=False, many=True, allow_none=True)


class UpdateServiceMetricTypeRequestSchema(Schema):
    metric_type = fields.Nested(UpdateServiceMetricTypeParamRequestSchema)


class UpdateServiceMetricTypeBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceMetricTypeRequestSchema, context=u'body')


class UpdateServiceMetricType(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateServiceMetricTypeRequestSchema':UpdateServiceMetricTypeRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceMetricTypeBodyRequestSchema)
    parameters_schema = UpdateServiceMetricTypeRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kvargs):

        resp = controller.update_service_metric_type(oid, data)
        return {u'uuid': resp}, 200


# # delete
class DeleteServiceMetricType(ServiceApiView):
    tags = [u'service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete service metric type object
        Call this api to delete service metric type object.
        """

        resp = controller.delete_service_metric_type(oid)
        return resp, 204


# # Get instant consume service
class GetInstantConsumeServiceParamsResponseSchema(Schema):
    container_id = fields.String(required=True)
    metric_type_name = fields.String(Required=True)
    group_name = fields.String(Required=True)
    value = fields.Float(required=True)
    extraction_date = fields.DateTime(required=True)


class GetInstantConsumeService1ResponseSchema(Schema):
    account_id = fields.String(required=True)
    request_date = fields.DateTime(required=True)
    metrics = fields.Nested(GetInstantConsumeServiceParamsResponseSchema, many=True, required=True, allow_none=True)


class GetInstantConsumeServiceResponseSchema(Schema):
    data = fields.Nested(GetInstantConsumeService1ResponseSchema, required=True)


class GetInstantConsumeServiceRequestSchema(GetApiObjectRequestSchema):
    extraction_date = fields.DateTime(required=False, context=u'query')


class GetInstantConsumeService(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetInstantConsumeServiceResponseSchema': GetInstantConsumeServiceResponseSchema,
        u'GetInstantConsumeServiceRequestSchema': GetInstantConsumeServiceRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(GetInstantConsumeServiceRequestSchema)
    parameters_schema = GetInstantConsumeServiceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetInstantConsumeServiceResponseSchema
        }
    })
    response_schema = GetInstantConsumeServiceResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):

        request_date = format_date(datetime.today())
        data = controller.get_service_instantconsume(oid, request_date)
        res_dict = {
                u'data': data
        }
        return res_dict


class ServiceMetricAPI(ApiView):
    """ServiceInstance api routes:
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/services/metrics' % base, u'GET', ListServiceMetric, {}),
            (u'%s/services/metrics' % base, u'POST', CreateServiceMetric, {}),
            (u'%s/services/metrics/<oid>' % base, u'GET', GetServiceMetric, {}),
            (u'%s/services/metrics' % base, u'DELETE', DeleteServiceMetric, {}),
            (u'%s/services/metrics/acquire' % base, u'POST', AcquireServiceMetric, {}),
            # (u'%s/services/metrics/quota' % base, u'POST', AcquireQuotaServiceMetric, {}),
            (u'%s/services/metrics/<oid>/instantconsume' % base, u'GET', GetInstantConsumeService, {}),

            (u'%s/services/metricstypes' % base, u'GET', ListServiceMetricType, {}),
            (u'%s/services/metricstypes' % base, u'POST', CreateServiceMetricType, {}),
            (u'%s/services/metricstypes/<oid>' % base, u'GET', GetServiceMetricType, {}),
            (u'%s/services/metricstypes/<oid>' % base, u'PUT', UpdateServiceMetricType, {}),
            (u'%s/services/metricstypes/<oid>' % base, u'DELETE', DeleteServiceMetricType, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
