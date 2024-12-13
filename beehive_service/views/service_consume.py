# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import (
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    GetApiObjectRequestSchema,
    SwaggerApiView,
    ApiView,
    AuditResponseSchema,
)
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiObjectRequestFiltersSchema
from beehive_service.service_util import __AGGREGATION_COST_TYPE__
from marshmallow.validate import OneOf, Length
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from beecell.simple import format_date
from beehive.common.data import transaction
from beehive_service.controller import ApiAccount


# # get
class GetConsumeParamsResponseSchema(AuditResponseSchema):
    id = fields.Integer(Required=True)
    #     platform_id = fields.Integer(Required=True)
    type_id = fields.Integer(required=True)
    consumed = fields.Float(required=True)
    cost = fields.Float(required=True)
    service_instance_id = fields.Integer(required=True)
    aggregation_type = fields.String(Required=True)
    period = fields.String(Required=True)
    account_id = fields.Integer(Required=True)
    cost_type_id = fields.Integer(Required=True)
    cost_type_name = fields.String(Required=True)
    job_id = fields.Integer(required=False)
    evaluation_date = fields.DateTime(required=True, example="1990-12-31T23:59:59Z")

    @staticmethod
    def detail(m):
        res = {
            "id": m.id,
            # 'platform_id': m.platform_id,
            # 'platform_name': m.platform_name,
            "type_id": m.metric_type_id,
            #  'type_name': m.metric_type_name,
            "consumed": m.consumed,
            "cost": m.cost,
            "service_instance_id": m.service_instance_id,
            "account_id": m.account_id,
            "aggregation_type": m.aggregation_type,
            "period": m.period,
            "cost_type_id": m.cost_type_id,
            "cost_type_name": m.cost_type.name,
            "job_id": m.job_id,
            "evaluation_date": format_date(m.evaluation_date),
            "date": {
                "creation": format_date(m.creation_date),
                "modified": format_date(m.modification_date),
                "expiry": "",
            },
        }
        return res


class GetConsumeResponseSchema(Schema):
    consume = fields.Nested(GetConsumeParamsResponseSchema, required=True, allow_none=True)


class GetConsume(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetConsumeResponseSchema": GetConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetConsumeResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        consume = controller.get_consume(oid)
        return {"consume": GetConsumeParamsResponseSchema.detail(consume)}

    # # list


class ListConsumeRequestSchema(PaginatedRequestQuerySchema, ApiObjectRequestFiltersSchema):
    id = fields.Integer(required=False, context="query")
    metric_type_id = fields.Integer(required=False, context="query")
    instance_oid = fields.Integer(required=False, context="query")
    account_oid = fields.String(required=False)
    evaluation_date_start = fields.DateTime(required=False, context="query")
    evaluation_date_end = fields.DateTime(required=False, context="query")
    period = fields.String(required=False, context="query")
    cost_type_id = fields.Integer(required=False, context="query")
    job_id = fields.Integer(required=False, context="query")
    aggregation_type = fields.String(required=False, context="query")

    field = fields.String(
        validate=OneOf(
            ["id", "metric_type_id", "evaluation_date", "period", "cost_type_id"],
            error="Field can be id, metric_type_id, evaluation_date, period, " "cost_type_id",
        ),
        description="enitities list order field. Ex. id, platform_name",
        default="id",
        example="id",
        missing="id",
        context="query",
    )


class ListConsumeResponseSchema(PaginatedResponseSchema):
    consume = fields.Nested(GetConsumeParamsResponseSchema, many=True, required=True, allow_none=True)


class ListConsume(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListConsumeRequestSchema": ListConsumeRequestSchema,
        "ListConsumeResponseSchema": ListConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListConsumeRequestSchema)
    parameters_schema = ListConsumeRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListConsumeResponseSchema}})
    response_schema = ListConsumeResponseSchema

    def get(self, controller, data, *args, **kwargs):
        consumes, total = controller.get_paginated_aggregate_costs(**data)
        res = [GetConsumeParamsResponseSchema.detail(m) for m in consumes]
        res_dict = self.format_paginated_response(res, "consume", total, **data)
        return res_dict


class CreateConsumeParamRequestSchema(Schema):
    metric_type_id = fields.Integer(required=True)
    consumed = fields.Float(required=True)
    cost = fields.Float(required=True)
    service_instance_oid = fields.String(required=False)
    account_oid = fields.String(required=False)
    aggregation_type = fields.String(required=True, validate=OneOf(__AGGREGATION_COST_TYPE__))
    period = fields.String(required=True, validate=Length(10, 10))
    cost_type_id = fields.Integer(required=True)
    evaluation_date = fields.DateTime(required=False, default="1970-01-01T00:00:00Z", example="1990-12-31T23:59:59Z")
    job_id = fields.Integer(required=False)

    @validates_schema
    def validate_Consume_parameters(self, data):
        if "daily" == data.get("aggregation_type") and data.get("service_instance_oid", None) is None:
            raise ValidationError("Param service_instance_oid cannot be null for daily aggregation type")
        if "monthly" == data.get("aggregation_type") and data.get("account_oid", None) is None:
            raise ValidationError("Param account_oid cannot be null for monthly aggregation type")


class CreateConsumeRequestSchema(Schema):
    consume = fields.Nested(CreateConsumeParamRequestSchema, context="body")


class CreateConsumeBodyRequestSchema(Schema):
    body = fields.Nested(CreateConsumeRequestSchema, context="body")


class CreateConsumeResponseSchema(Schema):
    id = fields.Integer(required=True)


class CreateConsume(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateConsumeRequestSchema": CreateConsumeRequestSchema,
        "CreateConsumeResponseSchema": CreateConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateConsumeBodyRequestSchema)
    parameters_schema = CreateConsumeRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CreateConsumeResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        data = data.get("consume")
        self.logger.warn(data)
        resp = controller.add_consume(**data)
        return {"id": resp}, 201


class DeleteBatchConsumeParamRequestSchema(Schema):
    metric_type_id = fields.Integer(required=False)
    service_instance_id = fields.String(required=False)
    aggregation_type = fields.String(required=False, validate=OneOf(__AGGREGATION_COST_TYPE__))
    period = fields.String(required=False, validate=Length(10, 10))
    cost_type_id = fields.Integer(required=False)
    evaluation_date_start = fields.DateTime(required=False, example="1990-12-31T23:59:59Z")
    evaluation_date_end = fields.DateTime(required=False, example="1990-12-31T23:59:59Z")
    job_id = fields.Integer(required=False)
    limit = fields.Integer(required=False, default=1000)


class DeleteBatchConsumeRequestSchema(Schema):
    consume = fields.Nested(DeleteBatchConsumeParamRequestSchema, context="body")


class DeleteBatchConsumeBodyRequestSchema(Schema):
    body = fields.Nested(DeleteBatchConsumeRequestSchema, context="body")


class DeleteBatchConsumeResponseSchema(Schema):
    deleted = fields.Integer(required=True)


class DeleteBatchConsume(ServiceApiView):
    tags = ["service"]
    definitions = {
        "DeleteBatchConsumeRequestSchema": DeleteBatchConsumeRequestSchema,
        "DeleteBatchConsumeResponseSchema": DeleteBatchConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteBatchConsumeBodyRequestSchema)
    parameters_schema = DeleteBatchConsumeRequestSchema
    responses = ServiceApiView.setResponses(
        {
            204: {
                "description": "no response",
                "schema": DeleteBatchConsumeResponseSchema,
            }
        }
    )

    def delete(self, controller, data, *args, **kwargs):
        data = data.get("consume")
        num = controller.delete_batch_consume(**data)
        self.logger.info("DeleteBatchConsume deleted %s" % num)
        return ({"deleted": num}, 204)


class DeleteConsume(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_m = controller.get_consume(oid)

        resp = srv_m.delete(soft=True)
        return (resp, 204)


# # generate
class GenerateConsumeParamRequestSchema(Schema):
    aggregation_type = fields.String(required=True, validate=OneOf(__AGGREGATION_COST_TYPE__))
    period = fields.String(required=False, validate=Length(7, 10), allow_none=True)


class GenerateConsumeRequestSchema(Schema):
    consume = fields.Nested(GenerateConsumeParamRequestSchema, context="body")


class GenerateConsumeBodyRequestSchema(Schema):
    body = fields.Nested(GenerateConsumeRequestSchema, context="body")


class GenerateConsumeResponseSchema(Schema):
    task_id = fields.String(required=True)


class GenerateConsume(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GenerateConsumeRequestSchema": GenerateConsumeRequestSchema,
        "GenerateConsumeResponseSchema": GenerateConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GenerateConsumeBodyRequestSchema)
    parameters_schema = GenerateConsumeRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": GenerateConsumeResponseSchema}})
    response_schema = GenerateConsumeResponseSchema

    def post(self, controller, data, *args, **kwargs):
        params = data.get("consume")
        from beehive.common.task_v2 import prepare_or_run_task

        dummy = ApiAccount(controller)
        task, code = prepare_or_run_task(
            dummy,
            "beehive_service.task_v2.metrics.generate_daily_consumes_task",
            params,
            sync=False,
        )
        return {"task_id": task["taskid"]}, 201


#
# list e get metric consume extended
#
class GetConsumeExtParamsResponseSchema(Schema):
    metric_id = fields.Integer(required=True, example=10)
    value = fields.Float(required=True)
    metric_num = fields.Integer(required=True)
    type_id = fields.Integer(required=True)
    type_name = fields.String(required=True)
    instance_id = fields.Integer(required=True)
    account_id = fields.Integer(required=True)
    job_id = fields.Integer(required=True)
    extraction_date = fields.DateTime(required=True, example="1990-12-31T23:59:59Z")

    @staticmethod
    def detail(m):
        res = {
            "metric_id": m.id,
            "value": m.value,
            "metric_num": m.metric_num,
            "type_id": m.metric_type_id,
            "type_name": m.metric_type_name,
            "instance_id": m.service_instance_id,
            "account_id": m.account_id,
            "job_id": m.job_id,
            "extraction_date": format_date(m.extraction_date),
        }
        return res


class GetConsumeExtResponseSchema(Schema):
    metric_consume = fields.Nested(GetConsumeExtParamsResponseSchema, required=True, allow_none=True)


class GetConsumeExt(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetConsumeExtResponseSchema": GetConsumeExtResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetConsumeExtResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        metric_consume_view = controller.get_service_metric_consume_view(oid)
        return {"metric_consume": GetConsumeExtParamsResponseSchema.detail(metric_consume_view)}


class ListConsumeExtRequestSchema(PaginatedRequestQuerySchema):
    id = fields.Integer(required=False, context="query")
    metric_type_id = fields.Integer(required=False, context="query")
    metric_type_name = fields.String(required=False, context="query")
    metric_num = fields.Integer(required=False, context="query")

    instance_id = fields.String(required=False, context="query")
    instance_parent_id = fields.String(required=False, context="query")
    account_id = fields.String(required=False, context="query")
    extraction_date_start = fields.DateTime(required=False, context="query")
    extraction_date_end = fields.DateTime(required=False, context="query")
    job_id = fields.Integer(required=False, context="query")

    field = fields.String(
        validate=OneOf(
            [
                "id",
                "metric_type_name",
                "extraction_date",
                "metric_num",
                "instance_parent_id",
                "instance_id",
            ],
            error="Field can be id, metric_type_name, extraction_date, metric_num, instance_parent_id, " "instance_id",
        ),
        description="enitities list order field. Ex. id, metric_type_name, ...",
        default="id",
        example="id",
        missing="id",
        context="query",
    )


class ListConsumeExtResponseSchema(PaginatedResponseSchema):
    metric_consume = fields.Nested(GetConsumeExtParamsResponseSchema, many=True, required=True, allow_none=True)


class ListConsumeExt(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListConsumeExtResponseSchema": ListConsumeExtResponseSchema,
        "ListConsumeExtRequestSchema": ListConsumeExtRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListConsumeExtRequestSchema)
    parameters_schema = ListConsumeExtRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListConsumeExtResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        metric_consume_view, total = controller.get_paginated_metric_consume_views(**data)
        res = [GetConsumeExtParamsResponseSchema.detail(m) for m in metric_consume_view]
        res_dict = self.format_paginated_response(res, "metric_consume", total, **data)
        return res_dict


class ServiceConsumeAPI(ApiView):
    """Consume api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            # ('%s/services/consumes/<oid>' % base, 'GET', GetConsume, {}),
            ("%s/services/consumes" % base, "GET", ListConsume, {}),
            # ('%s/services/consumes' % base, 'POST', CreateConsume, {}),
            # ('%s/services/consumes/<oid>' % base, 'DELETE', DeleteConsume, {}),
            # ('%s/services/consumes' % base, 'DELETE', DeleteBatchConsume, {}),
            ("%s/services/consumes/generate" % base, "POST", GenerateConsume, {}),
            # ('%s/services/consumes/ext' % base, 'GET', ListConsumeExt, {}),
            # ('%s/services/consume/ext/<oid>' % base, 'GET', GetConsumeExt, {})
        ]

        ApiView.register_api(module, rules, **kwargs)
