# Changelog

## Version 1.16.7 (2024-10-03)

Rilascio nuove funzionalità
* Added
  - nuovi parametri opzionali ricevuti i fase di creazione di db postgresql
* Fixed
  - permessi verificati oe job_list
  - fix alert triplet
  - cancellazione dei tags proma della cancellazione deglli account
  - changelog
  - parametri posgresql creando risorsa
  - wip
* Changed
  - check_parent_service aggiunta parametro action per verificare permissi altrii che update
  - disabilitata validazione per pg-extensions
  - parametri ino9ltrati a resource in fase di creazione di dbaas postgresql

## Version 1.16.6 (2024-09-23)
rilascio di correttive

* Added
  - Refactoring tag, unique name for account
  - UpdateAccountServiceInstance Adds tag to all vms, volumes, dbs of the account
  - check case sensitive product code
  - get product code, check in insert
  - service_tag added constraint account
  - rsa key 4096 bit create
  - added nvl-resourceId, nvl-hypervisor in dbaas instances
  - some type hint
* Fixed
  - definitions checks
  - fix db create
  - fix db flavour not updated NSP-3314
  - vm state before create/delete log, monitor instance
* Removed
  - some deprecated code

## Version 1.16.5 (2024-08-07)
rilascio di correttive

* Added
  - refactoringo vsphere dfw rules
* Fixed
  - map[grafana:from version 11 alert notrification doesn't exist!]
  - comment problem monitoring alert
* Changed
  - error message if provider image does not have an availability zone child

## Version 1.16.4 (2024-07-09)
rilascio di correttive

* Fixed
  - missing uuid after account update

## Version 1.16.3 (2024-06-27)
rilascio di correttive

* Added
  - ful version and metadata in db engines list
* Fixed
  - bug when db-instances update

## Version 1.16.2 (2024-06-13)
rilascio di correttive


## Version 1.16.1 (2024-06-04)
rilascio di correttive

* Added
  - account management model, and pods
  - check for capablity  using new attribitess account_type, pods
  - CheckAccount service
  - view for consumes by service
* Fixed
  - minor
  - restore previous api signature for backward compatibility
  - error due to server's name length
  - check definitions in dbaas creation end update

## Version 1.16.0 (2024-03-26)
rilascio di funzionalità

* Added
  - fix log sync user if ldap is none
  - fix delete account expiry date, active
  - fix wrong permission objid that resulted in error while creating account
  - user with taxcode
  - account-closed add param "close_account" to clone account instead delete it
  - Account operator and  Account operator role template permissions while creating accounts
  - vsphere-clone
  - clone swagger definition fix
  - get account deleted, Account is_active
  - get node password
  - Clone minor
  - API clone endpoint
  - Wip clone
  - clone wip
  - Commented obsolete code for linked clone
  - sync user revert per Grafana
  - update swagger users
  - sync_users con nuovo campo ldap di user
  - dbaas check min_ram_size creating db
  - vsphere clone with instanceId of source VM
  - Fix check on last snapshot @see https://jira.csi.it/browse/NSP-2895
  - service metric type hint, log
  - private cload network using vsphere_only
  - blacked
  - headers updated

## Version 1.15.0 (2025-10-12)
rilascio di funzionalità

* Added
  - new metrics collecting logic
  - monitoring alert service
* Fixed
  - minor fixies

## Version 1.14.0 (2023-06-22)
rilascio di funzionalità

* Added
  - method to get avz by site
  - set session for playing a sigle account's role
* Fixed
  - refacoring load balancer
  - service def get require no permissions
  - database name check
  - deregister moinitoring when delete resource
  - refactoring backup
  - check specified volume is at least as big as that of the template whe crating servrs

## Version 1.13.0 (2023-02-24)
rilascio di funzionalità

* Fixed
  - grafana dashboard copy
  - minor fixies

## Version 1.12.0 ()
rilascio di funzionalità

* Added
  - eleasticsearch upgrade
* Fixed
  - security group rule deletion
  - instant consumes
  - error while deleting a sopped server when monitoring is enabled
  - synchronization of account's users in monitoring as a service when user ha no e-mail
  - errors adding account capabilities

## Version v.1.15.3 ()
rilascio di correttive

* Added
  - Added support for mariadb
  - MariaDB nuovo engine
  - add check acronym inactive - account name cannot be changed
  - added org, div roles returne role name
  - account roles get return role name
* Fixed
  - account: fix in delete check service exists in order

  - fix swagger: serviceinsts list/get v1-v2

  - account: in delete check service exists in order

  - fix private cloud
  - account operate did not set OPERATOR
  - fix swagger DescribeVolumeTypesV20ApiResponseSchema
  - dbaas: check min_ram_size creating db

  - commented out  orchestrator_select_types
  - security_group: param orchestrator_select_types

  - vpc, subnet: param orchestrator_select_types

  - vm windows: updated existence check message

  - validate name in org, div, account
  - fix msg account service associated (logging, monitoring)
  - fix delete service: check service_type_plugin to avoid delete different type service

  - fix update service definition: FIX value contains ":"

  - update v_service_instant_consume per fix MonitoringService ACTIVE

## Version 1.11.0 (2022-10-21)
rilascio di funzionalità

* Added
  - now compute instance support static ip passed from api
  - map[add compute instance host_group openstack:bck and nobck]
  - add field nvl_HostGroup in DescribeInstancesV20 api
  - add LoggingServiceAPI, MonitoringSpaceServiceAPI, MonitoringInstanceServiceAPI,
  - add ApiMonitoringService, ApiMonitoringSpace, ApiMonitoringInstance
* Fixed
  - fixed problem with default name of logging space
  - fixed problem with icmp rule in security group
  - fixed problem with instance host_group when show flavor

## Version 1.10.0 (2022-02-11)
rilascio di funzionalità

* Added
  - modified now return 404 if core service is not present when getting or modifying account's attributes
  - add method v2.0/nws/accounts/.../definitions to get which definition are available for the account
  - add AccountServiceDefinition. Now the Account knows which definition can instantiate
  - add DatabaseInstanceV2 create method params Nvl_Options.Postgresql_GeoExtension to manage database options
  - add DatabaseInstanceV2 import api from stack sql v2
  - add InstanceV2 api with porting of the old v1.0 apis
  - add InstanceV2 api get console
  - add VolumeV2 api to manage volume type api update
  - add ComputeInstanceBackupAPI api to manage backup job, restore points and restore [beta]
  - add ComputeVolume pre_import method
  - add ComputeShare label management to get custom svm
  - extend ComputeShare to support ontap share
  - add LoggingServiceAPI, LoggingSpaceServiceAPI, LoggingInstanceServiceAPI,
  - add ApiLoggingService, ApiLoggingSpace, ApiLoggingInstance
  - add database instance mailx configuration and haproxy registration based on definition config
  - add model method get_service_definition_by_config
  - add ComputeVolume check when delete api is invoked. If volume is in-use error is returned
  - update capabilities and account capabilities to support account definitions
* Fixed
  - fixed bug in SecurityGroup set_service_info. It Does not manage icmp sub protocol field
  - fixed api /v2.0/nws/computeservices/instance/describeinstancetypes to support new account service catalog. Now required filter by account
  - fixed api /v2.0/nws/databaseservices/instance/describedbinstancetypes to support new account service catalog Now required filter by account
  - fixed api /v2.0/nws/databaseservices/instance/enginetypes to support new account service catalog Now required filter by account
  - fixed type check in db instance and compute instance
  - volume volumetype is read directly from resource
  - update DBInstanceClass param in api GET. Value is get from resource
  - update instanceType param in api GET. Value is get from resource
  - update Share size param in api GET. Value is get from resource
  - correct bug that blocks old sql stack delete

## Version 1.9.0 (2021-06-11)
rilascio di funzionalità

* Added
  - add service instance set config api
  - add ComputeInstance import
  - add ComputeInstance create from existing volume
  - add ComputeInstance api to add/delete/change password to internal user
  - add ComputeCustomization
  - add ComputeInstance api rebootinstances
  - add ComputeInstance api monitorinstances
  - add ComputeInstance api forwardloginstances
  - add DatabaseInstance db api describedbinstancedb, createdbinstancedb, deletedbinstancedb
  - add DatabaseInstance user api describedbinstanceuser, createdbinstanceuser, deletedbinstanceuser, changedbinstanceuserpassword, grantdbinstanceuserprivileges, revokedbinstanceuserprivileges
  - add filter by account in ComputeTag api
  - add ServiceInstance v2 patch api
  - add ComputeInstance patch
  - new version setup
  - add propagation of task error from resource to service
  - add task field in some api view schemas
  - add check of subnet type in db instance create. If subnet is public an error was returned
  - add some check in compute volume attach and detach
  - add account apis v2.0 with new delete api. Now when delete you can specify if delete all child services

## Version 1.8.0 (2020-02-05)
rilascio di funzionalità

* Added
  - add service instance check api
  - add new api ping (with sql check), capabilities and version to /v1.0/nws
  - add service instance name validation
  - add owner propagation from keypair to ssh key
* Fixed
  - removed error propagation that block dbaas instance query
  - fixed implementation of share delete

## Version 1.7.0 (2020-10-23)
rilascio di funzionalità

* Added
  - added dbaas api v2.0. Class ApiDatabaseServiceInstance was replaced with ApiDatabaseServiceInstanceV2
  - added ApiComputeInstance action to add/remove security group
  - added ApiComputeInstance action to add/remove/revert snapshots
  - added ApiServiceDefinition field config in update api
  - added ApiStorageEFS api param PerformanceMode used to manage share based on netapp and new share base on local openstack server
* Fixed
  - some minor fixed in schema fields definitions in order to get better swagger descriptions
  - api oid field declaration for post services with {oid} in path
  - set for all the business service state unknown when state is not known
  - apply patch to method ApiComputeSecurityGroup.get_rule_info_params
  - fixed error generating swagger specification

## Version 1.6.1 (2020-08021)
rilascio di correttive

* Added
  - added share quotas check
  - added private vpc and subnet
  - added delete of compute volumes after delete of compute instance
* Fixed
  - set resource api query size to -1
  - correct bug api sql stack invocation from db instance
  - correct bug during update and delete of some service instance
  - correct bugs in ServiceCatalog
  - correct bug that does not show all the rules for security group list
  - correct bug that does not filter subnet and security group by vpc
  - correct bug in get_paginated_service_defs that return wrong number of records. Set param group_by to True when call get_paginated_service_definitions

## Version 1.6.0 (2020-06-21)
rilascio di funzionalità

* Added
  - add scheduled start e stop for compute instance
  - add compute volume management
* Fixed
  - fixed view schema bug after marshmallow update
  - integrated service config api in service_defnition module
  - correct bug that preclude ComputeInstance elimination when some inputs checks fail
  - correct bug that preclude remove of failed service from capability
  - correct bug that list DELETED subnet in a vpc
  - correct creation of permtag. Sometimes sqlalchemy session is dirty and existing permtag was not found
  - correct bug in service keypair. Create keypair does not return fingerprint and private key
  - correct bug in ApiStorageEFS that print info incorrectly
  - correct describe of file share mount target. A mount target is showed also if it does not exist
* Removed
  - removed agreement api
  - removed division cost api
  - removed organization cost api
  - removed nivola cost api
  - removed service deflink api
  - removed service instink api
  - removed wallet api

## Version 1.5.0 (2019-09-04)
rilascio di funzionalità

* Added
  - ApiComputeTemplate controller per la gestione della nuova tipologia di service ComputeTemplate
  - api GET /computeservices/template/describetemplates
  - api POST /computeservices/template/createtemplate
  - api DELETE /computeservices/template/deletetemplate
  - api PUT /computeservices/instances/customizationinstances
  - nel Dao inserite nuove funzioni utili a definire se un listino prezzo è utilizzato
  - get_account_prices_by_pricelist
  - get_division_prices_by_pricelist
  - nel Controller inserite le seguenti funzioni
  - ApiServicePriceList.is_used  verifica se il listino è usato
  - ApiServicePriceList.pre_delete verifica se ci sono metrics prices da rimuovere
  - api /v1.0/nws/plugins/import [POST] to create a service instance from an existing resource. Extend method pre_import and post_import in a plugin type class to define the behaviour
  - aggiunto metodo ApiComputeKeyPairs pre_import  per la gestione dell'import di una ssh key esistente
  - agginuta stampa nvl_ownerAlias, nvl_ownerId nella Describe di ApiComputeKeyPairs
* Fixed
  - inserimento parametro context='query' nel request schema delle restAPI
  - /v1.0/nws/computeservices/instance/describeinstances
  - /v1.0/nws/computeservices/securitygroup/describesecuritygroups
  - /v1.0/nws/computeservices/subnet/describesubnets
  - /v1.0/nws/computeservices/tag/describetags
  - /v1.0/nws/computeservices/volume/describevolumetypes
  - /v1.0/nws/computeservices/vpc/describevpcs
  - /v1.0/nws/appengineservices/instance/describeappinstances
  - restAPI DELETE /prices/metrics/<oid> inserito controllo per verificare se un price è utilizzato e gestire il raise ApiManagerWarning, viene effettuata la cancellazione logica.
  - restAPI PUT/GET /prices/metrics/ gestione del parametro price_list_id, nel request schema il parametro price_list_id è adesso obbligatorio
  - restAPI request schema verifica ed eliminazione del parametro allow_none=True
  - computeservices/securitygroup/authorizesecuritygroupingress
  - computeservices/securitygroup/authorizesecuritygroupegress
  - computeservices/securitygroup/RevokeSecurityGroupIngress
  - computeservices/securitygroup/RevokeSecurityGroupEgress
  - restAPI DELETE /prices/metrics/<oid> inserito controllo per verificare se un price è utilizzato e gestire il raise ApiManagerWarning, viene effettuata la cancellazione logica.
  - restAPI PUT/GET /prices/metrics/ gestione del parametro price_list_id, nel request schema il parametro price_list_id è adesso obbligatorio
  - restAPI DELETE /pricelists/<oid> corretto il controllo che verifica se il listino è usato
  - ApiServicePriceList.is_used verifica se il listino è usato
  - ApiServicePriceList il campo self.delete_object è stato mappato da self.manager.delete_service_price_metric a self.manager.delete
  - ServiceController.get_service_price_metrics inserito il controllo sui permessi per l'utilizzo del listino - Model ServicePriceList e ServicePriceMetric aggiornate con relationship
  - add field propagate to /1.0/nws/plugis [DELETE] to enable propagation of delete to all cmp modules
  - added control of key name using service instance in ApiComputeInstance, ApiDatabaseServiceInstance and ApiAppEngineInstance pre_create

## Version 1.4.0 (2019-05-24)
rilascio di funzionalità

* Added
  - Inserimento restApi GET /databaseservices/instance/enginetypes
  - inserimento dei seguenti moduli .py e classi
  - DivisionCost per la gestione delle DivisionCostAPI
  - /divisions/<oid>/costs/report
  - /divisions/<oid>/costs/year_summary
  - OrganizationCost per la gestione delle OrganizationCostAPI
  - /organizations/<oid>/costs/report
  - /organizations/<oid>/costs/year_summary
  - NivolaCost per la gestione delle NivolaCostAPI
  - /nivola/cost/year_summary
  - /nivola/cost/report
  - Nivola per la gestione delle NivolaAPI
  - /services/objects/filter/byusername
  - /services/activeservices
  - Inserimento interfaccia restApi GET /computeservices/instance/describeinstancetypes
  - Inserimento interfaccia restApi GET /divisions/<oid>/costconsumes/report
  - Inserimento interfaccia restApi GET/organizations/<oid>/costconsumes/report
  - Inserimento interfaccia restApi GET /services/costconsumes/report
  - Inserimento e gestione def "get_report_costconsume" in ApiAccount, ApiDivision, ApiOrganization, ServiceController (caso Nivola)
  - Inserimento funzioni di formattazione report costconsume."
  - inserimemto e gestione restAPI POST computeservices/keypair/importkeypair
  - inserimemto e gestione restAPI POST /computeservices/keypair/createkeypair
  - inserimemto e gestione  restAPI DELETE /computeservices/keypair/deletekeypair - Controller Computeservice
  - class ApiComputeKeyPairsHelper, fornisce metodi per la generazione della RSA private key in formato SHA1 - DER-encoded (pkcs8)
  - class ApiComputeKeyPairs inseriti i metodi add_resource, import_resource, delete_resource
  - View Account inserimento e gestione restApi nws/accounts/<oid>/tags
  - inserimento restAPI /databaseservices/instancedescribedbinstancetypes
  - Inserimento interfaccia restApi POST /plugins da utilizzare per la creazione di service instance a partire da resource esistenti
  - Aggiunta gestione Volumi
  - Aggiunto api di update dei service type plugin
  - class ApiComputeKeyPairs è stato aggiornato il metodo get_resource invocazione del corrispondente servizio ssh tramite una user_request
  - Class ServiceDbManager metodo get_tags() inserimento parametro di ricerca objid
  - Model class Wallet  inserimento in  relationship agreements parametro lazy='dynamic'
* Fixed
  - restAPI DELETE /computeservices/tags corretto il request schema, inserito per il filtro Tag_N  l'attributo load_from=u'Tag.N'
  - aggiornamento restAPI GET computeservices/keypair/describekeypair
  - fixing schema response restAPI /computeservices/securitygroup/describesecuritygroups
  - aggiornamento restAPI /databaseservices/instances/describeinstancetypes
  - recupero delle service definition tramite la def get_catalog_service_definitions
  - aggiornamento schema DescribeDBInstanceTypesApiRequestSchema e
  - aggiornamento schema DescribeComputeInstanceTypesApiRequestSchema
  - inserito context=query per i parametri MaxResults e NextToken
  - modulo service.portal sono state spostate le seguenti restAPI
  - /accounts/<oid>/activeservices      in view/account.py
  - /divisions/<oid>/activeservices     in view/division.py
  - /organizations/<oid>/activeservices   in view/organization.py
  - /services/objects/filter/byusername  in view/nivola.py
  - /services/activeservices        in view/nivola.py
  - /services/costconsumes/report      in view/nivola.py
  - GET /services/objects/filter/byusername inserito filtro size=0 per recuperare elenco completo objects
  - Aggiornamento set restAPI /computeservices/keypair/ gestione Exception
  - GET computeservices/describeinstances fixing errori di validazione swagger del response schema (Placement)
  - GET computeservices/image/describeimages
  - inserimento nel response schema del campo custom nvl-minDiskSize
  - fixing def aws_info ApiComputeImage inserimento campo custom nvl-minDiskSize
  - fixing def aws_info ApiComputeImage ApiComputeInstance, ApiComputeScurityGroup, ApiSubnet, ApiVpc rename attributi custom
  - fixing ApiComputeScurityGroup def list_resources
  - fixing response schema restApi rimozione errori di validazione swagger, inserimento attributi custom
  - GET /computeservices/image/describeimages
  - GET /computeservices/subnet/describesubnets
  - GET /computeservices/vpc/describevpcs
  - GET /computeservices/vpc/describeinstances
  - GET /computeservices/securitygroup/describesecuritygroups
  - GET /computeservices/tag/describetags
  - GET /computeservices/describeavailabilityzones
  - fixing def aws_info  setting dell'attributo tagSet
  - Aggiornamento response schema restApi GET /computeservices/image/describeimages
  - Aggiornamento response schema restApi GET /computeservices/describeavailabilityzones
  - Aggiornamento response schema restApi GET /computeservices/instance/describeinstances
  - gestione parametro custom nvl_InstanceTypeExt (riporta info flavor su ram, vcpu,...)
  - Aggiornamento ApiAccount, ApiDivision, ApiWallet, ApiConsume sostituzione entity id con uuid value
  - Aggiornamento def get_account_applied_bundle sostituzione del metric_type id con uuid value
  - Aggiornamento model AppliedBundle inserimento relationship account e metric_type
  - Aggiornamento RestApi s/accounts/<oid>/appliedbundles sostituzione del metric_type id con uuid value
  - Aggiornamento interfaccia restApi GET /divisions/<oid>/agreements
  - Aggiornamento interfaccia restApi GET/accounts/<oid>/costconsumes/report
  - Aggiornamento servizi DAO di gestione agreements, report_cost
  - def get_agreements
  - def get_paginated_report_costs
  - def update_report_costs
  - def get_report_cost_monthly_by_account
  - def get_report_cost_monthly_by_accounts
  - def get_credit_by_authority_on_year
  - def get_cost_by_authority_on_period
  - Aggiornamento servizio DAO
  - def get_entity Parse oid and get entity entity by name or by model id or by uuid, test id entity is expired
  - validazione swagger restAPI aggiornamento response schema api
  - computeservices//databaseservices/instance/describedbinstances
  - validazione swagger restAPI aggiornamento request e response schema api
  - computeservices/instance/startinstances
  - computeservices/instance/stopinstances
  - computeservices/instance/terminateinstances
  - ServiceDbManager metodo get_entity()
  - inseriti i controlli per verificare se un entity è expired
  - Con questa modifica il metodo restiuisce solo entity attive a meno di invocare il metodo con filter_expired=True
  - Controller ApiWallet
  - metodo def info()  il valore dell'attributo capital_used è recuperato dall'oggetto self
  - View Class Agreement
  - restApi DELETE nws/divisions/<oid>/agreements/<aid>  modificato il controllo per il recupero dell'entity agreement
  - validazione swagger restAPI /databaseservices/instancedescribedbinstances /databaseservices/instancecreatedbinstance /databaseservices/instancedeletedbinstance
  - ApiDatabaseServiceInstance def aws-info aggiornamento attributi per validazione swagger
  - pre-delete ApiWallet inserimento check su presenza agreement
* Removed
  - Class ServiceDbManager eliminazione di tutti i metodi di gestione subwallet e consume
  - def add_subwallet (), def update_subwallet (),
  - def delete_subwallet (), def get_subwallets, def add_consume (),
  - def update_consume (), def get_consumes ()
  - Controller - Class ApiWallet eliminazione metodo def get_capital_used()
  - Controller eliminazione
  - Class ApiConsume
  - Class ApiSubWallet
  - Class ServiceController riferimenti e metodi di gestione CRUD entity subwallet e consume
  - Class ServiceModule
  - eliminazione riferimenti ApiConsume e ApiSubWallet
  - Model
  - Class Consume
  - Class Subwallet
  - Class Account eliminazione riferimenti a entity Subwallet
  - View rimozione restApi entity subwallet e consume e file py
  - corretto metdodo di interrogazione chiavi ssh. Usata user_request al posto di admin_request
  - aggiunto controllo lunghezza nome servizio a 40 caratteri massimi

## Version 1.3.0 (2019-02-27)
rilascio di funzionalità

* Added
  - aggiunta la action come task di default per ogni service type plugin instance
  - aggiunto il riferimento al task celery nelle operazioni asincrone del controller
  - aggiunto controllo dimesione minima imamgine
  - aggiunto elenco hypervisor nelle imamgini
  - DatabaseService corretti errori nei parametri di filtro della get
* Fixed
  - AppengineService revisione metodi di interrogazione, creazione, cancellazione e modifica
  - aggiunto il salvataggio dei job nel db mysql
  - ComputeSecurityGroup modificata creazione e cancellazione rule utilizzando le action
  - corretta cancellazione servizi in errore nelle account capability

## Version 1.2.0 (2019-02-01)

Rilascio nuove funzionalità
* Added
  - aggiunta gestione autorizzazione gruppi su ServiceCatalog, Account, Division, Organization
  - account capability
  - ComputeService aggiunte api describeaccountattributes, modifyaccountattributes, describeavailabilityzones
  - ComputeService aggiunto invio campo managed_by in fase di creazione
* Fixed
  - ComputeVpc revisione metodi di interrogazione, creazione, cancellazione e modifica
  - ComputeImage revisione metodi di interrogazione, creazione, cancellazione e modifica
  - ComputeSubnet revisione metodi di interrogazione, creazione, cancellazione e modifica
  - ComputeSecurityGroup revisione metodi di interrogazione, creazione, cancellazione e modifica
  - ComputeInstance, DatabaseInstance aggiunto controllo univocità nome
  - ComputeInstance, DatabaseInstance aggiunto controllo dimensione minima disco di boot di 20GB
  - ComputeInstance, DatabaseInstance aggiunto controllo quote in fase di creazione
  - ComputeInstance, DatabaseInstance aggiunto controllo stato availability zone
  - Division eliminato decorator transaction nel metodo add_division del controller che impediva la creazione nel db
  - Sistemata la gestione dei tag per ComputeInstance, ComputeVpc, SecurityGroup
  - ComputeService revisione metodi di interrogazione, creazione, cancellazione e modifica
  - DatabaseService revisione metodi di interrogazione, creazione, cancellazione e modifica
  - StorageService revisione metodi di interrogazione, creazione, cancellazione e modifica
  - AppengineService revisione metodi di interrogazione, creazione, cancellazione e modifica

## Version 1.1.0 (2019-01-13)
rilascio di funzionalità

* Added
  - Creata nuova classe ServiceTypePlugin con i metodi di add, get e list nel controller. Creati tutti i task e i job per gestire il ciclo di vita della creazione, cancellazione e modifica
  - ComputeInstance aggiunti metodi di start, stop e cambio instance_type
* Fixed
  - ServiceInstance refactoring
  - ServiceType refactoring
  - ServiceDefinition refactoring
  - ComputeInstance revisione metodi di interrogazione, creazione, cancellazione e modifica
  - SecurityGroup revisione metodi di interrogazione
  - DatabaseInstance revisione metodi di interrogazione, creazione, cancellazione e modifica

## Version 1.0.0 (2018-07-31)
First production preview release.


## Version 0.1.0 (2016-04-18)
First private preview release.

