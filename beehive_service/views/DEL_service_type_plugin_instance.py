# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from marshmallow import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiView, CrudApiObjectResponseSchema, SwaggerApiView, PaginatedResponseSchema, \
    ApiObjectRequestFiltersSchema, PaginatedRequestQuerySchema, ApiObjectResponseSchema, GetApiObjectRequestSchema, \
    ApiManagerWarning
from beehive_service.entity.service_type import ApiServiceType
from beehive_service.model import SrvStatusType
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema, ApiServiceObjectCreateRequestSchema


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
    tags = [u'service']
    definitions = {
        u'GetPluginTypeInstanceResponseSchema': GetPluginTypeInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetPluginTypeInstanceResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kvargs):
        plugin = controller.get_service_type_plugin(oid)
        return {u'plugin': plugin.detail()}


class ListPluginTypeInstancesRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                           PaginatedRequestQuerySchema):
    account_id = fields.String(required=False, context=u'query')
    service_definition_id = fields.String(required=False, context=u'query')
    status = fields.String(required=False, context=u'query')
    bpmn_process_id = fields.Integer(required=False, context=u'query')
    resource_uuid = fields.String(required=False, context=u'query')
    parent_id = fields.String(required=False, context=u'query')
    plugintype = fields.String(required=False, context=u'query')
    tags = fields.String(context=u'query', description=u'List of tags. Use comma as separator if tags are in or. Use + '
                                                       u'separator if tags are in and')
    flag_container = fields.Boolean(context=u'query', description=u'if True show only container instances')


class ListPluginTypeInstancesResponseSchema(PaginatedResponseSchema):
    plugins = fields.Nested(GetPluginTypeInstanceParamsResponseSchema, many=True, required=True, allow_none=True)


class ListPluginTypeInstances(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListPluginTypeInstancesResponseSchema': ListPluginTypeInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListPluginTypeInstancesRequestSchema)
    parameters_schema = ListPluginTypeInstancesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListPluginTypeInstancesResponseSchema
        }
    })

    def get(self, controller, data, *args, **kvargs):
        servicetags = data.pop(u'tags', None)
        if servicetags is not None and servicetags.find(u'+') > 0:
            data[u'servicetags_and'] = servicetags.split(u'+')
        elif servicetags is not None:
            data[u'servicetags_or'] = servicetags.split(u',')

        service, total = controller.get_service_type_plugins(**data)
        res = [r.info() for r in service]
        return self.format_paginated_response(res, u'plugins', total, **data)


class CreatePluginTypeInstanceParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    account_id = fields.String(required=True, description=u'id of the account')
    service_def_id = fields.String(required=True, description=u'id of the service definition')
    parent_id = fields.String(required=False, allow_none=True, description=u'id of the parent service instance')
    priority = fields.Integer(required=False, allow_none=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    hierarchy = fields.Boolean(required=False, missing=True, description=u'If True create service instance hierarchy')


class CreatePluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(CreatePluginTypeInstanceParamRequestSchema, context=u'body')


class CreatePluginTypeInstanceBodyRequestSchema(Schema):
    body = fields.Nested(CreatePluginTypeInstanceRequestSchema, context=u'body')


class CreatePluginTypeInstance(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreatePluginTypeInstanceRequestSchema': CreatePluginTypeInstanceRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreatePluginTypeInstanceBodyRequestSchema)
    parameters_schema = CreatePluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kvargs):
        """
        Crea una service instance utilizzando uno specifico plugin type
        Crea una service instance utilizzando uno specifico plugin type
        TODO
        """
        hierarchy = data.get(u'serviceinst').get(u'hierarchy')
        uuid = None
        # hierarchy creation
        if hierarchy is True:
            # Create tree hierarchy SI
            oid = data.get(u'serviceinst').pop(u'service_def_id')
            rootInstance = controller.createInstanceHierachy(oid, **data.get(u'serviceinst'))
            pluginRoot = ApiServiceType(controller).instancePlugin(rootInstance.id)

            # Create tree hierarchy Resource
            uuid = pluginRoot.createResource(rootInstance.id)

        # simple creation
        else:
            resp = controller.add_service_instance(**data.get(u'plugin'))
            uuid = resp.uuid
        return {u'uuid': uuid}, 201


class ImportPluginTypeInstanceParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    account_id = fields.String(required=True, description=u'id of the account')
    plugintype = fields.String(required=True, description=u'plugin type name')
    container_plugintype = fields.String(required=True, description=u'container plugin type name')
    service_definition_id = fields.String(required=False, missing=None, description=u'id of the service definition')
    parent_id = fields.String(required=False, allow_none=True, missing=None,
                              description=u'id of the parent service instance')
    resource_id = fields.String(required=True, allow_none=False, description=u'id of the resource')


class ImportPluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(ImportPluginTypeInstanceParamRequestSchema, context=u'body')


class ImportPluginTypeInstanceBodyRequestSchema(Schema):
    body = fields.Nested(ImportPluginTypeInstanceRequestSchema, context=u'body')


class ImportPluginTypeInstance(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ImportPluginTypeInstanceRequestSchema': ImportPluginTypeInstanceRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(ImportPluginTypeInstanceBodyRequestSchema)
    parameters_schema = ImportPluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kvargs):
        """
        Crea una service instance utilizzando uno specifico plugin type pertendo da una risorsa esistente
        Crea una service instance utilizzando uno specifico plugin type pertendo da una risorsa esistente
        """
        data = data.get(u'plugin')
        account_id = data.get(u'account_id')
        service_definition_id = data.get(u'service_definition_id')
        name = data.get(u'name')
        desc = name
        plugintype = data.get(u'plugintype')
        container_plugintype = data.get(u'container_plugintype')
        parent_id = data.get(u'parent_id')
        resource_id = data.get(u'resource_id')

        # check account with compute service
        # account, container_plugin = self.check_parent_service(controller, data.get(u'account_id'),
        #                                                       plugintype=container_plugintype)

        # check parent container service
        account = controller.get_account(account_id)

        # check if the account is associated to a Compute Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype=u'ComputeService')
        if total == 0:
            raise ApiManagerWarning(u'Account %s has not %s' % (account.oid, plugintype))
        compute_zone = insts[0].resource_uuid

        # check if the account is associated to the required container Service
        insts, total = controller.get_service_type_plugins(account_id=account.oid, plugintype=container_plugintype)
        if total == 0:
            raise ApiManagerWarning(u'Account %s has not %s' % (account.oid, plugintype))

        container_plugin = insts[0]

        if container_plugin.is_active() is False:
            raise ApiManagerWarning(u'Account %s %s is not in a correct status' % (account_id, plugintype))

        # checks authorization user on container service instance
        if container_plugin.instance.verify_permisssions(u'update') is False:
            raise ApiManagerWarning(u'User does not have the required permissions to make this action')

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
            u'owner_id': account.uuid,
            u'service_definition_id': service_definition_id,
            u'computeZone': compute_zone
        }
        plugin = controller.import_service_type_plugin(service_definition_id, account.oid, name=name, desc=desc,
                                                       parent_plugin=parent_plugin, instance_config=config,
                                                       resource_id=resource_id)

        return {u'uuid': plugin.instance.uuid}, 201


class UpdatePluginTypeInstanceTagRequestSchema(Schema):
    cmd = fields.String(default=u'add', required=True)
    values = fields.List(fields.String(default=u'test'), required=True)


class UpdatePluginTypeInstanceParamRequestSchema(Schema):
    # name = fields.String(required=False)
    # desc = fields.String(required=False)
    # account_id = fields.Integer(required=False)
    # service_definition_id = fields.Integer(required=False)
    # status = fields.String(required=False, default=SrvStatusType.DRAFT)
    # active = fields.Boolean(required=False)
    # bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, description=u'uuid of the new resource')
    tags = fields.Nested(UpdatePluginTypeInstanceTagRequestSchema, allow_none=True)
    parent_id = fields.String(required=False, allow_none=True, description=u'id of the parent service instance')


class UpdatePluginTypeInstanceRequestSchema(Schema):
    plugin = fields.Nested(UpdatePluginTypeInstanceParamRequestSchema, context=u'body')


class UpdatePluginTypeInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdatePluginTypeInstanceRequestSchema, context=u'body')


class UpdatePluginTypeInstance(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'DeletePluginTypeInstanceRequestSchema': UpdatePluginTypeInstanceRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdatePluginTypeInstanceBodyRequestSchema)
    parameters_schema = UpdatePluginTypeInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kvargs):
        """
        Modifica una service instance utilizzando uno specifico plugin type
        Modifica una service instance utilizzando uno specifico plugin type
        """
        type_plugin = controller.get_service_type_plugin(oid)
        type_plugin.update(**data.get(u'plugin'))

        return True, 201


class DeletePluginTypeInstanceRequestSchema(Schema):
    propagate = fields.Boolean(required=False, default=True, description=u'If True propagate delete to all cmp modules')
    force = fields.Boolean(required=False, default=False, description=u'If True force delete')


class DeletePluginTypeInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeletePluginTypeInstanceRequestSchema, context=u'body')


class DeletePluginTypeInstance(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'DeletePluginTypeInstanceRequestSchema': DeletePluginTypeInstanceRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeletePluginTypeInstanceBodyRequestSchema)
    parameters_schema = DeletePluginTypeInstanceRequestSchema
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        type_plugin.delete(**data)

        return True, 204


class UpdatePluginStatusParamRequestSchema(Schema):
    status = fields.String(required=True, example=SrvStatusType.DRAFT)


class UpdatePluginStatusRequestSchema(Schema):
    plugin = fields.Nested(UpdatePluginStatusParamRequestSchema)


class UpdatePluginStatusBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdatePluginStatusRequestSchema, context=u'body')


class UpdatePluginStatus(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdatePluginStatusRequestSchema': UpdatePluginStatusRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdatePluginStatusBodyRequestSchema)
    parameters_schema = UpdatePluginStatusRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kvargs):
        type_plugin = controller.get_service_type_plugin(oid)
        status = data.get(u'plugin', {}).get(u'status', None)
        resp = False
        if status is not None:
            type_plugin.update_status(status)
            resp = True

        return resp, 200


class ServicePluginTypeInstanceAPI(ApiView):
    """PluginTypeInstance api routes:
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/plugins' % base, u'GET', ListPluginTypeInstances, {}),
            (u'%s/plugins' % base, u'POST', CreatePluginTypeInstance, {}),
            (u'%s/plugins/import' % base, u'POST', ImportPluginTypeInstance, {}),
            (u'%s/plugins/<oid>' % base, u'GET', GetPluginTypeInstance, {}),
            (u'%s/plugins/<oid>' % base, u'PUT', UpdatePluginTypeInstance, {}),
            (u'%s/plugins/<oid>' % base, u'DELETE', DeletePluginTypeInstance, {}),
            (u'%s/plugins/<oid>/status' % base, u'PUT', UpdatePluginStatus, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
