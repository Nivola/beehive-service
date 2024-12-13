# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.data import transaction
from beehive.common.apimanager import (
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiObjectPermsResponseSchema,
    ApiObjectPermsRequestSchema,
    SwaggerApiView,
    ApiView,
    ApiManagerWarning,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectResponseSchema,
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    ApiBaseServiceObjectCreateRequestSchema,
)
from beehive_service.service_util import __SCHEDULE_TYPE__
from marshmallow.validate import OneOf
from beecell.simple import get_attrib
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError


## get
class GetServiceScheduleParamsResponseSchema(ApiServiceObjectResponseSchema):
    job_name = fields.String(required=True)
    job_options = fields.Dict(required=True)
    schedule_type = fields.String(required=True)
    schedule_params = fields.Dict(required=True)
    relative = fields.Boolean(required=True)
    retry = fields.Boolean(required=True)
    retry_policy = fields.Dict(required=True)
    job_args = fields.Raw(required=False)
    job_kvargs = fields.Dict(required=False)


class GetServiceScheduleResponseSchema(Schema):
    job_schedule = fields.Nested(GetServiceScheduleParamsResponseSchema, required=True, allow_none=True)


class GetServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceScheduleResponseSchema": GetServiceScheduleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceScheduleResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_job_schedule(oid)
        return {"job_schedule": servicepricelist.detail()}


## list
class ListServiceScheduleRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    job_name = fields.String(Required=False, context="query")
    schedule_type = fields.String(Required=False, context="query", validate=OneOf(__SCHEDULE_TYPE__))


class ListServiceScheduleResponseSchema(PaginatedResponseSchema):
    job_schedule = fields.Nested(
        GetServiceScheduleParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceScheduleResponseSchema": ListServiceScheduleResponseSchema,
        "ListServiceScheduleRequestSchema": ListServiceScheduleRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceScheduleRequestSchema)
    parameters_schema = ListServiceScheduleRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceScheduleResponseSchema}}
    )
    response_schema = ListServiceScheduleResponseSchema

    def get(self, controller, data, *args, **kwargs):
        job_schedule, total = controller.get_service_job_schedules(**data)
        res = [r.info() for r in job_schedule]
        res_dict = self.format_paginated_response(res, "job_schedule", total, **data)
        return res_dict


class ServiceScheduleParamRequestSchema(Schema):
    # crontab params
    minute = fields.String(required=False, allow_none=True, default="*")
    hour = fields.String(required=False, allow_none=True, default="*")
    day_of_week = fields.String(required=False, allow_none=True, default="*")
    day_of_month = fields.String(required=False, allow_none=True, default="*")
    month_of_year = fields.String(required=False, allow_none=True, default="*")

    # timedelta params
    days = fields.Float(required=False, allow_none=True, default="0")
    seconds = fields.Float(required=False, allow_none=True, default="0")
    minutes = fields.Float(required=False, allow_none=True, default="0")
    hours = fields.Float(required=False, allow_none=True, default="0")
    weeks = fields.Float(required=False, allow_none=True, default="0")

    @validates_schema
    def validate_parameters(self, data, **kwargs):
        schedule_type = data.get("schedule_type")
        if __SCHEDULE_TYPE__[0] == schedule_type:  # crontab
            keys = data.get("schedule_params", {})
            for key in keys:
                if key in ["days", "seconds", "minutes", "hours", "weeks"]:
                    raise ValidationError(
                        "For schedule type %s the parameter is not supported : %s" % (schedule_type, key)
                    )
        elif __SCHEDULE_TYPE__[1] == schedule_type:  # timedelta
            keys = data.get("schedule_params", {})
            for key in keys:
                if key in [
                    "minute",
                    "hour",
                    "day_of_week",
                    "day_of_month",
                    "month_of_year",
                ]:
                    raise ValidationError(
                        "For schedule type %s the parameter is not supported : %s" % (schedule_type, key)
                    )


class ServiceScheduleRetryRequestSchema(Schema):
    max_retries = fields.Integer(required=False, allow_none=True, default=3)
    interval_start = fields.Float(required=False, allow_none=True, default=0)
    interval_step = fields.Float(required=False, allow_none=True, default=0.2)
    interval_max = fields.Float(required=False, allow_none=True, default=0.2)


## create
class CreateServiceScheduleParamRequestSchema(ApiBaseServiceObjectCreateRequestSchema):
    job_name = fields.String(required=True)
    job_options = fields.Dict(required=False, allow_none=True)  # option
    schedule_type = fields.String(required=True, validate=OneOf(__SCHEDULE_TYPE__))
    schedule_params = fields.Nested(ServiceScheduleParamRequestSchema, required=True)
    relative = fields.Boolean(required=False, allow_none=True, default=False)
    retry = fields.Boolean(required=False, allow_none=True, default=False)
    retry_policy = fields.Nested(ServiceScheduleRetryRequestSchema, required=False)
    job_args = fields.Raw(required=False)  # args
    job_kvargs = fields.Dict(required=False, allow_none=True, missing={})  # kvargs


class CreateServiceScheduleRequestSchema(Schema):
    job_schedule = fields.Nested(CreateServiceScheduleParamRequestSchema, context="body")


class CreateServiceScheduleBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceScheduleRequestSchema, context="body")


class CreateServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateServiceScheduleRequestSchema": CreateServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceScheduleBodyRequestSchema)
    parameters_schema = CreateServiceScheduleRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        data = data.get("job_schedule")

        # initialize job_arg to bypass validation swagger error
        data["job_args"] = data.get("job_args", ["*", {}])

        resp = controller.add_service_job_schedule(**data)
        return ({"uuid": resp}, 201)


## update
class UpdateServiceScheduleParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)

    job_name = fields.String(required=False, allow_none=True)
    job_options = fields.Dict(required=False, allow_none=True)
    schedule_type = fields.String(required=False, allow_none=True, validate=OneOf(__SCHEDULE_TYPE__))
    schedule_params = fields.Nested(ServiceScheduleParamRequestSchema, required=False, allow_none=True)
    relative = fields.Boolean(required=False, allow_none=True)
    retry = fields.Boolean(required=False, allow_none=True)
    retry_policy = fields.Nested(ServiceScheduleRetryRequestSchema, many=False, allow_none=True)
    job_args = fields.Raw(required=False, allow_none=True)  # args
    job_kvargs = fields.Dict(required=False, allow_none=True, missing={})  # kvargs


class UpdateServiceScheduleRequestSchema(Schema):
    job_schedule = fields.Nested(UpdateServiceScheduleParamRequestSchema)


class UpdateServiceScheduleBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceScheduleRequestSchema, context="body")


class UpdateServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateServiceScheduleRequestSchema": UpdateServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceScheduleBodyRequestSchema)
    parameters_schema = UpdateServiceScheduleRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)
        data = data.get("job_schedule")
        resp = srv_pl.update(**data)
        return ({"uuid": resp}, 200)


class DeleteServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)

        resp = srv_pl.delete(soft=True)
        return (resp, 204)


## get perms
class GetServiceSchedulePerms(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ApiObjectPermsRequestSchema": ApiObjectPermsRequestSchema,
        "ApiObjectPermsResponseSchema": ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ApiObjectPermsResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        servicepricelist = controller.get_service_job_schedule(oid)
        res, total = servicepricelist.authorization(**data)
        return self.format_paginated_response(res, "perms", total, **data)


## ExecCMD
class ExecCMDServiceScheduleRequestSchema(Schema):
    cmd = fields.String(required=True)


class ExecCMDServiceScheduleBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(ExecCMDServiceScheduleRequestSchema, context="body")


class ExecCMDServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ExecCMDServiceScheduleRequestSchema": ExecCMDServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ExecCMDServiceScheduleBodyRequestSchema)
    parameters_schema = ExecCMDServiceScheduleRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)

        cmd = data.get("cmd")
        if "start" == cmd:
            resp = srv_pl.start()
        elif "stop" == cmd:
            resp = srv_pl.stop()
        elif "restart" == cmd:
            resp = srv_pl.restart()
        else:
            raise ApiManagerWarning("Unknow command %s!" % cmd)

        return ({"uuid": resp}, 200)


class StartServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ExecCMDServiceScheduleRequestSchema": ExecCMDServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(Schema)
    parameters_schema = Schema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)
        resp = srv_pl.start()

        return ({"uuid": resp}, 200)


class StopServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ExecCMDServiceScheduleRequestSchema": ExecCMDServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(Schema)
    parameters_schema = Schema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)
        resp = srv_pl.stop()

        return ({"uuid": resp}, 200)


class RestartServiceSchedule(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ExecCMDServiceScheduleRequestSchema": ExecCMDServiceScheduleRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(Schema)
    parameters_schema = Schema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    @transaction
    def put(self, controller, data, oid, *args, **kwargs):
        srv_pl = controller.get_service_job_schedule(oid)
        resp = srv_pl.restart()

        return ({"uuid": resp}, 200)


class ServiceJobScheduleAPI(ApiView):
    """ServiceJobSchedule api routes:"""

    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws/services"
        rules = [
            ("%s/job_schedules" % base, "GET", ListServiceSchedule, {}),
            ("%s/job_schedules" % base, "POST", CreateServiceSchedule, {}),
            ("%s/job_schedules/<oid>" % base, "GET", GetServiceSchedule, {}),
            ("%s/job_schedules/<oid>" % base, "PUT", UpdateServiceSchedule, {}),
            ("%s/job_schedules/<oid>" % base, "DELETE", DeleteServiceSchedule, {}),
            ("%s/job_schedules/<oid>/perms" % base, "GET", GetServiceSchedulePerms, {}),
            ("%s/job_schedules/<oid>/start" % base, "PUT", StartServiceSchedule, {}),
            ("%s/job_schedules/<oid>/stop" % base, "PUT", StopServiceSchedule, {}),
            ("%s/job_schedules/<oid>/restart" % base, "PUT", RestartServiceSchedule, {})
            # ('%s/job_schedules/<oid>/start' % base, 'PUT', ExecCMDServiceSchedule, {'cmd': 'start'}),
            # ('%s/job_schedules/<oid>/stop' % base, 'PUT', ExecCMDServiceSchedule, {'cmd': 'stop'}),
            # ('%s/job_schedules/<oid>/restart' % base, 'PUT', ExecCMDServiceSchedule, {'cmd': 'restart'})
        ]

        ApiView.register_api(module, rules, **kwargs)
