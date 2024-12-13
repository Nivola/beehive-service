SET SESSION wsrep_OSU_method='RSU';
SET wsrep_OSU_method='RSU';

ALTER TABLE service_tag
DROP CONSTRAINT IF EXISTS name;

ALTER TABLE service_tag
ADD COLUMN fk_account_id int(11) NOT NULL DEFAULT 1;

ALTER TABLE service_tag
ADD CONSTRAINT UNIQUE KEY name_account (name, fk_account_id);

ALTER TABLE service_tag
ADD CONSTRAINT service_tag_ibfk_1
FOREIGN KEY(fk_account_id) REFERENCES account(id);

SET SESSION wsrep_OSU_method='TOI';
SET wsrep_OSU_method='TOI';

SHOW status LIKE 'wsrep_local_state_comment';
SHOW status LIKE 'wsrep_cluster_status';
