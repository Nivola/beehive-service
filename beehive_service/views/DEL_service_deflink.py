# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema, \
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema, \
    ApiObjecCountResponseSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema, \
    ApiObjectRequestFiltersSchema


#
# service definition link
#
## list
class ListDefLinksRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                PaginatedRequestQuerySchema):
    name = fields.String(required=False, context=u'query')
    desc = fields.String(required=False, context=u'query')
    attributes = fields.String(required=False, context=u'query')
    start_service_id = fields.String(required=False, context=u'query')
    end_service_id = fields.String(required=False, context=u'query')
    priority = fields.Integer(required=False, context=u'query')


class ListDefLinksParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example=u'default link name')
    desc = fields.String(required=True, example=u'default link description')
    attributes = fields.String(required=True, example=u'default value')
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# # TODO ListLinksParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa     
class ListDefLinksParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(ListDefLinksParamsDetailsResponseSchema)


class ListDefLinksResponseSchema(PaginatedResponseSchema):
    service_links = fields.Nested(ListDefLinksParamsDetailsResponseSchema,
                                  many=True,
                                  required=True, allow_none=True)


class ListDefLinks(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'ListDefLinksResponseSchema': ListDefLinksResponseSchema,
        u'ListDefLinksRequestSchema': ListDefLinksRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListDefLinksRequestSchema)
    parameters_schema = ListDefLinksRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListDefLinksResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        service_links, total = controller.list_service_instlink(**data)
        res = [r.info() for r in service_links]
        return self.format_paginated_response(res, u'service_links', total, **data)


## count
class CountDefLinks(ServiceApiView):
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
        return {u'count': int(resp)}


## get
class GetDefLinkParamsDetailsResponseSchema(ApiObjectResponseSchema):
    name = fields.String(required=True, example=u'default link name')
    desc = fields.String(required=True, example=u'default link description')
    #     attributes = fields.Dict(required=True, example={})
    attributes = fields.String(required=False, default=u'')
    start_service_id = fields.String(required=True)
    end_service_id = fields.String(required=True)
    priority = fields.Integer(Required=True, example=0)


# TODO GetDefLinkParamsResponseSchema da utilizzare se si vuole aggiungere il dettaglio della risorsa
class GetDefLinkParamsResponseSchema(ApiObjectResponseSchema):
    details = fields.Nested(GetDefLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetDefLinkResponseSchema(Schema):
    service_link = fields.Nested(GetDefLinkParamsDetailsResponseSchema, required=True, allow_none=True)


class GetLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'GetDefLinkResponseSchema': GetDefLinkResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetDefLinkResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        res = controller.get_service_deflink(oid, authorize=True)
        resp = {u'service_link': res.detail()}
        return resp


## get perms
class GetDefLinkPerms(ServiceApiView):
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
        link = controller.get_service_deflink(oid)
        res, total = link.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)


## create
class CreateDefLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default=u'default link name')
    desc = fields.String(required=False, default=u'default link description')
    #     attributes = fields.Dict(required=False, default={})
    attributes = fields.String(required=False, default=u'')
    start_service_id = fields.String(required=True, allow_none=False)
    end_service_id = fields.String(required=True, allow_none=False)
    priority = fields.Integer(required=False)


class CreateDefLinkRequestSchema(Schema):
    service_link = fields.Nested(CreateDefLinkParamRequestSchema,
                                 context=u'body')


class CreateDefLinkBodyRequestSchema(Schema):
    body = fields.Nested(CreateDefLinkRequestSchema, context=u'body')


class CreateDefLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'CreateDefLinkRequestSchema': CreateDefLinkRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateDefLinkBodyRequestSchema)
    parameters_schema = CreateDefLinkRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_service_deflink(**data.get(u'service_link'))
        return ({u'uuid': resp}, 201)


## update
class UpdateDefLinkParamRequestSchema(Schema):
    name = fields.String(required=False, default=u'default link name')
    desc = fields.String(required=False, default=u'default link description')
    attributes = fields.Dict(required=False, default={})
    priority = fields.Integer(required=False)


class UpdateDefLinkRequestSchema(Schema):
    service_link = fields.Nested(UpdateDefLinkParamRequestSchema)


class UpdateDefLinkBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateDefLinkRequestSchema, context=u'body')


class UpdateDefLink(ServiceApiView):
    tags = [u'service']
    definitions = {
        u'UpdateLinkRequestSchema': UpdateDefLinkRequestSchema,
        u'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateDefLinkBodyRequestSchema)
    parameters_schema = UpdateDefLinkRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        srv_deflink = controller.get_service_deflink(oid)
        resp = srv_deflink.update(**data.get(u'service_link'))
        return ({u'uuid': resp}, 200)


## delete
class DeleteDefLink(ServiceApiView):
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

        srv_deflink = controller.get_service_deflink(oid)
        resp = srv_deflink.delete(soft=True)
        return (resp, 204)


class ServiceDefLinkAPI(ApiView):
    """Service Link Definition api routes:    
    * /servicedeflinks - **GET**
    * /servicedeflinks - **POST**            
    * /servicedeflinks/count - **GET**
    * /servicedeflinks/<oid> - **GET**
    * /servicedeflinks/<oid> - **DELETE**
    * /servicedeflinks/<oid> - **PUT**
    * /servicedeflinks/<oid>/perms - **GET**
    """

    @staticmethod
    def register_api(module, rules=None, version=None):
        base = u'nws'
        rules = [
            (u'%s/servicedeflinks' % base, u'GET', ListDefLinks, {}),
            # (u'%s/servicedeflinks' % base, u'POST', CreateDefLink, {}),
            # (u'%s/servicedeflinks/count' % base, u'GET', CountDefLinks, {}),
            (u'%s/servicedeflinks/<oid>' % base, u'GET', GetLink, {}),
            #
            # (u'%s/servicedeflinks/<oid>' % base, u'DELETE', DeleteDefLink, {}),
            # (u'%s/servicedeflinks/<oid>' % base, u'PUT', UpdateDefLink, {}),
            # (u'%s/servicedeflinks/<oid>/perms' % base, u'GET', GetDefLinkPerms, {}),
        ]

        ApiView.register_api(module, rules)
