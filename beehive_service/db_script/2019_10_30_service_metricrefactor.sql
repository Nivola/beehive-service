/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2022 CSI-Piemonte

*/


CREATE TABLE service_metric_store (
  creation_date datetime DEFAULT NULL,
  modification_date datetime DEFAULT NULL,
  expiry_date datetime DEFAULT NULL,
  id int(11) ,
  value float ,
  fk_metric_type_id int(11) DEFAULT NULL,
  metric_num int(11),
  fk_service_instance_id int(11) DEFAULT NULL,
  fk_job_id int(11) DEFAULT NULL,
  need_next tinyint(1) DEFAULT '1',
  PRIMARY KEY (id)
);
