/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE service.`expose_consumes_metric`;
DELIMITER $$
CREATE  PROCEDURE `expose_consumes_metric`(in p_period varchar(10), in metrictype int )
BEGIN
     DECLARE metricname VARCHAR(50);

    SELECT `name` INTO metricname FROM service_metric_type WHERE id = metrictype;
    DELETE FROM mv_aggregate_consumes WHERE `period`=p_period AND metric = metricname;
    INSERT INTO mv_aggregate_consumes
            (organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
            modification_date, `period`, metric, consumed, measure_unit, container_uuid,
            container_instance_type, container_type, category
            )
    SELECT organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
        modification_date, `period`, metric, consumed, measure_unit, container_uuid,
        container_instance_type, container_type, category
    FROM v_aggregate_consumes
    WHERE `period` = p_period AND metric=metricname;
    COMMIT;

END
$$
DELIMITER ;
