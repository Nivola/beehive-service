# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from asyncio.log import logger
from beecell.simple import format_date
from beehive.common.apimanager import ApiObjectResponseDateSchema, ApiObjectSmallResponseSchema, ApiView, PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, ApiObjectResponseSchema, \
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema, \
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema, CrudApiObjectSimpleResponseSchema
from flasgger import fields, Schema
from marshmallow import ValidationError
from marshmallow.decorators import validates_schema
from marshmallow.validate import OneOf
from beecell.swagger import SwaggerHelper
from beehive_service.controller import ApiAccount, ServiceController, ApiAccountCapability
from beehive_service.views import ServiceApiView, ApiServiceObjectRequestSchema,\
    ApiObjectRequestFiltersSchema
from typing import List
try:
    from dateutil.parser import relativedelta
except ImportError as ex:
    from dateutil import relativedelta


class ListAccountsRequestSchema(ApiServiceObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                PaginatedRequestQuerySchema):
    service_status_id = fields.Integer(required=False, context='query')
    division_id = fields.String(required=False, context='query')
    contact = fields.String(required=False, context='query')
    email = fields.String(required=False, context='query')
    email_support = fields.String(required=False, context='query')
    email_support_link = fields.String(required=False, context='query')


class AccountServiceResponseSchema(Schema):
    base = fields.Integer(required=False)
    core = fields.Integer(required=False)

class AccountResponseSchema(ApiObjectResponseSchema):
    desc = fields.String(required=False, allow_none=True, default='test', example='test')
    #service_status_id = fields.Integer(required=False, default=6)
    version = fields.String(required=False, default='1.0')
    division_id = fields.String(required=True)
    note = fields.String(required=False, allow_none=True, default='')
    contact = fields.String(required=False, allow_none=True, default='')
    email = fields.String(required=False, allow_none=True, default='')
    email_support = fields.String(required=False, allow_none=True, default='')
    email_support_link = fields.String(required=False, allow_none=True, default='')
    managed = fields.Boolean(required=False, allow_none=True, default=False)
    acronym = fields.String(required=False, allow_none=True, default='')
    # fix
    status = fields.String(required=False, allow_none=True, default='')
    division_name = fields.String(required=False, allow_none=True, default='')
    services = fields.Nested(AccountServiceResponseSchema, required=False, allow_none=True)


class ListAccountsResponseSchema(PaginatedResponseSchema):
    accounts = fields.Nested(AccountResponseSchema,  many=True, required=True, allow_none=True)


class ListAccounts(ServiceApiView):
    summary = 'List accounts'
    description = 'List accounts'
    tags = ['authority']
    definitions = {
        'ListAccountsResponseSchema': ListAccountsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountsRequestSchema)
    parameters_schema = ListAccountsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListAccountsResponseSchema
        }
    })
    response_schema = ListAccountsResponseSchema

    def get(self, controller: ServiceController, data, *args, **kwargs):
        accounts, total = controller.get_accounts(**data)

        # get divs
        divs = self.get_division_idx(controller)

        services = controller.count_service_instances_by_accounts(accounts=[a.oid for a in accounts])
        for entity in accounts:
            entity.services = services.get(entity.oid, None)
            if entity.services is None:
                entity.services = {'core': 0, 'base': 0}

        res = []
        for r in accounts:
            info = r.info()
            info['division_name'] = getattr(divs[str(r.division_id)], 'name')
            res.append(info)
        resp = self.format_paginated_response(res, 'accounts', total, **data)

        # self.logger.info('+++++ ListAccounts get START')
        # self.logger.info('+++++ ListAccounts get - resp: %s' % (resp))
        # listAccountsResponseSchema = ListAccountsResponseSchema()
        # listAccountsResponseSchema.load(data=resp)
        # self.logger.info('+++++ ListAccounts get END')

        return resp


class GetAccountResponseSchema(Schema):
    account = fields.Nested(AccountResponseSchema, required=True, allow_none=True)


class GetAccount(ServiceApiView):
    summary = 'Get one account'
    description = 'Get one account'
    tags = ['authority']
    definitions = {
        'GetAccountResponseSchema': GetAccountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountResponseSchema
        }
    })
    response_schema = GetAccountResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.detail()
        resp = {'account': res}
        return resp


class GetAccountPerms(ServiceApiView):
    summary = 'Get account permissions'
    description = 'Get account permissions'
    tags = ['authority']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })
    response_schema = ApiObjectPermsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res, total = account.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


class CreateAccountServiceBaseRequestSchema(Schema):
    name = fields.String(required=True, example='prova')
    type = fields.String(required=True, example='medium')


class CreateAccountServiceRequestSchema(CreateAccountServiceBaseRequestSchema):
    template = fields.String(required=False)
    params = fields.Dict(required=False, missing={})
    require = fields.Nested(CreateAccountServiceBaseRequestSchema, required=False)


class CreateAccountParamRequestSchema(Schema):
    name = fields.String(required=True, example='default')
    acronym = fields.String(required=False, default='default', example='prova',
                            description='Account acronym. Set this for managed account')
    desc = fields.String(required=False, allow_none=True)
    division_id = fields.String(required=True)
    price_list_id = fields.String(required=False, allow_none=True)
    note = fields.String(required=False, allow_none=True)
    contact = fields.String(required=False, allow_none=True)
    email = fields.String(required=False, allow_none=True)
    email_support = fields.String(required=False, allow_none=True)
    email_support_link = fields.String(required=False, allow_none=True, default='')
    managed = fields.Boolean(required=False, description='if True account is managed', missing=True)

    @validates_schema
    def validate_parameters(self, data, *arg, **kvargs):
        managed = data.get('managed')
        if managed is True:
            acronym = data.get('acronym', None)
            if acronym is None:
                raise ValidationError('The acronym for managed account must bu specified')
            if len(acronym) > 10:
                raise ValidationError('The acronym can be up to 10 characters long')


class CreateAccountRequestSchema(Schema):
    account = fields.Nested(CreateAccountParamRequestSchema, context='body')


class CreateAccountBodyRequestSchema(Schema):
    body = fields.Nested(CreateAccountRequestSchema, context='body')


class CreateAccount(ServiceApiView):
    summary = 'Create an account'
    description = 'Create an account'
    tags = ['authority']
    definitions = {
        'CreateAccountRequestSchema': CreateAccountRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateAccountBodyRequestSchema)
    parameters_schema = CreateAccountRequestSchema
    responses = ServiceApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        # create the account
        data = data.get('account')
        resp = controller.add_account(**data)

        return {'uuid': resp}, 201


class UpdateAccountParamRequestSchema(Schema):
    name = fields.String(required=False, default='default')
    desc = fields.String(required=False, default='default')
    note = fields.String(required=False, default='default')
    price_list_id = fields.String(required=False, allow_none=True)
    contact = fields.String(required=False, default='default')
    email = fields.String(required=False, default='default')
    email_support = fields.String(required=False, default='default')
    email_support_link = fields.String(required=False, default='default')
    active = fields.Boolean(required=False, default=False)
    ### aggiunto 5/7/19
    acronym = fields.String(required=False, allow_none=True, default='')


class UpdateAccountRequestSchema(Schema):
    account = fields.Nested(UpdateAccountParamRequestSchema)


class UpdateAccountBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateAccountRequestSchema, context='body')


class UpdateAccount(ServiceApiView):
    summary = 'Update an account'
    description = 'Update an account'
    tags = ['authority']
    definitions = {
        'UpdateAccountRequestSchema': UpdateAccountRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateAccountBodyRequestSchema)
    parameters_schema = UpdateAccountRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller: ServiceController, data: dict, oid:str, *args, **kwargs):
        data = data.get('account')
        resp = controller.update_account(oid, data)
        return {'uuid': resp}, 200


class PatchAccountParamRequestSchema(Schema):
    services = fields.Nested(CreateAccountServiceRequestSchema, required=False, allow_none=True, many=True)


class PatchAccountRequestSchema(Schema):
    account = fields.Nested(PatchAccountParamRequestSchema)


class PatchAccountBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(PatchAccountRequestSchema, context='body')


class PatchAccount(ServiceApiView):
    summary = 'Patch an account'
    description = 'Patch an account'
    tags = ['authority']
    definitions = {
        'PatchAccountRequestSchema': PatchAccountRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(PatchAccountBodyRequestSchema)
    parameters_schema = PatchAccountRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })
    response_schema = CrudApiObjectResponseSchema

    def patch(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get('account')
        account.patch(**data)
        return {'uuid': account.uuid}, 200


class DeleteAccount(ServiceApiView):
    summary = 'Delete an account'
    description = 'Delete an account'
    tags = ['authority']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = ServiceApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        resp = account.delete(soft=True)
        return resp, 204


class GetAccountRolesItemResponseSchema(Schema):
    name = fields.String(required=True, example='master')
    desc = fields.String(required=True, example='')


class GetAccountRolesResponseSchema(Schema):
    roles = fields.Nested(GetAccountRolesItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True)


class GetAccountRoles(ServiceApiView):
    summary = 'Get account available logical authorization roles'
    description = 'Get account available logical authorization roles'
    tags = ['authority']
    definitions = {
        'GetAccountRolesResponseSchema': GetAccountRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountRolesResponseSchema
        }
    })
    response_schema = GetAccountRolesResponseSchema

    def get(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_role_templates()
        return {'roles': res, 'count': len(res)}


class ApiObjectResponseDateUsersSchema(ApiObjectResponseDateSchema):
    last_login = fields.DateTime(required=False, example='1990-12-31T23:59:59Z', description='last login date')


class GetAccountUsersItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example='master')
    email = fields.String(required=False)
    date = fields.Nested(ApiObjectResponseDateUsersSchema, required=True)


class GetAccountUsersResponseSchema(Schema):
    users = fields.Nested(GetAccountUsersItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True, example=0)


class GetAccountUsers(ServiceApiView):
    summary = 'Get account authorized users'
    description = 'Get account authorized users'
    tags = ['authority']
    definitions = {
        'GetAccountUsersResponseSchema': GetAccountUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountUsersResponseSchema
        }
    })
    response_schema = GetAccountUsersResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_users()
        return {'users': res, 'count': len(res)}


class SetAccountUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default='prova', description='User name, id or uuid')
    role = fields.String(required=False, default='prova', description='Role name, id or uuid',
                         validate=OneOf(ApiAccount.role_templates.keys()))


class SetAccountUsersRequestSchema(Schema):
    user = fields.Nested(SetAccountUsersParamRequestSchema)


class SetAccountUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetAccountUsersRequestSchema, context='body')


class SetAccountUsers(ServiceApiView):
    summary = 'Set account authorized user'
    description = 'Set account authorized user'
    tags = ['authority']
    definitions = {
        'SetAccountUsersRequestSchema': SetAccountUsersRequestSchema,
        'CrudApiObjectSimpleResponseSchema': CrudApiObjectSimpleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(SetAccountUsersBodyRequestSchema)
    parameters_schema = SetAccountUsersRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectSimpleResponseSchema
        }
    })
    response_schema = CrudApiObjectSimpleResponseSchema

    def post(self, controller, data, oid, *args, **kwargs):
        account: ApiAccount = controller.get_account(oid)
        data = data.get('user')
        resp = account.set_user(**data)
        return {'uuid': resp}, 200


class UnsetAccountUsersParamRequestSchema(Schema):
    user_id = fields.String(required=False, default='prova', description='User name, id or uuid')
    role = fields.String(required=False, default='prova', description='Role name, id or uuid',
                         validate=OneOf(ApiAccount.role_templates.keys()))


class UnsetAccountUsersRequestSchema(Schema):
    user = fields.Nested(UnsetAccountUsersParamRequestSchema)


class UnsetAccountUsersBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetAccountUsersRequestSchema, context='body')


class UnsetAccountUsers(ServiceApiView):
    summary = 'Unset account authorized user'
    description = 'Unset account authorized user'
    tags = ['authority']
    definitions = {
        'UnsetAccountUsersRequestSchema': UnsetAccountUsersRequestSchema,
        'CrudApiObjectSimpleResponseSchema': CrudApiObjectSimpleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UnsetAccountUsersBodyRequestSchema)
    parameters_schema = UnsetAccountUsersRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectSimpleResponseSchema
        }
    })
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        account: ApiAccount = controller.get_account(oid)
        data = data.get('user')
        resp = account.unset_user(**data)
        return {'uuid': resp}, 200


class GetAccountGroupsItemResponseSchema(ApiObjectResponseSchema):
    role = fields.String(required=True, example='master')


class GetAccountGroupsResponseSchema(Schema):
    groups = fields.Nested(GetAccountGroupsItemResponseSchema, required=True, many=True, allow_none=True)
    count = fields.Integer(required=True, example=0)


class GetAccountGroups(ServiceApiView):
    summary = 'Get account authorized groups'
    description = 'Get account authorized groups'
    tags = ['authority']
    definitions = {
        'GetAccountGroupsResponseSchema': GetAccountGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountGroupsResponseSchema
        }
    })
    response_schema = GetAccountGroupsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        res = account.get_groups()
        return {'groups': res, 'count': len(res)}


class SetAccountGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default='prova', description='Group name, id or uuid')
    role = fields.String(required=False, default='prova', description='Role name, id or uuid',
                         validate=OneOf(ApiAccount.role_templates.keys()))


class SetAccountGroupsRequestSchema(Schema):
    group = fields.Nested(SetAccountGroupsParamRequestSchema)


class SetAccountGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(SetAccountGroupsRequestSchema, context='body')


class SetAccountGroups(ServiceApiView):
    summary = 'Set account authorized group'
    description = 'Set account authorized group'
    tags = ['authority']
    definitions = {
        'SetAccountGroupsRequestSchema': SetAccountGroupsRequestSchema,
        'CrudApiObjectSimpleResponseSchema': CrudApiObjectSimpleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(SetAccountGroupsBodyRequestSchema)
    parameters_schema = SetAccountGroupsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectSimpleResponseSchema
        }
    })

    def post(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get('group')
        resp = account.set_group(**data)
        return {'uuid': resp}, 200


class UnsetAccountGroupsParamRequestSchema(Schema):
    group_id = fields.String(required=False, default='prova', description='Group name, id or uuid')
    role = fields.String(required=False, default='prova', description='Role name, id or uuid',
                         validate=OneOf(ApiAccount.role_templates.keys()))


class UnsetAccountGroupsRequestSchema(Schema):
    group = fields.Nested(UnsetAccountGroupsParamRequestSchema)


class UnsetAccountGroupsBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UnsetAccountGroupsRequestSchema, context='body')


class UnsetAccountGroups(ServiceApiView):
    summary = 'Unset account authorized group'
    description = 'Unset account authorized group'
    tags = ['authority']
    definitions = {
        'UnsetAccountGroupsRequestSchema': UnsetAccountGroupsRequestSchema,
        'CrudApiObjectSimpleResponseSchema': CrudApiObjectSimpleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UnsetAccountGroupsBodyRequestSchema)
    parameters_schema = UnsetAccountGroupsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectSimpleResponseSchema
        }
    })
    response_schema = CrudApiObjectSimpleResponseSchema

    def delete(self, controller, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        data = data.get('group')
        resp = account.unset_group(**data)
        return {'uuid': resp}, 200


class GetAccountRolesParamsResponseSchema(Schema):
    name = fields.String(required=True, example='master', description='Role name')
    id = fields.Integer(required=False, default='', description='role id')
    uuid = fields.String(required=False, default='', description='role uuid or objid')
    desc = fields.String(required=False, default='', description='Generic description')
    active = fields.Boolean(required=False, default=True, description='Describes if a user is active')
    alias = fields.String(required=False, description='role alias')


class GetAccountUsernameParamsResponseSchema(Schema):
    name = fields.String(required=True, example='', description='Username')
    id = fields.Integer(required=False, default='', description='user id')
    uuid = fields.String(required=False, default='', description='user uuid or objid')
    active = fields.Boolean(required=False, default=True, description='Describes if a user is active')
    desc = fields.String(required=False, default='', description='Generic description')
    contact = fields.String(required=False, allow_none=True, description='Primary contact Account')
    email = fields.String(required=False, allow_none=True, description='email Account')
    account_name = fields.String(required=False, default='', description='name of Account')
    account_status = fields.String(required=False, default='', description='status of Account')
    roles = fields.Nested(GetAccountRolesParamsResponseSchema,required=True, many=True, allow_none=True,
                          description='List of roles associated with the user')


class GetAccountUserRolesResponseSchema(Schema):
    usernames = fields.Nested(GetAccountUsernameParamsResponseSchema, required=True, many=True, allow_none=True)


class GetAccountUserRoles(ServiceApiView):
    summary = 'Get roles for all account\'s users'
    description = 'Get roles for all account\'s users'
    tags = ['authority']
    definitions = {
        'GetAccountUserRolesResponseSchema': GetAccountUserRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    parameters_schema = GetApiObjectRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountUserRolesResponseSchema
        }
    })
    response_schema = GetAccountUserRolesResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        account = controller.get_account(oid)
        resp = account.get_username_roles()
        return resp


# class GetAccountTaskResponseSchema(ApiObjectResponseSchema):
#     task_name = fields.String(required=False, default='')
#     instance_id = fields.String(required=True, example='')
#     task_id = fields.String(required=True, example='')
#     execution_id = fields.String(required=False, default='')
#     due_date = fields.DateTime(required=False)
#     created = fields.DateTime(required=False)
#
#
# class GetTasksResponseSchema(Schema):
#     tasks = fields.Nested(GetAccountTaskResponseSchema, many=True, required=True, allow_none=True)
#     # tasks = fields.List(GetAccountParamsResponseSchema, required=True, allow_none=True)
#
#
# class GetAccountUserTasks(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'GetTasksResponseSchema': GetTasksResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': GetTasksResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         Get account
#         Call this api to get a specific account
#         """
#         res = controller.account_user_task_list(oid)
#         resp = {'tasks': res}
#         return resp, 200


class AccountCapabilitiesDescriptionSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=True)
    active = fields.Boolean(required=True)


class AccountCapabilityAssociationDefinitionsSchema(ApiObjectSmallResponseSchema):
    pass

class AccountCapabilityAssociationServicesRequireSchema(Schema):
    name = fields.String(required=True)
    type = fields.String(required=True)


class AccountCapabilityAssociationServicesParamsSchema(Schema):
    vpc = fields.String(required=False)
    zone = fields.String(required=False)
    cidr = fields.String(required=False)


class AccountCapabilityAssociationServicesSchema(Schema):
    template = fields.String(required=False)
    type = fields.String(required=True)
    name = fields.String(required=True)
    status = fields.String(required=True)
    require = fields.Nested(AccountCapabilityAssociationServicesRequireSchema, required=False, allow_none=True)
    params = fields.Nested(AccountCapabilityAssociationServicesParamsSchema, required=False, allow_none=True)


class AccountCapabilityAssociationReportServicesSchema(Schema):
    required = fields.Integer(required=False)
    created = fields.Integer(required=False)
    error = fields.Integer(required=False)


class AccountCapabilityAssociationReportDefinitionsMissedSchema(Schema):
    pass


class AccountCapabilityAssociationReportDefinitionsSchema(Schema):
    required = fields.Integer(required=False)
    created = fields.Integer(required=False)
    missed = fields.Nested(AccountCapabilityAssociationReportDefinitionsMissedSchema, required=False, many=True, allow_none=True)


class AccountCapabilityAssociationReportSchema(Schema):
    services = fields.Nested(AccountCapabilityAssociationReportServicesSchema, required=False, allow_none=True)
    definitions = fields.Nested(AccountCapabilityAssociationReportDefinitionsSchema, required=False, allow_none=True)


class AccountCapabilityAssociationSchema(Schema):
    name = fields.String(required=True)
    # plugin_name = fields.String(required=True)
    status = fields.String(required=True)
    definitions = fields.Nested(AccountCapabilityAssociationDefinitionsSchema, required=True, many=True, allow_none=True)
    services = fields.Nested(AccountCapabilityAssociationServicesSchema, required=True, many=True, allow_none=True)
    report = fields.Nested(AccountCapabilityAssociationReportSchema, required=False, allow_none=True)


class GetAccountCapabilitiesResponseSchema(Schema):
    capabilities = fields.Nested(AccountCapabilityAssociationSchema, required=True, many=True, allow_none=True)


class GetAccountCapabilitiesRequestSchema(GetApiObjectRequestSchema):
    name = fields.String(required=False, description='name of the capability', context='query')


class GetAccountCapabilities(ServiceApiView):
    summary = 'Get account capabilities'
    description = 'Get account capabilities'
    tags = ['authority']
    definitions = {
        'GetAccountCapabilitiesResponseSchema': GetAccountCapabilitiesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetAccountCapabilitiesRequestSchema)
    parameters_schema = GetAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetAccountCapabilitiesResponseSchema
        }
    })
    response_schema = GetAccountCapabilitiesResponseSchema

    def get(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        capabilities = account.get_capabilities_list()
        if data.get('name', None) is not None:
            resp = []
            for cap in capabilities:
                if cap.get('name') == data.get('name'):
                    resp = [cap]
                    break
        else:
            resp = capabilities

        resp = {'capabilities': resp}
        return resp, 200


class AddAccountCapabilitiesRequestSchema(Schema):
    capabilities = fields.List(fields.String(required=True, allow_none=True), required=True, allow_none=True)


class AddAccountCapabilitiesBodyRequestSchema (GetApiObjectRequestSchema):
    body = fields.Nested(AddAccountCapabilitiesRequestSchema, context='body')


class AddAccountCapabilitiesResponseSchema (Schema):
    taskid = fields.UUID(default='db078b20-19c6-4f0e-909c-94745de667d4',
                         example='6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)


class AddAccountCapabilities(ServiceApiView):
    summary = 'Add account capability'
    description = 'Add account capability'
    tags = ['authority']
    definitions = {
         'AddAccountCapabilitiesRequestSchema': AddAccountCapabilitiesRequestSchema,
         'AddAccountCapabilitiesBodyRequestSchema': AddAccountCapabilitiesBodyRequestSchema,
    }

    parameters = SwaggerHelper().get_parameters(AddAccountCapabilitiesBodyRequestSchema)
    parameters_schema = AddAccountCapabilitiesRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': AddAccountCapabilitiesResponseSchema
        },
    })
    response_schema = AddAccountCapabilitiesResponseSchema

    def post(self, controller: ServiceController, data: dict, oid, *args, **kwargs):
        account = controller.get_account(oid)
        capabilities: List[str] = data.get('capabilities')
        resp = account.add_capabilities(capabilities)
        return resp


# class ListAccountAppliedBundleRequestSchema(Schema):
#     metric_type_id = fields.Integer(required=False, context='query', example='12',
#                                     description='metric type identifier for applied bundle')
#     start_date = fields.DateTime(required=False, context='query', example='',
#                                  description='start applied bundle validation date')
#     end_date = fields.DateTime(required=False, context='query', example='',
#                                description='end applied bundle validation date')
#
#
# class AppliedBundleResponseSchema(Schema):
#     id = fields.Integer(required=True)
#     metric_type_id = fields.Integer(required=True)
#     start_date = fields.DateTime(required=True)
#     end_date = fields.DateTime(required=False)
#
#
# class ListAccountAppliedBundleResponseSchema(Schema):
#     bundles = fields.Nested(AppliedBundleResponseSchema, many=True, required=True, allow_none=True)
#
#
# class ListAccountAppliedBundles(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'ListAccountAppliedBundleResponseSchema': ListAccountAppliedBundleResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(ListAccountAppliedBundleRequestSchema)
#     parameters_schema = ListAccountAppliedBundleRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ListAccountAppliedBundleResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         List applied bundle for an account
#         Call this api to list all the applied bundle for an account
#         """
#
#         bundles = []
#
#         res= controller.get_account_applied_bundles(oid, **data)
#         for r in res:
#             bundle = {}
#             bundle['id'] = r.id
#             bundle['metric_type_id'] = r.metric_type.uuid
#             bundle['start_date'] = format_date(r.start_date, "%Y-%m-%d")
#             if r.end_date is not None:
#                 bundle['end_date'] = format_date(r.end_date,"%Y-%m-%d" )
#
#             bundles.append(bundle)
#
#         resp = {'bundles': bundles}
#         return resp
#
#
# class GetAccountAppliedBundleResponseSchema(Schema):
#     bundle = fields.Nested(AppliedBundleResponseSchema, required=True)
#
# class GetAccountAppliedBundleRequestSchema(GetApiObjectRequestSchema):
#     bid = fields.String(required=True, description='id applied bundle', context='path')
#
# class GetAccountAppliedBundles(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'GetAccountAppliedBundleResponseSchema': GetAccountAppliedBundleResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetAccountAppliedBundleRequestSchema)
#     parameters_schema = GetAccountAppliedBundleRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': GetAccountAppliedBundleResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, bid, *args, **kwargs):
#         """
#         Get a specific applied bundle for a account
#         Call this api to get a specific account
#         """
#         account = controller.get_account(oid)
#         res = controller.get_account_applied_bundle(account.oid, bid)
#         resp = {'bundle': res}
#         return resp
#
# class SetAccountAppliedBundleParamRequestSchema(Schema):
#     metric_type_id = fields.String(required=True, example='12', description='metric type identifier for applied bundle')
#     start_date = fields.String(required=True, example='', description='start applied bundle validation date')
#     end_date = fields.String(required=False, allow_none= True, example='', description='end applied bundle validation date')
#
# class SetAccountAppliedBundleRequestSchema(Schema):
#     bundles = fields.Nested(SetAccountAppliedBundleParamRequestSchema, many=True, allow_none=False, context='body')
#
# class SetAccountAppliedBundleBodyRequestSchema(GetApiObjectRequestSchema):
#     body = fields.Nested(SetAccountAppliedBundleRequestSchema, context='body')
#
# class SetAccountAppliedBundles(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'SetAccountAppliedBundleRequestSchema': SetAccountAppliedBundleRequestSchema,
#         'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
#     }
#     parameters = SwaggerHelper().get_parameters(SetAccountAppliedBundleBodyRequestSchema)
#     parameters_schema = SetAccountAppliedBundleRequestSchema
#     responses = ServiceApiView.setResponses({
#         201: {
#             'description': 'success',
#             'schema': CrudApiObjectResponseSchema
#         }
#     })
#
#     def post(self, controller, data, oid, *args, **kwargs):
#         """
#             Register a applied bundle for an account object
#             Call this api to register a applied bundle for an account object
#         """
#         account = controller.get_account(oid)
#         # register applied bundle for account
#         controller.set_account_applied_bundle(account.oid, data.get('bundles',[]))
#         return {'uuid': account.uuid}, 201
#
# class UpdateAccountAppliedBundleParamRequestSchema(Schema):
#     id = fields.String(required=True, example='12', description='identifier applied bundle to update')
# #     metric_type_id = fields.String(required=True, example='12', description='metric type identifier for applied bundle')
# #     start_date = fields.String(required=True, example='01/01/1900', description='start applied bundle validation date')
#     end_date = fields.String(required=True, example='31/12/1900', description='end applied bundle validation date')
#
#
# class UpdateAccountAppliedBundleRequestSchema(Schema):
#     bundle = fields.Nested(UpdateAccountAppliedBundleParamRequestSchema)
#
#
# class UpdateAccountAppliedBundleBodyRequestSchema(GetApiObjectRequestSchema):
#     body = fields.Nested(UpdateAccountAppliedBundleRequestSchema, context='body')
#
#
# class UpdateAccountAppliedBundles(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'UpdateAccountAppliedBundleRequestSchema':UpdateAccountAppliedBundleRequestSchema,
#         'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
#     }
#     parameters = SwaggerHelper().get_parameters(UpdateAccountAppliedBundleBodyRequestSchema)
#     parameters_schema = UpdateAccountAppliedBundleRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': CrudApiObjectResponseSchema
#         }
#     })
#
#     def put(self, controller, data, oid, *args, **kwargs):
#         """
#             Update a applied bundle object for an account object
#             Call this api to update a applied bundle for an accolunt object
#         """
#         account = controller.get_account(oid)
#         controller.update_account_applied_bundle(account.oid, data)
#         return {'uuid':account.uuid}, 200
#
# class UnsetAccountAppliedBundlesParamRequestSchema(Schema):
#     id = fields.String(required=True, example='12', description='applied bundle id')
#
# class UnsetAccountAppliedBundlesRequestSchema(Schema):
#     bundle = fields.Nested(UnsetAccountAppliedBundlesParamRequestSchema)
#
# class UnsetAccountAppliedBundlesBodyRequestSchema(GetApiObjectRequestSchema):
#     body = fields.Nested(UnsetAccountAppliedBundlesRequestSchema, context='body')
#
# class UnsetAccountAppliedBundles(ServiceApiView):
#     tags = ['authority']
#     definitions = {
#         'UnsetAccountAppliedBundlesRequestSchema': UnsetAccountAppliedBundlesRequestSchema,
#         'CrudApiObjectSimpleResponseSchema': CrudApiObjectSimpleResponseSchema
#     }
#     parameters = SwaggerHelper().get_parameters(UnsetAccountAppliedBundlesBodyRequestSchema)
#     parameters_schema = UnsetAccountAppliedBundlesRequestSchema
#     responses = ServiceApiView.setResponses({
#         204: {
#             'description': 'no response'
#         }
#     })
#
#     def delete(self, controller, data, oid, *args, **kwargs):
#         """
#         Delete a specific applied bundle for an account object
#         Call this api to delete a applied bundle for an account object.
#         """
#         controller.get_account(oid)
#         bundle_id = data.get('bundle').get('id')
# #         resp = controller.manager.delete_applied_bundle(account_id=account.oid, id=bundle_id)
#         resp = controller.unset_account_applied_bundle(oid, bundle_id)
#         return resp, 204
#
#
# #
# # jobs
# #
# class JobResponseSchema(Schema):
#     id = fields.String(required=True, example='c518fa8b-1247-4f9f-9d73-785bcc24b8c7')
#     name = fields.String(required=True, example='beehive.module.scheduler.tasks.jobtest')
#     params = fields.String(required=True, example='...')
#     start_time = fields.String(required=True, example='16-06-2017 14:58:50.352286')
#     stop_time = fields.String(required=True, example='16-06-2017 14:58:50.399747')
#     status = fields.String(required=True, example='SUCCESS')
#     worker = fields.String(required=True, example='celery@tst-beehive-02')
#     # tasks = fields.Integer(required=True, example=1)
#     # jobs = fields.Integer(required=True, example=0)
#     elapsed = fields.Float(required=True, example=0.0474607944)
#     account = fields.Integer(required=True, example=0)
#
#
# class ListAccountJobsResponseSchema(Schema):
#     jobs = fields.Nested(JobResponseSchema, many=True, required=True, allow_none=True)
#     count = fields.Integer(required=True, example=1)
#
#
# class ListAccountJobsRequestSchema(GetApiObjectRequestSchema):
#     size = fields.Integer(required=False, allow_none=True, default=10, example=10, missing=10,
#                           description='max number of jobs listed', context='query')
#     page = fields.Integer(required=False, allow_none=True, default=10, example=10, missing=0,
#                           description='page of jobs list', context='query')
#     status = fields.String(required=False, allow_none=True, default='SUCCESS', example='SUCCESS',
#                            description='job status', context='query',)
#     job = fields.String(required=False, allow_none=True, default='SUCCESS', example='SUCCESS',
#                         description='job id', context='query',)
#     name = fields.String(required=False, allow_none=True, default='SUCCESS', example='SUCCESS',
#                          description='job name', context='query',)
#
#
# class ListAccountJobs(ServiceApiView):
#     tags = ['resource']
#     definitions = {
#         'ListAccountJobsRequestSchema': ListAccountJobsRequestSchema,
#         'ListAccountJobsResponseSchema': ListAccountJobsResponseSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(ListAccountJobsRequestSchema)
#     parameters_schema = ListAccountJobsRequestSchema
#     responses = ServiceApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': ListAccountJobsResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         List business jobs
#         List business jobs. Filter for account using <oid> or use 'all' to show unfiltered jobs
#         """
#         params = data
#         if oid != 'all':
#             # data['account'] = controller.get_account(oid).oid
#             params['account'] = controller.get_account(oid).uuid
#         jobs, count = controller.get_service_jobs(**params)
#         return {'jobs': jobs, 'count': count}


class ListAccountTagsItemResponseSchema(ApiObjectResponseSchema):
    services = fields.Integer(required=False, default=0, missing=0)
    links = fields.Integer(required=False, default=0, missing=0)
    version = fields.Integer(required=False, allow_none=True)


class ListAccountTagsResponseSchema(PaginatedResponseSchema):
    tags = fields.Nested(ListAccountTagsItemResponseSchema, required=True, many=True, allow_none=True)


class ListAccountTagsRequestSchema(GetApiObjectRequestSchema, ApiObjectRequestFiltersSchema,
                                   PaginatedRequestQuerySchema):
    pass


class ListAccountTags(ServiceApiView):
    summary = 'Get account tags'
    description = 'Get account tags'
    tags = ['authority']
    definitions = {
        'ListAccountTagsResponseSchema': ListAccountTagsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListAccountTagsRequestSchema)
    parameters_schema = ListAccountTagsRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListAccountTagsResponseSchema
        }
    })
    response_schema = ListAccountTagsResponseSchema

    def get(self, controller, data, oid, *args, **kwargs):
        objid_filter = controller.get_account(oid).objid + '%'
        res, total = controller.get_tags(objid=objid_filter)

        resp = [r.info() for r in res]
        resp = self.format_paginated_response(resp, 'tags', total, **data)
        return resp


class GetActiveServicesByAccountApiRequestSchema(Schema):
    oid = fields.String(required=True, description='id, uuid', context='path')
    plugin_name = fields.String(required=False, description='plugin name', context='query')


class MetricsItemResponseSchema(Schema):
    metric = fields.String(required=True, example='ram', description='metric name')
    value = fields.Float(required=True,  example=0.0, description='metric value consumed')
    unit = fields.String(required=True,  example='Gb', description='metric unit')
    quota = fields.Float(required=False, allow_none=True, example=0.0, description='Total quota available on container')


class ContainerInstancesItemResponseSchema(Schema):
    name = fields.String(required=True, example='computeservice-medium', description='service name')
    uuid = fields.String(required=True, example='148175b2-948a-4567-9ecd-9c80425fc8f0', description='service uuid')
    status = fields.String(required=True, example='ACTIVE', description='service status')
    plugin_type = fields.String(required=True, example='ComputeService', description='Service container plugin name')
    desc = fields.String(required=False)
    instances = fields.Integer(required=True, example=0, description='Num. instances')
    tot_metrics = fields.Nested(MetricsItemResponseSchema, many=True, required=True, allow_none=True)
    extraction_date = fields.DateTime(required=False, example='1990-12-31T23:59:59Z',
                                      description='metric extraction date')


class GetActiveServicesByAccountResponse1Schema(Schema):
    service_container = fields.Nested(ContainerInstancesItemResponseSchema, many=True, required=True, allow_none=False)
    extraction_date = fields.DateTime(required=True)


class GetActiveServicesByAccountResponseSchema(Schema):
    services = fields.Nested(GetActiveServicesByAccountResponse1Schema, required=True, many=False, allow_none=False)


class GetActiveServicesByAccount(ServiceApiView):
    summary = 'Returns the active services list for an account, for each service are provided information about ' \
              'resources usage'
    description = 'Returns the active services list for an account, for each service are provided information ' \
                  'about resources usage'
    tags = ['authority']
    definitions = {
        'GetActiveServicesByAccountApiRequestSchema': GetActiveServicesByAccountApiRequestSchema,
        'GetActiveServicesByAccountResponseSchema': GetActiveServicesByAccountResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetActiveServicesByAccountApiRequestSchema)
    parameters_schema = GetActiveServicesByAccountApiRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetActiveServicesByAccountResponseSchema
        }
    })
    response_schema = GetActiveServicesByAccountResponseSchema

    def get(self, controller: ServiceController, data, oid, *args, **kwargs):
        # get account
        account = controller.get_account(oid)
        # get related service instant consume
        active_services = controller.get_service_instant_consume_by_account(
            account.oid, plugin_name=data.get('plugin_name', None))

        return {'services': active_services}


class AccountAPI(ApiView):
    """AccountAPI
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'
        rules = [
            ('%s/accounts' % base, 'GET', ListAccounts, {}),
            ('%s/accounts/<oid>' % base, 'GET', GetAccount, {}),
            ('%s/accounts' % base, 'POST', CreateAccount, {}),
            ('%s/accounts/<oid>' % base, 'PUT', UpdateAccount, {}),
            ('%s/accounts/<oid>' % base, 'PATCH', PatchAccount, {}),
            ('%s/accounts/<oid>' % base, 'DELETE', DeleteAccount, {}),

            ('%s/accounts/<oid>/perms' % base, 'GET', GetAccountPerms, {}),
            ('%s/accounts/<oid>/roles' % base, 'GET', GetAccountRoles, {}),
            ('%s/accounts/<oid>/users' % base, 'GET', GetAccountUsers, {}),
            ('%s/accounts/<oid>/users' % base, 'POST', SetAccountUsers, {}),
            ('%s/accounts/<oid>/users' % base, 'DELETE', UnsetAccountUsers, {}),
            ('%s/accounts/<oid>/groups' % base, 'GET', GetAccountGroups, {}),
            ('%s/accounts/<oid>/groups' % base, 'POST', SetAccountGroups, {}),
            ('%s/accounts/<oid>/groups' % base, 'DELETE', UnsetAccountGroups, {}),

            # ('%s/accounts/<oid>/tasks' % base, 'GET', GetAccountUserTasks, {}),

            ('%s/accounts/<oid>/capabilities' % base, 'GET', GetAccountCapabilities, {}),
            ('%s/accounts/<oid>/capabilities' % base, 'POST', AddAccountCapabilities, {}),

            # ('%s/accounts/<oid>/appliedbundles/<bid>' % base, 'GET', GetAccountAppliedBundles, {}),
            # ('%s/accounts/<oid>/appliedbundles' % base, 'GET', ListAccountAppliedBundles, {}),
            # ('%s/accounts/<oid>/appliedbundles' % base, 'POST', SetAccountAppliedBundles, {}),
            # ('%s/accounts/<oid>/appliedbundles' % base, 'PUT', UpdateAccountAppliedBundles, {}),
            # ('%s/accounts/<oid>/appliedbundles' % base, 'DELETE', UnsetAccountAppliedBundles, {}),

            ('%s/accounts/<oid>/userroles' % base, 'GET', GetAccountUserRoles, {}),
            # ('%s/accounts/<oid>/jobs' % base, 'GET', ListAccountJobs, {}),
            ('%s/accounts/<oid>/tags' % base, 'GET', ListAccountTags, {}),

            ('%s/accounts/<oid>/activeservices' % base, 'GET', GetActiveServicesByAccount, {}),

        ]

        ApiView.register_api(module, rules, **kwargs)
