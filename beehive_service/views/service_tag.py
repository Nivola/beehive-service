# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, \
    PaginatedRequestQuerySchema, SwaggerApiView, PaginatedResponseSchema,\
    ApiObjectResponseSchema, ApiObjectPermsResponseSchema, CrudApiObjectResponseSchema,\
    GetApiObjectRequestSchema, ApiObjectPermsRequestSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper


class ListTagsRequestSchema(PaginatedRequestQuerySchema):
    value = fields.String(context='query')
    service = fields.String(context='query')
    link = fields.String(context='query')


class ListTagsParamsResponseSchema(ApiObjectResponseSchema):
    services = fields.Integer(default=0)
    links = fields.Integer(default=0)
    version = fields.String(required=False, allow_none=True)


class ListTagsResponseSchema(PaginatedResponseSchema):
    tags = fields.Nested(ListTagsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListTags(SwaggerApiView):
    summary = 'Get service tags'
    description = 'Get service tags'
    tags = ['service']
    definitions = {
         'ListTagsResponseSchema': ListTagsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListTagsRequestSchema)
    parameters_schema = ListTagsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
             'description':  'success',
             'schema': ListTagsResponseSchema
        }
    })
    response_schema = ListTagsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        from beehive_service.controller import ServiceController
        serviceController: ServiceController = controller
        tags, total = serviceController.get_tags(**data)
        res = [r.info() for r in tags]
        return self.format_paginated_response(res,  'tags', total, **data)


# class CountTags(SwaggerApiView):
#     tags = ['service']
#     definitions = {
#          'ApiObjecCountResponseSchema': ApiObjecCountResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = SwaggerApiView.setResponses({
#         200: {
#              'description':  'success',
#              'schema': ApiObjecCountResponseSchema
#         }
#     })
#
#     def get(self, controller, data, *args, **kwargs):
#         resp = controller.count_all_tags()
#         return {'count': int(resp)}


class GetTagParamsResponseSchema(ApiObjectResponseSchema):
    services = fields.List(fields.Dict, required=True)
    links = fields.List(fields.Dict, required=True)


class GetTagResponseSchema(Schema):
    tag = fields.Nested(GetTagParamsResponseSchema, required=True, allow_none=True)


class GetTag(SwaggerApiView):
    summary = 'Get a service tag'
    description = 'Get a service tag'
    tags = ['service']
    definitions = {
         'GetTagResponseSchema': GetTagResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
             'description':  'success',
             'schema': GetTagResponseSchema
        }
    })
    response_schema = GetTagResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        tag = controller.get_tag(oid)
        return {'tag': tag.detail()}


class GetTagPerms(SwaggerApiView):
    summary = 'Get service tag permissions'
    description = 'Get service tag permissions'
    tags = ['service']
    definitions = {
         'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
         'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
             'description':  'success',
             'schema': ApiObjectPermsResponseSchema
        }
    })
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        tag = controller.get_tag(oid)
        res, total = tag.authorization(**data)
        return self.format_paginated_response(res,  'perms', total, **data)


class CreateTagParamRequestSchema(Schema):
    value = fields.String(required=True)
    account = fields.String(required=True, description='Account id or uuid related to tag')


class CreateTagRequestSchema(Schema):
    tag = fields.Nested(CreateTagParamRequestSchema)


class CreateTagBodyRequestSchema(Schema):
    body = fields.Nested(CreateTagRequestSchema, context='body')


class CreateTag(SwaggerApiView):
    summary = 'Create a service tag'
    description = 'Create a service tag'
    tags = ['service']
    definitions = {
         'CreateTagRequestSchema': CreateTagRequestSchema,
         'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateTagBodyRequestSchema)
    parameters_schema = CreateTagRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
             'description':  'success',
             'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_tag(**data.get('tag'))
        return {'uuid': resp}, 201


class UpdateTagParamRequestSchema(Schema):
    value = fields.String()


class UpdateTagRequestSchema(Schema):
    tag = fields.Nested(UpdateTagParamRequestSchema)


class UpdateTagBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateTagRequestSchema, context= 'body')


class UpdateTag(SwaggerApiView):
    summary = 'Update a service tag'
    description = 'Update a service tag'
    tags = ['service']
    definitions = {
         'UpdateTagRequestSchema': UpdateTagRequestSchema,
         'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateTagBodyRequestSchema)
    parameters_schema = UpdateTagRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
             'description':  'success',
             'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def put(self, controller, data, oid, *args, **kwargs):
        tag = controller.get_tag(oid)
        resp = tag.update(**data.get('tag'))
        return {'uuid': resp}


class DeleteTag(SwaggerApiView):
    summary = 'Delete a service tag'
    description = 'Delete a service tag'
    tags = ['service']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
             'description':  'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        tag = controller.get_tag(oid)
        resp = tag.delete()
        return resp, 204


class ServiceTagAPI(ApiView):
    """Service tag api routes:
    """
    @staticmethod
    def register_api(module, **kwargs):
        base = 'nws'
        rules = [
            ('%s/tags' % base,  'GET', ListTags, {}),
            ('%s/tags' % base,  'POST', CreateTag, {}),
            # ( '%s/tags/count' % base,  'GET', CountTags, {}),
            ('%s/tags/<oid>' % base,  'GET', GetTag, {}),
            ('%s/tags/<oid>' % base,  'PUT', UpdateTag, {}),
            ('%s/tags/<oid>' % base,  'DELETE', DeleteTag, {}),
            ('%s/tags/<oid>/perms' % base,  'GET', GetTagPerms, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
