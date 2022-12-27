# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema,\
    ApiObjecCountResponseSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema,\
    ApiObjectRequestFiltersSchema, ApiServiceObjectCreateRequestSchema

       

#
# service instance link
#
## list
class ListLinksRequestSchema(ApiServiceObjectRequestSchema, 
                             ApiObjectRequestFiltersSchema,
                             PaginatedRequestQuerySchema):
    name = fields.String(required=False, context=u'query')
    desc = fields.String(required=False, context=u'query')
    attributes = fields.String(required=False, context=u'query')
    start_service_id = fields.String(required=False, context=u'query')
    end_service_id = fields.String(required=False, context=u'query')
    priority = fields.Integer(required=False, context=u'query')
   
class ListLinksParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name=fields.String(required=True, example=u'default link name')
    desc=fields.String(required=True, example=u'default link description')
    attributes = fields.String(required=True, example=u'default value')
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)
     
# # TODO ListLinksParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa     
class ListLinksParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListLinksParamsDetailsResponseSchema)
  
class ListLinksResponseSchema(PaginatedResponseSchema):
    instancelinks = fields.Nested(ListLinksParamsDetailsResponseSchema, 
                                  many=True, 
                                  required=True, allow_none=True)
 
class ListLinks(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListLinksResponseSchema': ListLinksResponseSchema,
        u'ListLinksRequestSchema': ListLinksRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListLinksRequestSchema)
    parameters_schema = ListLinksRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListLinksResponseSchema
        }
    })
  
    def get(self, controller, data, *args, **kwargs):     
        service_links, total = controller.list_service_instlink(**data)
        res = [r.info() for r in service_links]
        return self.format_paginated_response(res, u'instancelinks', total, **data)

## count
class CountLinks(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ApiObjecCountResponseSchema': ApiObjecCountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjecCountResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        resp = controller.count_service_instlinks()
        return {u'count':int(resp)}

## get
class GetLinkParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name=fields.String(required=True, example=u'default link name')
    desc=fields.String(required=True, example=u'default link description')
#     attributes = fields.Dict(required=True, example={})
    attributes = fields.String(required=False, default=u'')
    start_service_id = fields.String (required=True)
    end_service_id = fields.String (required=True)
    priority = fields.Integer(Required=True, example=0)

# TODO GetLinkParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class GetLinkParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(GetLinkParamsDetailsResponseSchema, required=True, allow_none=True)

class GetLinkResponseSchema(Schema):
    service_link = fields.Nested(GetLinkParamsDetailsResponseSchema, required=True, allow_none=True)

class GetLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetLinkResponseSchema': GetLinkResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetLinkResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        res = controller.get_service_instlink(oid)     
        resp = {u'service_link':res.detail()}        
        return resp

## get perms
class GetLinkPerms(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        link = controller.get_service_instlink(oid)
        res, total = link.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)
    
## create
class CreateLinkParamRequestSchema(Schema):
# TODO CreateLinkParamRequestSchema getsione campi di tipo DICT
#     attributes = fields.Dict(required=False, default={})
    name = fields.String(required=False, default=u'')
    desc = fields.String(required=False, allow_none=True)
    attributes = fields.String(required=False, default=u'')
    start_service_id = fields.String(required=True, allow_none=False)
    end_service_id = fields.String(required=True, allow_none=False)
    priority = fields.Integer(required=False)


class CreateLinkRequestSchema(Schema):
    instancelink = fields.Nested(CreateLinkParamRequestSchema, 
                                 context=u'body')
    
class CreateLinkBodyRequestSchema(Schema):
    body = fields.Nested(CreateLinkRequestSchema, context=u'body')

class CreateLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateLinkRequestSchema': CreateLinkRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateLinkBodyRequestSchema)
    parameters_schema = CreateLinkRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_instlink(**data.get(u'instancelink'))
        return ({u'uuid':resp}, 201)

## update
class UpdateLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default=u'default link name')
    desc = fields.String(required=False, default=u'default link description')
    attributes = fields.Dict(required=False, default={})
    priority = fields.Integer(required=False)
    active = fields.Boolean(required=False, default=False)

class UpdateLinkRequestSchema(Schema):
    instancelink = fields.Nested(UpdateLinkParamRequestSchema)

class UpdateLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateLinkRequestSchema, context=u'body')
    
class UpdateLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateLinkRequestSchema':UpdateLinkRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateLinkBodyRequestSchema)
    parameters_schema = UpdateLinkRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def put(self, controller, data, oid, *args, **kwargs):
        srv_instlink = controller.get_service_instlink(oid)
        resp = srv_instlink.update(**data.get(u'instancelink'))
        return ({u'uuid':resp}, 200)
    
## delete
class DeleteLink(ServiceApiView):
    tags = [u'service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
#         link = controller.delete_service_instlink(oid)
#         resp = link.delete()

        srv_instlink = controller.get_service_instlink(oid)
        resp = srv_instlink.delete(soft=True)
        return (resp, 204)
    
class ServiceInstLinkAPI(ApiView):
    """Service Link Instance api routes:    
    * /serviceinstlinks - **GET**
    * /serviceinstlinks - **POST**            
    * /serviceinstlinks/count - **GET**
    * /serviceinstlinks/<oid> - **GET**
    * /serviceinstlinks/<oid> - **DELETE**
    * /serviceinstlinks/<oid> - **PUT**
    * /serviceinstlinks/<oid>/perms - **GET**

    """
    @staticmethod
    def register_api(module, rules=None, version=None):
        base = u'nws'
        rules = [
            (u'%s/serviceinstlinks' % base, u'GET', ListLinks, {}),
            (u'%s/serviceinstlinks' % base, u'POST', CreateLink, {}),            
            (u'%s/serviceinstlinks/count' % base, u'GET', CountLinks, {}),
            (u'%s/serviceinstlinks/<oid>' % base, u'GET', GetLink, {}),            
  
            (u'%s/serviceinstlinks/<oid>' % base, u'DELETE', DeleteLink, {}),
            (u'%s/serviceinstlinks/<oid>' % base, u'PUT', UpdateLink, {}),
            (u'%s/serviceinstlinks/<oid>/perms' % base, u'GET', GetLinkPerms, {}),     
       ]

        ApiView.register_api(module, rules)