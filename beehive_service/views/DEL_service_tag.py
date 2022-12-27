# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from beehive.common.data import transaction, trace
from beehive.common.apimanager import  PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema,\
    SwaggerApiView,\
    ApiView, ApiManagerError
from flasgger import fields, Schema

from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectResponseSchema
from beehive_service.controller import ApiServiceTag, ApiServiceInstance
from beecell.simple import id_gen
from beehive_service.model import ServiceTag
from beecell.db import QueryError, TransactionError


## get


class GetServiceTagResponseSchema(Schema):
    servicetag = fields.Nested(ApiServiceObjectResponseSchema, 
                             required=True, allow_none=True)

class GetServiceTag(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetServiceTagResponseSchema': GetServiceTagResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetServiceTagResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        servicetag = controller.get_service_tag(oid)
        return {u'servicetag':servicetag.detail()} 


## list
class ListServiceTagRequestSchema(PaginatedRequestQuerySchema):
    version=fields.String(Required=False, context=u'query')
    name=fields.String(Required=False, context=u'query')
    objid=fields.String(Required=False, context=u'query')


class ListServiceTagResponseSchema(PaginatedResponseSchema):
    servicetags = fields.Nested(ApiServiceObjectResponseSchema, 
                                  many=True, required=True, allow_none=True)


class ListServiceTag(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListServiceTagResponseSchema': ListServiceTagResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceTagRequestSchema)
    parameters_schema = ListServiceTagRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListServiceTagResponseSchema
        }
    })

    def get(self, controller, data,   *args, **kwargs):
        self.logger.info(u'TESTData33 = %s' %data)
        service_tag, total = controller.get_service_tags( **data)
        res = [r.info() for r in service_tag]
        return self.format_paginated_response(res, u'servicetags', total, **data)
    
## create
class CreateServiceTagParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    fk_parent_id = fields.Integer(required=False, allow_none=True)
    version = fields.String(required=True)
    
    
class CreateServiceTagRequestSchema(Schema):
    servicetag = fields.Nested(CreateServiceTagParamRequestSchema, 
                                 context=u'body')
    
class CreateServiceTagBodyRequestSchema(Schema):
    body = fields.Nested(CreateServiceTagRequestSchema, context=u'body')

class CreateServiceTag(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateServiceTagRequestSchema': CreateServiceTagRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateServiceTagBodyRequestSchema)
    parameters_schema = CreateServiceTagRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    @staticmethod
    @trace(entity=u'ApiServiceTag', op=u'insert')
    def add_service_tag(controller, name=u'', desc=None,  
            active=False):
        
        """ """
        
        # check authorization
        controller.check_authorization(ApiServiceInstance.objtype, 
                                 ApiServiceInstance.objdef, 
                                 None, u'update')
        try:
            # create organization reference
            objid = id_gen()
            
            srv_tag = ServiceTag(objid=objid, name=name, 
                                  desc=desc, active=active)
            
            res = controller.manager.add(srv_tag)
            # create object and permission
            
            ApiServiceTag(controller, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            CreateServiceTag.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    def post(self, controller, data, *args, **kwargs):
        resp = self.add_service_tag(controller, **data.get(u'servicetag'))
        return ({u'uuid':resp}, 201)


## update
class UpdateServiceTagParamRequestSchema(Schema):
    name = fields.String(required=False, allow_none=True)
    desc = fields.String(required=False, allow_none=True)
    fk_parent_id = fields.Integer(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True)
    
class UpdateServiceTagRequestSchema(Schema):
    servicetag = fields.Nested(UpdateServiceTagParamRequestSchema)

class UpdateServiceTagBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateServiceTagRequestSchema, context=u'body')
    
class UpdateServiceTag(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateServiceTagRequestSchema':UpdateServiceTagRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateServiceTagBodyRequestSchema)
    parameters_schema = UpdateServiceTagRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def put(self, controller, data, oid, *args, **kwargs):
        srv_tag = controller.get_service_tag(oid)
        data = data.get(u'servicetag')
        
        resp = srv_tag.update(**data)
        return ({u'uuid':resp}, 200)
    
class DeleteServiceTag(ServiceApiView):
    tags = [u'service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    @transaction
    def delete(self, controller, data, oid, *args, **kwargs):
        srv_tag = controller.get_service_tag(oid)
        
        # Delete cascate on childs
        if srv_tag.fk_parent_id is not None:
            self.delete(controller, data, srv_tag.fk_parent_id,
                        *args, **kwargs)
        
        resp = srv_tag.delete(soft=True)
        return (resp, 204)
    
    
## get perms
class GetServiceTagPerms(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        servicetag = controller.get_service_tag(oid)
        res, total = servicetag.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)
    
class ServiceTagAPI(ApiView):
    """ServiceInstance api routes:
    """
    @staticmethod
    def register_api(module):
        base = u'nws'
        rules = [
            (u'%s/servicetags' % base, u'GET', ListServiceTag, {}),
            (u'%s/servicetags' % base, u'POST', CreateServiceTag, {}),
            (u'%s/servicetags/<oid>' % base, u'GET', GetServiceTag, {}),
            (u'%s/servicetags/<oid>' % base, u'PUT', UpdateServiceTag, {}),
            (u'%s/servicetags/<oid>' % base, u'DELETE', DeleteServiceTag, {}),            
            (u'%s/servicetags/<oid>/perms' % base, u'GET', GetServiceTagPerms, {}),
        ]

        ApiView.register_api(module, rules)
