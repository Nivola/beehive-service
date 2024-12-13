/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/

ALTER TABLE service_metric_type ADD COLUMN creation_date DATETIME;
ALTER TABLE service_metric_type ADD COLUMN modification_date DATETIME;
ALTER TABLE service_metric_type ADD COLUMN expiry_date DATETIME;
ALTER TABLE service_metric_type ADD COLUMN uuid VARCHAR(50);
ALTER TABLE service_metric_type ADD COLUMN objid VARCHAR(400);
ALTER TABLE service_metric_type ADD COLUMN status VARCHAR(20) NOT NULL;
ALTER TABLE service_metric_type ADD COLUMN active BIT;


CREATE UNIQUE INDEX uuid
   ON service_metric_type (uuid ASC);

CREATE INDEX status
   ON service_metric_type (status ASC);


# queste danno problemi #

update service_metric_type set status = 'ACTIVE';

ALTER TABLE service_metric_type
  ADD CONSTRAINT service_metric_type_ibfk_1 FOREIGN KEY (status)
  REFERENCES service_status (name)
  ON UPDATE NO ACTION
  ON DELETE NO ACTION;