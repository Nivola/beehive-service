
/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2019 CSI-Piemonte
(C) Copyright 2018-2023 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `dailyconsumes_by_account`;
DELIMITER $$
CREATE  PROCEDURE `dailyconsumes_by_account`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
BEGIN
    DECLARE smetrics INT;
    SELECT  COUNT(*) into smetrics
        FROM
            service_metric sm
            INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
        WHERE
            sm.creation_date >=  DATE(p_period)
            AND sm.creation_date <  adddate(p_period,1)
            AND si.fk_account_id = p_account_id;
    IF smetrics > 0 THEN

        DELETE FROM aggregate_cost WHERE  fk_account_id = p_account_id AND aggregate_cost.period = p_period;
        COMMIT;

        INSERT INTO aggregate_cost (creation_date, modification_date, `expiry_date`,
                                    fk_metric_type_id, cost, evaluation_date, fk_service_instance_id,
                                    fk_account_id, fk_job_id, aggregation_type, period,
                                    fk_cost_type_id, consumed)
            SELECT
                NOW() creation_date,
                NOW() modification_date,
                NULL,
                dd.fk_metric_type_id fk_metric_type_id,
                0,
                NOW() evaluation_date,
                dd.fk_service_instance_id fk_service_instance_id,
                min(dd.account_id) account_id,
                jobid,
                'daily',
                p_period,
                CASE count(*) WHEN 1 THEN 2 else 1 end fk_cost_type_id,
                ifnull(sum(value * wt) / sum(wt) , 0)  consumed
            FROM (
                    SELECT

                        sm.creation_date,
                        UNIX_TIMESTAMP(nm.creation_date)- UNIX_TIMESTAMP(DATE(p_period)) wt,
                        sm.value,
                        sm.fk_metric_type_id ,
                        sm.fk_service_instance_id,
                        si.fk_account_id account_id
                    FROM
                        service_metric sm
                        INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                        INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                        INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                        INNER JOIN ( SELECT
                                    max(sm.creation_date) creation_date,
                                    sm.fk_metric_type_id ,
                                    sm.fk_service_instance_id
                                FROM
                                    service_metric sm
                                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                                WHERE sm.creation_date <  DATE(p_period)
                                GROUP BY sm.fk_metric_type_id, sm.fk_service_instance_id) prevt
                        ON sm.creation_date=prevt.creation_date AND sm.fk_metric_type_id = prevt.fk_metric_type_id
                            AND sm.fk_service_instance_id = prevt.fk_service_instance_id
                union
                    SELECT

                        sm.creation_date,
                        CASE
                            WHEN sm.creation_date = nm.creation_date THEN 1
                            WHEN nm.creation_date < adddate(p_period,1) THEN UNIX_TIMESTAMP(nm.creation_date)- UNIX_TIMESTAMP(sm.creation_date)
                            ELSE abs(UNIX_TIMESTAMP(adddate(p_period,1))- UNIX_TIMESTAMP(sm.creation_date)) END wt,
                        sm.value,
                        sm.fk_metric_type_id ,
                        sm.fk_service_instance_id,
                        si.fk_account_id account_id
                    FROM
                        service_metric sm
                        INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                        INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                        INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                    WHERE
                        sm.creation_date >=  DATE(p_period)
                        AND sm.creation_date <  adddate(p_period,1)
                    ) dd
                    GROUP by dd.fk_metric_type_id, dd.fk_service_instance_id
                ;
        COMMIT;
    END IF;
END
$$
DELIMITER ;
