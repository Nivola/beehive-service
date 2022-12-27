# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema, \
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema, SwaggerApiView, \
    ApiManagerWarning
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.entity.service_instance import ApiServiceLinkInst, ApiServiceInstance, ApiServiceInstanceConfig
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema, \
    ApiObjectRequestFiltersSchema, ApiServiceObjectCreateRequestSchema
from beehive_service.model import SrvStatusType
from beehive.common.data import transaction
from beehive_service.service_util import ServiceUtil
from beehive_service.controller import ApiServiceType


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

    def get(self, controller, data, *args, **kvargs):
        servicetags = data.pop('tags', None)
        if servicetags is not None and servicetags.find('+') > 0:
            data['servicetags_and'] = servicetags.split('+')
        elif servicetags is not None:
            data['servicetags_or'] = servicetags.split(',')

        service, total = controller.get_paginated_service_instances(**data)
        res = [r.info() for r in service]
        return self.format_paginated_response(res, 'serviceinsts', total, **data)


class CreateServiceInstanceParamRequestSchema(ApiServiceObjectCreateRequestSchema):
    account_id = fields.String(required=True)
    service_def_id = fields.String(required=True)
    parent_id = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, allow_none=True)
    status = fields.String(required=False, default=SrvStatusType.PENDING)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    hierarchy = fields.Boolean(required=False, missing=True, description='If True create service instance hierarchy')


class CreateServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(CreateServiceInstanceParamRequestSchema, context='body')


class CreateServiceInstanceBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceInstanceRequestSchema, context='body')


class CreateServiceInstance(ServiceApiView):
    tags = ['service']
    definitions = {
        'CreateServiceInstanceRequestSchema': CreateServiceInstanceRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceInstanceBodyRequestSchema)
    parameters_schema = CreateServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kvargs):
        hierarchy = data.get('serviceinst').get('hierarchy')
        uuid = None
        # hierarchy creation
        if hierarchy is True:
            # Create tree hierarchy SI
            oid = data.get('serviceinst').pop('service_def_id')
            rootInstance = controller.createInstanceHierachy(oid, **data.get('serviceinst'))
            pluginRoot = ApiServiceType(controller).instancePlugin(rootInstance.id)

            # Create tree hierarchy Resource
            uuid = pluginRoot.createResource(rootInstance.id)

        # simple creation
        else:
            resp = controller.add_service_instance(**data.get('serviceinst'))
            uuid = resp.uuid
        return {'uuid': uuid}, 201


class UpdateServiceTagDescRequestSchema(Schema):
    cmd = fields.String(default='add', required=True)
    values = fields.List(fields.String(default='test'), required=True)


class UpdateServiceInstanceParamRequestSchema(Schema):
    name = fields.String(required=False)
    desc = fields.String(required=False)
    # account_id = fields.Integer(required=False)
    # service_definition_id = fields.Integer(required=False)
    status = fields.String(required=False, default=SrvStatusType.DRAFT)
    active = fields.Boolean(required=False)
    bpmn_process_id = fields.Integer(required=False, allow_none=True)
    resource_uuid = fields.String(required=False)
    tags = fields.Nested(UpdateServiceTagDescRequestSchema, allow_none=True)


class UpdateServiceInstanceRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateServiceInstanceParamRequestSchema)


class UpdateServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstanceRequestSchema, context='body')


class UpdateServiceInstance(ServiceApiView):
    tags = ['service']
    definitions = {
        'UpdateServiceInstanceRequestSchema': UpdateServiceInstanceRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstanceBodyRequestSchema)
    parameters_schema = UpdateServiceInstanceRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kvargs):
        srv_inst = controller.get_service_instance(oid)
        data = data.get('serviceinst')
        tags = data.pop('tags', None)
        self.logger.warn(tags)

        pluginCh = srv_inst.instancePlugin(oid)
        # TODO UpdateServiceInstance: selezione parametri data da passare a updateResource
        # dataResource = {}
        # if data.get('active', None) is not None:
        #     dataResource['active'] = data.get('active')
        # dataResource['attribute'] = {'key': 'value'}
        # pluginCh.updateResource(srv_inst, **dataResource)
        resp = srv_inst.update(srv_inst, **data)

        if tags is not None:
            cmd = tags.get('cmd')
            values = tags.get('values')
            # add tag
            if cmd == 'add':
                for value in values:
                    srv_inst.add_tag(value)
                    # controller.create_service_tag(srv_inst, srv_inst.account_id, value)
            elif cmd == 'delete':
                for value in values:
                    # controller.delete_service_tag(srv_inst, srv_inst.account_id, value)
                    srv_inst.remove_tag(value)

        return {'uuid': resp}, 200


class UpdateServiceInstanceStatusParamRequestSchema(Schema):
    status = fields.String(required=True, example=SrvStatusType.DRAFT)


class UpdateServiceInstanceStatusRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateServiceInstanceStatusParamRequestSchema)


class UpdateServiceInstanceStatusBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstanceStatusRequestSchema, context='body')


class UpdateServiceInstanceStatus(ServiceApiView):
    tags = ['service']
    definitions = {
        'UpdateServiceInstanceStatusRequestSchema': UpdateServiceInstanceStatusRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstanceStatusBodyRequestSchema)
    parameters_schema = UpdateServiceInstanceStatusRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kvargs):
        data = data.get('serviceinst')
        status = data.get('status', None)
        resp = controller.updateInstanceStatus(oid, status)
        return {'uuid': resp}, 200


class DeleteServiceInstanceRequestSchema(Schema):
    recursive = fields.Boolean(required=False, default=False)


class DeleteServiceInstanceBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(DeleteServiceInstanceRequestSchema, context='body')


class DeleteServiceInstance(ServiceApiView):
    tags = ['service']
    definitions = {
        'DeleteServiceInstanceRequestSchema': DeleteServiceInstanceRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteServiceInstanceBodyRequestSchema)
    parameters_schema = DeleteServiceInstanceRequestSchema
    responses = ServiceApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    @transaction
    def delete(self, controller, data, oid, *args, **kvargs):
        self.logger.info('Delete ServiceInstance START oid=%s' % oid)

        recursive_delete = data.get('recursive')
        self.logger.debug('recursive_delete: %s' % recursive_delete)

        # make soft delete of: ServiceInstance, Servicelink, ServiceConfig entity
        entity = kvargs.get('instance')
        if entity is not None and entity.oid == oid:  # in recursive call
            srv_inst = entity
        else:
            srv_inst = controller.get_service_instance(oid)

        controller.check_authorization(
            srv_inst.objtype, srv_inst.objdef,
            srv_inst.objid, action='delete')

        if srv_inst.model.linkChildren is not None and srv_inst.model.linkChildren.count() > 0:
            if not recursive_delete:
                self.logger.warn('The instance %s has children. Force deletion with parameter '
                                 '\'recursive\' to true.' % srv_inst.oid)
                raise ApiManagerWarning('The instance %s has children. Force deletion with parameter '
                                        '\'recursive\' to true.' % srv_inst.oid)

        # delete instance link Parent
        for l in srv_inst.model.linkParent:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
            api_link = ServiceUtil.instanceApi(controller, ApiServiceLinkInst, l)
            api_link.delete(soft=True)

        # delete instance link and children
        for l in srv_inst.model.linkChildren:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
            api_link = ServiceUtil.instanceApi(controller, ApiServiceLinkInst, l)
            child = ServiceUtil.instanceApi(controller, ApiServiceInstance, l.end_service)
            self.delete(controller, data, l.end_service_id, instance=child)

        pluginCh = srv_inst.instancePlugin(oid)
        # make delete of resource
        if srv_inst.resource_uuid is not None:
            # check resource already exists
            res = pluginCh.checkResource(srv_inst)

            # delete resource
            try:
                if res is not None:
                    resp_resource = pluginCh.deleteResource(srv_inst)
            except:
                self.logger.error('Error deleting resource', exc_info=1)
                raise

        # delete instance config
        for cfg in srv_inst.model.config:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % cfg)
            api_cfg = ServiceUtil.instanceApi(controller, ApiServiceInstanceConfig, cfg)
            api_cfg.delete(soft=True)

        resp = srv_inst.delete(soft=True)

        self.logger.info('Delete ServiceInstance END oid=%s' % oid)

        return resp, 204


class GetServiceInstancePerms(ServiceApiView):
    tags = ['service']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kvargs):
        service = controller.get_service_instance(oid)
        res, total = service.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


## update link
class UpdateServiceInstanceLinkParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    end_service_id = fields.String(required=True, allow_none=True)
    priority = fields.Integer(required=False, allow_none=True)


class UpdateServiceInstanceLinkRequestSchema(Schema):
    serviceinst = fields.Nested(UpdateServiceInstanceLinkParamRequestSchema)


class UpdateServiceInstanceLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceInstanceLinkRequestSchema, context='body')


class UpdateServiceInstanceLink(ServiceApiView):
    tags = ['service']
    definitions = {
        'UpdateServiceInstanceLinkRequestSchema': UpdateServiceInstanceLinkRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceInstanceLinkBodyRequestSchema)
    parameters_schema = UpdateServiceInstanceLinkRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kvargs):
        data = data.get('serviceinst')
        end_service_id = data.pop('end_service_id', None)

        datalink = {}
        datalink['start_service_id'] = controller.get_service_instance(oid).oid
        datalink['end_service_id'] = controller.get_service_instance(end_service_id).oid
        #
        reslink, total = controller.list_service_instlink(**datalink)

        for r in reslink:
            srv_link = controller.get_service_instlink(r.oid)
            resp = srv_link.update(**data)
            return ({'uuid': resp}, 200)
        # TODO gestione response schema for ApiManagerWarning        
        return ({'uuid': 'Link not found'}, 208)


#         raise ApiManagerWarning('Link not found', 208)


## get links
class ListServiceInstanceLinksParamsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example='default link name')
    desc = fields.String(required=True, example='default link description')
    attributes = fields.String(required=True, allow_none=True, example='default value')
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


class ListServiceInstanceLinksResponseSchema(Schema):
    links = fields.Nested(ListServiceInstanceLinksParamsResponseSchema, many=True, required=True, allow_none=True)


class GetServiceInstanceLinks(ServiceApiView):
    tags = ['service']
    definitions = {
        'ListServiceInstanceLinksResponseSchema': ListServiceInstanceLinksResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServiceInstanceLinksResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kvargs):
        res = controller.get_service_instance(oid)
        data['start_service_id'] = res.model.id
        data['size'] = 0

        service_links, total = controller.list_service_instlink(**data)
        links = [r.info() for r in service_links]
        res = {'links': links}

        return res  # self.format_paginated_response(res, 'service_links', total, **data)


class GetLinkedServiceInstancesRequestSchema(PaginatedRequestQuerySchema):
    type = fields.String(context='query')
    link_type = fields.String(context='query')
    oid = fields.String(required=True, description='id, uuid', context='path')


class GetLinkedServiceInstancesResponseSchema(PaginatedResponseSchema):
    serviceinsts = fields.Nested(GetServiceInstanceResponseSchema, many=True, required=True, allow_none=True)


class GetLinkedServiceInstances(ServiceApiView):
    tags = ['service']
    definitions = {
        'GetLinkedServiceInstancesResponseSchema': GetLinkedServiceInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetLinkedServiceInstancesRequestSchema)
    parameters_schema = GetLinkedServiceInstancesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetLinkedServiceInstancesResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        srv_inst = controller.get_service_instance(oid)
        srv_insts, total = srv_inst.get_linked_services(**data)
        res = [r.info() for r in srv_insts]
        return self.format_paginated_response(res, 'serviceinsts', total, **data)


'''
## RunInstanceApi
class RunInstanceApiRequestParamSchema(Schema):
    account_id = fields.Integer(required=True)
    params_resource = fields.String(required=True, example='{}')
    name = fields.String(required=False, default='')
    desc = fields.String(required=False, default='')
    
class RunInstanceApiRequestSchema(Schema):
    serviceinst = fields.Nested(RunInstanceApiRequestParamSchema, context='body')

class RunInstanceApiBodyRequestSchema(Schema):
    body = fields.Nested(RunInstanceApiRequestSchema, context='body')

    
class RunInstance(ServiceApiView):
    tags = ['service']
    definitions = {
        'RunInstanceApiRequestSchema':RunInstanceApiRequestSchema,
        'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(RunInstanceApiBodyRequestSchema)
    parameters_schema = RunInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })    
    
    def post(self, controller, data, oid, *args, **kvargs):
        
        # Create tree hierarchy SI
        self.logger.info('********************* RUN INSTANCE *****************, oid=%s' %( oid))
        rootInstance = controller.createInstanceHierachy( oid, **data.get('serviceinst'))
        
        pluginRoot = ApiServiceType(controller).instancePlugin(rootInstance.id)
        
        # Create tree hierarchy Resource
        self.logger.info('********************* create resource tree *****************, oid=%s' %( oid))
        pluginRoot.createResource(rootInstance.id)
        
        return {'uuid':rootInstance.uuid} 
    

## DescribeInstanceApi

class DescribeInstanceApiRequestSchema(Schema):
    pass

class DescribeInstanceApiResponseSchema(Schema):
    pass
    
class DescribeInstanceApi(ServiceApiView):
    tags = ['service']
    definitions = {
        'DescribeInstanceApiRequestSchema':DescribeInstanceApiRequestSchema,
        'DescribeInstanceApiResponseSchema':DescribeInstanceApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeInstanceApiRequestSchema)
    parameters_schema = DescribeInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeInstanceApiResponseSchema
        }
    })    
    
    def get(self, controller, data, oid, *args, **kvargs):
#         srv_inst = controller.get_service_instance(oid)
#         plugin = srv_inst.instancePlugin(srv_inst.oid)
#         return (plugin.getResourceTreeInfo(srv_inst), 200)
        pass


## DescribeSingleInstanceApi
class DescribeSingleInstanceApiRequestSchema(Schema):
    pass

class DescribeSingleInstanceApiResponseSchema(Schema):
    pass
    
class DescribeSingleInstanceApi(ServiceApiView):
    tags = ['service']
    definitions = {
        'DescribeSingleInstanceApiRequestSchema':DescribeSingleInstanceApiRequestSchema,
        'DescribeSingleInstanceApiResponseSchema':DescribeSingleInstanceApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeSingleInstanceApiRequestSchema)
    parameters_schema = DescribeSingleInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
# TODO DescribeSingleInstanceApi: response schema to be defined'
            'schema': DescribeSingleInstanceApiResponseSchema
        }
    })     
    def get(self, controller, data, oid, *args, **kvargs):
        srv_inst = controller.get_service_instance(oid)
        plugin = srv_inst.instancePlugin(srv_inst.oid)
        return (plugin.getResourceInfo(srv_inst), 200)

## StartInstanceApi
class StartInstanceApiRequestSchema(Schema):
    pass

class StartInstanceApiResponseSchema(Schema):
    pass
    
class StartInstanceApi(ServiceApiView):
    tags = ['service']
    definitions = {
        'StartInstanceApiRequestSchema':StartInstanceApiRequestSchema,
        'StartInstanceApiResponseSchema':StartInstanceApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(StartInstanceApiRequestSchema)
    parameters_schema = StartInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': StartInstanceApiResponseSchema
        }
    })    
    
    def get(self, controller, data, oid, *args, **kvargs):
        res = {
            'StartInstanceApi': {
                '__xmlns':'http://nivolapiemonte.it/XMLdoc/2016-11-15/',
            }
        }
        return res

## StopInstanceApi
class StopInstanceApiRequestSchema(Schema):
    pass

class StopInstanceApiResponseSchema(Schema):
    pass
    
class StopInstanceApi(ServiceApiView):
    tags = ['service']
    definitions = {
        'StopInstanceApiRequestSchema':StopInstanceApiRequestSchema,
        'StopInstanceApiResponseSchema':StopInstanceApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(StopInstanceApiRequestSchema)
    parameters_schema = StopInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': StopInstanceApiResponseSchema
        }
    })    
    
    def get(self, controller, data, oid, *args, **kvargs):
        res = {
            'StopInstanceApi': {
                '__xmlns':'http://nivolapiemonte.it/XMLdoc/2016-11-15/',
            }
        }
        return res

## TerminateInstanceApi
class TerminateInstanceApiRequestSchema(Schema):
    pass

class TerminateInstanceApiResponseSchema(Schema):
    pass
    
class TerminateInstanceApi(ServiceApiView):
    tags = ['service']
    definitions = {
        'TerminateInstanceApiRequestSchema':TerminateInstanceApiRequestSchema,
        'TerminateInstanceApiResponseSchema':TerminateInstanceApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(TerminateInstanceApiRequestSchema)
    parameters_schema = TerminateInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': TerminateInstanceApiResponseSchema
        }
    })    
    
    def get(self, controller, data, oid, *args, **kvargs):
        res = {
            'TerminateInstanceApi': {
                '__xmlns':'http://nivolapiemonte.it/XMLdoc/2016-11-15/',
            }
        }
        return res'''


###########################################################################
## bpmn user task
class ServiceTaskResponseSchema(ApiObjectResponseSchema):
    task_name = fields.String(required=False, default='')
    instance_id = fields.String(required=True, example='')
    task_id = fields.String(required=True, example='')
    execution_id = fields.String(required=False, default='')
    due_date = fields.DateTime(required=False)
    created = fields.DateTime(required=False)


class ServiceTaskListResponseSchema(Schema):
    tasks = fields.Nested(ServiceTaskResponseSchema, many=True, required=True, allow_none=True)
    # tasks = fields.List(ServiceTaskResponseSchema, required=True, allow_none=True)


class ServiceUserTasksList(ServiceApiView):
    tags = ['service']
    definitions = {
        'ServiceTaskListResponseSchema': ServiceTaskListResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ServiceTaskListResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get account
        Call this api to get a specific account
        """
        res = controller.serviceinstance_user_task_list(oid)
        resp = {'tasks': res}
        return (resp, 200)


####

class ServiceTaskDetailRequestSchema(GetApiObjectRequestSchema):
    taskid = fields.String(required=True, description='attribute name',
                           context='path')


class ServiceTaskDetaiLResponseSchema(Schema):
    variables = fields.Dict()


class GetServiceTasksDetail(ServiceApiView):
    tags = ['service']
    definitions = {
        'ServiceTaskListResponseSchema': ServiceTaskDetaiLResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ServiceTaskDetailRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ServiceTaskDetaiLResponseSchema
        }
    })

    def get(self, controller, data, oid, taskid, *args, **kwargs):
        """
        Get task variables
        """
        res = controller.user_task_detail(oid, task_id=taskid)
        resp = {'variables': res}
        return (resp, 200)


class SetServiceTasksDetail(ServiceApiView):
    tags = ['service']
    definitions = {
        'ServiceTaskListResponseSchema': ServiceTaskListResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ServiceTaskDetailRequestSchema)
    parameters_schema = ServiceTaskDetaiLResponseSchema

    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            # 'schema': GetServiceTasksResponseSchema
        }
    })

    def post(self, controller, data, oid, taskid, *args, **kwargs):
        """
        Complete Task and set variables
        """
        res = controller.complete_user_task(oid, taskid, data.get('variables'))
        controller.serviceinstance_user_task_list(oid)
        return (res, 200)


class ServiceInstanceAPI(ApiView):
    """ServiceInstance api routes:
    """

    @staticmethod
    def register_api(module, rules=None, version=None):
        base = 'nws'
        rules = [
            ('%s/serviceinsts' % base, 'GET', ListServiceInstances, {}),
            ('%s/serviceinsts' % base, 'POST', CreateServiceInstance, {}),
            ('%s/serviceinsts/<oid>' % base, 'GET', GetServiceInstance, {}),
            ('%s/serviceinsts/<oid>' % base, 'PUT', UpdateServiceInstance, {}),
            ('%s/serviceinsts/<oid>/status' % base, 'PUT', UpdateServiceInstanceStatus, {}),
            ('%s/serviceinsts/<oid>' % base, 'DELETE', DeleteServiceInstance, {}),
            ('%s/serviceinsts/<oid>/perms' % base, 'GET', GetServiceInstancePerms, {}),
            ('%s/serviceinsts/<oid>/link' % base, 'PUT', UpdateServiceInstanceLink, {}),
            ('%s/serviceinsts/<oid>/links' % base, 'GET', GetServiceInstanceLinks, {}),
            ('%s/serviceinsts/<oid>/linked' % base, 'GET', GetLinkedServiceInstances, {}),
            ('%s/serviceinsts/<oid>/task' % base, 'GET', ServiceUserTasksList, {}),
            ('%s/serviceinsts/<oid>/task/<taskid>' % base, 'GET', GetServiceTasksDetail, {}),
            ('%s/serviceinsts/<oid>/task/<taskid>' % base, 'POST', SetServiceTasksDetail, {}),
        ]

        ApiView.register_api(module, rules)
