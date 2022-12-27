# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import format_date
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.entity import ServiceApiObject


class ApiAgreement(AuthorityApiObject):
    """Deprecated: this class wil be removed"""

    objdef = 'Organization.Division.Wallet.Agreement'
    objuri = 'agreement'
    objname = 'agreement'
    objdesc = 'Agreement'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)

        self.code = None
        self.amount = None
        self.agreement_date_start = None
        self.agreement_date_end = None
        self.wallet_id = None
        self.service_status_id = 1
        self.division_id = None
        self.year = None

        if self.model is not None:
            self.code = self.name
            self.amount = self.model.amount
            self.agreement_date_start = format_date(self.model.agreement_date_start, '%Y-%m-%d')
            self.agreement_date_end = format_date(self.model.agreement_date_end, '%Y-%m-%d')
            self.wallet_id = self.model.wallet.uuid
            self.service_status_id = self.model.service_status_id
            self.division_id = self.model.wallet.division.uuid
            self.year = self.model.wallet.year

        # child classes
        self.child_classes = [
        ]

        self.update_object = self.manager.update_agreement
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update( {
            'code': self.code,
            'amount': self.amount,
            'agreement_date_start': self.agreement_date_start,
            'agreement_date_end': self.agreement_date_end,
            'wallet_id': self.wallet_id,
            'service_status_id': self.service_status_id,
            'division_id': self.division_id,
            'year': self.year
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
        return '<%s id=%s objid=%s name=%s>' % (
                        'ApiAgreement',
                        self.oid, self.objid, self.name)