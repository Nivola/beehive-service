# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive_service.views import ServiceApiView


class DescribeDBSnapshots (ServiceApiView):
    '''
        List DB Snapshots
    '''
    pass

class DescribeDBSnapshotAttributes (ServiceApiView):
    '''
        List DB Snapshot attribute
    '''
    pass

class CreateDBSnapshot (ServiceApiView):
    '''
        Create DB Snapshot
    '''
    pass

class CopyDBSnapshot (ServiceApiView):
    '''
        Copy DB Snapshot
    '''
    pass

class DeleteDBSnapshot (ServiceApiView):
    '''
        Delete DB Snapshot
    '''
    pass

class ModifyDBSnapshot (ServiceApiView):
    '''
        Modify DB Snapshot
    '''
    pass

class ModifyDBSnapshotAttribute (ServiceApiView):
    '''
        Modify DB Snapshot attribute
    '''
    pass

class RestoreDBInstanceFromDBSnapshot (ServiceApiView):
    '''
        List Snapshots
    '''
    pass
