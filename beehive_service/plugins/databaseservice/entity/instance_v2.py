# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from copy import deepcopy
from ipaddress import IPv4Network
from logging import getLogger
from typing import TYPE_CHECKING, List, Union
from urllib.parse import urlencode
from beecell.password import obscure_data
from beecell.simple import (
    format_date,
    truncate,
    obscure_data,
    dict_get,
)
from beecell.types.type_string import truncate, str2bool
from beecell.types.type_date import format_date
from beecell.types.type_dict import dict_get
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import trace
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model.base import SrvStatusType
from beehive_service.plugins.computeservice.controller import (
    ApiComputeSubnet,
    ApiComputeSecurityGroup,
    ApiComputeVPC,
    ApiComputeKeyPairsHelper,
    ApiComputeService,
)

if TYPE_CHECKING:
    from beehive_service.controller import ServiceController

logger = getLogger(__name__)


class ApiDatabaseServiceInstanceV2(AsyncApiServiceTypePlugin):
    plugintype = "DatabaseInstance"
    objname = "dbinstance"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.sql_stack_version = "v2.0"

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return ApiServiceTypePlugin.info(self)

    @staticmethod
    def customize_list(controller: 'ServiceController', entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_ids = {e.instance.account_id for e in entities}
        account_idx = controller.get_account_idx(id_list=account_ids)
        subnet_idx = controller.get_service_instance_idx(ApiComputeSubnet.plugintype, account_id_list=account_ids)
        vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype, account_id_list=account_ids)
        security_group_idx = controller.get_service_instance_idx(
            ApiComputeSecurityGroup.plugintype, account_id_list=account_ids
        )
        compute_service_idx = controller.get_service_instance_idx(
            ApiComputeService.plugintype, index_key="account_id", account_id_list=account_ids
        )
        instance_type_idx = controller.get_service_definition_idx(ApiDatabaseServiceInstanceV2.plugintype)
        # get resources
        resources = set()
        zones = set()
        for entity in entities:
            entity_instance = entity.instance
            account_id_s = "%s" % entity_instance.account_id
            entity.account = account_idx.get(account_id_s)
            entity.compute_service = compute_service_idx.get(account_id_s)

            subnet = subnet_idx.get("%s" % entity.get_config("dbinstance.DBSubnetGroupName"))
            entity.subnet = subnet
            if subnet is not None:
                entity.subnet_vpc = vpc_idx.get(subnet.get_parent_id())
                entity.avzone = subnet.get_config("site")
            else:
                entity.subnet_vpc = None
                entity.avzone = None

            # set security group indexes
            entity.security_group_idx = security_group_idx
            # get instance type
            entity.instance_type = instance_type_idx.get("%s" % entity_instance.service_definition_id)
            zones.add(entity.compute_service.resource_uuid)
            if entity_instance.resource_uuid is not None:
                resources.add(entity_instance.resource_uuid)

        resources_idx = {}
        if len(resources) > 0 and len(zones) <= 3:
            api_db_serv_inst = ApiDatabaseServiceInstanceV2(controller)
            resources_list = api_db_serv_inst.list_resources(zones=zones, uuids=resources)
            resources_idx = {r["uuid"]: r for r in resources_list}
        elif len(resources) > 0:
            api_db_serv_inst = ApiDatabaseServiceInstanceV2(controller)
            resources_list = api_db_serv_inst.list_resources(uuids=resources)
            resources_idx = {r["uuid"]: r for r in resources_list}
        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    @staticmethod
    def customize_simple_list(controller: 'ServiceController', entities, *args, **kvargs):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_ids = {e.instance.account_id for e in entities}
        account_idx = controller.get_account_idx(id_list=account_ids)

        # divisions
        division_ids: List[int] = []
        from beehive_service.controller.api_account import ApiAccount
        apiAccounts: List[ApiAccount] = account_idx.values()
        for apiAccount in apiAccounts:
            div_oid = apiAccount.model.division.id
            if div_oid not in division_ids:
                division_ids.append(div_oid)
        logger.debug2("fv - customize_simple_list - division_ids: %s" % division_ids)
        division_idx = controller.get_division_idx(id_list=division_ids)
        logger.debug2("fv - customize_simple_list - division_idx: %s" % division_idx)

        subnet_idx = controller.get_service_instance_idx(ApiComputeSubnet.plugintype, account_id_list=account_ids)
        # vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype, account_id_list=account_ids)
        # security_group_idx = controller.get_service_instance_idx(
        #     ApiComputeSecurityGroup.plugintype, account_id_list=account_ids
        # )
        # compute_service_idx = controller.get_service_instance_idx(
        #     ApiComputeService.plugintype, index_key="account_id", account_id_list=account_ids
        # )
        # instance_type_idx = controller.get_service_definition_idx(ApiDatabaseServiceInstanceV2.plugintype)
        # get resources
        resource_uuids = []
        # zones = set()
        for entity in entities:
            entity_instance = entity.instance
            account_id_s = "%s" % entity_instance.account_id
            entity.account = account_idx.get(account_id_s)
            entity.division = division_idx.get(str(entity.account.model.division.id))
            # entity.compute_service = compute_service_idx.get(account_id_s)

            subnet = subnet_idx.get("%s" % entity.get_config("dbinstance.DBSubnetGroupName"))
            entity.subnet = subnet
            if subnet is not None:
                # entity.subnet_vpc = vpc_idx.get(subnet.get_parent_id())
                entity.avzone = subnet.get_config("site")
            else:
                entity.subnet_vpc = None
                entity.avzone = None

            # set security group indexes
            # entity.security_group_idx = security_group_idx
            # get instance type
            # entity.instance_type = instance_type_idx.get("%s" % entity_instance.service_definition_id)

            # zones.add(entity.compute_service.resource_uuid)
            if entity_instance.resource_uuid is not None:
                resource_uuids.append(entity_instance.resource_uuid)

        resources_idx = {}
        if len(resource_uuids) > 0:
            # sg_info = kvargs.get("sg_info", False)
            # flavor_info = kvargs.get("flavor_info", False)
            api_db_serv_inst = ApiDatabaseServiceInstanceV2(controller)
            resources = []

            block_size = 80
            blocks = [resource_uuids[i:i + block_size] for i in range(0, len(resource_uuids), block_size)]
            # logger.debug2(f"fv - customize_simple_list - blocks: {blocks}")
            for block in blocks:
                logger.debug2(f"fv - customize_simple_list - block length: {len(block)}")
                resources += api_db_serv_inst.list_simple_resources(
                    uuids=block, # sg_info=sg_info, flavor_info=flavor_info
                )
            resources_idx = {r["uuid"]: r for r in resources}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        self.account = self.controller.get_account(str(self.instance.account_id))
        if self.get_config("dbinstance.DBSubnetGroupName") is not None:
            self.subnet = self.controller.get_service_instance(self.get_config("dbinstance.DBSubnetGroupName"))
            self.subnet_vpc = self.controller.get_service_instance(self.subnet.get_parent_id())
            self.avzone = self.subnet.get_config("site")
        else:
            self.subnet = None
            self.subnet_vpc = None
            self.avzone = None

        # get security group indexes
        self.security_group_idx = self.controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)

        # get instance type
        self.instance_type = self.controller.get_service_def(self.instance.service_definition_id)

        # assign resources
        if self.instance.resource_uuid is not None and self.instance.resource_uuid != "":
            try:
                self.resource = self.get_resource(uuid=self.instance.resource_uuid)
            except:
                self.resource = None

    def state_mapping(self, state, runstate):
        mapping = {
            SrvStatusType.PENDING: "pending",
            SrvStatusType.BUILDING: "modifying",
            SrvStatusType.CREATED: "creating",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETED: "deleting",
            SrvStatusType.DELETING: "deleting",
            SrvStatusType.DRAFT: "transient",
            SrvStatusType.ERROR: "failed",
            SrvStatusType.ERROR_CREATION: "failed",
            SrvStatusType.TERMINATED: "deleting",
            SrvStatusType.UNKNOWN: "failed",
            SrvStatusType.UPDATING: "modifying",
        }
        inst_state = mapping.get(state, "unknown")

        if state == SrvStatusType.ACTIVE and runstate == "poweredOn":
            inst_state = "available"
        elif state == SrvStatusType.ACTIVE and runstate == "poweredOff":
            inst_state = "stopped"
        # elif state == SrvStatusType.ACTIVE and runstate == 'update':
        #     inst_state = 'modifying'
        # manage rebooting, starting, stopping

        return inst_state

    def get_db_type(self) -> str:
        flavor_resource_name = dict_get(self.resource, "flavor.name")
        if flavor_resource_name is not None:
            flavor_name = flavor_resource_name
        else:
            # NSP-1356
            flavor_name = self.get_config("flavor")
        if flavor_name is not None:
            return flavor_name.replace("vm.", "db.")
        return flavor_name

    def aws_info(self, api_version="v1.0"):
        """Get info as required by aws api

        :param api_version: api version
        :return:
        """
        instance_item = {}

        # get config
        config = self.get_config("dbinstance")
        if config is None:
            config = {}

        # get subnet
        subnet = self.subnet
        subnet_vpc = self.subnet_vpc
        subnet_vpc_id = getattr(subnet_vpc, "uuid")
        avzone = self.avzone

        if self.resource is None:
            self.resource = {}

        resource = self.resource
        attributes = resource.get("attributes", {})
        engine = attributes.get("engine")
        version = attributes.get("version")
        outputs = attributes.get("outputs")
        hypervisor = attributes.get("hypervisor")
        allocated_storage = int(config.get("AllocatedStorage", -1))
        # select correct resource stack version
        # new resource stack v2
        if outputs is not None:
            # replica = attributes.get('replica')
            address = dict_get(resource, "listener.address")
            port = dict_get(resource, "listener.port") or dict_get(resource, "attributes.engine_configs.engine.port")
            # get allocated storage noly if is not present in service config
            if allocated_storage == -1:
                allocated_storage = resource.get("allocated_storage", int(config.get("AllocatedStorage", -1)))
            charset = attributes.get("charset")
            timezone = attributes.get("timezone")

        # old resource stack v1
        else:
            stacks = resource.get("stacks", [])
            # replica = config.get('MultiAZ')
            # resource stack ref
            avz_main_stack = {}
            if len(stacks) > 0:
                avz_main_stack = stacks[0]
            address, port = None, None
            if avz_main_stack.get("listener", ":") is not None:
                address, port = avz_main_stack.get("listener", ":").split(":")

            # get allocated storage
            #  unused value c = int(config.get("AllocatedStorage", -1))

            charset = config.get("CharacterSetName")
            timezone = config.get("Timezone")

        dbname = ""
        if engine == "mysql":
            dbname = "%s:%s" % (address, port)
        elif engine == "mariadb":
            dbname = "%s:%s" % (address, port)
        elif engine == "postgresql":
            dbname = dict_get(attributes, "postgres:database")
        elif engine == "oracle":
            dbname = dict_get(attributes, "oracle:sid")

        port_number = None
        if port is not None and port != "":
            port_number = port

        # get instance and resource status
        instance = self.instance
        status = instance.status
        if resource.get("state") == "ERROR":
            status = "ERROR"

        if api_version == "v1.0":
            instance_item["DBInstanceIdentifier"] = instance.uuid
            instance_item["DbiResourceId"] = ""
            instance_item["nvl-resourceId"] = instance.resource_uuid
            instance_item["StorageType"] = config.get("StorageType")
            instance_item["LicenseModel"] = ""
            instance_item["MasterUsername"] = config.get("MasterUsername")
            instance_item["nvl-name"] = instance.name
            instance_item["StatusInfos"] = [{"Status": self.state_mapping(status, resource.get("runstate"))}]
            instance_item["nvl-stateReason"] = {"nvl-code": None, "nvl-message": None}
            if instance.status == "ERROR":
                instance_item["nvl-stateReason"] = {
                    "nvl-code": "400",
                    "nvl-message": instance.last_error,
                }

        elif api_version == "v2.0":
            instance_item["DBInstanceIdentifier"] = instance.name
            instance_item["DbiResourceId"] = instance.uuid
            instance_item["nvl-resourceId"] = instance.resource_uuid
            instance_item["StorageType"] = attributes.get("volume_flavor")
            instance_item["LicenseModel"] = attributes.get("license", "general-public-license")
            
            admin_user = attributes.get("admin_user")
            if admin_user is None:
                admin_user = config.get("MasterUsername")
            else:
                # fix structure dict MasterUsername of some old ComputeStack
                if "pwd" not in admin_user:
                    new_admin_user = {}
                    new_admin_user["pwd"] = admin_user
                    admin_user = new_admin_user
            instance_item["MasterUsername"] = admin_user

            instance_item["StatusInfos"] = []
            # instance_item['nvl_keyName'] = config.get('Nvl_KeyName')
            instance_item["nvl-stateReason"] = []
            if instance.status == "ERROR":
                instance_item["nvl-stateReason"].append({"nvl-code": "400", "nvl-message": instance.last_error})

        instance_item["AllocatedStorage"] = allocated_storage
        instance_item["AvailabilityZone"] = avzone
        instance_item["MultiAZ"] = False
        # if config.get('BackupRetentionPeriod', None) is not None:
        #     instance_item['BackupRetentionPeriod'] = int(config.get('BackupRetentionPeriod', -1))
        # instance_item['CACertificateIdentifier'] = ''OptionGroupMemberships
        instance_item["CharacterSetName"] = charset
        instance_item["Timezone"] = timezone
        instance_item["DBInstanceClass"] = self.get_db_type()  # self.instance_type.name
        instance_item["DbInstancePort"] = port_number
        instance_item["DBInstanceStatus"] = self.state_mapping(status, resource.get("runstate"))
        # instance_item['DBName'] = config.get('DBName')
        instance_item["DBName"] = dbname
        instance_item["Endpoint"] = {"Address": address, "Port": port_number}
        instance_item["Engine"] = engine
        instance_item["EngineVersion"] = version
        instance_item["InstanceCreateTime"] = format_date(instance.model.creation_date)
        instance_item["TagList"] = []

        instance_item["PreferredBackupWindow"] = config.get("PreferredBackupWindow")
        instance_item["PreferredMaintenanceWindow"] = config.get("PreferredMaintenanceWindow")
        instance_item["ReadReplicaDBClusterIdentifiers"] = []
        instance_item["ReadReplicaDBInstanceIdentifiers"] = []
        instance_item["ReadReplicaSourceDBInstanceIdentifier"] = ""
        instance_item["SecondaryAvailabilityZone"] = ""
        instance_item["StorageEncrypted"] = config.get("StorageEncrypted")
        instance_item["DBSubnetGroup"] = {
            "DBSubnetGroupDescription": getattr(subnet, "desc", ""),
            "DBSubnetGroupName": getattr(subnet, "name", ""),
            "SubnetGroupStatus": getattr(subnet, "status", ""),
            "Subnets": [
                {
                    "SubnetAvailabilityZone": {"AvailabilityZone": {"Name": avzone}},
                    "SubnetIdentifier": getattr(subnet, "uuid", ""),
                    "SubnetStatus": getattr(subnet, "status", ""),
                }
            ],
            "VpcId": subnet_vpc_id,
        }

        # get security groups from resource
        sgs = resource.get("security_groups", [])

        instance_item["VpcSecurityGroups"] = []
        security_group_idx = self.security_group_idx
        if sgs is not None:
            for sg in sgs:
                sg_obj = security_group_idx.get(sg["uuid"])
                sg_name = None
                sg_uuid = sg["uuid"]
                if sg_obj is not None:
                    sg_name = sg_obj.name
                    sg_uuid = sg_obj.uuid
                instance_item["VpcSecurityGroups"].append(
                    {
                        "VpcSecurityGroupMembership": {
                            "VpcSecurityGroupId": sg_uuid,
                            "Status": None,
                            "nvl-vpcSecurityGroupName": sg_name,
                        }
                    }
                )

        # custom params
        account = self.account
        instance_item["nvl-ownerAlias"] = account.name
        instance_item["nvl-ownerId"] = account.uuid
        instance_item["nvl-hypervisor"] = hypervisor

        monitoring_enabled = dict_get(resource, "attributes.monitoring_enabled", default=False)
        instance_item["monitoring_enabled"] = monitoring_enabled

        return instance_item
    
    def aws_simple_info(self):
        instance_item = {}

        # get config
        config = self.get_config("dbinstance")
        if config is None:
            config = {}

        avzone = self.avzone

        if self.resource is None:
            self.resource = {}

        resource = self.resource
        attributes = resource.get("attributes", {})
        engine = attributes.get("engine")
        version = attributes.get("version")
        outputs = attributes.get("outputs")
        # hypervisor = attributes.get("hypervisor")
        # allocated_storage = int(config.get("AllocatedStorage", -1))
        # select correct resource stack version
        # new resource stack v2
        # self.logger.info(f"fv - aws_simple_info - outputs: {outputs}")
        if outputs is not None:
            # replica = attributes.get('replica')
            address = dict_get(resource, "listener.address")
            port = dict_get(resource, "listener.port")

        # old resource stack v1
        else:
            stacks = resource.get("stacks", [])
            # self.logger.info(f"fv - aws_simple_info - stacks: {stacks}")
            # replica = config.get('MultiAZ')
            # resource stack ref
            avz_main_stack = {}
            if len(stacks) > 0:
                avz_main_stack = stacks[0]
            address, port = None, None
            if avz_main_stack.get("listener", ":") is not None:
                address, port = avz_main_stack.get("listener", ":").split(":")
        
        dbname = ""
        if engine == "mysql":
            dbname = "%s:%s" % (address, port)
        elif engine == "mariadb":
            dbname = "%s:%s" % (address, port)
        elif engine == "postgresql":
            dbname = dict_get(attributes, "postgres:database")
        elif engine == "oracle":
            dbname = dict_get(attributes, "oracle:sid")

        port_number = None
        if port is not None and port != "":
            port_number = port

        # get instance and resource status
        instance = self.instance
        status = instance.status
        if resource.get("state") == "ERROR":
            status = "ERROR"

        instance_item["DBInstanceIdentifier"] = instance.name
        instance_item["DbiResourceId"] = instance.uuid
        # instance_item["nvl-resourceId"] = instance.resource_uuid

        admin_user = attributes.get("admin_user")
        if admin_user is None:
            admin_user = config.get("MasterUsername")
        else:
            # fix structure dict MasterUsername of some old ComputeStack
            if "pwd" not in admin_user:
                new_admin_user = {}
                new_admin_user["pwd"] = admin_user
                admin_user = new_admin_user
        instance_item["MasterUsername"] = admin_user

        instance_item["AvailabilityZone"] = avzone

        instance_item["DbInstancePort"] = port_number
        # instance_item["DBInstanceStatus"] = self.state_mapping(status, resource.get("runstate"))
        instance_item["DBInstanceStatus"] = self.state_mapping(status, attributes.get("last_runstate"))
        instance_item["DBName"] = dbname
        instance_item["Endpoint"] = {"Address": address, "Port": port_number}

        instance_item["Engine"] = engine
        instance_item["EngineVersion"] = version
        instance_item["InstanceCreateTime"] = format_date(instance.model.creation_date)
        instance_item["TagList"] = []

        # custom params
        account = self.account
        instance_item["nvl-ownerAlias"] = account.name
        instance_item["nvl-ownerId"] = account.uuid

        from beehive_service.controller.api_division import ApiDivision
        division: ApiDivision = self.division
        if division:
            instance_item["nvl-divisionAlias"] = division.name
            instance_item["nvl-divisionId"] = division.uuid

        return instance_item

    def _get_postgresql_parameters(self, data_instance: dict) -> dict:
        """Get Optional postgrsql parameters

        Args:
            data_instance (dict): _description_

        Returns:
            dict: _description_
        """
        postgresql_db_options = data_instance.get("Nvl_Postgresql_Options", {})
        geo_extension = postgresql_db_options.get("Postgresql_GeoExtension", True)
        encoding = postgresql_db_options.get("pg_encoding", "UTF-8")
        lc_collate = postgresql_db_options.get("pg_lc_collate", "en_US.UTF-8")
        lc_ctype = postgresql_db_options.get("pg_lc_ctype", "en_US.UTF-8")
        db_name = postgresql_db_options.get("pg_db_name", None)
        role_name = postgresql_db_options.get("pg_role_name", None)
        password = postgresql_db_options.get("pg_password", None)
        schema_name = postgresql_db_options.get("pg_schema_name", None)
        extensions = ",".join(postgresql_db_options.get("pg_extensions", []))
        pg_starter_pack = "N"
        if role_name is not None:
            pg_starter_pack = "Y"
        else:
            if password is not None:
                raise ApiManagerError("schema password is required for schema creation")
        return {
            "postgresql_params": {
                "geo_extension": geo_extension,
                "encoding": encoding,
                "lc_collate": lc_collate,
                "lc_ctype": lc_ctype,
                "db_name": db_name,
                "role_name": role_name,
                "password": password,
                "schema_name": schema_name,
                "extensions": extensions,
                # "starter_pack": pg_starter_pack,
            }
        }

    def _get_oracle_parameters(self, data_instance: dict, engine_params: dict) -> dict:
        """Get Optional Oracle paramenters

        Args:
            data_instance (dict): _description_

        Returns:
            dict: _description_
        """
        oracle_db_options = data_instance.get("Nvl_Oracle_Options", {})

        ora_dbname = oracle_db_options.get("ora_dbname", "ORCL0")
        ora_dbnatcharset = oracle_db_options.get("ora_natcharset", "AL16UTF16")
        ora_dbarchmode = oracle_db_options.get("ora_archmode", "Y")
        ora_dbpartopt = oracle_db_options.get("ora_partopt", "Y")
        ora_charset = oracle_db_options.get("ora_charset", "WE8ISO8859P1")
        ora_dblistenerport = oracle_db_options.get("ora_lsnport", 1521)

        # ora_dbdbfdisksize: nessun default, eredita default di AllocatedStorage,
        # definito come missing=30 in resource 'data_disk_size'
        ora_dbdbfdisksize = oracle_db_options.get("ora_dbfdisksize")

        ora_dbrecoverydisksize = oracle_db_options.get("ora_recodisksize", 30)

        # get oracle os user
        ora_os_user = dict_get(engine_params, "os_dbuser")

        # Oracle constants
        # ora_dbfpath = data_instance.get('OracleDBDatafilePath')
        # ora_dbbckbasepath = data_instance.get('OracleDBRecoveryBaseFilePath')
        # collect starter pack info
        ora_user_name = oracle_db_options.get("ora_user_name", "--")
        ora_user_pwd = oracle_db_options.get("ora_user_pwd", "--")
        ora_data_tbs_name = oracle_db_options.get("ora_data_tbs_name", "--")
        ora_data_tbs_next = oracle_db_options.get("ora_data_tbs_next", "--")
        ora_data_tbs_size = oracle_db_options.get("ora_data_tbs_size", "--")
        ora_idx_tbs_name = oracle_db_options.get("ora_idx_tbs_name", "--")
        ora_idx_tbs_next = oracle_db_options.get("ora_idx_tbs_next", "--")
        ora_idx_tbs_size = oracle_db_options.get("ora_idx_tbs_size", "--")
        ora_lob_tbs_name = oracle_db_options.get("ora_lob_tbs_name", "--")
        ora_lob_tbs_next = oracle_db_options.get("ora_lob_tbs_next", "--")
        ora_lob_tbs_size = oracle_db_options.get("ora_lob_tbs_size", "--")

        try:
            ## check there is still room for tablespaces
            tsize = 0
            if ora_data_tbs_size != "--":
                tsize += int(ora_data_tbs_size[:-1])
            if ora_idx_tbs_size != "--":
                tsize += int(ora_idx_tbs_size[:-1])
            if ora_lob_tbs_size != "--":
                tsize += int(ora_lob_tbs_size[:-1])
            tsize = tsize / 1024

            if tsize > int(data_instance.get("AllocatedStorage")):
                raise ApiManagerError("no room for tablespace in alocated storage")
        except Exception:
            pass

        ora_starter_pack = "Y"
        if ora_user_name == "--":
            ora_starter_pack = "N"
        else:
            if ora_user_pwd == "--":
                raise ApiManagerError("schema password is required for schema creation")

        return {
            "oracle_params": {
                "oracle_db_name": ora_dbname,
                "oracle_charset": ora_charset,
                "oracle_natcharset": ora_dbnatcharset,
                "oracle_archivelog_mode": ora_dbarchmode,
                "oracle_partitioning_option": ora_dbpartopt,
                "oracle_listener_port": ora_dblistenerport,
                "oracle_data_disk_size": ora_dbdbfdisksize,
                "oracle_bck_disk_size": ora_dbrecoverydisksize,
                "oracle_os_user": ora_os_user,
                "oracle_starter_pack": ora_starter_pack,
                "oracle_user_name": ora_user_name,
                "oracle_user_pwd": ora_user_pwd,
                "oracle_data_tbs_name": ora_data_tbs_name,
                "oracle_data_tbs_next": ora_data_tbs_next,
                "oracle_data_tbs_size": ora_data_tbs_size,
                "oracle_idx_tbs_name": ora_idx_tbs_name,
                "oracle_idx_tbs_next": ora_idx_tbs_next,
                "oracle_idx_tbs_size": ora_idx_tbs_size,
                "oracle_lob_tbs_name": ora_lob_tbs_name,
                "oracle_lob_tbs_next": ora_lob_tbs_next,
                "oracle_lob_tbs_size": ora_lob_tbs_size,
            }
        }

    def pre_create(self, **params):
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id

        # base quotas
        quotas = {
            "database.cores": 0,
            "database.instances": 1,
            "database.ram": 0,
        }

        # get container
        container_id = self.get_config("container")
        flavor_resource_uuid = self.get_config("flavor")
        compute_zone = self.get_config("computeZone")
        data_instance = self.get_config("dbinstance")
        engine_params = self.get_config("engine")
        hypervisor = engine_params.get("hypervisor")
        if engine_params is None:
            engine_params = {}
        self.logger.debug("+++++ engine_params: %s", engine_params)
        image_engine = engine_params.get("image")
        self.logger.debug("+++++ image_engine: %s", image_engine)

        # check all parameters are present
        keys_check: Union[None, List[str]] =  engine_params.get("check")
        if isinstance(keys_check, list):
            for key in keys_check:
                if isinstance(key, str) :
                    if dict_get(engine_params, key) is None:
                        raise ApiManagerError (f"parmeter {key} not set")
                    
        
        # get resource image
        image_resource = self.get_image(image_engine)
        image_configs = image_resource.get("attributes", {}).get("configs", {})
        # image_volume_size = image_configs.get("min_disk_size")
        image_ram_size_gb = image_configs.get("min_ram_size", 0)
        self.logger.debug("+++++ image_ram_size_gb: %s", image_ram_size_gb)

        # get Flavor resource Info
        flavor_resource = self.get_flavor(flavor_resource_uuid)

        # try to get main volume size from flavor
        flavor_configs = flavor_resource.get("attributes", None).get("configs", None)
        quotas["database.cores"] = flavor_configs.get("vcpus", 0)
        quotas["database.ram"] = flavor_configs.get("memory", 0)
        if quotas["database.ram"] > 0:
            quotas["database.ram"] = quotas["database.ram"] / 1024
        root_disk_size = flavor_configs.get("disk", 40)

        flavor_memory = flavor_configs.get("memory", 0)
        self.logger.debug("+++++ flavor_memory: %s", flavor_memory)
        image_ram_size_mb = image_ram_size_gb * 1024
        if flavor_memory < image_ram_size_mb:
            raise ApiManagerError(
                "Minimum memory required is %s GB - flavor memory: %s MB" % (image_ram_size_gb, flavor_memory)
            )

        # get availability zone from request parameters
        av_zone = data_instance.get("AvailabilityZone", None)

        # check subnet
        subnet_id = data_instance.get("DBSubnetGroupName", None)
        if subnet_id is None:
            raise ApiManagerError("Subnet is not defined")

        subnet_inst = self.controller.check_service_instance(subnet_id, ApiComputeSubnet, account=account_id)
        subnet_name = subnet_inst.name
        if av_zone is None:
            subnet_inst.get_main_config()
            av_zone = subnet_inst.get_config("site")

        # check availability zone status
        if self.is_availability_zone_active(compute_zone, av_zone) is False:
            raise ApiManagerError("Availability zone %s is not in available status" % av_zone)

        # get and check the id SecurityGroupId
        security_group_ress = []
        for security_group in data_instance.get("VpcSecurityGroupIds", {}).get("VpcSecurityGroupId", []):
            sg_inst = self.controller.check_service_instance(
                security_group, ApiComputeSecurityGroup, account=account_id
            )
            if sg_inst.resource_uuid is None:
                raise ApiManagerError("SecurityGroup id %s is invalid" % security_group)
            security_group_ress.append(sg_inst.resource_uuid)

            # link security group to db instance
            self.instance.add_link(
                name="link-%s-%s" % (self.instance.oid, sg_inst.oid),
                type="sg",
                end_service=sg_inst.oid,
                attributes={},
            )

        if len(security_group_ress) == 0:
            raise ApiManagerError("VpcSecurityGroupId is not correct")

        # get vpc
        vpc_resource_uuid = self.controller.get_service_instance(
            subnet_inst.model.linkParent[0].start_service_id
        ).resource_uuid
        uri = f"/v2.0/nrs/provider/vpcs/{vpc_resource_uuid}/available-ips"
        data = {"orchestrator_type": hypervisor, "site": av_zone}
        res = self.controller.api_client.admin_request("resource", uri, "get", data=data)
        available_ips = res.get("available_ips")
        if available_ips is not None:
            available_ips = int(available_ips)
            if available_ips <= 0:
                msg = f"""\
No more available ips on subnet {subnet_name} for hypervisor {hypervisor} due to full allocation; \
consider requesting a new subnet or selecting another one.
        """
                raise ApiManagerError(msg)
        else:
            msg = "Failed to retrieve available IP count for %s on %s. Attempting to proceed."
            self.logger.warning(msg, subnet_name, hypervisor)

        # get engine name and version
        engine = data_instance.get("Engine")
        engine_version = data_instance.get("EngineVersion")
        if engine_version.find("-") > 0:
            engine_version = engine_version.split("-")[0]
        replica = data_instance.get("MultiAZ", False)
        if replica:
            av_zone = None

        # get params for given engine and version
        host_group = engine_params.get("host_group")
        volume_flavor = engine_params.get("volume_flavor")
        image = engine_params.get("image")
        customization = engine_params.get("customization")

        # bypass key for pgsql engine
        if engine == "sqlserver":
            key_name = None
            self.set_config("dbinstance.Nvl_KeyName", key_name)
        else:
            # get key name
            key_name = data_instance.get("Nvl_KeyName", None)
            # get key name from database definition
            if key_name is None:
                key_name = engine_params.get("key_name")
                self.set_config("dbinstance.Nvl_KeyName", key_name)
            else:
                ApiComputeKeyPairsHelper(self.controller).check_service_instance(key_name, account_id)

        charset = data_instance.get("CharacterSetName", "latin1")
        timezone = data_instance.get("Timezone", "Europe/Rome")
        port = data_instance.get("Port")

        # get lvm parameters
        lvm_vg_data = dict_get(engine_params, "lvm.volume_group.data")
        lvm_vg_backup = dict_get(engine_params, "lvm.volume_group.backup")
        lvm_lv_data = dict_get(engine_params, "lvm.logical_volume.data")
        lvm_lv_backup = dict_get(engine_params, "lvm.logical_volume.backup")

        # get mount points
        data_dir = dict_get(engine_params, "mount_point.data")
        backup_dir = dict_get(engine_params, "mount_point.backup")

        # name = '%s-%s' % (self.instance.name, id_gen(length=8))
        name = self.instance.name
        hostname = name
        if engine == "sqlserver" and len(hostname) > 15:
            hostname = name[0:15]

        db_root_password = data_instance.get("MasterUserPassword", None)

        if db_root_password is not None:
            pass
            # todo: check password complexity

        subnet = subnet_inst.get_config("cidr")

        # check if subnet is global or private
        if IPv4Network(subnet).is_private is False:
            raise ApiManagerError("db instance can not be created on public subnet")

        # set options
        options = {
            "enable_mailx": engine_params.get("enable_mailx", False),
            "register_on_haproxy": engine_params.get("register_on_haproxy", False),
        }

        data = {
            "name": name,
            "desc": name,
            "container": container_id,
            "compute_zone": compute_zone,
            "availability_zone": av_zone,
            "flavor": flavor_resource_uuid,
            "volume_flavor": volume_flavor,
            "image": image,
            "vpc": vpc_resource_uuid,
            "subnet": subnet,
            "security_group": security_group_ress[0],
            # 'db_name': dbname,
            "replica": replica,
            "charset": charset,
            "timezone": timezone,
            "port": port,
            # 'db_appuser_name': db_appuser_name,
            # 'db_appuser_password': db_appuser_password,
            # 'db_root_name': db_root_name,
            "db_root_password": db_root_password,
            "key_name": key_name,
            "version": engine_version,
            "engine": engine,
            "root_disk_size": root_disk_size,
            "data_disk_size": data_instance.get("AllocatedStorage"),
            "resolve": True,
            "hostname": hostname,
            "host_group": host_group,
            "customization": customization,
            "hypervisor": hypervisor,
            "options": options,
            "lvm_vg_data": lvm_vg_data,
            "lvm_vg_backup": lvm_vg_backup,
            "lvm_lv_data": lvm_lv_data,
            "lvm_lv_backup": lvm_lv_backup,
            "data_dir": data_dir,
            "backup_dir": backup_dir,
        }

        if engine == "postgresql":
            data.update(self._get_postgresql_parameters(data_instance=data_instance))
        elif engine == "oracle":
            data.update(self._get_oracle_parameters(data_instance=data_instance, engine_params=engine_params))

        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    #
    # import
    #
    def pre_import(self, **params) -> dict:
        """Check input params before resource import. Use this to format parameters for service creationg1596
        Extend this function to manipulate and validate create input params.

        Service instance config is populated with: owner_id, service_definition_id, computeZone

        :param params: input params
        :param params.id: inst.oid,
        :param params.uuid: inst.uuid,
        :param params.objid: inst.objid,
        :param params.name: name,
        :param params.desc: desc,
        :param params.attribute: None,
        :param params.tags: None,
        :param params.resource_id: resource_id
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id

        # get resource
        resource = self.get_resource(uuid=params.get("resource_id"))
        resource_uuid = dict_get(resource, "uuid")
        compute_zone = dict_get(resource, "parent")
        attributes = resource.get("attributes", {})
        flavor_resource_uuid = dict_get(resource, "flavor.uuid")
        availability_zone_name = dict_get(resource, "availability_zone.name")
        vpc_resource_id = dict_get(resource, "vpc")
        security_group_resources = dict_get(resource, "security_groups")
        engine = attributes.get("engine")
        engine_version = attributes.get("version")

        # get vpc, subnets child of the vpc and security group
        vpc_si = self.controller.get_service_instance_by_resource_uuid(vpc_resource_id["uuid"], plugintype="ComputeVPC")
        subnet_sis, tot = self.controller.get_paginated_service_instances(
            account_id=account_id,
            filter_expired=False,
            plugintype="ComputeSubnet",
            with_perm_tag=False,
            size=-1,
        )

        subnet_si = None
        for subnet in subnet_sis:
            vpc_id = subnet.get_config("subnet.VpcId")
            subnet_availability_zone_name = subnet.get_config("subnet.AvailabilityZone")
            self.logger.warning(vpc_resource_id["uuid"])
            self.logger.warning(vpc_id)
            self.logger.warning(vpc_si.uuid)
            self.logger.warning(subnet.uuid)
            self.logger.warning(subnet_availability_zone_name)
            self.logger.warning(availability_zone_name)
            if vpc_id == vpc_si.uuid and subnet_availability_zone_name == availability_zone_name:
                subnet_si = subnet
                break

        if subnet_si is None:
            raise ApiManagerError("no valid subnet found")

        security_group_si = self.controller.get_service_instance_by_resource_uuid(security_group_resources[0]["uuid"])

        params["resource_id"] = resource_uuid

        # get Flavor resource Info
        flavor_resource = self.get_flavor(flavor_resource_uuid)
        # try to get main volume size from flavor
        flavor_configs = flavor_resource.get("attributes", None).get("configs", None)

        # base quotas
        quotas = {
            "database.cores": flavor_configs.get("vcpus", 0),
            "database.instances": 1,
            "database.ram": flavor_configs.get("memory", 0) / 1024,
        }
        # self.check_quotas(compute_zone, quotas)

        # get service definition with engine configuration
        engine_def_name = "db-engine-%s-%s" % (engine, engine_version)
        engine_defs, tot = self.controller.get_paginated_service_defs(name=engine_def_name)
        if len(engine_defs) < 1 or len(engine_defs) > 1:
            raise ApiManagerError("Engine %s with version %s was not found" % (engine, engine_version))

        # add engine config
        self.instance.set_config("engine", engine_defs[0].get_main_config().params)

        # setup dbinstance config
        dbinstance_params = {
            "Timezone": attributes.get("timezone"),
            "DBInstanceClass": self.instance.get_config("flavor"),
            "EngineVersion": engine_version,
            "DBInstanceIdentifier": self.instance.name,
            "Port": None,
            "AccountId": self.instance.get_config("owner_id"),
            "Timezone": attributes.get("timezone"),
            "CharacterSetName": attributes.get("charset"),
            "Engine": engine,
            "MultiAZ": False,
            "DBSubnetGroupName": subnet_si.uuid,
            "VpcSecurityGroupIds.VpcSecurityGroupId.0": security_group_si.uuid,
            "AllocatedStorage": attributes.get("allocated_storage"),
            "Nvl_KeyName": None,
        }
        self.instance.set_config("dbinstance", dbinstance_params)

        self.logger.warn(self.instance.config_object.json_cfg)

        return params

    def post_import(self, **params):
        """Post import function. Use this after service creation.
        Extend this function to execute some operation after entity was created.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        # get resource
        resource = self.get_resource(uuid=params.get("resource_id"))

        # link security groups
        security_group_resources = dict_get(resource, "security_groups")
        for sg in security_group_resources:
            sg_inst = self.controller.get_service_instance_by_resource_uuid(sg["uuid"])

            # link security group to db instance
            self.instance.add_link(
                name="link-%s-%s" % (self.instance.oid, sg_inst.oid),
                type="sg",
                end_service=sg_inst.oid,
                attributes={},
            )

        return None

    def pre_update(self, **params):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # change instance type
        service_definition_id = params.pop("DBInstanceClass", None)
        if service_definition_id is not None:
            ext_params = self.set_instance_type(service_definition_id)
            params.update(ext_params)

        # change security group
        security_groups = params.pop("VpcSecurityGroupIds", {}).pop("VpcSecurityGroupId", None)
        if security_groups is not None:
            actions = []
            for action in security_groups:
                action_param = self.change_security_group(action)
                actions.append(action_param)
            ext_params = {"resource_params": {"actions": actions}}
            params.update(ext_params)

        # resize storage
        allocated_storage = params.pop("AllocatedStorage", None)
        if allocated_storage is not None:
            ext_params = self.resize_storage(allocated_storage)
            params.update(ext_params)

        # install extensions
        extensions = params.pop("Extensions", [])
        if extensions:
            ext_params = self.install_extensions(extensions)
            params.update(ext_params)

        # # manage instance user: add, delete, change password
        # user_params = params.pop('Nvl_User', None)
        # if user_params is not None:
        #     ext_params = self.manage_user(user_params)
        #     params.update(ext_params)

        self.logger.debug("pre-update params: %s" % params)

        return params

    #
    # action
    #
    def set_instance_type(self, instance_type):
        """Set instance type

        :param instance_type: instance type
        :return: action params
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        # check hypervisor
        # type_provider = self.get_config('type')
        # if type_provider == 'vsphere':
        #     raise ApiManagerError('Instance type change is not already supported for provider %s' % type_provider)

        # check instance status
        if self.get_runstate() in ["poweredOn", "poweredOff"]:
            try:
                self.instance.change_definition(instance_type)
            except ApiManagerError as ex:
                self.logger.warning(ex)
                raise ApiManagerError("Instance_type does not change. Select a new one")

            flavor = self.instance.config_object.json_cfg.get("flavor")
            def_uuid = self.instance.controller.get_service_def(instance_type).uuid
            self.instance.config_object.set_json_property("dbinstance.DBInstanceClass", def_uuid)
            params = {"resource_params": {"action": {"name": "set_flavor", "args": {"flavor": flavor}}}}
            self.logger.info("Set instance %s type" % self.instance.uuid)
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)
        return params

    def change_security_group(self, security_group):
        """Change security group

        :param security_group: security group
        :return: action params
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        security_group, action = security_group.split(":")
        action = action.upper()
        security_group = self.controller.get_service_type_plugin(
            security_group, plugin_class=ApiComputeSecurityGroup, details=False
        )

        action_param = None

        # get active security groups
        sgs = [sg["uuid"] for sg in self.resource.get("security_groups", [])]
        attached = security_group.resource_uuid in sgs

        if attached is True and action == "DEL":
            if len(sgs) == 1:
                raise ApiManagerError("Can't delete security group. Database %s must have al least one security group" % (self.instance.uuid))

            action_param = {
                "name": "del_security_group",
                "args": {"security_group": security_group.resource_uuid},
            }
        elif attached is False and action == "DEL":
            raise ApiManagerError(
                "security group %s is not attached to instance %s" % (security_group.instance.uuid, self.instance.uuid)
            )
        elif attached is True and action == "ADD":
            raise ApiManagerError(
                "security group %s is already attached to instance %s"
                % (security_group.instance.uuid, self.instance.uuid)
            )
        elif attached is False and action == "ADD":
            action_param = {
                "name": "add_security_group",
                "args": {"security_group": security_group.resource_uuid},
            }
        return action_param

    def resize_storage(self, allocated_storage):
        """Resize storage

        :param allocated_storage: the new amount of storage (in GiB) to allocate to the DB instance
        :return: action params
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        # check instance status
        if self.get_runstate() in ["poweredOn", "poweredOff"]:
            params = {
                "resource_params": {
                    "action": {
                        "name": "resize",
                        "args": {"new_data_disk_size": allocated_storage},
                    }
                }
            }
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)

        return params

    def install_extensions(self, extensions):
        """Install extensions

        :param extensions: list of extension names
        :return: action params
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported(action="install_extensions")

        # check instance status
        if self.get_runstate() in ["poweredOn", "poweredOff"]:
            extensions = [{"name": extension.get("Name"), "type": extension.get("Type")} for extension in extensions]
            params = {
                "resource_params": {
                    "action": {
                        "name": "install_extensions",
                        "args": {"extensions": extensions},
                    }
                }
            }
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)

        return params

    def start(self, schedule=None):
        """Start instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        # check instance status
        if self.get_runstate() == "poweredOff":
            params = {"resource_params": {"action": {"name": "start", "args": True}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Start db instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Db instance %s is already started" % self.instance.uuid)
        return res

    def stop(self, schedule=None):
        """Stop instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        # check instance status
        if self.get_runstate() == "poweredOn":
            params = {"resource_params": {"action": {"name": "stop", "args": {"force": False}}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Stop db instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Db instance %s is already stopped" % self.instance.uuid)
        return res

    def reboot(self, schedule=None):
        """Reboot instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        # check instance status
        if self.get_runstate() == "poweredOn":
            params = {"resource_params": {"action": {"name": "restart", "args": True}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Reboot db instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Db instance %s is not in a correct state" % self.instance.uuid)
        return res

    def enable_monitoring(self, templates):
        """Enable monitoring

        :param templates: templates
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "enable_monitoring",
                    "args": {"templates": templates},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("Enable monitoring on db instance %s" % self.instance.uuid)
        return res

    def disable_monitoring(self):
        """Disable monitoring

        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {"resource_params": {"action": {"name": "disable_monitoring", "args": {}}}}
        res = self.update(**params)
        self.logger.info("Disable monitoring on db instance %s" % self.instance.uuid)
        return res

    def disable_resource_monitoring(self, task):
        """Disable resource monitoring. Invoked by delete_resource()

        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        :return:
        """
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"disable_monitoring": {"deregister_only": True}}}
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Disable monitoring on db instance %s" % self.instance.uuid)

    def enable_logging(self, files, pipeline):
        """Enable log forwarding

        :param files: log files to be forwarded
        :param pipeline: log collector port number
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "enable_logging",
                    "args": {"files": files, "logstash_port": pipeline},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("Enable logging on db instance %s" % self.instance.uuid)
        return res

    def enable_mailx(self, task):
        """Provide the ability to send email through mailx client

        :param task: celery task reference
        """
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"enable_mailx": {"relayhost": None}}}
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Enable mailx on db instance %s" % self.instance.uuid)

    def register_on_haproxy(self, task):
        """Register db instance on haproxy

        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        """
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"haproxy_register": {}}}
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Register db instance %s on haproxy" % self.instance.uuid)

    def deregister_from_haproxy(self, task):
        """Deregister db instance from haproxy
        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        """
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"haproxy_deregister": True}}
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Deregister db instance %s from haproxy" % self.instance.uuid)

    def get_schemas(self):
        """get schemas

        :return: schema list
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        res = self.get_resource_dbs()
        return res

    def create_schema(self, name, charset):
        """create schema

        :param name: schema name
        :param charset: schema charset
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "add_db",
                    "args": {"db_name": name, "charset": charset},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("Create schema %s on db instance %s" % (name, self.instance.uuid))
        return res

    def remove_schema(self, name):
        """remove schema

        :param name: schema name
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {"resource_params": {"action": {"name": "drop_db", "args": {"db_name": name}}}}
        res = self.update(**params)
        self.logger.info("Remove schema %s from db instance %s" % (name, self.instance.uuid))
        return res

    def get_users(self):
        """get users

        :return: user list
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        res = self.get_resource_users()
        return res

    def create_user(self, name, password):
        """create user

        :param name: user name
        :param password: user password
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "add_user",
                    "args": {"name": name, "password": password},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("Create user %s on db instance %s" % (name, self.instance.uuid))
        return res

    def remove_user(self, name, force):
        """remove user

        :param name: user name
        :param force: force deletion
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {"resource_params": {"action": {"name": "drop_user", "args": {"name": name, "force": force}}}}
        res = self.update(**params)
        self.logger.info("Remove user %s from db instance %s" % (name, self.instance.uuid))
        return res

    def check_priv_string(self, db, privileges):
        """Check if privileges are allowed for engine type and database

        :param db: database
        :param privileges: string privileges
        :return:
        """
        # check the action is supported by engine
        self.check_supported()

        # select correct resource stack version
        resource = self.get_resource()
        attributes = resource.get("attributes", {})
        engine = attributes.get("engine", None)
        if engine == "mysql":
            allowed_privileges = ["SELECT", "INSERT", "DELETE", "UPDATE", "ALL"]
        elif engine == "mariadb":
            allowed_privileges = ["SELECT", "INSERT", "DELETE", "UPDATE", "ALL"]
        elif engine == "postgresql":
            db = db.split(".")
            if len(db) == 1:
                allowed_privileges = ["CONNECT"]
            elif len(db) == 2:
                if db[1] == "information_schema" or db[1].find("pg_") >= 0:
                    raise ApiManagerError("Postgres schema %s can not be grant" % db[1])
                allowed_privileges = ["USAGE", "CREATE", "ALL"]
            else:
                raise ApiManagerError("Bad database.schema format")
        else:
            allowed_privileges = []

        for p in privileges.split(","):
            if p.upper() not in allowed_privileges:
                raise ApiManagerError("Allowed privileges are %s" % allowed_privileges)

    def grant_privs(self, db, user, privileges):
        """grant privileges

        :param db: schema name
        :param user: user name
        :param privileges: privileges string like SELECT,INSERT,DELETE,UPDATE or ALL
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "grant_privs",
                    "args": {"db_name": db, "usr_name": user, "privileges": privileges},
                }
            }
        }
        res = self.update(**params)
        self.logger.info(
            "Grant privileges %s to user %s on db %s for db instance %s" % (privileges, db, user, self.instance.uuid)
        )
        return res

    def revoke_privs(self, db, user, privileges):
        """revoke privileges

        :param db: schema name
        :param user: user name
        :param privileges: privileges string like SELECT,INSERT,DELETE,UPDATE or ALL
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "revoke_privs",
                    "args": {"db_name": db, "usr_name": user, "privileges": privileges},
                }
            }
        }
        res = self.update(**params)
        self.logger.info(
            "Revoke privileges %s to user %s on db %s for db instance %s" % (privileges, db, user, self.instance.uuid)
        )
        return res

    def change_pwd(self, user, pwd):
        """change password

        :param user: user name
        :param pwd: user password
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check the action is supported by engine
        self.check_supported()

        params = {
            "resource_params": {
                "action": {
                    "name": "change_pwd",
                    "args": {"name": user, "new_password": pwd},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("Change password to user %s for db instance %s" % (user, self.instance.uuid))
        return res

    def get_runstate(self):
        """Get resource runstate

        :return: resource runstate
        :rtype: str
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.get_status() not in ["ACTIVE", "ERROR"]:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)

        resource = self.get_resource()
        runstate = resource.get("runstate")
        self.logger.debug("Get instance %s runstate: %s" % (self.instance.uuid, runstate))
        return runstate

    @trace(op="view")
    def get_resource(self, uuid=None):
        """Get resource info

        :param uuid: resource uuid [optional]
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        instance = None
        if uuid is None:
            uuid = self.instance.resource_uuid
        if uuid is not None:
            try:
                uri = "/v2.0/nrs/provider/sql_stacks/%s" % uuid
                instance = self.controller.api_client.admin_request("resource", uri, "get", data="").get("sql_stack")
                self.sql_stack_version = "v2.0"
            except:
                uri = "/v1.0/nrs/provider/sql_stacks/%s" % uuid
                instance = self.controller.api_client.admin_request("resource", uri, "get", data="").get("sql_stack")
                self.sql_stack_version = "v1.0"

        self.logger.debug("Get sql stack resource: %s" % truncate(instance))
        return instance

    @trace(op="view")
    def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=-1):
        """Get resource info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if zones is None:
            zones = []
        if uuids is None:
            uuids = []
        if tags is None:
            tags = []
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)

        encoded_data = data = urlencode(data)
        api_client = self.controller.api_client

        # query new api
        instances = api_client.admin_request("resource", "/v2.0/nrs/provider/sql_stacks", "get", data=encoded_data).get(
            "sql_stacks", []
        )

        # query old api - remove when all the sql stack are migrated
        instances += api_client.admin_request(
            "resource", "/v1.0/nrs/provider/sql_stacks", "get", data=encoded_data
        ).get("sql_stacks", [])

        self.controller.logger.debug("Get sql stack resources: %s" % truncate(instances))
        return instances
    
    @trace(op="view")
    def list_simple_resources(self, uuids=None, page=0, size=-1, **kvargs):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            "size": size,
            "page": page,
            # "sg_info": kvargs.get("sg_info"),
            # "flavor_info": kvargs.get("flavor_info"),
        }
        if uuids is not None:
            data["uuids"] = ",".join(uuids)
        self.logger.debug("list_simple_resources %s" % data)

        resources = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/simple_entities",
            "get",
            data=urlencode(data),
            timeout=600,
        ).get("resources", [])
        self.logger.debug("Get database instance simple resources: %s" % truncate(resources))
        return resources

    @trace(op="view")
    def list_engines(self):
        """List database engine type and version

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        engines = self.controller.api_client.admin_request("resource", "/v2.0/nrs/provider/sql_stacks/engines", "get")
        self.controller.logger.debug("Get sql stack resource engines: %s" % truncate(engines))
        return engines

    @trace(op="view")
    def get_resource_dbs(self):
        """List schema from resource

        :return: Dictionary with schema info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = []
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"get_dbs": True}}
            data = self.controller.api_client.admin_request("resource", uri, "put", data=data).get("dbs")
        self.logger.debug("Get sql stack %s dbs: %s" % (uuid, truncate(data)))
        return data

    @trace(op="view")
    def get_resource_users(self):
        """List user from resource

        :return: Dictionary with user info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = []
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % uuid
            data = {"action": {"get_users": True}}
            data = self.controller.api_client.admin_request("resource", uri, "put", data=data).get("users")
        self.logger.debug("Get sql stack %s users: %s" % (uuid, truncate(data)))
        return data

    @trace(op="insert")
    def create_resource(self, task, *args, **kvargs):
        """Create resource
        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        options = args[0].pop("options", {})
        data = {"sql_stack": args[0]}
        ## add engine configuration from definition as resurce parameter
        data["sql_stack"]["engine_configs"] = self.get_config("engine")
        import json

        self.logger.debug("+++++++++++++ %s ", json.dumps(data, indent=4))
        try:
            uri = "/v2.0/nrs/provider/sql_stacks"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create sql stack resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            # FF: maxtime=1200 -> maxtime=3600
            self.wait_for_task(taskid, delta=2, maxtime=3600, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.controller.logger.debug("Update sql stack resource: %s" % uuid)

            # enable mailx
            if str2bool(options.get("enable_mailx", False)) is True:
                self.enable_mailx(task)

            # register db instance on haproxy
            if str2bool(options.get("register_on_haproxy", False)) is True:
                self.register_on_haproxy(task)

        return uuid

    def update_resource(self, task, *args, **kvargs):
        """Update resource

        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :param kvargs.actions: list of {'name':<action name>, 'args':<action args>}
        :param kvargs.action: {'name':<action name>, 'args':<action args>}
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            # multi actions
            actions = kvargs.pop("actions", [])
            for action in actions:
                data = None
                if action is not None:
                    data = {"action": {action.get("name"): action.get("args")}}
                uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Send sql stack action resources: %s" % res)

            # single action
            action = kvargs.pop("action", None)
            if action is not None:
                data = {"action": {action.get("name"): action.get("args")}}
                uri = "/v2.0/nrs/provider/sql_stacks/%s/action" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Send sql stack action resources: %s" % res)

            # base update
            elif len(kvargs.keys()) > 0:
                data = {"instance": kvargs}
                uri = "/v2.0/nrs/provider/sql_stacks/%s" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Update sql stack resources: %s" % res)

        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))
        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        Warning!
        This method call a wait_for_task and must be run only by an asyncronus worker!

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        monitoring_enabled = dict_get(self.resource, "attributes.monitoring_enabled", default=False)

        # deregister db instance from haproxy
        engine_params = self.get_config("engine")
        if engine_params is None:
            engine_params = {}
        if str2bool(engine_params.get("register_on_haproxy", False)) is True:
            self.deregister_from_haproxy(task)

        # disable monitoring
        self.logger.debug("delete_resource - monitoring_enabled %s" % monitoring_enabled)
        if monitoring_enabled is True and self.sql_stack_version in ["v2.0"]:
            self.logger.debug("delete_resource - disable_resource_monitoring")
            self.disable_resource_monitoring(task)

        # call superclass method
        if self.check_resource() is None:
            return False

        try:
            uuid = self.instance.resource_uuid
            if uuid is not None:
                uri = "/v2.0/nrs/provider/sql_stacks/%s" % uuid
            else:
                return False
            res = self.controller.api_client.admin_request("resource", uri, "delete", data="")
            taskid = res.get("taskid", None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=1)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))

        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug("Delete sql stack resources: %s" % res)

        return True

        # ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

    def check_supported(self, action=""):
        engine = self.get_config("dbinstance.Engine")
        version = self.get_config("dbinstance.EngineVersion")
        if engine == "postgresql" and action == "install_extensions":
            raise ApiManagerError("Action %s not supported on %s %s" % (action, engine, version))

    def get_job_restore_points(self, data_search):
        """Get backup job restore points

        :return: backup resource points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.instance.verify_permisssions("view")

        restore_points, restore_point_total = self.get_resource_backup_job_restore_points(data_search)
        restore_points = [self.aws_restore_point_info(item) for item in restore_points]
        self.logger.debug(
            "get database instance %s backup resource points: %s" % (self.instance.uuid, truncate(restore_points))
        )
        return restore_points, restore_point_total

    @trace(op="view")
    def get_resource_backup_job_restore_points(self, data_search):
        """Get resource backup

        :return: backup restore points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        restore_points = None
        restore_point_total = 0
        if self.instance.resource_uuid is not None and data_search is not None:
            data = {
                "size": data_search.get("size", -1),
                "page": data_search.get("page", 0),
            }
            # uri = "/v1.0/nrs/provider/instances/%s/backup/restore_points" % self.instance.resource_uuid
            uri = "/v2.0/nrs/provider/sql_stacks/%s/backup/restore_points" % self.instance.resource_uuid
            res = self.controller.api_client.admin_request("resource", uri, "get", data=data)
            restore_points = res.get("restore_points", [])
            restore_point_total = res.get("restore_point_total", 0)
        self.logger.debug("Get database instance resource backup restore points: %s" % truncate(restore_points))
        return restore_points, restore_point_total

    def aws_restore_point_info(self, restore_point):
        """Get info as required by aws api

        :param restore_point: restore_point dict with data
        :return: restore point data
        """
        restore_point_item = restore_point
        restore_point_item.pop("metadata", None)
        restore_point_item.pop("instances", None)
        return restore_point_item
