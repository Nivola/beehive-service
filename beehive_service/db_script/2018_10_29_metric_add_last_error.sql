/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2022 CSI-Piemonte

*/

ALTER TABLE service_job ADD COLUMN task_id VARCHAR(50) NOT NULL AFTER params;
ALTER TABLE service_job ADD COLUMN status VARCHAR(10) NOT NULL AFTER task_id;
ALTER TABLE service_job ADD COLUMN last_error TEXT NULL AFTER status;
