# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.controller import ServiceController
from marshmallow import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiObjectSmallResponseSchema,
    ApiView,
    CrudApiObjectResponseSchema,
    SwaggerApiView,
    PaginatedResponseSchema,
    ApiObjectRequestFiltersSchema,
    PaginatedRequestQuerySchema,
    ApiObjectResponseSchema,
    GetApiObjectRequestSchema,
    ApiManagerError,
    ApiManagerWarning,
    CrudApiObjectTaskResponseSchema,
)
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import ApiServiceType, ApiServiceTypePlugin
from beehive_service.model import SrvStatusType
from beehive_service.plugins.computeservice.controller import ApiComputeInstance
from beehive_service.views import (
    ServiceApiView,
    ApiServiceObjectRequestSchema,
    ApiServiceObjectCreateRequestSchema,
)


class AccountResponseSchema(ApiObjectSmallResponseSchema):
    pass


class ParentResponseSchema(Schema):
    uuid = fields.UUID(
        required=False, example="6d960236-d280-46d2-817d-f3ce8f0aeff7", description="api object uuid", allow_none=True
    )
    name = fields.String(required=False, default="test", example="test", description="entity name")


class CheckResponseSchema(Schema):
    check = fields.Boolean(required=False, allow_none=True)
    msg = fields.String(required=False, allow_none=True)


class GetServiceInstanceParamsResponseSchema(ApiObjectResponseSchema):
    # account_id = fields.String(required=True)
    account = fields.Nested(AccountResponseSchema, required=True, allow_none=True)
    definition_id = fields.String(required=True)
    definition_name = fields.String(required=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, allow_none=True)
    config = fields.Dict(required=False, allow_none=True)
    version = fields.String(required=False, allow_none=True)
    parent = fields.Nested(ParentResponseSchema, required=False, allow_none=True)
    is_container = fields.Boolean(required=False, allow_none=True)
    last_error = fields.String(required=False, allow_none=True)
    plugintype = fields.String(required=False, allow_none=True)
    tags = fields.List(fields.String(required=False, allow_none=True))
    # per check resource
    check = fields.Nested(CheckResponseSchema, required=False, allow_none=True)


class GetServiceInstanceResponseSchema(Schema):
    serviceinst = fields.Nested(GetServiceInstanceParamsResponseSchema, required=True, allow_none=True)


class GetServiceInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetServiceInstanceResponseSchema": GetServiceInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetServiceInstanceResponseSchema}}
    )
    response_schema = GetServiceInstanceResponseSchema

    def get(self, controller, data, oid, *args, **kvargs):
        from beehive_service.controller import ServiceController

        serviceController: ServiceController = controller

        plugin = serviceController.get_service_type_plugin(oid)
        return {"serviceinst": plugin.detail()}


class CheckServiceInstanceParamsResponseSchema(ApiObjectResponseSchema):
    account_id = fields.String(required=True)
    service_definition_id = fields.String(required=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, allow_none=True)
    config = fields.Dict(required=False, allow_none=True)
    check = fields.Dict(required=False, allow_none=True)


class CheckServiceInstanceResponseSchema(Schema):
    serviceinst = fields.Nested(GetServiceInstanceParamsResponseSchema, required=True, allow_none=True)


class CheckServiceInstance(ServiceApiView):
    tags = ["service"]
    definitions = {
        "CheckServiceInstanceResponseSchema": CheckServiceInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": CheckServiceInstanceResponseSchema}}
    )
    response_schema = CheckServiceInstanceResponseSchema

    def get(self, controller, data, oid, *args, **kvargs):
        plugin = controller.get_service_type_plugin(oid)
        item = plugin.info()
        item["check"] = plugin.check()
        if item["check"]["check"] is False:
            item["status"] = "BAD"
        return {"serviceinst": item}


class ListServiceInstancesRequestSchema(
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
    details = fields.Boolean(
        required=False, description="if True and only one plugin type is selected show details (resource)", default=True
    )
    tags = fields.String(
        context="query",
        description="List of tags. Use comma as separator if tags are in or. Use + " "separator if tags are in and",
    )
    flag_container = fields.Boolean(context="query", description="if True show only container instances")


class ListServiceInstancesResponseSchema(PaginatedResponseSchema):
    serviceinsts = fields.Nested(
        GetServiceInstanceParamsResponseSchema,
        many=True,
        required=True,
        allow_none=True,
    )


class ListServiceInstances(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListServiceInstancesRequestSchema": ListServiceInstancesRequestSchema,
        "ListServiceInstancesResponseSchema": ListServiceInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceInstancesRequestSchema)
    parameters_schema = ListServiceInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ListServiceInstancesResponseSchema}}
    )
    response_schema = ListServiceInstancesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kvargs):
        servicetags = data.pop("tags", None)
        if servicetags is not None and servicetags.find("+") > 0:
            data["servicetags_and"] = servicetags.split("+")
        elif servicetags is not None:
            data["servicetags_or"] = servicetags.split(",")
        service, total = controller.get_service_type_plugins(**data)
        res = [r.info() for r in service]
        return self.format_paginated_response(res, "serviceinsts", total, **data)


class CreateServiceInstanceParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    account_id = fields.String(required=True, description="id of the account")
    service_def_id = fields.String(required=True, description="id of the service definition")
    parent_id = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="id of the parent service instance",
    )
    config = fields.Dict(required=False, missing={}, description="Service instance confgiuration")
    status = fields.String(required=False, default=SrvStatusType.DRAFT)
    # bpmn_process_id = fields.Integer(required=False, allow_none=True)


class CreateServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(CreateServiceInstanceParamRequestSchema, context="body")


class CreateServiceInstanceBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceInstanceRequestSchema, context="body")


class CreateServiceInstance(ServiceApiView):
    summary = "Create a service instance using a specific plugintype"
    description = "Create a service instance using a specific plugintype"
    tags = ["service"]
    definitions = {
        "CreateServiceInstanceRequestSchema": CreateServiceInstanceRequestSchema,
        "CrudApiObjectTaskResponseSchema": CrudApiObjectTaskResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceInstanceBodyRequestSchema)
    parameters_schema = CreateServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses(
        {201: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def post(self, controller, data, *args, **kvargs):
        data = data.get("serviceinst")
        service_definition_id = data["service_def_id"]
        account_id = data["account_id"]
        parent_id = data["parent_id"]
        name = data["name"]
        desc = data["desc"]
        instance_config = data["config"]

        parent_plugin = None
        if parent_id is not None:
            parent_plugin = controller.get_service_type_plugin(parent_id)

        resp = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=instance_config,
        )
        uuid = resp.uuid
        taskid = resp.active_task
        return {"uuid": uuid, "taskid": taskid}, 201


class ImportInstanceParamRequestSchema(Schema):
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


class ImportInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(ImportInstanceParamRequestSchema, context="body")


class ImportInstanceBodyRequestSchema(Schema):
    body = fields.Nested(ImportInstanceRequestSchema, context="body")


class ImportInstance(ServiceApiView):
    summary = "Create a service instance using a specific plugintype and an existing resource"
    description = "Create a service instance using a specific plugintype and an existing resource"
    tags = ["service"]
    definitions = {
        "ImportInstanceRequestSchema": ImportInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ImportInstanceBodyRequestSchema)
    parameters_schema = ImportInstanceRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kvargs):
        data = data.get("serviceinst")
        account_id = data.get("account_id")
        service_definition_id = data.get("service_definition_id")
        name = data.get("name")
        desc = name
        plugintype = data.get("plugintype")
        container_plugintype = data.get("container_plugintype")
        parent_id = data.get("parent_id")
        resource_id = data.get("resource_id")

        # check account with compute service
        # account, container_plugin = self.check_parent_service(controller, data.get('account_id'),
        #                                                       plugintype=container_plugintype)

        # check parent container service
        account = controller.get_account(account_id)

        # check if the account is associated to a Compute Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype="ComputeService")
        if total == 0:
            raise ApiManagerWarning("Account %s does not have core ComputeService." % account.oid)
        compute_zone = insts[0].resource_uuid
        if compute_zone is None:
            raise ApiManagerError("comput zone is None")

        # check if the account is associated to the required container Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype=container_plugintype)
        if total == 0:
            raise ApiManagerWarning("Account %s does not have %s" % (account.oid, container_plugintype))
        container_plugin = insts[0]

        if container_plugin.is_active() is False:
            raise ApiManagerWarning("Account %s: %s is not in a correct status" % (account_id, container_plugintype))

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


class UpdateServiceInstanceTagRequestSchema(Schema):
    cmd = fields.String(default="add", required=True)
    values = fields.List(fields.String(default="test"), required=True)


class UpdateServiceInstanceParamRequestSchema(Schema):
    # name = fields.String(required=False)
    # desc = fields.String(required=False)
    # account_id = fields.Integer(required=False)
    # service_definition_id = fields.Integer(required=False)
    # status = fields.String(required=False, default=SrvStatusType.DRAFT)
    active = fields.Boolean(required=False)
    # bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, description="uuid of the new resource")
    tags = fields.Nested(UpdateServiceInstanceTagRequestSchema, allow_none=True)
    parent_id = fields.String(required=False, allow_none=True, description="id of the parent service instance")


class UpdateServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateServiceInstanceParamRequestSchema, context="body")


class UpdateServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstanceRequestSchema, context="body")


class UpdateServiceInstance(ServiceApiView):
    summary = "Update a service instance"
    description = "Update a service instance"
    tags = ["service"]
    definitions = {
        "UpdateServiceInstanceRequestSchema": UpdateServiceInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstanceBodyRequestSchema)
    parameters_schema = UpdateServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses(
        {201: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def put(self, controller, data, oid, *args, **kvargs):
        type_plugin: ApiComputeInstance = controller.get_service_type_plugin(oid)
        type_plugin.update(**data.get("serviceinst"))

        uuid = type_plugin.uuid
        taskid = type_plugin.active_task
        return {"uuid": uuid, "taskid": taskid}, 201


class UpdateAccountServiceInstanceResponseSchema(Schema):
    num_services = fields.Integer(required=False)


class UpdateAccountServiceInstanceParamRequestSchema(Schema):
    tags = fields.Nested(UpdateServiceInstanceTagRequestSchema, allow_none=True)


class UpdateAccountServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateAccountServiceInstanceParamRequestSchema, context="body")


class UpdateAccountServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateAccountServiceInstanceRequestSchema, context="body")


class UpdateAccountServiceInstance(ServiceApiView):
    summary = "Update account's service instance"
    description = "Update account's service instance"
    tags = ["service"]
    definitions = {
        "UpdateAccountServiceInstanceRequestSchema": UpdateAccountServiceInstanceRequestSchema,
        "UpdateAccountServiceInstanceResponseSchema": UpdateAccountServiceInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateAccountServiceInstanceBodyRequestSchema)
    parameters_schema = UpdateAccountServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses(
        {201: {"description": "success", "schema": UpdateAccountServiceInstanceResponseSchema}}
    )
    response_schema = UpdateAccountServiceInstanceResponseSchema

    def put(self, controller: ServiceController, data, oid, *args, **kvargs):
        from beehive_service.plugins.computeservice.controller import ApiComputeInstance, ApiComputeVolume
        from beehive_service.plugins.databaseservice.controller import ApiDatabaseServiceInstance

        num_services = 0

        params = data.get("serviceinst")
        tags = params.pop("tags", None)
        self.logger.info("update instance - tags: %s" % (tags))
        if tags is not None:
            cmd = tags.get("cmd")
            values = tags.get("values")
            # add tag
            if cmd == "add":
                type_plugins, total_insts = controller.get_service_type_plugins(
                    account_id=oid, size=-1, flag_container=False
                )
                # self.logger.info("update instance - type_plugins: %s" % (len(type_plugins)))
                self.logger.info("update instance - total_insts: %s" % (total_insts))

                for type_plugin in type_plugins:
                    self.logger.info("update instance - type_plugin: %s" % (type_plugin))
                    if (
                        isinstance(type_plugin, ApiComputeInstance)
                        or isinstance(type_plugin, ApiComputeVolume)
                        or isinstance(type_plugin, ApiDatabaseServiceInstance)
                    ):
                        num_services += 1
                        res_apiServiceInstance: ApiServiceInstance = controller.get_service_instance(
                            type_plugin.instance.oid
                        )

                        for value in values:
                            self.logger.info(
                                "update instance - oid: %s - value: %s" % (type_plugin.instance.oid, value)
                            )
                            res_apiServiceInstance.add_tag(value)
                            # apiServiceTypePlugin: ApiServiceTypePlugin = type_plugin
                            # apiServiceTypePlugin.instance.add_tag(value)

        return {"num_services": num_services}


class PatchServiceInstanceParamRequestSchema(Schema):
    pass
    # name = fields.String(required=False)
    # desc = fields.String(required=False)
    # account_id = fields.Integer(required=False)
    # service_definition_id = fields.Integer(required=False)
    # status = fields.String(required=False, default=SrvStatusType.DRAFT)
    # active = fields.Boolean(required=False)
    # # bpmn_process_id = fields.Integer(required=False, allow_none=True)
    # resource_uuid = fields.String(required=False, description='uuid of the new resource')
    # tags = fields.Nested(PatchServiceInstanceTagRequestSchema, allow_none=True)
    # parent_id = fields.String(required=False, allow_none=True, description='id of the parent service instance')


class PatchServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(PatchServiceInstanceParamRequestSchema, context="body")


class PatchServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchServiceInstanceRequestSchema, context="body")


class PatchServiceInstance(ServiceApiView):
    summary = "Patch a service instance"
    description = "Patch a service instance"
    tags = ["service"]
    definitions = {
        "PatchServiceInstanceRequestSchema": PatchServiceInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(PatchServiceInstanceBodyRequestSchema)
    parameters_schema = PatchServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses(
        {201: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def patch(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        type_plugin.patch(**data.get("serviceinst"))

        uuid = type_plugin.uuid
        taskid = type_plugin.active_task
        return {"uuid": uuid, "taskid": taskid}, 201


class DeleteServiceInstanceRequestSchema(Schema):
    propagate = fields.Boolean(
        required=False,
        default=True,
        description="If True propagate delete to all cmp modules",
    )
    force = fields.Boolean(required=False, default=False, description="If True force delete")


class DeleteServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteServiceInstanceRequestSchema, context="body")


class DeleteServiceInstance(ServiceApiView):
    summary = "Delete a service instance"
    description = "Delete a service instance"
    tags = ["service"]
    definitions = {
        "DeleteServiceInstanceRequestSchema": DeleteServiceInstanceRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteServiceInstanceBodyRequestSchema)
    parameters_schema = DeleteServiceInstanceRequestSchema
    responses = ServiceApiView.setResponses(
        {201: {"description": "success", "schema": CrudApiObjectTaskResponseSchema}}
    )
    response_schema = CrudApiObjectTaskResponseSchema

    def delete(self, controller: ServiceController, data, oid, *args, **kvargs):
        type_plugin: ApiServiceTypePlugin = controller.get_service_type_plugin(oid)
        type_plugin.delete(**data)

        uuid = type_plugin.uuid
        taskid = getattr(type_plugin, "active_task", None)
        return {"uuid": uuid, "taskid": taskid}, 201


class UpdateServiceInstanceStatusParamRequestSchema(Schema):
    status = fields.String(required=True, example=SrvStatusType.DRAFT)


class UpdateServiceInstanceStatusRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateServiceInstanceStatusParamRequestSchema)


class UpdateServiceInstanceStatusBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstanceStatusRequestSchema, context="body")


class UpdateServiceInstanceStatus(ServiceApiView):
    summary = "Update service instance status"
    description = "Update service instance status"
    tags = ["service"]
    definitions = {
        "UpdateServiceInstanceStatusRequestSchema": UpdateServiceInstanceStatusRequestSchema,
        "CrudApiObjectResponseSchema": CrudApiObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstanceStatusBodyRequestSchema)
    parameters_schema = UpdateServiceInstanceStatusRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CrudApiObjectResponseSchema}})
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        status = data.get("serviceinst", {}).get("status", None)
        if status is not None:
            type_plugin.update_status(status)

        return {"uuid": type_plugin.uuid}, 200


# class ListServiceInstanceLinksParamsResponseSchema(ApiObjectResponseSchema):
#     name = fields.String(required=True, example='default link name')
#     desc = fields.String(required=True, example='default link description')
#     attributes = fields.String(required=True, allow_none=True, example='default value')
#     start_service_id = fields.String(required=True)
#     end_service_id = fields.String(required=True)
#     priority = fields.Integer(Required=True, example=0)
#
#
# class ListServiceInstanceLinksResponseSchema(Schema):
#     links = fields.Nested(ListServiceInstanceLinksParamsResponseSchema, many=True, required=True, allow_none=True)
#
#
# class GetServiceInstanceLinks(ServiceApiView):
#     summary = 'Get service instance links'
#     description = 'Get service instance links'
#     tags = ['service']
#     definitions = {
#         'ListServiceInstanceLinksResponseSchema': ListServiceInstanceLinksResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ListServiceInstanceLinksResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kvargs):
#         type_plugin = controller.get_service_type_plugin(oid)
#         # res = controller.get_service_instance(oid)
#         data = {
#             'start_service_id': type_plugin.instance.oid,
#             'size': 0
#         }
#
#         service_links, total = controller.list_service_instlink(**data)
#         links = [r.info() for r in service_links]
#         res = {'links': links}
#
#         return res


class GetLinkedServiceInstancesRequestSchema(PaginatedRequestQuerySchema):
    type = fields.String(context="query")
    link_type = fields.String(context="query")
    oid = fields.String(required=True, description="id, uuid", context="path")


class GetLinkedServiceInstancesResponseSchema(PaginatedResponseSchema):
    serviceinsts = fields.Nested(GetServiceInstanceResponseSchema, many=True, required=True, allow_none=True)


class GetLinkedServiceInstances(ServiceApiView):
    summary = "Get service instance linked instances"
    description = "Get service instance linked instances"
    tags = ["service"]
    definitions = {
        "GetLinkedServiceInstancesResponseSchema": GetLinkedServiceInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetLinkedServiceInstancesRequestSchema)
    parameters_schema = GetLinkedServiceInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetLinkedServiceInstancesResponseSchema,
            }
        }
    )
    response_schema = GetLinkedServiceInstancesResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        srv_inst = controller.get_service_instance(oid)
        srv_insts, total = srv_inst.get_linked_services(**data)
        res = [r.info() for r in srv_insts]
        return self.format_paginated_response(res, "serviceinsts", total, **data)


class UpdateServiceConfigParamRequestSchema(Schema):
    key = fields.String(default="test", required=True, description="config key like key1.key2")
    value = fields.String(default="test", required=False, missing=None, description="config value")


class UpdateServiceConfigRequestSchema(Schema):
    config = fields.Nested(
        UpdateServiceConfigParamRequestSchema,
        required=True,
        many=False,
        allow_none=True,
    )


class UpdateServiceConfigBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceConfigRequestSchema, context="body")


class UpdateServiceConfigResponseSchema(Schema):
    config = fields.Dict(equired=True)


class UpdateServiceConfig(ServiceApiView):
    tags = ["service"]
    definitions = {
        "UpdateServiceConfigRequestSchema": UpdateServiceConfigRequestSchema,
        "UpdateServiceConfigResponseSchema": UpdateServiceConfigResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceConfigBodyRequestSchema)
    parameters_schema = UpdateServiceConfigRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": UpdateServiceConfigResponseSchema}}
    )

    def put(self, controller, data, oid, *args, **kwargs):
        service = controller.get_service_type_plugin(oid)
        config = data.get("config")
        # if data.get('config').get('value') is None:
        #     resource.unset_configs(key=data.get('config').get('key'))
        # else:
        attr_value = config.get("value")
        if isinstance(attr_value, str) and attr_value.isdigit():
            attr_value = int(attr_value)

        service.set_config(config.get("key"), attr_value)
        return {"config": {"key": config.get("key"), "value": config.get("value")}}


class ServiceInstanceAPI(ApiView):
    """PluginTypeInstance api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"
        rules = [
            ("%s/serviceinsts" % base, "GET", ListServiceInstances, {}),
            ("%s/serviceinsts" % base, "POST", CreateServiceInstance, {}),
            ("%s/serviceinsts/import" % base, "POST", ImportInstance, {}),
            ("%s/serviceinsts/<oid>" % base, "GET", GetServiceInstance, {}),
            ("%s/serviceinsts/<oid>" % base, "PUT", UpdateServiceInstance, {}),
            ("%s/serviceinsts/<oid>" % base, "PATCH", PatchServiceInstance, {}),
            ("%s/serviceinsts/<oid>" % base, "DELETE", DeleteServiceInstance, {}),
            ("%s/serviceinsts/<oid>/check" % base, "GET", CheckServiceInstance, {}),
            (
                "%s/serviceinsts/<oid>/status" % base,
                "PUT",
                UpdateServiceInstanceStatus,
                {},
            ),
            # ('%s/serviceinsts/<oid>/links' % base, 'GET', GetServiceInstanceLinks, {}),
            (
                "%s/serviceinsts/<oid>/linked" % base,
                "GET",
                GetLinkedServiceInstances,
                {},
            ),
            ("%s/serviceinsts/<oid>/config" % base, "PUT", UpdateServiceConfig, {}),
            ("%s/serviceinsts/account/<oid>" % base, "PUT", UpdateAccountServiceInstance, {}),
        ]

        kwargs["version"] = "v2.0"
        ApiView.register_api(module, rules, **kwargs)
