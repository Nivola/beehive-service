# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive.common.apimanager import (
    SwaggerApiView,
    ApiView,
    PaginatedResponseSchema,
    PaginatedRequestQuerySchema,
    ApiObjectResponseDateSchema,
)
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper
from beehive_service.views import ServiceApiView
from beehive_service.controller import ApiAccount, ApiDivision, ApiOrganization


class GetPortalDescRoleResponseSchema(Schema):
    generic_name = fields.String(
        required=True,
        metadata={"example": "AdminAccountRole", "description": "generic name entity role"},
    )
    desc_sp = fields.String(
        required=True,
        metadata={"example": "Master di Account", "description": "generic descripion of entity role"},
    )


class GetPortalDescRoleRequestSchema(Schema):
    role_name = fields.String(
        required=False,
        context="query",
        metadata={"example": "AdminAccountRole-9", "description": "name entity role"},
    )


class GetPortalDescRole(ServiceApiView):
    tags = ["service"]
    definitions = {
        "GetPortalDescRoleResponseSchema": GetPortalDescRoleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetPortalDescRoleRequestSchema)
    parameters_schema = GetPortalDescRoleRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetPortalDescRoleResponseSchema}}
    )
    response_schema = GetPortalDescRoleResponseSchema

    def get(self, controller, data, *args, **kvargs):
        """
        Returns the description of the requested role.
        """
        templates = [
            ApiAccount.role_templates,
            ApiDivision.role_templates,
            ApiOrganization.role_templates,
        ]
        for i in range(len(templates)):
            for k in templates[i].keys():
                role_items = templates[i].get(k)
                if role_items.get("name").split("-")[0] == data.get("role_name").split("-")[0]:
                    return {"desc_sp": role_items.get("desc_sp"), "generic_name": k}
        return None


class ListPortalRolesParamResponseSchema(Schema):
    name = fields.String(required=True, metadata={"example": "AdminAccountRole-1", "description": "name entity role"})
    desc_sp = fields.String(
        required=True,
        metadata={"example": "Master di Account", "description": "generic description of entity role"},
    )


class ListPortalRolesResponseSchema(Schema):
    roles = fields.Nested(ListPortalRolesParamResponseSchema, required=True, many=True)


class ListPortalDescRole(ServiceApiView):
    tags = ["service"]
    definitions = {
        "ListPortalRolesResponseSchema": ListPortalRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(Schema)
    parameters_schema = Schema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListPortalRolesResponseSchema}})
    response_schema = ListPortalRolesResponseSchema

    def get(self, controller, data, *args, **kvargs):
        """
        Returns a list of the all role description.
        """
        templates = [
            ApiAccount.role_templates,
            ApiDivision.role_templates,
            ApiOrganization.role_templates,
        ]
        roles = {"roles": []}
        resp = []
        for i in range(len(templates)):
            for k in templates[i].keys():
                role_items = templates[i].get(k)
                resp.append(
                    {
                        "desc_sp": role_items.get("desc_sp"),
                        "name": role_items.get("name").split("-")[0],
                    }
                )
        if resp is not None:
            roles.update({"roles": resp})
        return roles


class ServicePortalAPI(ApiView):
    """Generic Service Object api routes:"""

    @staticmethod
    def register_api(module, **kwargs):
        base = "nws"

        rules = [
            ("%s/roles/portaldesc" % base, "GET", GetPortalDescRole, {}),
            ("%s/roles/description" % base, "GET", GetPortalDescRole, {}),
            ("%s/roles/listportaldescription" % base, "GET", ListPortalDescRole, {}),
            ("%s/roles/listroledescription" % base, "GET", ListPortalDescRole, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
