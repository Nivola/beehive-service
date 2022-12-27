# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib import response
from flasgger import fields, Schema
from beehive_service.entity.service_type import ApiServiceTypePlugin
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView
from beehive_service.plugins.computeservice.controller import ApiComputeTag, ApiComputeService
from marshmallow.validate import OneOf, Range
from beehive.common.data import operation
from beehive_service.service_util import __SRV_AWS_TAGS_RESOURCE_TYPE__
from marshmallow.exceptions import ValidationError
from marshmallow.decorators import validates_schema


class DescribeTagsApiRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='owner-id.N',
                             description='account ID of compute service')
    key_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                        data_key='key.N', collection_format='multi', description='tag key')
    resource_id_N = fields.List(fields.String(example=''), description='resource type ID', required=False,
                                allow_none=True, context='query', data_key='resource-id.N',
                                collection_format='multi')
    # AWS resource_type valid values
    resource_type_N = fields.List(fields.String(example='', validate=OneOf(__SRV_AWS_TAGS_RESOURCE_TYPE__)),
                                  required=False, allow_none=True, context='query', data_key='resource-type.N',
                                  collection_format='multi', description='resource type ID')
    # MaxResults vedi  https://jira.csi.it/browse/NSP-355 con beneficio di inventario
    MaxResults = fields.Integer(required=False,  missing=10, default=10, validate=Range(min=-1, max=1000),
                                example='', description='maximum number of results to return', context='query')
    NextToken = fields.String(required=False, example='',
                              description='pagination token', context='query')

    @validates_schema
    def validate_unsupported_parameters(self, data, *args, **kvargs):
        keys = data.keys()
        if 'value_N' in keys:
            raise ValidationError('Parameter value is not supported. Use only the parameter Parameter key')


class DescribeTagsApiItemResponseSchema(Schema):
    resourceId = fields.String(required=False, allow_none=True, example='', description='resource type ID')
    resourceType = fields.String(required=False, allow_none=True, example='', description='resource type')
    key = fields.String(required=False, allow_none=True, example='', description='tag key')
    value = fields.String(required=False, allow_none=True, missing='', default='', example='', description='tag value')


class DescribeTagsApi1ResponseSchema(Schema):
    nextToken = fields.String(required=True, example='', description='next pagination token')
    requestId = fields.String(required=True, example='', description='')
    tagSet = fields.Nested(DescribeTagsApiItemResponseSchema, many=True, required=True,
                           allow_none=False, example='', description='list of tags' )
    nvl_tagTotal = fields.Integer(required=False, example='', description='total number of tag items',
                                  data_key='nvl-tagTotal')
    xmlns = fields.String(required=False, data_key='__xmlns')


class DescribeTagsApiResponseSchema(Schema):
    DescribeTagsResponse = fields.Nested(DescribeTagsApi1ResponseSchema, required=True, many=False, allow_none=False)


class DescribeTags(ServiceApiView):
    summary = 'Describe compute tag'
    description = 'Describe compute tag'
    tags = ['computeservice']
    definitions = {
        'DescribeTagsApiRequestSchema': DescribeTagsApiRequestSchema,
        'DescribeTagsApiResponseSchema': DescribeTagsApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeTagsApiRequestSchema)
    parameters_schema = DescribeTagsApiRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeTagsApiResponseSchema
        }
    })
    response_schema = DescribeTagsApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        data_search = {}
        data_search['size'] = data.get('MaxResults', 10)
        data_search['page'] = int(data.get('NextToken', 0))

        # check Account
        account_id_list = data.get('owner_id_N', [])

        # get filtered service tag
        tag_values = data.get('key_N', [])
        service_list = data.get('resource_id_N', [])
        plugintype_list = [ApiComputeTag.resource_type_mapping(t) for t in data.get('resource_type_N', [])]
        tags, tot = controller.get_service_tags_with_instance(value_list=tag_values,
                                                              account_id_list=account_id_list,
                                                              service_list=service_list,
                                                              plugintype_list=plugintype_list,
                                                              **data_search)

        tags = ApiComputeTag.customize_list(controller, tags)
        tag_set = [t.aws_info() for t in tags]

        res = {
            'DescribeTagsResponse': {
                '__xmlns': self.xmlns,
                'nextToken': str(data_search['page'] + 1),
                'requestId': operation.id,
                'tagSet': tag_set,
                'nvl-tagTotal': tot
            }
        }

        return res


class TagRequestSchema(Schema):
    Key = fields.String(required=True, example='', description='tag key')

    @validates_schema
    def validate_unsupported_parameters(self, data, *args, **kvargs):
        keys = data.keys()
        if 'Value' in keys:
            raise ValidationError('Parameters Tag.N.Value is not supported. Can be used only the parameter '
                                  'Parameters Tag.N.Key')


class TagsApiParamRequestSchema(Schema):
    owner_id = fields.String(required=True, allow_none=False, data_key='owner-id',
                             description='account ID of compute service')
    ResourceId_N = fields.List(fields.String(example=''), required=True, many=True, allow_none=False,
                               data_key='ResourceId.N', description='list of resource id')
    Tag_N = fields.Nested(TagRequestSchema, required=True, many=True, allow_none=False, data_key='Tag.N',
                          description='list of tags')


class TagsApiRequestSchema(Schema):
    tags = fields.Nested(TagsApiParamRequestSchema, context='body')


class TagsApiBodyRequestSchema(Schema):
    body = fields.Nested(TagsApiRequestSchema, context='body')


class CreateTagsApiResponse1Schema(Schema):
    return_ = fields.Boolean(required=True, allow_none=False, data_key='return')
    requestId = fields.String(required=True, allow_none=True)


class CreateTagsApiResponseSchema(Schema):
    CreateTagsResponse = fields.Nested(CreateTagsApiResponse1Schema, required=True, allow_none=False)


class CreateTags(ServiceApiView):
    summary = 'Create a compute tag'
    description = 'Create a compute tag'
    tags = ['computeservice']
    definitions = {
        'TagsApiRequestSchema': TagsApiRequestSchema,
        'CreateTagsApiResponseSchema': CreateTagsApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(TagsApiBodyRequestSchema)
    parameters_schema = TagsApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CreateTagsApiResponseSchema
        }
    })
    response_schema = CreateTagsApiResponseSchema

    def post(self, controller, data, *args, **kwargs):
        return_value = False

        data = data.get('tags')

        # get account
        # account = controller.get_account(data.get('owner_id'))

        # check account
        account, parent_plugin = self.check_parent_service(controller, data.get('owner_id'),
                                                           plugintype=ApiComputeService.plugintype)

        # get service instance
        service_ids = data.get('ResourceId_N', [])
        service_list, toto = controller.get_paginated_service_instances(service_uuid_list=service_ids,
                                                                        fk_account_id=account.oid,
                                                                        details=False,
                                                                        size=-1,
                                                                        filter_expired=False)

        # check Tag
        tags = data.get('Tag_N', [])
        tag_value_list = [tag.get('Key') for tag in tags]

        # create Tag for resource
        # Tag keys must be unique per resource
        for service in service_list:
            for tag in tag_value_list:
                plugin = ApiServiceTypePlugin(controller)
                plugin.instance = service
                plugin.add_tag(tag)
                return_value = True

        res = {
            'CreateTagsResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'return': return_value
            }
        }

        return res, 200


class DeleteTagsResponse1Schema(Schema):
    return_ = fields.Boolean(required=True, allow_none=False, data_key='return')
    requestId = fields.String(required=True, allow_none=True)


class DeleteTagsResponseSchema(Schema):
    DeleteTagsResponse = fields.Nested(DeleteTagsResponse1Schema, required=True, allow_none=False)


class DeleteTagsApiParamRequestSchema(Schema):
    ResourceId_N = fields.List(fields.String(example=''), required=True, many=True,
                               allow_none=False, data_key='ResourceId.N',
                               description='list of resource id')
    Tag_N = fields.Nested(TagRequestSchema, required=False, many=True, allow_none=False, data_key='Tag.N',
                          description='one or more tags')


class DeleteTagsApiRequestSchema (Schema):
    tags = fields.Nested(DeleteTagsApiParamRequestSchema, context='body')


class DeleteTagsApiBodyRequestSchema(Schema):
    body = fields.Nested(DeleteTagsApiRequestSchema, context='body')


class DeleteTags(ServiceApiView):
    summary = 'Delete a compute tag'
    description = 'Delete a compute tag'
    tags = ['computeservice']
    definitions = {
        'DeleteTagsApiRequestSchema': DeleteTagsApiRequestSchema,
        'DeleteTagsResponseSchema': DeleteTagsResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DeleteTagsApiBodyRequestSchema)
    parameters_schema = DeleteTagsApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DeleteTagsResponseSchema
        }
    })
    response_schema = DeleteTagsResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        data = data.get('tags')
        delete_all_tags = True

        # check Tag
        tags = data.get('Tag_N', [])
        tag_value_list = [tag.get('Key') for tag in tags]
        if len(tag_value_list) > 0:
            delete_all_tags = False

        # get service instance
        service_ids = data.get('ResourceId_N', [])
        service_list, toto = controller.get_paginated_service_instances(service_uuid_list=service_ids,
                                                                        details=False,
                                                                        size=-1,
                                                                        filter_expired=False)

        # delete tag for resource
        for service in service_list:
            if delete_all_tags is True:
                # tag_value_list = [t.name for t in service.get_tags()]
                tag_value_list = [t.name for t in service.model.tags]

            # delete tag
            for tag in tag_value_list:
                plugin = ApiServiceTypePlugin(controller)
                plugin.instance = service
                plugin.remove_tag(tag)

        # check tags has service associated. if no remove tag
        for tag in tag_value_list:
            tags, total = controller.get_tags(value=tag)
            if total == 1 and tags[0].services == 0:
                tags[0].delete()

        res = {
            'DeleteTagsResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'return': True
            }
        }

        return res, 200


class ComputeTagAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/computeservices/tag'
        rules = [
            ('%s/describetags' % base, 'GET', DescribeTags, {}),
            ('%s/createtags' % base, 'POST', CreateTags, {}),
            ('%s/deletetags' % base, 'DELETE', DeleteTags, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
