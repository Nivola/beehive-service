# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte

import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from six import ensure_text
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.plugins.computeservice.controller import (
    ApiComputeService,
    ApiComputeInstance,
)
from beehive_service.views import NotEmptyString, ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiManagerError,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    PaginatedRequestQuerySchema,
    ApiView,
    ApiManagerWarning,
)
from beehive_service.plugins.loggingservice.controller import (
    ApiLoggingService,
    ApiLoggingInstance,
)
from beehive.common.assert_util import AssertUtil
from beehive_service.service_util import (
    __SRV_STORAGE_PERFORMANCE_MODE_DEFAULT__,
    __SRV_STORAGE_PERFORMANCE_MODE__,
    __SRV_AWS_STORAGE_STATUS__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE__,
    __SRV_STORAGE_GRANT_ACCESS_LEVEL__,
    __REGEX_SHARE_GRANT_ACCESS_TO_USER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_USER_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_CERT_LOWER__,
    __SRV_STORAGE_GRANT_ACCESS_TYPE_IP_LOWER__,
)
from ipaddress import IPv4Address, AddressValueError
from beehive.common.data import operation
from beecell.types.type_string import validate_string


class CreateLoggingInstanceApiParamRequestSchema(Schema):
    ComputeInstanceId = fields.String(required=True, description="compute instance id")
    owner_id = fields.String(
        required=True,
        example="1",
        data_key="owner-id",
        description="account id or uuid associated to compute zone",
    )
    InstanceType = NotEmptyString(required=False, description="service definition of the instance")
    norescreate = fields.Boolean(required=False, allow_none=True, description="don't create physical resource")


class CreateLoggingInstanceApiRequestSchema(Schema):
    instance = fields.Nested(CreateLoggingInstanceApiParamRequestSchema, context="body")


class CreateLoggingInstanceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateLoggingInstanceApiRequestSchema, context="body")


class CreateLoggingInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class CreateLoggingInstanceApiResponseSchema(Schema):
    CreateLoggingInstanceResponse = fields.Nested(
        CreateLoggingInstanceApiResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateLoggingInstance(ServiceApiView):
    summary = "Create logging instance"
    description = "Create logging instance"
    tags = ["loggingservice"]
    definitions = {
        "CreateLoggingInstanceApiResponseSchema": CreateLoggingInstanceApiResponseSchema,
        "CreateLoggingInstanceApiRequestSchema": CreateLoggingInstanceApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateLoggingInstanceApiBodyRequestSchema)
    parameters_schema = CreateLoggingInstanceApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": CreateLoggingInstanceApiResponseSchema,
            }
        }
    )
    response_schema = CreateLoggingInstanceApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        inner_data = data.get("instance")
        service_definition_id = inner_data.get("InstanceType", None)
        account_id = inner_data.get("owner_id")
        compute_instance_id = inner_data.get("ComputeInstanceId")
        norescreate = inner_data.get("norescreate")

        # # check parent service exists
        # res, tot = controller.get_service_type_plugins(account_id_list=[account_id],
        #                                                plugintype=ApiLoggingService.plugintype)
        # self.logger.debug('CreateLoggingInstance post - res {}'.format(res))
        # if tot > 0:
        #     attribute_set = res[0].aws_get_attributes()
        # else:
        #     raise ApiManagerError('Account %s has no logging service core' % account_id)
        #
        # # check instance with the same name already exists
        # # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account: ApiAccount
        parent_plugin: ApiLoggingService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiLoggingService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # check compute instance
        compute_service_instance = controller.check_service_instance(
            compute_instance_id, ApiComputeInstance, account=account.oid
        )
        data["ComputeInstanceId"] = compute_service_instance.uuid

        # fix compute instance name
        name_instance: str = ""
        for element in compute_service_instance.name:
            if validate_string(element, validation_string=r"[^a-zA-Z0-9\-]") is False:  # without dot!
                name_instance += "-"
            else:
                name_instance += element

        name = "LoggingInstance-%s" % name_instance
        desc = "LoggingInstance of %s" % compute_service_instance.name

        data["norescreate"] = norescreate

        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiLoggingInstance.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)

        plugin: ApiLoggingInstance
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
            name_max_length=60,
        )

        res = {
            "CreateLoggingInstanceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceId": plugin.instance.uuid,
                "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class DeleteLoggingInstanceApiRequestSchema(Schema):
    InstanceId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
        context="query",
    )


class DeleteLoggingInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceId = fields.String(
        required=False,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="instance id",
    )
    nvl_activeTask = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        data_key="nvl-activeTask",
        description="task id",
    )


class DeleteLoggingInstanceApiResponseSchema(Schema):
    DeleteInstanceResponse = fields.Nested(DeleteLoggingInstanceApiResponse1Schema, required=True, allow_none=False)


class DeleteLoggingInstance(ServiceApiView):
    summary = "Delete logging instance"
    description = "Delete logging instance"
    tags = ["loggingservice"]
    definitions = {
        "DeleteLoggingInstanceApiRequestSchema": DeleteLoggingInstanceApiRequestSchema,
        "DeleteLoggingInstanceApiResponseSchema": DeleteLoggingInstanceApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteLoggingInstanceApiRequestSchema)
    parameters_schema = DeleteLoggingInstanceApiRequestSchema
    responses = ServiceApiView.setResponses(
        {
            202: {
                "description": "no response",
                "schema": DeleteLoggingInstanceApiResponseSchema,
            }
        }
    )
    response_schema = DeleteLoggingInstanceApiResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.get("InstanceId")
        type_plugin: ApiLoggingInstance
        type_plugin = controller.get_service_type_plugin(instance_id)

        if isinstance(type_plugin, ApiLoggingInstance):
            type_plugin.delete()
        else:
            raise ApiManagerError("Instance is not a LoggingInstance")

        res = {
            "DeleteInstanceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceId": type_plugin.instance.uuid,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        self.logger.debug("DeleteLoggingInstance delete - end")
        return res, 202


class LoggingInstanceStateReasonResponseSchema(Schema):
    nvl_code = fields.Integer(required=False, allow_none=True, description="state code", data_key="nvl-code")
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state message",
        data_key="nvl-message",
    )


class LoggingInstanceItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="id of the instance",
    )
    name = fields.String(required=True, example="test", description="name of the instance")
    creationDate = fields.DateTime(required=True, example="2022-01-25T11:20:18Z", description="creation date")
    description = fields.String(required=True, example="test", description="description of the instance")
    ownerId = fields.String(
        required=True,
        example="075df680-2560-421c-aeaa-8258a6b733f0",
        description="account id of the owner of the instance",
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        example="test",
        description="account name of the owner of the instance",
    )
    state = fields.String(
        required=True,
        example="available",
        description="state of the instance",
        data_key="state",
    )
    stateReason = fields.Nested(
        LoggingInstanceStateReasonResponseSchema,
        many=False,
        required=True,
        description="state description",
    )
    computeInstanceId = fields.String(required=False, allow_none=True)
    modules = fields.Dict(required=False, default={}, allow_none=True)


class DescribeLoggingInstances1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    instanceInfo = fields.Nested(
        LoggingInstanceItemParameterResponseSchema,
        many=True,
        required=False,
    )
    nvl_instanceTotal = fields.Integer(
        required=False,
        example="0",
        descriptiom="total logging instance",
        data_key="nvl-instanceTotal",
    )


class DescribeLoggingInstancesResponseSchema(Schema):
    DescribeLoggingInstancesResponse = fields.Nested(
        DescribeLoggingInstances1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeLoggingInstancesRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account id",
    )
    InstanceName = fields.String(required=False, description="logging instance name", context="query")
    instance_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-id.N",
        description="list of logging instance id",
    )
    MaxItems = fields.Integer(
        required=False,
        missing=100,
        validation=Range(min=1),
        context="query",
        description="max number elements to return in the response",
    )
    Marker = fields.String(
        required=False,
        missing="0",
        example="",
        description="pagination token",
        context="query",
    )


class DescribeLoggingInstances(ServiceApiView):
    summary = "Describe logging"
    description = "Describe logging"
    tags = ["loggingservice"]
    definitions = {
        "DescribeLoggingInstancesRequestSchema": DescribeLoggingInstancesRequestSchema,
        "DescribeLoggingInstancesResponseSchema": DescribeLoggingInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeLoggingInstancesRequestSchema)
    parameters_schema = DescribeLoggingInstancesRequestSchema
    responses = ServiceApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeLoggingInstancesResponseSchema,
            }
        }
    )
    response_schema = DescribeLoggingInstancesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        self.logger.debug("DescribeLoggingInstances get - begin")
        logging_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        account_id_list = data.get("owner_id_N", [])
        instance_id_list = data.get("instance_id_N", [])
        instance_name_list = data.get("InstanceName", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            service_id_list=logging_id_list,
            account_id_list=account_id_list,
            plugintype=ApiLoggingInstance.plugintype,
            **data_search,
        )

        instances_set = []
        for r in res:
            r: ApiLoggingInstance
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = "0"
        else:
            next_token = str(data_search["page"] + 1)

        res = {
            "DescribeLoggingInstancesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "next_token": next_token,
                "instanceInfo": instances_set,
                "nvl-instanceTotal": total,
            }
        }
        return res


class EnableLogConfigApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    Return = fields.Boolean(required=True, example=True, allow_none=False, data_key="return")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        description="active task id",
    )


class EnableLogConfigApiResponseSchema(Schema):
    EnableLogConfigResponse = fields.Nested(
        EnableLogConfigApi1ResponseSchema, required=True, many=False, allow_none=False
    )


class EnableLogConfigApiRequestSchema(Schema):
    InstanceId = fields.String(required=False, description="logging instance id", context="query")
    Config = fields.String(required=False, example="tomcat", description="name of logging configuration")


class EnableLogConfigApiBodyRequestSchema(Schema):
    body = fields.Nested(EnableLogConfigApiRequestSchema, context="body")


class EnableLogConfig(ServiceApiView):
    summary = "Enable logging config in a compute instance"
    description = "Enable logging config in a compute instance"
    tags = ["loggingservice"]
    definitions = {
        "EnableLogConfigApiRequestSchema": EnableLogConfigApiRequestSchema,
        "EnableLogConfigApiResponseSchema": EnableLogConfigApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(EnableLogConfigApiBodyRequestSchema)
    parameters_schema = EnableLogConfigApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": EnableLogConfigApiResponseSchema}}
    )
    response_schema = EnableLogConfigApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        # get service definition with engine configuration
        conf = data.get("Config")
        oid = data.get("InstanceId")
        conf_def_name = "log-conf.%s" % conf
        conf_defs, tot = controller.get_paginated_service_defs(name=conf_def_name)
        if len(conf_defs) < 1 or len(conf_defs) > 1:
            raise ApiManagerError("Conf %s was not found" % conf)

        # add engine config
        conf_def_config = conf_defs[0].get_main_config().params
        module_params = conf_def_config.get("module_params")

        type_plugin: ApiLoggingInstance = controller.get_service_type_plugin(oid, plugin_class=ApiLoggingInstance)
        return_value = type_plugin.enable_log_config(module_params)

        res = {
            "EnableLogConfigResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class DisableLogConfigApi1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    Return = fields.Boolean(required=True, example=True, allow_none=False, data_key="return")
    requestId = fields.String(
        required=True,
        example="29647df5-5228-46d0-a2a9-09ac9d84c099",
        description="api request id",
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        description="active task id",
    )


class DisableLogConfigApiResponseSchema(Schema):
    DisableLogConfigResponse = fields.Nested(
        DisableLogConfigApi1ResponseSchema, required=True, many=False, allow_none=False
    )


class DisableLogConfigApiRequestSchema(Schema):
    InstanceId = fields.String(required=False, description="logging instance id", context="query")
    Config = fields.String(required=False, example="tomcat", description="name of logging configuration")


class DisableLogConfigApiBodyRequestSchema(Schema):
    body = fields.Nested(DisableLogConfigApiRequestSchema, context="body")


class DisableLogConfig(ServiceApiView):
    summary = "Disable logging config in a compute instance"
    description = "Disable logging config in a compute instance"
    tags = ["loggingservice"]
    definitions = {
        "DisableLogConfigApiRequestSchema": DisableLogConfigApiRequestSchema,
        "DisableLogConfigApiResponseSchema": DisableLogConfigApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DisableLogConfigApiBodyRequestSchema)
    parameters_schema = DisableLogConfigApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": DisableLogConfigApiResponseSchema}}
    )
    response_schema = DisableLogConfigApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        # get service definition with engine configuration
        conf = data.get("Config")
        oid = data.get("InstanceId")
        conf_def_name = "log-conf.%s" % conf
        conf_defs, tot = controller.get_paginated_service_defs(name=conf_def_name)
        if len(conf_defs) < 1 or len(conf_defs) > 1:
            raise ApiManagerError("Conf %s was not found" % conf)

        # add engine config
        conf_def_config = conf_defs[0].get_main_config().params
        module_params = conf_def_config.get("module_params")

        type_plugin: ApiLoggingInstance = controller.get_service_type_plugin(oid, plugin_class=ApiLoggingInstance)
        return_value = type_plugin.disable_log_config(module_params)

        res = {
            "DisableLogConfigResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": return_value,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class DescribeLoggingInstanceLogConfigApiV2RequestSchema(Schema):
    owner_id = fields.String(
        example="d35d19b3-d6b8-4208-b690-a51da2525497",
        required=True,
        context="query",
        data_key="owner-id",
        description="account id of the instance type owner",
    )


class DescribeLoggingInstanceLogConfigParamsApiV2ResponseSchema(Schema):
    name = fields.String(required=True, example="tomcat", description="name of the logging configuration")


class DescribeLoggingInstanceLogConfigApi1V2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, description="api request id")
    logConfigSet = fields.Nested(
        DescribeLoggingInstanceLogConfigParamsApiV2ResponseSchema,
        many=True,
        allow_none=False,
    )
    logConfigTotal = fields.Integer(required=True, example=10, description="Total number of configuration available")


class DescribeLoggingInstanceLogConfigApiV2ResponseSchema(Schema):
    DescribeLoggingInstanceLogConfigResponse = fields.Nested(
        DescribeLoggingInstanceLogConfigApi1V2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeLoggingInstanceLogConfig(ServiceApiView):
    summary = "List of logging instance confs"
    description = "List of logging instance confs"
    tags = ["loggingservice"]
    definitions = {
        "DescribeLoggingInstanceLogConfigApiV2RequestSchema": DescribeLoggingInstanceLogConfigApiV2RequestSchema,
        "DescribeLoggingInstanceLogConfigApiV2ResponseSchema": DescribeLoggingInstanceLogConfigApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeLoggingInstanceLogConfigApiV2RequestSchema)
    parameters_schema = DescribeLoggingInstanceLogConfigApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeLoggingInstanceLogConfigApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeLoggingInstanceLogConfigApiV2ResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)
        instance_confs_set, total = account.get_definitions(plugintype="VirtualService", size=-1)

        res_type_set = []
        log_confs_total = 0
        for r in instance_confs_set:
            name = r.name

            if name.find("log-conf") != 0:
                continue
            esplit = name.split(".")

            item = {"name": esplit[1]}
            res_type_set.append(item)
            log_confs_total += 1

        res = {
            "DescribeLoggingInstanceLogConfigResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "logConfigSet": res_type_set,
                "logConfigTotal": log_confs_total,
            }
        }
        return res


class LoggingInstanceServiceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/loggingservices"
        rules = [
            ("%s/instance/createinstance" % base, "POST", CreateLoggingInstance, {}),
            (
                "%s/instance/deleteteinstance" % base,
                "DELETE",
                DeleteLoggingInstance,
                {},
            ),
            (
                "%s/instance/describeinstances" % base,
                "GET",
                DescribeLoggingInstances,
                {},
            ),
            (
                "%s/instance/describelogconfig" % base,
                "GET",
                DescribeLoggingInstanceLogConfig,
                {},
            ),
            ("%s/instance/enablelogconfig" % base, "PUT", EnableLogConfig, {}),
            ("%s/instance/disablelogconfig" % base, "PUT", DisableLogConfig, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
