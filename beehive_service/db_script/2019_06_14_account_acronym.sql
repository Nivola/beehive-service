/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/



ALTER TABLE service.account
CHANGE COLUMN acronym acronym VARCHAR(10) CHARACTER SET 'latin1' NULL DEFAULT NULL ;