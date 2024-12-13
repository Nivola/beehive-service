/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS  service.daily_consumes;
DELIMITER $$
CREATE  PROCEDURE daily_consumes( IN p_period VARCHAR(10) )
BEGIN
    DECLARE v_jobid INTEGER;
    DECLARE done INTEGER DEFAULT FALSE;
    DECLARE v_account_id INTEGER;
    DECLARE cur_account CURSOR FOR SELECT id FROM account WHERE creation_date < DATE(p_period) AND (expiry_date IS NULL OR expiry_date > DATE(p_period));
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- SELECT max(id) INTO v_jobid FROM scheduler_task;
    SELECT 1 INTO v_jobid ;

    OPEN cur_account;

    account_loop: LOOP
        FETCH cur_account INTO v_account_id;
        SELECT CONCAT('Computing consume for account id ',v_account_id) AS MSG;

        IF done THEN
            LEAVE account_loop;
        END IF;

            CALL compute_daily_consumes( v_account_id, p_period, v_jobid) ;

    END LOOP;
    CLOSE cur_account;

    COMMIT;

    UPDATE  aggregate_cost  SET was_metric_type_id = fk_metric_type_id  WHERE was_metric_type_id  IS NULL;
    UPDATE
        service.aggregate_cost ac
        INNER JOIN  service.tmp_databases_  d ON d.fk_service_instance_id = ac.fk_service_instance_id
        INNER JOIN  service.tmp_metric_map_ m  ON ac.fk_metric_type_id =  m.from_id AND m.dbtype = d.dbtype
        SET fk_metric_type_id = m.to_id
    WHERE
        ac.fk_metric_type_id = ac.was_metric_type_id
        AND ac.fk_metric_type_id !=  m.to_id
        AND ac.period = p_period ;
    CALL expose_consumes(p_period);
    COMMIT;
END
$$
DELIMITER ;
