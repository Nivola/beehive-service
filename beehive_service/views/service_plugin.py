#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


"""
base views blueprints for beehive_service plugins
"""
from flasgger import fields, Schema
from beehive_service.model.base import SrvStatusType

class StateReasonResponseSchema(Schema):
    """
    code and message for state change
    """
    code = fields.String(required=False, allow_none=True, metadata={"description": "reason code for the state change"})
    message = fields.String(required=False, allow_none=True, metadata={"description": "message for the state change"})


#  /pluginservices - "GET" - DescribePluginService


class DescribePluginServiceRequestSchema(Schema):
    """
    filter by account
    """
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        metadata={"description": "account ID of the instance owner"},
    )


class PluginResponseSchema(Schema):
    """
    describes a plugin core service for a specific account (owner)
    """
    id = fields.String(required=True)
    name = fields.String(required=True)
    creationDate = fields.DateTime(required=False, allow_none=True, metadata={"description": "date creation"})
    description = fields.String(required=True)
    state = fields.String(required=False, dump_default=SrvStatusType.DRAFT)
    owner = fields.String(required=True)
    owner_name = fields.String(required=True)
    template = fields.String(required=True)
    template_name = fields.String(required=True)
    stateReason = fields.Nested(
        StateReasonResponseSchema,
        many=False,
        required=False,
        allow_none=False,
        metadata={"description": "array of status reason"},
    )
    resource_uuid = fields.String(required=False, allow_none=True)


class DescribePluginServiceResponseSchema(Schema):
    """
    schema for list of core plugin services
    """
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=False)
    pluginSet = fields.Nested(PluginResponseSchema, data_key="pluginSet", many=True, required=False)
    pluginTotal = fields.Integer(required=False, data_key="pluginTotal")


class DescribePluginApiResponseSchema(Schema):
    DescribePluginResponse = fields.Nested(
        DescribePluginServiceResponseSchema,
        data_key="DescribePluginResponse",
        required=True,
        allow_none=False,
    )


#  /pluginservices - "POST" - CreatePluginService


class CreatePluginServiceApiRequestSchema(Schema):
    owner_id = fields.String(required=True)
    name = fields.String(required=False, dump_default="")
    desc = fields.String(required=False, dump_default="")
    service_def_id = fields.String(required=True)
    resource_desc = fields.String(required=False, dump_default="")


class CreatePluginServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreatePluginServiceApiRequestSchema, context="body")


#  /pluginservices - "PUT" - UpdatePluginService


class UpdatePluginServiceApiRequestParamSchema(Schema):
    owner_id = fields.String(
        required=True,
        allow_none=False,
        context="query",
        data_key="owner-id",
        metadata={"description": "account ID of the instance owner"},
    )
    name = fields.String(required=False, dump_default="")
    desc = fields.String(required=False, dump_default="")
    service_def_id = fields.String(required=False, dump_default="")


class UpdatePluginServiceApiRequestSchema(Schema):
    serviceinst = fields.Nested(UpdatePluginServiceApiRequestParamSchema, context="body")


class UpdatePluginServiceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdatePluginServiceApiRequestSchema, context="body")
