# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerError, XmlnsSchema
from marshmallow.validate import OneOf, Range
from beehive_service.plugins.databaseservice.controller import (
    ApiDatabaseServiceInstance,
    ApiDatabaseService,
)
from beehive.common.data import operation
from beehive_service.views import ServiceApiView
from beehive_service.controller import ApiAccount, ServiceController
from .check import validate_ora_db_name


class StateReasonResponseSchema(Schema):
    nvl_code = fields.String(
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


class DBResponseMetadataResponseSchema(Schema):
    RequestId = fields.String(required=False, allow_none=True)


class AVZoneResponseSchema(Schema):
    Name = fields.String(required=False, allow_none=True)


class AvailabilityZone(Schema):
    AvailabilityZone = fields.Nested(AVZoneResponseSchema, many=False, allow_none=False)

class SubnetResponseSchema(Schema):
    SubnetAvailabilityZone = fields.Nested(AvailabilityZone, many=False, allow_none=False)
    SubnetIdentifier = fields.String(required=False, metadata={"description": "ID of the subnet"})
    SubnetStatus = fields.String(required=False, metadata={"description": "status of the subnet"})


class DBParameterGroupStatus1ResponseSchema(Schema):
    DBParameterGroupName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the DB parameter group applied to DB instance"},
    )

    ParameterApplyStatus = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "status of the DB parameter applied to DB instance"},
    )


class DBParameterGroupStatusResponseSchema(Schema):
    DBParameterGroup = fields.Nested(
        DBParameterGroupStatus1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class DBSecurityGroupMembership1ResponseSchema(Schema):
    DBSecurityGroupName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the DB security group"},
    )

    Status = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "status of the DB security group"}
    )


class DBSecurityGroupMembershipResponseSchema(Schema):
    DBSecurityGroupMembership = fields.Nested(
        DBSecurityGroupMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class DBSubnetGroupResponseSchema(Schema):
    DBSubnetGroupArn = fields.String(required=False, allow_none=True)

    DBSubnetGroupDescription = fields.String(
        required=False,
        metadata={"description": "description of the DB security group"},
    )

    DBSubnetGroupName = fields.String(required=False, metadata={"description": "name of the DB security group"})
    SubnetGroupStatus = fields.String(required=False, metadata={"description": "status of the DB security group"})
    Subnets = fields.Nested(SubnetResponseSchema, required=False, many=True, allow_none=False)
    VpcId = fields.String(required=False, metadata={"description": "VpcId of the DB subnet group"})


class DomainMembership1ResponseSchema(Schema):
    Domain = fields.String(required=False, metadata={"description": "identifier of the Active Directory Domain."})
    FQDN = fields.String(required=False)
    IAMRoleName = fields.String(required=False)

    Status = fields.String(
        required=False,
        metadata={"description": "status of the DB instance Active Directory Domain membership"},
    )


class DomainMembershipsResponseSchema(Schema):
    DomainMembership = fields.Nested(DomainMembership1ResponseSchema, many=False, required=False, allow_none=False)


class EndpointResponseSchema(Schema):
    Address = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "the DNS address of the DB instance"},
    )

    # HostedZoneId = fields.String(required=False, example='', description= '')
    Port = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "the port that the database engine is listening on"},
    )


class OptionGroupMembership1ResponseSchema(Schema):
    OptionGroupName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the option group that the instance belongs to"},
    )

    Status = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "status of the DB instance option group membership"},
    )


class OptionGroupMembershipResponseSchema(Schema):
    OptionGroupMembership = fields.Nested(
        OptionGroupMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=False,
    )


class PendingModifiedValuesResponseSchema(Schema):
    pass


class DBInstanceStatusInfoResponseSchema(Schema):
    Message = fields.String(required=False, allow_none=True)
    Normal = fields.Boolean(required=False, allow_none=True)
    Status = fields.String(required=False, allow_none=True)
    StatusType = fields.String(required=False, allow_none=True)


class VpcSecurityGroupMembership1ResponseSchema(Schema):
    nvl_vpcSecurityGroupName = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-vpcSecurityGroupName",
        metadata={"description": "name of the VPC security group"},
    )

    VpcSecurityGroupId = fields.String(required=False, metadata={"description": "ID of the VPC security group"})

    Status = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "status of the VPC security group"},
    )


class VpcSecurityGroupMembershipResponseSchema(Schema):
    VpcSecurityGroupMembership = fields.Nested(
        VpcSecurityGroupMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=True,
    )


class DBSecurityGroupsResponseSchema(Schema):
    DBSecurityGroupName = fields.String(
        required=False,
        metadata={"description": "security groups to associate with DB instance"},
    )


class CreateDBInstances2ApiResponseSchema(Schema):
    AllocatedStorage = fields.Integer(
        required=False,
        dump_default=0,
        metadata={"example": 20, "description": "amount of storage (in GB) to allocate for the DB instance"},
    )

    AutoMinorVersionUpgrade = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "indicates that minor version patches are applied automatically"},
    )

    AvailabilityZone = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "availability zone for DB instance"},
    )

    BackupRetentionPeriod = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"example": 1, "description": "number of days for which automatic DB snapshots are retained"},
    )

    CACertificateIdentifier = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "identifier of the CA certificate for this DB instance."},
    )

    CharacterSetName = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": " character set associated to instance"},
    )

    CopyTagsToSnapshot = fields.Boolean(required=False, allow_none=True)

    DBClusterIdentifier = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "name of the DB cluster that the DB instance is a member of."},
    )

    DBInstanceArn = fields.String(required=False, allow_none=True)
    DBInstanceClass = fields.String(required=False, allow_none=True)
    DBInstanceIdentifier = fields.String(required=False, allow_none=True)
    DbInstancePort = fields.Integer(required=False, allow_none=True)
    DBInstanceStatus = fields.String(required=False, allow_none=True)
    # DBIResourceId = fields.String(required=False, allow_none=True, example="", description="")
    DbiResourceId = fields.String(required=False, allow_none=True)
    DBName = fields.String(required=False, allow_none=True)
    DBParameterGroups = fields.Nested(DBParameterGroupStatusResponseSchema, many=True, required=False, allow_none=True)

    DBSecurityGroups = fields.Nested(
        DBSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )

    DBSubnetGroup = fields.Nested(DBSubnetGroupResponseSchema, many=False, required=False, allow_none=True)
    DomainMemberships = fields.Nested(DomainMembershipsResponseSchema, many=True, required=False, allow_none=True)
    Endpoint = fields.Nested(EndpointResponseSchema, many=False, required=False, allow_none=False)

    Engine = fields.String(required=False)
    EngineVersion = fields.String(required=False)
    EnhancedMonitoringResourceArn = fields.String(required=False)
    IAMDatabaseAuthenticationEnabled = fields.Boolean(required=False)
    InstanceCreateTime = fields.DateTime(required=False)
    Iops = fields.Integer(required=False)
    KmsKeyId = fields.String(required=False)
    LatestRestorableTime = fields.DateTime(required=False)
    LicenseModel = fields.String(required=False)
    MasterUsername = fields.String(required=False)
    MonitoringInterval = fields.Integer(required=False)
    MonitoringRoleArn = fields.String(required=False)
    MultiAZ = fields.Boolean(required=False)

    OptionGroupMemberships = fields.Nested(
        OptionGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )

    PendingModifiedValues = fields.Nested(
        PendingModifiedValuesResponseSchema,
        many=False,
        required=False,
        allow_none=True,
    )

    PerformanceInsightsEnabled = fields.Boolean(required=False)
    PerformanceInsightsKMSKeyId = fields.String(required=False)
    PreferredBackupWindow = fields.String(required=False)
    PreferredMaintenanceWindow = fields.String(required=False)
    PromotionTier = fields.Integer(required=False)
    PubliclyAccessible = fields.Boolean(required=False)

    ReadReplicaDBClusterIdentifiers = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        data_key="ReadReplicaDBClusterIdentifiers.ReadReplicaDBClusterIdentifier.N",
        attribute="ReadReplicaDBClusterIdentifiers.ReadReplicaDBClusterIdentifier.N",
        metadata={"description": ""},
    )

    ReadReplicaDBInstanceIdentifiers = fields.List(
        fields.String(example=""),
        required=False,
        many=False,
        allow_none=True,
        data_key="ReadReplicaDBInstanceIdentifiers.ReadReplicaDBInstanceIdentifier.N",
        attribute="ReadReplicaDBInstanceIdentifiers.ReadReplicaDBInstanceIdentifier.N",
        metadata={"description": ""},
    )

    ReadReplicaSourceDBInstanceIdentifier = fields.String(required=False)
    SecondaryAvailabilityZone = fields.String(required=False)
    StatusInfos = fields.Nested(DBInstanceStatusInfoResponseSchema, many=True, required=False, allow_none=True)
    StorageEncrypted = fields.Boolean(required=False)
    StorageType = fields.String(required=False)
    TdeCredentialArn = fields.String(required=False)
    Timezone = fields.String(required=False)

    VpcSecurityGroups = fields.Nested(
        VpcSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )


class CreateDBInstancesApiResponseSchema(Schema):
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, required=True, many=False, allow_none=False)
    DBInstance = fields.Nested(CreateDBInstances2ApiResponseSchema, required=True, many=True, allow_none=False)


class CreateDBInstanceApiResponseSchema(Schema):
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, required=True, many=False, allow_none=False)
    DBInstance = fields.Nested(CreateDBInstances2ApiResponseSchema, required=True, many=False, allow_none=False)


class CreateDBInstanceResultApiResponseSchema(XmlnsSchema):
    CreateDBInstanceResult = fields.Nested(
        CreateDBInstanceApiResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class CreateDBInstanceResponseSchema(XmlnsSchema):
    CreateDBInstanceResponse = fields.Nested(
        CreateDBInstanceResultApiResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class VpcSecurityGroupId_NRequestSchema(Schema):
    VpcSecurityGroupId = fields.List(fields.String(), required=True, metadata={"description": "security group id"})


class Tag_NRequestSchema(Schema):
    key = fields.String(required=False, allow_none=False, metadata={"description": "tag key"})
    value = fields.String(required=False, allow_none=False, metadata={"description": "tag value"})


class TagSetRequestSchema(Schema):
    Tag = fields.Nested(Tag_NRequestSchema, many=False, required=False, allow_none=False)


class CreateDBInstancesApiParamRequestSchema(Schema):
    AccountId = fields.String(required=True, metadata={"description": "account id or uuid associated to compute zone"})
    AllocatedStorage = fields.Integer(
        Required=False,
        dump_default=30,
        load_default=30,
        validate=Range(min=30),
        metadata={"example": 30, "description": "amount of storage (in GB) to allocate for the DB instance"},
    )
    # AvailabilityZone = fields.String(required=False, allow_none=True, example='',
    #                                  description='availability zone of DB instance')
    # BackupRetentionPeriod = fields.Integer(required=False, default=1, example='1',
    #                                        description='number of days to retain backup')
    # CharacterSetName = fields.String(required=False, example='', description='characterSet of DB instance')

    # DBClusterIdentifier = fields.String(required=False, example='', description='identifier of the DB cluster ')

    DBInstanceClass = fields.String(

        required=True,

        metadata={"example": "db.m1.small", "description": "service definition of the DB instance"},

    )
    DBInstanceIdentifier = fields.String(required=True, metadata={"description": "ID DB instance account"})

    DBName = fields.String(
        required=False,
        load_default="mydbname",
        validate=validate_ora_db_name,
        metadata={"description": "name of instance database to create"},
    )

    # ??
    VpcSecurityGroupIds = fields.Nested(VpcSecurityGroupId_NRequestSchema, many=False, required=False, allow_none=False)
    DBSubnetGroupName = fields.String(
        required=True,
        metadata={"description": "a DB security groups to associate with DB instance"},
    )

    # EnableCloudwatchLogsExports_member_N = fields.List(fields.String(example='transaction.log'),
    # required=False, many=False, allow_none=True)
    # engine possibile value ['MySQL' | 'MariaDB' | 'PostgresSQL' | 'Oracle' | 'SQL Server']
    Engine = fields.String(
        required=True,
        validate=OneOf(["mysql", "oracle", "postgresql", "sqlserver", "mariadb"]),
        metadata={"example": "mysql", "description": "engine of DB instance"},
    )
    EngineVersion = fields.String(
        required=True,
        metadata={"example": "5.7", "description": "engine version of DB instance"},
    )

    # Iops_member_N =
    # Iops = fields.Integer(Required=False, example='1000', description='amount of Provisioned IOPS
    # (input/output operations per second) to be initially allocated for the DB instance.')
    # KmsKeyId = fields.String(required=False, example='', description= 'AWS KMS key identifier for an
    # encrypted DB instance')

    # LicenseModel = fields.String(required=False, example='general-public-license',
    #                              description='type of license for database engine',
    #                              validate=OneOf(['license-included', 'bring-your-own-license',
    #                                              'general-public-license']))
    # MasterUsername = fields.String(required=False,  allow_none=True,  example='',
    #                                description='name for the master database user')
    MasterUserPassword = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "password for the master database user"},
    )
    #
    # MonitoringInterval = fields.Integer(Required=False, default=0, example='20', description='interval in seconds
    # for Enhanced Monitoring metrics are collected for the DB instance')
    # MonitoringRoleArn = fields.String(Required=False,example='', description='')
    # TdeCredentialArn = fields.String(required=False,  example='', description='ARN for TDE encryption to associate
    # with DB instance')
    # TdeCredentialPassword = fields.String(required=False,  example='', description='password for the given ARN')

    MultiAZ = fields.Boolean(
        required=False,
        allow_none=True,
        load_default=False,
        metadata={"example": True, "description": "Specifies if the DB instance is a Multi-AZ deployment"},
    )

    # Port = fields.Integer(required=False,  example='', description='port number for database connection',
    #                       validate=OneOf([3306, 1521, 5432, 1433]))
    # PreferredBackupWindow = fields.String(required=False, example='04:00-04:30',
    #                                       description='daily time range during which automated backups are created if '
    #                                                   'automated backups are enabled')
    # PreferredMaintenanceWindow = fields.String(required=False, example='wed:06:38-wed:07:08',
    #                                            description='time range each week during which system maintenance '
    #                                                        'can occur')
    # PubliclyAccessible = fields.Boolean(required=False, default=False,
    #                                     description='internet accessibility options for the DB instance '
    #                                                 '(True=instance with a public ip address)')
    # StorageEncrypted = fields.Boolean(required=False, default=False,
    #                                   description='specifies whether the DB instance is encrypted')
    # StorageType = fields.String(required=False,  example='standard | io1 (with Iops)', description='')
    Tag_N = fields.Nested(TagSetRequestSchema, many=True, required=False, allow_none=True)
    # SchemaName = fields.String(required=False,  example='', description='schema name to use for a db instance
    # postgresql')
    # ExtensionName_N = fields.List (fields.String(example=''), required=False, description='extension to install
    # for a db instance postgresql')
    Nvl_KeyName = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "1ffd", "description": "The name of the key pair"},
    )


class CreateDBInstancesApiRequestSchema(Schema):
    dbinstance = fields.Nested(CreateDBInstancesApiParamRequestSchema, context="body")


class CreateDBInstancesApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateDBInstancesApiRequestSchema, context="body")


class CreateDBInstances(ServiceApiView):
    summary = "Create database service"
    description = "Create database service"
    tags = ["databaseservice"]

    definitions = {
        "CreateDBInstancesApiRequestSchema": CreateDBInstancesApiRequestSchema,
        "CreateDBInstanceResponseSchema": CreateDBInstanceResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(CreateDBInstancesApiBodyRequestSchema)
    parameters_schema = CreateDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses({202: {"description": "success", "schema": CreateDBInstanceResponseSchema}})
    response_schema = CreateDBInstanceResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        inner_data = data.get("dbinstance")

        service_definition_id = inner_data.get("DBInstanceClass")
        account_id = inner_data.get("AccountId")
        name = inner_data.get("DBInstanceIdentifier")
        desc = inner_data.get("DBInstanceIdentifier")
        engine = inner_data.get("Engine")
        engine_version = inner_data.get("EngineVersion")
        # check instance with the same name already exists
        self.service_exist(controller, name, ApiDatabaseService.plugintype)

        account, parent_inst = self.check_parent_service(
            controller, account_id, plugintype=ApiDatabaseService.plugintype
        )

        # get service definition with engine configuration
        engine_def_name = "db-engine-%s-%s" % (engine, engine_version)
        engine_defs, tot = controller.get_paginated_service_defs(name=engine_def_name)
        if len(engine_defs) < 1 or len(engine_defs) > 1:
            raise ApiManagerError("Engine %s with version %s was not found" % (engine, engine_version))

        # add engine config
        engine_def_config = engine_defs[0].get_main_config().params
        data.update({"engine": engine_def_config})

        self.logger.warn(data)

        data["computeZone"] = parent_inst.instance.resource_uuid
        inst = controller.add_service_type_plugin(
            service_definition_id,  # flavor db.xx.yyyy
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


class DBInstanceParameterResponseSchema(Schema):
    AllocatedStorage = fields.Integer(
        Required=False,
        dump_default=0,
        load_default=0,
        metadata={"example": "20", "description": "amount of storage (in GB) to allocate for the DB instance"},
    )

    AutoMinorVersionUpgrade = fields.Boolean(
        Required=False,
        allow_none=True,
        metadata={"description": "indicates that minor version patches are " "applied automatically"},
    )

    AvailabilityZone = fields.String(required=False, allow_none=True)
    BackupRetentionPeriod = fields.Integer(required=False, allow_none=True)
    CACertificateIdentifier = fields.String(required=False, allow_none=True)
    CharacterSetName = fields.String(required=False, allow_none=True)
    # Not supported
    CopyTagsToSnapshot = fields.Boolean(required=False, allow_none=True)
    DomainMemberships = fields.Nested(DomainMembershipsResponseSchema, many=True, required=False, allow_none=True)
    DBParameterGroups = fields.Nested(DBParameterGroupStatusResponseSchema, many=True, required=False, allow_none=True)
    IAMDatabaseAuthenticationEnabled = fields.Boolean(required=False, allow_none=True)
    PerformanceInsightsKMSKeyId = fields.String(required=False, allow_none=True)

    OptionGroupMemberships = fields.Nested(
        OptionGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )

    PerformanceInsightsEnabled = fields.Boolean(required=False, allow_none=True)
    PromotionTier = fields.Integer(required=False, allow_none=True)
    Timezone = fields.String(required=False, allow_none=True)

    #    Deprecated
    DBSecurityGroups = fields.Nested(
        DBSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )

    #    We don't known parameter
    DBClusterIdentifier = fields.String(required=False, allow_none=True)
    MonitoringInterval = fields.Integer(required=False, allow_none=True)
    MonitoringRoleArn = fields.String(required=False, allow_none=True)
    TdeCredentialArn = fields.String(required=False, allow_none=True)
    TdeCredentialPassword = fields.String(required=False, allow_none=True)
    Iops = fields.Integer(required=False, allow_none=True)
    KmsKeyId = fields.String(required=False)

    EnabledCloudwatchLogsExports_member_N = fields.List(
        fields.String(example=""),
        required=False,
        data_key="EnabledCloudwatchLogsExports.member.N",
        metadata={"description": ""},
    )

    DBInstanceArn = fields.String(required=False, allow_none=True)
    EnhancedMonitoringResourceArn = fields.String(required=False)
    #
    DBInstanceClass = fields.String(required=False)
    DBInstanceIdentifier = fields.String(required=False)

    DbInstancePort = fields.Integer(
        required=False,
        allow_none=True,
        metadata={
            "example": 3306,
            "description": (
                "Specifies the port that the DB instance listens on. "
                "If the DB instance is part of a DB cluster, this can be a different port than the DB cluster port."
            )
        },
    )

    DBInstanceStatus = fields.String(required=False, allow_none=True)
    DbiResourceId = fields.String(required=False)
    DBName = fields.String(required=False, allow_none=True, metadata={"description": "name of the database instance"})

    DBSubnetGroup = fields.Nested(DBSubnetGroupResponseSchema, many=False, required=False, allow_none=True)
    Endpoint = fields.Nested(EndpointResponseSchema, many=False, required=False, allow_none=False)
    Engine = fields.String(required=False, allow_none=True, metadata={"description": "name of the DB engine"})
    EngineVersion = fields.String(required=False, allow_none=True, metadata={"description": "DB engine version"})
    InstanceCreateTime = fields.DateTime(required=False, metadata={"description": "DB instance creation date"})

    LatestRestorableTime = fields.DateTime(
        required=False,
        metadata={"description": "DB instance last modification date"},
    )

    LicenseModel = fields.String(required=False, allow_none=True)

    MasterUsername = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "master username for the DB instance"},
    )

    MultiAZ = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={"description": "Specifies if the DB instance is a Multi-AZ deployment"},
    )

    PendingModifiedValues = fields.Nested(
        PendingModifiedValuesResponseSchema,
        many=False,
        required=False,
        allow_none=True,
    )

    PreferredBackupWindow = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "the daily time range during which automated backups are created"},
    )

    PreferredMaintenanceWindow = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "the weekly time range during which system maintenance can occur"},
    )

    PubliclyAccessible = fields.Boolean(required=False, allow_none=True)
    ReadReplicaDBClusterIdentifiers = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        # data_key="ReadReplicaDBClusterIdentifiers." "ReadReplicaDBClusterIdentifier.N",
        # attribute="ReadReplicaDBClusterIdentifiers." "ReadReplicaDBClusterIdentifier.N",
        # description="",
    )

    ReadReplicaDBInstanceIdentifiers = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        # data_key="ReadReplicaDBInstanceIdentifiers." "ReadReplicaDBInstanceIdentifier.N",
        # attribute="ReadReplicaDBInstanceIdentifiers." "ReadReplicaDBInstanceIdentifier.N",
        # description="",
    )

    ReadReplicaSourceDBInstanceIdentifier = fields.String(required=False, allow_none=True)
    SecondaryAvailabilityZone = fields.String(required=False, allow_none=True)
    StatusInfos = fields.Nested(DBInstanceStatusInfoResponseSchema, many=True, required=False, allow_none=True)
    StorageEncrypted = fields.Boolean(required=False, allow_none=True)
    StorageType = fields.String(required=False, allow_none=True)

    VpcSecurityGroups = fields.Nested(
        VpcSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True,
    )

    nvl_stateReason = fields.Nested(
        StateReasonResponseSchema,
        many=False,
        required=False,
        allow_none=True,
        data_key="nvl-stateReason",
    )

    nvl_name = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-name",
        metadata={"description": "name of the instance"},
    )

    nvl_ownerAlias = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-ownerAlias",
        metadata={"description": "name of the account that owns the instance"},
    )

    nvl_ownerId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-ownerId",
        metadata={"description": "ID of the account that owns the instance"},
    )

    nvl_resourceId = fields.String(
        required=False,
        allow_none=True,
        data_key="nvl-resourceId",
        metadata={"description": "ID of the instance resource"},
    )

    nvl_hypervisor = fields.String(required=False, allow_none=True, data_key="nvl-hypervisor")
    monitoring_enabled = fields.Boolean(required=False, allow_none=True)
    TagList = fields.List(fields.String(example=""), required=False, allow_none=True)


class DBInstanceResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterResponseSchema, many=False, required=True, allow_none=False)


class DescribeDBInstanceResultResponseSchema(Schema):
    DBInstances = fields.Nested(DBInstanceResponseSchema, many=True, required=False, allow_none=True)
    Marker = fields.Integer(required=False, allow_none=True)
    nvl_DBInstancesTotal = fields.Integer(required=True, dump_default=0, data_key="nvl-DBInstancesTotal")


class DescribeDBInstanceResultResponse1Schema(Schema):
    DescribeDBInstancesResult = fields.Nested(DescribeDBInstanceResultResponseSchema, many=False, required=True)
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, many=False, required=False, allow_none=True)
    xmlns = fields.String(required=False, data_key="__xmlns")


class DescribeDBInstancesResponseSchema(Schema):
    DescribeDBInstancesResponse = fields.Nested(
        DescribeDBInstanceResultResponse1Schema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstancesRequestSchema(Schema):
    owner_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="owner-id.N",
    )

    DBInstanceIdentifier = fields.String(required=False, context="query")

    db_instance_id_N = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="db-instance-id.N",
    )

    MaxRecords = fields.Integer(required=False, load_default=100, validation=Range(min=20, max=100), context="query")
    Marker = fields.String(required=False, load_default="0", dump_default="0", context="query")

    Nvl_tag_key_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="Nvl-tag-key.N",
        metadata={"description": "value of a tag assigned to the resource"},
    )


class DescribeDBInstances(ServiceApiView):
    summary = "Describe database service"
    description = "Describe database service"
    tags = ["databaseservice"]

    definitions = {
        "DescribeDBInstancesRequestSchema": DescribeDBInstancesRequestSchema,
        "DescribeDBInstancesResponseSchema": DescribeDBInstancesResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeDBInstancesRequestSchema)
    parameters_schema = DescribeDBInstancesRequestSchema

    responses = ServiceApiView.setResponses(
        {200: {"description": "success", "schema": DescribeDBInstancesResponseSchema}}
    )

    response_schema = DescribeDBInstancesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
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
        instances_set = [{"DBInstance": r.aws_info()} for r in res]

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


class DeleteDBInstanceResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstanceResultResponseSchema(XmlnsSchema):
    DeleteDBInstanceResult = fields.Nested(DeleteDBInstanceResponseSchema, many=False, required=False, allow_none=False)
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstancesApiResponseSchema(Schema):
    DeleteDBInstanceResponse = fields.Nested(
        DeleteDBInstanceResultResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DeleteDBInstancesApiRequestSchema(Schema):
    DBInstanceIdentifier = fields.String(
        required=True,
        context="query",
        metadata={"description": "The DB instance identifier for the DB instance to be deleted"},
    )

    FinalDBSnapshotIdentifier = fields.String(
        required=False,
        allow_none=True,
        context="query",
        metadata={
            "description": (
                "The DBSnapshotIdentifier of the new DBSnapshot created "
                "when SkipFinalSnapshot is set to false."
            )
        },
    )

    SkipFinalSnapshot = fields.String(
        required=False,
        allow_none=True,
        context="query",
        metadata={
            "description": (
                "Determines whether a final DB snapshot is created before the DB "
                "instance is deleted. If true is specified, no DBSnapshot is "
                "created. If false is specified, a DB snapshot is created before "
                "the DB instance is deleted."
            )
        },
    )


class DeleteDBInstances(ServiceApiView):
    summary = "Delete database service"
    description = "Delete database service"
    tags = ["databaseservice"]

    definitions = {
        "DeleteDBInstancesApiRequestSchema": DeleteDBInstancesApiRequestSchema,
        "DeleteDBInstancesApiResponseSchema": DeleteDBInstancesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DeleteDBInstancesApiRequestSchema)
    parameters_schema = DeleteDBInstancesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": DeleteDBInstancesApiResponseSchema}}
    )

    response_schema = DeleteDBInstancesApiResponseSchema

    def delete(self, controller: ServiceController, data, *args, **kwargs):
        instance_id = data.pop("DBInstanceIdentifier")

        type_plugin = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info()
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


class StopDBInstances(ServiceApiView):
    """
    Stop a database instance
    """
    pass


class StartDBInstances(ServiceApiView):
    """
    Start a database instance
    """
    pass


class CreateDBInstanceReadReplica(ServiceApiView):
    """
    Create a database instance in Replica
    """
    pass


class PromoteReadReplica(ServiceApiView):
    """
    Backup a database instance in Replica
    """
    pass


class RebootDBInstance(ServiceApiView):
    """
    Reboot a database instance
    """
    pass


class PurchaseReservedDBInstancesOffering(ServiceApiView):
    """
    Purchase a database instance
    """
    pass


class InstanceTypeFeatureResponseSchema(Schema):
    vcpus = fields.String(required=False, allow_none=True)
    ram = fields.String(required=False, allow_none=True)
    disk = fields.String(required=False, allow_none=True)


class InstanceTypeResponseSchema(Schema):
    id = fields.Integer(required=True)
    uuid = fields.String(required=True)
    name = fields.String(required=True)
    resource_id = fields.String(required=False, allow_none=True)
    description = fields.String(required=True, allow_none=True)
    features = fields.Nested(InstanceTypeFeatureResponseSchema, required=True, many=False, allow_none=False)


class DescribeDBInstanceTypesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    instanceTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    instanceTypesTotal = fields.Integer(required=True)


class DescribeDBInstanceTypesApiResponseSchema(Schema):
    DescribeDBInstanceTypesResponse = fields.Nested(
        DescribeDBInstanceTypesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceTypesApiRequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False,
        dump_default=10,
        context="query",
        metadata={"description": "entities list page size"},
    )

    NextToken = fields.String(
        required=False,
        dump_default="0",
        context="query",
        metadata={"description": "entities list page selected"},
    )

    ownerId = fields.String(
        required=False,
        allow_none=True,
        context="query",
        metadata={"description": "ID of the account that owns the customization"},
    )

    instance_type_N = fields.List(
        fields.String(example=""),
        required=False,
        allow_none=True,
        context="query",
        collection_format="multi",
        data_key="instance-type.N",
        metadata={"description": "list of instance type uuid"},
    )


class DescribeDBInstanceTypes(ServiceApiView):
    summary = "List of active instance types"
    description = "List of active instance types"
    tags = ["databaseservice"]

    definitions = {
        "DescribeDBInstanceTypesApiRequestSchema": DescribeDBInstanceTypesApiRequestSchema,
        "DescribeDBInstanceTypesApiResponseSchema": DescribeDBInstanceTypesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceTypesApiRequestSchema)
    parameters_schema = DescribeDBInstanceTypesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceTypesApiResponseSchema,
            }
        }
    )

    response_schema = DescribeDBInstanceTypesApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        instance_types_set, total = controller.get_catalog_service_definitions(
            size=data.pop("MaxResults", 10),
            page=int(data.pop("NextToken", 0)),
            plugintype="DatabaseInstance",
            def_uuids=data.pop("instance_type_N", []),
        )

        res = {
            "DescribeDBInstanceTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "instanceTypesSet": instance_types_set,
                "instanceTypesTotal": total,
            }
        }
        return res


# deprecates use v2 instead
# class DescribeAccountDBInstanceTypes(ServiceApiView):
#     summary = 'List of active instance types'
#     description = 'List of active instance types'
#     tags = ['databaseservice']
#     definitions = {
#         'DescribeDBInstanceTypesApiRequestSchema': DescribeDBInstanceTypesApiRequestSchema,
#         'DescribeDBInstanceTypesApiResponseSchema': DescribeDBInstanceTypesApiResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(DescribeDBInstanceTypesApiRequestSchema)
#     parameters_schema = DescribeDBInstanceTypesApiRequestSchema
#     responses = SwaggerApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': DescribeDBInstanceTypesApiResponseSchema
#         }
#     })

#     def get(self, controller: ServiceController, data:dict, oid:str, *args, **kwargs):
#         account: ApiAccount = controller.get_account(oid)
#         account.verify_permisssions('view')
#         instance_types_set, total = controller.get_account_catalog(
#             size=data.pop('MaxResults', 10),
#             page=int(data.pop('NextToken', 0)),
#             plugintype='DatabaseInstance',
#             account_id= account.oid,
#             def_uuids=data.pop('instance_type_N', [])
#             )

#         res = {
#             'DescribeDBInstanceTypesResponse': {
#                 '$xmlns': self.xmlns,
#                 'requestId': operation.id,
#                 'instanceTypesSet': instance_types_set,
#                 'instanceTypesTotal': total
#             }
#         }
#         return res


class DescribeDBInstanceEngineTypesApiRequestSchema(Schema):
    pass


class DescribeDBInstanceEngineTypesParamsApiResponseSchema(Schema):
    engine = fields.String(required=True, metadata={"example": "postgresql", "description": "Database engine type"})
    engineVersion = fields.String(required=True, metadata={"description": "Database engine version"})


class DescribeDBInstanceEngineTypesApi1ResponseSchema(Schema):
    engineTypesSet = fields.Nested(
        DescribeDBInstanceEngineTypesParamsApiResponseSchema,
        many=True,
        allow_none=False,
        metadata={"description": ""},
    )

    engineTypesTotal = fields.Integer(required=True)


class DescribeDBInstanceEngineTypesApiResponseSchema(Schema):
    DescribeDBInstanceEngineTypesResponse = fields.Nested(
        DescribeDBInstanceEngineTypesApi1ResponseSchema,
        required=True,
        many=False,
        allow_none=False,
    )


class DescribeDBInstanceEngineTypes(ServiceApiView):
    summary = "List of db instance engine types"
    description = "List of db instance engine types"
    tags = ["databaseservice"]

    definitions = {
        "DescribeDBInstanceEngineTypesApiRequestSchema": DescribeDBInstanceEngineTypesApiRequestSchema,
        "DescribeDBInstanceEngineTypesApiResponseSchema": DescribeDBInstanceEngineTypesApiResponseSchema,
    }

    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceEngineTypesApiRequestSchema)
    parameters_schema = DescribeDBInstanceEngineTypesApiRequestSchema

    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": DescribeDBInstanceEngineTypesApiResponseSchema,
            }
        }
    )

    response_schema = DescribeDBInstanceEngineTypesApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        # raise ApiManagerError("Deprecation Error please use non deprecated v2 ",410)
        instance_engines_set, total = controller.get_catalog_service_definitions(plugintype="VirtualService", size=-1)
        self.logger.warn(instance_engines_set)

        engine_types_set, total = [], 0
        for e in instance_engines_set:
            name = e.get("name")
            if name.find("db-engine") != 0:
                continue
            esplit = name.split("-")
            item = {}
            item["engine"] = esplit[2]
            item["engineVersion"] = esplit[3]
            engine_types_set.append(item)
            total += 1

        res = {
            "DescribeDBInstanceEngineTypesResponse": {
                "$xmlns": self.xmlns,
                "requestId": operation.id,
                "engineTypesSet": engine_types_set,
                "engineTypesTotal": total,
            }
        }

        self.logger.warning("res=%s" % res)
        return res


class DatabaseInstanceAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = module.base_path + "/databaseservices/instance"
        rules = [
            ("%s/describedbinstances" % base, "GET", DescribeDBInstances, {}),
            ("%s/createdbinstance" % base, "POST", CreateDBInstances, {}),
            # ('%s/stopdbinstance' % base, 'PUT', StopDBInstances, {}),
            # ('%s/startdbinstance' % base, 'PUT', StartDBInstances, {}),
            ("%s/deletedbinstance" % base, "DELETE", DeleteDBInstances, {}),
            # ('%s/createdbinstancereadreplica' % base, 'POST', CreateDBInstanceReadReplica, {}),
            # ('%s/promotereadreplica' % base, 'GET', PromoteReadReplica, {}),
            # ('%s/rebootdbinstance' % base, 'PUT', RebootDBInstance, {}),
            # ('%s/purchasereserveddbinstancesoffering' % base, 'GET', PurchaseReservedDBInstancesOffering, {})
            ("%s/describedbinstancetypes" % base, "GET", DescribeDBInstanceTypes, {}),
            # (f'{module.base_path}/accounts/<oid>/databaseservices/describedbinstancetypes', 'GET', DescribeAccountDBInstanceTypes, {}),
            ("%s/enginetypes" % base, "GET", DescribeDBInstanceEngineTypes, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
