# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from copy import deepcopy
import logging
from time import sleep
from urllib.parse import urlencode

from marshmallow.fields import String
from sqlalchemy.sql.functions import array_agg
from beecell.simple import format_date, obscure_data, dict_get
from beecell.types.type_string import truncate
from beehive_service.controller.api_account import ApiAccount
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.entity.service_type import (
    ApiServiceTypePlugin,
    ApiServiceTypeContainer,
    AsyncApiServiceTypePlugin,
)
from beehive_service.model.account import Account
from beehive_service.model.base import SrvStatusType
from beehive.common.apimanager import ApiClient, ApiManagerWarning, ApiManagerError
from beehive_service.model import Division, Organization
from beehive.common.assert_util import AssertUtil
from beehive_service.plugins.computeservice.controller import (
    ApiComputeInstance,
)
from pprint import pprint
from uuid import uuid4
from beecell.types.type_id import id_gen


class ApiContainerService(ApiServiceTypeContainer):
    objuri = "containerservice"
    objname = "containerservice"
    objdesc = "ContainerService"
    plugintype = "ContainerService"

    def __init__(self, *args, **kvargs):
        """ """
        ApiServiceTypeContainer.__init__(self, *args, **kvargs)
        self.flag_async = True
        self.child_classes = []

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
    def customize_list(controller, entities, *args, **kvargs):
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
        instance_type_idx = controller.get_service_definition_idx(ApiContainerService.plugintype)

        # get resources
        # zones = []
        # resources = []
        for entity in entities:
            account_id = str(entity.instance.account_id)
            entity.account = account_idx.get(account_id)
            entity.instance_type = instance_type_idx.get(str(entity.instance.service_definition_id))
        #     if entity.instance.resource_uuid is not None:
        #         resources.append(entity.instance.resource_uuid)

        # resources_list = ApiContainerService(controller).list_resources(uuids=resources)
        # resources_idx = {r["uuid"]: r for r in resources_list}

        # # assign resources
        # for entity in entities:
        #     entity.resource = resources_idx.get(entity.instance.resource_uuid)

        return entities

    def pre_create(self, **params) -> dict:
        """Check input params before resource creation. Use this to format parameters for service creation
        Extend this function to manipulate and validate create input params.

        :param params: input params
        :return: resource input params
        :raise ApiManagerError:
        """
        # self.logger.debug("pre_create - begin - params: %s" % obscure_data(deepcopy(params)))
        # compute_services, tot = self.controller.get_paginated_service_instances(
        #     plugintype="ComputeService",
        #     account_id=self.instance.account_id,
        #     filter_expired=False,
        # )
        # self.logger.debug("pre_create - tot: %s" % tot)
        # if tot == 0:
        #     raise ApiManagerError("Some service dependency does not exist")

        # compute_service = compute_services[0]
        # if compute_service.is_active() is False:
        #     raise ApiManagerError("Some service dependency are not in the correct status")

        # # set resource uuid
        # self.set_resource(compute_service.resource_uuid)

        params["resource_params"] = {}
        self.logger.debug("pre_create - end - params: %s" % obscure_data(deepcopy(params)))

        return params

    def state_mapping(self, state):
        mapping = {
            SrvStatusType.PENDING: "pending",
            SrvStatusType.ACTIVE: "available",
            SrvStatusType.DELETED: "deregistered",
            SrvStatusType.DRAFT: "trasient",
            SrvStatusType.ERROR: "error",
        }
        return mapping.get(state, "unknown")

    def aws_info(self):
        """Get info as required by aws api

        :return:
        """
        if self.resource is None:
            self.resource = {}

        # instance_type_idx = self.controller.get_service_definition_idx(ApiContainerService.plugintype)

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

        # for quota in self.get_resource_quotas():
        #     name = quota.get("quota")
        #     if name.find("container") == 0:
        #         name = name.replace("container.", "")
        #         attributes_item = {
        #             "attributeName": "%s [%s]" % (name, quota.get("unit")),
        #             "attributeValueSet": [
        #                 {
        #                     "item": {
        #                         "attributeValue": quota.get("value"),
        #                         "nvl-attributeUsed": quota.get("allocated"),
        #                     }
        #                 }
        #             ],
        #         }
        #         attributes.append(attributes_item)

        return attributes

    def set_attributes(self, quotas):
        """Set service quotas

        :param quotas: dict with quotas to set
        :return: Dictionary with quotas.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {}
        # for quota, value in quotas.items():
        #     data["container.%s" % quota] = value

        # res = self.set_resource_quotas(None, data)
        # return res
        return None

    def get_attributes(self, prefix="container"):
        return self.get_container_attributes(prefix=prefix)

    def create_resource(self, task, *args, **kvargs):
        """Create resource

        :param task: the running task which is calling the method
        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("do nothing")
        # self.logger.debug("create_resource begin")
        # self.update_status(SrvStatusType.PENDING)
        # quotas = self.get_config("quota")
        # self.logger.debug("create_resource quotas: {}".format(quotas))
        # self.set_resource_quotas(task, quotas)

        # update service status
        # self.update_status(SrvStatusType.CREATED)
        # self.logger.debug("create_resource - Update instance resources: %s" % self.instance.resource_uuid)

        return self.instance.resource_uuid

    def delete_resource(self, *args, **kvargs):
        """Delete resource do nothing. Compute zone is owned by ComputeService

        :param args: custom positional args
        :param kvargs: custom key=value args
        :return: True
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.logger.debug("do nothing")
        # self.logger.debug("delete_resource begin")
        return True

    def aws_get_availability_zones(self):
        """Get account availability zones

        :return:
        """
        if self.resource is None:
            self.resource = {}

        # def state_mapping(state):
        #     mapping = {"ACTIVE": "available", "ERROR": "unavailable"}
        #     return mapping.get(state, "unavailable")

        res = []
        # for avz in self.get_resource_availability_zones():
        #     reason = avz.get("reason", None)
        #     if avz.get("state") != "ACTIVE" and isinstance(reason, list) and len(reason) > 0:
        #         reason = reason[0]
        #     else:
        #         reason = None
        #     res.append(
        #         {
        #             "zoneName": dict_get(avz, "site.name"),
        #             "zoneState": state_mapping(avz.get("state")),
        #             "regionName": dict_get(avz, "region.name"),
        #             "messageSet": [{"message": reason}],
        #         }
        #     )

        return res
