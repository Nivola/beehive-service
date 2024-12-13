# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from marshmallow import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiView,
    CrudApiObjectResponseSchema,
    SwaggerApiView,
    PaginatedResponseSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
    ApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiManagerWarning,
)
from beehive_service.entity.service_type import ApiServiceType
from beehive_service.model import SrvStatusType
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiServiceObjectCreateRequestSchema,
)


class GetPluginTypeInstanceParamsResponseSchema(ApiObjectResponseSchema):
    account_id = fields.String(required=True)
    service_definition_id = fields.String(required=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, allow_none=True)
    config = fields.Dict(required=False, allow_none=True)


class GetPluginTypeInstanceResponseSchema(Schema):
    plugin = fields.Nested(GetPluginTypeInstanceParamsResponseSchema, required=True, allow_none=True)


class GetPluginTypeInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetPluginTypeInstanceResponseSchema": GetPluginTypeInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetPluginTypeInstanceResponseSchema}}
    )

    def get(self, controller, data, oid, *args, **kvargs):
        plugin = controller.get_service_type_plugin(oid)
        return {"plugin": plugin.detail()}


class ListPluginTypeInstancesRequestSchema(
    ApiServiceObjectRequestSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
):
    account_id = fields.String(required=False, context="query")
    service_definition_id = fields.String(required=False, context="query")
    status = fields.String(required=False, context="query")
    bpmn_process_id = fields.Integer(required=False, context="query")
    resource_uuid = fields.String(required=False, context="query")
    parent_id = fields.String(required=False, context="query")
    plugintype = fields.String(required=False, context="query")
    tags = fields.String(
        context="query",
        description="List of tags. Use comma as separator if tags are in or. Use + " "separator if tags are in and",
    )
    flag_container = fields.Boolean(context="query", description="if True show only container instances")


class ListPluginTypeInstancesResponseSchema(PaginatedResponseSchema):
    plugins = fields.Nested(
        GetPluginTypeInstanceParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListPluginTypeInstances(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListPluginTypeInstancesResponseSchema": ListPluginTypeInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListPluginTypeInstancesRequestSchema)
    parameters_schema = ListPluginTypeInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": ListPluginTypeInstancesResponseSchema,
            }
        }
    )

    def get(self, controller, data, *args, **kvargs):
        servicetags = data.pop("tags", None)
        if servicetags is not None and servicetags.find("+") > 0:
            data["servicetags_and"] = servicetags.split("+")
        elif servicetags is not None:
            data["servicetags_or"] = servicetags.split(",")

        service, total = controller.get_service_type_plugins(**data)
        res = [r.info() for r in service]
        return self.format_paginated_response(res, "plugins", total, **data)


class CreatePluginTypeInstanceParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    account_id = fields.String(required=True, description="id of the account")
    service_def_id = fields.String(required=True, description="id of the service definition")
    parent_id = fields.String(required=False, allow_none=True, description="id of the parent service instance")
    priority = fields.Integer(required=False, allow_none=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    hierarchy = fields.Boolean(
        required=False,
        missing=True,
        description="If True create service instance hierarchy",
    )


class CreatePluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(CreatePluginTypeInstanceParamRequestSchema, context="body")


class CreatePluginTypeInstanceBodyRequestSchema(Schema):
    body = fields.Nested(CreatePluginTypeInstanceRequestSchema, context="body")


class CreatePluginTypeInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CreatePluginTypeInstanceRequestSchema": CreatePluginTypeInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreatePluginTypeInstanceBodyRequestSchema)
    parameters_schema = CreatePluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kvargs):
        """
        Crea una service instance utilizzando uno specifico plugin type
        Crea una service instance utilizzando uno specifico plugin type
        TODO
        """
        hierarchy = data.get("serviceinst").get("hierarchy")
        uuid = None
        # hierarchy creation
        if hierarchy is True:
            # Create tree hierarchy SI
            oid = data.get("serviceinst").pop("service_def_id")
            rootInstance = controller.createInstanceHierachy(oid, **data.get("serviceinst"))
            pluginRoot = ApiServiceType(controller).instancePlugin(rootInstance.id)

            # Create tree hierarchy Resource
            uuid = pluginRoot.createResource(rootInstance.id)

        # simple creation
        else:
            resp = controller.add_service_instance(**data.get("plugin"))
            uuid = resp.uuid
        return {"uuid": uuid}, 201


class ImportPluginTypeInstanceParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    account_id = fields.String(required=True, description="id of the account")
    plugintype = fields.String(required=True, description="plugin type name")
    container_plugintype = fields.String(required=True, description="container plugin type name")
    service_definition_id = fields.String(required=False, missing=None, description="id of the service definition")
    parent_id = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="id of the parent service instance",
    )
    resource_id = fields.String(required=True, allow_none=False, description="id of the resource")


class ImportPluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(ImportPluginTypeInstanceParamRequestSchema, context="body")


class ImportPluginTypeInstanceBodyRequestSchema(Schema):
    body = fields.Nested(ImportPluginTypeInstanceRequestSchema, context="body")


class ImportPluginTypeInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ImportPluginTypeInstanceRequestSchema": ImportPluginTypeInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ImportPluginTypeInstanceBodyRequestSchema)
    parameters_schema = ImportPluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def post(self, controller, data, *args, **kvargs):
        """
        Crea una service instance utilizzando uno specifico plugin type pertendo da una risorsa esistente
        Crea una service instance utilizzando uno specifico plugin type pertendo da una risorsa esistente
        """
        data = data.get("plugin")
        account_id = data.get("account_id")
        service_definition_id = data.get("service_definition_id")
        name = data.get("name")
        desc = name
        plugintype = data.get("plugintype")
        container_plugintype = data.get("container_plugintype")
        parent_id = data.get("parent_id")
        resource_id = data.get("resource_id")

        # check account with compute service
        # account, container_plugin = self.check_parent_service(controller, data.get(u'account_id'),
        #                                                       plugintype=container_plugintype)

        # check parent container service
        account = controller.get_account(account_id)

        # check if the account is associated to a Compute Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype="ComputeService")
        if total == 0:
            raise ApiManagerWarning("Account %s has not %s" % (account.oid, plugintype))
        compute_zone = insts[0].resource_uuid

        # check if the account is associated to the required container Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype=container_plugintype)
        if total == 0:
            raise ApiManagerWarning("Account %s has not %s" % (account.oid, plugintype))

        container_plugin = insts[0]

        if container_plugin.is_active() is False:
            raise ApiManagerWarning("Account %s %s is not in a correct status" % (account_id, plugintype))

        # checks authorization user on container service instance
        if container_plugin.instance.verify_permisssions("update") is False:
            raise ApiManagerWarning("User does not have the required permissions to make this action")

        # get parent
        if parent_id is not None:
            parent_plugin = controller.get_service_type_plugin(parent_id, details=False)
        else:
            parent_plugin = container_plugin

        # get definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(plugintype)
            service_definition_id = service_definition.uuid

        # create instance and resource
        config = {
            "owner_id": account.uuid,
            "service_definition_id": service_definition_id,
            "computeZone": compute_zone,
        }
        plugin = controller.import_service_type_plugin(
            service_definition_id,
            account.oid,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=config,
            resource_id=resource_id,
        )

        return {"uuid": plugin.instance.uuid}, 201


class UpdatePluginTypeInstanceTagRequestSchema(Schema):
    cmd = fields.String(default="add", required=True)
    values = fields.List(fields.String(default="test"), required=True)


class UpdatePluginTypeInstanceParamRequestSchema(Schema):
    # name = fields.String(required=False)
    # desc = fields.String(required=False)
    # account_id = fields.Integer(required=False)
    # service_definition_id = fields.Integer(required=False)
    # status = fields.String(required=False, default=SrvStatusType.DRAFT)
    # active = fields.Boolean(required=False)
    # bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, description="uuid of the new resource")
    tags = fields.Nested(UpdatePluginTypeInstanceTagRequestSchema, allow_none=True)
    parent_id = fields.String(required=False, allow_none=True, description="id of the parent service instance")


class UpdatePluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(UpdatePluginTypeInstanceParamRequestSchema, context="body")


class UpdatePluginTypeInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdatePluginTypeInstanceRequestSchema, context="body")


class UpdatePluginTypeInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "DeletePluginTypeInstanceRequestSchema": UpdatePluginTypeInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdatePluginTypeInstanceBodyRequestSchema)
    parameters_schema = UpdatePluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kvargs):
        """
        Modifica una service instance utilizzando uno specifico plugin type
        Modifica una service instance utilizzando uno specifico plugin type
        """
        type_plugin = controller.get_service_type_plugin(oid)
        type_plugin.update(**data.get("plugin"))

        return True, 201


class DeletePluginTypeInstanceRequestSchema(Schema):
    propagate = fields.Boolean(
        required=False,
        default=True,
        description="If True propagate delete to all cmp modules",
    )
    force = fields.Boolean(required=False, default=False, description="If True force delete")


class DeletePluginTypeInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeletePluginTypeInstanceRequestSchema, context="body")


class DeletePluginTypeInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "DeletePluginTypeInstanceRequestSchema": DeletePluginTypeInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeletePluginTypeInstanceBodyRequestSchema)
    parameters_schema = DeletePluginTypeInstanceRequestSchema
    responses = ServiceApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        type_plugin.delete(**data)

        return True, 204


class UpdatePluginStatusParamRequestSchema(Schema):
    status = fields.String(required=True, example=SrvStatusType.DRAFT)


class UpdatePluginStatusRequestSchema(Schema):
    plugin = fields.Nested(UpdatePluginStatusParamRequestSchema)


class UpdatePluginStatusBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdatePluginStatusRequestSchema, context="body")


class UpdatePluginStatus(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdatePluginStatusRequestSchema": UpdatePluginStatusRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdatePluginStatusBodyRequestSchema)
    parameters_schema = UpdatePluginStatusRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})

    def put(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        status = data.get("plugin", {}).get("status", None)
        resp = False
        if status is not None:
            type_plugin.update_status(status)
            resp = True

        return resp, 200


class ServicePluginTypeInstanceAPI(ApiView):
    """PluginTypeInstance api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/plugins" % base, "GET", ListPluginTypeInstances, {}),
            ("%s/plugins" % base, "POST", CreatePluginTypeInstance, {}),
            ("%s/plugins/import" % base, "POST", ImportPluginTypeInstance, {}),
            ("%s/plugins/<oid>" % base, "GET", GetPluginTypeInstance, {}),
            ("%s/plugins/<oid>" % base, "PUT", UpdatePluginTypeInstance, {}),
            ("%s/plugins/<oid>" % base, "DELETE", DeletePluginTypeInstance, {}),
            ("%s/plugins/<oid>/status" % base, "PUT", UpdatePluginStatus, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
