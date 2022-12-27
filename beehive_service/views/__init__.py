# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import SwaggerApiView, ApiObjectResponseSchema, ApiManagerError, ApiManagerWarning
from flasgger import fields, Schema
from marshmallow.validate import Regexp
from beehive.common.data import transaction, operation
from beecell.simple import truncate
from beehive.common.assert_util import AssertUtil
from beehive_service.entity.service_instance import ApiServiceInstance
from beehive_service.controller import ServiceController
from marshmallow.decorators import validates_schema
from marshmallow.exceptions import ValidationError
from six import  text_type, binary_type
from typing import List, Type, Tuple, Any, Union, Dict

class ServiceApiView(SwaggerApiView):
    authorizable = True
    xmlns = 'http://nivolapiemonte.it/XMLdoc/2016-11-15/'

    consumes = [
        'application/xml',
        'application/json'
    ]
    produces = [
        'application/xml',
        'application/json',
        'text/plain'
    ]

    def format_create_response(self, root_field, instances_set):
        """Format create response with aws style

        :param root_field: root field like 'RunInstanceResponse'
        :param instances_set: list of response instances
        :return:
        """
        res = {
            root_field: {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'instancesSet': instances_set
            }
        }
        self.logger.debug('Service Aws response: %s' % res)
        return res

    def service_exist(self, controller: ServiceController, name:str, plugintype:str):
        exist = controller.exist_service_instance(name, plugintype)
        if exist is True:
            raise ApiManagerWarning('%s %s already exists' % (plugintype, name))

    def check_parent_service(self, controller: ServiceController, account_id:int, plugintype:str=None):
        return controller.check_service_type_plugin_parent_service(account_id, plugintype)

    def get_process_key(self, instance_model, method_key: str):
        if instance_model.service_definition.service_type.serviceProcesses is None:
            return None, None

        for p in instance_model.service_definition.service_type.serviceProcesses:
            if p.method_key == method_key:
                return p.process_key, p.template

        return None, None

    def get_account_list(self, controller, data, service_class):
        """
        :param controller: service controller
        :param data: request data
        :param service_class: service implementation class
        :return:
        """
        account_ids = data.get('owner_id_N', [])
        account_ids.extend(data.get('requester_id_N', []))
        account_ids.extend(data.get('owner_id', []))

        # if data.get('owner_id', None) is not None:

        account_id_list = []
        zone_list = []
        for accountId in account_ids:
            try:
                account = controller.get_account(accountId)
                services = controller.get_service_instances(fk_account_id=account.oid,
                                                            plugintype=service_class.plugintype,
                                                            active=True)
                if len(services) > 0:
                    account_id_list.append(str(account.oid))
                    if services[0].resource_uuid is not None:
                        zone_list.append(services[0].resource_uuid)
                else:
                    self.logger.warn('account %s does not have associated compute service' % accountId)
            except ApiManagerError as ex:
                if ex.code != 403:
                    raise
        self.logger.debug('Get accounts and zones by filter: %s %s' % (account_id_list, zone_list))
        return account_id_list, zone_list

    def get_organization_idx(self, controller: ServiceController):
        """Get organizations indexed by id TODO: use another get without limits
        """
        # orgs, tot = controller.get_organizations(authorize=False, size=100)
        # return {str(a.oid): a for a in orgs}
        return controller.get_organization_idx()

    def get_division_idx(self, controller: ServiceController):
        """Get divisions indexed by id TODO: use another get without limits
        """
        # divs, tot = controller.get_divisions(authorize=False, size=100)
        # return {str(a.oid): a for a in divs}
        return controller.get_division_idx()

    def get_account_idx(self, controller: ServiceController):
        """Get accounts indexed by id TODO: use another get without limits
        """
        # accounts, tot = controller.get_accounts(authorize=False, size=100)
        # return {str(a.oid): a for a in accounts}
        return controller.get_account_idx()

    def get_service_definition_idx(self, controller: ServiceController, plugintype: str):
        """Get service instance indexed by id and uuid
        """
        # data, tot = controller.get_paginated_service_defs(plugintype=plugintype,
        #                                                   authorize=False,
        #                                                   size=1000)
        # res = {}
        # for item in data:
        #     res[item.uuid] = item
        #     res[str(item.oid)] = item
        # self.logger.debug('Index service definition : %s' % truncate(res))
        # return res
        return controller.get_service_definition_idx(plugintype)

    def get_service_instance_idx(self, controller, plugintype):
        """Get service instance indexed by id and uuid
        """
        # data, tot = controller.get_paginated_service_instances(filter_expired=False,
        #                                                        plugintype=plugintype,
        #                                                        authorize=False,
        #                                                        size=1000)
        # res = {}
        # for item in data:
        #     res[item.uuid] = item
        #     res[str(item.oid)] = item
        #     res[item.resource_uuid] = item
        # self.logger.debug('Index service instance : %s' % truncate(res))
        # return res
        return controller.get_service_instance_idx(plugintype)

    def get_tag_instance_idx(self, controller, *args, **kvargs):
        """Get service instance filter by a specific tag. Results are indexed by id and uuid
        """
        data, tot = controller.get_tags(filter_expired=False, authorize=False, *args, **kvargs)
        res = {}
        for item in data:
            res[item.name] = item
            res[item.uuid] = item
            res[str(item.oid)] = item
        self.logger.debug('Index tag instance : %s' % res)
        return res

    def delete_service_instance(self, controller, srv_inst, data, recursive_delete=True, batch=True):
        controller.delete_service_instance(srv_inst, data, recursive_delete=recursive_delete, batch=batch)
        resp = {'uuid': srv_inst.uuid}
        return resp, 204


class ApiObjectRequestFiltersSchema(Schema):
    filter_expired = fields.Boolean(required=False, context='query', missing=False)
    filter_creation_date_start = fields.DateTime(required=False, context='query')
    filter_creation_date_stop = fields.DateTime(required=False, context='query')
    filter_modification_date_start = fields.DateTime(required=False, context='query')
    filter_modification_date_stop = fields.DateTime(required=False, context='query')
    filter_expiry_date_start = fields.DateTime(required=False, context='query')
    filter_expiry_date_stop = fields.DateTime(required=False, context='query')


class ApiServiceObjectRequestSchema(Schema):
    name = fields.String(required=False, context='query')
    objid = fields.String(required=False, context='query')
    version = fields.String(required=False, context='query')
    active = fields.Boolean(required=False, context='query')


class ApiBaseServiceObjectCreateRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=False, allow_none=True)
    active = fields.Boolean(required=False, allow_none=True)


class ApiServiceObjectCreateRequestSchema(ApiBaseServiceObjectCreateRequestSchema):
    version = fields.String(required=True)


class ApiServiceObjectResponseSchema(ApiObjectResponseSchema):
    version = fields.String(required=False, allow_none=True)


class ServiceRegexp(Regexp):
    """Validate ``value`` against the provided regex.

    :param regex: The regular expression string to use. Can also be a compiled
        regular expression pattern.
    :param flags: The regexp flags to use, for example re.IGNORECASE. Ignored
        if ``regex`` is not a string.
    :param str error: Error message to raise in case of a validation error.
        Can be interpolated with `{input}` and `{regex}`.
    """

    def __call__(self, value):
        ch_value = None
        # if isinstance(value, unicode) or isinstance(value, str):
        if isinstance(value, (text_type, binary_type)):
            ch_value = value
        else:
            ch_value = '%s' % value

        return super(ServiceRegexp, self).__call__(ch_value)


class ServiceValidateDate(Schema):

    @validates_schema
    def validate_date_parameters(self, data):
        '''
        '''
        date_is_not_valid = True
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)

        if start_date is not None and end_date is not None:

            if start_date.year != end_date.year:
                raise ValidationError(
                    'Param start_date %s and end_date %s can be refer the same year' % (start_date, end_date))

            if start_date.year > end_date.year:
                raise ValidationError(
                    'Param start_date %s and end_date %s are not in a valid range' % (start_date, end_date))

            date_is_not_valid = False

        if data.get('year_month', None) is None and date_is_not_valid:
            raise ValidationError('Param year_month or start_date and end_date cannot be None')

#Added to avoid empty string value
class NotEmptyString(fields.String):
    """A String field type where empty string is deserialized to None"""

    def _deserialize(self, value, attr, data,**kwargs):
        if value == '':
            return None
        return super()._deserialize(value, attr, data,**kwargs)
