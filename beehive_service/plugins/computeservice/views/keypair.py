# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from marshmallow import Schema, fields
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerWarning
from beehive.common.data import operation
from beehive_service.plugins.computeservice import ApiComputeService
from beehive_service.plugins.computeservice.controller import ApiComputeKeyPairs
from beehive_service.views import ServiceApiView
from beehive_service.controller import ServiceController
from beehive_service.controller.api_account import ApiAccount
from marshmallow.validate import Length
from base64 import b64decode
from marshmallow.validate import OneOf


class DescribeKeyPairItemResponseSchema(Schema):
    nvl_keyId = fields.String(
        required=True,
        allow_none=True,
        example="123",
        data_key="nvl-keyId",
        description="The id of the key pair",
    )
    keyName = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="The name of the key pair",
    )
    keyFingerprint = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="If you used CreateKeyPair to create the key pair, this is the SHA-1 "
        "digest of the DER encoded private key. If you used ImportKeyPair to "
        "provide AWS the public key, this is the MD5 public key fingerprint "
        "as specified in section 4 of RFC4716. ",
    )
    nvl_ownerAlias = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the account that owns the key",
        data_key="nvl-ownerAlias",
    )
    nvl_ownerId = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="ID of the account that owns the key",
        data_key="nvl-ownerId",
    )


class DescribeKeyPairResponseSchema(Schema):
    nvl_keyTotal = fields.Integer(
        required=True,
        allow_none=True,
        example="",
        description="",
        data_key="nvl-keyTotal",
    )
    requestId = fields.String(required=True, allow_none=True, example="", description="")
    keySet = fields.Nested(DescribeKeyPairItemResponseSchema, many=True, required=False)
    xmlns = fields.String(required=False, data_key="$xmlns")


class DescribeKeyPairsResponseSchema(Schema):
    DescribeKeyPairsResponse = fields.Nested(DescribeKeyPairResponseSchema, required=True, many=False, allow_none=False)


class DescribeKeyPairsRequestSchema(Schema):
    key_name_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="key-name.N",
        description="keypair name",
    )
    keyName_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="KeyName.N",
        description="keypair name",
    )
    # fingerprint_N = fields.List(fields.String(example=''), required=False,
    #                             allow_none=True, context='query',
    #                             collection_format='multi', data_key='fingerprint.N',
    #                             description='The fingerprint of the key pair. ')
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the keypair owner",
    )
    Nvl_MaxResults = fields.Integer(
        required=False,
        default=10,
        description="",
        context="query",
        data_key="Nvl-MaxResults",
    )
    Nvl_NextToken = fields.String(
        required=False,
        default="0",
        description="",
        context="query",
        data_key="Nvl-NextToken",
    )


class DescribeKeyPairs(ServiceApiView):
    summary = "Describe compute keypair"
    description = "Describe compute keypair"
    tags = ["computeservice"]
    definitions = {
        "DescribeKeyPairsRequestSchema": DescribeKeyPairsRequestSchema,
        "DescribeKeyPairsResponseSchema": DescribeKeyPairsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeKeyPairsRequestSchema)
    parameters_schema = DescribeKeyPairsRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": DescribeKeyPairsResponseSchema}})
    response_schema = DescribeKeyPairsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        # TODO: management filter by fingerprint
        # fingerprints = data.get('fingerprint_N', [])
        size = data.get("Nvl_MaxResults", 10)
        page = int(data.get("Nvl_NextToken", 0))

        # get key id
        instance_ids = data.get("key_name_N", [])
        instance_ids.extend(data.get("keyName_N", []))

        # check Account
        account_id_list, zone_list = self.get_account_list(controller, data, ApiComputeService)

        # get key pair instance
        keys, total = controller.get_service_type_plugins(
            service_name_list=instance_ids,
            account_id_list=account_id_list,
            plugintype=ApiComputeKeyPairs.plugintype,
            page=page,
            size=size,
            active=True,
        )
        instances = [k.aws_info() for k in keys]

        res = {
            "DescribeKeyPairsResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "keySet": instances,
                # 'nvl-keyTotal': len(keys)
                "nvl-keyTotal": total,
            }
        }
        return res, 200


class ExportKeyPairItemResponseSchema(Schema):
    nvl_keyId = fields.String(
        required=True,
        allow_none=True,
        example="123",
        data_key="nvl-keyId",
        description="The id of the key pair",
    )
    keyName = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="The name of the key pair",
    )
    keyFingerprint = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="If you used CreateKeyPair to create the key pair, this is the SHA-1 "
        "digest of the DER encoded private key. If you used ImportKeyPair to "
        "provide AWS the public key, this is the MD5 public key fingerprint "
        "as specified in section 4 of RFC4716. ",
    )
    nvl_ownerAlias = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the account that owns the key",
        data_key="nvl-ownerAlias",
    )
    nvl_ownerId = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="ID of the account that owns the key",
        data_key="nvl-ownerId",
    )
    priv_key = fields.String(required=True)
    pub_key = fields.String(required=True)


class ExportKeyPairResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True, example="", description="")
    instance = fields.Nested(ExportKeyPairItemResponseSchema, many=False, required=False)
    xmlns = fields.String(required=False, data_key="$xmlns")


class ExportKeyPairsResponseSchema(Schema):
    ExportKeyPairsResponse = fields.Nested(ExportKeyPairResponseSchema, required=True, many=False, allow_none=False)


class ExportKeyPairsRequestSchema(Schema):
    key_name_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="key-name.N",
        description="keypair name",
    )
    keyName_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="KeyName.N",
        description="keypair name",
    )
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the keypair owner",
    )


class ExportKeyPairs(ServiceApiView):
    summary = "Describe compute keypair"
    description = "Describe compute keypair"
    tags = ["computeservice"]
    definitions = {
        "ExportKeyPairsRequestSchema": ExportKeyPairsRequestSchema,
        "ExportKeyPairsResponseSchema": ExportKeyPairsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ExportKeyPairsRequestSchema)
    parameters_schema = ExportKeyPairsRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ExportKeyPairsResponseSchema}})
    response_schema = ExportKeyPairsResponseSchema

    def get(self, controller, data, *args, **kwargs):
        size = 1
        page = 0
        account_id_list = []

        # get key id
        instance_ids = data.get("key_name_N", [])
        instance_ids.extend(data.get("keyName_N", []))

        # get key pair instance
        keys, total = controller.get_service_type_plugins(
            service_name_list=instance_ids,
            account_id_list=account_id_list,
            plugintype=ApiComputeKeyPairs.plugintype,
            page=page,
            size=size,
            active=True,
        )

        instance = None
        if len(keys) > 0:
            apiComputeKeyPairs: ApiComputeKeyPairs = keys[0]
            instance = apiComputeKeyPairs.aws_info()

            key = apiComputeKeyPairs.get_resource(instance["keyName"])
            # instance['priv_key'] = key.get('priv_key')
            instance["priv_key"] = b64decode(key.get("priv_key")).decode("utf-8")
            instance["pub_key"] = b64decode(key.get("pub_key")).decode("utf-8")

        res = {
            "ExportKeyPairsResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "instance": instance,
            }
        }
        return res, 200


class CreateKeyPairParamRequestSchema(Schema):
    # AccountId managed by AWS Wrapper
    owner_id = fields.String(
        required=True,
        example="1",
        data_key="owner-id",
        description="account id or uuid associated to compute zone",
    )
    KeyName = fields.String(
        required=True,
        example="ssh-key1",
        validate=Length(min=8, max=100),
        description="name for the key pair",
    )
    Nvl_KeyPairType = fields.String(
        required=False,
        missing=None,
        description="Key pair type definition",
        data_key="Nvl-KeyPairType",
        validate=OneOf(["DefaultKeyPair", "KeyPair.Private"]),
    )


class CreateKeyPairRequestSchema(Schema):
    keypair = fields.Nested(CreateKeyPairParamRequestSchema, context="body")


class CreateKeyPairBodyRequestSchema(Schema):
    body = fields.Nested(CreateKeyPairRequestSchema, context="body")


class CreateKeyPairApiResponse1Schema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    keyName = fields.String(
        required=False,
        allow_none=True,
        example="my-key-name",
        description="name of the key pair",
    )
    keyFingerprint = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="The SHA-1 digest of the DER encoded private key",
    )
    keyMaterial = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="An unencrypted PEM encoded RSA private key",
    )


class CreateKeyPairApiResponseSchema(Schema):
    CreateKeyPairResponse = fields.Nested(CreateKeyPairApiResponse1Schema, required=True, allow_none=False)


class CreateKeyPair(ServiceApiView):
    summary = "Create compute keypair"
    description = "Create compute keypair"
    tags = ["computeservice"]
    definitions = {
        "CreateKeyPairRequestSchema": CreateKeyPairRequestSchema,
        "CreateKeyPairApiResponseSchema": CreateKeyPairApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateKeyPairBodyRequestSchema)
    parameters_schema = CreateKeyPairRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CreateKeyPairApiResponseSchema}})
    response_schema = CreateKeyPairApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        data = data.get("keypair")
        service_definition_id = data.get("Nvl_KeyPairType")
        name = data.get("KeyName")
        desc = name
        # check account
        account: ApiAccount
        parent_plugin: ApiComputeService
        account, parent_plugin = self.check_parent_service(
            controller, data.get("owner_id"), plugintype=ApiComputeService.plugintype
        )

        # get definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiComputeKeyPairs.plugintype)
            service_definition_id = service_definition.oid

        # create instance and resource
        data["computeZone"] = parent_plugin.resource_uuid
        inst: ApiComputeKeyPairs = controller.add_service_type_plugin(
            service_definition_id,
            account.oid,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            account=account,
        )

        # keyFingerprint = The SHA-1 digest of the DER encoded private key.
        # keyMaterial = An unencrypted PEM encoded RSA private key
        response = {"CreateKeyPairResponse": {"__xmlns": self.xmlns, "requestId": operation.id}}
        response["CreateKeyPairResponse"].update(inst.aws_create_info())
        return response, 201


class DeleteKeyPairResponse1Schema(Schema):
    return_ = fields.Boolean(required=True, data_key="return")
    requestId = fields.String(required=True, allow_none=True)


class DeleteKeyPairResponseSchema(Schema):
    DeleteKeyPairResponse = fields.Nested(DeleteKeyPairResponse1Schema, required=True, allow_none=False)


class DeleteKeyPairRequestSchema(Schema):
    # AccountId managed by AWS Wrapper
    # owner_id = fields.String(required=False, example='1', data_key='owner-id',
    # description='account id or uuid associated to compute zone')
    Nvl_KeyPairId = fields.String(
        required=False,
        example="1",
        data_key="Nvl-KeyPairId",
        description="identifier key pair instance",
    )
    KeyName = fields.String(required=True, example="", description="name of the key pair")


class DeleteKeyPairBodyRequestSchema(Schema):
    body = fields.Nested(DeleteKeyPairRequestSchema, context="body")


class DeleteKeyPair(ServiceApiView):
    summary = "Delete compute keypair"
    description = "Delete compute keypair"
    tags = ["computeservice"]
    definitions = {
        "DeleteKeyPairRequestSchema": DeleteKeyPairRequestSchema,
        "DeleteKeyPairResponseSchema": DeleteKeyPairResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteKeyPairBodyRequestSchema)
    parameters_schema = DeleteKeyPairRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": DeleteKeyPairResponseSchema}})
    response_schema = DeleteKeyPairResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        key_name = data.get("KeyName")
        # get Plugin
        plugin = controller.get_service_type_plugin(key_name, ApiComputeKeyPairs)
        plugin.delete(key_name=key_name)
        response = {
            "DeleteKeyPairResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "return": True,
            }
        }

        return response, 202


class ImportKeyPairResponse1Schema(Schema):
    requestId = fields.String(required=True, allow_none=True, example="", description="")
    keyName = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="The name of the key pair",
    )
    keyFingerprint = fields.String(
        required=True,
        allow_none=True,
        example="",
        description="the MD5 public key fingerprint",
    )


class ImportKeyPairResponseSchema(Schema):
    ImportKeyPairResponse = fields.Nested(ImportKeyPairResponse1Schema, required=True, many=False, allow_none=False)


class ImportKeyPairParamRequestSchema(Schema):
    # AccountId managed by AWS Wrapper
    owner_id = fields.String(
        required=True,
        example="1",
        data_key="owner-id",
        description="account id or uuid associated to compute zone",
    )
    KeyName = fields.String(required=True, example="", description="keypair name")
    Nvl_KeyPairType = fields.String(
        required=False,
        missing=None,
        description="Key pair type definition",
        data_key="Nvl-KeyPairType",
        validate=OneOf(["DefaultKeyPair", "KeyPair.Private"]),
    )
    PublicKeyMaterial = fields.String(required=True, example="", description="public key base64-encoded")


class ImportKeyPairRequestSchema(Schema):
    keypair = fields.Nested(ImportKeyPairParamRequestSchema, context="body")


class ImportKeyPairBodyRequestSchema(Schema):
    body = fields.Nested(ImportKeyPairRequestSchema, context="body")


class ImportKeyPair(ServiceApiView):
    summary = "Imports the public key from an RSA key pair"
    description = "Imports the public key from an RSA key pair"
    tags = ["computeservice"]
    definitions = {
        "ImportKeyPairRequestSchema": ImportKeyPairRequestSchema,
        "ImportKeyPairResponseSchema": ImportKeyPairResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ImportKeyPairBodyRequestSchema)
    parameters_schema = ImportKeyPairRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ImportKeyPairResponseSchema}})
    response_schema = ImportKeyPairResponseSchema

    def post(self, controller, data, *args, **kwargs):
        data = data.get("keypair")
        service_definition_id = data.pop("Nvl_KeyPairType")
        public_key_material = data.pop("PublicKeyMaterial")
        name = data.get("KeyName")
        desc = name

        # check account
        account, parent_plugin = self.check_parent_service(
            controller, data.get("owner_id"), plugintype=ApiComputeService.plugintype
        )
        try:
            b64decode(public_key_material)
        except TypeError:
            raise ApiManagerWarning("Provide a base64 encoded PublicKeyMaterial for KeyPair %s " % name)

        # get definition
        if service_definition_id is None:
            service_definition = controller.get_default_service_def(ApiComputeKeyPairs.plugintype)
            service_definition_id = service_definition.oid

        # create instance and resource
        # data['action'] = 'ImportKeyPair'
        action = "ImportKeyPair"
        data["computeZone"] = parent_plugin.resource_uuid
        data["service_definition_id"] = service_definition_id

        instance = controller.add_service_type_plugin(
            service_definition_id,
            account.oid,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
            action=action,
            public_key_material=public_key_material,
        )
        response = {"ImportKeyPairResponse": {"$xmlns": self.xmlns, "requestId": operation.id}}
        response["ImportKeyPairResponse"].update(instance.aws_import_info())

        return response, 200


class ComputeKeyPairAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            (
                "%s/computeservices/keypair/describekeypairs" % base,
                "GET",
                DescribeKeyPairs,
                {},
            ),
            (
                "%s/computeservices/keypair/importkeypair" % base,
                "POST",
                ImportKeyPair,
                {},
            ),
            (
                "%s/computeservices/keypair/createkeypair" % base,
                "POST",
                CreateKeyPair,
                {},
            ),
            (
                "%s/computeservices/keypair/deletekeypair" % base,
                "DELETE",
                DeleteKeyPair,
                {},
            ),
            # ('%s/computeservices/keypair/exportkeypairs' % base, 'GET', ExportKeyPairs, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
