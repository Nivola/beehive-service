/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2023 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `dailyconsumes_one_transaction`;
DELIMITER $$
CREATE  PROCEDURE `dailyconsumes_one_transaction`( in p_period varchar(10), in jobid  INTEGER )
BEGIN

    DELETE FROM aggregate_cost WHERE aggregate_cost.period = p_period;

    INSERT INTO aggregate_cost (creation_date, modification_date, `expiry_date`, fk_metric_type_id, cost, evaluation_date, fk_service_instance_id, fk_account_id, fk_job_id, aggregation_type, period, fk_cost_type_id, consumed)
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
            sum(value * wt) / sum(wt) consumed
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
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
                    INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                    INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                    INNER JOIN ( SELECT
                                max(sm.creation_date) creation_date,
                                sm.fk_metric_type_id ,
                                sm.fk_service_instance_id
                            FROM
                                service_metric sm
                                INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
                            WHERE sm.creation_date <  DATE(p_period)
                            GROUP BY sm.fk_metric_type_id, sm.fk_service_instance_id) prevt
                    ON sm.creation_date=prevt.creation_date AND sm.fk_metric_type_id = prevt.fk_metric_type_id
                        AND sm.fk_service_instance_id = prevt.fk_service_instance_id
               union
                SELECT

                    sm.creation_date,
                    CASE WHEN nm.creation_date < adddate(p_period,1) THEN UNIX_TIMESTAMP(nm.creation_date)- UNIX_TIMESTAMP(sm.creation_date)
                    else UNIX_TIMESTAMP(adddate(p_period,1))- UNIX_TIMESTAMP(sm.creation_date) end wt,
                    sm.value,
                    sm.fk_metric_type_id ,
                    sm.fk_service_instance_id,
                    si.fk_account_id account_id
                FROM
                    service_metric sm
                    INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                    INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
                WHERE
                    sm.creation_date >=  DATE(p_period)
                    AND sm.creation_date <  adddate(p_period,1)
                ) dd
                GROUP by dd.fk_metric_type_id, dd.fk_service_instance_id
            ;
    COMMIT;
END
$$
DELIMITER ;
