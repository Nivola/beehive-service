# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerError
from marshmallow.validate import OneOf, Range
from beehive_service.plugins.databaseservice.controller import ApiDatabaseServiceInstance, ApiDatabaseService
from beehive.common.data import operation
from beehive_service.views import ServiceApiView
from beehive_service.controller import ApiAccount, ServiceController

class StateReasonResponseSchema(Schema):
    nvl_code = fields.String(required=False, allow_none=True, example='', description='state code', data_key='nvl-code')
    nvl_message = fields.String(required=False, allow_none=True, example='', description='state message',
                                data_key='nvl-message')


class DBResponseMetadataResponseSchema(Schema):
    RequestId = fields.String(required=False, allow_none=True, example='', description='')


class AVZoneResponseSchema (Schema):
    Name = fields.String(required=False, allow_none=True, example='', description='')


class SubnetResponseSchema(Schema):
    SubnetAvailabilityZone = fields.Nested(AVZoneResponseSchema, many=False, allow_none=False, example='',
                                           description='')
    SubnetIdentifier = fields.String(required=False, example='', description='ID of the subnet')
    SubnetStatus = fields.String(required=False, example='', description='status of the subnet')


class DBParameterGroupStatus1ResponseSchema(Schema):
    DBParameterGroupName = fields.String(required=False, allow_none=True, example='',
                                         description='name of the DB parameter group applied to DB instance')
    ParameterApplyStatus = fields.String(required=False, allow_none=True, example='',
                                         description='status of the DB parameter applied to DB instance')


class DBParameterGroupStatusResponseSchema(Schema):
    DBParameterGroup = fields.Nested(DBParameterGroupStatus1ResponseSchema, many=False, required=False,
                                     allow_none=False)


class DBSecurityGroupMembership1ResponseSchema(Schema):
    DBSecurityGroupName = fields.String(required=False, allow_none=True, example='',
                                        description='name of the DB security group')
    Status = fields.String( required=False, example='', allow_none=True, description='status of the DB security group')


class DBSecurityGroupMembershipResponseSchema(Schema):
    DBSecurityGroupMembership = fields.Nested(DBSecurityGroupMembership1ResponseSchema, many=False, required=False,
                                              allow_none=False)


class DBSubnetGroupResponseSchema(Schema):
    DBSubnetGroupArn = fields.String(required=False, allow_none=True, example='', description='')
    DBSubnetGroupDescription = fields.String( required=False, example='',
                                              description='description of the DB security group')
    DBSubnetGroupName = fields.String(required=False, example='', description='name of the DB security group')
    SubnetGroupStatus = fields.String(required=False, example='', description='status of the DB security group')
    Subnets = fields.Nested(SubnetResponseSchema, required=False, many=True, allow_none=False )
    VpcId = fields.String(required=False, example='', description='VpcId of the DB subnet group')


class DomainMembership1ResponseSchema(Schema):
    Domain = fields.String(required=False, example='', description='identifier of the Active Directory Domain.')
    FQDN = fields.String(required=False, example='', description='')
    IAMRoleName = fields.String(required=False, example='', description='')
    Status = fields.String(required=False, example='',
                           description='status of the DB instance Active Directory Domain membership')


class DomainMembershipsResponseSchema(Schema):
    DomainMembership = fields.Nested(
        DomainMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=False)


class EndpointResponseSchema(Schema):
    Address = fields.String(
        required=False,
        allow_none=True,
        example='',
        description= 'the DNS address of the DB instance')
    # HostedZoneId = fields.String(required=False, example='', description= '')
    Port = fields.Integer(
        required=False,
        allow_none=True,
        example='',
        description='the port that the database engine is listening on')


class OptionGroupMembership1ResponseSchema(Schema):
    OptionGroupName = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='name of the option group that the instance belongs to')
    Status = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='status of the DB instance option group membership')


class OptionGroupMembershipResponseSchema(Schema):
    OptionGroupMembership = fields.Nested(
        OptionGroupMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=False)


class PendingModifiedValuesResponseSchema(Schema):
    pass


class DBInstanceStatusInfoResponseSchema(Schema):
    Message = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    Normal = fields.Boolean (
        required=False,
        allow_none=True,
        example='',
        description='')
    Status = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    StatusType = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')


class VpcSecurityGroupMembership1ResponseSchema(Schema):
    nvl_vpcSecurityGroupName = fields.String(
        required=False,
        allow_none=True,
        data_key='nvl-vpcSecurityGroupName',
        example='',
        description='name of the VPC security group')
    VpcSecurityGroupId = fields.String(
        required=False,
        example='',
        description='ID of the VPC security group')
    Status = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='status of the VPC security group')


class VpcSecurityGroupMembershipResponseSchema(Schema):
    VpcSecurityGroupMembership = fields.Nested(
        VpcSecurityGroupMembership1ResponseSchema,
        many=False,
        required=False,
        allow_none=True)


class DBSecurityGroupsResponseSchema(Schema):
    DBSecurityGroupName = fields.String(
        required=False,
        example='',
        description='security groups to associate with DB instance')


class CreateDBInstances2ApiResponseSchema(Schema):
    AllocatedStorage = fields.Integer(
        required=False,
        default=0,
        example='20',
        description='amount of storage (in GB) to allocate for the DB instance')
    AutoMinorVersionUpgrade = fields.Boolean(
        required=False,
        allow_none=True,
        description='indicates that minor version patches are applied automatically')
    AvailabilityZone = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='availability zone for DB instance')
    BackupRetentionPeriod = fields.Integer(
        required=False,
        allow_none=True,
        example='1',
        description='number of days for which automatic DB snapshots are retained')
    CACertificateIdentifier = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='identifier of the CA certificate for this DB instance.')
    CharacterSetName = fields.String(
        required=False,
        allow_none=True,
        example='',
        description=' character set associated to instance')
    CopyTagsToSnapshot = fields.Boolean(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBClusterIdentifier = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='name of the DB cluster that the DB instance is a member of.')
    DBInstanceArn = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBInstanceClass = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBInstanceIdentifier = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DbInstancePort = fields.Integer(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBInstanceStatus = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBIResourceId = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBName = fields.String(
        required=False,
        allow_none=True,
        example='',
        description='')
    DBParameterGroups = fields.Nested(
        DBParameterGroupStatusResponseSchema,
        many=True,
        required=False,
        allow_none=True)
    DBSecurityGroups = fields.Nested(
        DBSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True)
    DBSubnetGroup = fields.Nested(
        DBSubnetGroupResponseSchema,
        many=False,
        required=False,
        allow_none=True)
    DomainMemberships = fields.Nested(
        DomainMembershipsResponseSchema,
        many=True,
        required=False,
        allow_none=True)
    Endpoint = fields.Nested(
        EndpointResponseSchema,
        many=False,
        required=False,
        allow_none=False)

    Engine = fields.String(
        required=False,
        example='',
        description='')
    EngineVersion = fields.String(
        required=False,
        example='',
        description='')
    EnhancedMonitoringResourceArn = fields.String(
        required=False,
        example='',
        description='')
    IAMDatabaseAuthenticationEnabled = fields.Boolean(
        required=False,
        example='',
        description='')
    InstanceCreateTime= fields.DateTime(
        required=False,
        example='',
        description='')
    Iops = fields.Integer(
        required=False,
        example='',
        description='')
    KmsKeyId = fields.String(
        required=False,
        example='',
        description='')
    LatestRestorableTime= fields.DateTime(
        required=False,
        example='',
        description='')
    LicenseModel = fields.String(
        required=False,
        example='',
        description='')
    MasterUsername = fields.String(
        required=False,
        example='',
        description='')
    MonitoringInterval = fields.Integer(
        required=False,
        example='',
        description='')
    MonitoringRoleArn = fields.String(
        required=False,
        example='',
        description='')
    MultiAZ = fields.Boolean(
        required=False,
        example='',
        description='')

    OptionGroupMemberships = fields.Nested(
        OptionGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True)
    PendingModifiedValues = fields.Nested(
        PendingModifiedValuesResponseSchema,
        many=False,
        required=False,
        allow_none=True)

    PerformanceInsightsEnabled = fields.Boolean(
        required=False,
        example='',
        description='')
    PerformanceInsightsKMSKeyId = fields.String(
        required=False,
        example='',
        description='')
    PreferredBackupWindow = fields.String(
        required=False,
        example='',
        description='')
    PreferredMaintenanceWindow = fields.String(
        required=False,
        example='',
        description='')
    PromotionTier = fields.Integer(
        required=False,
        example='',
        description='')
    PubliclyAccessible = fields.Boolean(
        required=False,
        example='',
        description='')
    ReadReplicaDBClusterIdentifiers = fields.List(
        fields.String(example=''),
        required=False,
        many=False,
        allow_none=True,
        data_key='ReadReplicaDBClusterIdentifiers.ReadReplicaDBClusterIdentifier.N',
        attribute='ReadReplicaDBClusterIdentifiers.ReadReplicaDBClusterIdentifier.N',
        description='')
    ReadReplicaDBInstanceIdentifiers = fields.List(
        fields.String(example=''),
        required=False,
        many=False,
        allow_none=True,
        data_key='ReadReplicaDBInstanceIdentifiers.ReadReplicaDBInstanceIdentifier.N',
        attribute='ReadReplicaDBInstanceIdentifiers.ReadReplicaDBInstanceIdentifier.N',
        description='')

    ReadReplicaSourceDBInstanceIdentifier = fields.String(
        required=False,
        example='',
        description='')
    SecondaryAvailabilityZone = fields.String(
        required=False,
        example='',
        description='')
    StatusInfos = fields.Nested(
        DBInstanceStatusInfoResponseSchema,
        many=True,
        required=False,
        allow_none=True)
    StorageEncrypted = fields.Boolean(
        required=False,
        example='',
        description='')
    StorageType = fields.String(
        required=False,
        example='',
        description='')
    TdeCredentialArn = fields.String(
        required=False,
        example='',
        description='')
    Timezone = fields.String(
        required=False,
        example='',
        description='')

    VpcSecurityGroups = fields.Nested(
        VpcSecurityGroupMembershipResponseSchema,
        many=True,
        required=False,
        allow_none=True)


class CreateDBInstancesApiResponseSchema(Schema):
    ResponseMetadata = fields.Nested(
        DBResponseMetadataResponseSchema,
        required=True,
        many=False,
        allow_none=False)
    DBInstance = fields.Nested(
        CreateDBInstances2ApiResponseSchema,
        required=True,
        many=True,
        allow_none=False)


class CreateDBInstanceApiResponseSchema(Schema):
    ResponseMetadata = fields.Nested(
        DBResponseMetadataResponseSchema,
        required=True,
        many=False,
        allow_none=False)
    DBInstance = fields.Nested(
        CreateDBInstances2ApiResponseSchema,
        required=True,
        many=False,
        allow_none=False)


class CreateDBInstanceResultApiResponseSchema(Schema):
    CreateDBInstanceResult = fields.Nested(
        CreateDBInstanceApiResponseSchema,
        required=True,
        many=False,
        allow_none=False)


class CreateDBInstanceResponseSchema(Schema):
    CreateDBInstanceResponse = fields.Nested(
        CreateDBInstanceResultApiResponseSchema,
        required=True,
        many=False,
        allow_none=False)


class VpcSecurityGroupId_NRequestSchema(Schema):
    VpcSecurityGroupId = fields.List(fields.String(), required=True, description='security group id')


class Tag_NRequestSchema(Schema):
    key = fields.String(required=False, allow_none=False, description='tag key')
    value = fields.String(required=False, allow_none=False, description='tag value')


class TagSetRequestSchema(Schema):
    Tag = fields.Nested(Tag_NRequestSchema, many=False, required=False, allow_none=False)


class CreateDBInstancesApiParamRequestSchema(Schema):
    AccountId = fields.String(required=True, example='', description='account id or uuid associated to compute zone')
    AllocatedStorage = fields.Integer(Required=False, default=30, example=30, missing=30, validate=Range(min=30),
                                      description='amount of storage (in GB) to allocate for the DB instance')
    # AvailabilityZone = fields.String(required=False, allow_none=True, example='',
    #                                  description='availability zone of DB instance')
    # BackupRetentionPeriod = fields.Integer(required=False, default=1, example='1',
    #                                        description='number of days to retain backup')
    # CharacterSetName = fields.String(required=False, example='', description='characterSet of DB instance')

    # DBClusterIdentifier = fields.String(required=False, example='', description='identifier of the DB cluster ')

    DBInstanceClass = fields.String(required=True,  example='db.m1.small',
                                    description='service definition of the DB instance')
    DBInstanceIdentifier = fields.String(required=True,  example='', description='ID DB instance account')
    DBName = fields.String(required=False, missing='mydbname', example='', description='name of instance database to create')
    # ??
    VpcSecurityGroupIds = fields.Nested(VpcSecurityGroupId_NRequestSchema, many=False, required=False, allow_none=False)
    DBSubnetGroupName = fields.String(required=True, example='',
                                      description='a DB security groups to associate with DB instance')

    # EnableCloudwatchLogsExports_member_N = fields.List(fields.String(example='transaction.log'),
    # required=False, many=False, allow_none=True)
    # engine possibile value ['MySQL' | 'MariaDB' | 'PostgresSQL' | 'Oracle' | 'SQL Server']
    Engine = fields.String(required=True,  example='MySQL', description='engine of DB instance',
                           validate=OneOf(['mysql', 'oracle', 'postgresql', 'sqlserver']))
    EngineVersion = fields.String(required=True,  example='5.7', description='engine version of DB instance')

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
    MasterUserPassword = fields.String(required=False, allow_none=True, example='',
                                       description='password for the master database user')
    #
    # MonitoringInterval = fields.Integer(Required=False, default=0, example='20', description='interval in seconds
    # for Enhanced Monitoring metrics are collected for the DB instance')
    # MonitoringRoleArn = fields.String(Required=False,example='', description='')
    # TdeCredentialArn = fields.String(required=False,  example='', description='ARN for TDE encryption to associate
    # with DB instance')
    # TdeCredentialPassword = fields.String(required=False,  example='', description='password for the given ARN')

    MultiAZ = fields.Boolean(required=False, allow_none=True, example=True, missing=False,
                             description='Specifies if the DB instance is a Multi-AZ deployment')
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
    Tag_N = fields.Nested(TagSetRequestSchema, many=True, required=False,  allow_none=True)
    # SchemaName = fields.String(required=False,  example='', description='schema name to use for a db instance
    # postgresql')
    # ExtensionName_N = fields.List (fields.String(example=''), required=False, description='extension to install
    # for a db instance postgresql')
    Nvl_KeyName = fields.String(required=False, example='1ffd', allow_none=True,
                                description='The name of the key pair')


class CreateDBInstancesApiRequestSchema(Schema):
    dbinstance = fields.Nested(CreateDBInstancesApiParamRequestSchema, context='body')


class CreateDBInstancesApiBodyRequestSchema(Schema):
    body = fields.Nested(CreateDBInstancesApiRequestSchema, context='body')


class CreateDBInstances(ServiceApiView):
    summary = 'Create database service'
    description = 'Create database service'
    tags = ['databaseservice']
    definitions = {
        'CreateDBInstancesApiRequestSchema': CreateDBInstancesApiRequestSchema,
        'CreateDBInstanceResponseSchema': CreateDBInstanceResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateDBInstancesApiBodyRequestSchema)
    parameters_schema = CreateDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateDBInstanceResponseSchema
        }
    })
    response_schema = CreateDBInstanceResponseSchema

    def post(self, controller: ServiceController, data, *args, **kwargs):
        inner_data = data.get('dbinstance')

        service_definition_id = inner_data.get('DBInstanceClass')
        account_id = inner_data.get('AccountId')
        name = inner_data.get('DBInstanceIdentifier')
        desc = inner_data.get('DBInstanceIdentifier')
        engine = inner_data.get('Engine')
        engine_version = inner_data.get('EngineVersion')

        # check instance with the same name already exists
        self.service_exist(controller, name, ApiDatabaseService.plugintype)

        account, parent_inst = self.check_parent_service(controller, account_id,
                                                         plugintype=ApiDatabaseService.plugintype)

        # get service definition with engine configuration
        engine_def_name = 'db-engine-%s-%s' % (engine, engine_version)
        engine_defs, tot = controller.get_paginated_service_defs(name=engine_def_name)
        if len(engine_defs) < 1 or len(engine_defs) > 1:
            raise ApiManagerError('Engine %s with version %s was not found' % (engine, engine_version))

        # add engine config
        engine_def_config = engine_defs[0].get_main_config().params
        data.update({'engine': engine_def_config})

        self.logger.warn(data)

        data['computeZone'] = parent_inst.instance.resource_uuid
        inst = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                  parent_plugin=parent_inst, instance_config=data)

        res = {
            'CreateDBInstanceResponse': {
                '__xmlns': self.xmlns,
                'CreateDBInstanceResult': {
                    'DBInstance': {
                        'DBInstanceIdentifier': inst.instance.uuid,
                        'DBInstanceStatus': inst.status,
                        'DbiResourceId': None,
                    },
                    'ResponseMetadata': {
                        'RequestId': operation.id
                    }
                }
            }
        }

        return res, 202


class DBInstanceParameterResponseSchema(Schema):
    AllocatedStorage = fields.Integer(Required=False, default=0, missing=0, example='20',
                                      description='amount of storage (in GB) to allocate for the DB instance')
    AutoMinorVersionUpgrade = fields.Boolean(Required=False, allow_none=True, description='indicates that minor version patches are '
                                                                         'applied automatically')
    AvailabilityZone = fields.String(required=False, allow_none=True, example='', description='')
    BackupRetentionPeriod = fields.Integer(required=False, allow_none=True, example='', description='')
    CACertificateIdentifier = fields.String(required=False, allow_none=True, example='', description='')
    CharacterSetName = fields.String(required=False, allow_none=True, example='', description='')
    # Not supported
    CopyTagsToSnapshot = fields.Boolean(required=False, allow_none=True, example='', description='')
    DomainMemberships = fields.Nested(DomainMembershipsResponseSchema, many=True, required=False, allow_none=True)
    DBParameterGroups = fields.Nested(DBParameterGroupStatusResponseSchema, many=True, required=False, allow_none=True)
    IAMDatabaseAuthenticationEnabled = fields.Boolean(required=False, allow_none=True, example='', description='')
    PerformanceInsightsKMSKeyId = fields.String(required=False,allow_none=True, example='', description='')
    OptionGroupMemberships = fields.Nested(OptionGroupMembershipResponseSchema, many=True, required=False,
                                           allow_none=True)
    PerformanceInsightsEnabled = fields.Boolean(required=False, allow_none=True, example='', description='')
    PromotionTier = fields.Integer(required=False, allow_none=True, example='', description='')
    Timezone = fields.String(required=False, allow_none=True, example='', description='')

    #    Deprecated
    DBSecurityGroups = fields.Nested(DBSecurityGroupMembershipResponseSchema, many=True, required=False,
                                     allow_none=True)

    #    We don't known parameter
    DBClusterIdentifier = fields.String(required=False, allow_none=True, example='', description='')
    MonitoringInterval = fields.Integer(required=False, allow_none=True, example='', description='')
    MonitoringRoleArn = fields.String(required=False, allow_none=True, example='', description='')
    TdeCredentialArn = fields.String(required=False, allow_none=True, example='', description='')
    TdeCredentialPassword = fields.String(required=False, allow_none=True, example='', description='')
    Iops = fields.Integer(required=False, allow_none=True, example='', description='')
    KmsKeyId = fields.String(required=False, example='', description='')
    EnabledCloudwatchLogsExports_member_N = fields.List(fields.String(example=''), required=False, description='',
                                                       data_key='EnabledCloudwatchLogsExports.member.N')
    DBInstanceArn = fields.String(required=False, allow_none=True, example='', description='')
    EnhancedMonitoringResourceArn = fields.String(required=False, example='', description='')
    #
    DBInstanceClass = fields.String(required=False, example='', description='')
    DBInstanceIdentifier = fields.String(required=False, example='', description='')
    DbInstancePort = fields.Integer(required=False, example='', description='')
    DBInstanceStatus = fields.String(required=False, example='', description='')
    DbiResourceId = fields.String(required=False, example='', description='')
    DBName = fields.String(required=False, example='', description='name of the database instance')

    DBSubnetGroup = fields.Nested(DBSubnetGroupResponseSchema, many=False, required=False, allow_none=True)
    Endpoint = fields.Nested(EndpointResponseSchema, many=False, required=False, allow_none=False)
    Engine = fields.String(required=False, allow_none=True, example='', description='name of the DB engine')
    EngineVersion = fields.String(required=False, allow_none=True, example='', description='DB engine version')
    InstanceCreateTime= fields.DateTime(required=False, example='', description='DB instance creation date')
    LatestRestorableTime= fields.DateTime(required=False, example='', description='DB instance last modification date')
    LicenseModel = fields.String(required=False, allow_none=True, example='', description='')
    MasterUsername = fields.String(required=False, allow_none=True, example='', description='master username for the DB instance')
    MultiAZ = fields.Boolean(required=False, allow_none=True, example='', description='Specifies if the DB instance is a Multi-AZ deployment')
    PendingModifiedValues = fields.Nested(PendingModifiedValuesResponseSchema, many=False, required=False,
                                          allow_none=True)
    PreferredBackupWindow = fields.String(required=False, allow_none=True, example='', description='the daily time range during which automated backups are created')
    PreferredMaintenanceWindow = fields.String(required=False, example='', description='the weekly time range during which system maintenance can occur')
    PubliclyAccessible = fields.Boolean(required=False, allow_none=True, example='', description='')
    ReadReplicaDBClusterIdentifiers = fields.List(fields.String(example=''), required=False, many=False,
                                                  allow_none=True, data_key='ReadReplicaDBClusterIdentifiers.'
                                                                             'ReadReplicaDBClusterIdentifier.N',
                                                  attribute='ReadReplicaDBClusterIdentifiers.'
                                                            'ReadReplicaDBClusterIdentifier.N',
                                                  description='')
    ReadReplicaDBInstanceIdentifiers = fields.List(fields.String(example=''), required=False, many=False,
                                                   allow_none=True, data_key='ReadReplicaDBInstanceIdentifiers.'
                                                                              'ReadReplicaDBInstanceIdentifier.N',
                                                   attribute='ReadReplicaDBInstanceIdentifiers.'
                                                             'ReadReplicaDBInstanceIdentifier.N',
                                                   description='')
    ReadReplicaSourceDBInstanceIdentifier = fields.String(required=False, allow_none=True, example='', description='')
    SecondaryAvailabilityZone = fields.String(required=False, allow_none=True, example='', description='')
    StatusInfos = fields.Nested(DBInstanceStatusInfoResponseSchema, many=True, required=False, allow_none=True)
    StorageEncrypted = fields.Boolean(required=False, allow_none=True, example='', description='')
    StorageType = fields.String(required=False, allow_none=True, example='', description='')
    VpcSecurityGroups = fields.Nested(VpcSecurityGroupMembershipResponseSchema, many=True, required=False,
                                      allow_none=True)
    nvl_stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False,
                                    allow_none=True, data_key='nvl-stateReason')
    nvl_name = fields.String(required=False, allow_none=True, example='',
                             description='name of the instance', data_key = 'nvl-name')
    nvl_ownerAlias = fields.String(required=False, allow_none=True, example='',
                                   description='name of the account that owns the instance',
                                   data_key='nvl-ownerAlias')
    nvl_ownerId = fields.String(required=False, allow_none=True, example='',
                                description='ID of the account that owns the instance', data_key='nvl-ownerId')
    nvl_resourceId = fields.String(required=False, allow_none=True, example='',
                                   description='ID of the instance resource', data_key='nvl-resourceId')


class DBInstanceResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterResponseSchema, many=False, required=True, allow_none=False)


class DescribeDBInstanceResultResponseSchema(Schema):
    DBInstances = fields.Nested(DBInstanceResponseSchema, many=True, required=False, allow_none=True)
    Marker = fields.String(required=False, allow_none=True)
    nvl_DBInstancesTotal =  fields.String(required=True, example=0, data_key = 'nvl-DBInstancesTotal')


class DescribeDBInstanceResultResponse1Schema (Schema):
    DescribeDBInstancesResult = fields.Nested(DescribeDBInstanceResultResponseSchema, many=False, required=True)
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, many=False, required=False, allow_none=True)


class DescribeDBInstancesResponseSchema(Schema):
    DescribeDBInstancesResponse = fields.Nested(DescribeDBInstanceResultResponse1Schema, required=True, many=False,
                                                allow_none=False)


class DescribeDBInstancesRequestSchema(Schema):
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=True,
                             context='query', collection_format='multi', data_key='owner-id.N')
    DBInstanceIdentifier = fields.String(required=False, context='query')
    db_instance_id_N = fields.List(fields.String(example=''), required=False, allow_none=True,
                                   context='query', collection_format='multi', data_key='db-instance-id.N')

    MaxRecords = fields.Integer(required=False, missing=100, validation=Range(min=20, max=100), context='query')
    Marker = fields.String(required=False, missing='0', default='0', context='query')
    Nvl_tag_key_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                collection_format='multi', data_key='Nvl-tag-key.N',
                                descriptiom='value of a tag assigned to the resource')


class DescribeDBInstances(ServiceApiView):
    summary = 'Describe database service'
    description = 'Describe database service'
    tags = ['databaseservice']
    definitions = {
        'DescribeDBInstancesRequestSchema': DescribeDBInstancesRequestSchema,
        'DescribeDBInstancesResponseSchema': DescribeDBInstancesResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstancesRequestSchema)
    parameters_schema = DescribeDBInstancesRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeDBInstancesResponseSchema
        }
    })
    response_schema = DescribeDBInstancesResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        maxRecords = data.get('MaxRecords', 100)
        marker = int(data.get('Marker', 0))

        # check Account
        # accountIdList, zone_list = self.get_account_list(controller, data, ApiDatabaseService)

        # check Account
        account_id_list = data.get('owner_id_N', [])

        # get instance identifier
        instance_id_list = data.get('db_instance_id_N', [])

        # get instance name
        instance_name_list = data.get('DBInstanceIdentifier', None)
        if instance_name_list is not None:
            instance_name_list = [instance_name_list]

        # get tags
        tag_values = data.get('Nvl_tag_key_N', None)

        # get instances list
        res, total = controller.get_service_type_plugins(service_uuid_list=instance_id_list,
                                                         service_name_list=instance_name_list,
                                                         account_id_list=account_id_list,
                                                         servicetags_or=tag_values,
                                                         plugintype=ApiDatabaseServiceInstance.plugintype,
                                                         page=marker,
                                                         size=maxRecords)

        # format result
        instances_set = [{'DBInstance':r.aws_info()} for r in res]

        res = {
            'DescribeDBInstancesResponse': {
                '__xmlns': self.xmlns,
                'DescribeDBInstancesResult': {
                    'Marker': marker,
                    'DBInstances': instances_set,
                    'nvl-DBInstancesTotal': total
                },
                'ResponseMetadata': {
                    'RequestId': operation.id,
                }
            }
        }
        return res


class DeleteDBInstanceResponseSchema(Schema):
    DBInstance = fields.Nested(DBInstanceParameterResponseSchema, many=False, required=False, allow_none=True)
    ResponseMetadata = fields.Nested(DBResponseMetadataResponseSchema, many=False, required=False, allow_none=True)


class DeleteDBInstanceResultResponseSchema(Schema):
    DeleteDBInstanceResult = fields.Nested(DeleteDBInstanceResponseSchema, many=False, required=False, allow_none=False)


class DeleteDBInstancesApiResponseSchema(Schema):
    DeleteDBInstanceResponse = fields.Nested(DeleteDBInstanceResultResponseSchema, required=True, many=False,
                                             allow_none=False)


class DeleteDBInstancesApiRequestSchema(Schema):
    DBInstanceIdentifier = fields.String(required=True, context='query',
                                         description='The DB instance identifier for the DB instance to be deleted')
    FinalDBSnapshotIdentifier = fields.String(required=False, allow_none=True, context='query',
                                              description='The DBSnapshotIdentifier of the new DBSnapshot created '
                                                          'when SkipFinalSnapshot is set to false.')
    SkipFinalSnapshot = fields.String(required=False, allow_none=True, context='query',
                                      description='Determines whether a final DB snapshot is created before the DB '
                                                  'instance is deleted. If true is specified, no DBSnapshot is '
                                                  'created. If false is specified, a DB snapshot is created before '
                                                  'the DB instance is deleted.')


class DeleteDBInstances(ServiceApiView):
    summary = 'Delete database service'
    description = 'Delete database service'
    tags = ['databaseservice']
    definitions = {
        'DeleteDBInstancesApiRequestSchema': DeleteDBInstancesApiRequestSchema,
        'DeleteDBInstancesApiResponseSchema': DeleteDBInstancesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DeleteDBInstancesApiRequestSchema)
    parameters_schema = DeleteDBInstancesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DeleteDBInstancesApiResponseSchema
        }
    })
    response_schema = DeleteDBInstancesApiResponseSchema

    def delete(self, controller: ServiceController, data, *args, **kwargs):
        instance_id = data.pop('DBInstanceIdentifier')

        type_plugin = controller.get_service_type_plugin(instance_id)
        info = type_plugin.aws_info()
        type_plugin.delete()

        res = {
            'DeleteDBInstanceResponse': {
                '__xmlns': self.xmlns,
                'DeleteDBInstanceResult': {
                    'DBInstance': info,
                },
                'ResponseMetadata': {
                    'RequestId': operation.id,
                }
            }
        }

        return res, 202


class StopDBInstances(ServiceApiView):
    """
    Stop a database instance
    Stop a database instance
    """
    pass


class StartDBInstances(ServiceApiView):
    """
    Start a database instance
    Start a database instance
    """
    pass


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


class RebootDBInstance(ServiceApiView):
    """
    Reboot a database instance
    Reboot a database instance
    """
    pass


class PurchaseReservedDBInstancesOffering(ServiceApiView):
    """
    Purchase a database instance
    Purchase a database instance
    """
    pass


class InstanceTypeFeatureResponseSchema (Schema):
    vcpus = fields.String(required=False, allow_none=True, example='', description='')
    ram = fields.String(required=False, allow_none=True, example='', description='')
    disk = fields.String(required=False, allow_none=True, example='', description='')


class InstanceTypeResponseSchema(Schema):
    id = fields.Integer(required=True, example='', description='')
    uuid = fields.String(required=True, example='', description='')
    name = fields.String(required=True, example='', description='')
    resource_id = fields.String(required=False, allow_none=True, example='', description='')
    description = fields.String(required=True, allow_none=True, example='', description='')
    features = fields.Nested(InstanceTypeFeatureResponseSchema, required=True, many=False, allow_none=False)


class DescribeDBInstanceTypesApi1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    instanceTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    instanceTypesTotal = fields.Integer(required=True)


class DescribeDBInstanceTypesApiResponseSchema(Schema):
    DescribeDBInstanceTypesResponse = fields.Nested(DescribeDBInstanceTypesApi1ResponseSchema, required=True,
                                                    many=False, allow_none=False)


class DescribeDBInstanceTypesApiRequestSchema(Schema):
    MaxResults = fields.Integer(
        required=False, default=10, description='entities list page size', context='query')
    NextToken = fields.String(required=False, default='0',
                              description='entities list page selected', context='query')
    ownerId = fields.String(required=False, allow_none=True, example='',
                            description='ID of the account that owns the customization')
    instance_type_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                  collection_format='multi', data_key='instance-type.N',
                                  description='list of instance type uuid')


class DescribeDBInstanceTypes(ServiceApiView):
    summary = 'List of active instance types'
    description = 'List of active instance types'
    tags = ['databaseservice']
    definitions = {
        'DescribeDBInstanceTypesApiRequestSchema': DescribeDBInstanceTypesApiRequestSchema,
        'DescribeDBInstanceTypesApiResponseSchema': DescribeDBInstanceTypesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceTypesApiRequestSchema)
    parameters_schema = DescribeDBInstanceTypesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeDBInstanceTypesApiResponseSchema
        }
    })
    response_schema = DescribeDBInstanceTypesApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        instance_types_set, total = controller.get_catalog_service_definitions(
            size=data.pop('MaxResults', 10), page=int(data.pop('NextToken', 0)), plugintype='DatabaseInstance',
            def_uuids=data.pop('instance_type_N', []))

        res = {
            'DescribeDBInstanceTypesResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'instanceTypesSet': instance_types_set,
                'instanceTypesTotal': total
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
    engine = fields.String(required=True, example='', description='')
    engineVersion = fields.String(required=True, example='', description='')


class DescribeDBInstanceEngineTypesApi1ResponseSchema(Schema):
    engineTypesSet = fields.Nested(DescribeDBInstanceEngineTypesParamsApiResponseSchema, many=True, allow_none=False,
                                   example='', description='')
    engineTypesTotal = fields.Integer(required=True, example='', description='')


class DescribeDBInstanceEngineTypesApiResponseSchema(Schema):
    DescribeDBInstanceEngineTypesResponse = fields.Nested(DescribeDBInstanceEngineTypesApi1ResponseSchema,
                                                          required=True, many=False, allow_none=False)


class DescribeDBInstanceEngineTypes(ServiceApiView):
    summary = 'List of db instance engine types'
    description = 'List of db instance engine types'
    tags = ['databaseservice']
    definitions = {
        'DescribeDBInstanceEngineTypesApiRequestSchema': DescribeDBInstanceEngineTypesApiRequestSchema,
        'DescribeDBInstanceEngineTypesApiResponseSchema': DescribeDBInstanceEngineTypesApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeDBInstanceEngineTypesApiRequestSchema)
    parameters_schema = DescribeDBInstanceEngineTypesApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeDBInstanceEngineTypesApiResponseSchema
        }
    })
    response_schema = DescribeDBInstanceEngineTypesApiResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        instance_engines_set, total = controller.get_catalog_service_definitions(plugintype='VirtualService', size=-1)
        self.logger.warn(instance_engines_set)

        engine_types_set, total = [], 0
        for e in instance_engines_set:
            name = e.get('name')
            if name.find('db-engine') != 0:
                continue
            esplit = name.split('-')
            item = {}
            item['engine'] = esplit[2]
            item['engineVersion'] = esplit[3]
            engine_types_set.append(item)
            total += 1

        res = {
            'DescribeDBInstanceEngineTypesResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'engineTypesSet': engine_types_set,
                'engineTypesTotal': total
            }
        }
        self.logger.warning('res=%s' % res)
        return res


class DatabaseInstanceAPI(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/databaseservices/instance'
        rules = [
            ('%s/describedbinstances' % base, 'GET', DescribeDBInstances, {}),
            ('%s/createdbinstance' % base, 'POST', CreateDBInstances, {}),
            # ('%s/stopdbinstance' % base, 'PUT', StopDBInstances, {}),
            # ('%s/startdbinstance' % base, 'PUT', StartDBInstances, {}),
            ('%s/deletedbinstance' % base, 'DELETE', DeleteDBInstances, {}),
            # ('%s/createdbinstancereadreplica' % base, 'POST', CreateDBInstanceReadReplica, {}),
            # ('%s/promotereadreplica' % base, 'GET', PromoteReadReplica, {}),
            # ('%s/rebootdbinstance' % base, 'PUT', RebootDBInstance, {}),
            # ('%s/purchasereserveddbinstancesoffering' % base, 'GET', PurchaseReservedDBInstancesOffering, {})
            ('%s/describedbinstancetypes' % base, 'GET', DescribeDBInstanceTypes, {}),
            # (f'{module.base_path}/accounts/<oid>/databaseservices/describedbinstancetypes', 'GET', DescribeAccountDBInstanceTypes, {}),
            ('%s/enginetypes' % base, 'GET', DescribeDBInstanceEngineTypes, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
