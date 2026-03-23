# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

import json
import re
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Length, Range
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from beecell.util import ensure_text
from beecell.simple import jsonDumps
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.plugins.computeservice.controller import (
    ApiComputeService,
    ApiComputeInstance,
)
from beehive_service.plugins.databaseservice.entity.instance_v2 import ApiDatabaseServiceInstanceV2
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
    ComputeInstanceId = fields.String(required=True, metadata={"description": "compute instance id"})
    owner_id = fields.String(
        required=True,
        data_key="owner-id",
        metadata={"example": "1", "description": "account id or uuid associated to compute zone"},
    )
    InstanceType = NotEmptyString(required=False, description="service definition of the instance")
    norescreate = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "don't create physical resource"},
    )


class CreateLoggingInstanceApiRequestSchema(Schema):
    instance = fields.Nested(CreateLoggingInstanceApiParamRequestSchema, context="body")


class CreateLoggingInstanceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateLoggingInstanceApiRequestSchema, context="body")


class CreateLoggingInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    instanceId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "instance id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
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

        # check account
        account: ApiAccount
        parent_plugin: ApiLoggingService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiLoggingService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # check compute instance
        # compute_service_instance = controller.check_service_instance(
        #     compute_instance_id, ApiComputeInstance, account=account.oid
        # )
        apiServiceInstance: ApiServiceInstance = controller.get_service_instance(compute_instance_id)
        self.logger.debug("+++++ aaa apiServiceInstance: %s - %s" % (type(apiServiceInstance), apiServiceInstance))
        if account is not None and apiServiceInstance.account_id != account.oid:
            raise ApiManagerWarning("Service %s is not in the account %s" % (apiServiceInstance.uuid, account))

        plugintype = None
        self.logger.debug(
            "+++++ aaa apiServiceInstance.getPluginTypeName(): %s" % apiServiceInstance.getPluginTypeName()
        )
        if apiServiceInstance.getPluginTypeName() == ApiComputeInstance.plugintype:
            plugintype = ApiComputeInstance.plugintype
        elif apiServiceInstance.getPluginTypeName() == ApiDatabaseServiceInstanceV2.plugintype:
            plugintype = ApiDatabaseServiceInstanceV2.plugintype
        else:
            raise ApiManagerWarning("pluginTypeName not managed: %s" % apiServiceInstance.getPluginTypeName())
        data["plugintype"] = plugintype

        data["ComputeInstanceId"] = apiServiceInstance.uuid

        # fix compute instance name
        name_instance: str = ""
        for element in apiServiceInstance.name:
            if validate_string(element, validation_string=r"[^a-zA-Z0-9\-]") is False:  # without dot!
                name_instance += "-"
            else:
                name_instance += element

        name = "LoggingInstance-%s" % name_instance
        desc = "LoggingInstance of %s" % apiServiceInstance.name

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
        context="query",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "instance id"},
    )


class DeleteLoggingInstanceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    instanceId = fields.String(
        required=False,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "instance id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
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
    nvl_code = fields.Integer(
        required=False,
        allow_none=True,
        data_key="nvl-code",
        metadata={"description": "state code"},
    )
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-message",
        metadata={"description": "state message"},
    )


class LoggingInstanceItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "id of the instance"},
    )
    name = fields.String(required=True, metadata={"example": "test", "description": "name of the instance"})
    creationDate = fields.DateTime(
        required=True,
        metadata={"example": "2022-01-25T11:20:18Z", "description": "creation date"},
    )
    description = fields.String(
        required=True,
        metadata={"example": "test", "description": "description of the instance"},
    )
    ownerId = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "account id of the owner of the instance"},
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        metadata={"example": "test", "description": "account name of the owner of the instance"},
    )
    state = fields.String(
        required=True,
        data_key="state",
        metadata={"example": "available", "description": "state of the instance"},
    )
    stateReason = fields.Nested(
        LoggingInstanceStateReasonResponseSchema,
        many=False,
        required=True,
        metadata={"description": "state description"},
    )
    computeInstanceId = fields.String(required=False, allow_none=True)
    plugintype = fields.String(required=False, allow_none=True)
    modules = fields.Dict(required=False, dump_default={}, allow_none=True)


class DescribeLoggingInstances1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    instanceInfo = fields.Nested(LoggingInstanceItemParameterResponseSchema, many=True, required=False)
    nvl_instanceTotal = fields.Integer(
        required=False,
        data_key="nvl-instanceTotal",
        metadata={"example": "0", "description": "total logging instance"},
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
        metadata={"description": "account id"},
    )
    InstanceName = fields.String(required=False, context="query", metadata={"description": "logging instance name"})
    instance_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-id.N",
        metadata={"description": "list of logging instance id"},
    )
    MaxItems = fields.Integer(
        required=False,
        load_default=100,
        validation=Range(min=1),
        context="query",
        metadata={"description": "max number elements to return in the response"},
    )
    Marker = fields.String(
        required=False,
        load_default="0",
        context="query",
        metadata={"description": "pagination token"},
    )
    Detail = fields.Boolean(
        required=False,
        allow_none=True,
        context="query",
        metadata={"description": "details in list"},
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

        detail = data.get("Detail", False)
        data_search["detail"] = detail

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
            instances_set.append(r.aws_info(detail))

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
    Return = fields.Boolean(required=True, allow_none=False, data_key="return", metadata={"example": True})
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        metadata={"description": "active task id"},
    )


class EnableLogConfigApiResponseSchema(Schema):
    EnableLogConfigResponse = fields.Nested(
        EnableLogConfigApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class EnableLogConfigApiRequestSchema(Schema):
    InstanceId = fields.String(required=False, context="query", metadata={"description": "logging instance id"})
    Config = fields.String(
        required=False,
        metadata={"example": "tomcat", "description": "name of logging configuration"},
    )


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

    def put(self, controller: ServiceController, data, *args, **kwargs):
        # get service definition with engine configuration
        conf = data.get("Config")
        oid = data.get("InstanceId")

        module_params = None
        conf_def_name = "log-conf.%s" % conf
        conf_defs, tot = controller.get_paginated_service_defs(name=conf_def_name)
        if len(conf_defs) == 1:
            # add engine config
            conf_def_config = conf_defs[0].get_main_config().params
            module_params = conf_def_config.get("module_params")
        else:
            conf_generic = controller.get_service_def("log-conf.generic")
            conf_def_config = conf_generic.get_main_config().params
            modules = conf_def_config.get("modules")
            for module in modules:
                name = module["name"]
                if name == conf:
                    module_params = conf_def_config.get("module_params")
                    str_json = jsonDumps(module_params)
                    str_json = str_json.replace("<module name>", conf)
                    module_params = json.loads(str_json)

        if module_params is None:
            raise ApiManagerError("Conf %s was not found" % conf)

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
    Return = fields.Boolean(required=True, allow_none=False, data_key="return", metadata={"example": True})
    requestId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "api request id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        allow_none=True,
        data_key="nvl-activeTask",
        metadata={"description": "active task id"},
    )


class DisableLogConfigApiResponseSchema(Schema):
    DisableLogConfigResponse = fields.Nested(
        DisableLogConfigApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DisableLogConfigApiRequestSchema(Schema):
    InstanceId = fields.String(required=False, context="query", metadata={"description": "logging instance id"})
    Config = fields.String(
        required=False,
        metadata={"example": "tomcat", "description": "name of logging configuration"},
    )


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

        module_params = None
        conf_def_name = "log-conf.%s" % conf
        conf_defs, tot = controller.get_paginated_service_defs(name=conf_def_name)
        if len(conf_defs) == 1:
            # add engine config
            conf_def_config = conf_defs[0].get_main_config().params
            module_params = conf_def_config.get("module_params")
        else:
            conf_generic = controller.get_service_def("log-conf.generic")
            conf_def_config = conf_generic.get_main_config().params
            modules = conf_def_config.get("modules")
            for module in modules:
                name = module["name"]
                if name == conf:
                    module_params = conf_def_config.get("module_params")
                    str_json = jsonDumps(module_params)
                    str_json = str_json.replace("<module name>", conf)
                    module_params = json.loads(str_json)

        if module_params is None:
            raise ApiManagerError("Conf %s was not found" % conf)

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
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id of the instance type owner"},
    )


class DescribeLoggingInstanceLogConfigParamsApiV2ResponseSchema(Schema):
    name = fields.String(
        required=True,
        metadata={"example": "tomcat", "description": "name of the logging configuration"},
    )
    title = fields.String(required=True, metadata={"example": "Tomcat", "description": "title"})
    type = fields.String(required=True, metadata={"example": "custom", "description": "type"})


class DescribeLoggingInstanceLogConfigApi1V2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    logConfigSet = fields.Nested(DescribeLoggingInstanceLogConfigParamsApiV2ResponseSchema, many=True, allow_none=False)
    logConfigTotal = fields.Integer(
        required=True,
        metadata={"example": 10, "description": "Total number of configuration available"},
    )


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
        for definition in instance_confs_set:
            name = definition.name
            self.logger.debug("+++++ definition.name: %s" % definition.name)

            if name.find("log-conf") != 0:
                continue

            if name == "log-conf.generic":
                conf_def_config = definition.get_main_config().params
                modules = conf_def_config.get("modules")
                for module in modules:
                    item = {"title": module["title"], "name": module["name"], "type": "generic"}
                    res_type_set.append(item)
                    log_confs_total += 1

            else:
                esplit = name.split(".")

                item = {
                    "title": esplit[1].capitalize(),
                    "name": esplit[1],
                    "type": "custom"
                }
                res_type_set.append(item)
                log_confs_total += 1

        res_type_set.sort(key=lambda x: x.get("name"))
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
