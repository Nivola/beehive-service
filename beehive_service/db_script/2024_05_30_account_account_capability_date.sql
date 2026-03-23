-- # SPDX-License-Identifier: EUPL-1.2
-- #
-- # (C) Copyright 2018-2026 CSI-Piemonte

ALTER TABLE service.account_account_capabilities
ADD COLUMN application_date DATETIME;
;
