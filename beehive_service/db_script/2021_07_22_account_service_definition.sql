-- # SPDX-License-Identifier: EUPL-1.2
-- #
-- # (C) Copyright 2020-2023 CSI-Piemonte


CREATE TABLE IF NOT EXISTS `account_service_definition` (
-- service.account_service_definition definition
  `creation_date` datetime DEFAULT NULL,
  `modification_date` datetime DEFAULT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid` varchar(50) COLLATE latin1_general_ci DEFAULT NULL,
  `objid` varchar(400) COLLATE latin1_general_ci DEFAULT NULL,
  `desc` varchar(255) COLLATE latin1_general_ci DEFAULT NULL,
  `active` tinyint(1) DEFAULT NULL,
  `name` varchar(100) COLLATE latin1_general_ci DEFAULT NULL,
  `version` varchar(100) COLLATE latin1_general_ci NOT NULL,
  `fk_account_id` int(11) DEFAULT NULL,
  `fk_service_definition_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`),
  KEY `fk_account_id` (`fk_account_id`),
  KEY `fk_service_definition_id` (`fk_service_definition_id`),
  CONSTRAINT `account_service_definition_ibfk_1` FOREIGN KEY (`fk_account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `account_service_definition_ibfk_2` FOREIGN KEY (`fk_service_definition_id`) REFERENCES `service_definition` (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`active` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

 CREATE INDEX `ix_account_service_definition`
 on `account_service_definition`( `fk_service_definition_id`, `fk_account_id` );


ALTER TABLE service_plugin_type ADD service_category varchar(20) NULL;

update service_plugin_type set service_category= 'dummy' where name_type ='Dummy';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeService';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeInstance';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeImage';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeVPC';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeSubnet';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeSecurityGroup';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeVolume';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeKeyPairs';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeLimits';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeAddress';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseService';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseInstance';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseSchema';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseUser';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseBackup';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseLog';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseSnapshot';
update service_plugin_type set service_category= 'dbaas' where name_type ='DatabaseTag';
update service_plugin_type set service_category= 'staas' where name_type ='StorageService';
update service_plugin_type set service_category= 'staas' where name_type ='StorageEFS';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeTag';
update service_plugin_type set service_category= 'plaas' where name_type ='AppEngineService';
update service_plugin_type set service_category= 'plaas' where name_type ='AppEngineInstance';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeTemplate';
update service_plugin_type set service_category= 'netaas' where name_type ='ApiNetworkService';
update service_plugin_type set service_category= 'netaas' where name_type ='ApiNetworkGateway';
update service_plugin_type set service_category= 'netaas' where name_type ='NetworkService';
update service_plugin_type set service_category= 'netaas' where name_type ='NetworkGateway';
update service_plugin_type set service_category= 'cpaas' where name_type ='VirtualService';
update service_plugin_type set service_category= 'cpaas' where name_type ='ComputeCustomization';