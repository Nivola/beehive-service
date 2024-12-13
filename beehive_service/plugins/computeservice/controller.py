# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from __future__ import annotations
import hashlib
import ipaddress
from typing import List
from logging import getLogger
from copy import deepcopy
from datetime import datetime, timedelta
from random import randint
from base64 import b64encode, b64decode
from six.moves.urllib.parse import urlencode
from six import ensure_binary, ensure_text
from Crypto.PublicKey import RSA
from paramiko.rsakey import RSAKey
from paramiko.py3compat import StringIO
from beecell.types import is_int, is_string
from beecell.types.type_id import id_gen
from beecell.types.type_dict import dict_get
from beecell.types.type_date import format_date
from beecell.types.type_string import truncate
from beecell.simple import obscure_data, import_class
from beehive.common.data import trace, operation
from beehive.common.apiclient import BeehiveApiClientError
from beehive.common.apimanager import ApiManagerError, ApiManagerWarning
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import (
    ApiServiceTypeContainer,
    ApiServiceTypePlugin,
    AsyncApiServiceTypePlugin,
)
from beehive_service.controller import ServiceController
from beehive_service.model import SrvStatusType, Division, Organization
from beehive_service.service_util import __RULE_GROUP_INGRESS__, __RULE_GROUP_EGRESS__

logger = getLogger(__name__)


class ApiComputeKeyPairsHelper(object):
    def __init__(self, controller):
        self.controller = controller

    def __ssh_key_check(self, key_name, sshkey):
        valid_key = False
        algorithm = sshkey.get("type")
        size = sshkey.get("bits")

        # Add other security check here
        security_key_len_standards = {
            "ssh-rsa": 3072,
            "ssh-dss": 2048,
            "ecdsa": 384,
        }
        message = f"Ssh keypair {key_name}, using {algorithm.upper()} with a {size}-bit key, "
        if algorithm == "GARBAGE":
            valid_key = False
            message += f"IS GARBAGE."
        elif algorithm not in security_key_len_standards:
            valid_key = True
        else:
            min_size = security_key_len_standards[algorithm]
            if size < min_size:
                message += f"IS DEPRECATED; a key greater than {min_size} bits is required.\n"
            else:
                valid_key = True
        if not valid_key:
            message += f"""\n\
To create a new robust SSH key, run 'beehive bu cpaas keypairs add <account_id> <new_key_name>'.\n\
Then, rerun the command using the -sshkey <new_key_name> argument.
"""
            logger.error(message)
            raise ApiManagerError(message)
        logger.info(message + "is valid.")

    def __ssh_get_key(self, key_name):
        uri = "/v1.0/gas/keys/%s" % key_name
        return self.controller.api_client.user_request("ssh", uri, "get", data="").get("key")

    def check_service_instance(self, key_name, account_id=None):
        try:
            ssh_key = self.__ssh_get_key(key_name)
            self.__ssh_key_check(key_name, ssh_key)
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex, code=404)

    def insert_char_every_n_chars(self, string, char="\n", every=64):
        return char.join(string[i : i + every] for i in range(0, len(string), every))

    def get_rsa_key(self, key_location=None, key_file_obj=None, passphrase=None):
        key_fobj = key_file_obj or open(key_location)
        try:
            return RSA.import_key(key_fobj, passphrase=passphrase)
        except ValueError:
            raise Exception("Invalid RSA private key file")

    def get_private_rsa_fingerprint(self, key_location=None, key_file_obj=None, passphrase=None):
        """
        Returns the fingerprint of a private RSA key as a 59-character string (40 characters separated every 2
        characters by a ':'). The fingerprint is computed using the SHA1 (hex) digest of the DER-encoded (pkcs8)
        RSA private key.
        """
        k = self.get_rsa_key(
            key_location=key_location,
            key_file_obj=key_file_obj,
            passphrase=passphrase,
        )
        sha1digest = hashlib.sha1(k.exportKey("DER", pkcs=8)).hexdigest()
        fingerprint = self.insert_char_every_n_chars(sha1digest, ":", 2)
        return fingerprint


class ApiComputeService(ApiServiceTypeContainer):
    objuri = "computeservice"
    objname = "computeservice"
    objdesc = "ComputeService"
    plugintype = "ComputeService"

    class state_enum(object):
        """enumerate state name esposed by api"""

        unknown = "unknown"
        pending = "pending"
        available = "available"
        deregistered = "deregistered"
        trasient = "trasient"
        error = "error"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypeContainer.__init__(self, *args, **kvargs)

        self.child_classes = [
            ApiComputeImage,
            ApiComputeInstance,
            ApiComputeKeyPairs,
            ApiComputeSecurityGroup,
            ApiComputeSubnet,
            ApiComputeTag,
            ApiComputeVolume,
            ApiComputeVPC,
        ]

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypeContainer.info(self)
        info.update({})
        return info

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List[ApiComputeService],
        *args,
        **kvargs,
    ) -> List[ApiComputeService]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        instance_type_idx = controller.get_service_definition_idx(ApiComputeService.plugintype)

        # get resources
        zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiComputeService(controller).list_resources(uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # get parent account
        account = self.controller.get_account(self.instance.account_id)
        # get parent division
        div = self.controller.manager.get_entity(Division, account.division_id)
        # get parent organization
        org = self.controller.manager.get_entity(Organization, div.organization_id)

        container = self.get_config("container")
        quota = self.get_config("quota")
        resource_desc = self.get_config("resource_desc")
        if resource_desc is None:
            resource_desc = "%s.%s.%s" % (org.name, div.name, account.name)

        data = {
            "container": container,
            "name": "%s-%s" % (self.instance.name, id_gen(8)),
            "desc": resource_desc,
            "quota": quota,
            "managed": account.managed,
        }

        if account.managed is True:
            data["managed_by"] = operation.user[0]

        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.DELETED: self.state_enum.deregistered,  # 'deregistered',
            SrvStatusType.DRAFT: self.state_enum.trasient,  # 'trasient',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error',
        }
        return mapping.get(state, self.state_enum.unknown)

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        instance_item = {}
        instance_item["id"] = self.instance.uuid
        instance_item["name"] = self.instance.name
        instance_item["creationDate"] = format_date(self.instance.model.creation_date)
        instance_item["description"] = self.instance.desc
        instance_item["state"] = self.state_mapping(self.instance.status)
        instance_item["owner"] = self.account.uuid
        instance_item["owner_name"] = self.account.name
        instance_item["template"] = self.instance_type.uuid
        instance_item["template_name"] = self.instance_type.name
        instance_item["stateReason"] = {"code": None, "message": None}
        # reason = self.resource.get('reason', None)
        if self.instance.status == "ERROR":
            instance_item["stateReason"] = {
                "code": 400,
                "message": self.instance.last_error,
            }
        instance_item["resource_uuid"] = self.instance.resource_uuid

        return instance_item

    def aws_get_attributes(self):
        """Get account attributes like quotas

        :return:
        """
        if self.resource is None:
            self.resource = {}
        attributes = []

        for quota in self.get_resource_quotas():
            name = quota.get("quota")
            if name.find("compute") == 0:
                name = name.replace("compute.", "")
                attributes_item = {
                    "attributeName": "%s [%s]" % (name, quota.get("unit")),
                    "nvl-attributeUnit": quota.get("unit"),
                    "attributeValueSet": [
                        {
                            "item": {
                                "attributeValue": quota.get("value"),
                                "nvl-attributeUsed": quota.get("allocated"),
                            }
                        }
                    ],
                }
                attributes.append(attributes_item)

        return attributes

    def aws_get_availability_zones(self):
        """Get account availability zones

        :return:
        """
        if self.resource is None:
            self.resource = {}

        def state_mapping(state):
            mapping = {"ACTIVE": "available", "ERROR": "unavailable"}
            return mapping.get(state, "unavailable")

        res = []
        for avz in self.get_resource_availability_zones():
            reason = avz.get("reason", None)
            if avz.get("state") != "ACTIVE" and isinstance(reason, list) and len(reason) > 0:
                reason = reason[0]
            else:
                reason = None
            res.append(
                {
                    "zoneName": dict_get(avz, "site.name"),
                    "zoneState": state_mapping(avz.get("state")),
                    "regionName": dict_get(avz, "region.name"),
                    "messageSet": [{"message": reason}],
                }
            )

        return res

    def set_attributes(self, quotas):
        """Set service quotas

        :param quotas: dict with quotas to set
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {}
        for quota, value in quotas.items():
            data["compute.%s" % quota] = value

        res = self.set_resource_quotas(None, data)
        return res

    def get_attributes(self, prefix="compute"):
        return self.get_container_attributes(prefix=prefix)

    def change_definition(self, inst_service, def_id):
        """Change service definition

        :param inst_service:
        :param def_id:
        :return:
        """
        # get new quota
        service_def = self.controller.get_service_def(def_id)
        new_quota = service_def.get_config("quota")
        # set new quota to service instance
        service_inst_config = inst_service.get_main_config()
        service_def.set_config("quota", new_quota)
        inst_service.update(service_definition_id=service_def.oid)
        self.update_resource_compute_zone_quotas(new_quota)
        self.logger.debug("Change compute service %s definition to %s" % (inst_service.uuid, def_id))
        return True

    #
    # resource client method
    #
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"compute_zone": args[0]}
        try:
            uri = "/v1.0/nrs/provider/compute_zones"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            self.logger.debug("Create resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)

            # create compute zone availability zones "sites" from service config
            for site in self.get_config("sites"):
                site["quota"] = dict_get(data, "compute_zone.quota")
                self.create_resource_availability_zone(task, uuid, site)

            # update compute service status
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update compute instance resources: %s" % uuid)

        return uuid

    def create_resource_availability_zone(self, task, compute_zone, config):
        """Create resource availability zone

        :param compute_zone: compute zone uuid
        :param config: availability zone configuration
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        avz_id = config.get("id")
        try:
            data = {"availability_zone": config}
            uri = "/v1.0/nrs/provider/compute_zones/%s/availability_zones" % compute_zone
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            taskid = res.get("taskid", None)
            self.logger.debug("Create compute zone %s availability zone %s - START" % (compute_zone, avz_id))
        except ApiManagerError as ex:
            self.logger.debug("Create compute zone %s availability zone %s - ERROR" % (compute_zone, avz_id))
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.debug("Create compute zone %s availability zone %s - ERROR" % (compute_zone, avz_id))
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if taskid is not None:
            self.wait_for_task(taskid, delta=5, maxtime=600, task=task)
            self.logger.debug("Create compute zone %s availability zone %s - STOP" % (compute_zone, avz_id))

        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # get availability zones
        avzs = self.get_resource_availability_zones()

        for avz in avzs:
            try:
                data = {"availability_zone": {"id": dict_get(avz, "site.name")}}
                uri = "/v1.0/nrs/provider/compute_zones/%s/availability_zones" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "delete", data=data)
                taskid = res.get("taskid", None)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Delete availability zone resource %s" % avz.get("uuid"))

        return ApiServiceTypePlugin.delete_resource(self, *args, **kvargs)

    def acquire_metric(self, resource_uuid):
        """Get metrics from compute zone"""
        uri = "/v1.0/nrs/provider/compute_zones/%s/metrics" % resource_uuid
        res = self.controller.api_client.admin_request("resource", uri, "get")
        self.logger.debug("acquire metric for resource %s" % resource_uuid)
        return res.get("compute_zone")

    def update_resource_compute_zone_quotas(self, quotas):
        """Update compute zone quotas

        :param quotas: list of new quotas
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = "/v1.0/nrs/provider/compute_zones/%s/quotas" % self.instance.resource_uuid
        res = self.controller.api_client.admin_request("resource", uri, "put", data={"quotas": quotas})
        self.controller.logger.debug("Update compute zone %s quotas: %s" % (self.instance.resource_uuid, truncate(res)))
        return res

    #
    # custom object
    #
    def get_compute_instance_backup(self):
        """Get ApiComputeInstanceBackup instance to manage backup function"""
        # self.verify_permisssions('use')
        instance = ApiComputeInstanceBackup(
            self.controller,
            oid=self.oid,
            objid=self.objid,
            name=self.name,
            desc=self.desc,
            active=self.active,
            model=self.model,
            compute_service=self,
        )
        return instance


class ApiComputeInstanceBackup(AsyncApiServiceTypePlugin):
    plugintype = "ComputeInstanceBackup"
    objname = "instance_backup"

    def __init__(self, *args, **kvargs):
        """ """
        self.compute_service = kvargs.pop("compute_service")
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self._resource_uuid = self.compute_service.instance.resource_uuid

    def verify_permisssions(self, action="use"):
        self.controller.check_authorization(
            self.compute_service.instance.objtype,
            self.compute_service.instance.objdef,
            self.compute_service.instance.objid,
            action,
        )

    def aws_job_info(self, job):
        """Get info as required by aws api

        :return: job data
        """
        account = self.compute_service.get_account()

        job_item = {
            "owner_id": account.uuid,
            "jobId": job.get("id"),
            "name": job.get("name"),
            "desc": job.get("desc"),
            "hypervisor": job.get("hypervisor"),
            # "policy": job.get("id"),
            "availabilityZone": job.get("site"),
            "jobState": job.get("status"),
            "reason": job.get("error"),
            "created": job.get("created"),
            "updated": job.get("updated"),
            "enabled": job.get("enabled"),
            "usage": job.get("usage"),
            "policy": job.get("policy"),
        }

        # get instances
        instances = job.get("instances")
        instance_service_list = []
        if isinstance(instances, list) is True:
            for instance in instances:
                try:
                    item = self.controller.get_service_instance_by_resource_uuid(instance.get("uuid"))
                    instance_service_list.append({"uuid": item.uuid, "name": item.name})
                except ApiManagerError as ame:
                    self.logger.warning(ame)
            job_item["instanceSet"] = instance_service_list
        else:
            job_item["instanceNum"] = instances

        return job_item

    def aws_restore_point_info(self, restore_point):
        """Get info as required by aws api

        :param restore_point: restore_point dict with data
        :return: restore point data
        """
        restore_point_item = restore_point
        restore_point_item.pop("metadata", None)

        # get instances
        instances = restore_point_item.pop("instances", None)
        instance_service_list = []
        if isinstance(instances, list) is True:
            for instance in instances:
                try:
                    item = self.controller.get_service_instance_by_resource_uuid(instance.get("uuid"))
                    instance_service_list.append({"uuid": item.uuid, "name": item.name})
                except ApiManagerError as ame:
                    self.logger.warning(ame)
            restore_point_item["instanceSet"] = instance_service_list

        return restore_point_item

    def list_jobs(self, job_id=None, hypervisor=None):
        """Get jobs by account or by tuple (account, job_id)

        :param job_id: backup job id
        :return:
        """
        self.verify_permisssions(action="view")

        if job_id is None:
            jobs = self.list_resource_jobs(hypervisor)
        else:
            jobs = [self.get_resource_job(job_id)]

        res = [self.aws_job_info(i) for i in jobs]
        self.logger.debug(
            "get compute service %s backup jobs: %s" % (self.compute_service.instance.uuid, truncate(res))
        )

        return res

    def random_start_in_window(self, start_time_window):
        # generate start_time
        # get start time random in window
        start_time = start_time_window[0]
        end_time = start_time_window[1]

        date_format_str = "%H:%M"
        # create datetime object from timestamp string
        start_hour = datetime.strptime(start_time, date_format_str)
        self.logger.debug("start_hour: %s" % start_hour)
        end_hour = datetime.strptime(end_time, date_format_str)
        self.logger.debug("end_hour: %s" % end_hour)

        if end_hour.timestamp() > start_hour.timestamp():
            seconds_diff = end_hour.timestamp() - start_hour.timestamp()
        else:
            end_hour = end_hour + timedelta(days=1)
            self.logger.debug("end_hour: %s" % end_hour)
            seconds_diff = end_hour.timestamp() - start_hour.timestamp()

        self.logger.debug("seconds_diff: %s" % seconds_diff)
        minutes_diff = seconds_diff / 60
        self.logger.debug("minutes_diff: %s" % minutes_diff)
        minutes_random = randint(0, minutes_diff)
        self.logger.debug("minutes_random: %s" % minutes_random)

        final_time = start_hour + timedelta(minutes=minutes_random)
        self.logger.debug("final_time: %s" % final_time)

        # Convert datetime object to string in specific format
        # start_time = '0:00 AM'
        start_time = final_time.strftime("%I:%M %p")
        self.logger.debug("start_time: %s" % start_time)
        return start_time

    def add_job(self, account, name, desc, site, flavor, instance_ids, hypervisor="openstack"):
        from beehive_service.controller.api_account import ApiAccount

        apiAccount: ApiAccount = account

        self.verify_permisssions(action="update")

        compute_zone = self.compute_service.instance.resource_uuid

        # get flavor params
        service_def = self.controller.get_service_def(flavor)
        if service_def.is_active() is False:
            raise ApiManagerWarning("Service definition %s is not in ACTIVE state" % service_def.uuid)

        check, reason = apiAccount.can_instantiate(definition=service_def)
        if not check:
            raise ApiManagerError(reason + f": Account {account.name} ({account.uuid}) definition {service_def.name}")

        fullbackup_interval = service_def.get_config("fullbackup_interval")
        restore_points = service_def.get_config("restore_points")
        start_time_window = service_def.get_config("start_time_window")
        interval = service_def.get_config("interval")
        timezone = service_def.get_config("timezone")
        hypervisor_tag = service_def.get_config("host_group")

        start_time = self.random_start_in_window(start_time_window)

        # check hypervisor
        if hypervisor not in ["openstack"]:
            raise ApiManagerError("backup job creation is supported only for hypervisor openstack")

        # check instances are not already in a backup job
        instance_resource_ids = []
        for instance_id in instance_ids:
            plugin: ApiComputeInstance = self.controller.get_service_type_plugin(instance_id)
            if plugin.is_backup_enabled() is True:
                raise ApiManagerError("compute instance %s is already in a backup job" % plugin.instance.uuid)
            if plugin.get_availability_zone() != site:
                raise ApiManagerError(
                    "compute instance %s and backup job availability zone does not match" % plugin.instance.uuid
                )
            if plugin.get_hypervisor() != hypervisor:
                raise ApiManagerError(
                    "compute instance %s and backup job hypervisor does not match" % plugin.instance.uuid
                )
            instance_resource_ids.append(plugin.instance.resource_uuid)

        # base quotas
        quotas = {
            "compute.backup_jobs": 1,
        }

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # add job
        res = self.add_resource_job(
            name,
            desc,
            site,
            fullbackup_interval,
            restore_points,
            start_time,
            instance_resource_ids,
            hypervisor=hypervisor,
            hypervisor_tag=hypervisor_tag,
            timezone=timezone,
            interval=interval,
            job_type="Parallel",
        )
        self.logger.debug("add compute service %s backup job: %s" % (self.compute_service.instance.uuid, truncate(res)))
        return res

    def update_job(self, job_id, name=None, flavor=None, enabled=None):
        self.verify_permisssions(action="update")

        # get flavor params
        fullbackup_interval = None
        restore_points = None
        if flavor is not None:
            service_def = self.controller.get_service_def(flavor)
            fullbackup_interval = service_def.get_config("fullbackup_interval")
            restore_points = service_def.get_config("restore_points")

        # add job
        res = self.update_resource_job(
            job_id,
            name=name,
            fullbackup_interval=fullbackup_interval,
            restore_points=restore_points,
            enabled=enabled,
        )
        self.logger.debug(
            "update compute service %s backup job: %s" % (self.compute_service.instance.uuid, truncate(res))
        )
        return res

    def add_instance_to_job(self, job_id, instance_id):
        """add instance to backup job

        :param job_id: job id
        :param instance_id: instance id
        :return:
        """
        self.verify_permisssions(action="update")

        # chek job exists
        job = self.exist_backup_job(job_id)

        # check instance is not already in a backup job
        plugin: ApiComputeInstance = self.controller.get_service_type_plugin(instance_id)
        if plugin.is_backup_enabled() is True:
            raise ApiManagerError("compute instance %s is already in a backup job" % plugin.instance.uuid)
        if plugin.get_availability_zone() != job.get("site"):
            raise ApiManagerError(
                "compute instance %s and backup job availability zone does not match" % plugin.instance.uuid
            )
        if plugin.get_hypervisor() != job.get("hypervisor"):
            raise ApiManagerError("compute instance %s and backup job hypervisor does not match" % plugin.instance.uuid)
        instance_resource_id = plugin.instance.resource_uuid

        # add instance to job
        enabled = dict_get(job, "schedule.enabled")
        res = self.add_resource_instance_to_job(job_id, instance_resource_id, enabled)
        self.logger.debug(
            "add compute instance %s to compute service %s backup job %s"
            % (instance_id, self.compute_service.instance.uuid, job_id)
        )
        return res

    def del_instance_from_job(self, job_id, instance_id):
        """remove instance from backup job

        :param job_id: job id
        :param instance_id: instance id
        :return:
        """
        self.verify_permisssions(action="update")

        # chek job exists
        job = self.exist_backup_job(job_id)
        job_instance_uuids = [
            self.controller.get_service_instance_by_resource_uuid(i.get("uuid")).uuid for i in job.get("instances", [])
        ]

        # check instance is not already in a backup job
        plugin = self.controller.get_service_type_plugin(instance_id)
        if plugin.instance.uuid not in job_instance_uuids:
            raise ApiManagerError("compute instance %s is not in the backup job %s" % (plugin.instance.uuid, job_id))
        instance_resource_id = plugin.instance.resource_uuid

        # check job contains at least one instance
        if (len(job_instance_uuids) - 1) < 1:
            raise ApiManagerError("backup job %s must contain at least one compute instance" % job_id)

        # del instance to job
        enabled = dict_get(job, "schedule.enabled")
        res = self.del_resource_instance_from_job(job_id, instance_resource_id, enabled)
        self.logger.debug(
            "add compute instance %s to compute service %s backup job %s"
            % (instance_id, self.compute_service.instance.uuid, job_id)
        )
        return res

    def del_job(self, job_id):
        self.verify_permisssions(action="update")

        # chek job exists
        self.exist_backup_job(job_id)

        # delete job
        res = self.del_resource_job(job_id)
        self.logger.debug("delete compute service %s backup job %s" % (self.compute_service.instance.uuid, job_id))
        return res

    def exist_backup_job(self, job_id):
        try:
            job = self.get_resource_job(job_id)
        except ApiManagerError as ex:
            self.logger.error(ex.value)
            raise ApiManagerError(
                "compute service %s backup job %s does not exist" % (self.compute_service.instance.uuid, job_id)
            )

        return job

    def exist_backup_job_restore_point(self, job_id, restore_point_id):
        restore_points = self.get_resource_backup_job_restore_points(job_id, restore_point_id)

        if len(restore_points) < 1:
            err = "compute service %s backup job %s restore point %s does not exist" % (
                self.compute_service.instance.uuid,
                job_id,
                restore_point_id,
            )
            self.logger.error(err)
            raise ApiManagerError(err)

        return restore_points[0]

    def get_job_restore_points(self, job_id, data_search, restore_point_id=None):
        """Get backup job restore points

        :param job_id: job id
        :param restore_point_id: restore point id
        :return: backup resource points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(action="view")

        restore_points, restore_point_total = self.get_resource_backup_job_restore_points(
            job_id, data_search, restore_point_id=restore_point_id
        )
        res = [self.aws_restore_point_info(item) for item in restore_points]
        self.logger.debug(
            "get compute instance %s backup resource points: %s" % (self.compute_service.instance.uuid, truncate(res))
        )
        return res, restore_point_total

    def add_job_restore_point(self, job_id, name, desc=None, full=True):
        """add job restore point

        :param job_id: job id
        :param name: restore point name
        :param desc: restore point description [optional]
        :param name: restore point full or incremental [default=True]
        :return: resource taskid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(action="update")

        # chek job exists
        self.exist_backup_job(job_id)
        taskid = self.res_add_job_restore_point(job_id, name, desc, full)
        return taskid

    def del_job_restore_point(self, job_id, restore_point_id):
        """delete job restore point

        :param job_id: job id
        :param restore_point_id: restore point id
        :return: resource taskid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(action="update")

        # chek job exists
        self.exist_backup_job(job_id)
        # chek restore point exists
        self.exist_backup_job_restore_point(job_id, restore_point_id)
        # create restore point
        taskid = self.res_del_job_restore_point(job_id, restore_point_id)
        return taskid

    #
    # resource client method
    #
    def list_resource_jobs(self, hypervisor=None):
        """Get backup job resources

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs" % self._resource_uuid
        data = {}
        if hypervisor is not None:
            data.update({"hypervisor": hypervisor})
        instances = self.controller.api_client.admin_request("resource", uri, "get", data=data).get("jobs", [])
        self.logger.debug("Get compute zone backup jobs: %s" % truncate(instances))
        return instances

    def get_resource_job(self, job_id):
        """Get backup job resource

        :param job_id: job id
        :return: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs/%s" % (
            self._resource_uuid,
            job_id,
        )
        instance = self.controller.api_client.admin_request("resource", uri, "get", data="").get("job", None)
        self.logger.debug("Get compute zone backup job %s: %s" % (job_id, truncate(instance)))
        return instance

    def add_resource_job(
        self,
        name,
        desc,
        site,
        fullbackup_interval,
        restore_points,
        start_time,
        instances,
        hypervisor="openstack",
        hypervisor_tag="default",
        timezone="Europe/Rome",
        interval="24hrs",
        job_type="Parallel",
    ):
        """Add backup job resource

        :param name: job name
        :param site: job availability zone
        :param fullbackup_interval: job interval between two full backup
        :param restore_points: number of job restore point
        :param start_time: job start time
        :param instances: instances managed by backup job
        :param hypervisor: hypervisor managed by job [openstack]
        :param hypervisor_tag: hypervisor tag managed by job [default]
        :param timezone: job timezone [Europe/Rome]
        :param interval: job interval [24hrs]
        :param job_type: job type [Parallel]
        :return:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # define start_date
        now = datetime.today()
        start_date = "%s/%s/%s" % (now.day, now.month, now.year)

        data = {
            "name": name,
            "desc": desc,
            "site": site,
            "hypervisor": hypervisor,
            "hypervisor_tag": hypervisor_tag,
            "resource_type": "ComputeInstance",
            "fullbackup_interval": fullbackup_interval,
            "restore_points": restore_points,
            "start_date": start_date,
            "end_date": None,
            "start_time": start_time,
            "interval": interval,
            "timezone": timezone,
            "job_type": job_type,
            "instances": instances,
        }
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs" % self._resource_uuid
        instance = self.controller.api_client.admin_request("resource", uri, "post", data=data).get("job")
        self.logger.debug("Add compute zone backup job: %s" % truncate(instance))
        return instance

    def update_resource_job(
        self,
        job_id,
        name=None,
        fullbackup_interval=None,
        restore_points=None,
        enabled=None,
    ):
        """Update backup job resource

        :param job_id: job id
        :param name: job name
        :param fullbackup_interval: job interval between two full backup
        :param restore_points: number of job restore point
        :param enabled: if True enable job
        :return:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {}
        if name is not None:
            data["name"] = name
        if fullbackup_interval is not None:
            data["fullbackup_interval"] = fullbackup_interval
        if restore_points is not None:
            data["restore_points"] = restore_points
        if enabled is not None:
            data["enabled"] = enabled
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs/%s" % (
            self._resource_uuid,
            job_id,
        )
        instance = self.controller.api_client.admin_request("resource", uri, "put", data=data).get("job")
        self.logger.debug("Update compute zone backup job: %s" % truncate(instance))
        return instance

    def del_resource_job(self, job_id):
        """delete backup job

        :param job_id: job id
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = ""
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs/%s" % (
            self._resource_uuid,
            job_id,
        )
        self.controller.api_client.admin_request("resource", uri, "delete", data=data).get("job")
        self.logger.debug("Delete compute zone backup job %s" % job_id)
        return True

    def add_resource_instance_to_job(self, job_id, instance_resource_id, enabled):
        """add compute instance to backup job

        :param job_id: job id
        :param instance_resource_id: compute instance resource uuid
        :param enabled: if True job is enabled
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            "enabled": enabled,
            "instances": [{"instance": instance_resource_id, "action": "add"}],
        }
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs/%s" % (
            self._resource_uuid,
            job_id,
        )
        self.controller.api_client.admin_request("resource", uri, "put", data=data).get("job")
        self.logger.debug("Add compute instance %s to compute zone backup job %s" % (instance_resource_id, job_id))
        return True

    def del_resource_instance_from_job(self, job_id, instance_resource_id, enabled):
        """remove compute instance from backup job

        :param job_id: job id
        :param instance_resource_id: compute instance resource uuid
        :param enabled: if True job is enabled
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            "enabled": enabled,
            "instances": [{"instance": instance_resource_id, "action": "del"}],
        }
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/jobs/%s" % (
            self._resource_uuid,
            job_id,
        )
        self.controller.api_client.admin_request("resource", uri, "put", data=data).get("job")
        self.logger.debug("Remove compute instance %s from compute zone backup job %s" % (instance_resource_id, job_id))
        return True

    def get_resource_backup_job_restore_points(self, job_id, data_search, restore_point_id=None):
        """Get resource backup job restore_points

        :return: backup restore points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            "job_id": job_id,
            "size": data_search["size"],
            "page": data_search["page"],
        }
        if restore_point_id is not None:
            data["restore_point_id"] = restore_point_id

        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/restore_points" % self._resource_uuid
        res = self.controller.api_client.admin_request("resource", uri, "get", data=data)
        restore_points = res.get("restore_points", [])
        restore_point_total = res.get("restore_point_total", 0)
        self.logger.debug("Get compute instance resource backup restore points: %s" % truncate(restore_points))
        return restore_points, restore_point_total

    def res_add_job_restore_point(self, job_id, name, desc=None, full=True):
        """add job restore point

        :param job_id: job id
        :param name: restore point name
        :param desc: restore point description [optional]
        :param name: restore point full or incremental [default=True]
        :return: resource taskid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            "job_id": job_id,
            "name": name,
            "desc": desc if desc is not None else name,
            "full": full,
        }
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/restore_points" % self._resource_uuid
        taskid = self.controller.api_client.admin_request("resource", uri, "post", data=data).get("taskid")
        self.logger.debug("Add compute zone backup job %s restore point using task: %s" % (job_id, taskid))
        return taskid

    def res_del_job_restore_point(self, job_id, restore_point_id):
        """remove job restore point

        :param job_id: job id
        :param restore_point_id: restore point id
        :return: taskid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"job_id": job_id, "restore_point_id": restore_point_id}
        uri = "/v1.0/nrs/provider/compute_zones/%s/backup/restore_points" % self._resource_uuid
        taskid = self.controller.api_client.admin_request("resource", uri, "delete", data=data).get("taskid")
        self.logger.debug("Delete compute zone backup job %s restore point using task: %s" % (job_id, taskid))
        return taskid


class ApiComputeImage(AsyncApiServiceTypePlugin):
    plugintype = "ComputeImage"
    objname = "image"

    class state_enum(object):
        """enumerate state name esposed by api"""

        unknown = "unknown"
        pending = "pending"
        available = "available"
        deregistered = "deregistered"
        transient = "transient"
        error = "error"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    @staticmethod
    def customize_list(
        controller: ServiceController, entities: List[ApiComputeImage], *args, **kvargs
    ) -> List[ApiComputeImage]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        compute_service_idx = controller.get_service_instance_idx(ApiComputeService.plugintype, index_key="account_id")

        # get resources
        zones = []
        resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.compute_service = compute_service_idx.get(account_id)
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        resources_list = ApiComputeImage(controller).list_resources()
        resources_idx = {r["name"]: r for r in resources_list}

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

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.DELETED: self.state_enum.deregistered,  # 'deregistered',
            SrvStatusType.DRAFT: self.state_enum.transient,  # 'transient',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error',
        }
        return mapping.get(state, self.state_enum.unknown)

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        inst_service = self.instance
        instance_item = {}

        # resource attributes
        if self.resource is None:
            self.resource = {}
        config = self.resource.get("attributes", {}).get("configs", {})

        availability_zones = self.resource.get("availability_zones", [])
        hypervisor = ""
        if len(availability_zones) > 0:
            hypervisor = ",".join(availability_zones[0].get("hypervisors"))

        instance_item["architecture"] = "x86_64"
        instance_item["blockDeviceMapping"] = [
            {
                "deviceName": "",
                "ebs": {
                    "snapshotId": None,
                    "volumeSize": config.get("min_disk_size"),
                    "deleteOnTermination": True,
                    "volumeType": "standard",
                },
            }
        ]
        instance_item["creationDate"] = format_date(inst_service.model.creation_date)
        instance_item["description"] = inst_service.desc
        instance_item["enaSupport"] = False
        instance_item["hypervisor"] = hypervisor
        instance_item["imageId"] = inst_service.uuid
        instance_item["imageLocation"] = ""
        instance_item["imageOwnerAlias"] = self.account.name
        instance_item["imageOwnerId"] = self.account.uuid
        instance_item["imageState"] = self.state_mapping(inst_service.status)
        instance_item["imageType"] = "machine"
        instance_item["isPublic"] = False
        instance_item["kernelId"] = None
        instance_item["name"] = inst_service.name
        instance_item["platform"] = "%s %s" % (config.get("os"), config.get("os_ver"))
        instance_item["tagSet"] = []
        instance_item["virtualizationType"] = "fullvirtual"
        instance_item["nvl-resourceId"] = self.instance.resource_uuid
        instance_item["nvl-minDiskSize"] = config.get("min_disk_size", None)

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id

        # base quotas
        quotas = {
            "compute.images": 1,
        }

        compute_zone = self.get_config("computeZone")

        # check quotas
        self.check_quotas(compute_zone, quotas)

        self.set_resource(self.get_config("resource_oid"))

        params["resource_params"] = {}
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    #
    # resource client method
    #
    def list_resources(self, zones=[], uuids=[], tags=[], page=0, size=-1):
        """Get resource info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)
        self.controller.logger.debug("list_iresources %s" % data)

        images = self.controller.api_client.admin_request(
            "resource", "/v1.0/nrs/provider/images", "get", data=urlencode(data)
        ).get("images", [])
        self.controller.logger.debug("Get compute image resources: %s" % truncate(images))
        return images

    def create_resource(self, *args, **kvargs):
        """Create resource. Do nothing. Use existing resource

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return None

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource do nothing.

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return True


class ApiComputeInstance(AsyncApiServiceTypePlugin):
    plugintype = "ComputeInstance"
    objname = "instance"

    class state_enum(object):
        """enumerate state name exposed by api"""

        pending = "pending"
        building = "building"
        error = "error"
        terminated = "terminated"
        running = "running"
        unknown = "unknown"
        stopped = "stopped"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return ApiServiceTypePlugin.info(self)

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List[ApiComputeInstance],
        *args,
        **kvargs,
    ) -> List[ApiComputeInstance]:
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
        image_idx = controller.get_service_instance_idx(ApiComputeImage.plugintype, account_id_list=account_ids)
        security_group_idx = controller.get_service_instance_idx(
            ApiComputeSecurityGroup.plugintype, account_id_list=account_ids
        )
        volume_idx = controller.get_service_instance_idx(ApiComputeVolume.plugintype, account_id_list=account_ids)
        compute_service_idx = controller.get_service_instance_idx(
            ApiComputeService.plugintype, account_id_list=account_ids, index_key="account_id"
        )
        instance_type_idx = controller.get_service_definition_idx(ApiComputeInstance.plugintype)
        instance_tags_idx = controller.get_service_tags_idx(account_id_list=account_ids)

        # get resources
        zones = {}
        for entity in entities:
            entity_instance = entity.instance
            account_id = "%s" % entity_instance.account_id
            entity.account = account_idx.get(account_id)
            entity.subnet_idx = subnet_idx
            entity.vpc_idx = vpc_idx
            entity.image_idx = image_idx
            entity.security_group_idx = security_group_idx
            entity.volume_idx = volume_idx
            entity.tag_set = [{"key": k, "value": ""} for k in instance_tags_idx.get(entity_instance.oid, [])]
            instance_type = instance_type_idx.get("%s" % entity_instance.service_definition_id)
            if instance_type is not None:
                entity.instance_type_name = instance_type.name
            entity.compute_service = compute_service_idx.get(account_id)
            zone_id = entity.compute_service.resource_uuid
            res_id = entity_instance.resource_uuid
            if zone_id not in zones:
                zones[zone_id] = set()
            if res_id is not None:
                zones[zone_id].add(res_id)

        resources_idx = {}
        """
        I loop for zone to avoid to have get with long query string that will fail;
        the code in resource in optimized to work on zone that are account at business layer.
        """
        if len(zones) > 0:
            api_compute_inst = ApiComputeInstance(controller)
            resources = []
            res_uuids_threshold = 3
            for zone in zones:
                resource_uuids = uuids = zones[zone]
                """
                The under hood code use get if there are to much param list_resources fail;
                then we prefer ask all!
                """
                if len(resource_uuids) > res_uuids_threshold:
                    resource_uuids = None
                resources += api_compute_inst.list_resources(zones=[zone], uuids=resource_uuids)
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
        if self.resource_uuid is not None:
            try:
                self.resource = self.get_resource()
            except Exception:
                self.resource = None

    def get_availability_zone(self):
        """Get availability zone where instance is deployed"""
        if self.resource is not None:
            return dict_get(self.resource, "availability_zone.name")
        return None

    def get_hypervisor(self):
        """Get instance hypervisor"""
        if self.resource is not None:
            return dict_get(self.resource, "attributes.type")
        return None

    def get_volume_type_by_resource(self, resource):
        """get volume type service definition by resource specified in flavor

        :param resource: volume type flavor resource
        :return: ServiceDefinition
        """
        res = None
        servdefs, tot = self.controller.get_paginated_service_defs(
            plugintype=ApiComputeVolume.plugintype, with_perm_tag=False, size=-1
        )
        for servdef in servdefs:
            flavor = servdef.get_config("flavor")
            if resource == flavor:
                res = servdef
        if res is None:
            raise ApiManagerError("no volume type found for flavor %s" % resource)
        self.logger.debug("get volume type %s from flavor %s" % (res, resource))
        return res

    def state_mapping(self, state, runstate):
        """Get the current state of the instance.
        Valid values: pending | running | shutting-down | terminated | stopping | stopped
        Additional values: building | error | unknown

        :param state:
        :param runstate:
        :return:
        """
        mapping = {
            SrvStatusType.DRAFT: self.state_enum.pending,  # 'pending',
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.BUILDING: self.state_enum.building,  # 'building',
            SrvStatusType.CREATED: self.state_enum.building,  # 'building',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error',
            SrvStatusType.ERROR_CREATION: self.state_enum.error,  # 'error',
            SrvStatusType.DELETING: self.state_enum.terminated,  # 'terminated',
            SrvStatusType.TERMINATED: self.state_enum.terminated,  # 'terminated',
            SrvStatusType.UNKNOWN: self.state_enum.error,  # 'error',
            SrvStatusType.UPDATING: self.state_enum.building,  # 'building',
        }
        inst_state = mapping.get(state, "unknown")

        if state == SrvStatusType.ACTIVE and runstate == "poweredOn":
            #'running'
            inst_state = self.state_enum.running
        elif state == SrvStatusType.ACTIVE and runstate == "poweredOff":
            # 'stopped'
            inst_state = self.state_enum.stopped
        elif state == SrvStatusType.ACTIVE and runstate == "update":
            inst_state = self.state_enum.building  # 'building'

        return inst_state

    def get_host_group(self):
        """get host_group"""
        try:
            host_group = self.get_config("instance.Nvl_HostGroup")
            if host_group is None:
                host_group = self.get_config("host_group")
                if host_group is None:
                    host_group = None
        except Exception:
            host_group = None
        return host_group

    def get_target_groups(self):
        """get load balancer target groups"""
        target_groups = self.get_config("instance.nvl-targetGroups")
        return target_groups

    def aws_info(self, version="v1.0"):
        """Get info as required by aws api

        :return:
        """
        subnet_name = None
        subnet_vpc_name = None
        subnet_id = None
        subnet_vpc_id = None
        avzone = None
        image_id = None
        image_name = None
        key_name = None
        sgs = []

        if self.resource is None:
            self.resource = {}

        resource = self.resource
        config = self.get_config("instance")

        if config is not None:
            subnet_id = config.get("SubnetId")
            image_id = config.get("ImageId")
            sgs = resource.get("security_groups", [])
            key_name = dict_get(resource, "attributes.key_name")

            subnet = self.subnet_idx.get(subnet_id)
            if subnet is not None:
                subnet_vpc = self.vpc_idx.get(subnet.get_parent_id())
                avzone = dict_get(resource, "availability_zone.name")
                subnet_id = subnet.uuid
                subnet_vpc_id = subnet_vpc.uuid
                subnet_name = subnet.name
                subnet_vpc_name = subnet_vpc.name

            image = self.image_idx.get(image_id)
            if image is not None:
                image_id = image.uuid
                image_name = image.name

        instance = self.instance
        instance_item = {}

        hypervisor = None
        attributes = resource.get("attributes")
        if attributes is not None:
            hypervisor = attributes.get("type")

        instance_item["instanceId"] = instance.uuid
        instance_item["instanceType"] = self.instance_type_name

        status = instance.status
        if len(resource) > 0:
            state = resource.get("state")
            runstate = resource.get("runstate")
        else:
            state = status
            runstate = "poweredOn" if instance.active else "poweredOff"

        instance_state = self.state_mapping(state, runstate)
        instance_item["instanceState"] = {"name": instance_state}
        instance_item["stateReason"] = {"code": None, "message": None}

        if status == "ERROR":
            instance_item["stateReason"] = {
                "code": 400,
                "message": instance.last_error,
            }

        instance_item["imageId"] = image_id

        vpcs = resource.get("vpcs", None)
        # get only the first vpc
        if vpcs is not None and len(vpcs) > 0:
            vpc = vpcs[0]
        else:
            vpc = {}

        fixed_ip = vpc.get("fixed_ip")
        if fixed_ip is not None:
            host_name = fixed_ip.get("hostname")
            instance_item["privateDnsName"] = host_name
            instance_item["dnsName"] = host_name
            instance_item["privateIpAddress"] = fixed_ip.get("ip")

        instance_item["launchTime"] = format_date(instance.model.creation_date)
        instance_item["placement"] = {"availabilityZone": avzone}
        instance_item["subnetId"] = subnet_id
        instance_item["vpcId"] = subnet_vpc_id
        instance_item["hypervisor"] = hypervisor
        instance_item["keyName"] = key_name
        instance_item["architecture"] = "x86_64"
        instance_item["virtualizationType"] = "full"
        instance_item["tagSet"] = self.tag_set
        instance_item["networkInterfaceSet"] = []

        # storage
        blocks = []
        volume_idx = self.volume_idx
        for item in resource.get("block_device_mapping", []):
            volume = volume_idx.get(item.get("id"))
            if volume is not None:
                volume_id = volume.uuid
            else:
                volume_id = None
            blocks.append(
                {
                    "deviceName": item.get("path"),
                    "ebs": {
                        "volumeId": volume_id,
                        "status": "attached",
                        "attachTime": item.get("attachment"),
                        "deleteOnTermination": True,
                        "volumeSize": item.get("volume_size"),
                    },
                }
            )

        instance_item["blockDeviceMapping"] = blocks
        instance_item["groupSet"] = []

        security_group_idx = self.security_group_idx
        for sg in sgs:
            sg_obj = security_group_idx.get(sg["uuid"])
            sg_name = None
            sg_uuid = sg["uuid"]
            if sg_obj is not None:
                sg_name = sg_obj.name
                sg_uuid = sg_obj.uuid
            instance_item["groupSet"].append({"groupId": sg_uuid, "groupName": sg_name})

        # custom params
        account = self.account
        instance_item["nvl-name"] = instance.name
        instance_item["nvl-subnetName"] = subnet_name
        instance_item["nvl-vpcName"] = subnet_vpc_name
        instance_item["nvl-imageName"] = image_name
        instance_item["nvl-ownerAlias"] = account.name
        instance_item["nvl-ownerId"] = account.uuid
        instance_item["nvl-resourceId"] = instance.resource_uuid
        instance_item["nvl-InstanceTypeExt"] = {}

        flavor = resource.get("flavor")
        if flavor is not None:
            flavor.pop("uuid")
            flavor.pop("name")
            instance_item["nvl-InstanceTypeExt"] = flavor

        # version v2.0
        if version == "v2.0":
            instance_item["nvl-HostGroup"] = self.get_host_group()
            instance_item["nvl-MonitoringEnabled"] = self.is_monitoring_enabled()
            instance_item["nvl-LoggingEnabled"] = self.is_logging_enabled()
            instance_item["nvl-BackupEnabled"] = self.is_backup_enabled()
            instance_item["nvl-targetGroups"] = self.get_target_groups()

        return instance_item

    def aws_restore_point_info(self, restore_point):
        """Get info as required by aws api

        :param restore_point: restore_point dict with data
        :return: restore point data
        """
        restore_point_item = restore_point
        restore_point_item.pop("metadata", None)
        restore_point_item.pop("instances", None)
        return restore_point_item

    @trace(op="view")
    def get_ssh_node(self, fqdnName):
        """Get password for an instance by fqdnName

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        ssh_node = None
        try:
            uri_node = "/v1.0/gas/nodes/%s" % fqdnName
            users = (
                self.controller.api_client.admin_request("ssh", uri_node, "get", data="").get("node").get("users", [])
            )
            if len(users) > 0:
                ssh_node = users[0]
                user_id = ssh_node["id"]
                uri_password = "/v1.0/gas/users/%s/password" % user_id
                password = self.controller.api_client.admin_request("ssh", uri_password, "get", data="").get("password")
                ssh_node.update({"plain_pwd": password})

        except BeehiveApiClientError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)
        return ssh_node

    def __get_admin_credentials_from_ssh_node(self, srv_inst, admin_username):
        """
        Get credentials from ssh node
        """
        admin_pwd = None
        res, total = self.controller.get_service_type_plugins(
            service_uuid_list=[srv_inst.uuid],
            account_id_list=[srv_inst.account_id],
            plugintype=ApiComputeInstance.plugintype,
        )
        dns_name = res[0].aws_info(version="v2.0").get("dnsName")
        ssh_node = self.get_ssh_node(dns_name)
        if ssh_node is not None:
            admin_username = ssh_node.get("name")
            admin_pwd = ssh_node.get("plain_pwd")
        return admin_username, admin_pwd

    def __clone_handle_admin_credentials(self, srv_inst, admin_username, admin_pwd):
        out_admin_username = admin_username
        out_admin_pwd = admin_pwd
        db_admin_username, db_admin_pwd = self.__get_admin_credentials_from_ssh_node(srv_inst, admin_username)
        if admin_pwd is not None:
            # check if the credentials from ssh node is equals to user one
            if db_admin_pwd is not None and db_admin_pwd != admin_pwd:
                raise ApiManagerError(
                    f"Authentication failure for CPAAS {srv_inst.uuid} due to incorrect password.", code=403
                )
        else:
            # Take credentials from ssh node
            out_admin_pwd = db_admin_pwd
        if out_admin_pwd is None:
            raise ApiManagerError(
                f"Authentication failure for CPAAS {srv_inst.uuid} due to missing password.", code=403
            )
        if db_admin_username is not None:
            out_admin_username = db_admin_username
        return out_admin_username, out_admin_pwd

    def __choose_name(self, account_id, os_name):
        if os_name == "Windows":
            hostname = self.instance.name

            # check instance with the same name already exists in the account
            insts, tot = self.controller.get_paginated_service_instances(
                name=hostname, filter_expired=False, authorize=False
            )
            if tot > 1:
                raise ApiManagerError("Windows ComputeInstance %s already exists" % hostname, code=409)

            # check name is long no more than 15 characters
            hostname_len = len(hostname)
            if hostname_len > 15:
                raise ApiManagerError(
                    "Hostname %s is too long. Windows ComputeInstance name maxsize is 15 characters, current size %s"
                    % (hostname, hostname_len)
                )
            return hostname
        hostname = "%s%s" % (
            self.instance.name,
            self.controller.get_account_acronym(account_id),
        )
        # check name is long no more than 45 characters
        hostname_len = len(hostname)
        if hostname_len > 45:
            maxsize = 45 - len(self.controller.get_account_acronym(account_id))
            raise ApiManagerError(
                "Hostname %s is too long. Linux ComputeInstance name maxsize is %s characters, current size %s"
                % (hostname, maxsize, hostname_len)
            )
        return hostname

    def __configure_flavor(
        self, default_volume_type, type_provider, host_group, flavor_resource_uuid, image_inst, quotas
    ):
        if type_provider == "openstack" and host_group:
            if host_group not in ["bck", "nobck"]:
                raise ApiManagerError('only "bck" and "nobck" are openstack supported hostgroup')
            flavor_resource_uuid += ".%s" % host_group

        flavor_resource = self.get_flavor(flavor_resource_uuid)
        flavor_configs = flavor_resource.get("attributes", {}).get("configs", {})
        volume_size = flavor_configs.get("disk", 40)
        storage = [
            {
                "boot_index": 0,
                "volume_size": volume_size,
                "flavor": default_volume_type.get_config("flavor"),
                "uuid": image_inst.resource_uuid,
                "source_type": "image",
                "tag": "default",
            }
        ]
        quotas["compute.cores"] = flavor_configs.get("vcpus", 0)
        quotas["compute.blocks"] = volume_size
        quotas["compute.ram"] = flavor_configs.get("memory", 0) / 1024 if flavor_configs.get("memory") else 0
        return flavor_resource, storage, quotas

    def __configure_block_device_mapping(self, default_volume_type, data_instance, image_volume_size, storage, quotas):
        # overwrite boot disk with BlockDeviceMapping first item param
        block_device_mappings = data_instance.get("BlockDeviceMapping_N", [])
        if len(block_device_mappings) > 0:
            main_block_device_mapping = block_device_mappings.pop(0)
            ebs_block = main_block_device_mapping.get("Ebs")
            if ebs_block is not None:
                vsize = ebs_block.get("VolumeSize")
                volume_type = ebs_block.get("VolumeType")
                if vsize is not None:
                    storage[0]["volume_size"] = vsize
                    quotas["compute.blocks"] = vsize
                if volume_type is not None:
                    volume_type = self.controller.check_service_definition(volume_type)
                    storage[0]["flavor"] = volume_type.get_config("flavor")

            # overwrite boot disk size if value < image_volume_size
            if storage[0]["volume_size"] < image_volume_size:
                storage[0]["volume_size"] = image_volume_size
                quotas["compute.blocks"] = image_volume_size

            # overwrite boot disk if clone volume exists
            clone_volume_id = ebs_block.get("Nvl_VolumeId")
            if clone_volume_id is not None:
                clone_volume = self.controller.check_service_instance(clone_volume_id, ApiComputeVolume)
                clone_volume_size = int(clone_volume.get_config("volume.Size"))
                storage[0]["uuid"] = clone_volume.resource_uuid
                storage[0]["source_type"] = "volume"
                storage[0]["volume_size"] = clone_volume_size
                quotas["compute.blocks"] = clone_volume_size

        # check BlockDeviceMapping param
        boot_index = 1
        for block_device_mapping in block_device_mappings:
            ebs_block = block_device_mapping.get("Ebs")
            if ebs_block is not None:
                volume_data = {
                    "boot_index": boot_index,
                    "volume_size": ebs_block.get("VolumeSize"),
                }

                # get volume to clone
                clone_volume_id = ebs_block.get("Nvl_VolumeId")
                if clone_volume_id is not None:
                    clone_volume = self.controller.check_service_instance(clone_volume_id, ApiComputeVolume)
                    clone_volume_size = int(clone_volume.get_config("volume.Size"))
                    volume_data["uuid"] = clone_volume.resource_uuid
                    volume_data["source_type"] = "volume"
                    volume_data["volume_size"] = clone_volume_size

                # get volume type
                volume_type = ebs_block.get("VolumeType")
                if volume_type is not None:
                    volume_type = self.controller.check_service_definition(volume_type)
                else:
                    volume_type = default_volume_type
                volume_data["flavor"] = volume_type.get_config("flavor")
                storage.append(volume_data)

                self.logger.debug("+++++ pre_create - ebs_block: %s" % ebs_block)
                self.logger.debug("+++++ pre_create - volume_size: %s" % ebs_block.get("VolumeSize"))
                quotas["compute.blocks"] += ebs_block.get("VolumeSize")
                quotas["compute.volumes"] += 1
                boot_index += 1
        return storage, quotas

    def __check_security_groups(self, data_instance, account_id):
        # get and check the id SecurityGroupId
        security_group_ress = []
        instance_oid = self.instance.oid
        for security_group in data_instance.get("SecurityGroupId_N", []):
            sg_inst = self.controller.check_service_instance(
                security_group, ApiComputeSecurityGroup, account=account_id
            )
            if sg_inst.resource_uuid is None:
                raise ApiManagerError("SecurityGroup id %s is invalid" % security_group)
            security_group_ress.append(sg_inst.resource_uuid)
            sg_inst_oid = sg_inst.oid
            # link security group to instance
            self.instance.add_link(
                name=f"link-{instance_oid}-{sg_inst_oid}",
                type="sg",
                end_service=sg_inst_oid,
                attributes={},
            )
        return security_group_ress

    def __check_ssh_key(self, data_instance, account_id, os_name, is_clone):
        # get key
        key_name = data_instance.get("KeyName")
        if is_clone and key_name is None:
            key_name = self.get_config("SshKeyName")
        if key_name is not None:
            ApiComputeKeyPairsHelper(self.controller).check_service_instance(key_name, account_id)
        elif os_name != "Windows":
            raise ApiManagerError("Ssh keyname is required")
        return key_name

    def __configure_network(
        self, data_instance, type_provider, hostname, account_id, compute_zone, image_avz_hypervisors
    ):
        # check subnet
        subnet_id = data_instance.get("SubnetId")
        if subnet_id is None:
            raise ApiManagerError("Subnet is not defined")

        subnet_inst = self.controller.check_service_instance(subnet_id, ApiComputeSubnet, account=account_id)

        subnet = subnet_inst.get_config("cidr")
        av_zone = subnet_inst.get_config("site")

        # check availability zone status
        if not self.is_availability_zone_active(compute_zone, av_zone):
            raise ApiManagerError("Availability zone %s is not in available status" % av_zone)

        # check image support hypervisor
        zone_image = image_avz_hypervisors.get(av_zone)
        if zone_image is None:
            raise ApiManagerError("Image %s not available for zone %s" % (data_instance.get("ImageId"), av_zone))

        if type_provider not in zone_image:
            raise ApiManagerError(
                "Image %s does not support hypervisor %s" % (data_instance.get("ImageId"), type_provider)
            )

        # get vpc
        vpc_resource_uuid = self.controller.get_service_instance(
            subnet_inst.model.linkParent[0].start_service_id
        ).resource_uuid

        network = {
            "subnet": subnet,
            "vpc": vpc_resource_uuid,
            "fixed_ip": {
                "hostname": hostname,
            },
        }

        private_ip = data_instance.get("PrivateIpAddress")
        if private_ip is not None:
            if ipaddress.IPv4Address(private_ip) not in ipaddress.IPv4Network(subnet):
                raise ApiManagerError("private ip is not in the subnet cidr")
            network["fixed_ip"]["ip"] = private_ip

        return network, av_zone

    def __initialize_quotas(self) -> dict:
        return {
            "compute.cores": 0,
            "compute.instances": 1,
            "compute.volumes": 1,
            "compute.ram": 0,
            "compute.blocks": 0,
        }

    def pre_create(self, **params) -> dict:
        """
        Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id
        flavor_resource_uuid = self.get_config("flavor")
        compute_zone = self.get_config("computeZone")
        data_instance = self.get_config("instance")

        image_inst = self.controller.check_service_instance(
            data_instance.get("ImageId"), ApiComputeImage, account=account_id
        )
        image_resource = self.get_image(image_inst.resource_uuid)
        image_configs = image_resource.get("attributes", {}).get("configs", {})
        os_name = image_configs.get("os")
        hostname = self.__choose_name(account_id, os_name)

        # Check instanceId used for clone with vsphere, it's the source vm id
        instance_id = self.get_config("InstanceId")

        admin_username = None
        admin_pwd = data_instance.get("AdminPassword")
        # This variable is used only for the clone task
        clone_source_uuid = None
        is_clone = instance_id is not None
        if is_clone:
            srv_inst = self.controller.get_service_instance(instance_id)
            clone_source_uuid = srv_inst.resource_uuid
            admin_username, admin_pwd = self.__clone_handle_admin_credentials(srv_inst, admin_username, admin_pwd)

        key_name = self.__check_ssh_key(data_instance, account_id, os_name, is_clone)
        type_provider = data_instance.get("Nvl_Hypervisor") or self.get_config("type") or "vsphere"
        self.set_config("type", type_provider)
        metadata = data_instance.get("Nvl_Metadata") or self.get_config("metadata") or {}
        multi_avz = data_instance.get("Nvl_MultiAvz") or self.get_config("multi_avz") or True
        host_group = data_instance.get("Nvl_HostGroup") or self.get_config("host_group")
        image_volume_size = image_configs.get("min_disk_size")
        image_avz_hypervisors = {a["name"]: a["hypervisors"] for a in image_resource.get("availability_zones")}
        default_volume_type = self.controller.get_default_service_def("ComputeVolume")

        quotas = self.__initialize_quotas()
        flavor_resource, storage, quotas = self.__configure_flavor(
            default_volume_type, type_provider, host_group, flavor_resource_uuid, image_inst, quotas
        )
        storage, quotas = self.__configure_block_device_mapping(
            default_volume_type, data_instance, image_volume_size, storage, quotas
        )
        self.check_quotas(compute_zone, quotas)

        network, av_zone = self.__configure_network(
            data_instance, type_provider, hostname, account_id, compute_zone, image_avz_hypervisors
        )
        security_groups = self.__check_security_groups(data_instance, account_id)

        # check if instance come from a backup restore
        restore_from_backup = data_instance.get("RestoreFromBackup", False)
        restore_point = data_instance.get("RestorePoint")
        backup_instance_resource_uuid = data_instance.get("BackupInstance")

        tags_list = (
            tag.get("Key")
            for tag_spec in data_instance.get("TagSpecification_N", [])
            for tag in tag_spec.get("Tags", [])
            if tag.get("Key") is not None
        )
        name = "%s-%s" % (self.instance.name, id_gen(length=8))
        data = {
            "admin_username": admin_username,
            "admin_pass": admin_pwd,
            "key_name": key_name,
            "availability_zone": av_zone,
            "multi_avz": multi_avz,
            "compute_zone": compute_zone,
            "container": self.get_config("container"),
            "desc": name,
            "flavor": flavor_resource_uuid,
            "metadata": metadata,
            "name": name,
            "networks": [network],
            "security_groups": security_groups,
            "block_device_mapping": storage,
            "type": type_provider,
            "orchestrator_tag": "default",
            "user_data": "",
            "tags": ",".join(tags_list),
            "check_main_vol_size": data_instance.get("CheckMainVolSize", True),
            "clone_source_uuid": clone_source_uuid,
        }
        if host_group is not None:
            data["host_group"] = host_group
        if restore_from_backup:
            data.update(
                {
                    "restore_from_backup": restore_from_backup,
                    "restore_point": restore_point,
                    "backup_instance_resource_uuid": backup_instance_resource_uuid,
                }
            )
        # set volume type to use when create ApiComputeVolume instance
        data["volume_type"] = default_volume_type.uuid
        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))
        return params

    #
    # import
    #
    def pre_import(self, **params) -> dict:
        """Check input params before resource import. Use this to format parameters for service creation
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
        vpc_resource_id = dict_get(resource, "vpcs.0.uuid")
        image_resource_id = dict_get(resource, "image.name")
        availability_zone_name = dict_get(resource, "availability_zone.name")
        vpcus = dict_get(resource, "flavor.vcpus", default=0)
        ram = dict_get(resource, "flavor.memory", default=0)
        block_devices = dict_get(resource, "block_device_mapping", default=0)

        params["resource_id"] = resource_uuid

        # base quotas
        quotas = {
            "compute.cores": int(vpcus),
            "compute.instances": 1,
            "compute.volumes": len(block_devices),
            "compute.ram": float(ram) / 1024,
            "compute.blocks": sum([bd.get("volume_sise", 0) for bd in block_devices]),
        }

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # get vpc and subnets child of the vpc
        vpc_si = self.controller.get_service_instance_by_resource_uuid(vpc_resource_id, plugintype="ComputeVPC")
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
            if vpc_id == vpc_si.uuid and subnet_availability_zone_name == availability_zone_name:
                subnet_si = subnet
                break

        if subnet_si is None:
            raise ApiManagerError("no valid subnet found")

        self.instance.set_config("instance.SubnetId", subnet_si.uuid)

        # get image
        images, tot = self.controller.get_paginated_service_instances(
            account_id=account_id,
            filter_expired=False,
            plugintype="ComputeImage",
            with_perm_tag=False,
            size=-1,
        )
        image = None
        for image in images:
            if image.name == image_resource_id:
                break

        if image is None:
            raise ApiManagerError("no valid image found")

        self.instance.set_config("instance.ImageId", image.uuid)

        return params

    def post_import(self, **params):
        """Post import function. Use this after service creation.
        Extend this function to execute some operation after entity was created.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        # import volumes as service instances
        self.__import_volumes_from_resource()

        return None

    #
    # update, delete
    #
    def pre_update(self, **params):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # change instance type
        service_definition_id = params.pop("InstanceType", None)
        if service_definition_id is not None:
            ext_params = self.set_instance_type(service_definition_id)
            params.update(ext_params)

        # change security group
        security_groups = params.pop("GroupId_N", None)
        if security_groups is not None:
            actions = []
            for action in security_groups:
                action_param = self.change_security_group(action)
                actions.append(action_param)
            ext_params = {"resource_params": {"actions": actions}}
            params.update(ext_params)

        # Manage instance user: add, delete, change password
        user_params = params.pop("Nvl_User", None)
        if user_params is not None:
            ext_params = self.manage_user(user_params)
            params.update(ext_params)

        self.logger.debug("Pre create params: %s" % params)

        return params

    def pre_patch(self, **params) -> dict:
        """Pre patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        params["resource_params"] = {}
        self.logger.debug("Pre patch params: %s" % obscure_data(deepcopy(params)))

        return params

    def pre_delete(self, **params):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        res, total = self.get_linked_services(link_type="logging", filter_expired=False)
        if total > 0:
            raise ApiManagerError("compute instance %s has a connected logging instance" % self.instance.uuid)

        res, total = self.get_linked_services(link_type="monitoring", filter_expired=False)
        if total > 0:
            raise ApiManagerError("compute instance %s has a connected monitoring instance" % self.instance.uuid)

        tgs = self.get_config("instance.nvl-targetGroups")
        if tgs is not None and len(tgs) > 0:
            raise ApiManagerError(
                "compute instance %s is load balanced. Deregister compute instance from target "
                "groups %s before proceeding with deletion" % (self.instance.uuid, tgs)
            )

        return params

    def post_delete(self, **params):
        """Post delete function. This function is used in delete method. Extend this function to execute action after
        object was deleted.
        ATTENTION: the delete in async task so post_delete is called immediately!

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        # get ApiComputeVolume instances
        try:
            resource = self.get_resource()
        except Exception:
            resource = None

        if resource is None:
            self.logger.error(
                "post_delete - resource None - cannot delete volume of service instance %s" % self.instance.oid
            )
        else:
            block_device_mapping = resource.get("block_device_mapping", [])
            if len(block_device_mapping) == 0:
                self.logger.error("post_delete - block_device_mapping empty")

            for item in block_device_mapping:
                resource_vol_uuid = item.get("id", None)
                self.logger.debug("post_delete - resource_vol_uuid: %s" % resource_vol_uuid)

                volume, tot = self.controller.get_service_type_plugins(
                    resource_uuid=resource_vol_uuid,
                    plugintype=ApiComputeVolume.plugintype,
                )
                if tot > 0:
                    volume: ApiComputeVolume = volume[0]
                    # soft delete - only logic service delete (not resource)
                    volume.delete_instance()
                    self.logger.debug(
                        "post_delete - delete volume service type %s - uuid: %s - instance oid: %s"
                        % (type(volume), volume.uuid, volume.instance.oid)
                    )
                else:
                    self.logger.error(
                        "post_delete - ApiComputeVolume not found - resource_vol_uuid: %s" % resource_vol_uuid
                    )

        return None

    #
    # action
    #
    def get_console(self):
        """get instance native console

        :return: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.get_hypervisor() not in ["openstack", "vsphere"]:
            raise ApiManagerError(
                "native console is available only for compute instance running on " "hypervisor openstack"
            )

        res = self.get_resource_console()
        return res

    def set_instance_type(self, instance_type):
        """Set instance type

        :param instance_type: instance type
        :return: action params
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check instance status
        if self.get_runstate() in ["poweredOn", "poweredOff"]:
            try:
                self.instance.change_definition(instance_type)
            except ApiManagerError as ex:
                self.logger.warning(ex)
                raise ApiManagerError("Instance_type does not change. Select e a new one")

            flavor = self.instance.config_object.json_cfg.get("flavor")

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
        security_group, action = security_group.split(":")
        action = action.upper()
        security_group = self.controller.get_service_type_plugin(
            security_group, plugin_class=ApiComputeSecurityGroup, details=False
        )

        # get active security groups
        sgs = [sg["uuid"] for sg in self.resource.get("security_groups", [])]
        attached = security_group.resource_uuid in sgs

        if attached is True and action == "DEL":
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

    def start(self, schedule=None):
        """Start instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check instance status
        if self.get_runstate() == "poweredOff":
            params = {"resource_params": {"action": {"name": "start", "args": True}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Start instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)
        return res

    def stop(self, schedule=None):
        """Stop instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check instance status
        if self.get_runstate() == "poweredOn":
            params = {"resource_params": {"action": {"name": "stop", "args": True}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Stop instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)
        return res

    def reboot(self, schedule=None):
        """reboot instance

        :param schedule: scheduler schedule definition. Ex. {'type': 'timedelta', 'minutes': 1}
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # check instance status
        if self.get_runstate() == "poweredOn":
            params = {"resource_params": {"action": {"name": "reboot", "args": True}}}
            if schedule is not None:
                params["resource_params"]["schedule"] = schedule
            res = self.update(**params)
            self.logger.info("Reboot instance %s" % self.instance.uuid)
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)
        return res

    def get_snapshots(self):
        """Get snapshots

        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = [
            {
                "snapshotId": s["id"],
                "snapshotStatus": s["status"],
                "snapshotName": s["name"],
                "createTime": s["created_at"],
            }
            for s in self.get_resource_snapshot()
        ]
        return res

    def add_snapshot(self, snapshot):
        """Add snapshot

        :param snapshot: snapshot name
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        params = {"resource_params": {"action": {"name": "add_snapshot", "args": {"snapshot": snapshot}}}}
        res = self.update(**params)
        self.logger.info("Add snapshot %s to instance %s" % (snapshot, self.instance.uuid))
        return res

    def del_snapshot(self, snapshot):
        """Delete snapshot

        :param snapshot: snapshot id
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.exists_snapshot(snapshot) is False:
            raise ApiManagerError("snapshot %s does not exist" % snapshot)

        params = {"resource_params": {"action": {"name": "del_snapshot", "args": {"snapshot": snapshot}}}}
        res = self.update(**params)
        self.logger.info("Delete snapshot %s from instance %s" % (snapshot, self.instance.uuid))
        return res

    def revert_snapshot(self, snapshot):
        """Revert snapshot

        :param snapshot: snapshot id
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.exists_snapshot(snapshot) is False:
            raise ApiManagerError("snapshot %s does not exist" % snapshot)

        if self.is_last_snapshot(snapshot) is False:
            raise ApiManagerError(
                "snapshot %s is not the last snapshot for this vm, if you want to restore this VM snapshot, remove the others first"
                % snapshot
            )

        params = {"resource_params": {"action": {"name": "revert_snapshot", "args": {"snapshot": snapshot}}}}
        res = self.update(**params)
        self.logger.info("Revert snapshot %s to instance %s" % (snapshot, self.instance.uuid))
        return res

    def is_monitoring_enabled(self):
        """Check if monitoring is enabled

        :return: True or False
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.resource is not None:
            return dict_get(self.resource, "attributes.monitoring_enabled", default=False)
        return False

    def is_logging_enabled(self):
        """Check if logging is enabled

        :return: True or False
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.resource is not None:
            return dict_get(self.resource, "attributes.logging_enabled", default=False)
        return False

    def is_backup_enabled(self):
        """Check if backup is enabled

        :return: True or False
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.resource is not None:
            return dict_get(self.resource, "attributes.backup_enabled", default=False)
        return False

    def get_job_restore_points(self, data_search):
        """Get backup job restore points

        :return: backup resource points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.instance.verify_permisssions("view")

        restore_points, restore_point_total = self.get_resource_backup_job_restore_points(data_search)
        restore_points = [self.aws_restore_point_info(item) for item in restore_points]
        self.logger.debug(
            "get compute instance %s backup resource points: %s" % (self.instance.uuid, truncate(restore_points))
        )
        return restore_points, restore_point_total

    def get_backup_restores(self, restore_point):
        """Get backup info

        :param restore_point: restore point id
        :return: backup restores list
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.instance.verify_permisssions("view")

        restores = self.get_resource_backup_restores(restore_point)
        if restores is not None:
            res = restores

        self.logger.debug("get compute instance %s backup restores: %s" % (self.instance.uuid, truncate(res)))
        return res

    def check_restore_point(self, restore_point, accepted_status=None):
        """check if backup restore point exists

        :param restore_point: restore_point id
        :param accepted_status: list of restore point accepted status. ex ['available', 'error']
        :return: True if exists
        """
        if accepted_status is None:
            accepted_status = ["available"]

        restore_points = self.get_resource_backup_job_restore_points({})
        for s in restore_points:
            if s["id"] != restore_point:
                self.logger.debug("+++++ id: %s - restore_point: %s" % (s["id"], restore_point))

            if s["status"] in accepted_status:
                pass
            else:
                self.logger.debug("+++++ status: %s - accepted_status: %s" % (s["status"], accepted_status))

        rps = [s for s in restore_points if s["id"] == restore_point and s["status"] in accepted_status]
        if len(rps) > 0:
            return rps[0]
        return None

    def restore_from_backup(self, restore_point, instance_name):
        """restore from backup

        :param restore_point: restore point id
        :param instance_name: restored instance name
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        objid = "//".join(self.instance.objid.split("//")[:-1])
        self.controller.check_authorization(self.instance.objtype, self.instance.objdef, objid, "insert")

        service_definition_id = self.instance.service_definition_id
        account_id = self.instance.account_id
        data = deepcopy(self.get_config("instance"))
        security_groups = self.resource.get("security_groups", [])
        block_device_mapping = self.resource.get("block_device_mapping", [])

        # for debug
        for v in block_device_mapping:
            volume_size = v.get("volume_size")
            self.logger.debug("+++++ restore_from_backup - volume_size: %s" % volume_size)

        data.update(
            {
                "InstanceType": service_definition_id,
                "Name": instance_name,
                "SecurityGroupId_N": [
                    self.controller.get_service_instance_by_resource_uuid(s["uuid"]).uuid for s in security_groups
                ],
                "BlockDeviceMapping_N": [
                    {
                        "Ebs": {
                            "deleteOnTermination": True,
                            "VolumeSize": v.get("volume_size", None),
                        }
                    }
                    for v in block_device_mapping
                ],
                "RestoreFromBackup": True,
                "BackupInstance": self.instance.resource_uuid,
                "RestorePoint": restore_point,
            }
        )
        data = {"instance": data}

        # check account
        (
            account,
            parent_plugin,
        ) = self.controller.check_service_type_plugin_parent_service(account_id, ApiComputeService.plugintype)
        data["computeZone"] = parent_plugin.resource_uuid

        if self.check_restore_point(restore_point, accepted_status=["available"]) is None:
            raise ApiManagerError("restore point %s does not exist or it is in a wrong status" % restore_point)

        # check quotas
        name = instance_name
        desc = instance_name
        inst = self.controller.add_service_type_plugin(
            service_definition_id,
            account_id,
            name=name,
            desc=desc,
            parent_plugin=parent_plugin,
            instance_config=data,
        )
        self.logger.info(
            "restore instance %s from backup restore point %s on instance: %s"
            % (self.instance.uuid, restore_point, inst.instance.uuid)
        )

        return inst

    def enable_monitoring(self, templates):
        """enable monitoring

        :param templates: templates
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        params = {
            "resource_params": {
                "action": {
                    "name": "enable_monitoring",
                    "args": {"templates": templates},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("enable monitoring on instance %s" % self.instance.uuid)
        return res

    def disable_monitoring(self):
        """disable monitoring

        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        params = {"resource_params": {"action": {"name": "disable_monitoring", "args": {}}}}
        res = self.update(**params)
        self.logger.info("disable monitoring on instance %s" % self.instance.uuid)
        return res

    def enable_logging(self, files, pipeline):
        """enable logging [DEPRECATED]

        :param files: log files to be forwarded
        :param pipeline: log collector port number
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        params = {
            "resource_params": {
                "action": {
                    "name": "enable_logging",
                    "args": {"files": files, "logstash_port": pipeline},
                }
            }
        }
        res = self.update(**params)
        self.logger.info("enable logging to instance %s" % self.instance.uuid)
        return res

    def disable_logging(self):
        """disable logging [DEPRECATED]

        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        params = {"resource_params": {"action": {"name": "disable_logging", "args": {}}}}
        res = self.update(**params)
        return res

    def manage_user(self, user_params):
        """Manage user. Add, delete, change password

        :param user_params: dict with action params
        :param user_params.Nvl_Action: Instance user action. Can be add, delete or set-password
        :param user_params.Nvl_Name: The instance user name
        :param user_params.Nvl_Password: he instance user password. Required with action add and set-password
        :param user_params.Nvl_SshKey: The instance user ssh key id. Required with action add
        :return: update params
        """
        # check instance status
        if self.get_runstate() == "poweredOn":
            action = user_params.get("Nvl_Action")
            user_name = user_params.get("Nvl_Name")
            if action == "add":
                user_pwd = user_params.get("Nvl_Password")
                user_ssh_key = user_params.get("Nvl_SshKey")
                params = {
                    "action": {
                        "name": "add_user",
                        "args": {
                            "user_name": user_name,
                            "user_pwd": user_pwd,
                            "user_ssh_key": user_ssh_key,
                        },
                    }
                }
                self.logger.info("Add user %s in instance %s" % (user_name, self.instance.uuid))
            elif action == "delete":
                params = {"action": {"name": "del_user", "args": {"user_name": user_name}}}
                self.logger.info("Delete user %s in instance %s" % (user_name, self.instance.uuid))
            elif action == "set-password":
                user_pwd = user_params.get("Nvl_Password")
                params = {
                    "action": {
                        "name": "set_user_pwd",
                        "args": {"user_name": user_name, "user_pwd": user_pwd},
                    }
                }
                self.logger.info("Delete user %s in instance %s" % (user_name, self.instance.uuid))
        else:
            raise ApiManagerError("Instance %s is not in a correct state" % self.instance.uuid)
        return {"resource_params": params}

    #
    # resource client method
    #
    def get_simple_runstate(self):
        """Get simple resource runstate
        :return: resource runstate
        :rtype: str
        """
        resource = self.get_resource()
        runstate = resource.get("runstate")
        self.logger.debug("Get instance %s simple runstate: %s" % (self.instance.uuid, runstate))
        return runstate

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
            uri = "/v1.0/nrs/provider/instances/%s" % uuid
            instance = self.controller.api_client.admin_request("resource", uri, "get", data="").get("instance")
        self.logger.debug("Get compute instance resource: %s" % truncate(instance))
        return instance

    @trace(op="view")
    def list_resources(self, zones=None, uuids=None, tags=None, page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if zones is not None:
            data["parent_list"] = ",".join(zones)
        if uuids is not None:
            data["uuids"] = ",".join(uuids)
        if tags is not None:
            data["tags"] = ",".join(tags)
        self.logger.debug("list_resources %s" % data)
        instances = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/instances",
            "get",
            data=urlencode(data),
            timeout=600,
        ).get("instances", [])
        self.logger.debug("Get compute instance resources: %s" % truncate(instances))
        return instances

    @trace(op="view")
    def get_resource_console(self):
        """Get resource native console

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        uuid = self.instance.resource_uuid
        uri = "/v1.0/nrs/provider/instances/%s/console" % uuid
        res = self.controller.api_client.admin_request("resource", uri, "get", data="").get("console")
        self.logger.debug("Get compute instance console: %s" % truncate(res))
        return res

    @trace(op="view")
    def get_resource_snapshot(self):
        """Get resource snapshots

        :return: list of snapshots
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        snapshots = []
        if self.instance.resource_uuid is not None:
            uri = "/v1.0/nrs/provider/instances/%s/snapshots" % self.instance.resource_uuid
            snapshots = self.controller.api_client.admin_request("resource", uri, "get", data="").get("snapshots")
        self.logger.debug("Get compute instance resource snapshots: %s" % truncate(snapshots))
        return snapshots

    def exists_snapshot(self, snapshot):
        """check if snapshot exists

        :param snapshot: snapshot id
        :return: True if exists
        """
        if len([s for s in self.get_resource_snapshot() if s["id"] == snapshot]) > 0:
            return True
        return False

    def is_last_snapshot(self, snapshot):
        """check if snapshot is the last one

        :param snapshot: snapshot id
        :return: True if exists
        """
        snapshots = self.get_snapshots()
        if len(snapshots) > 0:
            max_snapshot = max(snapshots, key=lambda x: x["createTime"])
            if max_snapshot["snapshotId"] == snapshot:
                return True
            return False
        return False

    @trace(op="view")
    def get_resource_backup_job_restore_points(self, data_search):
        """Get resource backup

        :return: backup restore points
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        restore_points = None
        if self.instance.resource_uuid is not None and data_search is not None:
            data = {
                "size": data_search.get("size", -1),
                "page": data_search.get("page", 0),
            }
            uri = "/v1.0/nrs/provider/instances/%s/backup/restore_points" % self.instance.resource_uuid
            res = self.controller.api_client.admin_request("resource", uri, "get", data=data)
            restore_points = res.get("restore_points", [])
            restore_point_total = res.get("restore_point_total", 0)
        self.logger.debug("Get compute instance resource backup restore points: %s" % truncate(restore_points))
        return restore_points, restore_point_total

    @trace(op="view")
    def get_resource_backup_restores(self, restore_point):
        """Get resource backup restores

        :param restore_point: restore point id
        :return: backup info
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        backup = None
        if self.instance.resource_uuid is not None:
            uri = "/v1.0/nrs/provider/instances/%s/backup/restore_points/%s/restores" % (
                self.instance.resource_uuid,
                restore_point,
            )
            restores = self.controller.api_client.admin_request("resource", uri, "get", data="")
        self.logger.debug("Get compute instance resource backup restores: %s" % truncate(backup))
        return restores

    @trace(op="insert")
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        volume_type = args[0].pop("volume_type", None)
        restore_from_backup = args[0].pop("restore_from_backup", False)

        if restore_from_backup is True:
            # restore instance from backup
            try:
                restore_point = args[0].get("restore_point")
                instance_name = args[0].get("name")
                backup_instance_resource_uuid = args[0].get("backup_instance_resource_uuid")
                data = {
                    "action": {
                        "restore_from_backup": {
                            "restore_point": restore_point,
                            "instance_name": instance_name,
                        }
                    }
                }
                uri = "/v1.0/nrs/provider/instances/%s/actions" % backup_instance_resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                # uuid = res.get('uuid', None)
                taskid = res.get("taskid", None)
                self.logger.debug("Create compute instance resource - START")
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                uuid = self.get_task_result(taskid)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Create compute instance resource: %s - STOP" % uuid)

            # set resource uuid
            if uuid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.logger.debug("Update compute instance resource: %s" % uuid)

        else:
            # create a new instance
            try:
                uri = "/v1.0/nrs/provider/instances"
                data = {"instance": args[0]}
                res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
                uuid = res.get("uuid", None)
                taskid = res.get("taskid", None)
                self.logger.debug("Create compute instance resource: %s - START" % uuid)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # set resource uuid
            if uuid is not None and taskid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Create compute instance resource: %s - STOP" % uuid)

        # import volumes as service instances
        self.__import_volumes_from_resource()

        return uuid

    @trace(op="update")
    def update_resource(self, task, *args, **kvargs):
        """Update resource

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
                if action is not None:
                    data = {"action": {action.get("name"): action.get("args")}}
                    uri = "/v1.0/nrs/provider/instances/%s/actions" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Update compute instance action resources: %s" % res)

            # single action
            action = kvargs.pop("action", None)
            if action is not None:
                data = {"action": {action.get("name"): action.get("args")}}
                uri = "/v1.0/nrs/provider/instances/%s/actions" % self.instance.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Update compute instance action resources: %s" % res)

            # base update
            elif len(kvargs.keys()) > 0:
                data = {"instance": kvargs}
                uri = "/v1.0/nrs/provider/instances/%s" % self.instance.resource_uuid

                res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
                taskid = res.get("taskid", None)
                if taskid is not None:
                    self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
                self.logger.debug("Update compute instance resources: %s" % res)

        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=str(ex))
            raise ApiManagerError(str(ex))
        return True

    def __import_volumes_from_resource(self):
        """Create ApiComputeVolume instances from resource block devices"""
        # get ApiComputeInstance resource
        resource = self.get_resource()
        blocks = resource.get("block_device_mapping", [])

        account_id = self.instance.account_id
        inst_name = self.instance.name

        # create ApiComputeVolume instance
        for block in blocks:
            # get volume
            volume_resource_id = block.get("id")
            uri = "/v1.0/nrs/provider/volumes/%s" % volume_resource_id
            volume_resource = self.controller.api_client.admin_request("resource", uri, "get").get("volume")
            self.logger.debug("Get compute volume %s resource: %s" % (volume_resource_id, truncate(volume_resource)))

            # get volume type
            volume_type_resource_name = dict_get(volume_resource, "flavor.name")
            volume_type = self.get_volume_type_by_resource(volume_type_resource_name).uuid

            parent_plugin = self.get_parent()

            # create volume service instance
            service_definition_id = volume_type
            name = "%s-volume-%s" % (inst_name, block.get("boot_index"))
            desc = name
            data = {
                "volume": {
                    "owner_id": account_id,
                    "VolumeType": volume_type,
                    "SnapshotId": None,
                    "Size": volume_resource.get("size"),
                    "Iops": -1,
                    "AvailabilityZone": dict_get(resource, "availability_zone.name"),
                    "MultiAttachEnabled": False,
                    "Encrypted": volume_resource.get("encrypted"),
                    "Nvl_Name": name,
                },
                "type": dict_get(resource, "hypervisor"),
                "computeZone": parent_plugin.resource_uuid,
            }

            # check service instance already exists
            insts, tot = self.controller.get_service_type_plugins(resource_uuid=volume_resource_id, with_perm_tag=False)

            # create service instance if it does not already exist
            if tot == 0:
                inst = self.controller.add_service_type_plugin(
                    service_definition_id,
                    account_id,
                    name=name,
                    desc=desc,
                    parent_plugin=parent_plugin,
                    instance_config=data,
                    resource_uuid=volume_resource_id,
                )
                inst.update_status(SrvStatusType.ACTIVE)
                self.logger.debug("Create compute volume %s from resource %s" % (inst, block.get("id")))

    @trace(op="update")
    def patch_resource(self, task, *args, **kvargs):
        """Patch resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.__import_volumes_from_resource()
        return self.instance.uuid

    def disable_resource_monitoring(self, task):
        """Disable resource monitoring. Invoked by delete_resource()

        :param task: celery task reference
        :return:
        """
        uuid = self.instance.resource_uuid
        if uuid is not None:
            uri = "/v1.0/nrs/provider/instances/%s/actions" % uuid
            data = {"action": {"disable_monitoring": {"deregister_only": True}}}
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("disable monitoring on instance %s" % self.instance.uuid)

    @trace(op="delete")
    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # disable monitoring
        resource = self.get_resource(self.instance.resource_uuid)
        monitoring_enabled = dict_get(resource, "attributes.monitoring_enabled")
        self.logger.debug("delete_resource - monitoring_enabled %s" % monitoring_enabled)
        if monitoring_enabled is True:
            self.logger.debug("delete_resource - disable_resource_monitoring")
            self.disable_resource_monitoring(task)

        # delete resource
        res = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

        return res


class ApiComputeKeyPairs(ApiServiceTypePlugin):
    plugintype = "ComputeKeyPairs"
    objname = "keypair"
    key_type = None
    key_bits = None

    keyMaterial = None

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)
        self.resourceInfo = None

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    @staticmethod
    def get_ssh_keys_idx(controller: ServiceController, ssh_key_names=None):
        if ssh_key_names is None:
            return []
        data = {"key_names": ssh_key_names, "size": -1, "page": 0}
        data = urlencode(data)
        uri = "/v1.0/gas/keys"
        keys = controller.api_client.admin_request("ssh", uri, "get", data=data).get("keys", [])
        return {k["name"]: k for k in keys}

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List[ApiComputeKeyPairs],
        *args,
        **kvargs,
    ) -> List[ApiComputeKeyPairs]:
        """
        Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        ssh_key_names = []
        for entity in entities:
            ssh_key_names.append(entity.instance.name)
            entity.account = account_idx.get(f"{entity.instance.account_id}")
        ssh_keys_idx = ApiComputeKeyPairs.get_ssh_keys_idx(controller, ssh_key_names)
        for entity in entities:
            ent_inst = entity.instance
            ent_inst_name = ent_inst.name
            ssh_key = ssh_keys_idx.get(f"{ent_inst_name}")
            if ssh_key is None:
                self.logger.error(f"Compute key pair {ent_inst.uuid} has no ssh nodes with name {ent_inst_name}")
                continue
            entity.key_type = ssh_key.get("type")
            entity.key_bits = ssh_key.get("bits")
        return entities

    def post_get(self):
        """
        Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        self.account = self.controller.get_account(str(self.instance.account_id))

    def aws_info(self):
        """
        Get info as required by aws api

        :return:
        """
        instance_item = {}
        inst = self.instance
        inst_name = inst.name
        instance_item["keyName"] = inst.name
        instance_item["nvl-keyId"] = inst.uuid
        instance_item["keyFingerprint"] = self.get_config("keyFingerprint")
        instance_item["nvl-ownerAlias"] = self.account.name
        instance_item["nvl-ownerId"] = self.account.uuid
        instance_item["bits"] = self.key_bits
        instance_item["type"] = self.key_type
        return instance_item

    def aws_create_info(self):
        """Get info as required by aws api

        :return:
        """
        instance_item = {}
        instance_item["keyName"] = self.instance.name
        instance_item["keyFingerprint"] = self.get_config("keyFingerprint")
        instance_item["keyMaterial"] = self.keyMaterial
        return instance_item

    def aws_import_info(self):
        """Get info as required by aws api

        :return:
        """
        instance_item = {}
        instance_item["keyName"] = self.instance.name
        instance_item["keyFingerprint"] = self.get_config("keyFingerprint")
        return instance_item

    def __add_resource(self, **params):
        """ """
        # get parent account
        account = self.controller.get_account(self.instance.account_id)
        try:
            bits = 4096
            key_type = "rsa"

            # generating private key
            prv = RSAKey.generate(bits=bits)
            file_obj = StringIO()
            prv.write_private_key(file_obj)

            # get finger print of private key
            key_fingerprint = ApiComputeKeyPairsHelper(self).get_private_rsa_fingerprint(
                key_file_obj=file_obj.getvalue()
            )
            priv_key = b64encode(ensure_binary(file_obj.getvalue()))
            file_obj.close()

            # get public key
            ssh_key = "%s %s" % (prv.get_name(), prv.get_base64())
            pub_key = b64encode(ensure_binary(ssh_key))

            # if account is managed store private key in ssh module
            key_name = self.get_config("KeyName")
            data = {
                "key": {
                    "name": key_name,
                    "desc": key_name,
                    "pub_key": ensure_text(pub_key),
                    "type": key_type,
                    "bits": bits,
                }
            }
            if account.managed is True:
                data["key"]["priv_key"] = ensure_text(priv_key)

            ssh_key_name = key_name
            self.set_config("SshKeyName", ssh_key_name)
            res = self.add_resource(data)

            # set key fingerprint
            self.set_config("keyFingerprint", key_fingerprint)

            # save private key
            b64_priv_key = ensure_text(b64decode(ensure_binary(priv_key)))
            self.keyMaterial = b64_priv_key

            return params
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

    def __import_resource(self, **params):
        """ """
        bits = 4096
        key_type = "rsa"
        key_name = self.get_config("KeyName")
        data = {
            "key": {
                "name": key_name,
                "desc": key_name,
                "priv_key": "",
                "pub_key": params.get("public_key_material"),
                "type": key_type,
                "bits": bits,
            }
        }
        ssh_key_name = key_name
        self.set_config("SshKeyName", ssh_key_name)
        res = self.add_resource(data)
        # get the updated key
        res = self.get_resource(key_name)

        # we provide only MD5 public key fingerprint of public key
        ssh_fingerprint = hashlib.md5(ensure_binary(res.get("pub_key"))).hexdigest()
        printableFingerprint = ":".join(a + b for a, b in zip(ssh_fingerprint[::2], ssh_fingerprint[1::2]))

        # set key fingerprint
        self.set_config("keyFingerprint", printableFingerprint)
        return params

    #
    # resource client method
    #
    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :param params.id: inst.oid,
        :param params.uuid: inst.uuid,
        :param params.objid: inst.objid,
        :param params.name: name,
        :param params.desc: desc,
        :param params.attribute: None,
        :param params.tags: None,
        :param params.resource_id: resource_id
        :param params.action: input action
        :return: resource input params
        :raise ApiManagerError:
        """
        action = params.get("action")

        if action == "ImportKeyPair":
            return self.__import_resource(**params)
        else:
            return self.__add_resource(**params)

    def post_create(self, **params):
        """Post create function. Use this after service creation
        Extend this function to execute some operation after entity was created.

        :param params: input params
        :return: None
        :raise ApiManagerError:
        """
        return None

    def pre_delete(self, **params):
        """Pre delete function. Use this function to manipulate and
        validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        key_name = self.instance.name
        res = self.remove_resource(key_name)
        return params

    def pre_update(self, **params):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        return params

    @trace(op="view")
    def has_resource(self, key_name):
        """Get ssh resource visibility

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            ssh_key_name = self.get_config("SshKeyName")
            self.get_resource(ssh_key_name)
            return True
        except BaseException:
            raise ApiManagerError("Ssh key %s does not exist or you are not authorized to use it" % key_name)

    @trace(op="insert")
    def add_resource(self, data):
        """Add ssh key pair

        :param account_id: identifier id, uuid or name of account
        :param key_name: ssh key name
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            uri = "/v1.0/gas/keys"
            res = self.controller.api_client.admin_request("ssh", uri, "post", data=data)
            key_uuid = res.get("uuid")

            # get user from auth
            uri = "/v1.0/nas/users"
            data = {"email": operation.user[0]}
            users = self.controller.api_client.admin_request("auth", uri, "get", data=data).get("users")

            # assign ssh key to a group or a user
            user = users[0]["uuid"]
            data = {"user": {"user_id": user, "role": "master"}}
            uri = "/v1.0/gas/keys/%s/users" % key_uuid
            res = self.controller.api_client.admin_request("ssh", uri, "post", data=data)
            self.logger.debug("Set authorization to ssh key %s for user %s with role master" % (key_uuid, user))
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

        self.logger.debug("Post ssh key: %s" % truncate(res))
        return res

    @trace(op="view")
    def get_resource(self, key_name):
        """Get ssh key pair info

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            ssh_key_name = self.get_config("SshKeyName")
            uri = "/v1.0/gas/keys/%s" % ssh_key_name
            key = self.controller.api_client.admin_request("ssh", uri, "get", data="").get("key")
            self.logger.debug("Get ssh key: %s" % truncate(key))
        except BeehiveApiClientError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

        return key

    @trace(op="view")
    def list_resources(self, page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            data = {"size": size, "page": page}
            data = urlencode(data)
            uri = "/v1.0/gas/keys"
            keys = self.controller.api_client.admin_request("ssh", uri, "get", data=data).get("keys", [])
        except BeehiveApiClientError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)
        self.logger.debug("Get ssh keys: %s" % truncate(keys))
        return keys

    def remove_resource(self, key_name):
        """remove ssh key pair

        :param account_id: identifier id, uuid or name of account
        :param key_name: ssh key name
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            ssh_key_name = self.get_config("SshKeyName")
            uri = "/v1.0/gas/keys/%s" % ssh_key_name
            res = self.controller.api_client.admin_request("ssh", uri, "delete")
        except BeehiveApiClientError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

        self.logger.debug("delete ssh keys: %s" % key_name)
        return True


class ApiComputeSecurityGroup(AsyncApiServiceTypePlugin):
    plugintype = "ComputeSecurityGroup"
    objname = "securitygroup"

    class state_enum(object):
        """enumerate state name esposed by api"""

        pending = "pending"
        available = "available"
        deregistering = "deregistering"
        deregistered = "deregistered"
        transient = "transient"
        transient = "transient"
        error = "error"
        updating = "updating"
        unknown = "unknown"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return ApiServiceTypePlugin.info(self)

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List[ApiComputeSecurityGroup],
        *args,
        **kvargs,
    ):
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)
        security_group_idx = controller.get_service_instance_idx(ApiComputeSecurityGroup.plugintype)

        # get resources
        zones = []
        resources = []
        account_id_list = []
        vpc_list = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.account_idx = account_idx
            entity.vpc_idx = vpc_idx
            entity.security_group_idx = security_group_idx
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

            config = entity.get_config("security_group")

            if config is not None:
                controller.logger.warn(config.get("VpcId"))
                vpc = vpc_idx.get(config.get("VpcId"))
                vpc_list.append(vpc.resource_uuid)

        if len(resources) > 3:
            resources = []
        resources_list = ApiComputeSecurityGroup(controller).list_resources(vpcs=vpc_list, uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

        # assign resources
        for entity in entities:
            resource = resources_idx.get(entity.instance.resource_uuid, None)
            entity.resource = resource
            if resource is not None:
                entity.rules = resource.pop("rules", [])
            else:
                entity.rules = []
                # entity.rules = rule_resource_list

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.DELETING: self.state_enum.deregistering,  # 'deregistering',
            SrvStatusType.DELETED: self.state_enum.deregistered,  # 'deregistered',
            SrvStatusType.DRAFT: self.state_enum.transient,  # 'transient',
            SrvStatusType.CREATED: self.state_enum.transient,  # 'transient',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error',
            SrvStatusType.UPDATING: self.state_enum.updating,  # 'updating'
        }
        return mapping.get(state, self.state_enum.unknown)

    def set_service_info(self, ip_protocol, ip_from_port_range, ip_to_port_range):
        """Get rule printed info

        :param ip_protocol: protocol
        :param ip_from_port_range: from port
        :param ip_to_port_range: to port
        :return:
        """
        if ip_protocol == "1":
            if ip_from_port_range == -1:
                service_info = {"subprotocol": "-1", "protocol": ip_protocol}
            else:
                service_info = {
                    "subprotocol": ("%s" % ip_from_port_range),
                    "protocol": ip_protocol,
                }
        elif ip_from_port_range == -1:
            service_info = {"port": "*", "protocol": ip_protocol}
        elif ip_from_port_range == ip_to_port_range:
            service_info = {
                "port": ("%s" % ip_from_port_range),
                "protocol": ip_protocol,
            }
        else:
            service_info = {
                "port": ("%s-%s" % (ip_from_port_range, ip_to_port_range)),
                "protocol": ip_protocol,
            }
        return service_info

    def get_ipv_range_list(self, data, range_type):
        """Get list of ip range

        :param data: input data to parse
        :param range_type: type of range. Can be IpRanges, Ipv6Ranges
        :return: list of ip range
        """
        ipv_range_list = []

        ip_ranges = data.get(range_type, [])
        for ip_range in ip_ranges:
            cidrip = ip_range.get("CidrIp", None)
            if cidrip is not None:
                try:
                    ipaddress.ip_network(cidrip)
                except ValueError as ex:
                    self.logger.error("Add Rule", exc_info=2)
                    raise ApiManagerError(f"Error parsing CidrIp {cidrip}: {ex.__str__()}", code=400)
                ipv_range_list.append(cidrip)

        return ipv_range_list

    def get_group_list(self, data):
        """Get list of security group

        :param data: input data to parse
        :return: list of securit group
        """
        group_list = []

        for user_sg_data in data.get("UserIdGroupPairs", []):
            # manage source of type SecurityGroup by id
            if user_sg_data.get("GroupName", None) is not None:
                sg_perm_plugin = self.controller.get_service_type_plugin(
                    user_sg_data.get("GroupName"),
                    plugin_class=ApiComputeSecurityGroup,
                    details=False,
                )
                sg_perm_inst = sg_perm_plugin.instance
                group_list.append(sg_perm_inst.resource_uuid)
        return group_list

    def get_rule_from_filter(self, data, rule_type):
        """Get list of rules from a filter

        :param data: input data to parse
        :param rule_type: type of rule. Can bu RULE_GROUP_INGRESS, RULE_GROUP_EGRESS
        :return: list of rule
        """
        ip_permission_list = data.get("IpPermissions_N", [])
        if not ip_permission_list:
            raise ApiManagerError("The parameter IpPermissions.N is empty, provide at least  an item", 400)

        # only one filter is supported for the moment
        ip_permission = ip_permission_list[0]

        # check ports and protocol
        ip_from_port_range = ip_permission.get("FromPort")
        ip_to_port_range = ip_permission.get("ToPort")

        if ip_permission.get("IpProtocol") == "-1":
            service = "*:*"
        else:
            proto = self.convert_rule_to_resource_proto(ip_permission.get("IpProtocol"))
            if proto == "1" and (ip_from_port_range == -1 or ip_to_port_range == -1):
                port = "-1"
            elif ip_from_port_range == -1 or ip_to_port_range == -1:
                port = "*"
            elif ip_from_port_range >= ip_to_port_range:
                port = ip_to_port_range
            else:
                port = "%s-%s" % (ip_from_port_range, ip_to_port_range)
            service = "%s:%s" % (proto, port)

        # check source/destionation
        if len(ip_permission.get("UserIdGroupPairs", [])) > 0 and (
            len(ip_permission.get("IpRanges", [])) > 0 or len(ip_permission.get("Ipv6Ranges", [])) > 0
        ):
            raise ApiManagerError(
                "Only one of IpPermissions.N.UserIdGroupPairs, IpPermissions.N.IpRanges, "
                "IpPermissions.N.Ipv6Ranges should be supplied",
                400,
            )
        if (
            len(ip_permission.get("UserIdGroupPairs", [])) == 0
            and len(ip_permission.get("IpRanges", [])) == 0
            and len(ip_permission.get("Ipv6Ranges", [])) == 0
        ):
            raise ApiManagerError(
                "One of IpPermissions.N.UserIdGroupPairs, IpPermissions.N.IpRanges, "
                "IpPermissions.N.Ipv6Ranges should be supplied",
                400,
            )

        # get cidr ipv4
        ipv4_range_list = self.get_ipv_range_list(ip_permission, "IpRanges")
        if len(ipv4_range_list) > 0:
            others = ["Cidr:%s" % i for i in ipv4_range_list]

        # get cidr ipv6
        ipv6_range_list = self.get_ipv_range_list(ip_permission, "Ipv6Ranges")
        if len(ipv6_range_list) > 0:
            others = ["Cidr:%s" % i for i in ipv6_range_list]

        others = []
        # get security group
        group_list = self.get_group_list(ip_permission)
        if len(group_list) > 0:
            others = ["SecurityGroup:%s" % i for i in group_list]

        rules = self.list_rule_resources(others, service, rule_type)
        self.logger.debug("Get rules from filter: %s" % truncate(rules))
        return rules

    def get_rule_ip_permission(self, data, sg_inst, rule_type):
        """Get rule ip permission

        :param data: input data to parse
        :param sg_inst: security group instance
        :param rule_type: type of rule. Can bu RULE_GROUP_INGRESS, RULE_GROUP_EGRESS
        :return: list of ip permissions
        """
        sg_perm_inst = None
        sg_perm_inst_value = None
        sg_perm_type = "SecurityGroup"
        sg_perm_user = None
        vpc_perm_inst = None
        # ip_from_port_range = -1
        # ip_to_port_range = -1
        # ip_protocol = '*'

        ip_permission_list = data.get("rule").get("IpPermissions_N", [])
        if not ip_permission_list:
            raise ApiManagerError("The parameter IpPermissions.N is empty, provide at least  an item", 400)

        # TODO management IpPermissions_N array object
        for ip_permission in ip_permission_list:
            if not ip_permission.get("UserIdGroupPairs", []) and len(ip_permission.get("IpRanges", [])) == 0:
                sg_perm_inst = sg_inst
                sg_perm_inst_value = sg_perm_inst.resource_uuid

            if len(ip_permission.get("UserIdGroupPairs", [])) > 0 and (
                len(ip_permission.get("IpRanges", [])) > 0 or len(ip_permission.get("Ipv6Ranges", [])) > 0
            ):
                raise ApiManagerError(
                    "can be supplied parameter IpPermissions.N.UserIdGroupPairs or alternatively "
                    "IpPermissions.N.IpRanges | IpPermissions.N.Ipv6Ranges",
                    400,
                )

            # convert protocol
            ip_protocol = self.convert_rule_to_resource_proto(ip_permission.get("IpProtocol"))
            ip_from_port_range = ip_permission.get("FromPort")
            ip_to_port_range = ip_permission.get("ToPort")

            if ip_from_port_range == -1:
                ip_to_port_range = -1
                self.logger.debug(
                    "parameters IpPermissions.N.ToPort has been set to IpPermissions.N.FromPort with " "-1 value"
                )
            elif ip_from_port_range > ip_to_port_range:
                raise ApiManagerError(
                    "Parameter IpPermissions.N.FromPort and IpPermissions.N.ToPort have a wrong " "value",
                    400,
                )

            if ip_permission.get("IpProtocol") == "-1" and (ip_from_port_range != -1 or ip_to_port_range != -1):
                raise ApiManagerError(
                    "Parameter IpPermissions.N.Protocol -1 accepts only default port value -1 ",
                    400,
                )

            # set service
            service = self.set_service_info(ip_protocol, ip_from_port_range, ip_to_port_range)

            # manage source of type SecurityGroup
            if ip_permission.get("UserIdGroupPairs", []):
                user_sg_data_list = ip_permission.get("UserIdGroupPairs", [])
                # TODO Management of UserIdGroupPairs array
                for user_sg_data in user_sg_data_list:
                    # manage source of type SecurityGroup by id
                    if user_sg_data.get("GroupName", None) is not None:
                        sg_perm_plugin = self.controller.get_service_type_plugin(
                            user_sg_data.get("GroupName"),
                            plugin_class=ApiComputeSecurityGroup,
                            details=False,
                        )
                        sg_perm_inst = sg_perm_plugin.instance
                        sg_perm_inst_value = sg_perm_inst.resource_uuid

            ipv_range_list = ApiComputeSecurityGroup(self.controller).get_ipv_range_list(ip_permission, "IpRanges")
            # ipv_range_list.extend(ApiComputeSecurityGroup(controller).get_ipv_range_list(ip_permission, 'Ipv6Ranges'))
            # TODO Management array value ipv4 or ipv6
            for ipv_range in ipv_range_list:
                sg_perm_inst_value = ipv_range
                sg_perm_type = "Cidr"
                break

        # create rule
        rule = {}
        if rule_type == __RULE_GROUP_EGRESS__:
            rule["source"] = {"type": "SecurityGroup", "value": sg_inst.resource_uuid}
            rule["destination"] = {"type": sg_perm_type, "value": sg_perm_inst_value}
        else:
            rule["source"] = {"type": sg_perm_type, "value": sg_perm_inst_value}
            rule["destination"] = {
                "type": "SecurityGroup",
                "value": sg_inst.resource_uuid,
            }
        rule["service"] = service

        return rule

    def convert_rule_proto(self, proto):
        mapping = {
            "-1": "-1",
            "6": "tcp",
            "17": "udp",
            "1": "icmp",
        }
        return mapping.get(str(proto), None)

    def convert_rule_to_resource_proto(self, proto):
        mapping = {
            "tcp": "6",
            "udp": "17",
            "icmp": "1",
            "-1": "*",
        }
        return mapping.get(proto, "*")

    def get_rule_info_params(self, item, item_list):
        """Get rule info params

        :param item:
        :param item_list:
        :return:
        """
        res = {}
        item_type = item.get("type")
        item_value = item.get("value")
        if item_type == "SecurityGroup":
            sg_service = self.security_group_idx.get(item_value)

            if sg_service is not None:
                res["groupId"] = sg_service.uuid
                res["userId"] = self.account_idx.get(str(sg_service.account_id)).uuid
                # custom param
                res["groupName"] = sg_service.name
                res["nvl-userName"] = self.account_idx.get(str(sg_service.account_id)).name
            else:
                res["groupId"] = ""
                res["userId"] = ""
                # custom param
                res["groupName"] = ""
                res["nvl-userName"] = ""

            item_list["groups"].append(res)
        elif item_type == "Cidr":
            res["cidrIp"] = item_value
            item_list["ipRanges"].append(res)
        return item_list

    def get_rule_info(self, resource, direction, reserved, state):
        """Get rule info

        :param sg_res_idx: security groups indexed by resource id
        :param direction: can be ingress or egress
        :param account_idx: index of account reference
        :param reserved: rule reservation
        :param state: rule state
        :param resource: dict like

            "source": {
                "type": "Cidr",
                "value": "1.1.1.0/24"
            },
            "destination": {
                "type": "SecurityGroup",
                "value": "<uuid>"
            },
            "service": {
                "protocol": "*",
                "port": "*"
            }

        :return: rule info
        """
        instance_item = {}

        service = resource.get("service", {})
        protocol = service.get("protocol", "-1")
        if protocol == "*":
            protocol = "-1"
        elif protocol == "1":
            subprotocol = service.get("subprotocol", None)
            if subprotocol is not None:
                instance_item["fromPort"] = int(subprotocol)
                instance_item["toPort"] = int(subprotocol)
        port = service.get("port", None)
        if port is not None and port != "*":
            if port.find("-") > 0:
                s_from_port, s_to_port = port.split("-")
                instance_item["fromPort"] = int(s_from_port)
                instance_item["toPort"] = int(s_to_port)
            else:
                instance_item["fromPort"] = instance_item["toPort"] = int(port)

        instance_item["ipProtocol"] = self.convert_rule_proto(protocol)
        instance_item["groups"] = []
        instance_item["ipRanges"] = []
        # instance_item['ipv6Ranges'] = []
        # instance_item['prefixListIds'] = []
        source = resource.get("source", {})
        dest = resource.get("destination", {})
        if direction == "ingress":
            instance_item = self.get_rule_info_params(source, instance_item)
        elif direction == "egress":
            instance_item = self.get_rule_info_params(dest, instance_item)

        # custom fields
        instance_item["nvl-reserved"] = reserved
        instance_item["nvl-state"] = state

        return instance_item

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        instance_item = {}

        res_uuid = None
        if isinstance(self.resource, dict):
            res_uuid = self.resource.get("uuid")
        instance_item["vpcId"] = ""
        instance_item["nvl-vpcName"] = ""
        instance_item["nvl-sgOwnerAlias"] = ""
        instance_item["nvl-sgOwnerId"] = ""
        config = self.get_config("security_group")

        if config is not None:
            vpc = self.vpc_idx.get(config.get("VpcId"))
            if vpc is not None:
                instance_item["vpcId"] = getattr(vpc, "uuid", None)
                instance_item["nvl-vpcName"] = getattr(vpc, "name", None)
                instance_item["nvl-sgOwnerAlias"] = self.account.name
                instance_item["nvl-sgOwnerId"] = self.account.uuid

        instance_item["ownerId"] = str(self.instance.account_id)
        instance_item["groupDescription"] = self.instance.desc
        instance_item["groupName"] = self.instance.name
        instance_item["groupId"] = self.instance.uuid
        instance_item["tagSet"] = []
        instance_item["ipPermissions"] = []
        instance_item["ipPermissionsEgress"] = []
        for rule in self.rules:
            state = rule.get("state", None)
            rule = rule.get("attributes", {})
            reserved = rule.get("reserved")
            rule = rule.get("configs", {})
            source = rule.get("source", {})
            dest = rule.get("destination", {})

            if dest.get("type") == "SecurityGroup" and dest.get("value") == res_uuid:
                instance_item["ipPermissions"].append(self.get_rule_info(rule, "ingress", reserved, state))
            if source.get("type") == "SecurityGroup" and source.get("value") == res_uuid:
                instance_item["ipPermissionsEgress"].append(self.get_rule_info(rule, "egress", reserved, state))

        # custom params
        instance_item["nvl-state"] = self.state_mapping(self.instance.status)
        instance_item["nvl-stateReason"] = {"nvl-code": None, "nvl-message": None}
        if instance_item["nvl-state"] == "error":
            instance_item["nvl-stateReason"] = {
                "nvl-code": 400,
                "nvl-message": self.instance.last_error,
            }

        return instance_item

    def check_rule_reservation(self, rule):
        """Check if rule is reserved. A reserved rule is created from template and can not be removed

        :param rule: rule data
        :return: True if reserved
        """
        rule = rule.get("attributes", {})
        reserved = rule.get("reserved")
        return reserved

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id
        # active_cfg = self.instance.get_main_config()

        # base quotas
        quotas = {
            "compute.security_groups": 1,
            "compute.security_group_rules": 0,
        }

        # get container
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        vpc = self.get_parent()

        # check quotas
        self.check_quotas(compute_zone, quotas)

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        # orchestrator_select_types_array = None
        # orchestrator_select_types: str = self.get_config("orchestrator_select_types")
        # if orchestrator_select_types is not None:
        #     orchestrator_select_types_array = orchestrator_select_types.split(",")

        data = {
            "container": container_id,
            "name": name,
            "desc": self.instance.desc,
            "vpc": vpc.resource_uuid,
            "compute_zone": compute_zone,
            # "orchestrator_select_types": orchestrator_select_types_array,
        }
        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    def pre_patch(self, **params) -> dict:
        """Pre patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # get service definition
        service_definition = self.controller.get_service_def(self.instance.service_definition_id)
        def_config = service_definition.get_main_config()
        rules = def_config.get_json_property("rules")

        # set rules from definition
        self.set_config("rules", rules)

        return params

    def aws_create_rule(self, security_group, rule, rule_type):
        """Create new rule using aws api

        :param security_group: source or destination security group service instance
        :param rule: rule data
        :param rule_type: rule type: ingress or egress
        :return:
        """
        res = False

        # checks authorization
        # todo: authorization must be reconsidered when use process
        self.controller.check_authorization(
            ApiServiceInstance.objtype,
            ApiServiceInstance.objdef,
            security_group.objid,
            "update",
        )

        # check rule already exists
        rules = self.get_rule_from_filter(rule, rule_type)
        if len(rules) > 0:
            raise ApiManagerError("Rule with the same parameters already exists")

        rule_data = self.get_rule_ip_permission({"rule": rule}, self.instance, rule_type)
        self.rule_factory(rule_data, reserved=False)
        return True

    def aws_delete_rule(self, security_group, rule, rule_type):
        """Delete a rule using aws api

        :param security_group: source or destination security group service instance
        :param rule: rule data
        :param rule_type: rule type: ingress or egress
        :return:
        """
        res = False

        # checks authorization
        # todo: authorization must be reconsidered when use process
        self.controller.check_authorization(
            ApiServiceInstance.objtype,
            ApiServiceInstance.objdef,
            security_group.objid,
            "update",
        )
        self.logger.warn(rule)
        # check rule already exists
        rules = self.get_rule_from_filter(rule, rule_type)
        for rule in rules:
            if self.check_rule_reservation(rule) is True:
                raise ApiManagerError("Rule is reserved and can not be deleted")

            # delete rule
            self.rule_delete_factory(rule)

        return True

    def rule_factory(self, rule, reserved=False):
        """Factory used toe create a rule using a task or a camunda process.

        :param dict rule: rule definition
        :param boolean reserved: flag for reserved rules (not deletable)
        :rtype: bool
        """
        try:
            self.logger.info("Add Rule for instance %s" % self.instance.uuid)
            process_key, template = self.get_bpmn_process_key(self.instance, ApiServiceTypePlugin.PROCESS_ADD_RULE)
            if process_key is not None and ApiServiceTypePlugin.INVALID_PROCESS_KEY != process_key:
                # asynchronous way
                data = self.prepare_add_rule_process_variables(self.instance, template, reserved=reserved, rule=rule)
                res = self.camunda_engine.process_instance_start_processkey(process_key, variables=data)
                self.logger.debug("Call bpmn process %s: %s" % (process_key, res))
                process_id = res.get("id")
                upd_data = {"bpmn_process_id": process_id}
                self.instance.update(**upd_data)
            else:
                # task creation
                params = {"resource_params": {"action": "add-rules", "rules": [rule]}}
                self.action(**params)

        except Exception:
            self.logger.error("Add Rule", exc_info=2)
            raise ApiManagerError("Error Adding rule for instance %s" % self.instance.uuid)

    def rule_delete_factory(self, rule):
        """Factory used toe delete a rule using a task or a camunda process.

        :param dict rule: rule definition
        :param boolean reserved: flag for reserved rules (not deletable)
        :rtype: bool
        """
        try:
            self.logger.info("Delete Rule for instance %s" % self.instance.uuid)
            process_key, template = self.get_bpmn_process_key(self.instance, ApiServiceTypePlugin.PROCESS_ADD_RULE)
            if process_key is not None and ApiServiceTypePlugin.INVALID_PROCESS_KEY != process_key:
                # asynchronous way TODO
                pass
            else:
                # task creation
                params = {"resource_params": {"action": "del-rules", "rules": [rule]}}
                self.action(**params)

        except Exception:
            self.logger.error("Add Rule", exc_info=2)
            raise ApiManagerError("Error removing rule for instance %s" % self.instance.uuid)

    #
    # resource client method
    #
    def list_resources(self, vpcs=[], uuids=[], page=0, size=-1):
        """List sg resource

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # todo: improve rules filter
        data = {"size": size, "page": page}
        if len(vpcs) > 0:
            data["parent_list"] = ",".join([x for x in vpcs if x is not None])
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)

        sgs = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/security_groups",
            "get",
            data=urlencode(data),
        ).get("security_groups", [])
        self.controller.logger.debug("Get compute sg resources: %s" % truncate(sgs))

        return sgs

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        compute_zone = args[0].pop("compute_zone")
        container = args[0].get("container")
        data = {"security_group": args[0]}
        try:
            uri = "/v1.0/nrs/provider/security_groups"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create security group %s resource with job %s" % (uuid, taskid))
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.controller.logger.debug("Update security group resource: %s" % uuid)

            # create rules
            rules = self.get_config("rules")
            for rule in rules:
                self.create_resource_rule(task, compute_zone, rule, container, reserved=True)
            self.logger.debug("Create security group %s resource with all rules" % uuid)

        return uuid

    def create_resource_rule(self, task, compute, rule, container, reserved=False):
        """Create rule

        :param task: celery task reference
        :param compute: computeservice resource uuid
        :param rule: rule definition
        :param container: container name
        :param reserved: flag for reserved rules (not deletable)
        :rtype: bool
        """
        # check rule contains reference to main security group
        if rule.get("source").get("value") == "<resource id of SecurityGroup>":
            rule["source"]["value"] = self.instance.resource_uuid
        if rule.get("destination").get("value") == "<resource id of SecurityGroup>":
            rule["destination"]["value"] = self.instance.resource_uuid

        name = "%s-rule-%s" % (self.instance.name, id_gen(length=8))
        rule_data = {
            "rule": {
                "container": container,
                "name": name,
                "desc": name,
                "compute_zone": compute,
                "source": rule.get("source"),
                "destination": rule.get("destination"),
                "service": rule.get("service"),
                "rule_orchestrator_types": rule.get("orchestrators"),
                "reserved": reserved,
            }
        }
        self.logger.debug("Rule data: %s" % rule_data)

        # TODO: check rule can be created
        # if reserved is False and rule.get('destination').get('type') == 'SecurityGroup':
        #     source = '%s:%s' % (rule.get('source').get('type'), rule.get('source').get('value'))
        #     dest = rule.get('destination').get('value')
        #     protocol = '%s:*' % rule.get('service').get('protocol')
        #     port = rule.get('service').get('port')
        #     self.check_rule_config_allowed(source, dest, protocol, port)

        # create rule
        res = self.controller.api_client.admin_request(
            "resource",
            "/v1.0/nrs/provider/rules",
            "post",
            data=rule_data,
            other_headers=None,
        )

        # wait job
        taskid = res.get("taskid", None)
        if taskid is not None:
            self.wait_for_task(taskid, delta=2, maxtime=600, task=task)
        else:
            raise ApiManagerError("Rule job does not started")

        self.logger.debug("Create rule resource %s in security group %s" % (rule, self.instance.uuid))
        return True

    def update_resource(self, task, *args, **kvargs):
        """Update resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return True

    def action_resource(self, task, *args, **kvargs):
        """Send action to resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        compute_zone = self.get_config("computeZone")
        container = self.get_config("container")

        # create new rules
        action = kvargs.get("action", None)
        rules = kvargs.get("rules", [])
        for rule in rules:
            if action == "add-rules":
                self.create_resource_rule(task, compute_zone, rule, container, reserved=False)
            elif action == "del-rules":
                self.delete_rule_resource(task, rule)
        return True

    def patch_resource(self, task, *args, **kvargs):
        """Patch resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        rules = self.get_config("rules")
        compute_zone = self.get_config("computeZone")
        container = self.get_config("container")
        # non serve usat precedentemente  uuid = self.instance.resource_uuid

        # create rules
        for rule in rules:
            rule_type = __RULE_GROUP_INGRESS__
            others = ["%s:%s" % (rule.get("source").get("type"), rule.get("source").get("value"))]
            if rule.get("source").get("value") == "<resource id of SecurityGroup>":
                rule_type = __RULE_GROUP_EGRESS__
                others = [
                    "%s:%s"
                    % (
                        rule.get("destination").get("type"),
                        rule.get("destination").get("value"),
                    )
                ]
            others[0] = others[0].replace("<resource id of SecurityGroup>", self.instance.resource_uuid)

            service = rule.get("service")
            if service.get("protocol") == "*":
                service = "*:*"
            else:
                service = "%s:%s" % (service.get("protocol"), service.get("port"))

            res = self.list_rule_resources(others, service, rule_type)

            if len(res) == 0:
                self.create_resource_rule(task, compute_zone, rule, container, reserved=True)
            elif res[0]["state"] == "ERROR":
                # delete ERROR rule
                self.delete_rule_resource(task, res)

                # recreate rule
                self.create_resource_rule(task, compute_zone, rule, container, reserved=True)
            else:
                self.logger.warning("Rule %s already exists" % rule)

        return True

    def list_rule_resources(self, others, service, rule_type):
        """List compute rules

        :param others:
        :param service: rule service
        :param rule_type: __RULE_GROUP_EGRESS__ or __RULE_GROUP_INGRESS__
        :return: rules
        """
        all_rules = []
        for other in others:
            if rule_type == __RULE_GROUP_EGRESS__:
                source = "SecurityGroup:%s" % self.instance.resource_uuid
                dest = other
            else:
                source = other
                dest = "SecurityGroup:%s" % self.instance.resource_uuid

            data = {"source": source, "destination": dest, "service": service}
            uri = "/v1.0/nrs/provider/rules"
            data = urlencode(data)
            rules = self.controller.api_client.admin_request("resource", uri, "get", data=data).get("rules", [])
            all_rules.extend(rules)
        return all_rules

    def check_rule_config_allowed(self, source, dest, protocol, ports):
        """Check rule_config are allowed by security group acl

        :param source: acl source. Can be *:*, Cidr:<>, Sg:<>
        :param dest: destination security group resource id
        :param protocol: acl protocol. Can be *:*, 7:*, 9:0 or tcp:*
        :param ports: comma separated list of ports, single port or ports interval
        :return: rules
        """
        data = {"source": source, "protocol": protocol, "ports": ports}
        uri = "/v1.0/nrs/provider/security_groups/%s/acls/check" % dest
        data = urlencode(data)
        res = self.controller.api_client.admin_request("resource", uri, "get", data=data).get(
            "security_group_acl_check", False
        )
        if res is False:
            raise ApiManagerError("Rule does not satisfy security group acl. It can not be created.")

    def list_all_resource_rules(self):
        """List all compute rules of the security group

        :return: rules
        """
        compute_zone = self.get_config("computeZone")

        data = {"parent_list": compute_zone, "size": -1}
        uri = "/v1.0/nrs/provider/rules"
        data = urlencode(data)
        rules = self.controller.api_client.admin_request("resource", uri, "get", data=data).get("rules", [])
        res = []
        for rule in rules:
            rule_conf = rule.get("attributes", {}).get("configs", {})
            source = rule_conf.get("source", {})
            dest = rule_conf.get("destination", {})
            if (dest.get("type") == "SecurityGroup" and dest.get("value") == self.instance.resource_uuid) or (
                source.get("type") == "SecurityGroup" and source.get("value") == self.instance.resource_uuid
            ):
                res.append(rule)
        self.logger.debug("Get security group %s rules: %s" % (self.instance.uuid, truncate(res)))
        return res

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        rules = self.list_all_resource_rules()

        # delete rules
        for rule in rules:
            self.delete_rule_resource(task, rule)

        return ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

    def delete_rule_resource(self, task, rule):
        """Delete security group rule resources

        :param task: celery task reference
        :param rule: compute zone rule uuid
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            uri = "/v1.0/nrs/provider/rules/%s" % rule.get("uuid")
            res = self.controller.api_client.admin_request("resource", uri, "delete")
            taskid = res.get("taskid", None)
            self.logger.debug("Delete compute zone rule: %s - start" % rule)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
            self.logger.debug("Delete compute zone rule: %s - stop" % rule)

        return True


class ApiComputeSubnet(AsyncApiServiceTypePlugin):
    plugintype = "ComputeSubnet"
    objname = "subnet"

    class state_enum(object):
        """enumerate state name esposed by api"""

        pending = "pending"
        available = "available"
        deregistered = "deregistered"
        transient = "transient"
        error = "error"
        unknown = "unknown"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    @staticmethod
    def customize_list(
        controller: ServiceController, entities: List[ApiComputeSubnet], *args, **kvargs
    ) -> List[ApiComputeSubnet]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        compute_service_idx = controller.get_service_instance_idx(ApiComputeService.plugintype, index_key="account_id")
        vpc_idx = controller.get_service_instance_idx(ApiComputeVPC.plugintype)

        # get resources
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.vpc_idx = vpc_idx
            entity.account = account_idx.get(account_id)
            entity.compute_service = compute_service_idx.get(account_id)
            entity.vpc = vpc_idx.get(entity.instance.get_parent_id())

        # assign resources
        for entity in entities:
            entity.resource = None

        return entities

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        self.account = self.controller.get_account(str(self.instance.account_id))
        self.vpc = self.controller.get_service_instance(self.instance.get_parent_id())

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.DELETED: self.state_enum.deregistered,  # 'deregistered',
            SrvStatusType.DRAFT: self.state_enum.transient,  # 'transient',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error'
        }
        return mapping.get(state, self.state_enum.unknown)

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        inst_service = self.instance
        instance_item = {}
        instance_item["assignIpv6AddressOnCreation"] = False
        instance_item["availableIpAddressCount"] = None
        instance_item["defaultForAz"] = True
        instance_item["mapPublicIpOnLaunch"] = False
        instance_item["tagSet"] = []

        if self.get_config("site") is not None:
            instance_item["availabilityZone"] = self.get_config("site")
            instance_item["cidrBlock"] = self.get_config("cidr")

        instance_item["subnetId"] = inst_service.uuid
        instance_item["vpcId"] = self.vpc.uuid
        instance_item["state"] = self.state_mapping(inst_service.status)
        instance_item["ownerId"] = self.account.uuid
        # custom params
        instance_item["nvl-name"] = inst_service.name
        instance_item["nvl-vpcName"] = self.vpc.name
        instance_item["nvl-subnetOwnerAlias"] = self.account.name
        instance_item["nvl-subnetOwnerId"] = self.account.uuid

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        data = self.get_config("subnet")
        dns_searches = self.get_config("dns_search")
        vpc_id = data.get("VpcId")
        zone = data.get("AvailabilityZone")
        cidr = data.get("CidrBlock")
        dns_search = None
        if dns_searches is not None:
            dns_search = dns_searches.get(zone)

        self.set_config("cidr", cidr)
        self.set_config("site", zone)

        # get vpc
        vpc: ApiComputeVPC = self.controller.get_service_type_plugin(vpc_id, plugin_class=ApiComputeVPC)
        tenancy = vpc.get_tenancy()

        if tenancy == "default":
            params["resource_params"] = {}

        elif tenancy == "dedicated":
            params["resource_params"] = {
                "vpc": {"id": vpc.resource_uuid, "tenancy": tenancy},
                "cidr": cidr,
                "dns_search": dns_search,
                "dns_nameservers": ["10.103.48.1", "10.103.48.2"],
                "availability_zone": zone,
                "orchestrator_tag": "default",
            }

        self.logger.debug("Adding link between subnet and vpc")
        # link vpc to instance
        vpc_instance: ApiServiceInstance = self.controller.get_service_instance(vpc_id)
        self.add_link(
            name="link-%s-%s" % (self.instance.oid, vpc_instance.oid),
            type="subnet",
            end_service=vpc_instance.oid,
            attributes={},
        )

        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))
        return params

    def get_cidr(self):
        """Get subnet cidr"""
        cidr = self.get_config("subnet").get("CidrBlock", None)
        return cidr

    #
    # resource client method
    #
    def list_resources(self, zones=[], uuids=[], tags=[], page=0, size=-1):
        """Get resource info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return []

    def create_resource(self, task, *args, **kvargs):
        """Create resource. Do nothing. Use existing resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        vpc = args[0].pop("vpc", {})

        if vpc.get("tenancy", None) == "dedicated":
            data = {"private": [args[0]]}
            try:
                uri = "/v2.0/nrs/provider/vpcs/%s/network" % vpc.get("id")
                res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
                uuid = res.get("uuid", None)
                taskid = res.get("taskid", None)
                self.logger.debug("Create subnet to vpc %s" % uuid)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # set resource uuid
            if uuid is not None and taskid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Update compute subnet resources: %s" % uuid)

    def post_delete(self, *args, **kvargs):
        # delete all subnet links
        links, tot = self.controller.get_links(type="subnet", service=self.instance.oid)
        for link in links:
            self.logger.debug("deleting subnet link %s" % link.uuid)
            link.delete()

        self.update_status(SrvStatusType.DELETED)
        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource. Do nothing.

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.resource_uuid is not None:
            data = self.get_config("subnet")
            vpc_id = data.get("VpcId")
            zone = data.get("AvailabilityZone")
            cidr = data.get("CidrBlock")

            vpc = self.controller.get_service_type_plugin(vpc_id, plugin_class=ApiComputeVPC)

            data = {
                "private": [
                    {
                        "cidr": cidr,
                        "availability_zone": zone,
                        "orchestrator_tag": "default",
                    }
                ]
            }
            try:
                uri = "/v2.0/nrs/provider/vpcs/%s/network" % vpc.resource_uuid
                res = self.controller.api_client.admin_request("resource", uri, "delete", data=data)
                uuid = res.get("uuid", None)
                taskid = res.get("taskid", None)
                self.logger.debug("Remove subnet from vpc %s" % uuid)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # set resource uuid
            if uuid is not None and taskid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Update compute subnet resources: %s" % uuid)


class ApiComputeTag(ApiServiceTypePlugin):
    plugintype = "ComputeTag"

    class state_enum(object):
        """enumerate state name esposed by api"""

        unknown = "unknown"
        creating = "creating"
        available = "available"
        deleting = "deleting"
        deleted = "deleted"
        error = "error"

    @staticmethod
    def customize_list(
        controller: ServiceController, entities: List[ApiComputeTag], *args, **kvargs
    ) -> List[ApiComputeTag]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        tags = []

        for tag in entities:
            item = ApiComputeTag(controller, name=tag.name)
            item.instance_uuid = tag.model.instance_uuid
            item.instance_type = import_class(tag.model.instance_objclass).objname
            tags.append(item)
        return tags

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        tag_item = {}
        tag_item["key"] = self.name
        tag_item["resourceId"] = self.instance_uuid
        tag_item["resourceType"] = self.instance_type
        return tag_item

    @staticmethod
    def resource_type_mapping(type_value):
        mapping = {
            "customer-gateway": None,
            "dhcp-options": None,
            "image": ApiComputeImage.plugintype,
            "instance": ApiComputeInstance.plugintype,
            "internet-gateway": None,
            "network-acl": None,
            "network-interface": None,
            "reserved-instances": None,
            "route-table": None,
            "snapshot": None,
            "spot-instances-request": None,
            "subnet": ApiComputeSubnet.plugintype,
            "security-group": ApiComputeSecurityGroup.plugintype,
            "volume": None,
            "vpc": ApiComputeVPC.plugintype,
            "vpn-connection": None,
            "vpn-gateway": None,
        }
        return mapping.get(type_value, None)


class ApiComputeVolume(AsyncApiServiceTypePlugin):
    plugintype = "ComputeVolume"
    objname = "volume"

    class state_enum(object):
        """enumerate state name esposed by api"""

        unknown = "unknown"
        creating = "creating"
        available = "available"
        deleting = "deleting"
        deleted = "deleted"
        error = "error"

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AsyncApiServiceTypePlugin.info(self)
        info.update({})
        return info

    def state_mapping(self, state, resource=None):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.creating,  # 'creating',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.TERMINATED: self.state_enum.deleting,  # 'deleting',
            SrvStatusType.TERMINATED: self.state_enum.deleted,  # 'deleted',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error'
        }
        res = mapping.get(state, self.state_enum.unknown)
        if resource is not None and state == SrvStatusType.ACTIVE and resource.get("used") is True:
            res = "in-use"
        return res

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List["ApiComputeVolume"],
        *args,
        **kvargs,
    ) -> List["ApiComputeVolume"]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        compute_service_idx = controller.get_service_instance_idx(ApiComputeService.plugintype, index_key="account_id")
        instance_type_idx = controller.get_service_definition_idx(ApiComputeInstance.plugintype)

        # get resources
        zones: list[str] = []
        resources: List[str] = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type_idx = instance_type_idx
            entity.compute_service = compute_service_idx.get(account_id)
            if entity.compute_service.resource_uuid not in zones:
                zones.append(entity.compute_service.resource_uuid)
            if entity.instance.resource_uuid is not None:
                resources.append(entity.instance.resource_uuid)

        if len(resources) > 3:
            resources = []
        else:
            zones = []

        resources_list = ApiComputeVolume(controller).list_resources(zones=zones, uuids=resources)
        resources_idx = {r["uuid"]: r for r in resources_list}

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

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # get params
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        data_instance = self.get_config("volume")
        av_zone = data_instance.get("AvailabilityZone")
        size = data_instance.get("Size")

        # base quotas
        quotas = {"compute.volumes": 1, "compute.blocks": int(size)}

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # get flavor
        flavor_resource_uuid = self.get_config("flavor")

        # get instance type
        type_provider = data_instance.get("Nvl_Hypervisor", None)
        if type_provider is None:
            type_provider = self.get_config("type")
            if type_provider is None:
                type_provider = "openstack"
        self.set_config("type", type_provider)

        # check the TagSpecificationId
        tag_specification_list = data_instance.get("TagSpecification_N", [])
        tags_list = []
        for tag_specification in tag_specification_list:
            tags = tag_specification.get("Tags", [])
            for tag in tags:
                key = tag.get("Key", None)
                # tags_list
                if key is not None:
                    tags_list.append(key)

        name = self.instance.name

        data = {
            "availability_zone": av_zone,
            "compute_zone": compute_zone,
            "multi_avz": True,
            "container": container_id,
            "name": name,
            "desc": name,
            "flavor": flavor_resource_uuid,
            "size": size,
            "type": type_provider,
            "orchestrator_tag": "default",
            "tags": ",".join(tags_list),
            "metadata": {}
            # 'volume': None,
            # 'snapshot': None,
            # 'image': None,
        }

        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    def pre_import(self, **params) -> dict:
        """Check input params before resource import. Use this to format parameters for service creation
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
        account_id = self.instance.get_account().uuid

        # get resource
        resource = self.get_resource(uuid=params.get("resource_id"))
        resource_uuid = dict_get(resource, "uuid")
        compute_zone = dict_get(resource, "parent")
        size = dict_get(resource, "size")
        hypervisor = dict_get(resource, "hypervisor")
        encrypted = dict_get(resource, "attributes.configs.encrypted")
        availability_zone = dict_get(resource, "availability_zone.name")

        params["resource_id"] = resource_uuid

        # base quotas
        quotas = {"compute.volumes": 1, "compute.blocks": int(size)}

        # check quotas
        self.check_quotas(compute_zone, quotas)

        self.instance.set_config("type", hypervisor)
        self.instance.set_config("volume.Nvl_Hypervisor", hypervisor)
        self.instance.set_config("volume.Size", size)
        self.instance.set_config("volume.VolumeType", self.instance.get_config("service_definition_id"))
        self.instance.set_config("volume.AvailabilityZone", availability_zone)
        self.instance.set_config("volume.owner_id", account_id)
        self.instance.set_config("volume.Nvl_Name", self.instance.name)
        self.instance.set_config("volume.Encrypted", encrypted)
        self.instance.set_config("volume.Iops", -1)
        self.instance.set_config("volume.MultiAttachEnabled", False)

        return params

    def pre_delete(self, **params):
        """Pre delete function. Use this function to manipulate and validate delete input params.

        :param params: input params
        :return: kvargs
        :raise ApiManagerError:
        """
        # definer se abilitaremodificare i paramere  se  ha una risoirsa if self.check_resource() is None:
        #     return params

        if self.is_attached() is True:
            raise ApiManagerError("volume %s is in use" % self.instance.uuid)

        return params

    def get_availability_zone(self):
        """Get availability zone where volume is deployed"""
        data_instance = self.get_config("volume")
        if data_instance is not None:
            return data_instance.get("AvailabilityZone", None)
        return None

    def get_volume_type(self):
        flavor_resource_name = dict_get(self.resource, "flavor.name")
        res = self.manager.get_service_definition_by_config("flavor", flavor_resource_name)
        if len(res) > 0:
            res = res[0]
        else:
            res = None
        return res

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        data_instance: dict = self.get_config("volume")
        if data_instance is None:
            data_instance = {}
        # get instance
        compute_instance = None
        attach_time = None
        attach_status = "detached"
        instance_resource = self.resource.get("instance", None)
        if instance_resource is not None:
            instance_resource_uuid = instance_resource.get("uuid", None)
            # self.logger.warning("searching instance by resource_uuid {}".format(instance_resource_uuid))
            compute_instance = self.manager.get_service_instance(resource_uuid=instance_resource_uuid).uuid
            attach_time = self.resource.get("attachment", None)
            attach_status = "attached"

        # get volume type
        volume_type = self.get_volume_type()
        volume_type_name = None
        if volume_type is not None:
            volume_type_name = volume_type.name

        instance_item = {}
        instance_item["volumeId"] = self.instance.uuid
        instance_item["size"] = data_instance.get("Size", "--")
        instance_item["snapshotId"] = None
        instance_item["availabilityZone"] = data_instance.get("AvailabilityZone", "--")
        instance_item["status"] = self.state_mapping(self.instance.status, resource=self.resource)
        instance_item["createTime"] = format_date(self.instance.model.creation_date)
        instance_item["attachmentSet"] = [
            {
                "volumeId": self.instance.uuid,
                "instanceId": compute_instance,
                "device": None,
                "status": attach_status,
                "attachTime": attach_time,
                "deleteOnTermination": True,
            }
        ]
        instance_item["volumeType"] = volume_type_name  # data_instance.get('VolumeType')
        instance_item["encrypted"] = False
        instance_item["multiAttachEnabled"] = False

        # custom params
        instance_item["nvl-hypervisor"] = self.get_config("type")
        instance_item["nvl-name"] = self.instance.name
        instance_item["nvl-volumeOwnerAlias"] = self.account.name
        instance_item["nvl-volumeOwnerId"] = self.account.uuid
        instance_item["nvl-resourceId"] = self.instance.resource_uuid
        return instance_item

    #
    # action
    #
    def is_attached(self):
        """Check if volume il already attached

        :return:
        """
        resource = self.get_resource()
        return resource.get("used")

    def attach(self, instance_id, device):
        """Attach instance to volume

        :param instance_id: instance id
        :param device: instance device
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.is_attached() is True:
            raise ApiManagerError("volume %s is already attached" % self.instance.uuid)

        instance: ApiComputeInstance = self.controller.get_service_type_plugin(
            instance_id, plugin_class=ApiComputeInstance, details=True
        )

        instance.check_status()
        self.check_status()

        if instance.get_hypervisor() != self.get_config("type"):
            raise ApiManagerError(
                "volume %s and instance %s hypervisors mismatch" % (self.instance.uuid, instance.instance.uuid)
            )

        # check volume and instance availability zones are the same
        if self.get_availability_zone() != instance.get_availability_zone():
            raise ApiManagerError(
                "volume %s and instance %s availability zones are different"
                % (self.instance.uuid, instance.instance.uuid)
            )

        params = {
            "resource_params": {
                "instance_id": instance.resource_uuid,
                "action": {
                    "name": "add_volume",
                    "args": {"volume": self.instance.resource_uuid},
                },
            }
        }
        res = self.update(**params)
        self.logger.info("Attach instance %s to volume %s" % (instance_id, self.instance.uuid))
        return None

    def detach(self, instance_id, device):
        """Detach volume from instance

        :param instance_id: instance id
        :param device: instance device
        :return: object instance
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.is_attached() is False:
            raise ApiManagerError("volume %s is not attached" % self.instance.uuid)

        instance = self.controller.get_service_type_plugin(instance_id, plugin_class=ApiComputeInstance, details=False)

        instance.check_status()
        self.check_status()

        params = {
            "resource_params": {
                "instance_id": instance.resource_uuid,
                "action": {
                    "name": "del_volume",
                    "args": {"volume": self.instance.resource_uuid},
                },
            }
        }
        res = self.update(**params)
        self.logger.info("Detach instance %s to volume %s" % (instance_id, self.instance.uuid))
        return None

    #
    # resource client method
    #
    @trace(op="view")
    def get_resource(self, uuid=None):
        """Get resource info

        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if uuid is None:
            uuid = self.instance.resource_uuid
        uri = "/v1.0/nrs/provider/volumes/%s" % uuid
        instances = self.controller.api_client.admin_request("resource", uri, "get", data="").get("volume")
        self.logger.debug("Get compute volume resource: %s" % truncate(instances))
        return instances

    @trace(op="view")
    def list_resources(
        self,
        zones: List[str] = [],
        uuids: List[str] = [],
        tags: List[str] = [],
        page: int = 0,
        size: int = -1,
    ) -> dict:
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)
        self.logger.debug("list_instance_resources %s" % data)

        instances = self.controller.api_client.admin_request(
            "resource", "/v1.0/nrs/provider/volumes", "get", data=urlencode(data)
        ).get("volumes", [])
        self.logger.debug("Get compute volumes resources: %s" % truncate(instances))
        return instances

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"volume": args[0]}
        try:
            uri = "/v1.0/nrs/provider/volumes"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=4, maxtime=7200, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update compute volume resources: %s" % uuid)

        return uuid

    def update_resource(self, task, *args, **kvargs):
        """Update resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            action = kvargs.get("action", None)
            if action is not None:
                data = {"action": {action.get("name"): action.get("args")}}
                if action.get("name") in ["add_volume", "del_volume"]:
                    instance_id = kvargs.get("instance_id", None)
                    uri = "/v1.0/nrs/provider/instances/%s/actions" % instance_id
            else:
                data = {"volume": kvargs}
                uri = "/v1.0/nrs/provider/volumes/%s" % self.instance.resource_uuid
            res = self.controller.api_client.admin_request("resource", uri, "put", data=data)
            taskid = res.get("taskid", None)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.instance.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        if taskid is not None:
            self.wait_for_task(taskid, delta=4, maxtime=600, task=task)
        self.logger.debug("Update compute volume resources: %s" % res)

        return True

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)


class ApiComputeVPC(AsyncApiServiceTypePlugin):
    plugintype = "ComputeVPC"
    objname = "vpc"

    class state_enum(object):
        """enumerate state name esposed by api"""

        unknown = "unknown"
        pending = "pending"
        available = "available"
        deregistered = "deregistered"
        transient = "transient"
        error = "error"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def get_tenancy(self):
        """Get vpc tenancy"""
        tenancy = self.get_config("vpc").get("InstanceTenancy", None)
        if tenancy is None:
            tenancy = "default"
        return tenancy

    def get_cidr(self):
        """Get vpc cidr"""
        cidr = self.get_config("vpc").get("CidrBlock", None)
        return cidr

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.ACTIVE: self.state_enum.available,  # 'available',
            SrvStatusType.DELETED: self.state_enum.deregistered,  # 'deregistered',
            SrvStatusType.DRAFT: self.state_enum.transient,  # 'transient',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error'
        }
        return mapping.get(state, self.state_enum.unknown)

    @staticmethod
    def customize_list(
        controller: ServiceController, entities: List[ApiComputeVPC], *args, **kvargs
    ) -> List[ApiComputeVPC]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()

        # get resources
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)

        return entities

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        self.account = self.controller.get_account(str(self.instance.account_id))

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        # get child subnets
        subnets = self.instance.get_child_instances(plugintype=ApiComputeSubnet.plugintype)

        instance_item = {}
        instance_item["vpcId"] = self.instance.uuid
        instance_item["state"] = self.state_mapping(self.instance.status)
        instance_item["cidrBlock"] = self.get_cidr()

        instance_item["cidrBlockAssociationSet"] = []
        instance_item["ipv6CidrBlockAssociationSet"] = []
        for subnet in subnets:
            cidr_block_association_set = {}
            cidr_block_association_set["associationId"] = subnet.uuid
            cidr_block_association_set["cidrBlock"] = subnet.get_main_config().get_json_property("cidr")
            cidr_block_association_set["cidrBlockState"] = {
                "state": "associated",
                "statusMessage": "",
            }
            instance_item["cidrBlockAssociationSet"].append(cidr_block_association_set)

        instance_item["dhcpOptionsId"] = ""
        instance_item["instanceTenancy"] = self.get_tenancy()
        instance_item["isDefault"] = False
        instance_item["tagSet"] = []

        instance_item["ownerId"] = self.account.uuid
        # custom params
        instance_item["nvl-name"] = self.instance.name
        instance_item["nvl-vpcOwnerAlias"] = self.account.name
        instance_item["nvl-vpcOwnerId"] = self.account.uuid
        instance_item["nvl-resourceId"] = self.instance.resource_uuid

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # base quotas
        quotas = {
            "compute.networks": 1,
        }

        # get container
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        vpc_config = self.get_config("vpc")
        tenancy = vpc_config.get("InstanceTenancy", "default")
        cidr = vpc_config.get("CidrBlock", None)

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # select cidr
        if cidr is None:
            cidr = self.get_config("cidr")

        # select vpc type
        if tenancy == "default":
            vpc_type = "shared"
            networks = self.get_config("networks")
        elif tenancy == "dedicated":
            vpc_type = "private"
            networks = None

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        data = {
            "container": container_id,
            "name": name,
            "desc": self.instance.desc,
            "compute_zone": compute_zone,
            "networks": networks,
            "type": vpc_type,
            "cidr": cidr,
        }

        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))
        return params

    def pre_delete(self, **params):
        res, total = self.get_linked_services(link_type="subnet", filter_expired=False)
        if total > 0:
            raise ApiManagerError("Vpc %s has %s linked Subnet instance." % (self.instance.uuid, total))
        return params

    #
    # resource client method
    #
    @trace(op="view")
    def list_resources(self, zones=[], uuids=[], tags=[], page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if len(zones) > 0:
            data["parent_list"] = ",".join(zones)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)
        self.logger.debug("list_vpc_resources %s" % data)

        instances = self.controller.api_client.admin_request(
            "resource", "/v2.0/nrs/provider/vpcs", "get", data=urlencode(data)
        ).get("instances", [])
        self.logger.debug("Get compute vpc resources: %s" % truncate(instances))
        return instances

    @trace(op="insert")
    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        vpc_type = args[0]["type"]
        networks = args[0].pop("networks", None)

        data = {"vpc": args[0]}
        try:
            uri = "/v2.0/nrs/provider/vpcs"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.message)
            raise ApiManagerError(ex.message)

        # set resource uuid
        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update compute vpc resources: %s" % uuid)

        # add shared network to vpc
        if vpc_type == "shared":
            try:
                data = {"site": [{"network": n} for n in networks]}
                uri = "/v2.0/nrs/provider/vpcs/%s/network" % uuid
                res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
                uuid = res.get("uuid", None)
                taskid = res.get("taskid", None)
                self.logger.debug("Append site networks to vpc %s - start" % uuid)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # set resource uuid
            if uuid is not None and taskid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Append site networks to vpc %s - end" % uuid)

        return uuid

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # get site networks to deassign
        networks = self.get_config("networks")

        # remove shared network from vpc
        if self.get_tenancy() == "default":
            uuid = None
            try:
                if networks is None:
                    self.logger.warning(
                        "No networks - don't remove site networks from vpc %s - start" % self.instance.resource_uuid
                    )
                else:
                    data = {"site": [{"network": n} for n in networks]}
                    uri = "/v2.0/nrs/provider/vpcs/%s/network" % self.instance.resource_uuid
                    res = self.controller.api_client.admin_request("resource", uri, "delete", data=data)
                    uuid = res.get("uuid", None)
                    taskid = res.get("taskid", None)
                    self.logger.debug("Remove site networks from vpc %s - start" % self.instance.resource_uuid)
            except ApiManagerError as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.value)
                raise
            except TypeError:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error="TypeError")
                raise ApiManagerError(ex.message)
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                self.update_status(SrvStatusType.ERROR, error=ex.message)
                raise ApiManagerError(ex.message)

            # set resource uuid
            if uuid is not None and taskid is not None:
                self.set_resource(uuid)
                self.update_status(SrvStatusType.PENDING)
                self.wait_for_task(taskid, delta=2, maxtime=180, task=task)
                self.update_status(SrvStatusType.CREATED)
                self.logger.debug("Remove site networks from vpc %s - end" % self.instance.resource_uuid)

        return ApiServiceTypePlugin.delete_resource(self, *args, **kvargs)


class ApiComputeCustomization(AsyncApiServiceTypePlugin):
    plugintype = "ComputeCustomization"
    objname = "customization"

    class state_enum(object):
        """Enumerate state name exposed by api"""

        unknown = "unknown"
        pending = "pending"
        building = "building"
        active = "active"
        error = "error"
        terminated = "terminated"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypePlugin.__init__(self, *args, **kvargs)

        self.child_classes = []

    def info(self):
        """Get object info
        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ApiServiceTypePlugin.info(self)
        info.update({})
        return info

    @staticmethod
    def customize_list(
        controller: ServiceController,
        entities: List[ApiComputeInstance],
        *args,
        **kvargs,
    ) -> List[ApiComputeInstance]:
        """Post list function. Extend this function to execute some operation after entity was created. Used only for
        synchronous creation.

        :param controller: controller instance
        :param entities: list of entities
        :param args: custom params
        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        account_idx = controller.get_account_idx()
        instance_type_idx = controller.get_service_definition_idx(ApiComputeCustomization.plugintype)
        #
        # # get resources
        for entity in entities:
            instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type_id = instance_type.uuid
            entity.instance_type_name = instance_type.name
        return entities

    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        instance_type = self.controller.get_service_def(str(self.instance.service_definition_id))
        self.account = self.controller.get_account(str(self.instance.account_id))
        self.instance_type_id = instance_type.uuid
        self.instance_type_name = instance_type.name

    def state_mapping(self, state):
        """Get the current state of the instance.

        :param state: customization state
        :return:
        """
        mapping = {
            SrvStatusType.DRAFT: self.state_enum.pending,  # 'pending',
            SrvStatusType.PENDING: self.state_enum.pending,  # 'pending',
            SrvStatusType.BUILDING: self.state_enum.building,  # 'building',
            SrvStatusType.CREATED: self.state_enum.building,  # 'building',
            SrvStatusType.ACTIVE: self.state_enum.active,  # 'active',
            SrvStatusType.ERROR: self.state_enum.error,  # 'error',
            SrvStatusType.ERROR_CREATION: self.state_enum.error,  # 'error',
            SrvStatusType.DELETING: self.state_enum.terminated,  # 'terminated',
            SrvStatusType.TERMINATED: self.state_enum.terminated,  # 'terminated',
            SrvStatusType.UNKNOWN: self.state_enum.error,  # 'error',
            SrvStatusType.UPDATING: self.state_enum.building,  # 'building',
        }
        inst_state = mapping.get(state, self.state_enum.unknown)

        return inst_state

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        instances = []
        args = []

        if self.resource is None:
            self.resource = {}

        if self.get_config("customization") is not None:
            config = self.get_config("customization")
            instances = config.get("Instances")
            args = self.get_config("final_args")

        status = self.instance.status
        if self.resource.get("state", None) == "ERROR":
            status = "ERROR"

        instance_item = {}
        instance_item["customizationId"] = self.instance.uuid
        instance_item["customizationName"] = self.instance.name
        instance_item["customizationType"] = self.instance_type_name
        instance_item["customizationState"] = {"name": self.state_mapping(status)}
        instance_item["reason"] = ""
        if status == "ERROR":
            instance_item["reason"] = self.instance.last_error
        instance_item["launchTime"] = format_date(self.instance.model.creation_date)
        instance_item["ownerAlias"] = self.account.name
        instance_item["ownerId"] = self.account.uuid
        instance_item["resourceId"] = self.instance.resource_uuid
        instance_item["instances"] = instances
        instance_item["args"] = args

        return instance_item

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        account_id = self.instance.account_id
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        customization_resource_id = self.get_config("customization_resource_id")
        data_instance = self.get_config("customization")
        customize_args_schema = self.get_config("args")
        instances = data_instance.get("Instances")
        customize_args = data_instance.get("Args")

        # base quotas
        quotas = {
            "compute.customization": 1,
        }

        # check quotas
        self.check_quotas(compute_zone, quotas)

        # check instances
        instance_resources = []
        for instance in instances:
            serv_inst = self.controller.check_service_instance(instance, ApiComputeInstance, account=account_id)
            instance_resources.append({"id": serv_inst.resource_uuid})

            # link instance to customization
            self.instance.add_link(
                name="link-%s-%s" % (self.instance.oid, serv_inst.oid),
                type="instance",
                end_service=serv_inst.oid,
                attributes={},
            )

        # update Instances attribute with uuid of instance
        self.set_config("customization.Instances", [item["id"] for item in instance_resources])

        # validate extra vars
        customize_args = {c.get("Name"): c.get("Value") for c in customize_args}
        customize_args_schema = {c.get("name"): c for c in customize_args_schema}
        extra_vars = {}
        for name, var in customize_args_schema.items():
            # assign default value from schema
            default_value = var.get("default")
            extra_vars[name] = default_value

        for name in extra_vars.keys():
            # get var schema
            extra_var_schema = customize_args_schema.get(name)
            # check param is required
            arg_required = extra_var_schema.get("required", False)
            if arg_required is True and name not in customize_args:
                raise ApiManagerError("param %s is required" % name)

        # assign user params
        for name, value in customize_args.items():
            # check user param exist
            if name not in customize_args_schema:
                raise ApiManagerError("param %s does not exist" % name)

            # get var schema
            extra_var_schema = customize_args_schema.get(name)

            # check value type
            arg_type = extra_var_schema.get("type")
            if arg_type is not None:
                if arg_type == "int":
                    if not is_int(value):
                        raise Exception(
                            "Type of parameter %s is %s, should be %s" % (name, type(value).__name__, arg_type)
                        )
                elif arg_type == "str":
                    if not is_string(value):
                        raise Exception(
                            "Type of parameter %s is %s, should be %s" % (name, type(value).__name__, arg_type)
                        )
                else:
                    raise Exception("Type %s not supported" % arg_type)

            # check value is allowed
            arg_allowed = extra_var_schema.get("allowed")
            if arg_allowed is not None:
                arg_allowed = arg_allowed.split(",")
                if value not in arg_allowed:
                    raise Exception("Value %s for parameter %s is not allowed" % (value, name))

            # assign user value
            extra_vars[name] = value

        # set action for ansible playbook
        extra_vars["p_operation"] = "install"

        self.set_config("final_args", [{"name": k, "value": v} for k, v in extra_vars.items()])

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        data = {
            "compute_zone": compute_zone,
            "container": container_id,
            "desc": name,
            "customization": customization_resource_id,
            "instances": instance_resources,
            "name": name,
            "extra_vars": extra_vars,
        }

        params["resource_params"] = data
        self.logger.debug("Pre create params: %s" % obscure_data(deepcopy(params)))

        return params

    def pre_update(self, **params):
        """

        :param params:
        :return:
        """
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        customization_resource_id = self.get_config("customization_resource_id")
        instances = self.get_config("customization.Instances")
        final_args = self.get_config("final_args")

        # base quotas
        quotas = {"compute.customization": 1}

        # check quotas
        self.check_quotas(compute_zone, quotas)

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        instance_resources = [{"id": instance} for instance in instances]

        # retrieve verified extra vars from final args
        extra_vars = {item["name"]: item["value"] for item in final_args}

        data = {
            "container": container_id,
            "compute_zone": compute_zone,
            "name": name,
            "desc": name,
            "customization": customization_resource_id,
            "instances": instance_resources,
            "extra_vars": extra_vars,
        }

        params["resource_params"] = data
        self.logger.debug("Pre update params: %s" % params)

        return params

    def pre_delete(self, **params):
        """Check input params before resource deletion. Use this to format parameters for service deletion.
        Extend this function to manipulate and validate deletion input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        container_id = self.get_config("container")
        compute_zone = self.get_config("computeZone")
        customization_resource_id = self.get_config("customization_resource_id")
        instances = self.get_config("customization.Instances")

        # base quotas
        quotas = {"compute.customization": 1}

        # check quotas
        self.check_quotas(compute_zone, quotas)

        name = "%s-%s" % (self.instance.name, id_gen(length=8))

        instance_resources = [{"id": instance} for instance in instances]

        # set action for ansible playbook
        extra_vars = {"p_operation": "uninstall"}

        data = {
            "container": container_id,
            "compute_zone": compute_zone,
            "name": name,
            "desc": name,
            "customization": customization_resource_id,
            "instances": instance_resources,
            "extra_vars": extra_vars,
        }

        params["resource_params"] = data
        self.logger.debug("Pre delete params: %s" % params)

        return params

    #
    # actions
    #

    #
    # resource client method
    #
    def get_runstate(self):
        """Get resource runstate

        :return: resource runstate
        :rtype: str
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        if self.get_status() != "ACTIVE":
            raise ApiManagerError("Customization %s is not in a correct state" % self.instance.uuid)

        resource = self.get_resource()
        runstate = resource.get("runstate")
        self.logger.debug("Get customization %s runstate: %s" % (self.instance.uuid, runstate))
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
            uri = "/v1.0/nrs/provider/applied_customizations/%s" % uuid
            instance = self.controller.api_client.admin_request("resource", uri, "get", data="").get(
                "applied_customization"
            )
        self.logger.debug("Get compute applied customization resource: %s" % truncate(instance))
        return instance

    @trace(op="view")
    def list_resources(self, customization_types=[], uuids=[], tags=[], page=0, size=-1):
        """Get resources info

        :return: Dictionary with resources info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"size": size, "page": page}
        if len(customization_types) > 0:
            data["parent_list"] = ",".join(customization_types)
        if len(uuids) > 0:
            data["uuids"] = ",".join(uuids)
        if len(tags) > 0:
            data["tags"] = ",".join(tags)
        self.logger.debug("list_resources %s" % data)

        uri = "/v1.0/nrs/provider/applied_customizations"
        instances = self.controller.api_client.admin_request("resource", uri, "get", data=urlencode(data)).get(
            "applied_customization", []
        )
        self.logger.debug("Get compute applied customization resources: %s" % truncate(instances))
        return instances

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {"applied_customization": args[0]}
        uuid = self.apply_resource_customization(task, data)
        return uuid

    def update_resource(self, task, *args, **kvargs):
        """Update resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # delete current resource entities
        res = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

        # create resource entities to run install customization playbook
        data = {"applied_customization": args[0]}
        uuid = self.apply_resource_customization(task, data)
        return uuid

    def delete_resource(self, task, *args, **kvargs):
        """Delete resource

        :param task: celery task reference
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # delete current resource entities
        res = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

        # create resource entities to run uninstall customization playbook
        data = {"applied_customization": args[0]}
        uuid = self.apply_resource_customization(task, data)

        # delete previously created resource entities
        res = ApiServiceTypePlugin.delete_resource(self, task, *args, **kvargs)

        return uuid

    def apply_resource_customization(self, task, data):
        """Execute an action by running an applied customization

        :param task: celery task reference
        :param data: applied customization data, i.e. customization, playbook, extra_vars
        :return: resource uuid
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            uri = "/v1.0/nrs/provider/applied_customizations"
            res = self.controller.api_client.admin_request("resource", uri, "post", data=data)
            uuid = res.get("uuid", None)
            taskid = res.get("taskid", None)
            self.logger.debug("Create resource: %s" % uuid)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=ex.value)
            raise
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            self.update_status(SrvStatusType.ERROR, error=getattr(ex, "message", repr(ex)))
            raise ApiManagerError(getattr(ex, "message", repr(ex)))

        if uuid is not None and taskid is not None:
            self.set_resource(uuid)
            self.update_status(SrvStatusType.PENDING)
            self.wait_for_task(taskid, delta=4, maxtime=1200, task=task)
            self.update_status(SrvStatusType.CREATED)
            self.logger.debug("Update compute instance resources: %s" % uuid)

        return uuid


class ApiComputeAddress(AsyncApiServiceTypePlugin):
    plugintype: str = "ComputeAddress"
    objname: str = "address"
