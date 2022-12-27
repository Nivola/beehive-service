# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import str2bool
from beehive_service.entity import ServiceApiObject
from beehive_service.model.service_job_schedule import ServiceJobSchedule


class ApiServiceJobSchedule(ServiceApiObject):
    objdef = 'ServiceJobSchedule'
    objuri = 'servicejobschedule'
    objname = 'servicejobschedule'
    objdesc = 'servicejobschedule'

    def __init__(self, *args, **kvargs):
        """ """
        ServiceApiObject.__init__(self, *args, **kvargs)
        #         self.job_name = None
        #         self.params = None
        #
        #         if self.model is not None:
        #             self.job_name = self.model.job_name
        #             self.params = self.model.params
        # child classes
        self.child_classes = []

        self.update_object = self.manager.update_service_job_schedule
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        info = ServiceApiObject.info(self)

        if self.model is not None:
            info.update({
               'job_name' : self.model.job_name,
               'job_options' : self.model.job_options,
               'schedule_type': self.model.schedule_type,
               'schedule_params': self.model.schedule_params,
               'retry_policy': self.model.retry_policy,
               'retry': str2bool(self.model.retry),
               'job_args': self.model.job_args,
               'job_kvargs': self.model.job_kvargs,
               'relative': str2bool(self.model.relative)
            })

        return info

    def detail(self):
        """Get object extended info
        """
        info = self.info()
        return info

    def scheduler_data(self):
        """
        """
        info = ServiceApiObject.info(self)
        self.model: ServiceJobSchedule
        if self.model is not None:
            info.update({
                'name': self.model.name,
                'task': self.model.job_name,
                'args': self.model.job_args,
                'kvargs': self.model.job_kvargs,
                'options': self.model.job_options,
                'schedule': {'type': 'unknow'},
                'relative': str2bool(self.model.relative),
                # 'retry': str2bool(self.model.retry),
                # 'retry_policy': self.model.retry_policy,
            })
            schedule = self.model.schedule_params.copy()
            schedule['type'] = self.model.schedule_type

            info['schedule'] = schedule

        return {'schedule': info}

    def start(self):

        data = self.scheduler_data()

        self.logger.debug2('Schedule "%s" id:%s' %(self.model.job_name, self.oid))
        res = self.api_client.admin_request('service', '/v2.0/nws/scheduler/entries', 'post', data=data)
        self.logger.debug2('START Schedule instance "%s" id:%s - %s' % (self.model.job_name, self.oid, res))

        return self.oid

    def stop(self):
        uri = '/v2.0/nws/scheduler/entries/%s' % self.name
        res = self.api_client.admin_request('service', uri, 'delete')
        self.logger.info('Deleted schedule %s' % self.name)

        self.logger.info('Deleted schedule %s' % res)

        return self.oid

    def restart(self):
        try:
            self.stop()
        except :
            pass
        return self.start()