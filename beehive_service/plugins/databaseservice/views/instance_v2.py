# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerError
from marshmallow.validate import OneOf, Range
from beehive_service.controller import ServiceController
from beehive_service.plugins.databaseservice.controller import (
    ApiDatabaseServiceInstance,
    ApiDatabaseService,
)
from beehive.common.data import operation
from beehive_service.views import ServiceApiView
from .check import validate_ora_db_name


class InstanceTypeFeatureV2ResponseSchema(Schema):
    vcpus = fields.String(required=False, allow_none=True, example="", description="")
    ram = fields.String(required=False, allow_none=True, example="", description="")
    disk = fields.String(required=False, allow_none=True, example="", description="")


class InstanceTypeV2ResponseSchema(Schema):
    id = fields.Integer(required=True, example="", description="")
    uuid = fields.String(required=True, example="", description="")
    name = fields.String(required=True, example="", description="")
    resource_id = fields.String(required=False, allow_none=True, example="", description="")
    description = fields.String(required=True, allow_none=True, example="", description="")
    features = fields.Nested(InstanceTypeFeatureV2ResponseSchema, required=True, many=False, allow_none=False)


class DescribeDBInstanceTypesApi1V2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True)
    instanceTypesSet = fields.Nested(InstanceTypeV2ResponseSchema, required=True, many=True, allow_none=True)
    instanceTypesTotal = fields.Integer(required=True)


class DescribeDBInstanceTypesApiV2ResponseSchema(Schema):
    DescribeDBInstanceTypesResponse = fields.Nested(
        DescribeDBInstanceTypesApi1V2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceTypesApiV2RequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False,
        default=10,
        missing=10,
        description="entities list page size",
        context="query",
    )
    NextToken = fields.Integer(
        required=False,
        default=0,
        missing=0,
        description="entities list page selected",
        context="query",
    )
    owner_id = fields.String(
        example="d35d19b3-d6b8-4208-b690-a51da2525497",
        required=True,
        context="query",
        data_key="owner-id",
        description="account id of the instance type owner",
    )
    InstanceType = fields.String(
        example="d35d19b3-d6b8-4208-b690-a51da2525497",
        required=False,
        context="query",
        missing=None,
        data_key="InstanceType",
        description="instance type id",
    )


class DescribeDBInstanceTypes(ServiceApiView):
    summary = "List of active instance types"
    description = "List of active instance types"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDBInstanceTypesApiV2RequestSchema": DescribeDBInstanceTypesApiV2RequestSchema,
        "DescribeDBInstanceTypesApiV2ResponseSchema": DescribeDBInstanceTypesApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceTypesApiV2RequestSchema)
    parameters_schema = DescribeDBInstanceTypesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceTypesApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeDBInstanceTypesApiV2ResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        size = data.pop("MaxResults")
        page = data.pop("NextToken")
        def_id = data.pop("InstanceType")
        account = controller.get_account(account_id)

        instance_types_set, total = account.get_definitions(
            plugintype=ApiDatabaseServiceInstance.plugintype,
            service_definition_id=def_id,
            size=size,
            page=page,
        )

        res_type_set = []
        for r in instance_types_set:
            res_type_item = {
                "id": r.oid,
                "uuid": r.uuid,
                "name": r.name,
                "description": r.desc,
            }

            features = []
            if r.desc is not None:
                features = r.desc.split(" ")

            feature = {}
            for f in features:
                try:
                    k, v = f.split(":")
                    feature[k] = v
                except ValueError:
                    pass

            res_type_item["features"] = feature
            res_type_set.append(res_type_item)

        if total == 1:
            res_type_set[0]["config"] = instance_types_set[0].get_main_config().params

        res = {
            "DescribeDBInstanceTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceTypesSet": res_type_set,
                "instanceTypesTotal": total,
            }
        }
        return res


class DescribeDBInstanceEngineTypesApiV2RequestSchema(Schema):
    owner_id = fields.String(
        example="d35d19b3-d6b8-4208-b690-a51da2525497",
        required=True,
        context="query",
        data_key="owner-id",
        description="account id of the instance type owner",
    )


class DescribeDBInstanceEngineTypesParamsApiV2ResponseSchema(Schema):
    engine = fields.String(required=True, example="", description="")
    engineVersion = fields.String(required=True, example="", description="")


class DescribeDBInstanceEngineTypesApi1V2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="$xmlns")
    requestId = fields.String(required=True, description="api request id")
    engineTypesSet = fields.Nested(
        DescribeDBInstanceEngineTypesParamsApiV2ResponseSchema,
        many=True,
        allow_none=False,
        example="",
        description="",
    )
    engineTypesTotal = fields.Integer(required=True, example="", description="")


class DescribeDBInstanceEngineTypesApiV2ResponseSchema(Schema):
    DescribeDBInstanceEngineTypesResponse = fields.Nested(
        DescribeDBInstanceEngineTypesApi1V2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceEngineTypes(ServiceApiView):
    summary = "List of db instance engine types"
    description = "List of db instance engine types"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDBInstanceEngineTypesApiV2RequestSchema": DescribeDBInstanceEngineTypesApiV2RequestSchema,
        "DescribeDBInstanceEngineTypesApiV2ResponseSchema": DescribeDBInstanceEngineTypesApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceEngineTypesApiV2RequestSchema)
    parameters_schema = DescribeDBInstanceEngineTypesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceEngineTypesApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeDBInstanceEngineTypesApiV2ResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        account_id = data.pop("owner_id")
        account = controller.get_account(account_id)

        # instance_engines_set, total = controller.get_catalog_service_definitions(plugintype='VirtualService')
        # self.logger.warn(instance_engines_set)

        instance_engines_set, total = account.get_definitions(plugintype="VirtualService", size=-1)

        res_type_set = []
        for r in instance_engines_set:
            name = r.name

            if r.name.find("db-engine") != 0:
                continue
            esplit = r.name.split("-")
            item = {"engine": esplit[2], "engineVersion": esplit[3]}
            res_type_set.append(item)
            total += 1

        res = {
            "DescribeDBInstanceEngineTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "engineTypesSet": res_type_set,
                "engineTypesTotal": total,
            }
        }
        return res


class StateReasonV2ResponseSchema(Schema):
    nvl_code = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state code",
        data_key="nvl-code",
    )
    nvl_message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="state message",
        data_key="nvl-message",
    )


class AVZoneV2ResponseSchema(Schema):
    Name = fields.String(required=False, allow_none=True)


class AvailabilityZoneResponseSchema(Schema):
    AvailabilityZone = fields.Nested(AVZoneV2ResponseSchema, many=False, allow_none=False, example="", description="")


class SubnetV2ResponseSchema(Schema):
    SubnetAvailabilityZone = fields.Nested(
        AvailabilityZoneResponseSchema,
        many=False,
        allow_none=False,
        example="",
        description="",
    )
    SubnetIdentifier = fields.String(required=False, example="", description="ID of the subnet")
    SubnetStatus = fields.String(required=False, example="", description="status of the subnet")


class DBParameterGroupStatus1V2ResponseSchema(Schema):
    DBParameterGroupName = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the DB parameter group applied to DB instance",
    )
    ParameterApplyStatus = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="status of the DB parameter applied to DB instance",
    )


class DBParameterGroupStatusV2ResponseSchema(Schema):
    DBParameterGroup = fields.Nested(
        DBParameterGroupStatus1V2ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class DBSecurityGroupMembership1V2ResponseSchema(Schema):
    DBSecurityGroupName = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the DB security group",
    )
    Status = fields.String(
        required=False,
        example="",
        allow_none=True,
        description="status of the DB security group",
    )


class DBSecurityGroupMembershipV2ResponseSchema(Schema):
    DBSecurityGroupMembership = fields.Nested(
        DBSecurityGroupMembership1V2ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class DBSubnetGroupV2ResponseSchema(Schema):
    DBSubnetGroupArn = fields.String(required=False, allow_none=True, example="", description="")
    DBSubnetGroupDescription = fields.String(
        required=False, example="", description="description of the DB security group"
    )
    DBSubnetGroupName = fields.String(required=False, example="", description="name of the DB security group")
    SubnetGroupStatus = fields.String(required=False, example="", description="status of the DB security group")
    Subnets = fields.Nested(SubnetV2ResponseSchema, required=False, many=True, allow_none=False)
    VpcId = fields.String(required=False, example="", description="VpcId of the DB subnet group")


class DomainMembership1V2ResponseSchema(Schema):
    Domain = fields.String(
        required=False,
        example="",
        description="identifier of the Active Directory Domain.",
    )
    FQDN = fields.String(required=False, example="", description="")
    IAMRoleName = fields.String(required=False, example="", description="")
    Status = fields.String(
        required=False,
        example="",
        description="status of the DB instance Active Directory Domain membership",
    )


class DomainMembershipsV2ResponseSchema(Schema):
    DomainMembership = fields.Nested(DomainMembership1V2ResponseSchema, many=False, required=False, allow_none=False)


class EndpointV2ResponseSchema(Schema):
    Address = fields.String(
        required=False,
        allow_none=True,
        description="the DNS address of the DB instance",
    )
    # HostedZoneId = fields.String(required=False, example='', description= '')
    Port = fields.Integer(
        required=False,
        allow_none=True,
        description="the port that the database engine is listening on",
    )


class OptionGroupMembership1V2ResponseSchema(Schema):
    OptionGroupName = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the option group that the instance belongs to",
    )
    Status = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="status of the DB instance option group membership",
    )


class OptionGroupMembershipV2ResponseSchema(Schema):
    OptionGroupMembership = fields.Nested(
        OptionGroupMembership1V2ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class DBInstanceStatusInfoV2ResponseSchema(Schema):
    Message = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="Details of the error if there is "
        "an error for the instance. If the instance is not in an error state, this value is blank",
    )
    Normal = fields.Boolean(
        required=False,
        allow_none=True,
        example=True,
        description="Boolean value that is true if "
        "the instance is operating normally, or false if the instance is in an error state.",
    )
    Status = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="Status of the DB instance. For a "
        "StatusType of read replica, the values can be replicating, replication stop point set, "
        "replication stop point reached, error, stopped, or terminated.",
    )
    StatusType = fields.String(
        required=False,
        allow_none=True,
        example="read replication",
        description='This value is currently "read replication"',
    )


class VpcSecurityGroupMembership1V2ResponseSchema(Schema):
    nvl_vpcSecurityGroupName = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-vpcSecurityGroupName",
        example="",
        description="name of the VPC security group",
    )
    VpcSecurityGroupId = fields.String(required=False, example="", description="ID of the VPC security group")
    Status = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="status of the VPC security group",
    )


class VpcSecurityGroupMembershipV2ResponseSchema(Schema):
    VpcSecurityGroupMembership = fields.Nested(
        VpcSecurityGroupMembership1V2ResponseSchema,
        many=False,
        required=False,
        allow_none=True,
    )


class ProcessorFeaturesV2ResponseSchema(Schema):
    Name = fields.String(
        required=False,
        allow_none=True,
        example="coreCount",
        description="The name of the processor " "feature. Valid names are coreCount and threadsPerCore.",
    )
    Value = fields.String(
        required=False,
        allow_none=True,
        example="2",
        description="The value of a processor feature name",
    )


class TagNV2ResponseSchema(Schema):
    Key = fields.String(required=False, allow_none=False, description="tag key")
    Value = fields.String(required=False, allow_none=False, description="tag value")


class MasterUsernameResponseSchema(Schema):
    pwd = fields.String(required=False, allow_none=True, description="master username password")
    name = fields.String(required=False, allow_none=True, description="master username name")


class TagSetV2ResponseSchema(Schema):
    Tag = fields.Nested(TagNV2ResponseSchema, many=False, required=False, allow_none=False)


class DBInstanceParameterV2ResponseSchema(Schema):
    AllocatedStorage = fields.Integer(
        Required=False,
        default=0,
        missing=0,
        example="20",
        description="amount of storage (in GB) to allocate for the DB instance",
    )
    AvailabilityZone = fields.String(required=False, allow_none=True, example="", description="")
    # BackupRetentionPeriod = fields.Integer(required=False, allow_none=True, example='', description='')
    CharacterSetName = fields.String(
        required=False,
        allow_none=True,
        missing="latin1",
        description="For supported engines, "
        "indicates that the DB instance should be  associated with the specified "
        "CharacterSet.",
    )
    DBInstanceClass = fields.String(
        required=False,
        example="db.m4.large",
        description="The compute and memory capacity" " of the DB instance",
    )
    DBInstanceIdentifier = fields.String(required=False, example="", description="The DB instance identifier")
    DbInstancePort = fields.Integer(
        required=False,
        allow_none=True,
        example=3306,
        description="Specifies the port that the DB instance "
        "listens on. If the DB instance is part of a DB cluster, this can be a different "
        "port than the DB cluster port.",
    )
    DBInstanceStatus = fields.String(
        required=False,
        example="available",
        description="Specifies the current state of this database.",
    )
    DbiResourceId = fields.String(
        required=False,
        allow_none=True,
        example="1234",
        description="The Region-unique, immutable identifier for the DB instance. ",
    )
    DBName = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="The name of the database to create when the DB " "instance is created. ",
    )
    # DBParameterGroups = fields.Nested(DBParameterGroupStatusV2ResponseSchema, many=True, required=False,
    #                                   allow_none=True)
    DBSubnetGroup = fields.Nested(DBSubnetGroupV2ResponseSchema, many=False, required=False, allow_none=True)
    Endpoint = fields.Nested(
        EndpointV2ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
        description="Specifies the connection endpoint",
    )
    Engine = fields.String(required=False, allow_none=True, example="", description="name of the DB engine")
    EngineVersion = fields.String(required=False, allow_none=True, example="", description="DB engine version")
    InstanceCreateTime = fields.DateTime(required=False, example="", description="DB instance creation date")
    # Iops: Specifies the Provisioned IOPS (I/O operations per second) value.
    LicenseModel = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="License model information for this DB instance.",
    )
    # ListenerEndpoint = fields.Nested(EndpointV2ResponseSchema, many=False, required=False, allow_none=False,
    #                                description='Specifies the listener connection endpoint for SQL Server Always On')
    # MasterUsername = fields.String(required=False, allow_none=True, example='',
    #                                description='master username for the DB instance')
    # MaxAllocatedStorage: The upper limit to which Amazon RDS can automatically scale the storage of the DB instance.
    MultiAZ = fields.Boolean(
        required=False,
        allow_none=True,
        example=True,
        missing=False,
        description="Specifies if the DB instance is a Multi-AZ deployment",
    )
    # PreferredBackupWindow: Specifies the daily time range during which automated backups are created if automated
    #                        backups are enabled, as determined by the BackupRetentionPeriod.
    # PreferredMaintenanceWindow: Specifies the weekly time range during which system maintenance can occur, in
    #                             Universal Coordinated Time (UTC).
    # ProcessorFeatures = fields.Nested(ProcessorFeaturesV2ResponseSchema, many=True, required=False,
    #                                   allow_none=True, description='The number of CPU cores and the number of  '
    #                                   'threads per core for the DB instance class of the DB instance.')
    # ReadReplicaDBInstanceIdentifiers.ReadReplicaDBInstanceIdentifier.N: Contains one or more identifiers of the
    #   read replicas associated with this DB instance.
    # ReadReplicaSourceDBInstanceIdentifier: Contains the identifier of the source DB instance if this DB instance
    #                                        is a read replica.
    # ReplicaMode: The open mode of an Oracle read replica. The default is open-read-only.
    #   Valid Values: open-read-only | mounted
    # SecondaryAvailabilityZone: If present, specifies the name of the secondary Availability Zone for a DB instance
    #   with multi-AZ support.
    StatusInfos = fields.Nested(
        DBInstanceStatusInfoV2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
        description="The status of a read replica. If the instance is not a read replica, " "this is blank",
    )
    StorageEncrypted = fields.Boolean(
        required=False,
        allow_none=True,
        example=False,
        description="Specifies whether the DB instance is encrypted",
    )
    StorageType = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="Specifies the storage type associated with DB instance",
    )
    TagList = fields.Nested(
        TagSetV2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
        description="A list of tags",
    )
    Timezone = fields.String(
        required=False,
        allow_none=True,
        example="Europe/Rome",
        description="The time zone of the DB instance",
    )
    VpcSecurityGroups = fields.Nested(
        VpcSecurityGroupMembershipV2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )
    nvl_stateReason = fields.Nested(
        StateReasonV2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
        data_key="nvl-stateReason",
    )
    nvl_ownerAlias = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="name of the account that owns the instance",
        data_key="nvl-ownerAlias",
    )
    nvl_ownerId = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="ID of the account that owns the instance",
        data_key="nvl-ownerId",
    )
    # nvl_keyName = fields.String(required=False, example='1ffd', allow_none=True,
    #                             description='The name of the key pair')
    ReadReplicaDBClusterIdentifiers = fields.List(fields.String(), required=False)
    ReadReplicaSourceDBInstanceIdentifier = fields.String(required=False, allow_none=True)
    SecondaryAvailabilityZone = fields.String(required=False, allow_none=True)
    PreferredMaintenanceWindow = fields.String(required=False, allow_none=True)
    # MasterUsername = fields.String(required=False, allow_none=True)
    MasterUsername = fields.Nested(MasterUsernameResponseSchema, required=False, allow_none=True, description="")
    PreferredBackupWindow = fields.String(required=False, allow_none=True)
    ReadReplicaDBInstanceIdentifiers = fields.List(fields.String(), required=False)


class DBResponseMetadataV2ResponseSchema(Schema):
    RequestId = fields.String(required=False, allow_none=True, example="", description="")


class CreateDBInstanceApiV2ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, required=True, many=False, allow_none=False)
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, required=True, many=False, allow_none=False)


class CreateDBInstanceResultApiV2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    CreateDBInstanceResult = fields.Nested(
        CreateDBInstanceApiV2ResponseSchema, required=True, many=False, allow_none=False
    )


class CreateDBInstanceV2ResponseSchema(Schema):
    CreateDBInstanceResponse = fields.Nested(
        CreateDBInstanceResultApiV2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class VpcSecurityGroupId_NV2RequestSchema(Schema):
    VpcSecurityGroupId = fields.List(fields.String(), required=True, description="security group id")


class Tag_NV2RequestSchema(Schema):
    key = fields.String(required=False, allow_none=False, description="tag key")
    value = fields.String(required=False, allow_none=False, description="tag value")


class TagSetV2RequestSchema(Schema):
    Tag = fields.Nested(Tag_NV2RequestSchema, many=False, required=False, allow_none=False)


class NvlOracleOptionsV2RequestSchema(Schema):
    ora_dbname = fields.String(
        required=False,
        description="Oracle database name",
        data_key="Oracle.DBName",
        validate=validate_ora_db_name,
    )
    ora_lsnport = fields.Integer(required=False, description="Oracle listener port", data_key="Oracle.LsnPort")
    ora_archmode = fields.String(required=False, description="Oracle archive mode", data_key="Oracle.ArchMode")
    ora_partopt = fields.String(
        required=False,
        description="Oracle partitioning option",
        data_key="Oracle.PartOption",
    )
    ora_charset = fields.String(
        required=False,
        description="Oracle database character set",
        data_key="Oracle.CharSet",
    )
    ora_natcharset = fields.String(
        required=False,
        description="Oracle database national character set",
        data_key="Oracle.NatCharSet",
    )
    ora_dbfdisksize = fields.Integer(
        required=False,
        description="Oracle database datafiles disk size",
        data_key="Oracle.DbfDiskSize",
    )
    ora_recodisksize = fields.Integer(
        required=False,
        description="Oracle database recovery disk size",
        data_key="Oracle.RecoDiskSize",
    )


class NvlPostgresqlOptionsV2RequestSchema(Schema):
    Postgresql_GeoExtension = fields.String(
        required=False,
        missing=True,
        data_key="Postgresql.GeoExtension",
        description="if True enable installation of postgres extension postgis",
    )


class NvlMysqlOptionsV2RequestSchema(Schema):
    pass


class CreateDBInstancesApiParamV2RequestSchema(Schema):
    AccountId = fields.String(
        required=True,
        example="",
        description="account id or uuid associated to compute zone",
    )
    AllocatedStorage = fields.Integer(
        Required=False,
        example=30,
        missing=30,
        description="amount of storage (in GB) to allocate for the DB instance",
    )
    # BackupRetentionPeriod
    CharacterSetName = fields.String(
        required=False,
        example="",
        missing="latin1",
        description="For supported engines, "
        "indicates that the DB instance should be associated with the specified "
        "CharacterSet.",
    )
    # DBClusterIdentifier: The identifier of the DB cluster that the instance will belong to.
    DBInstanceClass = fields.String(
        required=True,
        example="db.m1.small",
        description="service definition of the DB instance",
    )
    DBInstanceIdentifier = fields.String(required=True, example="", description="The DB instance identifier")
    # DBName = fields.String(required=False, missing='mydbname', example='',
    #                        description='The name of the database to create when the DB instance is created')
    # DBParameterGroupName: The name of the DB parameter group to associate with this DB instance. If you do not
    # specify a value, then the default DB parameter group for the specified DB engine and version is used.
    # DBSecurityGroups.DBSecurityGroupName.N: A list of DB security groups to associate with this DB instance.
    DBSubnetGroupName = fields.String(
        required=True,
        example="",
        description="a DB vpc subnet to associate with DB instance",
    )
    Engine = fields.String(
        required=True,
        example="MySQL",
        description="engine of DB instance",
        validate=OneOf(["mysql", "oracle", "postgresql", "sqlserver"]),
    )
    EngineVersion = fields.String(required=True, example="5.7", description="engine version of DB instance")
    # Iops: The amount of Provisioned IOPS (input/output operations per second) to be initially allocated for the DB
    #       instance. For information about valid Iops values, see Amazon RDS Provisioned IOPS Storage to Improve
    #       Performance in the Amazon RDS User Guide.
    # LicenseModel = fields.String(required=False, example='general-public-license', description='License model '
    #                              'information for this DB instance. Valid values: license-included | '
    #                              'bring-your-own-license | general-public-license')
    # MasterUsername = fields.String(required=False, example='root', missing='root',
    #                                description='The name for the master user')
    MasterUserPassword = fields.String(
        required=False,
        allow_none=True,
        example="",
        description="Password for the master database user",
    )
    # MaxAllocatedStorage: The upper limit to which can automatically scale the storage of the DB instance.
    # MonitoringInterval: The interval, in seconds, between points when Enhanced Monitoring metrics are collected for
    #                     the DB instance. To disable collecting Enhanced Monitoring metrics, specify 0. The default
    #                     is 0.
    MultiAZ = fields.Boolean(
        required=False,
        missing=False,
        description="A value that indicates whether the DB instance" " is a Multi-AZ deployment",
    )
    # OptionGroupName: Indicates that the DB instance should be associated with the specified option group.
    Port = fields.String(
        required=False,
        example="",
        missing=None,
        description="The port number on which the database "
        "accepts connections. MySql: 3306, PostgreSQL: 5432, Oracle: 1522, SQL Server: 1433",
    )
    Tags = fields.Nested(TagSetV2RequestSchema, many=True, required=False, allow_none=True)
    Nvl_KeyName = fields.String(
        required=False,
        example="1ffd",
        allow_none=True,
        description="The name of the key pair",
    )
    Timezone = fields.String(
        required=False,
        example="Europe/Rome",
        missing="Europe/Rome",
        description="characterSet of DB instance",
    )
    VpcSecurityGroupIds = fields.Nested(
        VpcSecurityGroupId_NV2RequestSchema,
        many=False,
        required=False,
        allow_none=False,
        description="a DB security groups to associate with DB " "instance",
    )
    Nvl_Oracle_Options = fields.Nested(
        NvlOracleOptionsV2RequestSchema,
        required=False,
        allow_none=True,
        description="Configure Oracle database options",
    )
    Nvl_Postgresql_Options = fields.Nested(
        NvlPostgresqlOptionsV2RequestSchema,
        required=False,
        allow_none=True,
        description="Configure Postgresql database options",
    )
    Nvl_Mysql_Options = fields.Nested(
        NvlMysqlOptionsV2RequestSchema,
        required=False,
        allow_none=True,
        description="Configure Mysql database options",
    )

    #
    # Oracle parameters
    #
    # OracleDBName = fields.String(Required=False, example='', missing='ORCL0', description='Oracle database instance name')
    # OracleDBArchiveLogMode = fields.String(Required=False, example='', missing='Y', description='Oracle database archivelog mode')
    # OracleDBPartitioningOption = fields.String(Required=False, example='', missing='Y', description='Oracle database partitioning option')
    # OracleDBNationalCharSet = fields.String(Required=False, example='', missin g='AL16UTF16', description='Oracle database national charset')
    # OracleDBDatafilesDiskSize = fields.Integer(Required=False, example='', missing=30,description='Oracle database datafiles disk size in GB')
    # OracleDBRecoveryDiskSize = fields.Integer(Required=False, example='', missing=30, description='Oracle database recovery disk size in GB')

    # # Oracle constant parameters
    # OracleDBDatafilePath = fields.String(Required=False, example='', missing='/oradata', description='Oracle database datafiles path')
    # OracleDBRecoveryBaseFilePath = fields.String(Required=False, example='', missing='/BCK_fisici', description='Oracle database recovery base file path')
    #
    #


class CreateDBInstancesApiV2RequestSchema(Schema):
    dbinstance = fields.Nested(CreateDBInstancesApiParamV2RequestSchema, context="body")


class CreateDBInstancesApiBodyV2RequestSchema(Schema):
    body = fields.Nested(CreateDBInstancesApiV2RequestSchema, context="body")


class CreateDBInstances(ServiceApiView):
    summary = "Create database service"
    description = "Create database service"
    tags = ["databaseservice"]
    definitions = {
        "CreateDBInstancesApiV2RequestSchema": CreateDBInstancesApiV2RequestSchema,
        "CreateDBInstanceV2ResponseSchema": CreateDBInstanceV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDBInstancesApiBodyV2RequestSchema)
    parameters_schema = CreateDBInstancesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CreateDBInstanceV2ResponseSchema}}
    )
    response_schema = CreateDBInstanceV2ResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        inner_data = data.get("dbinstance")

        service_definition_id = inner_data.get("DBInstanceClass")
        account_id = inner_data.get("AccountId")
        name = inner_data.get("DBInstanceIdentifier")
        desc = inner_data.get("DBInstanceIdentifier")
        engine = inner_data.get("Engine")
        engine_version = inner_data.get("EngineVersion")
        # check instance with the same name already exists
        self.service_exist(controller, name, ApiDatabaseServiceInstance.plugintype)

        account, parent_inst = self.check_parent_service(
            controller, account_id, plugintype=ApiDatabaseService.plugintype
        )

        # get service definition with engine configuration
        engine_def_name = "db-engine-%s-%s" % (engine, engine_version)
        engine_defs, tot = controller.get_paginated_service_defs(name=engine_def_name)
        if len(engine_defs) < 1 or len(engine_defs) > 1:
            raise ApiManagerError("Engine %s with version %s saw not found" % (engine, engine_version))

        # add engine config
        engine_def_config = engine_defs[0].get_main_config().params
        data.update({"engine": engine_def_config})

        # check service definition
        service_defs, total = controller.get_paginated_service_defs(
            service_definition_uuid_list=[service_definition_id],
            plugintype=ApiDatabaseServiceInstance.plugintype,
        )
        self.logger.warn(service_defs)
        if total < 1:
            raise ApiManagerError("DBInstanceClass is wrong")

        # create service instance
        data["computeZone"] = parent_inst.instance.resource_uuid
        inst = controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_inst,
            instance_config=data,
        )

        res = {
            "CreateDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "CreateDBInstanceResult": {
                    "DBInstance": {
                        "DBInstanceIdentifier": inst.instance.uuid,
                        "DBInstanceStatus": inst.status,
                        "DbiResourceId": None,
                    },
                    "ResponseMetadata": {"RequestId": operation.id},
                },
            }
        }

        return res, 202


class DBInstanceV2ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=True, allow_none=False)


class DescribeDBInstanceResultV2ResponseSchema(Schema):
    DBInstances = fields.Nested(DBInstanceV2ResponseSchema, many=True, required=False, allow_none=True)
    Marker = fields.Integer(required=False, allow_none=True)
    nvl_DBInstancesTotal = fields.Integer(required=True, default=0, data_key="nvl-DBInstancesTotal")


class DescribeDBInstanceResultResponse1Schema(Schema):
    DescribeDBInstancesResult = fields.Nested(DescribeDBInstanceResultV2ResponseSchema, many=False, required=True)
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class DescribeDBInstancesV2ResponseSchema(Schema):
    DescribeDBInstancesResponse = fields.Nested(
        DescribeDBInstanceResultResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstancesV2RequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
    )
    DBInstanceIdentifier = fields.String(
        required=False,
        context="query",
        description="The user-supplied instance identifier.",
    )
    db_cluster_id = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="db-cluster-id.N",
        description="Accepts DB cluster identifiers and DB cluster Names",
    )
    db_instance_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="db-instance-id.N",
        description="Accepts DB instance identifiers and DB instance Names",
    )
    # dbi_resource_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                                 collection_format='multi', data_key='dbi-resource-id.N',
    #                                 description='Accepts DB instance resource identifiers')
    MaxRecords = fields.Integer(required=False, missing=100, validation=Range(min=20, max=100), context="query")
    Marker = fields.String(required=False, missing="0", default="0", context="query")
    Nvl_tag_key_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="Nvl-tag-key.N",
        descriptiom="value of a tag assigned to the resource",
    )


class DescribeDBInstances(ServiceApiView):
    summary = "Describe database service"
    description = "Describe database service"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDBInstancesV2RequestSchema": DescribeDBInstancesV2RequestSchema,
        "DescribeDBInstancesV2ResponseSchema": DescribeDBInstancesV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstancesV2RequestSchema)
    parameters_schema = DescribeDBInstancesV2RequestSchema
    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeDBInstancesV2ResponseSchema}}
    )
    response_schema = DescribeDBInstancesV2ResponseSchema

    def get(self, controller, data, *args, **kwargs):
        maxRecords = data.get("MaxRecords", 100)
        marker = int(data.get("Marker", 0))

        # check Account
        # accountIdList, zone_list = self.get_account_list(controller, data, ApiDatabaseService)

        # check Account
        account_id_list = data.get("owner_id_N", [])

        # get instance identifier
        instance_id_list = data.get("db_instance_id_N", [])

        # get instance name
        instance_name_list = data.get("DBInstanceIdentifier", None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]

        # # get instance name
        # instance_name_list = None
        # db_instance_identifier = data.get('DBInstanceIdentifier', None)
        # db_instance_id_N = data.get('db_instance_id_N', None)
        # if db_instance_identifier is not None:
        #     instance_name_list = [db_instance_identifier]
        # if db_instance_id_N is not None:
        #     try:
        #         instance_name_list.extend(db_instance_id_N)
        #     except:
        #         instance_name_list = db_instance_id_N

        # get tags
        tag_values = data.get("Nvl_tag_key_N", None)

        # get instances list
        res, total = controller.get_service_type_plugins(
            service_uuid_list=instance_id_list,
            service_name_list=instance_name_list,
            account_id_list=account_id_list,
            servicetags_or=tag_values,
            plugintype=ApiDatabaseServiceInstance.plugintype,
            page=marker,
            size=maxRecords,
        )

        # format result
        instances_set = [{"DBInstance": r.aws_info(api_version="v2.0")} for r in res]

        res = {
            "DescribeDBInstancesResponse": {
                "__xmlns": self.xmlns,
                "DescribeDBInstancesResult": {
                    "Marker": marker,
                    "DBInstances": instances_set,
                    "nvl-DBInstancesTotal": total,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }
        return res


class DeleteDBInstanceV2ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstanceResultV2ResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    DeleteDBInstanceResult = fields.Nested(
        DeleteDBInstanceV2ResponseSchema, many=False, required=False, allow_none=False
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstancesApiV2ResponseSchema(Schema):
    DeleteDBInstanceResponse = fields.Nested(
        DeleteDBInstanceResultV2ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteDBInstancesApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(
        required=True,
        context="query",
        description="The DB instance identifier for " "the DB instance to be deleted",
    )
    FinalDBSnapshotIdentifier = fields.String(
        required=False,
        allow_none=True,
        context="query",
        description="The DBSnapshotIdentifier of the new DBSnapshot created " "when SkipFinalSnapshot is set to false.",
    )
    SkipFinalSnapshot = fields.String(
        required=False,
        allow_none=True,
        context="query",
        description="Determines whether"
        " a final DB snapshot is created before the DB instance is deleted. If true is "
        "specified, no DBSnapshot is created. If false is specified, a DB snapshot is "
        "created before the DB instance is deleted.",
    )


class DeleteDBInstances(ServiceApiView):
    summary = "Delete database service"
    description = "Delete database service"
    tags = ["databaseservice"]
    definitions = {
        "DeleteDBInstancesApiV2RequestSchema": DeleteDBInstancesApiV2RequestSchema,
        "DeleteDBInstancesApiV2ResponseSchema": DeleteDBInstancesApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteDBInstancesApiV2RequestSchema)
    parameters_schema = DeleteDBInstancesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DeleteDBInstancesApiV2ResponseSchema,
            }
        }
    )
    response_schema = DeleteDBInstancesApiV2ResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.pop("DBInstanceIdentifier")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info(api_version="v2.0")
        type_plugin.delete()

        res = {
            "DeleteDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "DeleteDBInstanceResult": {
                    "DBInstance": info,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class ModifyDBInstanceApiV2Result1ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=False, allow_none=True)
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class ModifyDBInstanceApiV2ResultResponseSchema(Schema):
    ModifyDBInstanceResult = fields.Nested(
        ModifyDBInstanceApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class ModifyDBInstanceApiV2ResponseSchema(Schema):
    ModifyDBInstanceResponse = fields.Nested(
        ModifyDBInstanceApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class ModifyDBInstanceApiV2SgRequestSchema(Schema):
    VpcSecurityGroupId = fields.List(
        fields.String(),
        required=True,
        description="security group id followed by :ADD " "to add and :DEL to remove",
    )


class ModifyDBInstanceApiV2ExtensionRequestSchema(Schema):
    Name = fields.String(required=True, description="Extension name")
    Type = fields.String(
        required=True,
        description="Extension type",
        validate=OneOf(["plugin", "component"]),
    )


class ModifyDBInstanceApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    AllocatedStorage = fields.Integer(
        required=False,
        example=100,
        description="The new amount of storage space, in " "gibibytes (GiB), to allocate to the DB instance",
    )
    DBInstanceClass = fields.String(
        required=False,
        allow_none=True,
        description="The new compute and memory capacity " "of the DB instance, for example db.m4.large",
    )
    VpcSecurityGroupIds = fields.Nested(
        ModifyDBInstanceApiV2SgRequestSchema,
        many=False,
        required=False,
        allow_none=False,
        description="Changes the security groups of the DB instance",
    )
    Extensions = fields.Nested(
        ModifyDBInstanceApiV2ExtensionRequestSchema,
        required=False,
        many=True,
        allow_none=True,
        description="Extensions to install on the DB instance",
    )
    # DBSubnetGroupName = fields.String(required=False, example='',
    #                                   description='a DB vpc subnet to associate with DB instance')


class ModifyDBInstanceApiBodyV2RequestSchema(Schema):
    body = fields.Nested(ModifyDBInstanceApiV2RequestSchema, context="body")


class ModifyDBInstance(ServiceApiView):
    summary = "Modify database service"
    description = (
        "Modifies the specified attribute of the specified db instance. You can specify only one attribute "
        "at a time. To modify some attributes, the db instance must be stopped."
    )
    tags = ["databaseservice"]
    definitions = {
        "ModifyDBInstanceApiV2RequestSchema": ModifyDBInstanceApiV2RequestSchema,
        "ModifyDBInstanceApiV2ResponseSchema": ModifyDBInstanceApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ModifyDBInstanceApiBodyV2RequestSchema)
    parameters_schema = ModifyDBInstanceApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ModifyDBInstanceApiV2ResponseSchema}}
    )
    response_schema = ModifyDBInstanceApiV2ResponseSchema

    def put(self, controller, data, *args, **kwargs):
        # check service definition
        service_definition_id = data.get("DBInstanceClass")
        if service_definition_id is not None:
            service_def = controller.get_service_def(service_definition_id)
            service_defs, total = controller.get_paginated_service_defs(
                service_definition_id_list=[service_def.oid],
                plugintype=ApiDatabaseServiceInstance.plugintype,
            )
            self.logger.info("service_defs: %s" % service_defs)
            if total < 1:
                raise ApiManagerError("DBInstanceClass is wrong")

        instance_id = data.pop("DBInstanceIdentifier")
        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info(api_version="v2.0")
        type_plugin.update(**data)

        res = {
            "ModifyDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "ModifyDBInstanceResult": {
                    "DBInstance": info,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class StopDBInstanceApiV2Result1ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=False, allow_none=True)


class StopDBInstanceApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    StopDBInstanceResult = fields.Nested(
        StopDBInstanceApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class StopDBInstanceApiV2ResponseSchema(Schema):
    StopDBInstanceResponse = fields.Nested(
        StopDBInstanceApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class StopDBInstanceApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(
        required=True,
        context="query",
        description="The DB instance identifier for " "the DB instance to stop",
    )
    # StopDBInstanceResponse = fields.String(required=False, allow_none=True, context='query',
    #                                        description='The user-supplied instance identifier of the DB Snapshot '
    #                                                    'created immediately before the DB instance is stopped')


class StopDBInstance(ServiceApiView):
    summary = "Stop a database service"
    description = "Stop a database service"
    tags = ["databaseservice"]
    definitions = {
        "StopDBInstanceApiV2RequestSchema": StopDBInstanceApiV2RequestSchema,
        "StopDBInstanceApiV2ResponseSchema": StopDBInstanceApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(StopDBInstanceApiV2RequestSchema)
    parameters_schema = StopDBInstanceApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": StopDBInstanceApiV2ResponseSchema}}
    )
    response_schema = StopDBInstanceApiV2ResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_id = data.pop("DBInstanceIdentifier")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info(api_version="v2.0")
        type_plugin.stop()

        res = {
            "StopDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "StopDBInstanceResult": {
                    "DBInstance": info,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class StartDBInstanceApiV2Result1ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=False, allow_none=True)


class StartDBInstanceApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    StartDBInstanceResult = fields.Nested(
        StartDBInstanceApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class StartDBInstanceApiV2ResponseSchema(Schema):
    StartDBInstanceResponse = fields.Nested(
        StartDBInstanceApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class StartDBInstanceApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(
        required=True,
        context="query",
        description="The DB instance identifier for " "the DB instance to start",
    )
    # StartDBInstanceResponse = fields.String(required=False, allow_none=True, context='query',
    #                                        description='The user-supplied instance identifier of the DB Snapshot '
    #                                                    'created immediately before the DB instance is Startped')


class StartDBInstance(ServiceApiView):
    summary = "Start a database service"
    description = "Start a database service"
    tags = ["databaseservice"]
    definitions = {
        "StartDBInstanceApiV2RequestSchema": StartDBInstanceApiV2RequestSchema,
        "StartDBInstanceApiV2ResponseSchema": StartDBInstanceApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(StartDBInstanceApiV2RequestSchema)
    parameters_schema = StartDBInstanceApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": StartDBInstanceApiV2ResponseSchema}}
    )
    response_schema = StartDBInstanceApiV2ResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_id = data.pop("DBInstanceIdentifier")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info(api_version="v2.0")
        type_plugin.start()

        res = {
            "StartDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "StartDBInstanceResult": {
                    "DBInstance": info,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class RebootDBInstanceApiV2Result1ResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterV2ResponseSchema, many=False, required=False, allow_none=True)


class RebootDBInstanceApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    RebootDBInstanceResult = fields.Nested(
        RebootDBInstanceApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class RebootDBInstanceApiV2ResponseSchema(Schema):
    RebootDBInstanceResponse = fields.Nested(
        RebootDBInstanceApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class RebootDBInstanceApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(
        required=True,
        context="query",
        description="The DB instance identifier for " "the DB instance to reboot",
    )


class RebootDBInstance(ServiceApiView):
    summary = "Reboot a database service"
    description = "Reboot a database service"
    tags = ["databaseservice"]
    definitions = {
        "RebootDBInstanceApiV2RequestSchema": RebootDBInstanceApiV2RequestSchema,
        "RebootDBInstanceApiV2ResponseSchema": RebootDBInstanceApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(RebootDBInstanceApiV2RequestSchema)
    parameters_schema = RebootDBInstanceApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": RebootDBInstanceApiV2ResponseSchema}}
    )
    response_schema = RebootDBInstanceApiV2ResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_id = data.pop("DBInstanceIdentifier")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info(api_version="v2.0")
        type_plugin.reboot()

        res = {
            "RebootDBInstanceResponse": {
                "__xmlns": self.xmlns,
                "RebootDBInstanceResult": {
                    "DBInstance": info,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class CreateDBInstanceReadReplica(ServiceApiView):
    """
    Create a database instance in Replica
    Create a database instance in Replica
    """

    pass


class PromoteReadReplica(ServiceApiView):
    """
    Backup a database instance in Replica
    Backup a database instance in Replica
    """

    pass


class DescribeDBInstanceSchemaApiV2Result2ResponseSchema(Schema):
    db_name = fields.String(required=True, description="The database or schema name")
    charset = fields.String(required=True, description="The database or schema charset")
    collation = fields.String(required=True, description="The database or schema collation")
    access_privileges = fields.String(
        required=False,
        allow_none=True,
        description="The database or schema access privileges",
    )


class DescribeDBInstanceSchemaApiV2Result1ResponseSchema(Schema):
    Schemas = fields.Nested(
        DescribeDBInstanceSchemaApiV2Result2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )
    SchemasTotal = fields.Int(required=True, description="The database or schema number")


class DescribeDBInstanceSchemaApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    DescribeDBInstanceSchemaResult = fields.Nested(
        DescribeDBInstanceSchemaApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class DescribeDBInstanceSchemaApiV2ResponseSchema(Schema):
    DescribeDBInstanceSchemaResponse = fields.Nested(
        DescribeDBInstanceSchemaApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceSchemaApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, context="query", description="The DB instance identifier")


class DescribeDBInstanceSchemaBodyV2RequestSchema(Schema):
    body = fields.Nested(DescribeDBInstanceSchemaApiV2RequestSchema, context="body")


class DescribeDBInstanceSchema(ServiceApiView):
    summary = "List database or schema"
    description = "List database or schema"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDBInstanceSchemaApiV2RequestSchema": DescribeDBInstanceSchemaApiV2RequestSchema,
        "DescribeDBInstanceSchemaApiV2ResponseSchema": DescribeDBInstanceSchemaApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceSchemaBodyV2RequestSchema)
    parameters_schema = DescribeDBInstanceSchemaApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceSchemaApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeDBInstanceSchemaApiV2ResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        res = type_plugin.get_schemas()

        res = {
            "DescribeDBInstanceSchemaResponse": {
                "__xmlns": self.xmlns,
                "DescribeDBInstanceSchemaResult": {
                    "Schemas": res,
                    "SchemasTotal": len(res),
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 200


class CreateDBInstanceSchemaApiV2Result1ResponseSchema(Schema):
    Name = fields.String(required=True, description="The database or schema name")
    Charset = fields.String(required=True, description="The database or schema charset")


class CreateDBInstanceSchemaApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    CreateDBInstanceSchemaResult = fields.Nested(
        CreateDBInstanceSchemaApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class CreateDBInstanceSchemaApiV2ResponseSchema(Schema):
    CreateDBInstanceSchemaResponse = fields.Nested(
        CreateDBInstanceSchemaApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateDBInstanceSchemaApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    Name = fields.String(required=True, description="The database or schema name")
    Charset = fields.String(required=False, allow_none=True, description="The database or schema charset")


class CreateDBInstanceSchemaBodyV2RequestSchema(Schema):
    body = fields.Nested(CreateDBInstanceSchemaApiV2RequestSchema, context="body")


class CreateDBInstanceSchema(ServiceApiView):
    summary = "Create a database or schema"
    description = "Create a database or schema"
    tags = ["databaseservice"]
    definitions = {
        "CreateDBInstanceSchemaApiV2RequestSchema": CreateDBInstanceSchemaApiV2RequestSchema,
        "CreateDBInstanceSchemaApiV2ResponseSchema": CreateDBInstanceSchemaApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDBInstanceSchemaBodyV2RequestSchema)
    parameters_schema = CreateDBInstanceSchemaApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": CreateDBInstanceSchemaApiV2ResponseSchema,
            }
        }
    )
    response_schema = CreateDBInstanceSchemaApiV2ResponseSchema

    def post(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        name = data.get("Name")
        charset = data.get("Charset")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.create_schema(name, charset)

        res = {
            "CreateDBInstanceSchemaResponse": {
                "__xmlns": self.xmlns,
                "CreateDBInstanceSchemaResult": {"Name": name, "Charset": charset},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class DeleteDBInstanceSchemaApiV2Result1ResponseSchema(Schema):
    Name = fields.String(required=True, description="The database or schema name")


class DeleteDBInstanceSchemaApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    DeleteDBInstanceSchemaResult = fields.Nested(
        DeleteDBInstanceSchemaApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstanceSchemaApiV2ResponseSchema(Schema):
    DeleteDBInstanceSchemaResponse = fields.Nested(
        DeleteDBInstanceSchemaApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteDBInstanceSchemaApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    Name = fields.String(required=True, description="The database or schema name")


class DeleteDBInstanceSchemaBodyV2RequestSchema(Schema):
    body = fields.Nested(DeleteDBInstanceSchemaApiV2RequestSchema, context="body")


class DeleteDBInstanceSchema(ServiceApiView):
    summary = "Delete a database or schema"
    description = "Delete a database or schema"
    tags = ["databaseservice"]
    definitions = {
        "DeleteDBInstanceSchemaApiV2RequestSchema": DeleteDBInstanceSchemaApiV2RequestSchema,
        "DeleteDBInstanceSchemaApiV2ResponseSchema": DeleteDBInstanceSchemaApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteDBInstanceSchemaBodyV2RequestSchema)
    parameters_schema = DeleteDBInstanceSchemaApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DeleteDBInstanceSchemaApiV2ResponseSchema,
            }
        }
    )
    response_schema = DeleteDBInstanceSchemaApiV2ResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        name = data.get("Name")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.remove_schema(name)

        res = {
            "DeleteDBInstanceSchemaResponse": {
                "__xmlns": self.xmlns,
                "DeleteDBInstanceSchemaResult": {"Name": name},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class GrantSchema(Schema):
    db = fields.String(required=False, description="db", example="performance_schema")
    privilege = fields.String(required=False, description="privilege", example="SELECT")


class DescribeDBInstanceUserApiV2Result2ResponseSchema(Schema):
    host = fields.String(required=True, description="The user host")
    user = fields.String(required=True, description="The user name")
    grants = fields.Nested(GrantSchema, many=True, required=False, allow_none=True)
    max_connections = fields.String(required=False, description="max connections")
    plugin = fields.String(required=False, description="plugin")
    account_locked = fields.String(required=False, description="account_locked")


class DescribeDBInstanceUserApiV2Result1ResponseSchema(Schema):
    Users = fields.Nested(
        DescribeDBInstanceUserApiV2Result2ResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )
    UserTotal = fields.Int(required=True, description="The user number")


class DescribeDBInstanceUserApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    DescribeDBInstanceUserResult = fields.Nested(
        DescribeDBInstanceUserApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class DescribeDBInstanceUserApiV2ResponseSchema(Schema):
    DescribeDBInstanceUserResponse = fields.Nested(
        DescribeDBInstanceUserApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceUserApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, context="query", description="The DB instance identifier")


class DescribeDBInstanceUserBodyV2RequestSchema(Schema):
    body = fields.Nested(DescribeDBInstanceUserApiV2RequestSchema, context="body")


class DescribeDBInstanceUser(ServiceApiView):
    summary = "List users"
    description = "List users"
    tags = ["databaseservice"]
    definitions = {
        "DescribeDBInstanceUserApiV2RequestSchema": DescribeDBInstanceUserApiV2RequestSchema,
        "DescribeDBInstanceUserApiV2ResponseSchema": DescribeDBInstanceUserApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceUserBodyV2RequestSchema)
    parameters_schema = DescribeDBInstanceUserApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceUserApiV2ResponseSchema,
            }
        }
    )
    response_schema = DescribeDBInstanceUserApiV2ResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        res = type_plugin.get_users()

        res = {
            "DescribeDBInstanceUserResponse": {
                "__xmlns": self.xmlns,
                "DescribeDBInstanceUserResult": {"Users": res, "UserTotal": len(res)},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 200


class CreateDBInstanceUserApiV2Result1ResponseSchema(Schema):
    Name = fields.String(required=True, description="The user name")


class CreateDBInstanceUserApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    CreateDBInstanceUserResult = fields.Nested(
        CreateDBInstanceUserApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class CreateDBInstanceUserApiV2ResponseSchema(Schema):
    CreateDBInstanceUserResponse = fields.Nested(
        CreateDBInstanceUserApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateDBInstanceUserApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    Name = fields.String(required=True, description="The user name")
    Password = fields.String(required=True, description="The user password")


class CreateDBInstanceUserBodyV2RequestSchema(Schema):
    body = fields.Nested(CreateDBInstanceUserApiV2RequestSchema, context="body")


class CreateDBInstanceUser(ServiceApiView):
    summary = "Create a user"
    description = "Create a user"
    tags = ["databaseservice"]
    definitions = {
        "CreateDBInstanceUserApiV2RequestSchema": CreateDBInstanceUserApiV2RequestSchema,
        "CreateDBInstanceUserApiV2ResponseSchema": CreateDBInstanceUserApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateDBInstanceUserBodyV2RequestSchema)
    parameters_schema = CreateDBInstanceUserApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": CreateDBInstanceUserApiV2ResponseSchema,
            }
        }
    )
    response_schema = CreateDBInstanceUserApiV2ResponseSchema

    def post(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        name = data.get("Name")
        password = data.get("Password")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.create_user(name, password)

        res = {
            "CreateDBInstanceUserResponse": {
                "__xmlns": self.xmlns,
                "CreateDBInstanceUserResult": {"Name": name},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class DeleteDBInstanceUserApiV2Result1ResponseSchema(Schema):
    Name = fields.String(required=True, description="The user name")
    Force = fields.Boolean(required=False, description="Force delete")


class DeleteDBInstanceUserApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    DeleteDBInstanceUserResult = fields.Nested(
        DeleteDBInstanceUserApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstanceUserApiV2ResponseSchema(Schema):
    DeleteDBInstanceUserResponse = fields.Nested(
        DeleteDBInstanceUserApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteDBInstanceUserApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    Name = fields.String(required=True, description="The user name")
    Force = fields.Boolean(required=False, default=False, missing=False, description="Force deletion flag")


class DeleteDBInstanceUserBodyV2RequestSchema(Schema):
    body = fields.Nested(DeleteDBInstanceUserApiV2RequestSchema, context="body")


class DeleteDBInstanceUser(ServiceApiView):
    summary = "Delete a user"
    description = "Delete a user"
    tags = ["databaseservice"]
    definitions = {
        "DeleteDBInstanceUserApiV2RequestSchema": DeleteDBInstanceUserApiV2RequestSchema,
        "DeleteDBInstanceUserApiV2ResponseSchema": DeleteDBInstanceUserApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteDBInstanceUserBodyV2RequestSchema)
    parameters_schema = DeleteDBInstanceUserApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DeleteDBInstanceUserApiV2ResponseSchema,
            }
        }
    )
    response_schema = DeleteDBInstanceUserApiV2ResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        name = data.get("Name")
        force = data.get("Force")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.remove_user(name, force)

        res = {
            "DeleteDBInstanceUserResponse": {
                "__xmlns": self.xmlns,
                "DeleteDBInstanceUserResult": {"Name": name, "Force": force},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class ChangeDBInstanceUserPasswordApiV2Result1ResponseSchema(Schema):
    Name = fields.String(required=True, description="The user name")


class ChangeDBInstanceUserPasswordApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    ChangeDBInstanceUserPasswordResult = fields.Nested(
        ChangeDBInstanceUserPasswordApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class ChangeDBInstanceUserPasswordApiV2ResponseSchema(Schema):
    ChangeDBInstanceUserPasswordResponse = fields.Nested(
        ChangeDBInstanceUserPasswordApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class ChangeDBInstanceUserPasswordApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    Name = fields.String(required=True, description="The user name")
    Password = fields.String(required=True, description="The user password")


class ChangeDBInstanceUserPasswordBodyV2RequestSchema(Schema):
    body = fields.Nested(ChangeDBInstanceUserPasswordApiV2RequestSchema, context="body")


class ChangeDBInstanceUserPassword(ServiceApiView):
    summary = "Change password to user"
    description = "Change password to user"
    tags = ["databaseservice"]
    definitions = {
        "ChangeDBInstanceUserPasswordApiV2RequestSchema": ChangeDBInstanceUserPasswordApiV2RequestSchema,
        "ChangeDBInstanceUserPasswordApiV2ResponseSchema": ChangeDBInstanceUserPasswordApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ChangeDBInstanceUserPasswordBodyV2RequestSchema)
    parameters_schema = ChangeDBInstanceUserPasswordApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": ChangeDBInstanceUserPasswordApiV2ResponseSchema,
            }
        }
    )
    response_schema = ChangeDBInstanceUserPasswordApiV2ResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        name = data.get("Name")
        password = data.get("Password")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.change_pwd(name, password)

        res = {
            "ChangeDBInstanceUserPasswordResponse": {
                "__xmlns": self.xmlns,
                "ChangeDBInstanceUserPasswordResult": {"Name": name},
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class GrantDBInstanceUserPrivilegesApiV2Result1ResponseSchema(Schema):
    DbName = fields.String(required=True, exmaple="testdb", description="The db name")
    UserName = fields.String(required=True, example="testuser", description="The user name")
    Privileges = fields.String(
        required=False,
        example="ALL",
        description="The privileges string like SELECT,INSERT," "DELETE,UPDATE or ALL",
    )


class GrantDBInstanceUserPrivilegesApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    GrantDBInstanceUserPrivilegesResult = fields.Nested(
        GrantDBInstanceUserPrivilegesApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class GrantDBInstanceUserPrivilegesApiV2ResponseSchema(Schema):
    GrantDBInstanceUserPrivilegesResponse = fields.Nested(
        GrantDBInstanceUserPrivilegesApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class GrantDBInstanceUserPrivilegesApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    DbName = fields.String(
        required=True,
        exmaple="testdb",
        description="database name. For postgres use db1 to select "
        "a database db1 and db1.schema1 to select schema schema1 in database db1",
    )
    UserName = fields.String(required=True, example="testuser", description="The user name")
    Privileges = fields.String(
        required=False,
        example="ALL",
        missing="ALL",
        description="Mysql privileges: string like SELECT,INSERT,DELETE,UPDATE or ALL"
        "Postgresql privileges: for database - CONNECT, "
        "                       for schema - CREATE,USAGE,ALL",
    )


class GrantDBInstanceUserPrivilegesBodyV2RequestSchema(Schema):
    body = fields.Nested(GrantDBInstanceUserPrivilegesApiV2RequestSchema, context="body")


class GrantDBInstanceUserPrivileges(ServiceApiView):
    summary = "Grant privileges to user"
    description = "Grant privileges to user"
    tags = ["databaseservice"]
    definitions = {
        "GrantDBInstanceUserPrivilegesApiV2RequestSchema": GrantDBInstanceUserPrivilegesApiV2RequestSchema,
        "GrantDBInstanceUserPrivilegesApiV2ResponseSchema": GrantDBInstanceUserPrivilegesApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GrantDBInstanceUserPrivilegesBodyV2RequestSchema)
    parameters_schema = GrantDBInstanceUserPrivilegesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GrantDBInstanceUserPrivilegesApiV2ResponseSchema,
            }
        }
    )
    response_schema = GrantDBInstanceUserPrivilegesApiV2ResponseSchema

    def post(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        db = data.get("DbName")
        user = data.get("UserName")
        privileges = data.get("Privileges")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.check_priv_string(db, privileges)
        type_plugin.grant_privs(db, user, privileges)

        res = {
            "GrantDBInstanceUserPrivilegesResponse": {
                "__xmlns": self.xmlns,
                "GrantDBInstanceUserPrivilegesResult": {
                    "DbName": db,
                    "UserName": user,
                    "Privileges": privileges,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class RevokeDBInstanceUserPrivilegesApiV2Result1ResponseSchema(Schema):
    DbName = fields.String(required=True, exmaple="testdb", description="The db name")
    UserName = fields.String(required=True, example="testuser", description="The user name")
    Privileges = fields.String(
        required=False,
        example="ALL",
        description="The privileges string like SELECT,INSERT," "DELETE,UPDATE or ALL",
    )


class RevokeDBInstanceUserPrivilegesApiV2ResultResponseSchema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    RevokeDBInstanceUserPrivilegesResult = fields.Nested(
        RevokeDBInstanceUserPrivilegesApiV2Result1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )
    ResponseMetadata = fields.Nested(DBResponseMetadataV2ResponseSchema, many=False, required=False, allow_none=True)


class RevokeDBInstanceUserPrivilegesApiV2ResponseSchema(Schema):
    RevokeDBInstanceUserPrivilegesResponse = fields.Nested(
        RevokeDBInstanceUserPrivilegesApiV2ResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class RevokeDBInstanceUserPrivilegesApiV2RequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, description="The DB instance identifier")
    DbName = fields.String(required=True, exmaple="testdb", description="The db name")
    UserName = fields.String(required=True, example="testuser", description="The user name")
    Privileges = fields.String(
        required=False,
        example="ALL",
        missing="ALL",
        description="The privileges string like SELECT,INSERT,DELETE,UPDATE or ALL",
    )


class RevokeDBInstanceUserPrivilegesBodyV2RequestSchema(Schema):
    body = fields.Nested(RevokeDBInstanceUserPrivilegesApiV2RequestSchema, context="body")


class RevokeDBInstanceUserPrivileges(ServiceApiView):
    summary = "Revoke privileges from user"
    description = "Revoke privileges from user"
    tags = ["databaseservice"]
    definitions = {
        "RevokeDBInstanceUserPrivilegesApiV2RequestSchema": RevokeDBInstanceUserPrivilegesApiV2RequestSchema,
        "RevokeDBInstanceUserPrivilegesApiV2ResponseSchema": RevokeDBInstanceUserPrivilegesApiV2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(RevokeDBInstanceUserPrivilegesBodyV2RequestSchema)
    parameters_schema = RevokeDBInstanceUserPrivilegesApiV2RequestSchema
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": RevokeDBInstanceUserPrivilegesApiV2ResponseSchema,
            }
        }
    )
    response_schema = RevokeDBInstanceUserPrivilegesApiV2ResponseSchema

    def delete(self, controller, data, *args, **kwargs):
        instance_id = data.get("DBInstanceIdentifier")
        db = data.get("DbName")
        user = data.get("UserName")
        privileges = data.get("Privileges")

        type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
        type_plugin.check_priv_string(db, privileges)
        type_plugin.revoke_privs(db, user, privileges)

        res = {
            "RevokeDBInstanceUserPrivilegesResponse": {
                "__xmlns": self.xmlns,
                "RevokeDBInstanceUserPrivilegesResult": {
                    "DbName": db,
                    "UserName": user,
                    "Privileges": privileges,
                },
                "ResponseMetadata": {
                    "RequestId": operation.id,
                },
            }
        }

        return res, 202


class DBInstanceStateResponseSchema(Schema):
    code = fields.Integer(
        required=False,
        allow_none=True,
        example="0",
        description="code of DB instance state",
    )
    name = fields.String(
        required=False,
        example="pending | running | ....",
        description="name of DB instance state",
        validate=OneOf(
            [
                "pending",
                "running",
                "shutting-down",
                "terminated",
                "stopping",
                "stopped",
                "error",
                "unknown",
            ]
        ),
    )


class StateDBInstancesApi2ResponseSchema(Schema):
    currentState = fields.Nested(DBInstanceStateResponseSchema, many=False, required=False)
    instanceId = fields.String(required=False, example="", description="DB instance ID")
    previousState = fields.Nested(DBInstanceStateResponseSchema, many=False, required=False)


class StateDBInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, example="", allow_none=True)
    instancesSet = fields.Nested(StateDBInstancesApi2ResponseSchema, required=True, many=True, allow_none=True)


class MonitorDBInstancesApi3ResponseSchema(Schema):
    state = fields.String(required=True, example="pending", description="monitoring state")


class MonitorDBInstancesApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True, example="", description="DB instance ID")
    monitoring = fields.Nested(MonitorDBInstancesApi3ResponseSchema, required=True, allow_none=True)


class MonitorDBInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, default="", allow_none=True)
    instancesSet = fields.Nested(MonitorDBInstancesApi2ResponseSchema, required=True, allow_none=True)


class MonitorDBInstancesApiResponseSchema(Schema):
    MonitorDBInstancesResponse = fields.Nested(
        StateDBInstancesApi1ResponseSchema, required=True, many=False, allow_none=False
    )


class MonitorDBInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the DB instance owner",
    )
    DBInstanceIdentifier = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="DBInstanceId.N",
        description="DB instance id",
    )
    Nvl_Templates = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        missing=None,
        description="List of monitoring template",
    )


class MonitorDBInstancesBodyRequestSchema(Schema):
    body = fields.Nested(MonitorDBInstancesApiRequestSchema, context="body")


class MonitorDBInstances(ServiceApiView):
    summary = "Enables detailed monitoring for a running db instance. Otherwise, basic monitoring is enabled."
    description = "Enables detailed monitoring for a running db instance. Otherwise, basic monitoring is enabled."
    tags = ["databaseservice"]
    definitions = {
        "MonitorDBInstancesApiRequestSchema": MonitorDBInstancesApiRequestSchema,
        "MonitorDBInstancesApiResponseSchema": MonitorDBInstancesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(MonitorDBInstancesBodyRequestSchema)
    parameters_schema = MonitorDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": MonitorDBInstancesApiResponseSchema}}
    )
    response_schema = MonitorDBInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("DBInstanceIdentifier")
        templates = data.pop("Nvl_Templates")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
            type_plugin.enable_monitoring(templates)
            instances_set.append({"instanceId": instance_id, "monitoring": {"state": "pending"}})

        res = {
            "MonitorDBInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class UnmonitorDBInstancesApiResponseSchema(MonitorDBInstancesApiResponseSchema):
    pass


class UnmonitorDBInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the DB instance owner",
    )
    DBInstanceIdentifier = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="DBInstanceId.N",
        description="DB instance id",
    )


class UnmonitorDBInstancesBodyRequestSchema(Schema):
    body = fields.Nested(UnmonitorDBInstancesApiRequestSchema, context="body")


class UnmonitorDBInstances(ServiceApiView):
    summary = "Disables detailed monitoring for a running db instance."
    description = "Disables detailed monitoring for a running db instance."
    tags = ["databaseservice"]
    definitions = {
        "UnmonitorDBInstancesApiRequestSchema": UnmonitorDBInstancesApiRequestSchema,
        "UnmonitorDBInstancesApiResponseSchema": UnmonitorDBInstancesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(UnmonitorDBInstancesBodyRequestSchema)
    parameters_schema = UnmonitorDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": UnmonitorDBInstancesApiResponseSchema,
            }
        }
    )
    response_schema = UnmonitorDBInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("DBInstanceIdentifier")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
            type_plugin.disable_monitoring()
            instances_set.append({"instanceId": instance_id, "monitoring": {"state": "pending"}})

        res = {
            "UnmonitorDBInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class ForwardLogDBInstancesApi3ResponseSchema(Schema):
    state = fields.String(required=True, example="pending", description="logging state")


class ForwardLogDBInstancesApi2ResponseSchema(Schema):
    instanceId = fields.String(required=True, example="", description="instance ID")
    logging = fields.Nested(ForwardLogDBInstancesApi3ResponseSchema, required=True, allow_none=True)


class ForwardLogDBInstancesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True, default="", allow_none=True)
    instancesSet = fields.Nested(
        ForwardLogDBInstancesApi2ResponseSchema,
        required=True,
        many=True,
        allow_none=True,
    )


class ForwardLogDBInstancesApiResponseSchema(Schema):
    ForwardLogDBInstancesResponse = fields.Nested(
        StateDBInstancesApi1ResponseSchema, required=True, many=False, allow_none=False
    )


class ForwardLogDBInstancesApiRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=False,
        collection_format="multi",
        data_key="owner-id.N",
        description="account ID of the DB instance owner",
    )
    DBInstanceIdentifier = fields.List(
        fields.String(example=""),
        required=True,
        allow_none=True,
        collection_format="multi",
        data_key="DBInstanceId.N",
        description="DB instance id",
    )
    Files = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        missing=None,
        description="List of files to forward",
    )
    Pipeline = fields.String(
        required=False,
        allow_none=True,
        missing=None,
        description="Log collector pipeline port",
    )


class ForwardLogDBInstancesBodyRequestSchema(Schema):
    body = fields.Nested(ForwardLogDBInstancesApiRequestSchema, context="body")


class ForwardLogDBInstances(ServiceApiView):
    summary = "Enables logs forwarding from a running instance to a log collector."
    description = "Enables logs forwarding from a running instance to a log collector."
    tags = ["databaseservice"]
    definitions = {
        "ForwardLogDBInstancesApiRequestSchema": ForwardLogDBInstancesApiRequestSchema,
        "ForwardLogDBInstancesApiResponseSchema": ForwardLogDBInstancesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ForwardLogDBInstancesBodyRequestSchema)
    parameters_schema = ForwardLogDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {
            202: {
                "description": "success",
                "schema": ForwardLogDBInstancesApiResponseSchema,
            }
        }
    )
    response_schema = ForwardLogDBInstancesApiResponseSchema

    def put(self, controller, data, *args, **kwargs):
        instance_ids = data.pop("DBInstanceIdentifier")
        files = data.pop("Files")
        pipeline = data.pop("Pipeline")
        instances_set = []
        for instance_id in instance_ids:
            type_plugin: ApiDatabaseServiceInstance = controller.get_service_type_plugin(instance_id)
            type_plugin.enable_logging(files, pipeline)
            instances_set.append({"instanceId": instance_id, "logging": {"state": "pending"}})

        res = {
            "ForwardLogDBInstancesResponse": {
                "__xmlns": self.xmlns,
                "requestId": operation.id,
                "instancesSet": instances_set,
            }
        }
        return res


class DatabaseInstanceV2API(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/databaseservices/instance"
        rules = [
            ("%s/describedbinstances" % base, "GET", DescribeDBInstances, {}),
            ("%s/createdbinstance" % base, "POST", CreateDBInstances, {}),
            ("%s/modifydbinstance" % base, "PUT", ModifyDBInstance, {}),
            ("%s/stopdbinstance" % base, "PUT", StopDBInstance, {}),
            ("%s/startdbinstance" % base, "PUT", StartDBInstance, {}),
            ("%s/rebootdbinstance" % base, "PUT", RebootDBInstance, {}),
            ("%s/deletedbinstance" % base, "DELETE", DeleteDBInstances, {}),
            # ('%s/createdbinstancemasterreplica' % base, 'POST', CreateDBInstanceMasterReplica, {}),
            # ('%s/createdbinstancereadreplica' % base, 'POST', CreateDBInstanceReadReplica, {}),
            # ('%s/promotereadreplica' % base, 'GET', PromoteReadReplica, {}),
            # ('%s/rebootdbinstance' % base, 'PUT', RebootDBInstance, {}),
            # ('%s/purchasereserveddbinstancesoffering' % base, 'GET', PurchaseReservedDBInstancesOffering, {})
            ("%s/describedbinstancetypes" % base, "GET", DescribeDBInstanceTypes, {}),
            ("%s/enginetypes" % base, "GET", DescribeDBInstanceEngineTypes, {}),
            # schema
            ("%s/describedbinstanceschema" % base, "GET", DescribeDBInstanceSchema, {}),
            ("%s/createdbinstanceschema" % base, "POST", CreateDBInstanceSchema, {}),
            ("%s/deletedbinstanceschema" % base, "DELETE", DeleteDBInstanceSchema, {}),
            # user
            ("%s/describedbinstanceuser" % base, "GET", DescribeDBInstanceUser, {}),
            ("%s/createdbinstanceuser" % base, "POST", CreateDBInstanceUser, {}),
            ("%s/deletedbinstanceuser" % base, "DELETE", DeleteDBInstanceUser, {}),
            (
                "%s/changedbinstanceuserpassword" % base,
                "PUT",
                ChangeDBInstanceUserPassword,
                {},
            ),
            (
                "%s/grantdbinstanceuserprivileges" % base,
                "POST",
                GrantDBInstanceUserPrivileges,
                {},
            ),
            (
                "%s/revokedbinstanceuserprivileges" % base,
                "DELETE",
                RevokeDBInstanceUserPrivileges,
                {},
            ),
            # monitoring
            ("%s/monitordbinstances" % base, "PUT", MonitorDBInstances, {}),
            ("%s/unmonitordbinstances" % base, "PUT", UnmonitorDBInstances, {}),
            # logging
            ("%s/forwardlogdbinstances" % base, "PUT", ForwardLogDBInstances, {}),
            # ('%s/unforwardlogdbinstances' % base, 'PUT', UnforwardLogDBInstances, {}),
        ]

        kwargs["version"] = "v2.0"
        ApiView.register_api(module, rules, **kwargs)
