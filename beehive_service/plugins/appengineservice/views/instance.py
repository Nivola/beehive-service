# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.model.account import Account
from beehive_service.controller.api_account import ApiAccount
from flasgger import fields, Schema

from beehive_service.plugins.appengineservice.controller import (
    ApiAppEngineService,
    ApiAppEngineInstance,
    ApiAppEngineServiceResourceHelper,
)
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView
from beehive_service.controller import ApiServiceType, ServiceController
from beehive_service.plugins.computeservice.controller import (
    ApiComputeSubnet,
    ApiComputeSecurityGroup,
    ApiComputeVPC,
    ApiComputeService,
)
from beehive.common.assert_util import AssertUtil
from beecell.simple import merge_dicts
from marshmallow.validate import OneOf
from beehive.common.data import operation


class DescribeAppInstancesRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, default=10, description="", context="query")
    NextToken = fields.String(required=False, default="0", description="", context="query")
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the instance owner",
    )
    name_N = fields.List(
        fields.String(),
        required=False,
        example="",
        description="name of the instance",
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="name.N",
    )
    availability_zone_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="availability-zone.N",
        description="availability zone of the instance",
    )
    InstanceId_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="InstanceId.N",
        description="instance id",
    )
    instance_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-id.N",
        description="instance id",
    )
    launch_time_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="launch-time.N",
        description="time when the instance was created",
    )
    tag_key_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="tag-key.N",
        descriptiom="value of a tag assigned to the resource",
    )


class InstanceConfigsRequestSchema(Schema):
    documentRoot = fields.String(required=False, example="/var/www", description="[apache-php] document root")
    ftpServer = fields.Boolean(
        required=False,
        example=True,
        default=True,
        description="[apache-php] if true install ftp server",
    )
    smbServer = fields.Boolean(
        required=False,
        example=False,
        default=False,
        description="[apache-php] if true install samba server",
    )
    shareDimension = fields.Integer(
        required=False,
        example=10,
        default=10,
        description="[apache-php] share dimension in GB",
    )
    shareCfgDimension = fields.Boolean(
        required=False,
        example=2,
        default=2,
        description="[apache-php] share config dimension in GB",
    )
    appPort = fields.Integer(
        required=False,
        example=80,
        default=80,
        description="[apache-php] internal application prot",
    )
    farmName = fields.String(
        required=True,
        example="tst-portali",
        description="[apache-php] parent compute zone id or uuid",
    )


class InstancePlacementsResponseSchema(Schema):
    availabilityZone = fields.String(required=False, example="", description="availability zone of the instance id")


class InstanceTagSetResponseSchema(Schema):
    key = fields.String(required=False, description="tag key")
    value = fields.String(required=False, description="tag value")


class InstanceGroupSetResponseSchema(Schema):
    groupName = fields.String(required=False, example="", description="security group name")
    groupId = fields.String(required=False, example="", description="security group id")


class InstanceMonitoringResponseSchema(Schema):
    state = fields.String(required=False, example="", description="status of monitoring")


class InstanceStateResponseSchema(Schema):
    code = fields.Integer(required=False, example="0", description="code of instance state")
    name = fields.String(
        required=False,
        example="pending | running | ....",
        description="name of instance state",
        validate=OneOf(["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]),
    )


class InstanceAppEngineSetResponseSchema(Schema):
    ownerId = fields.String(required=False, description="")
    instanceId = fields.String(required=False, example="", description="instance id")
    instanceState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)
    name = fields.String(
        required=False,
        allow_none=True,
        missing="default istance name",
        description="instance name",
    )
    additionalInfo = fields.String(required=False, allow_none=True, description="instance description")
    launchTime = fields.DateTime(
        required=False,
        example="",
        description="the timestamp the instance was launched",
    )
    placements = fields.Nested(InstancePlacementsResponseSchema, many=False, required=False)
    monitoring = fields.Nested(InstanceMonitoringResponseSchema, many=False, required=False)
    subnetId = fields.String(required=False, example="", description="subnet id ")
    vpcId = fields.String(required=False, example="", description="vpc id ")
    privateIpAddresses = fields.List(
        fields.String(example="###.###.###.###"),
        required=True,
        description="List of internal server ip adresses",
    )
    uris = fields.List(
        fields.String(example="https://###.###.###.###:443"),
        description="list of app engine uris",
        required=True,
    )
    groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)
    tagSet = fields.Nested(InstanceTagSetResponseSchema, many=True, required=False)
    keyName = fields.String(required=False, example="1ffd", description="The name of the key pair")
    engine = fields.String(required=False, example="apache-php", description="The name of the engine")
    version = fields.String(required=False, example="5.9", description="The versione of the engine")
    engineConfigs = fields.Nested(
        InstanceConfigsRequestSchema,
        required=True,
        description="App engine specific params",
    )


class DescribeAppInstancesApi1ResponseSchema(Schema):
    nextToken = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True)
    instancesSet = fields.Nested(InstanceAppEngineSetResponseSchema, many=True, required=True, allow_none=False)
    instancesTotal = fields.String(required=True, allow_none=False)


class DescribeAppInstancesResponseSchema(Schema):
    DescribeAppInstancesResponse = fields.Nested(
        DescribeAppInstancesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeAppInstances(ServiceApiView):
    tags = ["appengineservice"]
    definitions = {
        "DescribeAppInstancesRequestSchema": DescribeAppInstancesRequestSchema,
        "DescribeAppInstancesResponseSchema": DescribeAppInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeAppInstancesRequestSchema)
    parameters_schema = DescribeAppInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DescribeAppInstancesResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        """
        Appengine Instances list
        Appengine Instances list
        """
        data_search = {}
        data_search["size"] = data.get("MaxResults", 10)
        data_search["page"] = int(data.get("NextToken", 0))

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("instance_id_N", [])
        instance_id_list.extend(data.get("InstanceId_N", []))

        # get instance name
        instance_name_list = data.get("name_N", [])

        # get instance launch time
        instance_launch_time_list = data.get("launch_time_N", [])
        instance_launch_time = None
        if len(instance_launch_time_list) == 1:
            instance_launch_time = instance_launch_time_list[0]
        elif len(instance_launch_time_list) > 1:
            self.logger.warn("For the moment only one instance_launch_time can be submitted as filter")

        # get tags
        tag_values = data.get("tag_key_N", None)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            account_id_list=account_id_list,
            servicetags_or=tag_values,
            filter_creation_date_start=instance_launch_time,
            plugintype=ApiAppEngineInstance.plugintype,
            **data_search,
        )

        # format result
        instances_set = [r.aws_info() for r in res]

        res = {
            "DescribeAppInstancesResponse": {
                "__xmlns": self.xmlns,
                "nextToken": data_search["page"] + 1,
                "requestId": operation.id,
                "instancesSet": instances_set,
                "instancesTotal": total,
            }
        }
        return res


class CreateAppInstancesApiParamConfigsRequestSchema(Schema):
    DocumentRoot = fields.String(required=False, example="/var/www", description="[apache-php] document root")
    FtpServer = fields.Boolean(
        required=False,
        example=True,
        default=True,
        description="[apache-php] if true install ftp server",
    )
    SmbServer = fields.Boolean(
        required=False,
        example=False,
        default=False,
        description="[apache-php] if true install samba server",
    )
    ShareDimension = fields.Integer(
        required=False,
        example=10,
        missing=10,
        description="[apache-php] share dimension in GB",
    )
    ShareCfgDimension = fields.Boolean(
        required=False,
        example=2,
        default=2,
        description="[apache-php] share config dimension in GB",
    )
    AppPort = fields.Integer(
        required=False,
        example=80,
        default=80,
        description="[apache-php] internal application prot",
    )
    FarmName = fields.String(
        required=True,
        example="tst-portali",
        description="[apache-php] parent compute zone id or uuid",
    )


class CreateAppInstancesApiParamRequestSchema(Schema):
    Name = fields.String(
        required=False,
        allow_none=True,
        missing="default istance name",
        description="instance name",
    )
    InstanceType = fields.String(
        required=True,
        example="small2",
        description="service definition of the instance",
    )
    AdditionalInfo = fields.String(required=False, allow_none=True, description="instance description")
    SubnetId = fields.String(required=False, example="12", description="instance id or uuid of the subnet")
    PublicSubnetId = fields.String(
        required=False,
        example="12",
        description="instance id or uuid of the public subnet",
    )
    IsPublic = fields.Boolean(
        required=False,
        example=False,
        missing=False,
        description="if True app engine is exposed with a public ip",
    )
    SecurityGroupId_N = fields.List(
        fields.String(example="12"),
        required=False,
        allow_none=False,
        data_key="SecurityGroupId.N",
        description="list of instance security group ids",
    )
    KeyName = fields.String(required=False, example="1ffd", description="The name of the key pair")
    owner_id = fields.String(
        required=False,
        example="1",
        description="account id or uuid associated to compute zone",
    )
    EngineConfigs = fields.Nested(
        CreateAppInstancesApiParamConfigsRequestSchema,
        required=False,
        description="App engine specific params",
    )


class CreateAppInstancesRequestSchema(Schema):
    instance = fields.Nested(CreateAppInstancesApiParamRequestSchema, context="body")


class CreateAppInstancesApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateAppInstancesRequestSchema, context="body")


class CreateAppInstancesApi3ResponseSchema(Schema):
    code = fields.Integer(required=False, default=0)
    name = fields.String(required=True, example="PENDING")


class CreateAppInstancesApi2ResponseSchema(Schema):
    instanceId = fields.Integer(required=True)
    currentState = fields.Nested(CreateAppInstancesApi3ResponseSchema, required=True)


class CreateAppInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    instances_set = fields.Nested(CreateAppInstancesApi2ResponseSchema, many=True, required=True)


class CreateAppInstancesResponseSchema(Schema):
    CreateAppInstanceResponse = fields.Nested(CreateAppInstancesApi1ResponseSchema, required=True)


class CreateAppInstances(ServiceApiView):
    tags = ["appengineservice"]
    definitions = {
        "CreateAppInstancesRequestSchema": CreateAppInstancesRequestSchema,
        "CreateAppInstancesResponseSchema": CreateAppInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateAppInstancesApiBodyRequestSchema)
    parameters_schema = CreateAppInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CreateAppInstancesResponseSchema}}
    )

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        """
        Create app engine instance
        Create app engine instance
        """
        inner_data = data.get("instance")

        service_definition_id = inner_data.get("InstanceType")
        account_id = inner_data.get("owner_id")
        name = inner_data.get("Name")
        desc = inner_data.get("AdditionalInfo")

        # check instance with the same name already exists
        self.service_exist(controller, name, ApiAppEngineInstance.plugintype)

        # check account
        account: ApiAccount
        parent_plugin: ApiComputeService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiComputeService.plugintype
        )

        data["computeZone"] = parent_plugin.resource_uuid
        inst = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        instances_set = [
            {
                "instanceId": inst.instance.uuid,
                "currentState": {"name": inst.instance.status},
            }
        ]
        res = self.format_create_response("CreateAppInstanceResponse", instances_set)

        return res, 202


class DeleteAppInstancesResponseItemSchema(Schema):
    requestId = fields.String(required=True, example="")
    Return = fields.Boolean(required=True, example=True)


class DeleteAppInstancesResponseSchema(Schema):
    DeleteAppInstancesResponse = fields.Nested(
        DeleteAppInstancesResponseItemSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteAppInstancesRequestSchema(Schema):
    InstanceId_N = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="InstanceId.N",
        description="instance uuid",
    )


class DeleteAppInstances(ServiceApiView):
    tags = ["appengineservice"]
    definitions = {
        "DeleteAppInstancesRequestSchema": DeleteAppInstancesRequestSchema,
        "DeleteAppInstancesResponseSchema": DeleteAppInstancesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteAppInstancesRequestSchema)
    parameters_schema = DeleteAppInstancesRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DeleteAppInstancesResponseSchema}}
    )

    def delete(self, controller: ServiceController, data, *args, **kwargs):
        """
        Terminate an instance
        Terminate an instance
        """
        instance_ids = data.pop("InstanceId_N")

        for instance_id in instance_ids:
            type_plugin = controller.get_service_type_plugin(instance_id, plugin_class=ApiAppEngineInstance)
            type_plugin.delete()

        res = {
            "DeleteAppInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "Return": True,
            }
        }

        return res, 202


class AppEngineInstanceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            (
                "%s/appengineservices/instance/describeappinstances" % base,
                "GET",
                DescribeAppInstances,
                {},
            ),
            (
                "%s/appengineservices/instance/createappinstances" % base,
                "POST",
                CreateAppInstances,
                {},
            ),
            (
                "%s/appengineservices/instance/deleteappinstances" % base,
                "DELETE",
                DeleteAppInstances,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
