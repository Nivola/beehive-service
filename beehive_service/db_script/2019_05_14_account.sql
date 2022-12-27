/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2022 CSI-Piemonte

*/


-- Account
ALTER TABLE `service`.`account` ADD COLUMN `acronym` VARCHAR(10) NULL AFTER `params`;