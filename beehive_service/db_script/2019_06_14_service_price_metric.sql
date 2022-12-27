/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2022 CSI-Piemonte

*/


-- service_price_metric adding threshold an slice price
ALTER TABLE `service`.`service_price_metric` ADD COLUMN `price_type` VARCHAR(10) NOT NULL default 'SIMPLE' AFTER `time_unit`;
ALTER TABLE `service`.`service_price_metric` ADD COLUMN `params` TEXT NULL AFTER `price_type`;
ALTER TABLE `service`.`service_job` MODIFY COLUMN `fk_account_id` int(11) NULL;
