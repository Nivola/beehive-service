# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import ujson as json
from urllib.parse import urlencode
from typing import List, Union, Tuple, TYPE_CHECKING
from six import text_type, binary_type
from Crypto.Hash import SHA256
from beecell.db.util import TransactionError
from beecell.types.type_string import is_not_blank
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import transaction, trace
from beehive.common.task_v2 import prepare_or_run_task
from beehive_service.controller.api_account_capability import ApiAccountCapability
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.controller.api_service_tag import ApiServiceTag
from beehive_service.entity import ServiceApiObject
from beehive_service.model import ServiceDefinition
from beehive_service.model.account_capability import AccountCapabilityAssoc
from beehive_service.model.base import SrvStatusType
from beehive_service.entity.service_definition import ApiServiceDefinition
from beehive_service.entity.service_instance import ApiServiceInstance, ApiServiceInstanceLink
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from beehive_service.model.account import Account


class ApiAccount(AuthorityApiObject):
    """_summary_

    Args:
        AuthorityApiObject (_type_): _description_

    Raises:
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
        ApiManagerError: _description_
    operator roletemplate
    | path                                                                  | method | stato     |
    |-----------------------------------------------------------------------|--------|-----------|
    | /v1.0/nws/computeservices/instance/rebootinstances                    | PUT    | Deprecato |
    | /v1.0/nws/computeservices/instance/revertinstancesnapshots            | PUT    | Deprecato |
    | /v1.0/nws/computeservices/instance/startinstances                     | PUT    | Deprecato |
    | /v1.0/nws/computeservices/instance/stopinstances                      | PUT    | Deprecato |
    | /v1.0/nws/computeservices/instance/terminateinstances                 | DELETE | Deprecato |
    | /v1.0/nws/computeservices/volume/attachvolume                         | PUT    | Deprecato |
    | /v1.0/nws/computeservices/volume/deletevolume                         | DELETE | Deprecato |
    | /v1.0/nws/computeservices/volume/describevolumes                      | GET    | Deprecato |
    | /v1.0/nws/computeservices/volume/describevolumetypes                  | GET    | Deprecato |
    | /v1.0/nws/computeservices/volume/detachvolume                         | PUT    | Deprecato |
    | /v1.0/nws/databaseservices/instance/describedbinstances               | GET    | Deprecato |
    | /v1.0/nws/databaseservices/instance/describedbinstancetypes           | GET    | Deprecato |
    | /v1.0/nws/databaseservices/instance/enginetypes                       | GET    | Deprecato |

    | path                                                                  | method | stato     |
    |-----------------------------------------------------------------------|--------|-----------|
    | /v2.0/nws/databaseservices/instance/describedbinstances               | GET    | ok        |
    | /v2.0/nws/databaseservices/instance/deletedbinstanceuser              | DELETE | ok        |
    | /v2.0/nws/databaseservices/instance/createdbinstanceuser              | POST   | ok        |
    | /v2.0/nws/computeservices/volume/detachvolume                         | PUT    | ok        |
    | /v2.0/nws/computeservices/volume/describevolumes                      | GET    | ok        |
    | /v2.0/nws/computeservices/volume/attachvolume                         | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/terminateinstances                 | DELETE | ok        |
    | /v2.0/nws/computeservices/instance/stopinstances                      | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/startinstances                     | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/revertinstancesnapshots            | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/rebootinstances                    | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/modifyinstanceattribute            | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/modifyinstanceattribute            | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/getconsole                         | GET    | ok        |
    | /v2.0/nws/computeservices/instance/describeinstancesnapshots          | GET    | ok        |
    | /v2.0/nws/computeservices/instance/describeinstances                  | GET    | ok        |
    | /v2.0/nws/computeservices/instance/deleteinstancesnapshots            | PUT    | ok        |
    | /v2.0/nws/computeservices/instance/createinstancesnapshots            | PUT    | ok        |
    | /v1.0/nws/storageservices/efs/mount-targets/<oid>/grants              | DELETE | ok        |
    | /v1.0/nws/storageservices/efs/mount-targets/<oid>/grants              | POST   | ok        |
    | /v1.0/nws/storageservices/efs/mount-targets                           | GET    | ok        |
    | /v1.0/nws/storageservices/efs/file-systems                            | GET    | ok        |
    | /v1.0/nws/networkservices/vpc/revokesecuritygroupingress              | DELETE | ok        |
    | /v1.0/nws/networkservices/vpc/revokesecuritygroupegress               | DELETE | ok        |
    | /v1.0/nws/networkservices/vpc/patchsecuritygroup                      | PATCH  | ok        |
    | /v1.0/nws/networkservices/vpc/describevpcs                            | GET    | ok        |
    | /v1.0/nws/networkservices/vpc/describesubnets                         | GET    | ok        |
    | /v1.0/nws/networkservices/vpc/describesecuritygroups                  | GET    | ok        |
    | /v1.0/nws/networkservices/vpc/deletesecuritygroup                     | DELETE | ok        |
    | /v1.0/nws/networkservices/vpc/createvpc                               | POST   | ok        |
    | /v1.0/nws/networkservices/vpc/createsubnet                            | POST   | ok        |
    | /v1.0/nws/networkservices/vpc/createsecuritygroup                     | POST   | ok        |
    | /v1.0/nws/networkservices/vpc/authorizesecuritygroupingress           | POST   | ok        |
    | /v1.0/nws/networkservices/vpc/authorizesecuritygroupegress            | POST   | ok        |
    | /v1.0/nws/networkservices/ssh_gateway/configuration/list              | GET    | ok        |
    | /v1.0/nws/networkservices/ssh_gateway/configuration/activate          | PUT    | ok        |
    | /v1.0/nws/loggingservices                                             | POST   | ok        |
    | /v1.0/nws/computeservices/vpc/describevpcs                            | GET    | ok        |
    | /v1.0/nws/computeservices/vpc/createvpc                               | POST   | ok        |
    | /v1.0/nws/computeservices/securitygroup/revokesecuritygroupingress    | DELETE | ok        |
    | /v1.0/nws/computeservices/securitygroup/revokesecuritygroupegress     | DELETE | ok        |
    | /v1.0/nws/computeservices/securitygroup/patchsecuritygroup            | PATCH  | ok        |
    | /v1.0/nws/computeservices/securitygroup/describesecuritygroups        | GET    | ok        |
    | /v1.0/nws/computeservices/securitygroup/deletesecuritygroup           | DELETE | ok        |
    | /v1.0/nws/computeservices/securitygroup/createsecuritygroup           | POST   | ok        |
    | /v1.0/nws/computeservices/securitygroup/authorizesecuritygroupingress | POST   | ok        |
    | /v1.0/nws/computeservices/securitygroup/authorizesecuritygroupegress  | POST   | ok        |
    | /v1.0/nws/computeservices/keypair/importkeypair                       | POST   | ok        |
    | /v1.0/nws/computeservices/keypair/describekeypairs                    | GET    | ok        |
    | /v1.0/nws/computeservices/keypair/deletekeypair                       | DELETE | ok        |
    | /v1.0/nws/computeservices/keypair/createkeypair                       | POST   | ok        |
    | /v1.0/nws/capabilities/<oid>                                          | GET    | ok        |
    | /v1.0/nws/capabilities                                                | GET    | ok        |
    | /v1.0/nws/accounts/<oid>/users                                        | GET    | ok        |



    Returns:
        _type_: _description_
    """

    objdef = "Organization.Division.Account"
    objuri = "account"
    objname = "account"
    objdesc = "Account"

    STATUS_ACTIVE = 1
    STATUS_DELETED = 6
    STATUS_CLOSED = 22

    EXPIRE_DAYS = 180

    default_service_types = {
        "ComputeService": None,
        "DatabaseService": None,
        "StorageService": None,
        "AppEngineService": None,
        "ComputeImage": None,
        "ComputeVPC": None,
        "ComputeSecurityGroup": None,
        "ComputeSubnet": None,
    }

    role_templates = {
        "master": {
            "desc": "Account administrator. Can manage everything in the account",
            "desc_sp": "Master di Account",
            "name": "AccountAdminRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": "*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account",
                    "objid": "<objid>",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceLinkInst",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceInstanceConfig",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "*//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "*//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.CATEGORY.AccountServiceDefinition",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
            ],
        },
        "viewer": {
            "desc": "Account viewer. Can view everything in the account",
            "desc_sp": "Visualizzatore di Account",
            "name": "AccountViewerRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": "*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account",
                    "objid": "<objid>",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance",
                    "objid": "<objid>" + "//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceLinkInst",
                    "objid": "<objid>" + "//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceInstanceConfig",
                    "objid": "<objid>" + "//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "<objid>" + "//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "<objid>" + "//*",
                    "action": "view",
                },
            ],
        },
        "operator": {
            "desc": "Account operator. Can manage services in the account",
            "desc_sp": "Operatore di Account",
            "name": "AccountOperatorRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/databaseservices/instance/describedbinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/databaseservices/instance/deletedbinstanceuser", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/databaseservices/instance/createdbinstanceuser", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/volume/detachvolume", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/volume/describevolumes", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/volume/attachvolume", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/terminateinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/stopinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/startinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/revertinstancesnapshots", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/rebootinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/modifyinstanceattribute", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/modifyinstanceattribute", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/getconsole", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/describeinstancesnapshots", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/describeinstances", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/deleteinstancesnapshots", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v2.0/nws/computeservices/instance/createinstancesnapshots", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/storageservices/efs/mount-targets/<oid>/grants", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/storageservices/efs/mount-targets/<oid>/grants", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/storageservices/efs/mount-targets", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/storageservices/efs/file-systems", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/revokesecuritygroupingress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/revokesecuritygroupegress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/patchsecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PATCH",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/describevpcs", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/describesubnets", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/describesecuritygroups", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/deletesecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/networkservices/vpc/createvpc", encoding="utf-8")).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/createsubnet", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/createsecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/authorizesecuritygroupingress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/vpc/authorizesecuritygroupegress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/ssh_gateway/configuration/list", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/networkservices/ssh_gateway/configuration/activate", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PUT",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/loggingservices", encoding="utf-8")).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/vpc/describevpcs", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/computeservices/vpc/createvpc", encoding="utf-8")).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/revokesecuritygroupingress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/revokesecuritygroupegress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/patchsecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "PATCH",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/describesecuritygroups", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/deletesecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/createsecuritygroup", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/authorizesecuritygroupingress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/securitygroup/authorizesecuritygroupegress", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/keypair/importkeypair", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/keypair/describekeypairs", encoding="utf-8")
                    ).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/keypair/deletekeypair", encoding="utf-8")
                    ).hexdigest(),
                    "action": "DELETE",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(
                        bytes("/v1.0/nws/computeservices/keypair/createkeypair", encoding="utf-8")
                    ).hexdigest(),
                    "action": "POST",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/capabilities/<oid>", encoding="utf-8")).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/capabilities", encoding="utf-8")).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "ApiMethod",
                    "objid": SHA256.new(bytes("/v1.0/nws/accounts/<oid>/users", encoding="utf-8")).hexdigest(),
                    "action": "GET",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account",
                    "objid": "<objid>",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceLinkInst",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceInstanceConfig",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "*//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "*//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.CATEGORY.AccountServiceDefinition",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
            ],
        },
    }
    add_capability_task = "beehive_service.task_v2.account_capability.add_account_capability"
    update_capability_task = "beehive_service.task_v2.account_capability.update_account_capability"
    delete_task = "beehive_service.task_v2.servicetypeplugin.account_delete_task"

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        self.model: Account
        self.division_id: str = None
        self.service_status_id = 1
        self.contact: str = None
        self.note: str = None
        self.email: str = None
        self.email_support: str = None
        self.email_support_link: str = None
        self.services = {}

        self.managed: bool = False
        self.account_type: str = None
        self.management_model: str = None
        self.pods: str = None
        self.params = {}

        if self.model is not None:
            self.division_id = self.model.division.uuid
            self.contact = self.model.contact
            self.note = self.model.note
            self.email = self.model.email
            self.email_support = self.model.email_support
            self.email_support_link = self.model.email_support_link
            self.service_status_id = self.model.service_status_id
            self.status = self.model.status.name
            # if isinstance(self.model.params, str) or isinstance(self.model.params, unicode):
            if isinstance(self.model.params, (text_type, binary_type)):
                self.params = json.loads(self.model.params)
            elif isinstance(self.model.params, dict):
                self.params = self.model.params

            self.managed = self.params.get("managed", False)
            self.account_type = self.params.get("account_type", "")
            self.management_model = self.params.get("management_model", "")
            self.pods = self.params.get("pods", "")

        # child classes
        self.child_classes = [
            ApiServiceInstance,
            ApiServiceInstanceLink,
            ApiServiceTag,
        ]

        self.update_object = self.manager.update_account
        self.delete_object = self.manager.delete

    def __repr__(self):
        return "<%s id=%s objid=%s name=%s>" % (
            "ApiAccount",
            self.oid,
            self.objid,
            self.name,
        )

    def register_object(self, objids, desc=""):
        """Register object types, objects and permissions related to module.

        :param objids: objid split by //
        :param desc: object description
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        super().register_object(objids, desc=desc)

        from beehive_service.entity.account_service_definition import (
            ApiAccountServiceDefinition,
        )

        # add object and permissions
        desc = "ApiAccountServiceDefinition"
        objids.extend(["*", "*"])
        self.api_client.add_object(self.objtype, ApiAccountServiceDefinition.objdef, "//".join(objids), desc)

    def deregister_object(self, objids):
        super().deregister_object(objids)

        from beehive_service.entity.account_service_definition import (
            ApiAccountServiceDefinition,
        )

        # delete object and permissions
        objids.extend(["*", "*"])
        self.api_client.remove_object(self.objtype, ApiAccountServiceDefinition.objdef, "//".join(objids))

    def info(self, version=None):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "division_id": self.division_id,
                "status": self.status,
                "contact": self.contact,
                "note": self.note,
                "email": self.email,
                "email_support": self.email_support,
                "email_support_link": self.email_support_link,
                "managed": self.managed,
                "services": self.services,
                "acronym": self.model.acronym,
                "account_type": self.account_type,
                "management_model": self.management_model,
                "pods": self.pods,
            }
        )

        return info

    def detail(self, version=None):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info(version)
        return info

    def get_triplet_name(self):
        """Get triplet full name representation of account.

        :return: String account name with format organization.division.account.
        """
        account_name = self.name
        division_id = self.division_id
        controller = self.controller
        division = controller.get_division(division_id)
        division_name = division.name
        organization_id = division.organization_id
        organization = controller.get_organization(organization_id)
        organization_name = organization.name
        full_account_name = ".".join((organization_name, division_name, account_name))
        return full_account_name

    def get_username_roles(self, *args, **kvargs):
        def __purge_fields(self, field):
            i = 1
            fields = ["__meta__", "date"]
            for f in fields:
                try:
                    del field[f]
                except KeyError:
                    self.logger.error("field %d not found" % i)
                except Exception:
                    self.logger.error("field %s is not correct" % field)
            return field

        result = {}
        for role_template in self.role_templates.values():
            role_name = role_template.get("name") % self.oid
            # users = []
            roles = self.api_client.admin_request(
                "auth", "/v1.0/nas/roles", "GET", data=urlencode({"names": role_name})
            ).get("roles")
            for role in roles:
                role = __purge_fields(self, role)
                role_id = role["id"]
                data = {"role": role_id}
                users = self.api_client.admin_request("auth", "/v1.0/nas/users", "get", data=urlencode(data))
                users = users.get("users")
                for user in users:
                    user = __purge_fields(self, user)
                    user.update(
                        {
                            "account_name": self.name,
                            "email": self.email,
                            "account_status": self.status,
                            "contact": self.contact,
                        }
                    )
                    if result.get(user.get("id")) is None:
                        user.update({"roles": []})
                        user.get("roles").append(role)
                        result.update({user.get("id"): user})
                    else:
                        result.get(user.get("id")).get("roles").append(role)
        json_resp = {"usernames": list(result.values())}
        # self.logger.debug(json_resp)
        return json_resp

    @trace(op="update")
    def update(self, *args, **kvargs):
        # account_type
        self.logger.debug("+++++ update: kvargs %s" % kvargs)
        account_type = kvargs.pop("account_type", None)
        management_model = kvargs.pop("management_model", None)
        pods = kvargs.pop("pods", None)

        if account_type is not None:
            if is_not_blank(self.account_type) and account_type != self.account_type:
                raise ApiManagerError("account_type already set: %s" % self.account_type)
            else:
                self.params.update({"account_type": account_type})

        if management_model is not None:
            self.params.update({"management_model": management_model})

        if pods is not None:
            if is_not_blank(self.pods) and pods != self.pods:
                raise ApiManagerError("pods already set: %s" % self.pods)
            else:
                self.params.update({"pods": pods})
        self.logger.debug("+++++ update: params %s" % self.params)

        return super().update(params=self.params, *args, **kvargs)

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.

        :param args: custom params
        :param kvargs: custom params
        :param kvargs.delete_services: if True delete all child services before remove the account [optional]
        :param kvargs.delete_tags: if True delete all child tags before remove the account [optional]
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    @trace(op="delete")
    def delete(self, soft=False, **kvargs):
        """Delete account

        :param kvargs: custom params
        :param soft: if True make a soft delete
        :return: None
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        if self.delete_object is None:
            raise ApiManagerError("Delete is not supported for %s:%s" % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions("delete")

        # custom action
        if self.pre_delete is not None:
            kvargs = self.pre_delete(**kvargs)

        close_account = kvargs.get("close_account", False)
        if close_account and not self.is_active():
            raise ApiManagerError("Account %s is not active" % (self.uuid))

        # check service exists in order
        service_types_order_delete = [
            "ComputeInstance",
            "DatabaseInstance",
            "StorageEFS",
            "ComputeKeyPairs",
            "ComputeSecurityGroup",
            "ComputeSubnet",
            "ComputeVPC",
            "NetworkGateway",
            "NetworkLoadBalancer",
            "NetworkSshGateway",
        ]
        for service_type in service_types_order_delete:
            if self.has_service(service_type) is True:
                raise ApiManagerError(
                    "account %s has an active %s. Remove it before delete account" % (self.uuid, service_type)
                )

        # set asynch
        asynch = False
        params = {"alias": "Account.delete", "account": self.oid, "steps": []}
        params["close_account"] = close_account

        # services
        if kvargs.get("delete_services", False) is True:
            asynch = True
            params["steps"].append("beehive_service.task_v2.servicetypeplugin.AccountDeleteTask.delete_services_step")
        elif self.services.get("base", 0) > 0 or self.services.get("core", 0) > 0:
            msg = "Account %s has child services. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerError(msg)

        # tags
        tags, tot_tags = self.controller.get_tags_occurrences(objid=self.objid + "%", size=0)
        if kvargs.get("delete_tags", False) is True:
            asynch = True
            params["steps"].append("beehive_service.task_v2.servicetypeplugin.AccountDeleteTask.delete_tags_step")
        elif tot_tags > 0:
            msg = "Account %s has child tags. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerError(msg)

        # set status
        # self.update_status(5)  # DELETING

        if asynch is True:
            params["steps"].append("beehive_service.task_v2.servicetypeplugin.AccountDeleteTask.delete_account_step")
            params.update(self.get_user())
            task, status = prepare_or_run_task(self, self.delete_task, params, sync=False)
            self.logger.info("task created %s", task)
            resp = {"taskid": task["taskid"]}, status
        else:
            try:
                self.delete_object(self.model)

                if close_account:
                    if self.update_object is not None:
                        status = ApiAccount.STATUS_CLOSED
                        expiry_date = datetime.today() + timedelta(days=ApiAccount.EXPIRE_DAYS)
                        self.update_object(oid=self.oid, service_status_id=status, expiry_date=expiry_date)

                    for k, v in self.role_templates.items():
                        role_name = v.get("name") % self.oid
                        self.logger.debug("+++++ delete account - role_name %s - %s" % (k, role_name))

                        res_role_expire = self.controller.api_client.admin_request(
                            "auth", "/v1.0/nas/roles/%s/expire/%s" % (role_name, ApiAccount.EXPIRE_DAYS), "delete"
                        )
                        self.logger.debug("+++++ delete account - res_role_expire %s" % (res_role_expire))

                else:
                    self.model.disable()
                    self.update(self.model)
                    self.update_status(ApiAccount.STATUS_DELETED)

                    self.logger.debug("Soft delete %s: %s" % (self.objdef, self.oid))
                resp = None, 204
            except TransactionError as ex:
                self.logger.error(ex, exc_info=True)
                raise ApiManagerError(ex, code=400) from ex

        return resp

    #
    # customization
    #
    def customize(self, op_params, *args, **kvargs):
        """Customization function.

        :param op_params: operation params
        :param args: custom params
        :param kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        self.logger.info("Customize account %s - START" % self.oid)

        try:
            self.update_status(14)  # UPDATING
            self.add_roles()
            self.update_status(1)  # ACTIVE
            self.logger.info("Customize account %s - STOP" % self.oid)
            return True
        except Exception:
            self.logger.error("", exc_info=True)
            self.logger.error("Customize account %s - ERROR", self.oid)

        return False

    #
    # services
    #
    def get_services(self):
        """get services has a list ods service type plugins in the account

        Returns:
            _type_: a list ods service type plugins
        """
        services, tot = self.controller.get_service_type_plugins(account_id=self.oid, size=-1, with_perm_tag=False)
        return services

    def has_service(self, plugintype):
        """true if account has at least on service of type plugintype

        Args:
            plugintype (_type_): _description_

        Returns:
            _type_: _description_
        """
        services, tot = self.controller.get_service_type_plugins(
            account_id=self.oid, plugintype=plugintype, with_perm_tag=False
        )
        if tot > 0:
            return True
        return False

    def get_service_index(self):
        service_insts, tot = self.controller.get_paginated_service_instances(
            account_id=self.oid, size=-1, with_perm_tag=False, filter_expired=False
        )

        services = self.get_services()
        service_idx = {}
        for s in service_insts:
            plugin = s.get_service_type_plugin()
            try:
                service_idx[s.uuid]["plugin"] = plugin
            except Exception:
                service_idx[s.uuid] = {"plugin": plugin, "childs": [], "core": False}

            # get parent service
            parent = s.get_parent()

            # simple service
            if parent is not None:
                try:
                    service_idx[parent.uuid]["childs"].append(s.uuid)
                except Exception:
                    service_idx[parent.uuid] = {
                        "plugin": None,
                        "core": False,
                        "childs": [s.uuid],
                    }

            # core service
            else:
                service_idx[s.uuid]["core"] = True

        return service_idx

    #
    # Definitions
    #
    def can_instantiate(
        self,
        definition: ApiServiceDefinition = None,
        definition_id: Union[int, str] = None,
    ) -> Tuple[bool, str]:
        """Verify that a service of type definition is instantiable in the account

        :return: bool and a string in qhiche
        """
        # self.logger.debug(f'can_instantiate: account.id={self.model.id}, defobj={definition} definition.id= {definition_id}:{type(definition_id)}')
        if not self.is_active():
            return False, "Account not in ACTIVE state"
        if definition is None and definition_id is None:
            return False, "Definition not searchable"
        if definition is None:
            definition = self.controller.get_service_def(definition_id)
        if definition is not None:
            if not definition.is_active():
                return False, "Definition not in ACTIVE state"
            accsdlist, tot = self.controller.get_account_service_defintions(
                account_id=self.model.id,
                service_definition_id=definition.model.id,
                actice=1,
            )
            if tot == 0:
                # self.logger.debug(f'Account service definition missing found:{tot}')
                return False, "Account service definition missing"
            else:
                # self.logger.debug(f'Account service definition missing found:{tot}')
                return True, "Found Account Service Definition"
        return False, "Definition Not Found"

    def get_definitions(
        self,
        plugintype: str = None,
        only_container: bool = False,
        category: str = None,
        active: bool = True,
        service_definition_id: Union[str, int, None] = None,
        name: str = None,
        page: int = 0,
        size: int = 50,
        order: str = "DESC",
        field: int = "id",
        **kwargs,
    ) -> Tuple[List[ApiServiceDefinition], int]:
        """Get service definitions available for the account

        :param str plugintype: plugin type,
        :param bool only_container: only container definitions,
        :param str category: only category definitions,
        :param str service_definition_id: serivce definition id
        :param str name: name like [optional]
        :param int page: users list page to show [default=0]
        :param int size: number of users to show in list per page [default=0]
        :param int order: sort order [default=DESC]
        :param int field: sort field [default=id]
        :returns: List[ApiServiceDefinition]: [description]
        """
        # verify permissions
        self.verify_permisssions("view")

        if service_definition_id is not None:  # and not isinstance(service_definition_id, int ):
            service_definition_id = self.manager.get_definition_id(service_definition_id)

        accsdlist, tot = self.controller.get_account_service_defintions(
            account_id=self.model.id,
            plugintype=plugintype,
            only_container=only_container,
            category=category,
            active=active,
            service_definition_id=service_definition_id,
            name=name,
            page=page,
            size=size,
            order=order,
            field=field,
            **kwargs,
        )

        return [x.service_definition for x in accsdlist], tot

    #
    # Capabilities
    #
    def has_capability(self, capability_id):
        """Check if the account has capability

        :return: association
        """
        capabilities = []
        found = False
        association = None
        if self.model:
            capabilities = self.model.capabilities
        for association in capabilities:
            if association.capability.uuid == capability_id:
                found = True
                break
            if association.capability.name == capability_id:
                found = True
                break
            if isinstance(capability_id, int) and association.capability.id == int(capability_id):
                found = True
                break
        if not found:
            association = None
        return found, association

    @transaction
    def set_capability_building_only_if_none_building(self, capability_oid):
        """Try to set the capability status ord sel account as Building only if there is no
        others capability which are Building.
        begin a transaction
        lock the account-capabilities association table  in order to prevent a race condition
        if there is no building capabilities set the capability status
        commit transaction and release the table lock

        :param capability_oid:
        :return: True only if there is no building capability and new status for capability has been set False otherwise
        """

        building_capability = self.controller.manager.get_bulding_capability_for_account(self.model.id)
        if building_capability is None:
            self.set_capability_status(capability_oid, SrvStatusType.BUILDING)
            return True
        return False

    def has_building_capability(self):
        """Check if the account has a capability in BUILDING status

        :return: True or False
        """
        capabilities = []
        if self.model:
            capabilities = self.model.capabilities
        for association in capabilities:
            if association.status == SrvStatusType.BUILDING:
                self.logger.debug("Found capability %s still Building" % association.capability.name)
                return True
        return False

    @transaction
    def set_capability_status(self, capabilityoid, status):
        """set the capability status for the account if the return capability

        :param capabilityoid: cpability oid
        :param status: Unicode status
        """
        # check if self has capability
        # capabilities  = []

        has, assoc = self.has_capability(capabilityoid)
        if has:
            #
            assoc.status = status
            self.controller.manager.update(assoc)
        else:
            capability = self.controller.get_capability(capabilityoid)
            self.model.capabilities.append(AccountCapabilityAssoc(self.model.id, capability.model.id, status))

    def add_capability(self, capability: str = None):
        """Add capability to account
        Collect the capability definitions (list of services) and merge them within the actual service definitions
        then launch a task for the hierarchical service activation and verification

        :param capability: capability id or name
        :return: {'taskid':string}, http status
        """
        if not self.is_active():
            raise ApiManagerError(f"Account {self.oid} is not active")

        if self.has_building_capability():
            raise ApiManagerError("account %s has a BUILDING capability. Wait until it has finished" % self.uuid)

        found, _ = self.has_capability(capability)
        if found:
            raise ApiManagerError(
                f"capability {capability} already assigned to account {self.oid}, "
                f"cannot add. Use 'update' command to update the capability"
            )

        self.check_valid_capability(capability)

        params = {
            "alias": "AccountCapabilities.add",
            "objid": self.objid,
            "account": self.uuid,
            "steps": [],
        }
        step = {
            "step": "beehive_service.task_v2.account_capability.AddAccountCapabilityTask.step_add_capability",
            "args": [capability],
        }
        params["steps"].append(step)

        params.update(self.get_user())
        task, status = prepare_or_run_task(self, self.add_capability_task, params, sync=False)
        self.logger.info("task created: %s" % task)

        return {"taskid": task["taskid"]}, status

    def update_capability(self, capability: str = None):
        """Update account capability
        Collect the capability definitions (list of services) and merge them within the actual service definitions
        then launch a task for the hierarchical service activation and verification

        :param capability: capability id or name
        :return: {'taskid':string}, http status
        """
        if not self.is_active():
            raise ApiManagerError(f"Account {self.oid} is not active")

        if self.has_building_capability():
            raise ApiManagerError("account %s has a BUILDING capability. Wait until it has finished" % self.uuid)

        found, _ = self.has_capability(capability)
        if not found:
            raise ApiManagerError(
                f"capability {capability} not applied to account {self.oid}, "
                f"cannot update. Use 'add' command to assign capability to account"
            )

        params = {
            "alias": "AccountCapabilities.update",
            "objid": self.objid,
            "account": self.uuid,
            "steps": [],
        }

        step = {
            "step": "beehive_service.task_v2.account_capability.UpdateAccountCapabilityTask.step_update_capability",
            "args": [capability],
        }
        params["steps"].append(step)

        params.update(self.get_user())
        task, status = prepare_or_run_task(self, self.update_capability_task, params, sync=False)
        self.logger.info("task created: %s" % task)

        return {"taskid": task["taskid"]}, status

    def get_default_services_description(self):
        """gets le services described by all capabilities"""
        self.logger.info("get_default_services_description")

        services_list = []

        def notin(slist, srv):
            if srv is None:
                return False
            srv_ty = srv.get("type", "--")
            srv_nm = srv.get("name", "--")
            for item in slist:
                item_ty = item.get("type", "--")
                item_nm = item.get("name", "--")
                if item_ty == srv_ty and item_nm == srv_nm:
                    return False
            return True

        if self.model:
            for capability in self.model.capabilities:
                services = getattr(capability, "params", {}).get("services", [])
                for service in services:
                    if notin(services_list, service):
                        services_list.append(service)
        return services_list

    def get_capability(self, name):
        """get the capabilities associated with this account

        :param name: capability name
        :return: Capability object
        """
        if self.model:
            for c in self.model.capabilities:
                if c.get("name") == name:
                    return c
        raise ApiManagerError("no capability %s found" % name)

    def get_capabilities(self):
        """get the capabilities associated with this account

        :return: a list of Capability objects
        """
        if self.model:
            return self.model.capabilities
        else:
            return []

    def get_capabilities_list(self):
        """Get a list of capabilities associated with this account an the plugin_name which is the type of service
        enabled and the status of the association

        :return: a list of dict with shape{"name", "plugin_name", "status"}
        """
        res = []
        if self.model:
            capabilities = self.model.capabilities_list()
            account_services = self.get_services()
            account_definitions, tot = self.get_definitions(size=-1)
            account_service_idx = {a.instance.name: a for a in account_services}
            for c in capabilities:
                # check services
                capability_services = c.get("params", {}).get("services", [])
                service_required = len(capability_services)
                service_created = 0
                service_error = 0
                for capability_service in capability_services:
                    s = account_service_idx.get(capability_service.get("name"), None)
                    capability_service["status"] = SrvStatusType.UNKNOWN
                    if s is not None:
                        status = s.get_status()
                        capability_service["status"] = status
                        if status == SrvStatusType.ACTIVE:
                            service_created += 1
                        elif status == SrvStatusType.ERROR:
                            service_error += 1

                # check definitions
                capability_definitions = c.get("params", {}).get("definitions", [])
                definitions_required = len(capability_definitions)
                definitions_created = len(account_definitions)
                definitions_missed = []

                status = c.get("status")
                if service_created != service_required and status in [
                    SrvStatusType.ACTIVE,
                    SrvStatusType.ERROR,
                ]:
                    status = SrvStatusType.ERROR
                # if definitions_required > 0 and definitions_created != definitions_required:
                #     status = SrvStatusType.ERROR
                #     definitions_missed = list(set(capability_definitions).
                #                               difference(set([d.name for d in account_definitions])))
                #     self.logger.warn(definitions_missed)
                # else:
                #     definitions_created = 0
                #     definitions_missed = []

                item = {
                    "name": c.get("name"),
                    "status": status,
                    "services": capability_services,
                    "definitions": [d.small_info() for d in account_definitions],
                    "report": {
                        "services": {
                            "required": service_required,
                            "created": service_created,
                            "error": service_error,
                        },
                        "definitions": {
                            "required": definitions_required,
                            "created": definitions_required,
                            "missed": definitions_missed,
                        },
                    },
                }
                res.append(item)

        return res

    def get_capability_status(self, capability_id):
        """get capability status based on required and created services

        :return: a list of dict with shape{"name", "plugin_name", "status"}
        """
        res = False
        required = None
        created = None
        if self.model:
            capabilities = self.model.capabilities_list()
            account_services = self.get_services()
            account_service_idx = {a.instance.name: a for a in account_services}
            for c in capabilities:
                if c.get("id") != capability_id:
                    continue
                capability_services = c.get("params", {}).get("services", [])
                required = len(capability_services)
                created = 0
                error = 0
                for capability_service in capability_services:
                    s = account_service_idx.get(capability_service.get("name"), None)
                    capability_service["status"] = SrvStatusType.UNKNOWN
                    if s is not None:
                        status = s.get_status()
                        capability_service["status"] = status
                        if status == SrvStatusType.ACTIVE:
                            created += 1
                        elif status == SrvStatusType.ERROR:
                            error += 1
        if required == created:
            res = True
        return res

    def get_report_costconsume(self, year_month, start_date, end_date, report_mode, *args, **kvargs):
        """Get report costconsume

        :param year_month:
        :param start_date:
        :param end_date:
        :param report_mode:
        :param args:
        :param kvargs:
        :return:
        """
        res_report = self.controller._format_report_costcomsume(
            [self.oid], year_month, start_date, end_date, report_mode, *args, **kvargs
        )

        res_credit = self.controller._format_report_credit_summary([self.oid], None, year_month, start_date, end_date)

        postal_address = "" if self.model.division.postaladdress is None else self.model.division.postaladdress
        referent = (
            "" if self.model.division.organization.referent is None else self.model.division.organization.referent
        )
        email = "" if self.email is None else self.email

        res = {
            "organization": self.model.division.organization.name,
            "organization_id": self.model.division.organization.uuid,
            "division": self.model.division.name,
            "division_id": self.model.division.uuid,
            "account": self.name,
            "account_id": self.uuid,
            "postal_address": postal_address,
            "referent": referent,
            "email": email,
            "hasvat": self.model.division.organization.hasvat,
        }
        res.update(res_report)
        res.update(res_credit)

        return res

    def check_valid_capability(self, capability_id):
        """Check capability is valid for account: type, pods"""
        capability: ApiAccountCapability = self.controller.get_capability(capability_id)
        params = capability.get_params()
        capability_account_type: str = params.get("account_type", None)
        capability_pods: str = params.get("pods", None)

        # account_type
        if is_not_blank(self.account_type):
            if is_not_blank(capability_account_type):
                # check valid account_type
                if capability_account_type != self.account_type:
                    msg = "account_type %s of capability %s not match with account type %s" % (
                        capability_account_type,
                        capability_id,
                        self.account_type,
                    )
                    self.logger.error(msg)
                    raise Exception(msg)

        elif is_not_blank(capability_account_type):
            # set account_type
            self.account_type = capability_account_type
            self.update(account_type=self.account_type)

        # pods
        if is_not_blank(self.pods):
            if is_not_blank(capability_pods):
                # check valid pods
                if capability_pods != self.pods:
                    msg = "pods %s of capability %s not match with account pods %s" % (
                        capability_pods,
                        capability_id,
                        self.pods,
                    )
                    self.logger.error(msg)
                    raise Exception(msg)

        elif is_not_blank(capability_pods):
            # set pods
            self.pods = capability_pods
            self.update(pods=self.pods)
