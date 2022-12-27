# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import str2bool
from beehive.common.apimanager import ApiManagerWarning
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.controller.api_division import ApiDivision
from beehive_service.entity import ServiceApiObject


class ApiOrganization(AuthorityApiObject):
    objdef = 'Organization'
    objuri = 'organization'
    objname = 'organization'
    objdesc = 'Organization'

    role_templates = {
        'master': {
            'desc': 'Organization administrator. Can manage everything in the account',
            'desc_sp': 'Master di Organization',
            'name': 'OrgAdminRole-%s',
            'perms': [
                {'subsystem': 'service', 'type': 'Organization',
                 'objid': '<objid>', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division',
                 'objid': '<objid>' + '//*', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account',
                 'objid': '<objid>' + '//*//*', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceInstance',
                 'objid': '<objid>' + '//*//*//*', 'action': '*'},
                {'subsystem': 'service',
                 'type': 'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                 'objid': '<objid>' + '//*//*//*//*', 'action': '*'},
                {'subsystem': 'service',
                 'type': 'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                 'objid': '<objid>' + '//*//*//*//*', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceLink',
                 'objid': '<objid>' + '//*//*//*', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceTag',
                 'objid': '<objid>' + '//*//*//*', 'action': '*'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceLink',
                 'objid': '*//*//*//*', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceTag',
                 'objid': '*//*//*//*', 'action': 'view'},
            ],
        },
        'viewer': {
            'desc': 'Organization viewer. Can view everything in the account',
            'name': 'OrgViewerRole-%s',
            'desc_sp': 'Visualizzatore di Organization',
            'perms': [
                {'subsystem': 'service', 'type': 'Organization',
                 'objid': '<objid>', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division',
                 'objid': '<objid>' + '//*', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account',
                 'objid': '<objid>' + '//*//*', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceInstance',
                 'objid': '<objid>' + '//*//*//*', 'action': 'view'},
                {'subsystem': 'service',
                 'type': 'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                 'objid': '<objid>' + '//*//*//*//*', 'action': 'view'},
                {'subsystem': 'service',
                 'type': 'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                 'objid': '<objid>' + '//*//*//*//*', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceLink',
                 'objid': '<objid>' + '//*//*//*', 'action': 'view'},
                {'subsystem': 'service', 'type': 'Organization.Division.Account.ServiceTag',
                 'objid': '<objid>' + '//*//*//*', 'action': 'view'},
            ]
        },
        'operator': {
            'desc': 'Organization operator. Can manage services in the account',
            'desc_sp': 'Operatore di Organization',
            'name': 'OrgOperatorRole-%s',
            'perms': [
            ]
        }
    }

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        #  sostituiti con getters
        # self.org_type = None
        # self.ext_anag_id= None
        # self.attributes = None
        # self.hasvat = False
        # self.partner = False
        # self.referent = None
        # self.email = None
        # self.legalemail = None
        # self.postaladdress = None
        # self.service_status_id = 1


        #  if self.model is not None:
        #     self.org_type = self.model.org_type
        #     self.ext_anag_id = self.model.ext_anag_id
        #     self.attributes = self.model.attributes
        #     self.hasvat = self.model.hasvat
        #     self.partner = self.model.partner
        #     self.referent = self.model.referent
        #     self.email = self.model.email
        #     self.legalemail = self.model.legalemail
        #     self.postaladdress = self.model.postaladdress
        #     self.service_status_id = self.model.service_status_id
        #     self.status = self.model.status.name

        # child classes
        self.child_classes = [ApiDivision]

        self.update_object = self.manager.update_organization
        self.delete_object = self.manager.delete

    @property
    def org_type(self):
        if self.model is not None:
            return self.model.org_type
        else:
            return None

    @property
    def ext_anag_id(self):
        if self.model is not None:
            return self.model.ext_anag_id
        else:
            return None

    @property
    def attributes(self):
        if self.model is not None:
            return self.model.attributes
        else:
            return None

    @property
    def hasvat(self):
        if self.model is not None:
            return self.model.hasvat
        else:
            return None

    @property
    def partner(self):
        if self.model is not None:
            return self.model.partner
        else:
            return None

    @property
    def referent(self):
        if self.model is not None:
            return self.model.referent
        else:
            return None

    @property
    def email(self):
        if self.model is not None:
            return self.model.email
        else:
            return None

    @property
    def legalemail(self):
        if self.model is not None:
            return self.model.legalemail
        else:
            return None

    @property
    def postaladdress(self):
        if self.model is not None:
            return self.model.postaladdress
        else:
            return None

    @property
    def service_status_id(self):
        if self.model is not None:
            return self.model.service_status_id
        else:
            return None

    @property
    def status(self):
        if self.model is not None:
            return self.model.status.name
        else:
            return None

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = ServiceApiObject.info(self)
        info.update({
            'org_type': self.org_type,
            'ext_anag_id': self.ext_anag_id,
            'attributes': self.attributes,
            'hasvat': str2bool(self.hasvat),
            'partner': str2bool(self.partner),
            'referent': self.referent,
            'email': self.email,
            'legalemail': self.legalemail,
            'postaladdress': self.postaladdress,
            'status': self.status,
            'divisions': len(self.model.divisions.all())
        })
        return info

    def __repr__(self):
        return '<%s id=%s objid=%s name=%s>' % ('ApiOrganization', self.oid, self.objid, self.name)

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
        # check there are active divisions
        if len(self.model.divisions.all()) > 0 :
            msg = 'Organization %s has child divisions. Remove these before' % self.uuid
            self.logger.error(msg)
            raise ApiManagerWarning(msg)
        return kvargs

    def get_credit_by_year(self, year):
        return self.manager.get_credit_by_authority_on_year(year, organization_id=self.oid)

    def get_cost_by_period(self, start_period, end_period=None,
                plugin_name=None, reported=None, *args, **kvargs):
        """ Get an aggregate ReportCost by month

        :param start_period: aggregation start period
        :param end_period: aggregation end period
        :param plugin_name: plugin name
        :param reported: boolean to filter cost reported or unreported
        :return: total cost
        """
        return self.manager.get_cost_by_authority_on_period(period_start=start_period, period_end=end_period,
                            organization_id=self.oid, plugin_name=plugin_name, reported=reported)



    def get_report_costconsume (self, year_month, start_date, end_date, report_mode, *args, **kvargs):
        """
        """

        # get active division for organization
        divs, tot_divs = self.controller.get_divisions(organization_id=self.oid,
                                                            active=True,filter_expired=False,
                                                            size=0)
        div_list_id = [div.oid for div in divs]
        self.logger.warning ('divisions_list_id=%s' % div_list_id)

        accounts = []
        if len(div_list_id) > 0 :
            # get active account for division
            accounts, tot_accs = self.controller.get_accounts(division_id_list=div_list_id,
                                                            active=True,filter_expired=False,
                                                            size=0)

        account_list_id = [account.oid for account in accounts]
        self.logger.warning ('account_list_id=%s' % account_list_id)

        res_report = self.controller._format_report_costcomsume(account_list_id, year_month, start_date, end_date, report_mode, *args, **kvargs)
        res_credit_summary = self.controller._format_report_credit_summary(account_list_id, div_list_id, year_month, start_date, end_date)
        res_credit_composition = self.controller._format_report_credit_composition(div_list_id, year_month, start_date, end_date)

        postal_address = '' if self.postaladdress is None else self.postaladdress
        referent = '' if self.referent is None else self.referent
        email = '' if self.email is None else self.email

        res = {
            'organization': self.name,
            'organization_id': self.uuid,
            'division': '',
            'division_id': '',
            'account': '',
            'account_id': '',
            'postal_address': postal_address,
            'referent': referent,
            'email': email,
            'hasvat': self.hasvat,
        }
        res.update(res_report)
        res.update(res_credit_composition)
        res.update(res_credit_summary)

        return res