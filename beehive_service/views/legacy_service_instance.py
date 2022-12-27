# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    GetApiObjectRequestSchema, SwaggerApiView
    # CrudApiObjectResponseSchema, ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema, \
    # ApiManagerWarning
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
# from beehive_service.entity.service_instance import ApiServiceLinkInst, ApiServiceInstance, ApiServiceInstanceConfig
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema, \
    ApiObjectRequestFiltersSchema, ApiServiceObjectCreateRequestSchema
from beehive_service.model import SrvStatusType
# from beehive.common.data import transaction
# from beehive_service.service_util import ServiceUtil
# from beehive_service.controller import ApiServiceType


class GetServiceInstanceParamsResponseSchema(ApiObjectResponseSchema):
    account_id = fields.String(required=True)
    service_definition_id = fields.String(required=True)
    status = fields.String(required=False, default=SrvStatusType.RELEASED)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False, allow_none=True)
    config = fields.Dict(required=False, allow_none=True)


class GetServiceInstanceResponseSchema(Schema):
    serviceinst = fields.Nested(GetServiceInstanceParamsResponseSchema, required=True, allow_none=True)


class GetServiceInstance(ServiceApiView):
    tags = ['service']
    definitions = {
        'GetServiceInstanceResponseSchema': GetServiceInstanceResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetServiceInstanceResponseSchema
        }
    })
    response_schema = GetServiceInstanceResponseSchema

    def get(self, controller, data, oid, *args, **kvargs):
        srv_inst = controller.get_service_instance(oid)
        return {'serviceinst': srv_inst.detail()}


class ListServiceInstancesRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                        PaginatedRequestQuerySchema):
    account_id = fields.String(required=False, context='query')
    service_definition_id = fields.String(required=False, context='query')
    status = fields.String(required=False, context='query')
    bpmn_process_id = fields.Integer(required=False, context='query')
    resource_uuid = fields.String(required=False, context='query')
    parent_id = fields.String(required=False, context='query')
    plugintype = fields.String(required=False, context='query')
    tags = fields.String(context='query', description='List of tags. Use comma as separator if tags are in or. Use + '
                                                       'separator if tags are in and')
    flag_container = fields.Boolean(context='query', description='if True show only container instances')


class ListServiceInstancesResponseSchema(PaginatedResponseSchema):
    serviceinsts = fields.Nested(GetServiceInstanceParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceInstances(ServiceApiView):
    tags = ['service']
    definitions = {
        'ListServiceInstancesResponseSchema': ListServiceInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceInstancesRequestSchema)
    parameters_schema = ListServiceInstancesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServiceInstancesResponseSchema
        }
    })
    response_schema = ListServiceInstancesResponseSchema

    def get(self, controller, data, *args, **kvargs):
        servicetags = data.pop('tags', None)
        if servicetags is not None and servicetags.find('+') > 0:
            data['servicetags_and'] = servicetags.split('+')
        elif servicetags is not None:
            data['servicetags_or'] = servicetags.split(',')

        service, total = controller.get_paginated_service_instances(**data)
        res = [r.info() for r in service]
        return self.format_paginated_response(res, 'serviceinsts', total, **data)


class ServiceInstanceAPI(ApiView):
    """ServiceInstance api routes:
    """

    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/serviceinsts' % base, 'GET', ListServiceInstances, {}),
            # ('%s/serviceinsts' % base, 'POST', CreateServiceInstance, {}),
            ('%s/serviceinsts/<oid>' % base, 'GET', GetServiceInstance, {}),
            # ('%s/serviceinsts/<oid>' % base, 'PUT', UpdateServiceInstance, {}),
            # ('%s/serviceinsts/<oid>/status' % base, 'PUT', UpdateServiceInstanceStatus, {}),
            # ('%s/serviceinsts/<oid>' % base, 'DELETE', DeleteServiceInstance, {}),
            # ('%s/serviceinsts/<oid>/perms' % base, 'GET', GetServiceInstancePerms, {}),
            # ('%s/serviceinsts/<oid>/link' % base, 'PUT', UpdateServiceInstanceLink, {}),
            # ('%s/serviceinsts/<oid>/links' % base, 'GET', GetServiceInstanceLinks, {}),
            # ('%s/serviceinsts/<oid>/linked' % base, 'GET', GetLinkedServiceInstances, {}),
            # ('%s/serviceinsts/<oid>/task' % base, 'GET', ServiceUserTasksList, {}),
            # ('%s/serviceinsts/<oid>/task/<taskid>' % base, 'GET', GetServiceTasksDetail, {}),
            # ('%s/serviceinsts/<oid>/task/<taskid>' % base, 'POST', SetServiceTasksDetail, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
