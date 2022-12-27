# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from datetime import datetime
from copy import deepcopy
from beecell.simple import id_gen
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue
from kombu.pools import producers
from kombu import Connection, exceptions
from beehive.module.event.model import EventDbManager
from beehive.common.event import EventProducerRedis, Event
from beehive.common.data import operation
from beecell.db import TransactionError
from beehive.common.apimanager import ApiManager, ApiObject
from beehive_service.controller import ApiServiceType,\
    ApiServiceDefinition, ApiServiceConfig,\
    ApiServiceLinkDef
from beehive_service.entity.service_instance import ApiServiceInstance, ApiServiceLinkInst


class ServiceConsumerError(Exception): pass


class ServiceConsumerRedis(ConsumerMixin):
    def __init__(self, connection, api_manager):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)

        self.logger.info(u'ServiceConsumerRedis.__init__(...) ')

        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        self.manager = EventDbManager()

        self.api_module = api_manager.modules[u'ServiceModule']

        print(self.api_module)
        if self.api_module is not None:
            self.controller = self.api_module.get_controller()
            print(self.controller)

        self.redis_uri = self.api_manager.redis_service_uri
        self.redis_exchange = self.api_manager.redis_service_exchange

        self.exchange = Exchange(self.redis_exchange, type=u'direct',
                                 delivery_mode=1, durable=False)
        self.queue_name = u'%s.queue' % self.redis_exchange
        self.routing_key = u'%s.key' % self.redis_exchange
        self.queue = Queue(self.queue_name, self.exchange,
                           routing_key=self.routing_key,
                           delivery_mode=1, durable=False)

        self.logger.info(u'Service queue_name : %s' % self.queue_name)
        self.logger.info(u'Service routyng_key : %s' % self.routing_key)

        # subscriber
        #self.exchange_sub = Exchange(self.redis_exchange+u'.sub', type=u'topic',
        #                             delivery_mode=1)
        #self.queue_name_sub = u'%s.queue.sub' % self.redis_exchange
        #self.routing_key_sub = u'%s.sub.key' % self.redis_exchange
        #self.queue_sub = Queue(self.queue_name_sub, self.exchange_sub,
        #                       routing_key=self.routing_key_sub)

        self.event_producer = EventProducerRedis(self.redis_uri,
                                                 self.redis_exchange+u'.sub',
                                                 framework=u'kombu')
        self.conn = Connection(self.redis_uri)

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=[u'pickle', u'json'],
                         callbacks=[self.callback],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        self.logger.error(exc)




    def get_operation_id(self, objdef):
        """
            Split
        """
        temp = objdef.split(u'.')
        ids = [u'*' for i in temp]
        return u'//'.join(ids)

    def set_operation(self, ops):
        """
        """
        operation.perms = []
        for op in ops:
            perm = (1, 1, op.objtype, op.objdef, self.get_operation_id(op.objdef), 1, u'*')
            operation.perms.append(perm)
        self.logger.info(u'Set permissions: %s' % operation.perms)

        user = self.api_manager.auth_user.get(u'user')
        server = self.api_manager.server_name
        identity = u''
        print(u'user=%s, server=%s, identity=%s' %(user, server, identity))
        operation.user = (user, server, identity)

    #
    # Callback
    #
    def callback(self, event, message):

        try:
            ops = [
                ApiServiceType,
                ApiServiceInstance,
                ApiServiceDefinition,
                ApiServiceLinkDef,
                ApiServiceLinkInst,
                ApiServiceConfig
            ]

            self.set_operation(ops)

            # get db session
            operation.session = self.api_module.get_session()

            msg = message.decode()
            data = msg.get(u'data')


            action = data.get(u'action')
            self.logger.debug(u'action=%s' %action)

            if action == u'updateStatus':
                entity = data.get(u'entity')

                if entity in (u'ServiceInstance'):

                    inst_uuid = data.get(u'instance_uuid')

                    self.logger.debug(u'%s %s  instance_uuid=%s' %( action, entity, inst_uuid))
                    plugin = ApiServiceType(self.controller).instancePlugin(inst_uuid)
                    plugin.callback_update_status(inst_uuid, data)

            self.logger.debug(u'Service consume message : %s' % msg)
            self.logger.debug(u'XXXXX    Messaggio Consumato    XXXXX')
            message.ack()

        except Exception as ex:
            self.logger.error(u'Error consuming message  %s  - ERROR' % (str(msg)), exc_info=1)
            raise ex

        finally:
            message.ack()
            if operation.session is not None:
                self.api_module.release_session()
                self.logger.debug(u'XXXXX    Rilascio della session    XXXXX')

        self.log_event(event, message)
        # self.store_event(event, message)
        # self.publish_event_to_subscriber(event, message)

    def log_event(self, event, message):
        """Log received event

        :param event: json event to store
        :raise EventConsumerError:
        """

        self.logger.info(u'Consume event : %s  message : %s' % (event, message))

    def store_event(self, event, message):
        """Store event in db.

        :param event: json event to store
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()

            # clone event
            sevent = deepcopy(event)

            etype = sevent[u'type']

            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS'
            if etype == ApiObject.ASYNC_OPERATION:
                status = sevent[u'data'][u'response'][0]
                if status not in [u'STARTED', u'FAILURE', u'SUCCESS']:
                    return None

            creation = datetime.fromtimestamp(sevent[u'creation'])
            dest = sevent[u'dest']
            objid = dest.pop(u'objid')
            objdef = dest.pop(u'objdef')
            module = dest.pop(u'objtype')
            self.manager.add(sevent[u'id'], etype,
                             objid, objdef, module,
                             creation, sevent[u'data'],
                             event[u'source'], dest)

            self.logger.debug(u'Store event : %s' % sevent)
        except (TransactionError, Exception) as ex:
            self.logger.error(u'Error storing event : %s' % ex, exc_info=True)
            raise ServiceConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)

    def publish_event_to_subscriber(self, event, message):
        """Publish event to subscriber queue.

        :param event: json event to store
        :raise EventConsumerError:
        """
        self.__publish_event_simple(event[u'id'], event[u'type'],
                                    event[u'data'], event[u'source'],
                                    event[u'dest'])

    def __publish_event_simple(self, event_id, event_type, data, source, dest):
        try:
            self.event_producer.send(event_type, data, source, dest)
            self.logger.debug(u'Publish event %s to channel %s' %
                              (event_id, self.redis_exchange))
        except Exception as ex:
            self.logger.error(u'Event %s can not be published: %s' % (str(event_id), str(ex)), exc_info=1)

    def __publish_event_kombu(self, event_id, event_type, data, source, dest):
        try:
            event = Event(event_type, data, source, dest)
            producer = producers[self.conn].acquire()
            producer.publish(event.dict(),
                             serializer=u'json',
                             compression=u'bzip2',
                             exchange=self.exchange_sub,
                             declare=[self.exchange_sub],
                             routing_key=self.routing_key_sub,
                             expiration=60,
                             delivery_mode=1)
            producer.release()
            self.logger.debug(u'Publish event %s to exchenge %s' %
                              (event_id, self.exchange_sub))
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error(u'Event %s can not be published: %s' % (str(event_id), str(ex)), exc_info=1)
        except Exception as ex:
            self.logger.error(u'Event %s can not be published: %s' % (str(event_id), str(ex)), exc_info=1)

def start_event_consumer(params, log_path=None):
    """Start event consumer
    """
    # setup kombu logger
    #setup_logging(loglevel=u'DEBUG', loggers=[u''])

    # internal logger
    logger = logging.getLogger(u'beehive_service.event.manager_event')

    logger_level = logging.DEBUG
    if log_path is None:
        log_path = u'/var/log/%s/%s' % (params[u'api_package'],
                                        params[u'api_env'])


    logname = u'%s/%s.event.consumer' % (log_path, params[u'api_id'])

    logger_file = u'%s.log' % logname

    #loggers = [logging.getLogger(), logger]
    loggers = [logger,
                   logging.getLogger(u'oauthlib'),
                   logging.getLogger(u'beehive'),
                   logging.getLogger(u'beehive.db'),
                   logging.getLogger(u'beecell'),
                   logging.getLogger(u'beedrones'),
                   logging.getLogger(u'beehive_oauth2'),
                   logging.getLogger(u'beehive_monitor'),
                   logging.getLogger(u'beehive_service'),
                   logging.getLogger(u'beehive_resource')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, logger_file)

    # performance logging
    loggers = [logging.getLogger(u'beehive_service.perf')]
    logger_file = u'%s/%s.watch' % (log_path, params[u'api_id'])
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, logger_file,
                                      frmt=u'%(asctime)s - %(message)s')

    # setup api manager
    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()

    api_manager.get_session()

    def terminate(*args):
        worker.should_stop = True

    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)

    with Connection(api_manager.redis_service_uri) as conn:
        try:
            worker = ServiceConsumerRedis(conn, api_manager)
            logger.info(u'Start event consumer')
            logger.info(u'Active worker: %s' % worker)
            logger.debug(u'Use redis connection: %s' % conn)
            worker.run()
        except KeyboardInterrupt:
            logger.info(u'Stop event consumer')

    logger.info(u'Stop event consumer')
