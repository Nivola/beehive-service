# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from re import match
from six.moves.urllib.parse import urlencode
from beehive.common.apimanager import ApiController, ApiManagerError, ApiManagerWarning
from beecell.types.type_string import validate_string, truncate, compat, str2bool
from beecell.types.type_date import format_date
from beecell.types.type_id import id_gen
from beecell.simple import import_class
from beehive.common.data import trace, operation, maybe_run_batch_greenlet
from beehive.common.model import ENTITY
from beecell.db import QueryError, TransactionError
# from beehive_service.controller import ApiOrganization, AuthorityApiObject, ApiWallet, \
#     ApiAccountCapability, ApiAccount, ApiDivision, ApiServiceTag, ApiServiceJob, ApiServiceJobSchedule, \
#     ApiServicePriceList, ApiServicePriceMetric, ApiServiceMetricType, ApiAgreement
from beehive_service.controller.api_agreement import ApiAgreement
from beehive_service.controller.api_service_job import ApiServiceJob
from beehive_service.controller.api_account import ApiAccount
from beehive_service.controller.api_account_capability import ApiAccountCapability
from beehive_service.controller.api_division import ApiDivision
from beehive_service.controller.api_orgnization import ApiOrganization
from beehive_service.controller.api_serviceJob_schedule import ApiServiceJobSchedule
from beehive_service.controller.api_service_metric_type import ApiServiceMetricType
from beehive_service.controller.api_service_price_list import ApiServicePriceList
from beehive_service.controller.api_service_price_metric import ApiServicePriceMetric
from beehive_service.controller.api_service_tag import ApiServiceTag
from beehive_service.controller.api_wallet import ApiWallet
from beehive_service.controller.authority_api_object import AuthorityApiObject
from beehive_service.entity.account_service_definition import ApiAccountServiceDefinition
from beehive_service.entity.service_catalog import ApiServiceCatalog
from beehive_service.entity.service_definition import ApiServiceDefinition, ApiServiceConfig, ApiServiceLinkDef
from beehive_service.entity.service_type import ApiServiceType, ApiServiceProcess
from beehive_service.model import ServiceInstance, ServiceDefinition, ServiceMetric, \
    ServiceMetricType, \
    ServiceMetricTypeLimit, AppliedBundle,  ServiceType
from beehive_service.model.account import Account, AccountServiceDefinition
from beehive_service.model.base import SrvPluginTypeCategory, SrvStatusType, ConfParamType, OrgType
# from beehive_service.model.views import ServiceMetricConsumeView
from beehive_service.model.service_job_schedule import ServiceJobSchedule
from beehive_service.model.service_job import ServiceJob
from beehive_service.model.service_metric_type import MetricType
from beehive_service.model.aggreagate_cost import AggregateCost
from beehive_service.model.service_instance import ServiceInstanceConfig, ServiceTypePluginInstance
from beehive_service.model.service_link import ServiceLink
from beehive_service.model.service_tag import ServiceTag
from beehive_service.model.service_catalog import ServiceCatalog
from beehive_service.model.service_definition import ServiceConfig
from beehive_service.model.service_process import ServiceProcess
from beehive_service.model.account_capability import AccountCapability
from beehive_service.model.organization import Organization
from beehive_service.model.monitoring_message import MonitoringMessage
from beehive_service.model.division import Division
from beehive_service.model.deprecated import Agreement, Wallet, MetricTypePluginType, ServicePriceList, \
    ServicePriceMetricThresholds, ServicePriceMetric
from beehive_service.model.service_link_instance import ServiceLinkInstance
from beehive_service.model.service_link_def import ServiceLinkDef
from beehive_service.dao.ServiceDao import ServiceDbManager
from beehive_service.entity.service_instance import ApiServiceInstance, ApiServiceInstanceConfig, \
    ApiServiceInstanceLink, ApiServiceLinkInst
from beehive.common.assert_util import AssertUtil
from beehive.common.data import transaction
import json
from beehive_service.service_util import ServiceUtil
from beehive.common.task_v2 import prepare_or_run_task
from beehive.common.task_v2.manager import task_manager
from datetime import datetime, date, timedelta
from dateutil.parser import parse
from beehive_service.service_util import __SRV_REPORT_COMPLETE_MODE__
try:
    from dateutil.parser import relativedelta
except ImportError as ex:
    from dateutil import relativedelta
from typing import List, Type, Tuple, Any, Union, Dict, TypeVar, Callable
from beecell.simple import jsonDumps


class ServiceLinkType(object):
    SRVLINKDEF_L = 'servicelinkdef'
    SRVLINKDEF_U = 'ServiceLinkDef'
    SRVLINKINST_L = 'servicelinkinst'
    SRVLINKINST_U = 'ServiceLinkInst'


APIOBJ= TypeVar('APIOBJ')
APIPLUGIN= TypeVar('APIPLUGIN')

class ServiceController(ApiController):
    """Service Module controller.
    """
    version = 'v1.0'

    def __init__(self, module):
        ApiController.__init__(self, module)

        self.manager = ServiceDbManager()

        self.child_classes = [
            ApiOrganization,
            ApiServiceType,
            ApiServiceCatalog,
            ApiServiceJob,
            ApiServicePriceList,
            ApiAccountCapability,
            ApiServiceJobSchedule,
            ApiServiceMetricType,
        ]

    def resolve_fk_id(self, key, get_entity, data, new_key=None):
        fk = data.get(key)
        if fk is not None and not isinstance(fk, int) and not fk.isdigit():
            oid = self.resolve_oid(fk, get_entity)
            if new_key is None:
                data[key] = oid
            else:
                data.pop(key)
                data[new_key] = oid
        else:
            if new_key is not None and data.get(key, None) is not None:
                data[new_key] = data.pop(key, None)

    def resolve_oid(self, fk, get_entity):
        res = fk
        if fk is not None and not isinstance(fk, int) and not fk.isdigit():
            res = get_entity(fk).oid
        return res

    def populate(self, db_uri: str):
        """Populate initial data in service database

        :param db_uri: database uri
        :return:
        """
        self.manager.populate(db_uri)

    def getInstanceMetric(self, instance_id, resource_uuid, job_id):
        """
        TODO Check if used is stille necessary
        """
        AssertUtil.assert_is_not_none(instance_id)
        instance = self.get_service_instance(instance_id)
        plugins = self.instancePlugin(None, instance)

        metrics_dict = plugins.acquire_metric(resource_uuid)
        return metrics_dict


    #
    # index methods
    #
    def get_entities_idx(self,
                         entity_class: Type[APIOBJ],
                         query_func: Callable[[Dict[str, Any]], Tuple[ENTITY, int]],
                         index_key: str=None, *args, **kvargs) -> Dict[str, APIOBJ]:
        """Get entities indexed by id

        :param entity_class:
        :param query_func:
        :param index_key: alternative index key
        :param args:
        :param kvargs:
        :return:
        """
        entities: List[ENTITY]
        tot: int
        entities, tot = query_func(with_perm_tag=False, filter_expired=False, size=-1, *args, **kvargs)
        res: Dict[str, APIOBJ] = {}
        for entity in entities:
            obj = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                               desc=entity.desc, model=entity)
            if index_key is not None:
                res[str(getattr(entity, index_key))] = obj
            else:
                res[str(entity.id)] = obj
                res[entity.uuid] = obj
                res[entity.name] = obj
                resource_uuid = getattr(entity, 'resource_uuid', None)
                if resource_uuid is not None:
                    res[resource_uuid] = obj
        return res

    def get_organization_idx(self) -> Dict[str, ApiOrganization]:
        """Get organizations indexed by id and uuid
        """
        ret: Dict[str, ApiOrganization] = self.get_entities_idx(ApiOrganization, self.manager.get_organizations)
        return ret

    def get_division_idx(self) -> Dict[str, ApiDivision]:
        """Get divisions indexed by id and uuid
        """
        ret: Dict[str, ApiDivision] = self.get_entities_idx(ApiDivision, self.manager.get_divisions)
        return ret

    def get_account_idx(self) -> Dict[str, ApiAccount]:
        """Get accounts indexed by id and uuid
        """
        ret: Dict[str, ApiAccount] = self.get_entities_idx(ApiAccount, self.manager.get_accounts)
        return ret

    def get_service_definition_idx(self, plugintype: str) -> Dict[str, ApiServiceDefinition]:
        """Get service definition indexed by id and uuid
        """
        ret: Dict[str, ApiServiceDefinition] = self.get_entities_idx(
            ApiServiceDefinition, self.manager.get_paginated_service_definitions, plugintype=plugintype)
        return ret

    def get_service_instance_idx(self, plugintype, *args, **kvargs) -> Dict[str, ApiServiceInstance]:
        """Get service instance indexed by id and uuid or custom index_key
        """
        ret: Dict[str, ApiServiceInstance] = self.get_entities_idx(
            ApiServiceInstance, self.manager.get_paginated_service_instances, plugintype=plugintype, *args, **kvargs)
        return ret

    def get_service_instance_config_idx(self, *args, **kvargs)-> Dict[str, ApiServiceInstanceConfig]:
        """Get service instance config indexed by id and uuid or custom index_key
        """
        ret: Dict[str, ApiServiceInstanceConfig] = self.get_entities_idx(
            ApiServiceInstanceConfig, self.manager.get_paginated_service_instance_configs, *args, **kvargs)
        return ret

    @transaction
    def emptytransaction(self):
        """ Dummy transaction used in order to be sure tihave a clean database session
            it should call operation.session.commit();
        """
        pass

    ############################
    ###    ServiceJobs       ###
    ############################
    @trace(entity='ApiServiceJob', op='insert')
    def add_job(self, job_id:str, job_name:str, params) -> ServiceJob:
        """Add job

        :param job_id: job id
        :param job_name: task name
        :param params: job data
        :return:
        """
        job_record = ServiceJob(id_gen(), job_id, job_name, None, job_id, params=compat(params))
        self.manager.add(job_record)
        return job_record

    @trace(entity='ApiServiceJob', op='insert')
    def add_service_job(self, taskid, name, account_id, data):
        """Add service job

        :param taskid: job id
        :param name: task name
        :param account_id: account id. Can be None
        :param data: job data
        :return: ApiServiceJob
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        job_record = ServiceJob(id_gen(), taskid, name, account_id, taskid, params=compat(data))
        self.manager.add(job_record)
        self.logger.debug('Add job %s' % job_record)

    @trace(entity='ApiServiceJob', op='use')
    def get_service_jobs(self, status=None, job=None, name=None, account=None, size=10, page=0, *args, **kvargs):
        """Get resource jobs.

        :param status: jobstatus [optional]
        :param job: job id. [optional]
        :param name: job name. [optional]
        :param account: account uuid. [optional]
        :param size: max number of jobs [default=10]
        :param page: page of jobs [default=0]
        :return: List of jobs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        if operation.authorize is True:
            self.check_authorization('task', 'Manager', '*', 'view')
        self.logger.warn(size)
        jobs, count = self.manager.get_paginated_jobs(job=job, account_id=account, size=size, page=page, name=name,
                                                      with_perm_tag=False)
        redis_manager = self.redis_taskmanager
        res = []
        for j in jobs:
            try:
                task = redis_manager.get(task_manager.conf.CELERY_REDIS_RESULT_KEY_PREFIX + j.job)
                task = json.loads(task)
            except:
                task = {}
            jobstatus = task.get('status', None)
            children = task.get('children', [])
            if children is None:
                children = []
            children_jobs = task.get('jobs', [])
            if children_jobs is None:
                children_jobs = []
            if status is None or status == jobstatus:
                start_time = format_date(j.creation_date)
                stop_time = task.get('stop_time', None)
                if stop_time is not None:
                    stop_time = format_date(datetime.fromtimestamp(stop_time))
                res.append({
                    'id': j.job,
                    'name': j.name,
                    'account': j.account_id,
                    'params': json.loads(j.params),
                    'start_time': start_time,
                    'stop_time': stop_time,
                    'status': jobstatus,
                    'worker': task.get('worker', None),
                    # 'tasks': len(children),
                    # 'jobs': len(children_jobs),
                    'elapsed': task.get('stop_time', 0) - task.get('start_time', 0)
                })

        return res, count

    @trace(entity='ApiServiceJob', op='view')
    def get_service_job_by_task_id(self, task_id):
        """Update status of service_job api instance.

        :param task_id: task id
        :return: ApiServiceJob
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_js = self.manager.get_service_job_by_task_id(task_id)
        return ServiceUtil.instanceApi(self, ApiServiceJob, srv_js)

    @trace(entity='ApiServiceJob', op='view')
    def get_service_job(self, oid):
        """Get single service_job api instance.

        :param oid: entity model id, uuid
        :return: ApiServiceJob
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_js = self.get_entity(ApiServiceJob, ServiceJob, oid)
        return srv_js

    @trace(entity='ApiServiceJob', op='view')
    def get_jobs(self, *args, **kvargs):
        """Get service jobs.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceJobs
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceJobs(*args, **kvargs):
            entities, total = self.manager.get_paginated_jobs(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        #self.verify_permisssions('use')
        res, total = self.get_paginated_entities(ApiServiceJob, recuperaServiceJobs,
                                                 customize=customize, *args, **kvargs)
        return res, total

    def get_task_intervals(self, execution_date=None, metric_num=None, task=None, *args, **kvargs):
        tasks = self.manager.get_task_intervals(execution_date=execution_date,
                                                metric_num=metric_num, task=task, *args, **kvargs)
        return tasks

    ##################################
    ###  AccountServiceDefinition  ###
    ##################################
    @trace(entity='ApiAccountServiceDefinition', op='view')
    def get_account_service_defintion(self, oid: Union[int, str], for_update=False) -> ApiAccountServiceDefinition:
        """Get single ApiAccountServiceDefinition  api instance.

        :param oid: entity model id, uuid
        :return: ApiAccountServiceDefinition
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        adef: ApiAccountServiceDefinition = self.get_entity(ApiAccountServiceDefinition, AccountServiceDefinition, oid, for_update=for_update)
        return adef

    @trace(entity='ApiAccountServiceDefinition', op='view')
    def get_account_service_defintions(self, *args, **kvargs) -> Tuple[List[ApiAccountServiceDefinition], int]:
        """Get ServiceJobSchedule.

        :param int account_id: account id
        :param bool only_container:
        :param str category:
        :param str plugintype:
        :param int service_definition_id: serivce definition id
        :param int active: 0|1
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ApiAccountServiceDefinition
        :raises ApiManagerError: if query empty return error.
        """
        def get_asd(*args, **kvargs):
            entities, total = self.manager.get_paginated_account_service_definitions(*args, **kvargs)
            return entities, total

        res, total = self.get_paginated_entities(ApiAccountServiceDefinition, get_asd, *args, **kvargs)
        return res, total

    @trace(entity='ApiAccountServiceDefinition', op='view')
    def get_account_catalog(self, *args, **kvargs) -> Tuple[List[dict], int]:
        """Get service definitions as catalogo.
        this method is a raplacement of get_catalog_service_definitions
        Get service definitions relative to visible catalog

        :param int account_id: account id
        :param bool only_container:
        :param str category:
        :param str plugintype:
        :param int service_definition_id: serivce definition id
        :param int active: 0|1
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of dictinary
        {
            id: int,
            uuid: str,
            name:str,
            descripton: str
            features{
                k:v
            }
            config
        }
        :raises ApiManagerError: if query empty return error.
        """

        kvargs['authorize'] = False
        res, total = self.get_account_service_defintions(*args, **kvargs)

        res_type_set:List[dict] = []
        for af in res :
            r = af.service_definition
            res_type_item = {}
            res_type_item['id'] = r.oid
            res_type_item['uuid'] = r.uuid
            res_type_item['name'] = r.name
            res_type_item['description'] = r.desc

            features = []
            if r.desc is not None:
                features = r.desc.split(' ')

            feature = {}
            for f in features:
                try:
                    k, v = f.split(':')
                    feature[k] = v
                except ValueError:
                    pass
            res_type_item['features'] = feature
            res_type_set.append(res_type_item)

        if total == 1:
            res_type_set[0]['config'] = res[0].service_definition.get_main_config().params

        return res_type_set, total

    @trace(entity='ApiAccountServiceDefinition', op='insert')
    def add_account_service_definition(self, account_id: int, service_definition_id: int, name: str = None,
                                       account: ApiAccount = None, servicedefinition: ApiServiceDefinition = None):
        """Create a new Account Service Definition from account an Service Definition the objid is created using the
        account as parent and the service definition service_categoty propoerty the service category is a property
        inherited from the so that
        """
        srvdfs, tot = self.get_account_service_defintions(account_id=account_id,
                                                          service_definition_id=service_definition_id,
                                                          authorize=False)
        if tot > 0:
            raise ApiManagerError(f'Service definition {service_definition_id} already exists for Account {account_id}')

        # check authorization
        objid = f'{account.objid}//{servicedefinition.service_category}'
        self.logger.debug(f'check_authorization for "{ApiAccountServiceDefinition.objtype}", '
                          f'"{ApiAccountServiceDefinition.objdef}", "insert"')
        self.check_authorization(ApiAccountServiceDefinition.objtype,
                                 ApiAccountServiceDefinition.objdef, objid, 'insert')

        try:
            # create organization reference
            if account is None:
                account = self.get_account(account_id)
            if account is None:
                raise ApiManagerError(f'Account {account_id} does not exists')

            if servicedefinition is None:
                servicedefinition = self.get_service_def(service_definition_id)
            if servicedefinition is None:
                raise ApiManagerError(f'Service definition {service_definition_id} does not exists')

            objid = id_gen(parent_id=f'{account.objid}//{servicedefinition.service_category}')
            accsrvdef = AccountServiceDefinition(objid, account_id, service_definition_id)

            res = self.manager.add(accsrvdef)

            # create object and permission
            if name is None:
                name = res.desc
            ApiAccountServiceDefinition(self, oid=res.id, objid=res.objid, name=res.name, active=res.active,
                                        desc=res.desc, model=res).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ############################
    ###  ServiceJobSchedule  ###
    ############################
    @trace(entity='ApiServiceJobSchedule', op='view')
    def get_service_job_schedule(self, oid: Union[int, str], for_update:bool=False):
        """Get single service_job_schedule api instance.

        :param oid: entity model id, uuid
        :return: ApiServiceJobSchedule
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_js: ApiServiceJobSchedule = self.get_entity(ApiServiceJobSchedule, ServiceJobSchedule, oid, for_update=for_update)
        return srv_js

    @trace(entity='ApiServiceJobSchedule', op='view')
    def get_service_job_schedules(self, *args, **kvargs):
        """Get ServiceJobSchedule.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceJobSchedule
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceJobSchedules(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_job_schedules(*args, **kvargs)
            return entities, total

        res, total = self.get_paginated_entities(ApiServiceJobSchedule, recuperaServiceJobSchedules, *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceJobSchedule', op='insert')
    def add_service_job_schedule(self, name, job_name, schedule_type, desc='', job_options={},
                                 schedule_params={}, retry=False, retry_policy={},
                                 relative=False, job_args=[], job_kvargs={}):
        """ """
        js, tot = self.get_service_job_schedules(name=name, filter_expired=False, authorize=False)
        if tot > 0:
            raise ApiManagerError('Service job schedule %s already exists' % name)

        # check authorization
        self.check_authorization(ApiServiceJobSchedule.objtype, ApiServiceJobSchedule.objdef, None, 'insert')

        try:
            # create organization reference
            objid = id_gen()
            srv_js = ServiceJobSchedule(objid, name, job_name, schedule_type, desc, job_options, relative,
                                        schedule_params, retry, retry_policy, job_args, job_kvargs)

            res = self.manager.add(srv_js)

            # create object and permission
            ApiServiceJobSchedule(self, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ############################
    ###   ServicePriceList   ###
    ############################
    def get_service_price_list_by_account(self, account_id, period_date):
        """
        :param account_id: entity account id
        :return: ServicePriceList
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        listino = self.manager.get_account_prices(account_id, period_date)
        price_list_id = None
        if listino is not None:
            self.logger.debug('account %s con listino = %s' % (account_id, listino))
            price_list_id = listino.price_list_id
        else:
            account = self.manager.get_account_by_pk(account_id)
            if account is not None:
                listino = self.manager.get_divs_prices(account.division_id, period_date)
                if listino is not None:
                    self.logger.debug('account %s con listino = %s da division %s' %
                                      (account_id, listino, account.division_id))
                    price_list_id = listino.price_list_id
                else:
                    raise ApiManagerWarning('Price List not found for Account %s and Division %s' %
                                            (account_id, account.division_id))
            else:
                raise ApiManagerWarning('Account not found id=%s' % account_id)
        return price_list_id

    @trace(entity='ApiServicePriceList', op='view')
    def get_service_price_list(self, oid, for_update=False):
        """Get single service_price_list.

        :param oid: entity model id, uuid
        :return: ServicePriceList
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_pl = self.get_entity(ApiServicePriceList, ServicePriceList, oid, for_update=for_update)
        return srv_pl

    @trace(entity='ApiServicePriceList', op='view')
    def get_service_price_list_default(self):
        """Get single service_price_list default instance.

        :return: ServicePriceList
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_pl = self.manager.get_service_price_lists(flag_default=True)
        if len(srv_pl) != 1:
            raise ApiManagerWarning('Found %s default Service Price List' % len(srv_pl))

        return ServiceUtil.instanceApi(self, ApiServicePriceList, srv_pl[0])

    @trace(entity='ApiServicePriceList', op='view')
    def get_service_price_lists(self, *args, **kvargs):
        """Get ServicePriceList.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServicePriceList
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServicePriceLists(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_price_lists(*args, **kvargs)
            return entities, total

        res, total = self.get_paginated_entities(ApiServicePriceList, recuperaServicePriceLists, *args, **kvargs)
        return res, total

    @trace(entity='ApiServicePriceList', op='insert')
    def add_service_price_list(self, name='', desc=None, flag_default=False, active=True):
        """ """
        pl, tot = self.get_service_price_lists(name=name, filter_expired=False, authorize=False)
        if tot > 0:
            raise ApiManagerError('Service price list %s already exists' % name)

        if flag_default is True:
            srv_pl = self.manager.get_service_price_lists(flag_default=True)
            if len(srv_pl) == 1:
                raise ApiManagerError('Service price list default already exists')

        # check authorization
        self.check_authorization(ApiServicePriceList.objtype, ApiServicePriceList.objdef, None, 'insert')

        try:
            # create organization reference
            objid = id_gen()
            srv_pl = ServicePriceList(objid, name, flag_default, desc, active=active)

            res = self.manager.add(srv_pl)

            # create object and permission
            ApiServicePriceList(self, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ############################
    ###  ServicePriceMetric  ###
    ############################
    @trace(entity='ApiServicePriceMetric', op='view')
    def get_service_price_metric(self, oid):
        """Get single service_price_metric.

        :param oid: entity model id, uuid
        :return: ServicePriceMetric
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_pl = self.get_entity(ApiServicePriceMetric, ServicePriceMetric, oid)
        self.logger.debug("get_service_price_metric returng %s" % srv_pl.__class__ )
        return srv_pl

    @trace(entity='ApiServicePriceMetric', op='view')
    def get_service_price_metrics(self, *args, **kvargs):
        """Get ServicePriceMetric.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServicePriceMetric
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServicePriceMetrics(*args, **kvargs):
            srv_price_list = self.get_service_price_list(kvargs.pop('price_list_id'))
            entities, total = self.manager.get_paginated_service_price_metrics(price_list_id=srv_price_list.oid, *args, **kvargs)

            return entities, total

        def customize(entities, *args, **kvargs):
            pricelists = self.manager.get_service_price_lists()
            pricelist_idx = {p.id: p for p in pricelists}
            metrictypes = self.manager.get_service_metric_types()
            metrictype_idx = {m.id: m for m in metrictypes}
            for entity in entities:
                entity.metric_type = metrictype_idx.get(entity.model.metric_type_id, None)
                entity.price_list = pricelist_idx.get(entity.model.price_list_id, None)

            return entities

        res, total = self.get_paginated_entities(ApiServicePriceMetric, recuperaServicePriceMetrics,
                                                 customize=customize, *args, **kvargs)
        return res, total

    @trace(entity='ApiServicePriceMetric', op='insert')
    def add_service_price_metric(self, name, price, time_unit, metric_type_id, price_list_id, price_type='SIMPLE',thresholds=None, desc='', active=True):
        """Add service price metric

        :param name: name
        :param price: the price
        :param time_unit: YEAR DAY
        :param metric_type_id: the service metric
        :param price_list_id: oid of the price list
        :param desc: description
        :param price_type: default SIMPLE the price metric type
        :param threshols: optinale default None an array of dictionary describing the thresholds default SIMPLE the price metric type
        :param active: the status
        :return:
        """
        price_list = self.get_service_price_list(oid=price_list_id)
        metric_type = self.get_service_metric_type(metric_type_id)

        # check authorization
        self.check_authorization(ApiServicePriceMetric.objtype, ApiServicePriceMetric.objdef,
                                 price_list.objid, 'insert')
        try:
            # create organization reference
            objid = '%s//%s' % (price_list.objid, id_gen())

            srv_pl = ServicePriceMetric(objid=objid, name=name, price=price,
                    time_unit=time_unit, price_type=price_type,
                    metric_type_id=metric_type.oid,
                    price_list_id=price_list.oid,
                    desc=desc, active=active)

            res = self.manager.add(srv_pl)

            # create object and permission
            ApiServicePriceMetric(self, oid=res.id).register_object([objid], desc=name)
            if thresholds:
                for theshold in thresholds:
                    thr_pl = ServicePriceMetricThresholds(
                    from_ammount=theshold.get("ammount_from", 0),
                    till_ammount=theshold.get("ammount_till", None),
                    service_price_metric_id=res.id,
                    price=theshold.get("price", 0.0)
                    )
                    self.manager.add(thr_pl)



            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)



    ############################
    ###    ServiceMetric     ###
    ############################
    def get_service_metric(self, oid):
        """Get single service_metric.

        :param oid: entity model id, uuid
        :return: ServiceMetric
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_m = self.manager.get_service_metric(oid)
        return srv_m

    def get_service_metrics(self, metric_type=None, *args, **kvargs):
        """Get ServiceMetric.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceMetric
        :raises ApiManagerError: if query empty return error.
        """

        metric_type_id = None
        if metric_type_id is not None:
            metric_types = self.manager.get_service_metric_types(name=metric_type)
            if len(metric_types)>0:
                metric_type_id = metric_types[0].id

        self.resolve_fk_id('service_instance_id', self.get_service_instance, kvargs)

        res, total = self.manager.get_paginated_service_metrics(
                    metric_type_id=metric_type_id,
                    with_perm_tag=False, *args, **kvargs)

        return res, total

    def add_service_metric(self, value, metric_type_id, metric_num,
                 service_instance_oid, job_id, creation_date):
        """ """
        try:
            # Instance_id
            instance = self.get_service_instance(oid=service_instance_oid)
            if instance is not None:
                instance_id = instance.oid
            else:
                raise ApiManagerWarning('Instance not found: %s' %service_instance_oid)

            # check authorization
            self.check_authorization(ApiServiceInstance.objtype,
                                     ApiServiceInstance.objdef,
                                     instance.objid, 'update')

            srv_m = ServiceMetric(value=value,
                                  metric_type_id=metric_type_id,
                                  metric_num=metric_num,
                                  service_instance_id=instance_id,
                                  job_id=job_id,
                                  creation_date=creation_date)
            self.logger.warn('Metric=%s' %srv_m)
            res = self.manager.add(srv_m)

            # create object and permission
            # ApiServiceMetric(self, oid=res.id).register_object([objid], desc=name)

            return res.id
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def delete_service_metric(self, metric_oid=None, service_instance_oid=None,
                              metric_type_id=None, metric_num=None, job_id=None,
                              start_date=None, end_date=None):
        """ """
        res = None
        try:
            if metric_oid is not None:
                metric = self.get_service_metric(metric_oid)

                # Instance_id
                instance = self.get_service_instance(oid=service_instance_oid)
                # check authorization
                self.check_authorization(ApiServiceInstance.objtype,
                                     ApiServiceInstance.objdef,
                                     ApiServiceInstance.objdef,
                                     instance.objid, 'update')

                res = self.manager.delete(metric)
            else:
                # Instance_id
                instance_id = None
                instance = self.get_service_instance(oid=service_instance_oid)
                if instance is not None:
                    instance_id = instance.oid
                else:
                    raise ApiManagerWarning('No permission for: %s' %service_instance_oid)

                # check authorization
                self.check_authorization(ApiServiceInstance.objtype,
                                     ApiServiceInstance.objdef,
                                     instance.objid, 'update')

                res = self.manager.delete_service_metric(metric_type_id=metric_type_id,
                                      metric_num=metric_num,
                                      service_instance_id=instance_id,
                                      job_id=job_id,
                                      start_date=start_date,
                                      end_date=end_date)

                self.logger.warn('Metric=%s' %res)

            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def get_service_instantconsume(self, oid: Union[int, str], request_date, *args, **kvargs):
        """Get service instance consume.

        :param oid: account id or uuid
        :param request_date: request date of istant consume
        :return: array of instant consume from account id
        :raises ApiManagerError: if query empty return error.
        """
        # check account entity oid and permission
        account = self.get_entity(ApiAccount, Account, oid)

        resp = {
            'account_id': account.oid,
            'request_date': request_date,
            'metrics': []
        }

        fields = ['container_id', 'metric_type_name', 'group_name', 'value', 'extraction_date']
        qresp = self.manager.get_instant_consumes(oid)
        for r in qresp:
            metrics = dict(zip(fields, list(r)))
            metrics.update({'extraction_date': format_date(metrics.get('extraction_date'))})
            resp.get('metrics').append(metrics)

        return resp

    ############################
    ###  ServiceMetricType   ###
    ############################
    @trace(entity='ApiServiceMetricType', op='view')
    def get_service_metric_type(self, oid):
        """Get single service_metric_type.

        :param oid: entity model id, name
        :return: ServiceMetricType
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_mt = self.get_entity(ApiServiceMetricType, ServiceMetricType, oid)
        return srv_mt

    def get_service_metric_types(self, *args, **kvargs):
        """Get list of ServiceMetricType.

        :param name: name like [optional]
        :return: List of ServiceMetricType
        :raises ApiManagerError: if query empty return error.
        """
        entities = self.manager.get_service_metric_types(*args, **kvargs)
        return entities

    def get_paginated_service_metric_type(self, *args, **kvargs):
        """Get list of ServiceMetricType.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceMetricType
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceMetricType(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_metric_type(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        res, total = self.get_paginated_entities(ApiServiceMetricType, recuperaServiceMetricType,
                                                 customize=customize, *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceMetricType', op='insert')
    def add_service_metric_type(self, name, metric_type, group_name, desc, measure_unit, limits=None, status=SrvStatusType.DRAFT):
        """ """
        if limits is None:
            limits = []
        # check authorization
        self.check_authorization(ApiServiceMetricType.objtype, ApiServiceMetricType.objdef, None, 'insert')
        try:
            # create objid reference
            objid = id_gen()
            self.logger.warning('%s' % objid)

            mt = ServiceMetricType(objid, name, metric_type, group_name=group_name, desc=desc, measure_unit=measure_unit, status=status)
            self.logger.warning('mt=%s' % mt)
            res = self.add_service_metric_type_base(mt)

            for item in limits:
                self.add_service_metric_type_limit(res.id, item)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    # @transaction
    def add_service_metric_type_base(self, smt):
        """ """
        try:
            # create objid reference
            mts = self.get_service_metric_types(for_update=True)
            for item in mts:
                if item.name == smt.name:
                    return item

            res = self.manager.add(smt)
            ApiServiceMetricType(self, oid=res.id).register_object([res.objid], desc=res.name)
            self.logger.debug('Add service metric type: %s' % res)
            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @transaction
    def add_metric_type_plugin_type(self, plugin_type_id, metric_type_id):
        """ """
        try:
            # create objid reference
            mts = self.manager.get_metric_type_plugin_types(plugin_type_id=plugin_type_id, for_update = True)
            for item in mts:
                if item.plugin_type_id == plugin_type_id and item.metric_type_id == metric_type_id:
                    return item

            mtp = MetricTypePluginType(plugin_type_id, metric_type_id)
            res = self.manager.add(mtp)
            self.logger.info('added_____%s' %mtp)
            return res

        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def search_data_metric_type_limit_to_delete(self, mtl, limits):
        mtl_to_delete = []
        found = False

        for r in mtl:
            found = False
            for i in limits:
                if str(r.metric_type_id) == i.get('metric_type_id'):
                    found = True
                    break
            if found == False:
                mtl_to_delete.append(r.id)

        return mtl_to_delete

    @trace(entity='ApiServiceMetricType', op='update')
    @transaction
    def update_service_metric_type(self, oid, data, *args, **kvargs):
        """ """
        srv_mt = self.get_service_metric_type(oid)
        srv_mtl = srv_mt.model.limits

        # check authorization
        self.check_authorization(ApiServiceMetricType.objtype,
                                 ApiServiceMetricType.objdef,
                                 srv_mt.objid, 'update')

        try:
            if srv_mt.status == SrvStatusType.ACTIVE:
                raise ApiManagerWarning('service metric type %s is %s can not be updated' % (srv_mt.oid, srv_mt.status))

            data = data.get('metric_type')
            limits = data.pop('limits', [])

            # se presente in tabella e non in request cancello
            if len(srv_mtl) > 0 and len(limits) > 0:
                limits_to_delete = self.search_data_metric_type_limit_to_delete(srv_mtl, limits)
                for i in limits_to_delete:
                    self.manager.delete_service_metric_type_limits(id=i)

            for item in limits:
                self.logger.warning('item=%s' % item)
                mtl = self.manager.get_service_metric_type_limit(
                                    parent_id=srv_mt.oid, metric_type_id=item.get('metric_type_id'))
                # se non presente in tabella inserisco
                if mtl is None:
                    self.add_service_metric_type_limit(srv_mt.oid, item)
                # se  presente in tabella e in post aggiorno
                else:
                    mtl.name = item.get('name')
                    mtl.value = item.get('value')
                    mtl.desc = item.get('desc')
                    self.manager.update(mtl)

            return srv_mt.update(**data)

        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiServiceMetricType', op='delete')
    @transaction
    def delete_service_metric_type(self, oid):
        """ """
        res = None
        try:
            srv_mt = self.get_service_metric_type(oid)

            if srv_mt.status == SrvStatusType.ACTIVE:
                res = srv_mt.delete(soft=True)
            else:
                # TBD: da verificare funzionamento hard delete
                # res= srv_mt.delete(soft=False)
                # check authorization
                self.check_authorization(ApiServiceMetricType.objtype,
                                         ApiServiceMetricType.objdef,
                                         srv_mt.objid, 'delete')

                res = self.manager.delete_service_metric_type_limits(parent_id=srv_mt.oid)
                res = self.manager.delete_service_metric_type(id=srv_mt.oid)

                self.deregister_object(srv_mt.objid.split('//'))

            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiServiceMetricType', op='update')
    @transaction
    def add_service_metric_type_limit(self, parent_id, item, *args, **kvargs):

        parent_mt = self.get_service_metric_type(parent_id)
        fk_mt = self.get_service_metric_type(item.get('metric_type_id'))
        if fk_mt.metric_type != MetricType.CONSUME.name :
            raise ApiManagerWarning('check limit parameters: it is referered a wrong metric type %s %s' %
                                    (fk_mt.oid, fk_mt.metric_type))

        new_mtl = ServiceMetricTypeLimit(name=item.get('name'), parent_id=parent_mt.oid, metric_type_id=fk_mt.oid,
                                         value=item.get('value'), desc=item.get('desc', ''))

        self.manager.add(new_mtl)
        return new_mtl

    # def get_service_metric_consume_view(self, oid):
    #     """Get single service_metric_consume from view.
    #
    #     :param oid: entity model id, uuid
    #     :return: ServiceMetricConsumeView
    #     :raises ApiManagerError: raise :class:`ApiManagerError`
    #     """
    #     cv = self.manager.get_entity(ServiceMetricConsumeView, oid)
    #     return cv

    # def get_paginated_metric_consume_views(self, *args, **kvargs):
    #     """Get ServiceMetricConsumeView.
    #
    #     :param metric_type: metric type [optional]
    #     :param metric_num: metric ordinal number [optional]
    #     :param service_metric_id: metric id [optional]
    #     :param instance_id: instance id [optional]
    #     :param account_id: account id [optional]
    #     :param evaluation_date_start: date start [optional]
    #     :param evaluation_date_end: date end like [optional]
    #
    #     :param name: name like [optional]
    #     :param page: users list page to show [default=0]
    #     :param size: number of users to show in list per page [default=0]
    #     :param order: sort order [default=DESC]
    #     :param field: sort field [default=id]
    #     :return: List of ServiceMetricConsumeView
    #     :raises ApiManagerError: if query empty return error.
    #     """
    #     self.resolve_fk_id('instance_parent_id', self.get_service_instance, kvargs, 'instance_parent_id')
    #     self.resolve_fk_id('instance_id', self.get_service_instance, kvargs, 'service_instance_id')
    #     self.resolve_fk_id('account_id', self.get_account, kvargs, 'account_id')
    #     entities, total = self.manager.get_paginated_metric_consume_views(*args, **kvargs)
    #     return entities, total

    ############################
    ### ServiceAggregateCost ###
    ############################
    def get_aggregate_cost(self, oid):
        """Get single AggregateCost entity

        :param oid: entity model id, uuid
        :return: AggregateCost
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        ac = self.manager.get_entity(AggregateCost, oid)
        return ac

    def get_paginated_aggregate_costs(self, *args, **kvargs):
        """Get aggregate cost list.

        :param aggregation_type: aggregation type [optional]
        :param metric_type: metric type [optional]
        :param instance_oid: instance id [optional]
        :param date_start: date start [optional]
        :param date_end: date end [optional]
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of AggregationCost
        :raises ApiManagerError: if query empty return error.
        """
        self.resolve_fk_id('instance_oid', self.get_service_instance, kvargs, 'service_instance_id')
        self.resolve_fk_id('account_oid', self.get_account, kvargs, 'account_id')

        entities, total = self.manager.get_paginated_aggregate_costs(*args, **kvargs)
        return entities, total

    @transaction
    def add_aggregate_cost(self, metric_type_id=None, consumed=0, cost=0, service_instance_oid=None, account_oid=None,
                           aggregation_type='', period='', cost_type_id=None, evaluation_date=None, job_id=None):
        """Add aggregate cost

        :param metric_type_id:
        :param consumed:
        :param cost:
        :param service_instance_oid:
        :param account_oid:
        :param aggregation_type:
        :param period:
        :param cost_type_id:
        :param evaluation_date:
        :param job_id:
        :return:
        """
        instance = self.get_service_instance(service_instance_oid)

        # check authorization
        self.check_authorization(ApiServiceInstance.objtype, ApiServiceInstance.objdef, instance.objid, 'use')
        try:
            # resolve uuid in id
            service_instance_id = instance.oid

            account_id = None
            if account_oid is not None:
                acc = {'account_oid': account_oid}
                self.resolve_fk_id('account_oid', self.get_account, acc, 'account_id')
                account_id = acc.get('account_id', None)

            cost = AggregateCost(metric_type_id, consumed, cost, service_instance_id, account_id, aggregation_type,
                                 period, cost_type_id, evaluation_date, job_id)
            res = self.manager.add(cost)

            return res.id
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @transaction
    def add_all_aggregate_costs(self, aggregate_costs, instance):
        """ """

        # check authorization
        # self.check_authorization(ApiServiceInstance.objtype,
        #                          ApiServiceInstance.objdef,
        #                          instance.objid, 'use')
        try:
            return self.manager.add_all(aggregate_costs)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @transaction
    def delete_batch_aggregate_cost(self, *args, **kvargs):

        return self.manager.delete_batch_aggregate_cost(*args, **kvargs)

    ############################
    ###    ServiceType       ###
    ############################
    @trace(entity='ApiServiceType', op='plugintype.view')
    def get_service_plugin_type(self, authorize=True, *args, **kvargs):
        """Get service plugin type.

        :param plugintype : plugin type name
        :param objclass : plugin package class
        :param category : category plugin CONTAINER | INSTANCE  [optional]
        :return: array of ServicePluginType
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        # check authorization
        if authorize == True:
            self.check_authorization(ApiServiceType.objtype, ApiServiceType.objdef, '*', 'view')

        items = self.manager.get_service_plugin_type(*args, **kvargs)
        res = []
        for item in items:
            res.append({'id': item.id,
                        'name': item.name_type,
                        'objclass': item.objclass})

        return res

    @trace(entity='ApiServiceType', op='view')
    def get_service_type(self, oid):
        """Get single service_type.

        :param oid: entity model id, uuid
        :return: ServiceType
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srvType = self.get_entity(ApiServiceType, ServiceType, oid)
        return srvType

    @trace(entity='ApiServiceType', op='view')
    def get_service_types(self, *args, **kvargs):
        """Get ServiceType.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceType
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceTypes(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_types(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        res, total = self.get_paginated_entities(ApiServiceType, recuperaServiceTypes,
                                                 customize=customize, *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceType', op='insert')
    def add_service_type(self, template_cfg, name='', desc=None, objclass='object', flag_container=False,
                         active=True, status=SrvStatusType.DRAFT, version='1.0'):
        """ """
        # check already exixst
        cats = self.manager.get_service_types(name=name, filter_expired=False)
        if len(cats) > 0:
            self.logger.error('Service type %salready exists' % name, exc_info=True)
            raise ApiManagerError('Service type %s already exists' % name, code=409)

        # check authorization
        self.check_authorization(ApiServiceType.objtype, ApiServiceType.objdef, None, 'insert')
        try:
            # create organization reference
            objid = id_gen()

            srv_type = ServiceType(objid, name, desc, objclass, flag_container, active=active,
                                   template_cfg=template_cfg, status=status, version=version)

            res = self.manager.add(srv_type)
            # create object and permission
            ApiServiceType(self, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ################################
    ###    ServiceType Plugin    ###
    ################################
    def check_service_type_plugin_parent_service(self, account_id, plugintype)-> Tuple[ApiAccount,Any]:
        """Check if parent service type exists, status is active and you have update permission

        :param account_id: account uuid or name
        :param plugintype: plugintype
        :return: ServiceType Plugin
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check Account oid
        account = self.get_account(account_id)

        # check if the account is associated to a CS
        insts, total = self.get_service_type_plugins(account_id=account.oid, plugintype=plugintype)
        if total == 0:
            raise ApiManagerWarning('Account %s has not %s' % (account.oid, plugintype))

        plugin = insts[0]

        if plugin.is_active() is False:
            raise ApiManagerWarning('Account %s %s is not in a correct status' % (account_id, plugintype))

        # checks authorization user on container service instance
        if plugin.instance.verify_permisssions('update') is False:
            raise ApiManagerWarning('User does not have the required permissions to make this action')

        return account, plugin

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_type_plugin(self, instance, plugin_class:APIPLUGIN=None, details=True)-> APIPLUGIN:
        """Get single service type plugin from service instance.

        :param instance: service instance id, uuid or name
        :param plugin_class: service type plugin class you need associated to service instance [optional]
        :param details: if True call custom method post_get() [default=True]
        :return: ServiceType Plugin
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv = self.get_entity(ApiServiceInstance, ServiceInstance, instance, details=details)
        srv.get_main_config()
        plugin = srv.get_service_type_plugin()
        if plugin_class is not None and isinstance(plugin, plugin_class) is False:
            raise ApiManagerError('%s %s does not exist' % (plugin_class.plugintype, instance))

        plugin.instance.account = self.get_account(plugin.instance.account_id)
        plugin.definition_name = self.get_service_def(plugin.instance.service_definition_id).name

        if details is True:
            plugin.post_get()

        self.logger.debug('Get service type plugin from instance %s: %s' % (instance, plugin))
        return plugin

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_type_plugins(self, *args, **kvargs) -> Tuple[List[Any], int]:
        """Get service type plugins related to queried service instances.

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :param version: service version
        :param account_id: id account [optional]
        :param service_definition_id: id service definition [optional]
        :param status: instance status name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param plugintype: plugin type name [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param flag_container: if True show only container instances [optional]
        :param period_val_start: [optional]
        :param period_val_stop: [optional]
        :param service_name_list: list of services instances name [optional]
        :param service_uuid_list: list of services instances uuid [optional]
        :param service_id_list: list of services instances id [optional]
        :param account_id_list: list of accounts id related to services instances [optional]
        :param service_definition_id_list: list of service definitions id related to services instances [optional]
        :param resource_uuid_list: list of resources uuid related to services instances [optional]
        :param service_status_name_list: list of status names related to services instances [optional]
        :param servicetags_and: list of service tags. Search exactly the list of tags.  [optional]
        :param servicetags_or: list of service tags. Search in the tag list. [optional]
        :param details: if True and plugintype is not None exec custom staticmethod customize_list() [default=True]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of service type plugin instance
        :raises ApiManagerError: if query empty return error.
        """
        res = []
        objs = []
        tags = []

        if operation.authorize is True:
            # verify permissions
            objs = self.can('view', ApiServiceInstance.objtype, definition=ApiServiceInstance.objdef)
            objs = objs.get(ApiServiceInstance.objdef.lower())

            # create permission tags
            for p in objs:
                tags.append(self.manager.hash_from_permission(ApiServiceInstance.objdef, p))
            self.logger.debug('Permission tags to apply: %s' % tags)
        else:
            kvargs['with_perm_tag'] = False
            self.logger.debug('Authorization disabled for command')

        self.resolve_fk_id('account_id', self.get_account, kvargs)
        self.resolve_fk_id('service_definition_id', self.get_service_def, kvargs)
        self.resolve_fk_id('parent_id', self.get_service_instance, kvargs)
        kvargs['filter_expired'] = False

        # find id from uuid
        account_id_list = kvargs.get('account_id_list', None)
        accounts: List[ApiAccount] = []
        if account_id_list is not None:
            for account_id in account_id_list:
                accounts.append(self.get_account(account_id).oid)
            kvargs['account_id_list'] = accounts

        try:
            insts: List[ServiceTypePluginInstance]
            total_insts: int
            insts, total_insts = self.manager.get_paginated_service_type_plugins(tags=tags, *args, **kvargs)
            inst_class = None

            # get indexes
            inst_oids: List[int] = []
            type_ids: List[int] = []
            for inst in insts:
                inst_oids.append(inst.id)
                if inst.type_id not in type_ids:
                    type_ids.append(inst.type_id)

            type_idx = {}
            config_idx = {}
            account_idx = {}

            if len(inst_oids) > 0:
                types: List[ServiceType]
                types, total = self.manager.get_paginated_service_types(type_ids=type_ids, with_perm_tag=False, size=-1)
                type_idx = {c.id: c for c in types}

                config_idx = self.get_service_instance_config_idx(service_instance_ids=inst_oids,
                                                                  index_key='service_instance_id')
                account_idx = self.get_account_idx()

            for inst in insts:
                inst_class = import_class(inst.objclass)
                if inst_class is None:
                    self.logger.error('get_service_type_plugins - fail import objclass %s ' % (inst.objclass))
                    continue

                inst_type = type_idx.get(inst.type_id)

                obj = inst_class(self, oid=inst_type.id, objid=inst_type.objid, name=inst_type.name,
                                 active=inst_type.active, desc=inst_type.desc, model=inst_type)

                inst_obj = ApiServiceInstance(self, oid=inst.id, objid=inst.objid, name=inst.name,
                                              active=inst.active, desc=inst.desc, model=inst)
                obj.instance = inst_obj
                inst_obj.config_object = config_idx.get(str(inst.id))
                res.append(obj)

                inst_obj.account = account_idx.get(str(inst.account_id))
                obj.definition_name = inst.definition_name

            # if only one plugin type is selected exec customize list
            if kvargs.get('plugintype', None) is not None and kvargs.get('details', True) is True \
                    and inst_class is not None:
                inst_class.customize_list(self, res, *args,  **kvargs)
            if inst_class is not None:
                self.logger.info('Get %s (total:%s): %s' % (inst_class.__name__, total_insts, truncate(str(res))))
            return res, total_insts
        except QueryError as ex:
            self.logger.warning(ex, exc_info=True)
            return [], 0

    @trace(entity='ApiServiceInstance', op='insert')
    def add_service_type_plugin(self, service_definition_id, account_id, name=None, desc=None, parent_plugin=None,
                                instance_config=None, account: ApiAccount=None, status=None, resource_uuid=None, *args, **kvargs):
        """Factory used to create new service instance using the related service type plugin

        :param service_definition_id: service definition identifier
        :param account_id: account identifier
        :param parent_plugin: parent plugin instance
        :param name: instance name [optional]
        :param desc: instance description [optional]
        :param instance_config: service instance configurations [optional]
        :param account: Account if available beehive_service.controller.ApiAccount [optional]
        :param status: service instance status [optional]
        :param resource_uuid: uuid of associated resource [optional]
        :param kvargs.sync: if True run sync task, if False run async task
        :return: {'taskid': .., 'uuid': ..}
        :raises ApiManagerWarning: if instance cannot to be created.
        """
        if instance_config is None:
            instance_config = {}
        # get definition
        service_definition = self.get_service_def(service_definition_id)
        if service_definition.is_active() is False:
            raise ApiManagerWarning('Service definition %s is not in ACTIVE state' % service_definition.uuid)

        # get account
        if account is None:
            account = self.get_account(account_id)
        # if account.is_active() is False:
        #     raise ApiManagerWarning('Account %s is not in ACTIVE state' % account.uuid)
        check, reason = account.can_instantiate(definition=service_definition)
        if not check:
            raise ApiManagerError(
                reason + f': Account {account.name} ({account.uuid}) definition {service_definition.name}')

        # get name
        if name is None:
            name = service_definition.name + '-inst'

        # get desc
        if desc is None:
            desc = name

        # check name length
        if len(name) > 40:
            raise ApiManagerError('Service name is too long. Maxsize is 40')

        inst = None
        try:
            def_config = service_definition.get_main_config().params
            def_config.update(instance_config)

            # create service instance
            inst = self.add_service_instance(name=name, desc=desc, service_def_id=service_definition.oid,
                                             status=SrvStatusType.DRAFT, account=account, bpmn_process_id=None,
                                             active=True, version='1.0')

            # create service instance config
            self.add_service_instance_cfg(name='%s-config' % name, desc='%s desc' % desc, service_instance=inst,
                                          json_cfg=def_config, active=True)
            self.logger.debug('Set service instance configuration: %s' % truncate(def_config))

            # link instance to parent instance
            if parent_plugin is not None:
                # insert Link
                link_name = 'lnk_%s_%s' % (parent_plugin.instance.oid, inst.oid)
                self.add_service_instlink(link_name, parent_plugin.instance.oid, inst.oid)
                self.logger.info('Link service instance %s to parent instance %s' %
                                 (inst.uuid, parent_plugin.instance.uuid))

            self.release_session(None)
            self.get_session()
            inst.update_status(status)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            if inst is not None:
                inst.update_status(SrvStatusType.ERROR, error=ex.value)
            raise

        # get plugin type
        inst = self.get_service_instance(inst.oid)
        plugin = inst.get_service_type_plugin()

        # create post params
        params = {
            'alias': '%s.create' % plugin.plugintype,
            'id': inst.oid,
            'uuid': inst.uuid,
            'objid': inst.objid,
            'name': name,
            'desc': desc,
            'attribute': None,
            'tags': None
        }
        params.update(kvargs)

        # if resource uuid already exists update instance record and exit
        self.logger.debug('add_service_type_plugin - resource_uuid: %s' % resource_uuid)
        if resource_uuid is not None:
            # update model
            update_model_params = {'oid': inst.oid, 'resource_uuid': resource_uuid}
            inst.update_object(**update_model_params)
            return plugin

        try:
            # run pre create
            params = plugin.pre_create(**params)
            sync = params.pop('sync', False)
        except Exception:
            plugin.expunge_instance()
            self.logger.info('Delete service %s' % plugin.instance.uuid)
            raise

        try:
            # post create service using asynchronous celery task
            self.logger.debug('add_service_type_plugin - plugin.create_task %s' % plugin.create_task)
            if plugin.create_task is not None:
                params.update(inst.get_user())
                self.logger.debug('add_service_type_plugin - params: {}'.format(params))
                res = prepare_or_run_task(inst, plugin.create_task, params, sync=sync)
                self.logger.info('add_service_type_plugin - run create task: %s' % res[0])

                if sync is False:
                    plugin.active_task = res[0]['taskid']
                if sync is True:
                    plugin.active_task = res[0]

                # post create function
                self.logger.debug('add_service_type_plugin - post_create 01')
                plugin.post_create(**params)

            # post create service using sync method
            else:
                self.active_task = None

                self.logger.debug('add_service_type_plugin - update_status BUILDING')
                inst.update_status(SrvStatusType.BUILDING)

                # post create function
                self.logger.debug('add_service_type_plugin - post_create 02')
                plugin.post_create(**params)

                inst.update_status(SrvStatusType.ACTIVE)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            inst.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return plugin

    @trace(entity='ApiServiceInstance', op='insert')
    def import_service_type_plugin(self, service_definition_id, account_id, name=None, desc=None, parent_plugin=None,
                                   instance_config=None, account=None, resource_id=None, *args, **kvargs):
        """Factory used to create new service instance using the related service type plugin and set an existing
        resource.

        :param service_definition_id: service definition identifier
        :param account_id: account identifier
        :param parent_plugin: parent plugin instance
        :param name: instance name [optional]
        :param desc: instance description [optional]
        :param instance_config: service instance configurations [optional]
        :param account: Account if available beehive_service.controller.ApiAccount  [optional]
        :param resource_id: resource id to connect
        :return: {'uuid': ..}
        :raises ApiManagerWarning: if instance cannot to be created.
        """
        if instance_config is None:
            instance_config = {}
        # get definition
        service_definition = self.get_service_def(service_definition_id)
        if service_definition.is_active() is False:
            raise ApiManagerWarning('Service definition %s is not in ACTIVE state' % service_definition.uuid)

        # get account
        if account is None:
            account = self.get_account(account_id)
        # if account.is_active() is False:
        #     raise ApiManagerWarning('Account %s is not in ACTIVE state' % account.uuid)
        check, reason = account.can_instantiate(definition=service_definition)
        if not check:
            raise ApiManagerError( reason + f': Account {account.name} ({account.uuid}) definition {service_definition.name}')

        # get name
        if name is None:
            name = service_definition.name + '-inst'

        # get desc
        if desc is None:
            desc = name

        # check name length
        if len(name) > 40:
            raise ApiManagerError('Service name is too long. Maxsize is 40')

        inst = None
        try:
            def_config = service_definition.get_main_config().params
            def_config.update(instance_config)

            # create service instance
            inst = self.add_service_instance(name=name, desc=desc, service_def_id=service_definition.oid,
                                             status=SrvStatusType.DRAFT, account=account, bpmn_process_id=None,
                                             active=True, version='1.0')

            # create service instance config
            self.add_service_instance_cfg(name='%s-config' % name, desc='%s desc' % desc, service_instance=inst,
                                          json_cfg=def_config, active=True)
            self.logger.debug('Set service instance configuration: %s' % truncate(def_config))

            # link instance to parent instance
            if parent_plugin is not None:
                # insert Link
                link_name = 'lnk_%s_%s' % (parent_plugin.instance.oid, inst.oid)
                self.add_service_instlink(link_name, parent_plugin.instance.oid, inst.oid)
                self.logger.info('Link service instance %s to parent instance %s' %
                                 (inst.uuid, parent_plugin.instance.uuid))

            self.release_session(None)
            self.get_session()
            inst.update_status(SrvStatusType.DRAFT)
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            if inst is not None:
                inst.update_status(SrvStatusType.ERROR, error=ex.value)
            raise

        # get plugin type
        inst = self.get_service_instance(inst.oid)
        plugin = inst.get_service_type_plugin()

        # create post params
        params = {
            'id': inst.oid,
            'uuid': inst.uuid,
            'objid': inst.objid,
            'name': name,
            'desc': desc,
            'attribute': None,
            'tags': None,
            'resource_id': resource_id
        }
        params.update(kvargs)

        try:
            # run pre create
            params = plugin.pre_import(**params)
            resource_id = params.get('resource_id')
        except Exception:
            plugin.expunge_instance()
            self.logger.info('Delete service %s' % plugin.instance.uuid)
            raise

        # update instance record with resource uuid
        if resource_id is not None:
            # update model
            update_model_params = {'oid': inst.oid, 'resource_uuid': resource_id}
            inst.update_object(**update_model_params)

        try:
            # post create service using sync method
            inst.update_status(SrvStatusType.BUILDING)

            # post create function
            inst = self.get_service_instance(inst.oid)
            plugin = inst.get_service_type_plugin()
            plugin.post_import(**params)

            inst.update_status(SrvStatusType.ACTIVE)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            inst.update_status(SrvStatusType.ERROR, error=ex)
            raise

        return plugin

    # @trace(entity='ApiServiceInstance', op='view')
    # def del_service_type_plugin(self, service_definition_id, account_id, name=None, desc=None, instance_parent_id=None,
    #                             instance_config={}, *args, **kvargs):
    #     """Factory used to create new service instance using the related service type plugin
    #
    #     :param service_definition_id: service definition identifier
    #     :param account_id: account identifier
    #     :param name: instance name [optional]
    #     :param desc: instance description [optional]
    #     :param instance_parent_id : parent instance [optional]
    #     :param instance_config: service instance configurations [optional]
    #     :return: {'taskid': .., 'uuid': ..}
    #     :raises ApiManagerWarning: if instance cannot to be created.
    #     """
    #     pass

    ############################
    ###    ServiceProcess    ###
    ############################
    @trace(entity='ApiServiceProcess', op='view')
    def get_service_process(self, oid):
        """Get single ServiceProcess.

        :param oid: entity model id, uuid
        :return: ServiceProcess
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        srvCostParam = self.get_entity(ApiServiceProcess, ServiceProcess, oid)
        return srvCostParam

    @trace(entity='ApiServiceProcess', op='view')
    def get_service_processes(self, *args, **kvargs):
        """Get ServiceProcesses.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceCostParam
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceProcess(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_processes(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        # resolve uuid in id
        self.resolve_fk_id('service_type_id', self.get_service_type, kvargs )

        res, total = self.get_paginated_entities(ApiServiceProcess, recuperaServiceProcess,
                                                 customize=customize, authorize=False, *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceProcess', op='insert')
    def add_service_process(self, name='', desc=None,
            service_type_id=None, method_key=None,
            process_key=None, active=True, template = None):

        """  """
        servicetype = self.get_service_type(service_type_id)

        # check authorization on serviceType
        self.check_authorization(ApiServiceType.objtype,
                                 ApiServiceType.objdef,
                                 servicetype.objid, 'update')
        try:
            # create reference
            objid = id_gen(parent_id=servicetype.objid)
            srv_cp = ServiceProcess(objid, name, servicetype.oid, method_key, process_key, template,
                                    desc=desc,
                                    active=active)

            res = self.manager.add(srv_cp)

            # create object and permission
            #ApiServiceProcess(controller, oid=res.id).register_object([objid], desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    # ############################
    # ###   ServiceCostParam   ###
    # ############################
    # @trace(entity='ApiServiceCostParam', op='view')
    # def get_service_cost_param(self, oid):
    #     """Get single service_type.
    #
    #     :param oid: entity model id, uuid
    #     :return: ServiceType
    #     :raises ApiManagerError: raise :class:`ApiManagerError`
    #     """
    #
    #     srvCostParam = self.get_entity(ApiServiceCostParam, ServiceCostParam, oid)
    #     return srvCostParam
    #
    # @trace(entity='ApiServiceCostParam', op='view')
    # def get_service_cost_params(self, *args, **kvargs):
    #     """Get ServiceCostParam.
    #
    #     :param args:
    #     :param kvargs:
    #     :return:
    #     :name: name like [optional]
    #     :page: users list page to show [default=0]
    #     :size: number of users to show in list per page [default=0]
    #     :order: sort order [default=DESC]
    #     :field: sort field [default=id]
    #     :return: List of ServiceCostParam
    #     :raises ApiManagerError: if query empty return error.
    #     """
    #     def recuperaServiceCostParam(*args, **kvargs):
    #         entities, total = self.manager.get_paginated_service_cost_params(*args, **kvargs)
    #         return entities, total
    #
    #     def customize(res, *args, **kvargs):
    #         return res
    #
    #     #resolve uuid in id
    #     self.resolve_fk_id('service_type_id', self.get_service_type, kvargs )
    #
    #     res, total = self.get_paginated_entities(ApiServiceCostParam, recuperaServiceCostParam,
    #                                              customize=customize, *args, **kvargs)
    #     return res, total

    ############################
    ###    ServiceConfig     ###
    ############################
    @trace(entity='ApiServiceConfig', op='view')
    def get_service_cfg(self, oid):
        """Get single ServiceConfig.

        :param oid: entity model id, uuid
        :return: ServiceType
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        srvCfg = self.get_entity(ApiServiceConfig, ServiceConfig, oid)
        return srvCfg

    @trace(entity='ApiServiceConfig', op='view')
    def get_service_cfgs(self, *args, **kvargs):
        """Get ServiceConfig.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceConfig
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceConfigs(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_configs(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        # resolve uuid in id
        self.resolve_fk_id('service_definition_id', self.get_service_def, kvargs )

        res, total = self.get_paginated_entities(ApiServiceConfig, recuperaServiceConfigs, customize=customize,
                                                 *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceConfig', op='insert')
    def add_service_cfg(self, name='', desc=None, service_definition_id=None, params=None,
                        params_type=ConfParamType.JSON, active=True, version='1.0'):
        """Add service definition configuration

        :param name:
        :param desc:
        :param service_definition_id:
        :param params:
        :param params_type:
        :param active:
        :param version:
        :return:
        """
        if params is None:
            params = {}
        service_def = self.get_service_def(service_definition_id)

        # check already exixst
        config = self.manager.get_service_config(service_definition_id=service_def.oid)
        if config is not None:
            self.logger.error('Service definition %s config already exists' % service_def.uuid)
            raise ApiManagerError('Service definition %s config already exists' % service_def.uuid)

        # check authorization
        self.check_authorization(ApiServiceConfig.objtype, ApiServiceConfig.objdef, service_def.objid, 'insert')
        try:
            # create organization reference
            objid = id_gen(parent_id=service_def.objid)

            srv_type = ServiceConfig(objid=objid, name=name, desc=desc, service_definition_id=service_def.oid,
                                     params=params, params_type=params_type, active=active, version=version)

            res = self.manager.add(srv_type)
            # create object and permission

            ApiServiceConfig(self, oid=res.id).register_object(objid.split('//'), desc=name)
            return res.uuid

        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ############################
    ###   ServiceDefinition  ###
    ############################
    @trace(entity='ApiServiceDefinition', op='view')
    def get_service_def(self, oid: Union[int, str]) -> ApiServiceDefinition:
        """Get single service definition.

        :param oid: entity model id, uuid, or name
        :return: ServiceDefinition
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv = self.get_entity(ApiServiceDefinition, ServiceDefinition, oid)
        return srv

    @trace(entity='ApiServiceDefinition', op='view')
    def get_default_service_def(self, plugintype):
        """Get default service defition.

        :param plugintype: plugintype
        :return: ServiceDefinition
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        defs = self.manager.get_service_definitions(plugintype=plugintype, is_default=True)
        if len(defs) != 1:
            self.logger.error('Service definition default for type %s does not exist' % plugintype,
                              exc_info=True)
            raise ApiManagerError('Service definition default for type %s does not exist' % plugintype,
                                  code=409)

        entity = defs[0]
        obj = ApiServiceDefinition(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                                   desc=entity.desc, model=entity)

        if obj.is_active() is False:
            raise ApiManagerWarning('ServiceDefinition %s is not in ACTIVE state' % obj.uuid)

        self.logger.debug('Get default service definition %s for type %s' % (obj, plugintype))
        return obj

    @trace(entity='ApiServiceDefinition', op='view')
    def check_service_definition(self, service_definition_id: Union[int, str], service_definition_name: str='ServiceDefinition')-> ApiServiceDefinition:
        """Check service definition is active.

        :param service_definition_id: service definition id or uuid
        :param service_definition_type: service definition name [default=ServiceDefinition]
        :return: ServiceDefinition
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # get definition
        service_definition = self.get_service_def(service_definition_id)
        if service_definition.is_active() is False:
            raise ApiManagerWarning('%s %s is not in ACTIVE state' %
                                    (service_definition_name, service_definition.uuid))

        return service_definition

    @trace(entity='ApiServiceDefinition', op='view')
    def get_paginated_service_defs(self, *args, **kvargs) -> Tuple[List[ApiServiceDefinition], int]:
        """Get ServiceDefinition.

        :param service_type_id: id service [optional]
        :param status: service defintion status [optional]
        :param parent_id: parent service defintion id [optional]
        :param plugintype: plugin type name [optional]
        :param flag_container: if True select only definition with type that is a container [optional]
        :param catalogs: comma sepaarted list of service catalog ids [optional]
        :param service_definition_id_list: list of service definitions id [optional]
        :param service_definition_uuid_list: list of service definitions uuid [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceDefinition
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceDefinitions(*args, **kvargs):
            kvargs['group_by'] = True
            entities, total = self.manager.get_paginated_service_definitions(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('service_type_id', self.get_service_type, kvargs)
        kvargs['authorize'] = False
        res, total = self.get_paginated_entities(ApiServiceDefinition, recuperaServiceDefinitions,
                                                 customize=customize, *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceDefinition', op='view')
    def get_service_defs(self, *args, **kvargs):
        """Get ServiceDefinition.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceDefinition
        :raises ApiManagerError: if query empty return error.
        """
        def findServiceDefinitions(*args, **kvargs):
            entities = self.manager.get_service_definitions(*args, **kvargs)
            return entities

        self.resolve_fk_id('service_type_id', self.get_service_type, kvargs)
        kvargs['authorize'] = False
        res = self.get_entities(ApiServiceDefinition, findServiceDefinitions, *args, **kvargs)
        return res

    @trace(entity='ApiServiceDefinition', op='insert')
    def add_service_def(self, name='', desc=None, service_type_id=None, parent_id=None, priority=0, active=True,
                        status=SrvStatusType.DRAFT, version='1.0', is_default=False):
        """Add service definition

        :param name:
        :param desc:
        :param service_type_id:
        :param parent_id:
        :param priority:
        :param active:
        :param status:
        :param version:
        :param is_default: if True set service def as default
        :return:
        """
        # get entiy ServiceType
        serviceType = self.get_service_type(service_type_id)

        # check already exixst
        defs = self.manager.get_service_definitions(name=name, service_type_id=serviceType.oid)
        if len(defs) > 0:
            self.logger.error('Service definition %s for type %s already exists' % (name, serviceType.name),
                              exc_info=True)
            raise ApiManagerError('Service definition %s for type %s already exists' % (name, serviceType.name),
                                  code=409)

        # if is_default is True check no other default service def exists for the same type
        if is_default is True:
            defs = self.manager.get_service_definitions(service_type_id=serviceType.oid, is_default=True)
            if len(defs) > 0:
                self.logger.error('Service definition default for type %s already exists' % serviceType.name,
                                  exc_info=True)
                raise ApiManagerError('Service definition default for type %s already exists' % serviceType.name,
                                      code=409)

        # check authorization
        self.check_authorization(ApiServiceDefinition.objtype, ApiServiceDefinition.objdef,
                                 serviceType.objid, 'insert')
        try:
            # check parent
            if parent_id is not None:
                #  get the parent entity Service Definition
                srv_def_start = self.get_service_def(parent_id)

            # create service definition reference
            objid = id_gen(parent_id=serviceType.objid)
            self.logger.debug('Add Service Definition objid: %s' % objid)

            srv_def = ServiceDefinition(objid=objid, name=name, desc=desc, service_type_id=serviceType.oid,
                                        active=active, status=status, version=version, is_default=is_default)

            res = self.manager.add(srv_def)
            self.logger.debug('Added Service Definition: %s' % res)

            # create the service link
            if parent_id is not None:
                # get the model ServiceType
                srv_type = srv_def_start.model.service_type
                # check if the ServiceType is a container
                srv_deflink = self.add_service_deflink(name, srv_def_start.oid, res.id, priority)
                # TODO matching rule to verify compatibility beetween ServiceType
                self.logger.debug('Added ServiceDefinition Link: %s' % srv_deflink)

            # create object and permission
            ApiServiceDefinition(self, oid=res.id).register_object(objid.split('//'), desc=name)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def get_catalog_service_definitions(self, size=10, page=0, plugintype='ComputeInstance', def_uuids=None):
        """Get service definitions relative to visible catalog

        :param size: number of item to query
        :param page: page of query
        :param plugintype: plugintype
        :param def_uuids: list of definitions id or uuid
        :return: list of service definitions
        """
        if def_uuids is None:
            def_uuids = []
        args = []
        kwargs = {}

        # catalogs
        catalogs, total = self.get_service_catalogs(filter_expired=False)
        catalog_ids = ','.join([str(c.oid) for c in catalogs])

        kwargs['size'] = size
        kwargs['page'] = page

        # get only volume type list active and of type ComputeInstance
        # kwargs['filter_expired'] = False
        kwargs['service_definition_uuid_list'] = def_uuids
        kwargs['plugintype'] = plugintype
        kwargs['catalogs'] = catalog_ids
        kwargs['authorize'] = False
        res, total = self.get_paginated_service_defs(*args, **kwargs)

        # format result
        res_type_set = []

        for r in res:
            res_type_item = {}
            res_type_item['id'] = r.oid
            res_type_item['uuid'] = r.uuid
            res_type_item['name'] = r.name
            res_type_item['description'] = r.desc

            features = []
            if r.desc is not None:
                features = r.desc.split(' ')

            feature = {}
            for f in features:
                try:
                    k, v = f.split(':')
                    feature[k] = v
                except ValueError:
                    pass
                    # self.logger.warning('service definition %s does not have feature info in description '
                    #                     'attribute' % r.uuid)
            res_type_item['features'] = feature
            res_type_set.append(res_type_item)

        if total == 1:
            res_type_set[0]['config'] = res[0].get_main_config().params

        return res_type_set, total

    ############################
    ###   ServiceInstance    ###
    ############################
    def updateInstanceStatus(self, oid, statusName, resource_uuid=None):
        """ """
        #check parameters
        AssertUtil.assert_is_not_none(oid)
        AssertUtil.assert_is_not_none(statusName)
        # get instance
        srv_inst = self.get_service_instance(oid)

        try:
            data = {'status':statusName}
            if resource_uuid is not None:
                #ggg sembra un errore data.append({'resource_uuid':resource_uuid})
                data['resource_uuid']=resource_uuid

            resp = srv_inst.update(**data)

            return(resp)
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex.desc, code=400)

    def createInstanceHierachy(self, oid_def, account_id, service_def=None, name=None, desc=None, params_resource=None,
                               instance_parent_id=None, account=None, *args, **kvargs):
        """Create an instance hierarchy.

        :param oid_def: identifier service definition
        :param account_id: identifier account
        :param account: identifier account[optional]
        :param service_def: model service definition [optional]
        :param name: instance name [optional]
        :param desc: instance description [optional]
        :param params_resource: [optional]
        :param instance_parent_id : parent instance [optional]
        :return: Model ServiceInstance object
        :raises ApiManagerWarning: if instance cannot to be created.
        """
        if params_resource is None:
            params_resource = {}
        serviceDefRoot = None

        # get definition
        if service_def is None:
            AssertUtil.assert_is_not_none(oid_def)
            apiDef = self.get_service_def(oid_def)
            AssertUtil.assert_is_not_none(apiDef)
            serviceDefRoot = apiDef.model
            self.logger.debug('Recuperata serviceDef %s' % serviceDefRoot.uuid)
        else:
            serviceDefRoot = service_def.model

        if serviceDefRoot.is_active() is False:
            raise ApiManagerWarning('Service definition %s is not in ACTIVE state' % serviceDefRoot.uuid)

        # get account
        if account is None:
            AssertUtil.assert_is_not_none(account_id)
            account = self.get_account(account_id)

        # get name
        if name is None:
            instName = serviceDefRoot.name
        else:
            instName = name

        # get desc
        if desc is None:
            instDesc = serviceDefRoot.desc
        else:
            instDesc = desc

        # visita dept-first dell'albero e creazione della Instance Hierarchy
        if serviceDefRoot is not None:
            self.logger.info('Creazione Instance parent ...')
            parent = self.add_service_instance(name=instName, desc=instDesc, service_def_id=serviceDefRoot.id,
                                               status=SrvStatusType.DRAFT, account=account, bpmn_process_id=None,
                                               active=True, version='1.0')

            # link instance to parent instance
            if instance_parent_id is not None:
                # insert Link
                linkInstName = 'lnk_%s_%s' % (instance_parent_id, parent.oid)
                self.add_service_instlink(linkInstName, instance_parent_id, parent.oid)

            self.logger.info('Creazione Instance parent')
            serviceDefConfigParams = serviceDefRoot.config_params

            # create serviceConfigInstance
            for confDef in serviceDefConfigParams:
                conf_name = '%s-%s-config' % (instName, id_gen())
                self.add_service_instance_cfg(name=conf_name, desc=conf_name, service_instance=parent,
                                              json_cfg=confDef.params, active=True)
            # ricorsione sui figli
            for linkDef in serviceDefRoot.linkChildren:
                # creazione figlio
                link_end_service = ServiceUtil.instanceApi(self, ApiServiceDefinition, linkDef.end_service)
                child = self.createInstanceHierachy(linkDef.end_service_id, None, service_def=link_end_service,
                                                    params_resource=params_resource, account=account)
                # insert Link
                linkInstName = 'lnk_%s_%s' % (parent.oid, child.oid)
                self.add_service_instlink(linkInstName, parent.oid, child.oid, priority=linkDef.priority,
                                          desc=linkInstName, attributes=linkDef.attributes)
            return parent
        else:
            raise ApiManagerWarning('Cannot create instance', 208)

    @trace(entity='ApiServiceInstance', op='view')
    def exist_service_instance(self, oid: Union[str, int], plugintype: str)-> bool:
        """Check if ServiceInstance exists

        :param oid: entity model id, uuid
        :param plugintype: service istance plugintype
        :return: True or False
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        model = self.manager.get_entity(ServiceInstance, oid)
        if model is None:
            return False
        servicetype_model = model.service_definition.service_type
        plugin_class = import_class(servicetype_model.objclass)
        if plugin_class.plugintype != plugintype:
            return False
        return True

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_instance(self, oid)->ApiServiceInstance:
        """Get single ServiceInstance.

        :param oid: entity model id, uuid
        :return: ServiceInstance
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv = self.get_entity(ApiServiceInstance, ServiceInstance, oid)
        srv.get_main_config()
        return srv

    @trace(entity='ApiServiceInstance', op='view')
    def check_service_instance(self, oid, service_class, account=None):
        """Check single ServiceInstance.

        :param oid: entity model id, uuid
        :param service_class: service istance implementatio class
        :param account: service istance required parent account [optional]
        :return: ServiceInstance
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv = self.get_entity(ApiServiceInstance, ServiceInstance, oid)
        plugin_type = service_class.plugintype
        AssertUtil.assert_is_not_none(srv.getPluginType(plugin_type),
                                      'Service %s %s does not exist' % (plugin_type, srv.uuid))
        if srv.is_active() is False:
            raise ApiManagerWarning('Service %s %s is not in ACTIVE state' % (plugin_type, srv.uuid))

        if account is not None and srv.account_id != account:
            raise ApiManagerWarning('Service %s %s is not in the account %s' % (plugin_type, srv.uuid, account))

        return srv

    def count_service_instances(self, *args, **kvargs):
        """ count Service Instance
        :return: count of ServiceInstance
        :raises ApiManagerError: if query empty return error.
        """
        count = self.manager.count_service_instances(*args, **kvargs)
        self.logger.warning ('count_service_instances=%s' % count )
        return count

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_instances(self, *args, **kvargs):
        """Get ServiceInstance.

        :DEPRECATED: Da sostituire con il recupero delle istanze tramite serviceLink
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceInstance
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceInstances(*args, **kvargs):
            entities = self.manager.get_service_instances(*args, **kvargs)
            return entities

        self.resolve_fk_id('fk_account_id', self.get_account, kvargs)
        self.resolve_fk_id('fk_service_definition_id', self.get_service_def, kvargs)
        self.resolve_fk_id('parent_id', self.get_service_instance, kvargs)

        res = self.get_entities(ApiServiceInstance, recuperaServiceInstances, *args, **kvargs)
        return res

    @trace(entity='ApiServiceInstance', op='view')
    def get_paginated_service_instances(self, *args, **kvargs):
        """Get ServiceInstance.

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :param version: service version
        :param account_id: id account [optional]
        :param service_definition_id: id service definition [optional]
        :param status: instance status name [optional]
        :param bpmn_process_id: id process bpmn [optional]
        :param plugintype: plugin type name [optional]
        :param resource_uuid: resource uuid related to service instance[optional]
        :param flag_container: if True show only container instances [optional]
        :param period_val_start: [optional]
        :param period_val_stop: [optional]
        :param service_name_list: list of services instances name [optional]
        :param service_uuid_list: list of services instances uuid [optional]
        :param service_id_list: list of services instances id [optional]
        :param account_id_list: list of accounts id related to services instances [optional]
        :param service_definition_id_list: list of service definitions id related to services instances [optional]
        :param resource_uuid_list: list of resources uuid related to services instances [optional]
        :param service_status_name_list: list of status names related to services instances [optional]
        :param servicetags: comma separated list of service tags [optional]. Search exactly the list of tags.
        :param servicetags_in: comma separated list of service tags [optional]. Search in the tag list.
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param details: if True read also instance config, definition and parent account
        :return: List of ServiceInstance
        :raises ApiManagerError: if query empty return error.
        """
        def get_service_instances(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_instances(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            if kvargs.get('details', True) is True:
                oids = [i.oid for i in res]
                if len(oids) > 0:
                    config_idx = self.get_service_instance_config_idx(service_instance_ids=oids)
                    def_idx = self.get_service_definition_idx(None)
                    account_idx = self.get_account_idx()

                    for r in res:
                        c = config_idx.get(r.oid, None)
                        if c is not None:
                            config = ApiServiceInstanceConfig(self, oid=c.id, objid=c.objid, name=c.name, desc=c.desc,
                                                              active=c.active, model=c)
                            r.config_object = config
                        r.definition = def_idx.get(str(r.model.service_definition_id), None)
                        r.account = account_idx.get(str(r.model.account_id), None)

            return res

        self.resolve_fk_id('account_id', self.get_account, kvargs)
        self.resolve_fk_id('service_definition_id', self.get_service_def, kvargs)
        self.resolve_fk_id('parent_id', self.get_service_instance, kvargs)

        res, total = self.get_paginated_entities(ApiServiceInstance, get_service_instances,
                                                 customize=customize, *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_instance_by_resource_uuid(self, resource_uuid, plugintype=None):
        """Get ServiceInstance by resource uuid

        :param resource_uuid: resource uuid
        :return: service instance
        """
        res, tot = self.get_paginated_service_instances(resource_uuid=resource_uuid, plugintype=plugintype)
        if tot == 0:
            raise ApiManagerError('no service instance found for resource uuid %s' % resource_uuid)
        res = res[0]
        self.logger.debug('get service instance %s by resource uuid %s' % (res.uuid, resource_uuid))
        return res

    @trace(entity='ApiServiceInstance', op='insert')
    def add_service_instance(self, name='', desc=None, service_def_id=None, status=SrvStatusType.DRAFT,
                             account=None, bpmn_process_id=None, active=True, version='1.0'):
        """Add service instance

        :param name:
        :param desc:
        :param service_def_id:
        :param status:
        :param account:
        :param bpmn_process_id:
        :param active:
        :param version:
        :return:
        """
        # check authorization
        self.check_authorization(ApiServiceInstance.objtype, ApiServiceInstance.objdef, account.objid, 'insert')

        # check name characters are allowed
        if validate_string(name, validation_string=r'[^a-zA-Z0-9\-].') is False:
            raise ApiManagerError('Name must contains only alphanumeric characters, numbers and -')

        # check instance with the same name already exists in the account
        insts, tot = self.get_paginated_service_instances(name=name, account_id=account.oid, filter_expired=False,
                                                          authorize=False)
        if tot > 0:
            raise QueryError('Service instance %s already exists in account %s' % (name, account.uuid), code=409)

        try:
            # create service instance reference
            objid = id_gen(parent_id=account.objid)

            inst = ServiceInstance(objid, name=name, account_id=account.oid, service_definition_id=service_def_id,
                                   desc=desc, active=active, status=status, version=version,
                                   bpmn_process_id=bpmn_process_id, resource_uuid=None)
            res = self.manager.add(inst)

            api_inst = ApiServiceInstance(self, oid=inst.id, objid=inst.objid, name=inst.name, desc=inst.desc,
                                          active=inst.active, model=inst)

            # create object and permission
            api_inst.register_object(objid.split('//'), desc=name)
            # ApiServiceInstance(self, oid=res.id).register_object(objid.split('//'), desc=name)

            self.logger.info('Create service instance: %s' % api_inst.uuid)

            # # create the service link instance
            # if parent_id is not None:
            #     #  get the parent entity Service Instance
            #     srv_inst_start = self.get_service_instance(parent_id)
            #
            #     # get the model ServiceType
            #     srv_type = srv_inst_start.model.service_definition.service_type
            #
            #     # check if the ServiceType is a container
            #     pluginRoot = srv_inst_start.instancePlugin(None, srv_inst_start)
            #     if isinstance(pluginRoot, ApiServiceTypeContainer):
            #         # check priority
            #         if priority is None:
            #             if srv_inst_start.model.linkChildren is not None:
            #                 link = max(srv_inst_start.model.linkChildren, key=lambda p: p.priority)
            #                 nextPriority = link.priority+1
            #             else:
            #                 nextPriority = 1
            #         else:
            #             nextPriority = priority
            #
            #         # make link name
            #         linkInstName = 'lnk_%s_%s' % (srv_inst_start.oid, res.id)
            #
            #         # add link
            #         srv_instlink = self.add_service_instlink(linkInstName, srv_inst_start.oid, res.id,
            #                                                  priority=nextPriority)
            #         # TODO matching rule to verify compatibility beetween ServiceType
            #         self.logger.info('Added ServiceLinkInst: %s' % srv_instlink)
            #     else:
            #         self.logger.warn('Attribute parent_id have been ignored because the is not a container instance')
            return api_inst

        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @transaction
    def delete_service_instance2(self, srv_inst, data, recursive_delete=True, batch=True):
        """Delete service instance
        TODO: compatibility with camunda

        :param srv_inst:
        :param data:
        :param recursive_delete:
        :param batch:
        :return:
        """
        @maybe_run_batch_greenlet(self, batch, timeout=600)
        def action(srv_inst, data, recursive_delete):
            self.logger.info('Delete ServiceInstance START - %s' % srv_inst)
            self.logger.debug('recursive_delete: %s' % recursive_delete)

            self.check_authorization(srv_inst.objtype, srv_inst.objdef, srv_inst.objid, action='delete')

            if batch is True:
                # re get service instance from database (this method run in a different thread)
                srv_inst = self.get_service_instance(srv_inst.oid)

            srv_inst.pre_delete()

            if srv_inst.model.linkChildren is not None and srv_inst.model.linkChildren.count() > 0:
                if not recursive_delete:
                    self.logger.warn('The instance %s has children. Force deletion with parameter '
                                     '"recursive" to true.' % srv_inst.oid)
                    raise ApiManagerWarning('The instance %s has children. Force deletion with parameter '
                                            '"recursive" to true.' % srv_inst.oid)

            # delete instance link Parent
            for l in srv_inst.model.linkParent:
                self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
                api_link = ServiceUtil.instanceApi(self, ApiServiceLinkInst, l)
                api_link.delete(soft=True)

            # delete instance link and children
            for l in srv_inst.model.linkChildren:
                self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
                api_link = ServiceUtil.instanceApi(self, ApiServiceLinkInst, l)
                child = ServiceUtil.instanceApi(self, ApiServiceInstance, l.end_service)
                self.delete_service_instance(self, data, l.end_service_id, instance=child)

            pluginCh = srv_inst.instancePlugin(srv_inst.oid)
            # make delete of resource
            if srv_inst.resource_uuid is not None:
                # check resource already exists
                res = pluginCh.checkResource(srv_inst)

                # delete resource
                try:
                    if res is not None:
                        pluginCh.deleteResource(srv_inst, batch=False)
                except:
                    self.logger.error('Error deleting resource', exc_info=True)
                    raise

            # delete instance config
            for cfg in srv_inst.model.config:
                self.logger.debug('Delete ServiceInstanceConfig: %s' % cfg)
                api_cfg = ServiceUtil.instanceApi(self, ApiServiceInstanceConfig, cfg)
                api_cfg.delete(soft=True)

            resp = srv_inst.delete(soft=True)

            self.logger.info('Delete ServiceInstance END - %s' % srv_inst)

        action(srv_inst, data, recursive_delete)

    @transaction
    def delete_service_instance(self, srv_inst, data, recursive_delete=True, batch=True):
        """Delete service instance
        TODO: compatibility with camunda

        :param srv_inst:
        :param data:
        :param recursive_delete:
        :param batch: not supported
        :return:
        """
        self.logger.info('Delete ServiceInstance START - %s' % srv_inst)
        self.logger.debug('recursive_delete: %s' % recursive_delete)

        self.check_authorization(srv_inst.objtype, srv_inst.objdef, srv_inst.objid, action='delete')

        if batch is True:
            # re get service instance from database (this method run in a different thread)
            srv_inst = self.get_service_instance(srv_inst.oid)

        srv_inst.pre_delete()

        if srv_inst.model.linkChildren is not None and srv_inst.model.linkChildren.count() > 0:
            if not recursive_delete:
                self.logger.warn('The instance %s has children. Force deletion with parameter '
                                 '"recursive" to true.' % srv_inst.oid)
                raise ApiManagerWarning('The instance %s has children. Force deletion with parameter '
                                        '"recursive" to true.' % srv_inst.oid)

        # delete instance link Parent
        for l in srv_inst.model.linkParent:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
            api_link = ServiceUtil.instanceApi(self, ApiServiceLinkInst, l)
            api_link.delete(soft=True)

        # delete instance link and children
        for l in srv_inst.model.linkChildren:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % l)
            api_link = ServiceUtil.instanceApi(self, ApiServiceLinkInst, l)
            child = ServiceUtil.instanceApi(self, ApiServiceInstance, l.end_service)
            self.delete_service_instance(self, data, l.end_service_id, instance=child)

        pluginCh = srv_inst.instancePlugin(srv_inst.oid)
        # make delete of resource
        if srv_inst.resource_uuid is not None:
            # check resource already exists
            res = pluginCh.checkResource(srv_inst)

            # delete resource
            try:
                if res is not None:
                    pluginCh.deleteResource(srv_inst, batch=False)
            except:
                self.logger.error('Error deleting resource', exc_info=True)
                raise

        # delete instance config
        for cfg in srv_inst.model.config:
            self.logger.debug('Delete ServiceInstanceConfig: %s' % cfg)
            api_cfg = ServiceUtil.instanceApi(self, ApiServiceInstanceConfig, cfg)
            api_cfg.delete(soft=True)

        resp = srv_inst.delete(soft=True)

        self.logger.info('Delete ServiceInstance END - %s' % srv_inst)
        return resp

    @trace(entity='ApiServiceInstance', op='view')
    def get_service_instance_children(self, oid, authorize=True):
        """Get Service Instance children.

        :param oid: entity model id, name or uuid
        :return: Service Instance
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_inst = ApiController.get_entity(self, ApiServiceInstance, ServiceInstance, oid, authorize)

        for link in srv_inst.model.linkChildren:
            ApiController.get_entity(self, ApiServiceInstance, ServiceInstance, oid, authorize)

        return srv_inst

    #############################
    ### ServiceInstanceConfig ###
    #############################
    @trace(entity='ApiServiceInstanceConfig', op='view')
    def get_service_instance_cfg(self, oid):
        """Get single ServiceInstanceConfig.

        :param oid: entity model id, uuid
        :return: ServiceType
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srvCfg = self.get_entity(ApiServiceInstanceConfig, ServiceInstanceConfig, oid)
        return srvCfg

    @trace(entity='ApiServiceInstanceConfig', op='view')
    def get_service_instance_cfgs(self, *args, **kvargs):
        """Get ServiceInstanceConfig.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceInstanceConfig
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceInstConfigs(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_instance_configs(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('service_instance_id', self.get_service_instance, kvargs)

        res, total = self.get_paginated_entities(ApiServiceInstanceConfig, recuperaServiceInstConfigs,
                                                 customize=customize, *args, **kvargs)

        return res, total

    @trace(entity='ApiServiceInstanceConfig', op='insert')
    def add_service_instance_cfg(self, name='', desc=None, service_instance=None, json_cfg=None, active=True):
        """Add service instance configuration

        :param name:
        :param desc:
        :param service_instance:
        :param json_cfg:
        :param active:
        :return: ApiServiceInstanceConfig instance
        """
        if json_cfg is None:
            json_cfg = {}
        # check authorization
        self.check_authorization(ApiServiceInstanceConfig.objtype,
                                 ApiServiceInstanceConfig.objdef,
                                 service_instance.objid, 'insert')
        try:
            # create obj reference
            objid = id_gen(parent_id=service_instance.objid)
            cfg = ServiceInstanceConfig(objid, name, service_instance.oid, json_cfg=json_cfg, desc=desc,
                                        active=active)
            res = self.manager.add(cfg)
            api_cfg = ApiServiceInstanceConfig(self, oid=cfg.id, objid=cfg.objid, name=cfg.name, desc=cfg.desc,
                                               active=cfg.active, model=cfg)

            # create object and permission
            ApiServiceInstanceConfig(self, oid=res.id).register_object(objid.split('//'), desc=name)
            self.logger.info('Create service instance %s config: %s' % (cfg.uuid, truncate(json_cfg)))

            return api_cfg
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    #################################
    ###    ServiceInstanceLink    ###
    #################################
    @trace(entity='ApiServiceLinkInst', op='insert')
    def add_service_instlink(self, name, start_service_id, end_service_id, priority=0, desc=None, attributes=''):
        """ """
        # check authorization
        srv_instance_start = self.get_service_instance(start_service_id)
        srv_instance_end = self.get_service_instance(end_service_id)

        self.check_authorization(ApiServiceLinkInst.objtype,
                                 ApiServiceLinkInst.objdef,
                                 srv_instance_start.objid, 'insert')
        try:
            # create Service Instance Link
            objid = id_gen(parent_id=srv_instance_start.objid)

            srv_istlink = ServiceLinkInstance(objid, name, srv_instance_start.oid, srv_instance_end.oid,
                                              priority=priority, desc=desc, attributes=attributes)
            res = self.manager.add(srv_istlink)

            # create object and permission for Service Instance Link
            ApiServiceLinkInst(self, oid=srv_istlink.id).register_object(objid.split('//'), desc=name)
            return srv_istlink.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiServiceLinkInst', op='view')
    def list_service_instlink(self, *args, **kvargs):
        """Get service instance links.

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Link for a service instance
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            # start_service_id = kvargs.pop('start_service_id', None)
            # end_service_id = kvargs.pop('end_service_id', None)

            # # get all links
            # if start_service_id is not None:
            #     kvargs['start_service_id'] = self.get_service_instance(start_service_id).oid
            # if end_service_id is not None:
            #     kvargs['end_service_id'] = self.get_service_instance(end_service_id).oid

            entities, total = self.manager.get_service_links(ServiceLinkInstance, *args, **kvargs)

            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('start_service_id', self.get_service_instance, kvargs)
        self.resolve_fk_id('end_service_id', self.get_service_instance, kvargs)
        res, total = self.get_paginated_entities(ApiServiceLinkInst,
                                                 get_entities,
                                                 customize=customize,
                                                 *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceLinkInst', op='view')
    def count_service_instlinks(self):
        return self.manager.count_entities(ServiceLinkInstance)

    @trace(entity='ApiServiceLinkInst', op='view')
    def get_service_instlink(self, oid, authorize=True):
        """Get Service Instance Link.

        :param oid: entity model id, name or uuid
        :return: Service Instance Link
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_instlink = ApiController.get_entity(self, ApiServiceLinkInst,
                                            ServiceLinkInstance, oid, authorize)
        return srv_instlink

    #################################
    ###    ServiceDefinitionLink  ###
    #################################
    @trace(entity='ApiServiceLinkDef', op='view')
    def list_service_deflink(self, *args, **kvargs):
        """List Service Definition Link.
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Link for service definition
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_service_links(
                ServiceLinkDef, *args, **kvargs)

            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('start_service_id', self.get_service_def, kvargs)
        self.resolve_fk_id('end_service_id', self.get_service_def, kvargs)

        res, total = self.get_paginated_entities(ApiServiceLinkDef,
                                                 get_entities,
                                                 customize=customize,
                                                 *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceLinkDef', op='view')
    def count_service_deflinks(self):
        """Count Service Definition Link.

        :param:
        :return:
        :raises:
        """
        return self.manager.count_entities(ServiceLinkDef)

    @trace(entity='ApiServiceLinkDef', op='view')
    def get_service_deflink(self, oid, authorize=True):
        """Get Service Definition Link.

        :param oid: entity model id, name or uuid
        :return: Service Instance Link
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_deflink = ApiController.get_entity(self, ApiServiceLinkDef,
                                            ServiceLinkDef, oid, authorize)
        return srv_deflink

    @trace(entity='ApiServiceLinkDef', op='insert')
    def add_service_deflink(self, name, start_service_id, end_service_id, priority=0, desc=None, attributes=''):
        """
        """
        # check authorization
        srv_def_start= self.get_service_def(start_service_id)
        srv_def_end= self.get_service_def(end_service_id)

        self.check_authorization(ApiServiceLinkDef.objtype,
                                 ApiServiceLinkDef.objdef,
                                 srv_def_start.objid, 'insert')
        try:
            # create Service Instance Link
            objid = id_gen(parent_id=srv_def_start.objid)
            srv_deflink = ServiceLinkDef(objid, name, srv_def_start.oid, srv_def_end.oid, priority=priority, desc=desc,
                                         attributes=attributes)
            res = self.manager.add(srv_deflink)

            # create object and permission for Service Definition Link
            ApiServiceLinkDef(self, oid=srv_deflink.id).register_object(objid.split('//'), desc=name)

            return srv_deflink.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    ############################
    ###    Organization      ###
    ############################
    @trace(entity='ApiOrganization', op='insert')
    def add_organization(self, name='', desc=None, org_type=OrgType.PUBLIC, ext_anag_id=None, attributes=None,
                         hasvat=None, partner=None, referent=None, email=None, legalemail=None, postaladdress=None,
                         *args, **kvargs):
        """ """
        # check account with the same name already exists in the division
        orgs, tot = self.get_organizations(name=name, filter_expired=False, authorize=False)
        if tot > 0:
            raise QueryError('Organization %s already exists' % (name), code=409)

        # TDC:
        default_service_status = 1
        default_version = '1.0'
        # check authorization
        self.check_authorization(ApiOrganization.objtype, ApiOrganization.objdef, None, 'insert')

        try:
            # create organization reference
            objid = id_gen()
            org = self.manager.add_organization(
                objid, name, org_type, default_service_status,
                desc, default_version, ext_anag_id, attributes, str2bool(hasvat), str2bool(partner),
                referent, email, legalemail, postaladdress,
                active=True)

            # create object and permission
            api_org = ApiOrganization(self, oid=org.id, objid=org.objid, name=org.name, active=org.active,
                                      desc=org.desc, model=org)
            api_org.register_object(objid.split('//'), desc=name)

            api_org.update_status(1)  # ACTIVE

            # post create
            api_org.post_create(batch=False, **kvargs)

            return org.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def count_all_organizations(self):
        """Get all organizations count"""
        return self.manager.count_entities(Organization)

    # def update_organization(self, *args, **kvargs):
    #     """Update organization"""
    #     return self.manager.update_organization(*args, **kvargs)

    @trace(entity='ApiOrganization', op='view')
    def get_organization(self, oid, *args, **kvargs):
        """Get single organization.

        :param oid: entity model id, name or uuid
        :return: Organization
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(ApiOrganization, Organization, oid, *args, **kvargs)

    @trace(entity='ApiOrganization', op='view')
    def get_organizations(self, *args, **kvargs):
        """Get organizations.

        :param zone: organization zone. Value like internal or external
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of organizations
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_organizations(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        res, total = self.get_paginated_entities(ApiOrganization, get_entities,
                                                 customize=customize, *args, **kvargs)
        return res, total

    ############################
    ###     Division         ###
    ############################
    @trace(entity='ApiDivision', op='insert')
    def add_division(self, name, organization_id, price_list_id=None, desc='', version='1.0', contact=None,
                     email=None, postaladdress=None, *args, **kvargs):
        """Add division

        :param name:
        :param organization_id:
        :param price_list_id:
        :param desc:
        :param version:
        :param contact:
        :param email:
        :param postaladdress:
        :return:
        """
        default_service_status = 1

        organization = self.get_organization(organization_id)
        # check the organization and take the id reference
        organization_id = organization.oid
        organization_objid = organization.objid

        # check authorization
        self.check_authorization(ApiDivision.objtype, ApiDivision.objdef, organization_objid, 'insert')

        # check account with the same name already exists in the division
        divs, tot = self.get_divisions(name=name, organization_id=organization_id, filter_expired=False,
                                       authorize=False)
        if tot > 0:
            raise QueryError('Division %s already exists in organization %s' % (name, organization_id), code=409)

        try:
            # create Division reference
            objid = id_gen(parent_id=organization_objid)

            if price_list_id is None:
                # get default PriceList
                srv_pl = self.get_service_price_list_default()
                price_list_id = srv_pl.oid
            else:
                # resolve fk price list id
                price_list_id = self.get_service_price_list(price_list_id).oid

            div = self.manager.add_division(objid, name, organization_id, default_service_status,
                                            desc, version, contact, email, postaladdress, active=True)
            # Aggiunge entry nella tabella di collegamento con il price_list
            self.manager.add_divs_prices(div.id, price_list_id)

            # create object and permission
            api_div = ApiDivision(self, oid=div.id, objid=div.objid, name=div.name, active=div.active,
                                  desc=div.desc, model=div)
            api_div.register_object(objid.split('//'), desc=name)

            api_div.update_status(1)  # ACTIVE

            # post create
            api_div.post_create(batch=False, **kvargs)

            return div.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiDivision', op='view')
    def get_division(self, oid, *args, **kvargs):
        """Get single division.

        :param oid: entity model id, name or uuid
        :return: Division
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        division = self.get_entity(ApiDivision, Division, oid, *args, **kvargs)
        return division

    @trace(entity='ApiDivision', op='view')
    def get_divisions(self, *args, **kvargs):
        """Get divisions.

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of divisions for a organization
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_divisions(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('organization_id', self.get_organization, kvargs)

        res, total = self.get_paginated_entities(ApiDivision, get_entities,
                                                 customize=customize, *args, **kvargs)
        return res, total

    def update_division(self, oid, data, *args, **kvargs):
        '''
            :param oid: entity model id, name or uuid
            :param data: dict with other param (ex: price_list_id)
            :return division
        '''
        division = self.get_division(oid)
        data = data.get('division',{})
        data.pop("name",None)
        data.pop('price_list_id', None)
        # self.logger.warn(old_price_list_id)
        # self.resolve_fk_id('price_list_id', self.get_service_price_list, data, 'price_list_id')
        # self.logger.warn(data)
        # #insert record division-price_list
        # # price_list_id = data.get('division').get('price_list_id')
        # price_list_id = data.pop('price_list_id', None)
        # self.logger.warn(price_list_id)
        # if price_list_id is not None:
        #     self.manager.update_divs_prices(division.model.id, price_list_id, date.today())
        division = division.update(**data)

        return division

    ############################
    # Account Capability
    ############################
    @trace(entity='ApiAccountCapability', op='insert')
    def add_capability(self, name, desc='', version='1.0', *args, **kvargs):
        """Create a new Account Capability

        :param name:
        :param desc:
        :param version:
        :param args:
        :param kvargs:
        :return:
        """
        # check authorization
        self.check_authorization(ApiAccountCapability.objtype, ApiAccountCapability.objdef, None, 'insert')

        params = kvargs.get('params', '{}')
        status_id = kvargs.get('status', SrvStatusType.ACTIVE)

        self.logger.debug('Account Capability adding args %s' % (str(args)))
        self.logger.debug('Account Capability adding kvargs %s' % (str(kvargs)))
        self.logger.debug('Account Capability adding name %s , version %s' % (name, version))

        # check authorization
        # self.can('insert', ApiAccountCapability.objtype, ApiAccountCapability.objdef)

        # check account with the same name already exists
        _, tot = self.get_capabilities(name=name, filter_expired=False, authorize=False)
        if tot > 0:
            raise QueryError('Account Capability %s already exists ' % name, code=409)

        try:
            # create Account reference
            objid = id_gen()
            # def add_capability(self, objid, name, status, desc, version, params ):
            capability = self.manager.add_capability(objid, name, status_id, desc, version, params)

            # create object and permission for Account
            api_capability = ApiAccountCapability(self, oid=capability.id, objid=capability.objid,
                                                  name=capability.name, active=capability.active,
                                                  desc=capability.desc,
                                                  model=capability)
            api_capability.register_object(objid.split('//'), desc=name)

            api_capability.update_status(SrvStatusType.ACTIVE)  # ACTIVE

            return capability.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiAccountCapability', op='view')
    def get_capability(self, oid):
        """Get single Account Capability.

        :param oid: entity model id, name or uuid
        :return: Account Capability
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #filter_expired=False
        # check authorization
        # self.can('view', ApiAccountCapability.objtype, ApiAccountCapability.objdef)

        capability = self.get_entity(ApiAccountCapability, AccountCapability, oid, for_update=True)

        return capability

    @trace(entity='ApiAccountCapability', op='delete')
    def delete_capability(self, oid):
        """Delete a single Account Template.

        :param oid: entity model id, name or uuid
        :return: Account
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        #filter_expired=False
        # check authorization
        # self.can('delete', ApiAccountCapability.objtype, ApiAccountCapability.objdef)
        ### TODO
        ### problema avendo impostato l'autorizzazione nei parametri di thread in operation.authorize  rischiamo di
        ### ripetere il check diverse volte
        # capability = self.get_entity(ApiAccountCapability, AccountCapability, oid, authorize=False, for_update=True)
        capability = self.get_entity(ApiAccountCapability, AccountCapability, oid, for_update=True)
        capability.update_status(SrvStatusType.DELETED)
        resp = capability.delete(soft=True)
        return resp

    @trace(entity='ApiAccountCapability', op='view')
    def get_capabilities(self, *args, **kvargs):
        """Get accounts.

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of divisions for a organization
        :raises ApiManagerError: if query empty return error.
        """
        # self.can('view', ApiAccountCapability.objtype, ApiAccountCapability.objdef)

        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_capabilities(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('division_id', self.get_division, kvargs)

        res, total = self.get_paginated_entities(ApiAccountCapability, get_entities, customize=customize, *args, **kvargs)
        return res, total

    ############################
    ###      Account         ###
    ############################
    @trace(entity='ApiAccount', op='insert')
    def add_account(self, name, division_id, contact='', desc='', version='1.0', note=None, email=None,
                    email_support=None, email_support_link=None, managed=True, price_list_id=None, acronym=None,
                    *args, **kvargs):
        """Add account

        :param name:
        :param division_id:
        :param contact:
        :param desc:
        :param version:
        :param note:
        :param email:
        :param email_support:
        :param email_support_link:
        :param managed:
        :param price_list_id:
        :param acronym:
        :param args:
        :param kvargs:
        :return:
        """
        # DANIELA TBD:
        default_service_status = 4

        division = self.get_division(division_id)
        division_objid = division.objid

        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, division_objid, 'insert')

        # check account with the same name already exists in the division
        accounts, tot = self.get_accounts(name=name, division_id=division_id, filter_expired=False, authorize=False)
        if tot > 0:
            raise QueryError('Account %s already exists in division %s' % (name, division_id), code=409)

        try:
            params = {}
            objid = id_gen(parent_id=division_objid)
            params['managed'] = managed
            account = self.manager.add_account(objid, name, division.oid, default_service_status, desc, version,
                                               note,  contact, email, email_support, email_support_link, active=True,
                                               params=params, acronym=acronym)
            # create object and permission for Account
            api_account = ApiAccount(self, oid=account.id, objid=account.objid, name=account.name,
                                     active=account.active, desc=account.desc, model=account)
            api_account.register_object(objid.split('//'), desc=name)

            if price_list_id is not None:
                price_list_id = self.get_service_price_list(price_list_id).oid
                # Aggiunge entry nella tabella di collegamento con il price_list
                self.manager.add_account_prices(account.id, price_list_id)

            api_account.update_status(1)  # ACTIVE

            # post create
            api_account.post_create(**params)

            return account.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiAccount', op='view')
    def get_account_acronym(self, oid, *args, **kvargs):
        """Get account acronym.

        :param oid: entity model id
        :return: Account acronym
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        account = self.manager.get_account_by_pk(oid)
        managed = account.params.get('managed', False)
        acronym = ''
        if managed is True and account.acronym != '':
            acronym = '-%s' % account.acronym
        return acronym

    @trace(entity='ApiAccount', op='view')
    def get_account(self, oid: Union[int, str], *args, **kvargs):
        """Get single Account.

        :param oid: entity model id, name or uuid
        :return: Account
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        account: ApiAccount = self.get_entity(ApiAccount, Account, oid, *args, **kvargs)
        services: int = self.manager.count_service_instances_by_accounts(accounts=[account.oid])
        account.services = services.get(account.oid, {})
        return account

    @trace(entity='ApiAccount', op='view')
    def get_accounts(self, *args, **kvargs):
        """Get accounts.

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of divisions for a organization
        :raises ApiManagerError: if query empty return error.
        """
        # TODO verifica se c'e' il controllo dei permessi
        def get_entities(*args, **kvargs) -> Tuple[List[ApiAccount], int]:
            entities, total = self.manager.get_accounts(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('division_id', self.get_division, kvargs)

        res, total = self.get_paginated_entities(ApiAccount, get_entities, customize=customize, *args, **kvargs)
        return res, total

    def count_service_instances_by_accounts(self, accounts=None):
        """Count service instances by accounts

        :param accounts: list of accounts
        :return:
        """
        services = self.manager.count_service_instances_by_accounts(accounts)
        self.logger.debug('Count service instances by accounts %s: %s' % (accounts, truncate(services)))
        return services

    @transaction
    def update_account(self, oid, data, *args, **kvargs):
        """Update account

        :param oid: entity model id, name or uuid
        :param data: dict with other param (ex: price_list_id)
        :return account
        """
        account = self.get_account(oid)
        price_list_id = data.pop('price_list_id', None)
        account = account.update(**data)
        if price_list_id is not None:
            self.manager.update_account_prices(oid, price_list_id, date.today())
        return account

    ##########################################
    ### Applied bundle for account        ###
    ##########################################
    @trace(entity='ApiAccount', op='view')
    def get_account_applied_bundle(self, oid, bundle_id, *args, **kvargs):
        """Get list of applied bundle for an account.

        :param oid: account like name
        :param bundle_id: account identifier
        :return: Get a applied bundle
        :raises ApiManagerError: if query empty return error.
        """

        # check entity account and permission
        account = self.get_entity(ApiAccount, Account, oid)

        res = self.manager.get_applied_bundle(account_id=account.oid, id=bundle_id)
        bundle = {}
        # TDB: controllare sessione DB.
        if res is not None:
            bundle['id'] = res.id
            bundle['metric_type_id'] = res.metric_type.uuid
            bundle['start_date'] = format_date(res.start_date, "%Y-%m-%d")
            if res.end_date is not None:
                res.end_date += timedelta(days=-1)
                bundle['end_date'] = format_date(res.end_date,"%Y-%m-%d" )

        return bundle

    @trace(entity='ApiAccount', op='view')
    def get_account_applied_bundles(self, oid, *args, **kvargs):
        """Get list of applied bundle for an account.

        :param id: name like [optional]
        :return: List of applied bundle
        :raises ApiManagerError: if query empty return error.
        """
        # check entity account and permission
        account = self.get_entity(ApiAccount, Account, oid)

        entities = self.manager.get_applied_bundle_list(account_id=account.oid, *args, **kvargs)

        # TDB: controllare sessione DB.
        for e in entities:
            if e.end_date is not None:
                e.end_date += timedelta(days=-1)
        return entities

    @trace(entity='ApiAccount', op='update')
    @transaction
    def set_account_applied_bundle(self, oid, bundles=None):
        """ """
        if bundles is None:
            bundles = []
        account = self.get_entity(ApiAccount, Account, oid)
        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')
        try:
            for bundle in bundles:
                # get metric type object
                srv_mt = self.get_service_metric_type(bundle.get('metric_type_id'))
                # check if is not of type consume
                if srv_mt.metric_type == MetricType.CONSUME:
                    raise ApiManagerWarning ('applied bundle %s has a wrong metric type' % srv_mt.id)

                start_date = datetime.strptime(bundle.get('start_date'), '%Y-%m-%d')
                end_date = None
                if bundle.get('end_date', None) is not None:
                    end_date = datetime.strptime(bundle.get('end_date'), '%Y-%m-%d')
                    end_date += timedelta(days=1)

                #check if alreday exist the bundle to insert
                applied_bundles = self.manager.get_applied_bundle_list(account_id=account.oid, metric_type_id=srv_mt.oid, start_date=start_date, end_date=end_date)
                if len(applied_bundles) > 0:
                    self.logger.warning('bundle %s already exist' % bundle)
                    break

                new_applied_bundle = AppliedBundle(account_id=account.oid,
                                metric_type_id=srv_mt.oid,
                                start_date=start_date,
                                end_date=end_date,
                                )

                self.manager.add(new_applied_bundle)
            return True
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)



    @trace(entity='ApiAccount', op='update')
    @transaction
    def update_account_applied_bundle(self, oid, data, *args, **kvargs):
        """ """
        account = self.get_entity(ApiAccount, Account, oid)
        data = data.get('bundle')

        # check authorization
        self.check_authorization(ApiAccount.objtype,
                                 ApiAccount.objdef,
                                 account.objid, 'update')

        try:
            bundle = self.manager.get_applied_bundle(data.get('id'))
            if bundle is not None:
                    end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
                    end_date += timedelta(days=1)
                    bundle.end_date = end_date
                    self.manager.update(bundle)

            return bundle.id
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiAccount', op='delete')
    @transaction
    def unset_account_applied_bundle(self, oid, bundle_id, all=False, *args, **kvargs):
        """ """
        account = self.get_entity(ApiAccount, Account, oid)
        # check authorization
        self.check_authorization(ApiAccount.objtype,
                                 ApiAccount.objdef,
                                 account.objid, 'delete')
        try:
            res = self.manager.delete_applied_bundle(account_id=account.oid, id=bundle_id)
            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)


    def get_report_cost_by_account(self, account_id, oid):
        """Get report cost by account.

        :param account_id: account id or uuid
        :param request_date: request date of istant consume
        :return: array of instant consume from account id
        :raises ApiManagerError: if query empty return error.
        """
        account = self.get_entity(ApiAccount, Account, account_id)
        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')

        try:
            rc = self.manager.get_report_cost_by_account(account_id, oid)
            return rc
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def get_report_list_by_account(self, account_ids, *args, **kvargs):
        """Get report cost by account.

        :param account_ids: array of account id or uuid
        :param request_date: request date of istant consume
        :return: array of instant consume from account id
        :raises ApiManagerError: if query empty return error.
        """
        # TODO (g) authorization check should be optional
        account_id_list = []
        for id in account_ids:
            account = self.get_entity(ApiAccount, Account, id)
            # check authorization
            self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')
            account_id_list.append(account.oid)

        try:
            rc, total = self.manager.get_paginated_report_costs(account_id_list=account_id_list, *args, **kvargs)
            return rc, total
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def get_report_cost_monthly_by_account(self, oid, period, plugin_name=None, *args, **kvargs):
        """ Get an aggregate ReportCost by month

        :param account_id:
        :param year_month: aggregation month
        :param plugin_name: plugin name
        :return: list of ReportCost
        """
        account = self.get_entity(ApiAccount, Account, oid)
        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')

        return self.manager.get_report_cost_monthly_by_account(oid, period, plugin_name)

    def get_report_cost_monthly_by_accounts(self, account_ids, start_date, end_date, plugin_name=None, *args, **kvargs):
        """ Get an aggregate ReportCost by month

        :param account_ids:  array of account id
        :param year_month: aggregation month
        :param plugin_name: plugin name
        :return: list of ReportCost
        """

        account_id_list = []
        for id in account_ids:
            account = self.get_entity(ApiAccount, Account, id)
            # check authorization
            self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')
            account_id_list.append(account.oid)

        try:
            rcs = self.manager.get_report_cost_monthly_by_accounts(account_id_list, start_date=start_date, end_date=end_date, plugin_name=plugin_name)
            return rcs
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def get_cost_by_account_on_period(self, oid, start_period, end_period=None, plugin_name=None, reported=None, *args, **kvargs):
        """ Get an aggregate ReportCost by month

        :param account_id:
        :param year_month: aggregation month
        :param plugin_name: plugin name
        :return: list of ReportCost
        """
        account = self.get_entity(ApiAccount, Account, oid)
        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')

        return self.manager.get_cost_by_authority_on_period(start_period, period_end = end_period,
                            account_id=oid, plugin_name=plugin_name, reported=reported)


    def set_reported_reportcosts(self, oid, period_start=None, period_end=None, report_date=None):
        if report_date is None:
            report_date = date.today()
        account = self.get_entity(ApiAccount, Account, oid)
        # check authorization
        self.check_authorization(ApiAccount.objtype, ApiAccount.objdef, account.objid, 'use')

        try:
            total = self.manager.update_report_costs(account.oid, period_start, period_end, report_date=report_date)
            return total
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    def set_unreported_reportcosts(self, oid, period_start=None, period_end=None):
        return self.set_reported_reportcosts(oid, period_start, period_end, report_date=None)

    ############################
    ###      Agreement       ###
    ############################


    @trace(entity='ApiAgreement', op='insert')
    def add_agreement(self, name, division_id, year,
                desc='',
                amount=0.00,
                agreement_date_start=None, agreement_date_end=None, *args, **kvargs):
        """ """

        default_service_status_id = 1

        # check authorization on Division
        division = self.get_division(division_id)
        division_objid = division.objid
        self.check_authorization(ApiDivision.objtype,
                                 ApiDivision.objdef,
                                 division_objid, 'use')

        # check authorization on Division
        wallet = self.manager.get_wallet_by_year(division_id, year)

        if wallet is None:
            # add Waller on Year
            uuid = self.add_wallet(name, division_id, year, desc='Wallet year %s' % year)
            wallet = self.get_wallet(uuid)
            wallet_id = wallet.oid
        else:
            wallet_id = wallet.id

        if wallet is None:
            raise ApiManagerWarning('Could not create the Wallet for division %s ' % division_id)

        wallet_objid = wallet.objid
        wallet = self.get_wallet(wallet_id)
        self.check_authorization(ApiWallet.objtype,
                                 ApiWallet.objdef,
                                 wallet_objid, 'use')
        try:
            # create  Agreement
            objid = id_gen(parent_id=wallet_objid)
            agreement = self.manager.add_agreement(
                objid, name, wallet_id,
                service_status_id=default_service_status_id,
                desc=desc,version='1.0',
                amount=amount,
                agreement_date_start=agreement_date_start,
                agreement_date_end=agreement_date_end, active=True)

            # create object and permission for Wallet
            ApiAgreement(self, oid=agreement.id).register_object(objid.split('//'), desc=name)
            return agreement.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiAgreement', op='view')
    def get_agreement(self, oid, authorize=True):
        """Get agreement.

        :param oid: entity model id, name or uuid
        :return: Agreement
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        agreement = ApiController.get_entity(self, ApiAgreement, Agreement, oid, authorize)
        return agreement

    @trace(entity='ApiAgreement', op='view')
    def get_agreements(self, *args, **kvargs):
        """Get Agreements.

        :param page: list page to show [default=0]
        :param size: number of elements to show for page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Agreements
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_agreements(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        self.resolve_fk_id('wallet_id', self.get_wallet, kvargs)
        self.resolve_fk_id('division_id', self.get_division, kvargs)

        res, total = self.get_paginated_entities(ApiAgreement, get_entities,
                                                 customize=customize, *args, **kvargs)
        return res, total

    ############################
    ###      Wallet          ###
    ############################
    @trace(entity='ApiWallet', op='insert')
    def add_wallet(self, name, division_id, year,
                 desc='', version='1.0', capital_total=0.00,
                 capital_used=0.00, evaluation_date=None, active=True):
        """ """

        default_service_status_id = 1

        # check authorization
        division= self.get_division(division_id)
        division_objid = division.objid

        self.check_authorization(ApiWallet.objtype,
                                 ApiWallet.objdef,
                                 division_objid, 'insert')
        try:
            # create  Wallet
            objid = id_gen(parent_id=division.objid)
            wallet = self.manager.add_wallet(
                 objid,
                 name,
                 division_id,
                 year,
                 default_service_status_id,
                 desc=desc, version=version,
                 capital_total=capital_total,
                 capital_used=capital_used,
                 evaluation_date=evaluation_date, active=True
                 )

            # create object and permission for Wallet
            ApiWallet(self, oid=wallet.id).register_object(objid.split('//'), desc=name)
            return wallet.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiWallet', op='view')
    def get_wallet(self, oid, authorize=True):
        """Get wallet.

        :param oid: entity model id, name or uuid
        :return: Wallet
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        wallet= ApiController.get_entity(self, ApiWallet,
                                         Wallet, oid, authorize)
        return wallet

    @trace(entity='ApiWallet', op='view')
    def get_wallets(self, *args, **kvargs):
        """Get Wallets.

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Wallet
        :raises ApiManagerError: if query empty return error.
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get_wallets(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        res, total = self.get_paginated_entities(ApiWallet, get_entities,
                                                 customize=customize, *args, **kvargs)
        return res, total

    @trace(entity='ApiWallet', op='view')
    def get_wallet_by_year(self, division_id, year):
        return self.manager.get_wallet_by_year(division_id, year)

    ############################
    ###    ServiceCatalog    ###
    ############################
    @trace(entity='ApiServiceCatalog', op='view')
    def get_service_catalog(self, oid)-> ApiServiceCatalog:
        """Get single ServiceCatalog

        :param oid: entity model id, uuid
        :return: ServiceCatalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        srv_cat = self.get_entity(ApiServiceCatalog, ServiceCatalog, oid)
        return srv_cat

    @trace(entity='ApiServiceCatalog', op='insert')
    def add_service_catalog(self, name='', desc='', active=True, version='1.0', *args, **kvargs)-> str:
        """Add service catalog

        :param name:
        :param desc:
        :param active:
        :param version:
        :return: uuid of new created catalog
        """
        # check already exixst
        cats, tot = self.get_service_catalogs(name=name, filter_expired=False)
        if tot > 0:
            self.logger.error('Service catalog %s already exists' % name, exc_info=True)
            raise ApiManagerError('Service catalog %s already exists' % name, code=409)

        # check authorization
        self.check_authorization(ApiServiceCatalog.objtype, ApiServiceCatalog.objdef, None, 'insert')
        try:
            # create service catalog  reference
            objid = id_gen()
            srv_cat = ServiceCatalog(objid=objid, name=name, desc=desc, active=active, version=version)
            cat = self.manager.add(srv_cat)

            # create object and permission for Account
            api_cat = ApiServiceCatalog(self, oid=cat.id, objid=cat.objid, name=cat.name, active=cat.active,
                                        desc=cat.desc, model=cat)
            api_cat.register_object(objid.split('//'), desc=name)

            # api_cat.update_status(1) # ACTIVE

            # post create
            api_cat.post_create(batch=False, **kvargs)

            return cat.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(entity='ApiServiceCatalog', op='view')
    def get_service_catalogs(self, *args, **kvargs):
        """Get ServiceCatalog.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceCatalog
        :raises ApiManagerError: if query empty return error.
        """
        def recuperaServiceCatalogs(*args, **kvargs):
            entities, total = self.manager.get_paginated_service_catalogs(*args, **kvargs)
            return entities, total

        def customize(res, *args, **kvargs):
            return res

        res, total = self.get_paginated_entities(ApiServiceCatalog, recuperaServiceCatalogs,
                                                 customize=customize, *args, **kvargs)

        return res, total
        pass

    @trace(entity='ApiServiceCatalog', op='view')
    def get_service_catalog_defs(self, *args, **kvargs):
        """Get ServiceCatalog Defs.

        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of ServiceCatalog
        :raises ApiManagerError: if query empty return error.
        """
        # def recuperaServiceCatalogs(*args, **kvargs):
        #     entities, total = self.manager.get_paginated_service_catalogs(*args, **kvargs)
        #     return entities, total

        # def customize(res, *args, **kvargs):
        #     return res

        # res, total = self.get_paginated_entities(ApiServiceCatalog, recuperaServiceCatalogs,
        #                                          customize=customize, *args, **kvargs)

        # return res, total
        pass

    @trace(entity='ApiServiceCatalog', op='update')
    def add_service_catalog_def(self, catalog_oid, def_oids) -> List[str]:
        """Add some service definitions to a catalog

        :param catalog_oid: the catalog oid
        :param def_oids: list of definitions id
        :return: list of definitions id
        """
        # check authorization
        catalog = self.get_service_catalog(catalog_oid)
        self.check_authorization(ApiServiceCatalog.objtype, ApiServiceCatalog.objdef, catalog.objid, 'update')

        # check authorization and create list of id
        res = []
        for def_oid in def_oids:
            definition = self.get_service_def(def_oid)
            res1 = self.manager.add_service_catalog_def(catalog.model, definition.model)
            res.append(res1)
            self.logger.debug('Add service definition %s to service catalog %s' % (def_oid, catalog_oid))

        return res

    @trace(entity='ApiServiceCatalog', op='delete')
    def delete_service_catalog_def(self, catalog_oid, def_oids):
        """delete some service definitions to a catalog

        :param catalog_oid: the catalog oid
        :param def_oids: list of definitions id
        :return: list of definitions id
        """
        # check authorization
        catalog = self.get_service_catalog(catalog_oid)
        self.check_authorization(ApiServiceCatalog.objtype, ApiServiceCatalog.objdef, catalog.objid, 'delete')

        # check authorization and create list of id
        res = []
        for def_oid in def_oids:
            definition = self.get_service_def(def_oid)
            res1 = self.manager.delete_service_catalog_def(catalog.model, definition.model)
            res.append(res1)
            self.logger.debug('Delete service definition %s from service catalog %s' % (def_oid, catalog_oid))

        return res

    ############################
    ####  tags               ###
    ############################
    @trace(entity='ApiServiceTag', op='view')
    def get_tag(self, oid, authorize=True):
        """Get single tag.

        :param oid: entity model id or name or uuid
        :param authorize: if True check authorization
        :return: ApiServiceTag
        :raise ApiManagerError:
        """
        return ApiController.get_entity(self, ApiServiceTag, ServiceTag, oid)

    @trace(entity='ApiServiceTag', op='view')
    def get_service_tags_with_instance(self, *args, **kvargs):
        """Get service tags with tagged service instance

        :param value_list: tag value list [optional]
        :param service_list: list of services instances uuid [optional]
        :param plugintype_list: list of plugin type name [optional]
        :param account_id_list: list of account uuid [optional]
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: :py:class:`ApiServiceTag`
        :raise ApiManagerError:
        """
        def get_entities(*args, **kvargs):
            # find id from uuid
            account_id_list = kvargs.get('account_id_list', None)
            accounts: List[ApiAccount] = []
            if account_id_list is not None:
                for account_id in account_id_list:
                    accounts.append(self.get_account(account_id).oid)
                kvargs['account_id_list'] = accounts

            # get filter field
            tags, total = self.manager.get_service_tags_with_instance(*args, **kvargs)

            return tags, total

        res, total = ApiController.get_paginated_entities(self, ApiServiceTag, get_entities, *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceTag', op='view')
    def get_tags(self, *args, **kvargs):
        """Get tags.

        :param value: tag value [optional]
        :param value_list: tag value list [optional]
        :param service: service id, uuid [optional]
        :param service_list: service id, uuid list[optional]
        :param link: link id, uuid or name [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: :py:class:`ApiServiceTag`
        :raise ApiManagerError:
        """
        def get_entities(*args, **kvargs):
            # get filter field
            service = kvargs.get('service', None)
            service_list = kvargs.get('service_list', None)
            link = kvargs.get('link', None)

            # search tags by service
            if service is not None:
                # if match('[\-\w\d]+', str(service)):
                #     kvargs['service'] = service
                # else:
                kvargs['service'] = self.get_service_instance(service).oid
                tags, total = self.manager.get_service_tags(*args, **kvargs)
            elif service_list is not None and len(service_list) > 0:
                kvargs['service_list'] = tuple(service_list)
                tags, total = self.manager.get_service_tags(*args, **kvargs)

            # search tags by link
            elif link is not None:
                kvargs['link'] = self.get_link(link).oid
                tags, total = self.manager.get_link_tags(*args, **kvargs)

            # get all tags
            else:
                tags, total = self.manager.get_tags(*args, **kvargs)

            return tags, total

        res, total = ApiController.get_paginated_entities(self, ApiServiceTag, get_entities, *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceTag', op='view')
    def get_tags_occurrences(self, *args, **kvargs):
        """Get tags occurrences

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]

        :return:

            :py:class:`list` of :py:class:`ApiServiceTagOccurrences`

        :raise ApiManagerError:
        """

        def get_entities(*args, **kvargs):
            tags, total = self.manager.get_tags(*args, **kvargs)
            return tags, total

        def customize(res, *args, **kvargs):
            for item in res:
                item.services = item.model.services
                item.links = item.model.links
            return res

        res, total = ApiController.get_paginated_entities(self, ApiServiceTag, get_entities, customize=customize,
                                                          *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceTag', op='insert')
    def add_tag(self, value=None, account=None):
        """Add new tag.

        :param value: tag value
        :param account: account id or uuid
        :param authorize: if True check authorization
        :return: tag uuid
        :raise ApiManagerError:
        """
        account = self.get_account(account)

        # check tag already exists
        tags, tot = self.get_tags(value=value)
        if tot > 0:
            raise ApiManagerError('tag %s already exist' % value)

        # check authorization
        if operation.authorize is True:
            self.check_authorization(ApiServiceTag.objtype, ApiServiceTag.objdef, account.objid, 'insert')

        try:
            objid = '%s//%s' % (account.objid, id_gen())
            tag = self.manager.add_tag(value, objid)

            # add object and permission
            ApiServiceTag(self, oid=tag.id).register_object(objid.split('//'), desc=value)

            self.logger.debug('Add new tag: %s' % value)
            return tag.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=400)

    # #
    # # tags instance
    # #
    # @trace(entity='ApiServiceInstance', op='update')
    # def create_service_tag(self, instance, account_id, value, inst_tag=None):
    #     """Create a set of tag for a specific instance service
    #
    #     :param instance: tag value
    #     :param account: account id,uuid
    #     :param value: str tag value
    #     :param authorize: if True check authorization
    #     :return: tag uuid if operation is successful
    #     :rtype: str
    #     :raises ApiManagerError
    #     """
    #     tag = inst_tag
    #
    #     # check authorization
    #     instance.verify_permisssions('update')
    #
    #     # get tag
    #     if tag is None:
    #         try:
    #             tag = self.get_tag(value)
    #         except ApiManagerError as ex:
    #             # tag not found create it
    #             self.add_tag(value=value, account=account_id)
    #             tag = self.get_tag(value)
    #
    #     # create tag for instance
    #     res = self.manager.add_service_tag(instance.model, tag.model)
    #
    #     if res is True and instance.resource_uuid is not None:
    #         # call Plugin to create tag also for related instance resource
    #         plugin = ApiServiceType(self).instancePlugin(instance.uuid)
    #         res = plugin.create_resource_tag(instance, instance.resource_uuid, tag.name)
    #
    #     self.logger.info('Add tag %s to service %s: %s' % (value, instance.name, res))
    #
    #     return res
    #
    # @trace(entity='ApiServiceInstance', op='delete')
    # def delete_service_tag(self, instance, account_id, value,  authorize=True):
    #     """create a set of tag for a specific instance service
    #
    #     :param instance: tag value
    #     :param account_id: account id,uuid
    #     :param value: str tag value
    #     :param authorize: if True check authorization
    #     :return: tag uuid if operation is successful
    #     :rtype: str
    #     :raises ApiManagerError
    #     """
    #     # check authorization
    #
    #     AssertUtil.assert_is_not_none(instance, 'instance is None')
    #     res = instance.remove_tag(value)
    #
    #     if res is True and instance.resource_uuid is not None:
    #         plugin = ApiServiceType(self).instancePlugin(instance.uuid)
    #         res = plugin.delete_resource_tag(instance, instance.resource_uuid, value)
    #
    #     return res

    ############################
    # links
    #
    @trace(entity='ApiServiceInstanceLink', op='view')
    def get_link(self, oid, authorize=True):
        """Get single link.

        :param oid: entity model id or name or uuid
        :param authorize: if True check authorization
        :return: ApiServiceInstanceLink
        :raise ApiManagerError:
        """
        return ApiController.get_entity(self, ApiServiceInstanceLink, ServiceLink, oid)

    @trace(entity='ApiServiceInstanceLink', op='view')
    def get_links(self, *args, **kvargs):
        """Get links.

        :param start_service: start service id or uuid [optional]
        :param end_service: end service id or uuid [optional]
        :param service: service id or uuid [optional]
        :param type: link type [optional]
        :param servicetags: list of tags. All tags in the list must be met [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: :py:class:`list` of :py:class:`ApiServiceInstanceLink`
        :raise ApiManagerError:
        """

        def get_entities(*args, **kvargs):
            # get filter field
            start_service = kvargs.pop('start_service', None)
            end_service = kvargs.pop('end_service', None)
            service = kvargs.pop('service', None)

            # get all links
            if end_service is not None:
                kvargs['end_service'] = self.get_service_instance(end_service).oid
            if start_service is not None:
                kvargs['start_service'] = self.get_service_instance(start_service).oid
            if service is not None:
                kvargs['service'] = self.get_service_instance(service).oid
            links, total = self.manager.get_links(*args, **kvargs)

            return links, total

        res, total = ApiController.get_paginated_entities(self, ApiServiceInstanceLink, get_entities, *args, **kvargs)
        return res, total

    @trace(entity='ApiServiceInstanceLink', op='insert')
    def add_link(self, name=None, type=None, account=None, start_service=None, end_service=None, attributes=None):
        """Add new link.

        :param name: link name
        :param type: link type
        :param account: account id or uuid
        :param start_service: start service reference id, uuid
        :param end_service: end service reference id, uuid
        :param attributes: link attributes [default={}]
        :param authorize: if True check authorization
        :return: link uuid
        :raise ApiManagerError:
        """
        if attributes is None:
            attributes = {}
        account = self.get_account(account)

        if self.manager.exist_entity(ServiceLink, name) is True:
            raise ApiManagerError('link %s already exists' % name)

        # check authorization
        if operation.authorize is True:
            self.check_authorization(ApiServiceInstanceLink.objtype, ApiServiceInstanceLink.objdef, account.objid,
                                     'insert')

        # get services
        start_service_id = self.get_service_instance(start_service).oid
        end_service_id = self.get_service_instance(end_service).oid

        try:
            objid = '%s//%s' % (account.objid, id_gen())

            attributes = jsonDumps(attributes)
            link = self.manager.add_link(objid, name, type, start_service_id, end_service_id, attributes=attributes)

            # add object and permission
            ApiServiceInstanceLink(self, oid=link.id).register_object(objid.split('//'), desc=name)

            self.logger.debug('Add new link: %s' % name)
            return link.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=400)

    ############################
    # bpmn user task
    #
    @trace(entity='ApiAccount', op='view')
    def account_user_task_list(self, oid):
        """Get the user task list pending for the service instance
        """
        account = self.get_entity(ApiAccount, Account, oid, authorize=True)
        res = self.module.api_manager.camunda_engine.tasks(account_id= account.uuid)
        return res

    @trace(entity='ApiServiceInstance', op='view')
    def serviceinstance_user_task_list(self, oid):
        """Get the user task list pending for the service instance
        """
        service = self.get_entity(ApiServiceInstance, ServiceInstance, oid, authorize=True)
        res = self.module.api_manager.camunda_engine.tasks(instance_id= service.uuid)
        return res

    @trace(entity='ApiServiceInstance', op='view')
    def user_task_detail(self, service_oid,  task_id=None, execution_id=None):
        """ Gets user task detail
        """
        inst = self.get_service_instance(service_oid)
        self.check_authorization(ApiServiceInstance.objtype,
                                 ApiServiceInstance.objdef,
                                 inst.objid, 'view')
        res = self.module.api_manager.camunda_engine.task_localvariables(task_id=task_id, execution_id=execution_id)
        return res

    @trace(entity='ApiServiceInstance', op='update')
    def complete_user_task(self, service_oid, task_id, variables ):
        """ Gets user task detail
        """
        inst = self.get_service_instance(service_oid)
        self.check_authorization(ApiServiceInstance.objtype,
                            ApiServiceInstance.objdef,
                            inst.objid, 'update')

        res = self.module.api_manager.camunda_engine.task_complete(task_id, variables)
        return res


    def get_empty_portal_user_services_structure(self):

        return {
        'user_role' : '',
        'org_id' : '',
        'org_name' : '',
        'org_desc' : '',
        'org_uuid' : '',
        'org_id' : '',
        'div_name' : '',
        'div_desc' : '',
        'div_uuid' : '',
        'account_id' : '',
        'account_name' : '',
        'account_desc' : '',
        'account_uuid' : '',
        'catalog_id' : '',
        'catalog_name' : '',
        'catalog_desc' : '',
        'catalog_uuid' : '',
        }

    def __get_user_object_and_role_info(self, object, prefix):
        """
        """
        item = {}
        item['%s_name' % prefix] = object.name
        item['%s_id' % prefix] = str(object.id)
        item['%s_uuid' % prefix] = object.uuid
        item['%s_desc' % prefix] = object.desc

        return item

    def get_user_object_and_role_info_org(self, objects, roles):
        """
        """
        items = []
        item = {}

        for obj in objects:
            item = self.get_empty_portal_user_services_structure()

            item['user_role'] = roles[str(obj.model.id)]
            info = self. __get_user_object_and_role_info(obj.model, 'org')
            item.update(info)

            items.append(item)


        return items

    def get_user_object_and_role_info_div(self, objects, roles):
        """
        """
        items = []
        item = {}

        for obj in objects:
            item = self.get_empty_portal_user_services_structure()

            item['user_role'] = roles[str(obj.model.id)]
            info_div = self. __get_user_object_and_role_info(obj.model, 'div')
            item.update(info_div)

            info_org = self. __get_user_object_and_role_info(obj.model.organization,  'org')
            item.update(info_org)

            items.append(item)

        return items


    def get_user_object_and_role_info_account(self, objects, roles):
        """
        """
        items = []

        for obj in objects:
            item = self.get_empty_portal_user_services_structure()
            item['user_role'] = roles[str(obj.model.id)]

            info_account = self. __get_user_object_and_role_info(obj.model, 'account')
            item.update(info_account)

            info_div = self. __get_user_object_and_role_info(obj.model.division,  'div')
            item.update(info_div)

            info_org = self. __get_user_object_and_role_info(obj.model.division.organization,  'org')
            item.update(info_org)

            items.append(item)

        return items


    def get_user_object_and_role_info_catalog(self, objects, roles):
        """
        """
        items = []
        for obj in objects:
            item = self.get_empty_portal_user_services_structure()
            item['user_role'] = roles[str(obj.model.id)]

            info_catalog = self. __get_user_object_and_role_info(obj.model, 'catalog')
            item.update(info_catalog)

            items.append(item)

        return items

    def get_user_roles(self, user_name=None, group_name=None, group_id_list=None, size=10):
        """Get list of role for a user
        :return: Dictionary with roles.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """

        data = {}
        if user_name is not None:
            data['user'] = user_name

        if group_name is not None:
            data['group'] = group_name

        if group_id_list is not None:
            data['groups.N'] = group_id_list

        data['size'] = size

        res = self.api_client.admin_request('auth', '/v1.0/nas/roles',
                                                        'get', data=urlencode(data))

        return res

    def get_user_groups(self, user_name, size=10):
        """Get list of user group
        :return: Dictionary with group.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """

        data = {
            'user' : user_name,
            'size' : size,
            'active' : True
        }

        res = self.api_client.admin_request('auth', '/v1.0/nas/groups',
                                                        'get', data=urlencode(data))

        return res

    ###### Service instant consume ########################
    def _format_get_service_instant_consume(self, *args, **kvargs):
        service_plugin_types = self.get_service_plugin_type(authorize=False, category='CONTAINER',
                                                            plugintype=kvargs.get('plugin_name', None))
        # self.logger.warning('service plugin type container list %s' % service_plugin_types)

        service_containers = []
        all_instant_consumes = self.manager.get_service_instant_consumes(*args, **kvargs)

        containers_consumes = {}
        for spt in service_plugin_types:
            plugin_name = spt.get('name', None)
            if plugin_name is not None:
                containers_consumes[plugin_name]=[]

        while len (all_instant_consumes)>0:
            icm = all_instant_consumes.pop()
            conslist = containers_consumes.get(icm['plugin_name'], None)
            if conslist is not None:
                conslist.append(icm)

        # self.logger.warn(containers_consumes)
        for spt in service_plugin_types:
            plugin_name = spt.get('name', None)

            # get service instant consumes for an account and a specific plugin type container
            # instant_consumes = self.manager.get_service_instant_consumes(plugin_name=plugin_name, *args, **kvargs)
            instant_consumes = containers_consumes.get(plugin_name,[])
            # for icm in all_instant_consumes:
            #     if icm['plugin_name'] == plugin_name:
            #         instant_consumes.append(icm)
                    # all_instant_consumes.remove(icm)

            # self.logger.warn(plugin_name)
            # self.logger.warn(instant_consumes)
            container_item = {}
            container_item['plugin_type'] = plugin_name
            container_item['name'] = ''
            container_item['uuid'] = ''
            container_item['status'] = 'INACTIVE'
            container_item['desc'] = ''
            container_item['instances'] = 0

            tot_metrics = []
            for icm in instant_consumes:
                container_item['status'] = 'ACTIVE'
                container_item['extraction_date'] =  format_date(icm.get('creation_date'))
                if icm.get('metric_group_name') == 'instances':
                # if icm.get('metric_group_name') in ()== 'instances':
                    container_item['instances'] = int(icm.get('metric_instant_value'))

                metric_item = {
                    'metric': icm.get('metric_group_name'),
                    'value': icm.get('metric_instant_value'),
                    'unit': icm.get('metric_unit'),
                    'quota': icm.get('metric_value'),
                }
                tot_metrics.append(metric_item)

            container_item['tot_metrics'] = tot_metrics
            service_containers.append(container_item)

        return {'service_container': service_containers, 'extraction_date': format_date(date.today())}

    def get_service_instant_consume_by_nivola (self, *args, **kvargs):
        """
        """
        # get active organizations
        orgs, tot_orgs = self.get_organizations(active=True, filter_expired=False, size=0)
        orgs_list_id = [org.oid for org in orgs]
        self.logger.warning ('orgs_list_id=%s' % orgs_list_id)

        divs, tot_divs = [],0
        if len(orgs_list_id) > 0:
            # get active divisions for organizations
            divs, tot_divs = self.get_divisions(organization_id_list=orgs_list_id, active=True,
                                                filter_expired=False, size=0)
        div_list_id = [div.oid for div in divs]
        self.logger.warning ('divisions_list_id=%s' % div_list_id)

        accounts, tot_accs = [],0
        if len(div_list_id) > 0:
            # get active accounts for division
            accounts, tot_accs = self.get_accounts(divisions_list_id=div_list_id, active=True,
                                                filter_expired=False, size=0)
        account_list_id = [account.oid for account in accounts]
        self.logger.warning ('account_list_id=%s' % account_list_id)

        services = {}
        services ['organizations'] = tot_orgs
        services ['divisions'] = tot_divs
        services ['accounts'] = tot_accs

        if tot_divs == 0 or tot_accs == 0 or tot_orgs == 0:
            services ['service_container'] = []
            services ['extraction_date'] = format_date(date.today())
            return services

        res = self._format_get_service_instant_consume (account_list_id=account_list_id)
        services.update(res)

        return services


    def get_service_instant_consume_by_organization (self, oid=None, *args, **kvargs):
        """
        """
        # get active division for organization
        divs, tot_divs = self.get_divisions(organization_id=self.get_organization(oid).oid,
                                            active=True,filter_expired=False, size=0)
        div_list_id = [div.oid for div in divs]
        self.logger.warning ('divisions_list_id=%s' % div_list_id)

        accounts, tot_accs = [],0
        if len(div_list_id) > 0:
            # get active account for division
            accounts, tot_accs = self.get_accounts(division_id_list=div_list_id,
                                                   active=True,filter_expired=False, size=0)

        account_list_id = [account.oid for account in accounts]
        self.logger.warning ('account_list_id=%s' % account_list_id)

        services = {}
        services ['divisions'] = tot_divs
        services ['accounts'] = tot_accs

        if tot_divs == 0 or tot_accs ==0 :
            services ['service_container'] = []
            services ['extraction_date'] = format_date(date.today())
            return services

        res = self._format_get_service_instant_consume (account_list_id=account_list_id)
        services.update(res)

        return services

    def get_service_instant_consume_by_division (self, oid, *args, **kvargs):
        """
        """
        # get active account for division
        accounts, total = self.get_accounts(division_id=self.get_division(oid).oid,
                                            active=True,filter_expired=False, size=0)
        account_list_id = [account.oid for account in accounts]
        self.logger.warning ('account_list_id=%s' % account_list_id)

        services = {}
        services ['accounts'] = total

        if total == 0:
            services ['service_container'] = []
            services ['extraction_date'] = format_date(date.today())
            return services

        res = self._format_get_service_instant_consume(account_list_id=account_list_id)
        services.update(res)

        return services

    def get_service_instant_consume_by_account(self, oid, plugin_name, *args, **kvargs):
        """
        """
        services = {}
        # get account
        account = self.get_account(oid)

        res = self._format_get_service_instant_consume([account.oid], plugin_name=plugin_name, *args, **kvargs)
        services.update(res)

        return services

    def get_paginated_service_instant_consumes(self, id=None, organization_id=None, division_id=None, account_id=None,
                                               service_instance_id=None, plugin_name=None, *args, **kvargs):
        """Get service instant consumes.

        :param id: filter by service instance consume id [optional]
        :param organization_id: id organization [optional]
        :param division_id: id division [optional]
        :param account_id: id account [optional]
        :param service_instance_id: id service instance [optional]
        :param plugin_name: plugin type name [optional]
        :param organization_list_id: list organization id [optional]
        :param division_list_id: list division id [optional]
        :param account_list_id: list account id [optional]
        :param service_instance_list_id: list service instance id [optional]

        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of service instant consume
        :raises ApiManagerError: if query empty return error.
        """

        res, total = self.manager.get_paginated_service_instant_consumes(id=id, organization_id=organization_id,
                                                division_id=division_id, account_id=account_id,
                                                service_instance_id=service_instance_id, plugin_name=plugin_name,
                                                with_perm_tag=False, *args, **kvargs)

        return res, total


    def get_service_instant_consume(self, *args, **kvargs):
        """Get list of service instant consume.

        :param name: name like [optional]
        :return: List of ServiceInstantConsume
        :raises ApiManagerError: if query empty return error.
        """
        entities = self.manager.get_service_instant_consume_list(*args, **kvargs)
        return entities

    def _format_report_credit_summary(self, account_ids, division_ids, year_month, start_date, end_date):
        """

        :param account_ids:
        :param division_ids:
        :param year_month:
        :param start_date:
        :param end_date:
        :return:
        """
        first_month_str = None
        last_month_str = None
        year = None

        if year_month is not None:
            first_month_str = '%s-01' % year_month
            last_month = parse('%s-01' % year_month) + relativedelta.relativedelta(months=1) - \
                         relativedelta.relativedelta(days=1)
            last_month_str = format_date(last_month, '%Y-%m-%d')
            year = first_month_str.split('-')[0]

        if start_date is not None and end_date is not None:
            first_month_str = format_date(start_date, '%Y-%m-%d')
            last_month_str = format_date(end_date, '%Y-%m-%d')
            year = first_month_str.split('-')[0]

        imp_rendicontato = self.manager.get_cost_by_authority_on_period(
                                    period_start=first_month_str,
                                    period_end=last_month_str,
                                    account_id_list=account_ids,
                                    reported=True)

        imp_non_rendicontato = self.manager.get_cost_by_authority_on_period(
                                    period_start=first_month_str,
                                    period_end=last_month_str,
                                    account_id_list=account_ids,
                                    reported=False)
        imp_iniziale = 0.0
        imp_residuo_pre = 0.0
        residuo_post = 0.0
        if division_ids is not None:
            imp_iniziale = self.manager.get_credit_by_authority_on_year(year=year, division_id_list=division_ids)
            imp_residuo_pre = imp_iniziale - imp_rendicontato
            residuo_post = imp_residuo_pre - imp_non_rendicontato

        credit_summary = {}
        credit_summary['initial'] = imp_iniziale
        credit_summary['accounted'] = imp_rendicontato
        credit_summary['remaining_pre'] = imp_residuo_pre
        credit_summary['consume_period'] = imp_non_rendicontato
        credit_summary['remaining_post'] = residuo_post

        return { 'credit_summary': credit_summary}

    def _format_report_credit_composition(self, division_ids, year_month, start_date, end_date):
        '''
        '''

        first_month_str = None

        if year_month is not None:
            first_month_str = '%s-01' %year_month

        if start_date is not None and end_date is not None:
            first_month_str = format_date(start_date, '%Y-%m-%d')

        year = first_month_str.split('-')[0]

        res, total = self.get_agreements(division_ids=division_ids, year=year)
        self.logger.warning('agreements = %s' % res)

        total_amount = 0.0
        credit_composition = {}
        agreements = []
        for item in res:
            self.logger.warning('agreement item = %s' % item)
            agreement = {}
            agreement['agreement_id'] = item.uuid
            agreement['agreement_date_start'] = item.agreement_date_start
            agreement['agreement_date_end'] = item.agreement_date_end
            agreement['agreement_amount'] = item.amount
            agreement['agreement'] = item.code
            agreements.append(agreement)
            total_amount += item.amount

        credit_composition ['total_amount'] = total_amount
        credit_composition ['agreements'] =  agreements

        return {'credit_composition': credit_composition}

    def _format_report_costcomsume(self, account_ids, year_month, start_date, end_date, report_mode, *args, **kvargs):
        first_month_str = None
        last_month_str = None

        start_period = None
        end_period = None
        if year_month is not None:
            first_month_str = '%s-01' % year_month
            start_period = parse(first_month_str)
            last_month = parse('%s-01' % year_month) + relativedelta.relativedelta(months=1) - \
                         relativedelta.relativedelta(days=1)
            end_period = last_month
            last_month_str = format_date(last_month, '%Y-%m-%d')

        if start_date is not None and end_date is not None:
            first_month_str = format_date(start_date, '%Y-%m-%d')
            last_month_str = format_date(end_date, '%Y-%m-%d')
            start_period = start_date
            end_period = end_date

        plugin_containers = self.manager.get_plugin_type_by_account(account_ids=account_ids,
                                                                    category=SrvPluginTypeCategory.CONTAINER)

        # capabilities = []
        # for a in account_ids:
        #     capabilities.extend(self.get_account(a).model.capabilities_list())
        # self.logger.warning('capabilities=%s' % capabilities)

        imp_periodo = 0.0
        services = []
        for plugin_name in plugin_containers:
            service = {
                'name': plugin_name,
                'plugin_name': plugin_name
            }
            monthly_cost = self.get_report_cost_monthly_by_accounts(account_ids,
                                                                    start_date=first_month_str,
                                                                    end_date=last_month_str,
                                                                    plugin_name=plugin_name)
            sintesi = []
            imp_service = 0.0
            for m in monthly_cost:
                imp_service += m.get('cost', 0.0)
                sintesi.append({
                    'metric_type_id': m.get('metric_type_id',-1),
                    'name': m.get('name', '<unknow>'),
                    'unit': m.get('measure_unit', ''),
                    'qta': m.get('value', 0.0),
                    'amount': m.get('cost', 0.0)
                })

            imp_periodo += imp_service
            service['total'] = imp_service
            service['summary_consume'] = sintesi

            dettaglio = []
            daily_cost, total = [], 0
            if report_mode == __SRV_REPORT_COMPLETE_MODE__:
                daily_cost, total = self.get_report_list_by_account(
                                    account_ids, plugin_name=plugin_name,
                                    period_start=first_month_str, period_end=last_month_str, size = 0)

                period = None
                total_day = 0.0
                day = {}
                metrics = []
                for rc in daily_cost:
                    if period is not None and period != rc.period:
                        day['day'] = '' if period is None else period
                        day['total'] = total_day
                        day['metrics'] = metrics
                        dettaglio.append(day)
                        total_day = 0.0
                        day = {}
                        metrics = []

                    period = rc.period
                    metrics.append({
                        'metric_type_id': rc.metric_type_id,
                        'name': rc.metric_type.name,
                        'unit': rc.metric_type.measure_unit,
                        'qta': rc.value,
                        'amount': rc.cost
                    })

                    total_day += rc.cost

                day['day'] = '' if period is None else period
                day['total'] = total_day
                day['metrics'] = metrics
                dettaglio.append(day)

            service['details'] = dettaglio
            services.append(service)

        res = {
            'date_report': str(date.today()),
            'period': {'start_date': format_date(start_period), 'end_date': format_date(end_period)},
            'amount': imp_periodo,
            'services': services
        }
        return res

    def get_report_costconsume_bynivola (self, year_month, start_date, end_date, report_mode, *args, **kvargs):
        """
        """

        # get active organizations
        orgs, tot_orgs = self.get_organizations(active=True,filter_expired=False,
                                                    size=0)
        orgs_list_id = [org.oid for org in orgs]
        self.logger.warning ('orgs_list_id=%s' % orgs_list_id)

        divs = []
        if len(orgs_list_id) > 0 :
            # get active divisions for organizations
            divs, tot_divs = self.get_divisions(organization_id_list=orgs_list_id,
                                                    active=True, filter_expired=False,
                                                    size=0)
        div_list_id = [div.oid for div in divs]
        self.logger.warning ('divisions_list_id=%s' % div_list_id)

        accounts = []
        if len(div_list_id) > 0 :
            # get active accounts for division
            accounts, tot_accs = self.get_accounts(divisions_list_id=div_list_id,
                                                    active=True, filter_expired=False,
                                                    size=0)

        account_list_id = [account.oid for account in accounts]
        self.logger.warning ('account_list_id=%s' % account_list_id)


        res_report = self._format_report_costcomsume(
            account_list_id, year_month, start_date, end_date, report_mode, *args, **kvargs)

        res_credit_summary = self._format_report_credit_summary(account_list_id, div_list_id, year_month, start_date, end_date)
        res_credit_composition = self._format_report_credit_composition(div_list_id, year_month, start_date, end_date)

        res = {
            'organization': '',
            'organization_id': '',
            'division': '',
            'division_id': '',
            'account': '',
            'account_id': '',
            'postal_address': '',
            'referent': '',
            'email': '',
            'hasvat': False
        }
        res.update(res_report)
        res.update(res_credit_composition)
        res.update(res_credit_summary)

        return res

    def get_cost_by_nivola_on_period(self, start_period, end_period=None,
                plugin_name=None, reported=None, *args, **kvargs):
        """ Get an aggregate ReportCost for Nivola and a specific month

        :param start_period: aggregation start period
        :param end_period: aggregation end period
        :param plugin_name: plugin name
        :param reported: boolean to filter cost reported or unreported
        :return: total cost
        """

        # get active organizations
        orgs, tot_orgs = self.get_organizations(active=True, filter_expired=False, size=0)
        orgs_list_id = [org.oid for org in orgs]

        return self.manager.get_cost_by_authority_on_period(
                                period_start=start_period,
                                period_end=end_period, plugin_name=plugin_name,
                                reported=reported, organization_id_list=orgs_list_id)

    def get_credit_nivola_by_year(self, year):

        # get active organizations
        orgs, tot_orgs = self.get_organizations(active=True, filter_expired=False, size=0)
        orgs_list_id = [org.oid for org in orgs]

        return self.manager.get_credit_by_authority_on_year(year, organization_id_list=orgs_list_id)

    ############################
    ### MonitoringMessage    ###
    ############################
    def compute_monitoring_message (self )-> Tuple[str, str]:
            return self.manager.call_monitoring_proc()

    def get_monitoring_message (self, period:str = None )-> MonitoringMessage :
            return self.manager.monit_message_at(period)
