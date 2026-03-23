# SPDX# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import Callable
from flasgger import fields, Schema
from marshmallow.validate import Range
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.model import Division, Organization
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import (
    ApiManagerError,
    SwaggerApiView,
    ApiView
)
from beehive_service.plugins.containerservice.controller_service import ApiContainerService
from beehive_service.plugins.containerservice.controller_namespace import ApiNamespaceInstance

from beehive.common.data import operation


# 200m (indica come valore 200 millicpu) - 2 (indica come valore 2cpu)
def validator_cpu(value: str) -> Callable[[str], None]:
    import re
    print("_validate_cpu - value %s" % value)
    if value is None or value.strip() == "":
        return
    if re.match(r"^\d+m$", value) or re.match(r"^\d+$", value):
        print("_validate_cpu - check ok %s" % value)
    else:
        raise ApiManagerError("limit_cpu error value")

# 2Gi (indica come valore 2 Giga) - 2Mi (indica come valore per 2 Mega)
def validator_memory(value: str) -> Callable[[str], None]:
    import re
    print("_validate_memory - value %s" % value)
    if value is None or value.strip() == "":
        return
    if re.match(r"^\d+Gi$", value) or re.match(r"^\d+Mi$", value):
        print("_validate_memory - check ok %s" % value)
    else:
        raise ApiManagerError("limit_memory error value")

# 2 (indica come valore 2 Giga Byte) 0 (nel caso non sia necessario spazio nel namespace)
def validator_storage(value: str) -> Callable[[str], None]:
    import re
    print("_validate_storage - value %s" % value)
    if value is None or value.strip() == "":
        return
    if re.match(r"^\d+Gi$", value):
        print("_validate_storage - check ok %s" % value)
    else:
        raise ApiManagerError("limit_storage error value")

class CommonNamespaceApiParamRequestSchema(Schema):
    cluster_name = fields.String(required=False, metadata={"description": "namespace cluster_name"})

    codice_ente = fields.String(required=False, metadata={"description": "namespace codice_ente"})
    codice_prodotto = fields.String(required=False, metadata={"description": "namespace codice_prodotto"})
    environment = fields.String(required=False, metadata={"description": "namespace environment"})
    email_pm = fields.String(required=False, metadata={"description": "namespace email_pm"})

    limit_cpu = fields.String(required=False, validate=validator_cpu, metadata={"description": "namespace limit_cpu"})
    limit_memory = fields.String(
        required=False,
        validate=validator_memory,
        metadata={"description": "namespace limit_memory"},
    )
    limit_storage = fields.String(
        required=False,
        validate=validator_storage,
        metadata={"description": "namespace limit_storage"},
    )

    backup_policy = fields.String(required=False, metadata={"description": "namespace backup_policy"})

    allowedHosts = fields.String(required=False, allow_none=True, metadata={"description": "namespace allowedHosts"})
    allowedHostPatterns = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "namespace allowedHostPatterns"},
    )
    allowedCIDR = fields.String(required=False, allow_none=True, metadata={"description": "namespace allowedCIDR"})

    networkPolicyActive = fields.Boolean(required=False, allow_none=True)

    chartTargetRevision = fields.String(required=False, allow_none=True)

    norescreate = fields.Boolean(

        required=False,

        allow_none=True,

        metadata={"description": "don't create physical resource of the namespace"},

    )


class CreateNamespaceApiParamRequestSchema(CommonNamespaceApiParamRequestSchema):
    owner_id = fields.String(
        required=True,
        data_key="owner-id",
        metadata={"example": "1", "description": "account id or uuid associated to compute zone"},
    )
    name = fields.String(required=False, load_default=None, metadata={"description": "namespace name"})


class CreateNamespaceApiRequestSchema(Schema):
    namespace = fields.Nested(CreateNamespaceApiParamRequestSchema, context="body")


class CreateNamespaceApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateNamespaceApiRequestSchema, context="body")


class CreateNamespaceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    namespaceId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "namespace id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
    )


class CreateNamespaceApiResponseSchema(Schema):
    CreateNamespaceResponse = fields.Nested(
        CreateNamespaceApiResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateNamespace(ServiceApiView):
    summary = "Create container namespace"
    description = "Create container namespace"
    tags = ["containerservice"]
    definitions = {
        "CreateNamespaceApiResponseSchema": CreateNamespaceApiResponseSchema,
        "CreateNamespaceApiRequestSchema": CreateNamespaceApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateNamespaceApiBodyRequestSchema)
    parameters_schema = CreateNamespaceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CreateNamespaceApiResponseSchema}})
    response_schema = CreateNamespaceApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        self.logger.debug("CreateNamespace post - begin")
        inner_data = data.get("namespace")

        account_id = inner_data.get("owner_id")
        name = inner_data.get("name", None)

        # check account
        account: ApiAccount
        parent_plugin: ApiContainerService
        account, parent_plugin = self.check_parent_service(
            controller, account_id, plugintype=ApiContainerService.plugintype
        )
        data["computeZone"] = parent_plugin.resource_uuid

        # default definition
        service_definition_id = None
        service_definition: ApiServiceDefinition = None
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiNamespaceInstance.plugintype)
        else:
            service_definition = controller.get_service_def(service_definition_id)
        self.logger.debug("CreateNamespace - service_definition: %s" % service_definition)

        # get parent division
        div: Division = controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org: Organization = controller.manager.get_entity(Organization, div.organization_id)
        triplet = "%s.%s.%s" % (org.name, div.name, account.name)
        self.logger.debug("CreateNamespace - triplet: %s" % triplet)

        data.update({"triplet": triplet})
        data.update({"organization": org.name})
        data.update({"division": div.name})
        data.update({"account": account.name})

        plugin: ApiNamespaceInstance
        plugin = controller.add_service_type_plugin(
            service_definition.oid,
            account_id,
            name=name,
            desc=name,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        res = {
            "CreateNamespaceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "namespaceId": plugin.instance.uuid,
                "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class UpdateNamespaceApiParamRequestSchema(CommonNamespaceApiParamRequestSchema):
    oid = fields.String(required=True)


class UpdateNamespaceApiRequestSchema(Schema):
    namespace = fields.Nested(UpdateNamespaceApiParamRequestSchema, context="body")


class UpdateNamespaceApiBodyRequestSchema(Schema):
    body = fields.Nested(UpdateNamespaceApiRequestSchema, context="body")


class UpdateNamespaceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, allow_none=True)
    namespaceId = fields.String(
        required=True,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "namespace id"},
    )
    # nvl_activeTask = fields.String(
    #     required=True,
    #     example="29647df5-5228-46d0-a2a9-09ac9d84c099",
    #     data_key="nvl-activeTask",
    #     description="task id",
    # )


class UpdateNamespaceApiResponseSchema(Schema):
    UpdateNamespaceResponse = fields.Nested(
        UpdateNamespaceApiResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class UpdateNamespace(ServiceApiView):
    summary = "Update container namespace"
    description = "Update container namespace"
    tags = ["containerservice"]
    definitions = {
        "UpdateNamespaceApiResponseSchema": UpdateNamespaceApiResponseSchema,
        "UpdateNamespaceApiRequestSchema": UpdateNamespaceApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(UpdateNamespaceApiBodyRequestSchema)
    parameters_schema = UpdateNamespaceApiRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": UpdateNamespaceApiResponseSchema}})
    response_schema = UpdateNamespaceApiResponseSchema

    def put(self, controller: ServiceController, data: dict, *args, **kwargs):
        self.logger.debug("UpdateNamespace post - begin")
        inner_data = data.get("namespace")
        oid = inner_data.get("oid")
        type_plugin: ApiNamespaceInstance = controller.get_service_type_plugin(oid, plugin_class=ApiNamespaceInstance)
        self.logger.debug("UpdateNamespace post - type_plugin: %s" % type_plugin)
        type_plugin.update(**data)

        res = {
            "UpdateNamespaceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "namespaceId": oid,
                # "nvl-activeTask": plugin.active_task,
            }
        }
        return res, 202


class DeleteNamespaceApiRequestSchema(Schema):
    NamespaceId = fields.String(
        required=False,
        context="query",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "namespace id"},
    )
    noresdelete = fields.Boolean(
        required=False,
        allow_none=True,
        context="query",
        metadata={"description": "don't delete physical resource of the namespace"},
    )


class DeleteNamespaceApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    requestId = fields.String(required=True, metadata={"description": "operation id"})
    namespaceId = fields.String(
        required=False,
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "namespace id"},
    )
    nvl_activeTask = fields.String(
        required=True,
        data_key="nvl-activeTask",
        metadata={"example": "29647df5-5228-46d0-a2a9-09ac9d84c099", "description": "task id"},
    )


class DeleteNamespaceApiResponseSchema(Schema):
    DeleteNamespaceResponse = fields.Nested(
        DeleteNamespaceApiResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteNamespace(ServiceApiView):
    summary = "Delete container namespace"
    description = "Delete container namespace"
    tags = ["containerservice"]
    definitions = {
        "DeleteNamespaceApiRequestSchema": DeleteNamespaceApiRequestSchema,
        "DeleteNamespaceApiResponseSchema": DeleteNamespaceApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteNamespaceApiRequestSchema)
    parameters_schema = DeleteNamespaceApiRequestSchema
    responses = ServiceApiView.setResponses(
        {202: {"description": "no response", "schema": DeleteNamespaceApiResponseSchema}}
    )
    response_schema = DeleteNamespaceApiResponseSchema

    def delete(self, controller: ServiceController, data: dict, *args, **kwargs):
        namespace_id = data.get("NamespaceId")
        type_plugin: ApiNamespaceInstance
        type_plugin = controller.get_service_type_plugin(namespace_id)

        if isinstance(type_plugin, ApiNamespaceInstance):
            type_plugin.delete(**data)
        else:
            raise ApiManagerError("Instance is not a NamespaceInstance")

        res = {
            "DeleteNamespaceResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "namespaceId": type_plugin.instance.uuid,
                "nvl-activeTask": type_plugin.active_task,
            }
        }
        return res, 202


class NamespaceInstanceStateReasonResponseSchema(Schema):
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


class NamespaceDetailResponseSchema(Schema):
    cluster_name = fields.String(required=False, allow_none=True)
    codice_ente = fields.String(required=False, allow_none=True)
    codice_prodotto = fields.String(required=False, allow_none=True)
    environment = fields.String(required=False, allow_none=True)
    email_pm = fields.String(required=False, allow_none=True)

    limit_cpu = fields.String(required=False, allow_none=True)
    limit_memory = fields.String(required=False, allow_none=True)
    limit_storage = fields.String(required=False, allow_none=True)

    backup_policy = fields.String(required=False, allow_none=True)
    allowedHosts = fields.String(required=False, allow_none=True)
    allowedHostPatterns = fields.String(required=False, allow_none=True)
    allowedCIDR = fields.String(required=False, allow_none=True)
    networkPolicyActive = fields.Boolean(required=False, allow_none=True)

    chartTargetRevision = fields.String(required=False, allow_none=True)


class NamespaceInstanceItemParameterResponseSchema(Schema):
    id = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "id of the namespace"},
    )
    name = fields.String(required=True, metadata={"example": "test", "description": "name of the namespace"})
    creationDate = fields.DateTime(
        required=True,
        metadata={"example": "2022-01-25T11:20:18Z", "description": "creation date"},
    )
    description = fields.String(
        required=True,
        metadata={"example": "test", "description": "description of the namespace"},
    )
    ownerId = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "account id of the owner of the namespace"},
    )
    ownerAlias = fields.String(
        required=True,
        allow_none=True,
        metadata={"example": "test", "description": "account name of the owner of the namespace"},
    )
    state = fields.String(
        required=True,
        data_key="state",
        metadata={"example": "available", "description": "state of the namespace"},
    )
    stateReason = fields.Nested(
        NamespaceInstanceStateReasonResponseSchema,
        many=False,
        required=True,
        metadata={"description": "state namespace description"},
    )
    templateId = fields.String(
        required=True,
        metadata={"example": "075df680-2560-421c-aeaa-8258a6b733f0", "description": "id of the namespace template"},
    )
    templateName = fields.String(
        required=True,
        metadata={"example": "test", "description": "name of the namespace template"},
    )
    resource_uuid = fields.String(required=False, allow_none=True)
    namespace = fields.Nested(
        NamespaceDetailResponseSchema,
        many=False,
        required=False,
        metadata={"description": "namespace detail"},
    )


class DescribeNamespaceInstances1ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    next_token = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True, allow_none=True)
    namespaceInfo = fields.Nested(
        NamespaceInstanceItemParameterResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )
    namespaceTotal = fields.Integer(
        required=False,
        data_key="namespaceTotal",
        metadata={"example": "0", "description": "total container instance"},
    )


class DescribeNamespacesResponseSchema(Schema):
    DescribeNamespacesResponse = fields.Nested(DescribeNamespaceInstances1ResponseSchema, required=True, many=False)


class DescribeNamespacesRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        metadata={"description": "account id"},
    )
    NamespaceName = fields.String(required=False, context="query", metadata={"description": "namespace name"})
    name_pattern = fields.String(
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="name-pattern",
        metadata={"description": "name of the instance"},
    )
    namespace_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="namespace-id.N",
        metadata={"description": "list of namespace id"},
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


class DescribeNamespaces(ServiceApiView):
    summary = "Describe container namespace"
    description = "Describe container namespace"
    tags = ["containerservice"]
    definitions = {
        "DescribeNamespacesRequestSchema": DescribeNamespacesRequestSchema,
        "DescribeNamespacesResponseSchema": DescribeNamespacesResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeNamespacesRequestSchema)
    parameters_schema = DescribeNamespacesRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": DescribeNamespacesResponseSchema}})
    response_schema = DescribeNamespacesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        container_id_list = []

        data_search = {}
        data_search["size"] = data.get("MaxItems")
        data_search["page"] = int(data.get("Marker"))

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("namespace_id_N", [])
        self.logger.debug("DescribeNamespaces get - instance_id_list: %s" % instance_id_list)

        # get instance name
        instance_name_list = data.get("NamespaceName", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]
        self.logger.debug("DescribeNamespaces get - instance_name_list: %s" % instance_name_list)

        instance_name_pattern = data.get("name_pattern", None)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            name=instance_name_pattern,
            service_id_list=container_id_list,
            account_id_list=account_id_list,
            plugintype=ApiNamespaceInstance.plugintype,
            **data_search,
        )
        instances_set = []
        for r in res:
            r: ApiNamespaceInstance
            instances_set.append(r.aws_info())

        if total == 0:
            next_token = "0"
        else:
            next_token = str(data_search["page"] + 1)

        res = {
            "DescribeNamespacesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "next_token": next_token,
                "namespaceInfo": instances_set,
                "namespaceTotal": total,
            }
        }
        return res


class DescribeNamespaceClusterNameApiRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id"},
    )


class DescribeNamespaceClusterNameParamsApiResponseSchema(Schema):
    cluster_name = fields.String(required=True)


class DescribeNamespaceClusterNameDetailApiResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    clusterSet = fields.Nested(
        DescribeNamespaceClusterNameParamsApiResponseSchema,
        many=True,
        allow_none=False,
        metadata={"description": ""},
    )


class DescribeNamespaceClusterNameApiResponseSchema(Schema):
    DescribeNamespaceClusterNameResponse = fields.Nested(
        DescribeNamespaceClusterNameDetailApiResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeNamespaceClusterNames(ServiceApiView):
    summary = "List of namespace cluster"
    description = "List of namespace cluster"
    tags = ["containerservice"]
    definitions = {
        "DescribeNamespaceClusterNameApiRequestSchema": DescribeNamespaceClusterNameApiRequestSchema,
        "DescribeNamespaceClusterNameApiResponseSchema": DescribeNamespaceClusterNameApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeNamespaceClusterNameApiRequestSchema)
    parameters_schema = DescribeNamespaceClusterNameApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeNamespaceClusterNameApiResponseSchema,
            }
        }
    )
    response_schema = DescribeNamespaceClusterNameApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)
        cluster_set, total = account.get_definitions(plugintype="VirtualService", size=-1)
        clusterSet = []
        for def_cluster in cluster_set:
            apiServiceDefinition: ApiServiceDefinition = def_cluster
            def_name: str = apiServiceDefinition.name
            if def_name.find("namespace.cluster.") != 0:
                continue

            # cluster_name = name[len("namespace.cluster."):]
            cluster_name = apiServiceDefinition.get_config("cluster_name")
            item = {
                "cluster_name": cluster_name,
            }
            clusterSet.append(item)

        res = {
            "DescribeNamespaceClusterNameResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "clusterSet": clusterSet,
            }
        }
        return res


class DescribeNamespaceEnvironmentApiRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id"},
    )


class DescribeNamespaceEnvironmentParamsApiResponseSchema(Schema):
    environment_name = fields.String(required=True)


class DescribeNamespaceEnvironmentDetailApiResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    environmentSet = fields.Nested(
        DescribeNamespaceEnvironmentParamsApiResponseSchema,
        many=True,
        allow_none=False,
        metadata={"description": ""},
    )


class DescribeNamespaceEnvironmentApiResponseSchema(Schema):
    DescribeNamespaceEnvironmentResponse = fields.Nested(
        DescribeNamespaceEnvironmentDetailApiResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeNamespaceEnvironments(ServiceApiView):
    summary = "List of namespace environment"
    description = "List of namespace environment"
    tags = ["containerservice"]
    definitions = {
        "DescribeNamespaceEnvironmentApiRequestSchema": DescribeNamespaceEnvironmentApiRequestSchema,
        "DescribeNamespaceEnvironmentApiResponseSchema": DescribeNamespaceEnvironmentApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeNamespaceEnvironmentApiRequestSchema)
    parameters_schema = DescribeNamespaceEnvironmentApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeNamespaceEnvironmentApiResponseSchema,
            }
        }
    )
    response_schema = DescribeNamespaceEnvironmentApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        environmentSet = []

        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)
        def_namespaces, total = account.get_definitions(plugintype=ApiNamespaceInstance.plugintype, size=-1)
        for def_namespace in def_namespaces:
            apiServiceDefinition: ApiServiceDefinition = def_namespace

            def_environments = apiServiceDefinition.get_config("environments")
            for def_environment in def_environments:
                item = {
                    "environment_name": def_environment,
                }
                environmentSet.append(item)

            break

        res = {
            "DescribeNamespaceEnvironmentResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "environmentSet": environmentSet,
            }
        }
        return res


class DescribeNamespaceBackupPolicyApiRequestSchema(Schema):
    owner_id = fields.String(
        required=True,
        context="query",
        data_key="owner-id",
        metadata={"example": "d35d19b3-d6b8-4208-b690-a51da2525497", "description": "account id"},
    )

class DescribeNamespaceBackupPolicyParamsApiResponseSchema(Schema):
    backup_policy_name = fields.String(required=True)


class DescribeNamespaceBackupPolicyDetailApiResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, metadata={"description": "api request id"})
    backupPolicySet = fields.Nested(
        DescribeNamespaceBackupPolicyParamsApiResponseSchema,
        many=True,
        allow_none=False,
        metadata={"description": ""},
    )


class DescribeNamespaceBackupPolicyApiResponseSchema(Schema):
    DescribeNamespaceBackupPolicyResponse = fields.Nested(
        DescribeNamespaceBackupPolicyDetailApiResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeNamespaceBackupPolicies(ServiceApiView):
    summary = "List of namespace backupPolicy"
    description = "List of namespace backupPolicy"
    tags = ["containerservice"]
    definitions = {
        "DescribeNamespaceBackupPolicyApiRequestSchema": DescribeNamespaceBackupPolicyApiRequestSchema,
        "DescribeNamespaceBackupPolicyApiResponseSchema": DescribeNamespaceBackupPolicyApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeNamespaceBackupPolicyApiRequestSchema)
    parameters_schema = DescribeNamespaceBackupPolicyApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeNamespaceBackupPolicyApiResponseSchema,
            }
        }
    )
    response_schema = DescribeNamespaceBackupPolicyApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        backupPolicySet = []

        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)
        def_namespaces, total = account.get_definitions(plugintype=ApiNamespaceInstance.plugintype, size=-1)
        for def_namespace in def_namespaces:
            apiServiceDefinition: ApiServiceDefinition = def_namespace

            def_backupPolicys = apiServiceDefinition.get_config("backup_policies")
            for def_backupPolicy in def_backupPolicys:
                item = {
                    "backup_policy_name": def_backupPolicy,
                }
                backupPolicySet.append(item)

            break

        res = {
            "DescribeNamespaceBackupPolicyResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "backupPolicySet": backupPolicySet,
            }
        }
        return res

class NamespaceInstanceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/containerservices/namespaces"
        rules = [
            ("%s/createnamespace" % base, "POST", CreateNamespace, {}),
            ("%s/updatenamespace" % base, "PUT", UpdateNamespace, {}),
            ("%s/deletenamespace" % base, "DELETE", DeleteNamespace, {}),
            ("%s/describenamespaces" % base, "GET", DescribeNamespaces, {}),

            ("%s/clusternames" % base, "GET", DescribeNamespaceClusterNames, {}),
            ("%s/environments" % base, "GET", DescribeNamespaceEnvironments, {}),
            ("%s/backuppolicies" % base, "GET", DescribeNamespaceBackupPolicies, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
