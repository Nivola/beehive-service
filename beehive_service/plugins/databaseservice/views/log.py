# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive_service.views import ServiceApiView


class DescribeDBLogFiles(ServiceApiView):
    """
    List DB Log files
    """

    pass


class DownloadDBLogFilePortion(ServiceApiView):
    """
    Download a portion of DB Log file
    """

    pass
