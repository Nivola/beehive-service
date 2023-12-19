/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2023 CSI-Piemonte

*/

-- popola relazione sm sm

create index sm_searchidx on service_metric(creation_date,fk_metric_type_id,fk_service_instance_id);

alter table service_metric add column need_next boolean default true;

create index sm_need_nextidx on service_metric(need_next);

drop table if exists service_metric_next_service_metric;

create table
    service_metric_next_service_metric(
    fk_sm_id integer not NULL,
    next_sm_id integer not NULL,
    PRIMARY KEY (fk_sm_id)
);

update service_metric m inner join service_metric_next_service_metric mm on m.id = mm.fk_sm_id set m.need_next = null;




-- call smsmpopulate(10000);

-- alter table service_metric_next_service_metric add CONSTRAINT  UNIQUE KEY udx_smsm  (fk_sm_id, next_sm_id );
-- alter table service_metric_next_service_metric add CONSTRAINT smsm_fk_1 FOREIGN KEY (fk_sm_id) REFERENCES service_metric (id);
-- alter table service_metric_next_service_metric add CONSTRAINT smsm_fk_2 FOREIGN KEY (next_sm_id) REFERENCES service_metric (id);


-- alter table service_metric_next_service_metric drop KEY udx_smsm  ;
-- alter table service_metric_next_service_metric DROP FOREIGN KEY smsm_fk_1 ;
-- alter table service_metric_next_service_metric DROP FOREIGN KEY smsm_fk_2 ;
