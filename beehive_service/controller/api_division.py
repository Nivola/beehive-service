# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 CSI-Piemonte

from beehive.common.apimanager import ApiManagerWarning
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.controller.api_account import ApiAccount
from beehive_service.controller.api_wallet import ApiWallet
from beehive_service.entity import ServiceApiObject


class ApiDivision(AuthorityApiObject):
    objdef = "Organization.Division"
    objuri = "division"
    objname = "division"
    objdesc = "Division"

    role_templates = {
        "master": {
            "desc": "Division administrator. Can manage everything in the account",
            "desc_sp": "Master di Division",
            "name": "DivAdminRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "Organization.Division",
                    "objid": "<objid>",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account",
                    "objid": "<objid>" + "//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceInstanceConfig",
                    "objid": "<objid>" + "//*//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceLinkInst",
                    "objid": "<objid>" + "//*//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "<objid>" + "//*//*",
                    "action": "*",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "<objid>" + "//*//*",
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
            ],
        },
        "viewer": {
            "desc": "Division viewer. Can view everything in the account",
            "desc_sp": "Visualizzatore di Division",
            "name": "DivViewerRole-%s",
            "perms": [
                {
                    "subsystem": "service",
                    "type": "Organization.Division",
                    "objid": "<objid>",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account",
                    "objid": "<objid>" + "//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance",
                    "objid": "<objid>" + "//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceInstanceConfig",
                    "objid": "<objid>" + "//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceInstance.ServiceLinkInst",
                    "objid": "<objid>" + "//*//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceLink",
                    "objid": "<objid>" + "//*//*",
                    "action": "view",
                },
                {
                    "subsystem": "service",
                    "type": "Organization.Division.Account.ServiceTag",
                    "objid": "<objid>" + "//*//*",
                    "action": "view",
                },
            ],
        },
        "operator": {
            "desc": "Division operator. Can manage services in the account",
            "desc_sp": "Operatore di Division",
            "name": "DivOperatorRole-%s",
            "perms": [],
        },
    }

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.organization_id = None
        self.service_status_id = 1
        self.contact = None
        self.email = None
        self.postaladdress = None
        self.price_list_id = None

        if self.model is not None:
            self.organization_id = self.model.organization.uuid
            self.service_status_id = self.model.service_status_id
            self.contact = self.model.contact
            self.email = self.model.email
            self.postaladdress = self.model.postaladdress
            self.status = self.model.status.name

            # Assign current price list id
            if self.model.price_list is not None and len(self.model.price_list) > 0:
                self.price_list_id = self.model.price_list[0].id

        # child classes
        self.child_classes = [ApiAccount, ApiWallet]

        self.update_object = self.manager.update_division
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "organization_id": self.organization_id,
                "contact": self.contact,
                "email": self.email,
                "postaladdress": self.postaladdress,
                "status": self.status,
                "price_lists_id": self.price_list_id,
                "accounts": len(self.model.accounts.all()),
            }
        )

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def __repr__(self):
        return "<%s id=%s objid=%s name=%s>" % (
            "ApiDivision",
            self.oid,
            self.objid,
            self.name,
        )

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.


        :param args: custom params
        :param kvargs: custom params

        :return:

            kvargs

        :raise ApiManagerError:
        """
        # check there are active accounts and wallets
        if len(self.model.accounts.all()) > 0:
            msg = "Division %s has child accounts. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)

        if len(self.model.wallets.all()) > 0:
            msg = "Division %s has child wallets. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)

        return kvargs

    def get_credit_by_year(self, year):
        return self.manager.get_credit_by_authority_on_year(year, division_id=self.oid)

    def get_cost_by_period(
        self,
        start_period,
        end_period=None,
        plugin_name=None,
        reported=None,
        *args,
        **kvargs,
    ):
        """Get an aggregate ReportCost on period

        :param account_id:
        :param start_period: aggregation start period
        :param end_period: aggregation end period
        :param plugin_name: plugin name
        :return: total cost
        """
        return self.manager.get_cost_by_authority_on_period(
            period_start=start_period,
            period_end=end_period,
            division_id=self.oid,
            plugin_name=plugin_name,
            reported=reported,
        )

    def get_report_costconsume(self, year_month, start_date, end_date, report_mode, *args, **kvargs):
        """ """

        # get active account for division
        accounts, total = self.controller.get_accounts(division_id=self.oid, active=True, filter_expired=False, size=0)
        account_list_id = [account.oid for account in accounts]
        self.logger.debug("account_list_id=%s" % account_list_id)
        # get report cost for active account and period
        res_report = self.controller._format_report_costcomsume(
            account_list_id,
            year_month,
            start_date,
            end_date,
            report_mode,
            *args,
            **kvargs,
        )

        res_credit_summary = self.controller._format_report_credit_summary(
            account_list_id, [self.oid], year_month, start_date, end_date
        )
        res_credit_composition = self.controller._format_report_credit_composition(
            [self.oid], year_month, start_date, end_date
        )
        postal_address = "" if self.postaladdress is None else self.postaladdress
        referent = "" if self.contact is None else self.contact
        email = "" if self.email is None else self.email

        res = {
            "organization": self.model.organization.name,
            "organization_id": self.model.organization.uuid,
            "division": self.name,
            "division_id": self.uuid,
            "account": "",
            "account_id": "",
            "postal_address": postal_address,
            "referent": referent,
            "email": email,
            "hasvat": self.model.organization.hasvat,
        }
        res.update(res_report)
        res.update(res_credit_composition)
        res.update(res_credit_summary)

        return res
