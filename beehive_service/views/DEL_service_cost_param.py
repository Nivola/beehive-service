# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.data import transaction, trace
from beehive.common.apimanager import (
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    ApiObjectResponseSchema,
    CrudApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    SwaggerApiView,
    ApiView,
    ApiManagerError,
)
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.entity.service_type import ApiServiceType
from beehive_service.views import ServiceApiView
from beecell.simple import id_gen
from beehive_service.model import ServiceCostParam
from beecell.db import QueryError, TransactionError


## get
class GetServiceCostParamParamsResponseSchema(ApiObjectResponseSchema):
    service_type_id = fields.String(Required=True)
    name = fields.String(Required=True, allow_none=True, example="default name")
    objid = fields.String(Required=True)
    param_unit = fields.String(Required=False, allow_none=True, default="")
    param_definition = fields.String(Required=True, allow_none=False, example="")


class GetServiceCostParamResponseSchema(Schema):
    servicecostparam = fields.Nested(GetServiceCostParamParamsResponseSchema, required=True, allow_none=True)


class GetServiceCostParam(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceCostParamResponseSchema": GetServiceCostParamResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceCostParamResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kwargs):
        servicecostparam = controller.get_service_cost_param(oid)
        return {"servicecostparam": servicecostparam.detail()}


## list
class ListServiceCostParamRequestSchema(PaginatedRequestQuerySchema):
    service_type_id = fields.String(Required=False, context="query")
    name = fields.String(Required=False, context="query")
    objid = fields.String(Required=False, context="query")
    param_unit = fields.String(Required=False, context="query")
    param_definition = fields.String(Required=False, context="query")


class ListServiceCostParamResponseSchema(PaginatedResponseSchema):
    servicecostparams = fields.Nested(
        GetServiceCostParamParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListServiceCostParam(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceCostParamResponseSchema": ListServiceCostParamResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceCostParamRequestSchema)
    parameters_schema = ListServiceCostParamRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceCostParamResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        service_type, total = controller.get_service_cost_params(**data)
        res = [r.info() for r in service_type]
        return self.format_paginated_response(res, "servicecostparams", total, **data)


## create
class CreateServiceCostParamParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    service_type_id = fields.String(required=True)
    param_unit = fields.String(required=False, default="")
    param_definition = fields.String(required=True)


class CreateServiceCostParamRequestSchema(Schema):
    servicecostparam = fields.Nested(CreateServiceCostParamParamRequestSchema, context="body")


class CreateServiceCostParamBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceCostParamRequestSchema, context="body")


class CreateServiceCostParam(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreateServiceCostParamRequestSchema": CreateServiceCostParamRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceCostParamBodyRequestSchema)
    parameters_schema = CreateServiceCostParamRequestSchema
    responses = ServiceApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    @staticmethod
    @trace(entity="ApiServiceCostParam", op="insert")
    def add_service_cost_param(
        controller,
        name="",
        desc=None,
        service_type_id=None,
        param_unit=None,
        param_definition=None,
        active=False,
    ):
        """ """
        servicetype = controller.get_service_type(service_type_id)

        # check authorization on serviceType
        controller.check_authorization(ApiServiceType.objtype, ApiServiceType.objdef, servicetype.objid, "update")

        try:
            # create reference
            objid = id_gen(parent_id=servicetype.objid)
            srv_cp = ServiceCostParam(
                objid,
                param_unit=param_unit,
                param_definition=param_definition,
                name=name,
                service_type_id=servicetype.oid,
                desc=desc,
                active=active,
            )

            res = controller.manager.add(srv_cp)

            # create object and permission
            # ApiServiceCostParam(controller, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            CreateServiceCostParam.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    def post(self, controller, data, *args, **kwargs):
        resp = self.add_service_cost_param(controller, **data.get("servicecostparam"))
        return ({"uuid": resp}, 201)


## update
class UpdateServiceCostParamParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    service_type_id = fields.String(Required=False, allow_none=True)
    param_unit = fields.String(Required=False, allow_none=True)
    param_definition = fields.String(Required=False, allow_none=True)


class UpdateServiceCostParamRequestSchema(Schema):
    servicecostparam = fields.Nested(UpdateServiceCostParamParamRequestSchema)


class UpdateServiceCostParamBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceCostParamRequestSchema, context="body")


class UpdateServiceCostParam(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateServiceCostParamRequestSchema": UpdateServiceCostParamRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceCostParamBodyRequestSchema)
    parameters_schema = UpdateServiceCostParamRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kwargs):
        srv_cp = controller.get_service_cost_param(oid)
        data = data.get("servicecostparam")

        resp = srv_cp.update(**data)
        return ({"uuid": resp}, 200)


class DeleteServiceCostParam(ServiceApiView):
    tags = ["service"]
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_cp = controller.get_service_cost_param(oid)
        self.logger.warning("DeleteServiceCostParam %s" % srv_cp)
        resp = srv_cp.delete(soft=True)
        return (resp, 204)


class ServiceCostParamAPI(ApiView):
    """ServiceInstance api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/servicecostparams" % base, "GET", ListServiceCostParam, {}),
            ("%s/servicecostparams" % base, "POST", CreateServiceCostParam, {}),
            ("%s/servicecostparams/<oid>" % base, "GET", GetServiceCostParam, {}),
            ("%s/servicecostparams/<oid>" % base, "PUT", UpdateServiceCostParam, {}),
            ("%s/servicecostparams/<oid>" % base, "DELETE", DeleteServiceCostParam, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
