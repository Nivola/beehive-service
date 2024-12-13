-- service.v_aggregate_cost source
-- ssh root@cmpto1-galeracmp01.site01.nivolapiemonte.it -i .../prod/id_rsa
-- mysql -u root --password=... service

CREATE OR REPLACE
ALGORITHM = UNDEFINED VIEW `service`.`v_aggregate_cost` AS
SELECT 
    ac.id AS id, 
    a.uuid AS account_uuid, 
    ac.period AS period, 
    smt.name AS metric, 
    ac.consumed AS consumed, 
    smt.measure_unit AS measure_unit, 
    si.name AS instance_name
FROM service.aggregate_cost ac 
INNER JOIN service.account a ON ac.fk_account_id = a.id 
INNER JOIN service.service_metric_type smt ON ac.fk_metric_type_id = smt.id 
INNER JOIN service.service_instance si ON ac.fk_service_instance_id = si.id 
WHERE ac.aggregation_type = 'daily' 
;

-- user sola lettura del portale
GRANT SELECT ON service.v_aggregate_cost
TO 'servicero'@'%'
;

-- verifica
SHOW GRANTS FOR 'servicero'@'%';
