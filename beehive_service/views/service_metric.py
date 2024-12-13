# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import (
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    SwaggerApiView,
    ApiView,
    ApiObjectResponseDateSchema,
)
from flasgger import fields, Schema, ValidationError
from beecell.swagger import SwaggerHelper
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectResponseSchema,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
)
from marshmallow.validate import OneOf
from marshmallow.decorators import validates_schema
from beecell.simple import format_date
from beehive_service.controller import ApiAccount, ServiceController
from beehive.common.task_v2 import prepare_or_run_task
from datetime import datetime
from beehive_service.model.service_metric_type import ServiceMetricType, MetricType
from beehive_service.model.service_metric_type_limit import ServiceMetricTypeLimit
from beehive_service.model.base import SrvStatusType
from beehive.common.assert_util import AssertUtil
from beehive_service.service_util import __SRV_METRICTYPE__


# # get
class GetServiceMetricParamsResponseSchema(Schema):
    id = fields.Integer(required=True, example=10)
    value = fields.Float(required=True)
    metric_type = fields.String(required=True)
    metric_num = fields.Integer(required=True)
    service_instance_id = fields.Integer(required=True)
    job_id = fields.Integer(required=False)
    date = fields.Nested(ApiObjectResponseDateSchema, required=True)


class GetServiceMetricResponseSchema(Schema):
    metric = fields.Nested(GetServiceMetricParamsResponseSchema, required=True, allow_none=True)


class GetServiceMetric(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceMetricResponseSchema": GetServiceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetServiceMetricResponseSchema}})
    response_schema = GetServiceMetricResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        metric = controller.get_service_metric(oid)
        return {"metric": GetServiceMetric.metric_info(metric)}

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
            "id": model.id,
            "value": model.value,
            "metric_num": model.metric_num,
            "metric_type": model.metric_type.name,
            "service_instance_id": model.service_instance_id,
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


# # list
class ListServiceMetricRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    metric_type = fields.String(required=False, context="query")
    metric_num = fields.Integer(required=False, context="query")
    service_instance_id = fields.Integer(required=False, context="query")
    job_id = fields.Integer(required=False, context="query")
    creation_date = fields.DateTime(required=False, context="query")


class ListServiceMetricResponseSchema(PaginatedResponseSchema):
    metrics = fields.Nested(GetServiceMetricParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceMetric(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceMetricResponseSchema": ListServiceMetricResponseSchema,
        "ListServiceMetricRequestSchema": ListServiceMetricRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceMetricRequestSchema)
    parameters_schema = ListServiceMetricRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceMetricResponseSchema}}
    )
    response_schema = ListServiceMetricResponseSchema

    def get(self, controller, data, *args, **kwargs):
        service_metric, total = controller.get_service_metrics(**data)
        res = [GetServiceMetric.metric_info(metric) for metric in service_metric]
        res_dict = self.format_paginated_response(res, "metrics", total, **data)
        return res_dict


# # create
class CreateServiceMetricParamRequestSchema(Schema):
    # value = fields.Float(required=True)
    # metric_type_id = fields.Integer(required=True)
    # metric_num = fields.Integer(required=True)
    # service_instance_oid = fields.String(required=True)
    # job_id = fields.Integer(required=True)
    # creation_date = fields.DateTime(required=True)
    value = fields.Float(required=True, allow_none=True, description="Value of the metrics")
    metric_type_id = fields.Integer(
        required=False,
        allow_none=True,
        missing=None,
        description="metric numeric id equivalent to metric_type One of metric_type_id or metric_type is required",
    )
    metric_type = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="metric name equvalent to metric_type_id One of metric_type_id or metric_type is required",
    )
    metric_num = fields.Integer(
        required=False,
        allow_none=True,
        missing=None,
        description="daily acquistion number",
    )
    service_instance_oid = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="service instance which generate the metrics. One of service_instance_oid or resource_uuid is required",
    )
    resource_uuid = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="resource uuid which generate the metric. One of service_instance_oid or resource_uuid is required",
    )
    job_id = fields.Integer(required=False, description="job acquisition number deprecated")
    creation_date = fields.DateTime(
        required=False,
        allow_none=True,
        missing=None,
        description="creation date if not presente curtrente timestamp will be used",
    )

    @validates_schema
    def validate_schema_func(self, data: dict, *args, **kvargs):
        if (data.get("metric_type_id", None) is None) and (data.get("metric_type", None) is None):
            raise ValidationError("One of metric_type_id or metric_type is required")
        if (data.get("service_instance_oid", None) is None) and (data.get("resource_uuid", None) is None):
            raise ValidationError("One of service_instance_oid or resource_uuid is required")


class CreateServiceMetricRequestSchema(Schema):
    account = fields.String(
        required=False, allow_none=True, missing=None, description="account only when bulk inserting"
    )
    metrics = fields.Nested(
        CreateServiceMetricParamRequestSchema, required=False, allow_none=True, missing=None, context="body", many=True
    )
    metric = fields.Nested(
        CreateServiceMetricParamRequestSchema, required=False, allow_none=True, missing=None, context="body", many=False
    )

    @validates_schema
    def validate_schema_func(self, data: dict, *args, **kvargs):
        if (data.get("metrics", None) is None) and (data.get("metric", None) is None):
            raise ValidationError("One of metrics or metric is required")


class CreateServiceMetricBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceMetricRequestSchema, context="body")


class CreateServiceMetricResponseSchema(Schema):
    id = fields.Integer(required=True)


class CreateServiceMetric(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateServiceMetricRequestSchema": CreateServiceMetricRequestSchema,
        "CreateServiceMetricResponseSchema": CreateServiceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceMetricBodyRequestSchema)
    parameters_schema = CreateServiceMetricRequestSchema
    responses = ServiceApiView.setResponses(
        {201: {"description": "success", "schema": CreateServiceMetricResponseSchema}}
    )
    response_schema = CreateServiceMetricResponseSchema

    def post(self, controller, data, *args, **kwargs):
        # data = data.get("metric")
        from beehive_service.controller import ServiceController

        ctrl: ServiceController = controller
        resp = ctrl.add_service_metrics(data)
        return ({"id": resp}, 201)


# # acquire metric
class AcquireServiceMetricParamRequestSchema(Schema):
    account_id = fields.String(required=False, allow_none=True)
    metric_type_id = fields.Integer(required=False, allow_none=True)
    service_instance_id = fields.String(required=False, allow_none=True)


class AcquireServiceMetricRequestSchema(Schema):
    acquire_metric = fields.Nested(AcquireServiceMetricParamRequestSchema, context="body")


class AcquireServiceMetricBodyRequestSchema(Schema):
    body = fields.Nested(AcquireServiceMetricRequestSchema, context="body")


class AcquireServiceMetricResponseSchema(Schema):
    job_id = fields.String(required=True)


class AcquireServiceMetric(ServiceApiView):
    tags = ["service"]
    definitions = {
        "AcquireServiceMetricRequestSchema": AcquireServiceMetricRequestSchema,
        "AcquireServiceMetricResponseSchema": AcquireServiceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(AcquireServiceMetricBodyRequestSchema)
    parameters_schema = AcquireServiceMetricRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "success", "schema": AcquireServiceMetricResponseSchema}}
    )
    response_schema = AcquireServiceMetricResponseSchema

    def post(self, controller, data, *args, **kwargs):
        params = data.get("acquire_metric", {})
        params["steps"] = []
        #  metric_type_id    account_id  service_instance_id

        # ensure that service_instance_id is the int id not uuid
        controller.resolve_fk_id(
            "service_instance_id",
            controller.get_service_instance,
            params,
            new_key="service_instance_id",
        )
        oid = params.pop("account_id", None)
        account: ApiAccount = None
        account_objid: str
        if oid is not None:
            account = controller.get_account(oid)
            account_objid = account.objid
        else:
            account = ApiAccount(controller)
            account_objid = None
        params["objid"] = account_objid
        params["oid"] = account.oid
        task, status = prepare_or_run_task(
            account,
            "beehive_service.task_v2.metrics.acquire_metric_task",
            params,
            sync=False,
        )
        self.logger.info("Start job job_acquire_service_metrics {}".format(task))

        return {"job_id": task["taskid"]}, status


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
    body = fields.Nested(DeleteServiceMetricRequestSchema, context="body")


class DeleteServiceMetricResponseSchema(Schema):
    deleted = fields.Integer(required=True, allow_none=True)


class DeleteServiceMetric(ServiceApiView):
    tags = ["service"]
    definitions = {
        "DeleteServiceMetricRequestSchema": DeleteServiceMetricRequestSchema,
        "DeleteServiceMetricResponseSchema": DeleteServiceMetricResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteServiceMetricBodyRequestSchema)
    parameters_schema = DeleteServiceMetricRequestSchema
    responses = ServiceApiView.setResponses(
        {
            204: {
                "description": "no response",
                "schema": DeleteServiceMetricResponseSchema,
            }
        }
    )
    response_schema = DeleteServiceMetricResponseSchema

    @transaction
    def delete(self, controller, data, *args, **kwargs):
        resp = controller.delete_service_metric(**data.get("metric"))

        return {"deleted": resp.id}, 204


###########  ServiceMetricsType   ##############
class ServiceMetricTypeLimitParamRequestSchema(Schema):
    name = fields.String(
        required=True,
        example="vpc-bundle-bronze",
        description="service metrics type limit name",
    )
    desc = fields.String(
        required=False,
        example="vpc bundle bronze",
        default="",
        missing="",
        allow_none=True,
        description="service metrics type limit description",
    )
    value = fields.Float(required=True, example="0.00", description="service metrics type limit value")
    metric_type_id = fields.String(required=True, example="10", description="service metrics type id")


# # create
class CreateServiceMetricTypeParamRequestSchema(Schema):
    name = fields.String(required=True, example="GBRam", description="service metrics type name")
    desc = fields.String(
        required=False,
        example="Gb Ram",
        default="",
        missing="",
        allow_none=True,
        description="service metrics type description",
    )
    metric_type = fields.String(
        required=True,
        example="BUNDLE",
        validate=OneOf(__SRV_METRICTYPE__),
        description="service metrics type description. Can be one of the following value: "
        "CONSUME|BUNDLE|OPTIONAL_BUNDLE|PROFESSIONAL_SERVICE|UNKNOWN",
    )
    group_name = fields.String(
        required=False,
        example="cpaas",
        default="UNKNOWN",
        missing="UNKNOWN",
        description="service metrics type group",
    )
    measure_unit = fields.String(
        required=False,
        example="Gb",
        default="None",
        missing="None",
        description="service metrics type unit",
    )
    limits = fields.Nested(
        ServiceMetricTypeLimitParamRequestSchema,
        required=False,
        many=True,
        allow_none=True,
    )
    status = fields.String(
        required=False,
        example="ACTIVE",
        default="DRAFT",
        missing="DRAFT",
        description="service metrics type status: ACTIVE|DRAFT",
    )


class CreateServiceMetricTypeRequestSchema(Schema):
    metric_type = fields.Nested(CreateServiceMetricTypeParamRequestSchema, context="body")


class CreateServiceMetricTypeBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceMetricTypeRequestSchema, context="body")


class CreateServiceMetricTypeResponseSchema(Schema):
    id = fields.Integer(required=True)


class CreateServiceMetricType(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateServiceMetricTypeRequestSchema": CreateServiceMetricTypeRequestSchema,
        "CreateServiceMetricTypeResponseSchema": CreateServiceMetricTypeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceMetricTypeBodyRequestSchema)
    parameters_schema = CreateServiceMetricTypeRequestSchema
    responses = ServiceApiView.setResponses(
        {
            201: {
                "description": "success",
                "schema": CreateServiceMetricTypeResponseSchema,
            }
        }
    )
    response_schema = CreateServiceMetricTypeResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        """ """

        data = data.get("metric_type")
        limits = data.pop("limits", [])

        uuid = controller.add_service_metric_type(limits=limits, **data)
        return {"uuid": uuid}, 201


# # get
class GetServiceMetricTypeLimitParamsResponseSchema(Schema):
    id = fields.Integer(required=True, example="1", description="service metrics type limit id")
    name = fields.String(
        required=True,
        example="vpc-bundle-bronze",
        description="service metrics type limit name",
    )
    desc = fields.String(
        required=False,
        example="vpc bundle bronze",
        default="",
        missing="",
        description="service metrics type limit description",
    )
    value = fields.Float(required=True, example="0.00", description="service metrics type limit value")
    metric_type_id = fields.String(required=True, example="10", description="service metrics type id")


class GetServiceMetricTypeParamsResponseSchema(ApiServiceObjectResponseSchema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    group_name = fields.String(required=False)
    metric_type = fields.String(required=True)
    desc = fields.String(required=False)
    measure_unit = fields.String(required=False)
    limits = fields.Nested(
        GetServiceMetricTypeLimitParamsResponseSchema,
        required=False,
        many=True,
        allow_none=True,
    )


class GetServiceMetricTypeResponseSchema(Schema):
    metric_type = fields.Nested(GetServiceMetricTypeParamsResponseSchema, required=True, allow_none=True)


class GetServiceMetricType(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceMetricTypeResponseSchema": GetServiceMetricTypeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceMetricTypeResponseSchema}}
    )
    response_schema = GetServiceMetricTypeResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        mt = controller.get_service_metric_type(oid)
        res = {"metric_type": GetServiceMetricType.metric_type_info(mt)}
        return res

    @staticmethod
    def metric_type_limit_info(mtl):
        return {
            "id": mtl.id,
            "name": mtl.name,
            "desc": mtl.desc,
            "value": mtl.value,
            "parent_id": mtl.parent_id,
            "metric_type_id": mtl.metric_type_id,
        }

    @staticmethod
    def metric_type_info(mt):
        mtls_info = []
        for mtl in mt.limits:
            mtls_info.append(GetServiceMetricType.metric_type_limit_info(mtl))

        mt_detail = mt.detail()
        mt_detail["limits"] = mtls_info

        return mt_detail


# # list
class ListServiceMetricTypeRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    group_name = fields.String(Required=False, context="query")
    metric_type = fields.String(Required=False, context="query")
    status = fields.String(Required=False, context="query")


class ListServiceMetricTypeResponseSchema(Schema):
    metric_types = fields.Nested(
        GetServiceMetricTypeParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListServiceMetricType(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceMetricTypeResponseSchema": ListServiceMetricTypeResponseSchema,
        "ListServiceMetricTypeRequestSchema": ListServiceMetricTypeRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceMetricTypeRequestSchema)
    parameters_schema = ListServiceMetricTypeRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceMetricTypeResponseSchema}}
    )
    response_schema = ListServiceMetricTypeResponseSchema

    def get(self, controller, data, *args, **kwargs):
        metric_types, total = controller.get_paginated_service_metric_type(**data)
        res = [GetServiceMetricType.metric_type_info(r) for r in metric_types]
        return self.format_paginated_response(res, "metric_types", total, **data)


# # update
class UpdateServiceMetricTypeLimitParamRequestSchema(Schema):
    name = fields.String(
        required=False,
        example="vpc-bundle-bronze",
        description="service metrics type limit name",
    )
    desc = fields.String(
        required=False,
        example="vpc bundle bronze",
        default="",
        missing="",
        description="service metrics type limit description",
    )
    value = fields.Float(required=False, example="0.00", description="service metrics type limit value")
    metric_type_id = fields.String(required=True, example="10", description="service metrics type id")


class UpdateServiceMetricTypeParamRequestSchema(Schema):
    name = fields.String(required=False, example="GBRam", description="service metrics type name")
    desc = fields.String(required=False, example="Gb Ram", description="service metrics type description")
    metric_type = fields.String(
        required=False,
        example="BUNDLE",
        validate=OneOf(__SRV_METRICTYPE__),
        description="service metrics type description. Can be one of the following value: "
        "CONSUME|BUNDLE|OPT_BUNDLE|PROF_SERVICE|UNKNOWN",
    )
    status = fields.String(
        required=False,
        example="DRAFT",
        description="service metrics type status. Status can be " "one of the following value: DRAFT|ACTIVE",
    )
    group_name = fields.String(required=False, example="cpaas", description="service metrics type group")
    measure_unit = fields.String(required=False, example="Gb", description="service metrics type unit")
    limits = fields.Nested(
        UpdateServiceMetricTypeLimitParamRequestSchema,
        required=False,
        many=True,
        allow_none=True,
    )


class UpdateServiceMetricTypeRequestSchema(Schema):
    metric_type = fields.Nested(UpdateServiceMetricTypeParamRequestSchema)


class UpdateServiceMetricTypeBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceMetricTypeRequestSchema, context="body")


class UpdateServiceMetricType(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateServiceMetricTypeRequestSchema": UpdateServiceMetricTypeRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceMetricTypeBodyRequestSchema)
    parameters_schema = UpdateServiceMetricTypeRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller: ServiceController, data, oid, *args, **kvargs):
        resp = controller.update_service_metric_type(oid, data)
        return {"uuid": resp}, 200


# # delete
class DeleteServiceMetricType(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller: ServiceController, data, oid, *args, **kwargs):
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
    metrics = fields.Nested(
        GetInstantConsumeServiceParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class GetInstantConsumeServiceResponseSchema(Schema):
    data = fields.Nested(GetInstantConsumeService1ResponseSchema, required=True)


class GetInstantConsumeServiceRequestSchema(GetApiObjectRequestSchema):
    extraction_date = fields.DateTime(required=False, context="query")


class GetInstantConsumeService(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetInstantConsumeServiceResponseSchema": GetInstantConsumeServiceResponseSchema,
        "GetInstantConsumeServiceRequestSchema": GetInstantConsumeServiceRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetInstantConsumeServiceRequestSchema)
    parameters_schema = GetInstantConsumeServiceRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetInstantConsumeServiceResponseSchema,
            }
        }
    )
    response_schema = GetInstantConsumeServiceResponseSchema

    def get(self, controller, dummydata, oid, *args, **kwargs):
        request_date = format_date(datetime.today())
        data = controller.get_service_instantconsume(oid, request_date)
        res_dict = {"data": data}
        return res_dict


class ServiceMetricAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/services/metrics" % base, "GET", ListServiceMetric, {}),
            ("%s/services/metrics" % base, "POST", CreateServiceMetric, {}),
            ("%s/services/metrics/<oid>" % base, "GET", GetServiceMetric, {}),
            ("%s/services/metrics" % base, "DELETE", DeleteServiceMetric, {}),
            ("%s/services/metrics/acquire" % base, "POST", AcquireServiceMetric, {}),
            # (u'%s/services/metrics/quota' % base, u'POST', AcquireQuotaServiceMetric, {}),
            (
                "%s/services/metrics/<oid>/instantconsume" % base,
                "GET",
                GetInstantConsumeService,
                {},
            ),
            ("%s/services/metricstypes" % base, "GET", ListServiceMetricType, {}),
            ("%s/services/metricstypes" % base, "POST", CreateServiceMetricType, {}),
            ("%s/services/metricstypes/<oid>" % base, "GET", GetServiceMetricType, {}),
            (
                "%s/services/metricstypes/<oid>" % base,
                "PUT",
                UpdateServiceMetricType,
                {},
            ),
            (
                "%s/services/metricstypes/<oid>" % base,
                "DELETE",
                DeleteServiceMetricType,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
