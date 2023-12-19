/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2023 CSI-Piemonte

*/


-- Wallet
ALTER TABLE `service`.`wallet` ADD COLUMN year_ref INT NOT NULL ;

-- Agreement
ALTER TABLE `service`.`agreement` DROP FOREIGN KEY `agreement_ibfk_2`;
ALTER TABLE `service`.`agreement` DROP COLUMN `status`;
ALTER TABLE `service`.`agreement` ADD COLUMN `agreement_date_start` DATETIME NOT NULL AFTER `agreement_date`;
ALTER TABLE `service`.`agreement` ADD COLUMN `agreement_date_end` DATETIME NOT NULL AFTER `agreement_date_start`;
ALTER TABLE `service`.`agreement` ADD COLUMN year_ref INT NOT NULL ;
ALTER TABLE `service`.`agreement` DROP COLUMN `agreement_date` ;
ALTER TABLE `service`.`agreement` ADD COLUMN `fk_service_status_id` INT(11) NULL DEFAULT
  NULL AFTER `agreement_date_end`, ADD INDEX `fk_service_status_id` (`fk_service_status_id` ASC);

ALTER TABLE `service`.`agreement` ADD CONSTRAINT `agreement_ibfk_2` FOREIGN KEY (`id`)
  REFERENCES `service`.`service_status` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION;