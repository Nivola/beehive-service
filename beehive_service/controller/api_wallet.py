# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from datetime import datetime

from beecell.simple import format_date
from beehive.common.apimanager import ApiManagerWarning
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.controller.api_agreement import ApiAgreement
from beehive_service.entity import ServiceApiObject


class ApiWallet(AuthorityApiObject):
    """Deprecated: this class wil be removed"""

    objdef = "Organization.Division.Wallet"
    objuri = "wallet"
    objname = "wallet"
    objdesc = "Wallet"

    ST_CLOSED = 22
    ST_ACTIVE = 1

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.capital_total = None
        self.capital_used = None
        self.evaluation_date = None
        self.division_id = None
        self.service_status_id = ApiWallet.ST_ACTIVE
        self.status = None
        self.year = None

        if self.model is not None:
            self.capital_total = self.model.capital_total
            self.capital_used = self.model.capital_used
            self.evaluation_date = format_date(self.model.evaluation_date)
            self.division_id = self.model.division.uuid
            self.service_status_id = self.model.service_status_id
            self.status = self.model.status.name
            self.year = self.model.year

        #       child classes
        self.child_classes = [ApiAgreement]
        #
        self.update_object = self.manager.update_wallet
        self.delete_object = self.manager.delete

    def get_capital_total(self):
        """Calculate capital total adding all the agreements

        :return: total capital
        """
        agreements, total = self.controller.get_agreements(wallet_id=self.oid, filter_expired=False)
        tot = 0
        for agreement in agreements:
            data = agreement.info()
            tot += float(data["amount"])
        return tot

    def close_year(self, force_closure=False):
        """Close the wallet and update capital_tot and capital_used for report on year.
        This lock all modify functions on agreements in the year
        """
        if self.service_status_id != ApiWallet.ST_ACTIVE:
            raise ApiManagerWarning("The status of the Wallet does not allow closing")

        first_year_str = "%s-01-01" % self.year
        last_year_str = "%s-12-31" % self.year

        if self.division_id is not None and self.year is not None:
            imp_non_rendicontato = self.get_cost_by_period(first_year_str, last_year_str, reported=False)

            # check if there are not reported costs
            if force_closure is False and imp_non_rendicontato is not None and imp_non_rendicontato > 0.0:
                self.logger.warn("wallet id=%s imp_non_rendicontato = %s" % (self.oid, imp_non_rendicontato))
                raise ApiManagerWarning(
                    "Could not close the Wallet. There are costs not reported in the year %s" % self.year
                )

            capital_total = self.get_credit_by_year(self.year)
            imp_rendicontato = self.get_cost_by_period(first_year_str, last_year_str, reported=True)

            capital_used = imp_rendicontato + imp_non_rendicontato
            self.update(
                service_status_id=ApiWallet.ST_CLOSED,
                evaluation_date=datetime.now(),
                capital_total=capital_total,
                capital_used=capital_used,
            )

        else:
            raise ApiManagerWarning("Could not close the Wallet. wallet not found")

    def open_year(self):
        """Reopen the wallet on year.
        This unlock all modify functions on agreements in the year
        """
        if self.service_status_id != ApiWallet.ST_CLOSED:
            raise ApiManagerWarning("The status of the Wallet does not allow reopening")
        self.update(service_status_id=ApiWallet.ST_ACTIVE, evaluation_date=None)

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update(
            {
                "capital_total": self.get_capital_total(),
                "capital_used": self.capital_used,
                "evaluation_date": self.evaluation_date,
                "division_id": self.division_id,
                "service_status_id": self.service_status_id,
                "status": self.status,
                "year": self.year,
            }
        )
        return info

    def __repr__(self):
        return "<%s id=%s objid=%s name=%s>" % (
            "ApiWallet",
            self.oid,
            self.objid,
            self.name,
        )

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend
        this function to manipulate and validate delete input params.


        :param args: custom params
        :param kvargs: custom params

        :return:

            kvargs

        :raise ApiManagerError:
        """

        if len(self.model.agreements.all()) > 0:
            msg = "Wallet %s has child agreements. Remove these before" % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)
        return kvargs
