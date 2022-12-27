# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import SwaggerApiView, ApiView,\
    PaginatedResponseSchema, PaginatedRequestQuerySchema,\
    ApiObjectResponseDateSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView
from beehive_service.views.account import ContainerInstancesItemResponseSchema

portal_organizations_roles = ['OrgAdminRole', 'OrgViewerRole', 'OrgOperatorRole']
portal_divisions_roles = ['DivAdminRole', 'DivViewerRole', 'DivOperatorRole']
portal_accounts_roles = ['AccountAdminRole', 'AccountViewerRole', 'AccountOperatorRole']
portal_catalogs_roles = ['CatalogAdminRole', 'CatalogViewerRole', 'CatalogOperatorRole']


class GetUserRolesAndServicesApiRequestSchema(Schema):
    user_name = fields.String(required=True,
                              example='user1', description='id, uuid or name of the user',
                              context='query')


class GetUserRolesAndServicesParamItemResponseSchema (Schema):
    user_role = fields.String(required=True, description='user role')
    org_id = fields.String(required=True,  example='1',  description='organization identifier')
    org_name = fields.String(required=True,  example='CSI Piemonte', description='organization name')
    org_desc = fields.String(required=True,  example='CSI Piemonte', description='organization description')
    org_uuid = fields.String(required=True,   example='234523545645', description='organization uuid')
    div_id = fields.String(required=True,   example='', description='division identifier')
    div_name = fields.String(required=True,   example='', description='division name')
    div_desc = fields.String(required=True,   example='', description='division description')
    div_uuid = fields.String(required=True,   example='', description='division uuid')
    account_id = fields.String(required=True,   example='', description='account identifier')
    account_name = fields.String(required=True,  example='', description='account name')
    account_desc = fields.String(required=True,   example='', description='account description')
    account_uuid = fields.String(required=True,   example='', description='account uuid')
    catalog_id = fields.String(required=True,   example='', description='catalog identifier')
    catalog_name = fields.String(required=True,   example='', description='catalog name')
    catalog_desc = fields.String(required=True,   example='', description='catalog description')
    catalog_uuid = fields.String(required=True,   example='', description='catalog uuid')


class GetUserRolesAndServicesResponseSchema (Schema):
    services = fields.Nested(GetUserRolesAndServicesParamItemResponseSchema, many=True, required=True, allow_none=True)


class GetUserRolesAndServicesByUserName(ServiceApiView):
    tags = ['authority']
    definitions = {
#         'GetUserRolesAndServicesApiRequestSchema': GetUserRolesAndServicesApiRequestSchema,
        'GetUserRolesAndServicesResponseSchema': GetUserRolesAndServicesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetUserRolesAndServicesApiRequestSchema)
    parameters_schema = GetUserRolesAndServicesApiRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetUserRolesAndServicesResponseSchema
        }
    })
    def get(self, controller, data, *args, **kwargs):
        """
        Filter service object by user name. Returns a list of objects of type organization, division, account, catalog with the user role associated to
        Filter service object by user name. Returns a list of objects of type organization, division, account, catalog with the user role associated to
        """
        orgs = {}
        org_ids = []
        divs = {}
        div_ids = []
        accounts = {}
        account_ids= []
        catalogs = {}
        catalog_ids = []

        # TODO management backoffice roles
        backoffice_roles = []

        # TODO management portal roles
        portal_roles = []
        portal_roles.extend(portal_organizations_roles)
        portal_roles.extend(portal_divisions_roles)
        portal_roles.extend(portal_accounts_roles)
        portal_roles.extend(portal_catalogs_roles)

        roles = []

        user_name = data.get('user_name')
        # get roles by groups
        groups = controller.get_user_groups(user_name, size=0).get('groups', [])
        for g in groups:
            roles.extend(controller.get_user_roles(group_name=g.get('id'),  size=0).get('roles'))

        #Attention: optimized call has a problem with the group_id_list request parameter
        #group_id_list = [str(g.get('id')) for g in groups]
        #roles.extend(controller.get_user_roles(group_id_list=group_id_list).get('roles'))

        # get roles by user name
        roles.extend(controller.get_user_roles(user_name=user_name,  size=0).get('roles'))

        # split roles to get object id
        for r in roles:
            try:
                role_name, service_id = r.get('name').split('-')
                if role_name.startswith('Account') and role_name in portal_roles:
                        accounts[service_id] = role_name
                        account_ids.append(service_id)
                elif role_name.startswith('Org') and role_name in portal_roles:
                        orgs[service_id] = role_name
                        org_ids.append(service_id)
                elif role_name.startswith('Div') and role_name in portal_roles:
                        divs[service_id] = role_name
                        div_ids.append(service_id)
                elif role_name.startswith('Catalog') and role_name in portal_roles:
                        catalogs[service_id] = role_name
                        catalog_ids.append(service_id)
            except:
                pass;

        objects = []
        total = 0

        if len (orgs) > 0:
            res_orgs, total_orgs = controller.get_organizations(id_list=org_ids, size=0)
            objects.extend(controller.get_user_object_and_role_info_org(res_orgs, orgs))
            total += total_orgs

        if len (divs) > 0:
            res_divs, total_divs = controller.get_divisions(id_list=div_ids, size=0)
            objects.extend(controller.get_user_object_and_role_info_div(res_divs, divs))
            total += total_divs

        if len (accounts) > 0:
            res_accounts, total_accounts = controller.get_accounts(id_list=account_ids, size=0)
            objects.extend(controller.get_user_object_and_role_info_account(res_accounts, accounts))
            total += total_accounts

        if len (catalogs) > 0:
            res_catalogs, total_cats = controller.get_service_catalogs(id_list=catalog_ids,  size=0)
            objects.extend(controller.get_user_object_and_role_info_catalog(res_catalogs, catalogs))
            total += total_cats

        res = {'services': objects}
        return res


class GetNivolaActiveServicesApiRequestSchema(Schema):
    pass


class GetNivolaActiveServicesResponse1Schema (Schema):
    service_container = fields.Nested(ContainerInstancesItemResponseSchema, many=True, required=True, allow_none=False)
    extraction_date = fields.DateTime(required=True)
    accounts = fields.Integer(required=True)
    divisions = fields.Integer(required=True)
    organizations = fields.Integer(required=True)


class GetNivolaActiveServicesResponseSchema (Schema):
    services = fields.Nested(GetNivolaActiveServicesResponse1Schema, required=True, many=False, allow_none=False)


class GetNivolaActiveServices(ServiceApiView):
    tags = ['authority']
    definitions = {
        'GetNivolaActiveServicesResponseSchema': GetNivolaActiveServicesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetNivolaActiveServicesApiRequestSchema)
    parameters_schema = GetNivolaActiveServicesApiRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetNivolaActiveServicesResponseSchema
        }
    })
    def get(self, controller, data, *args, **kwargs):
        """
         Returns the active services list in the nivola domain, for each service are provided informations about resources usage.
         Returns the active services list in the nivola domain, for each service are provided informations about resources usage.
        """

        # get service instant consume for all Nivola organization
        active_services = controller.get_service_instant_consume_by_nivola()

        self.logger.warning( 'active services=%s' % active_services)
        return {'services': active_services}


class GetServiceInstantConsumeRequestSchema(Schema):
    id = fields.Integer(required=True, description='id', context='path')


class GetServiceInstantConsumeParamsResponseSchema(ApiObjectResponseDateSchema):
    id = fields.Integer(required=True)
    account_id = fields.String(required=True)
    service_definition_id = fields.String(required=True)
    plugin_name_type = fields.String(required=True)
    metric_group_name = fields.String(required=True)
    metric_instant_value = fields.Float(required=True)
    metric_unit = fields.String(required=True)
    metric_value = fields.Float(required=True)
    job_id = fields.Integer(required=True)


class GetServiceInstantConsumeResponseSchema(Schema):
    serviceinst = fields.Nested(GetServiceInstantConsumeParamsResponseSchema, required=True, allow_none=True)


class GetServiceInstantConsume(ServiceApiView):
    tags = ['service']
    definitions = {
        'GetServiceInstantConsumeResponseSchema': GetServiceInstantConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetServiceInstantConsumeRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetServiceInstantConsumeResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kvargs):
        pass


class ListServiceInstantConsumeRequestSchema(PaginatedRequestQuerySchema):
    account_id = fields.String(required=False, context='query')
    service_instance_id = fields.String(required=False, context='query')
    plugin_name = fields.String(required=False, context='query')


class ListServiceInstantConsumeResponseSchema(PaginatedResponseSchema):
    service_instant_consumes = fields.Nested(GetServiceInstantConsumeParamsResponseSchema, many=True, required=True, allow_none=True)


class ListServiceInstantConsume(ServiceApiView):
    tags = ['service']
    definitions = {
        'ListServiceInstantConsumeResponseSchema': ListServiceInstantConsumeResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListServiceInstantConsumeRequestSchema)
    parameters_schema = ListServiceInstantConsumeRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListServiceInstantConsumeResponseSchema
        }
    })

    def get(self, controller, data, *args, **kvargs):
        pass


class NivolaAPI(ApiView):
    """Generic Service Object api routes:
    """
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = 'nws'

        rules = [
            ('%s/services/objects/filter/byusername' % base, 'GET', GetUserRolesAndServicesByUserName, {}),
            ('%s/services/activeservices' % base, 'GET', GetNivolaActiveServices, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
