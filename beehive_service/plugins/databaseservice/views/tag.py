# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive_service.views import ServiceApiView


class ListTagsForResource(ServiceApiView):
    """
    List tags for resource
    """

    pass


class AddTagsToResource(ServiceApiView):
    """
    Create a tag for resource
    """

    pass


class RemoveTagsFromResource(ServiceApiView):
    """
    Delete a tag from a  resource
    """

    pass
