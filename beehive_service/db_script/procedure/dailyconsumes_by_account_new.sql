/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `dailyconsumes_by_account_new`;

DELIMITER $$

CREATE  PROCEDURE `dailyconsumes_by_account_new`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
BEGIN
    DECLARE smetrics INT;
    SELECT  COUNT(*) INTO smetrics
        FROM
            service_metric sm
            INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
        WHERE
            sm.creation_date >=  DATE(p_period)
            AND sm.creation_date <  adddate(p_period,1)
            AND si.fk_account_id = p_account_id;
    IF smetrics = 0 THEN
        DELETE FROM aggregate_cost WHERE  fk_account_id = p_account_id AND aggregate_cost.period = p_period;
        COMMIT;
        INSERT INTO aggregate_cost (creation_date, modification_date, `expiry_date`, fk_metric_type_id, cost, evaluation_date, fk_service_instance_id, fk_account_id, fk_job_id, aggregation_type, period, fk_cost_type_id, consumed)
            WITH
            prevt AS (
            SELECT
                    max(sm.id) id,
                    -- max(sm.creation_date) creation_date,
                    sm.fk_metric_type_id ,
                    sm.fk_service_instance_id
                FROM
                    service_metric sm
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                WHERE sm.creation_date <  DATE(p_period)
                GROUP BY sm.fk_metric_type_id, sm.fk_service_instance_id
            ),
            lastm AS (
                SELECT
                    sm.id,
                    'lastm' cd_from,
                    -- sm.creation_date  cd,
                    DATE(p_period) ts,
                    UNIX_TIMESTAMP(DATE(p_period)) epoc,
                    sm.value  val,
                    sm.fk_metric_type_id ,
                    sm.fk_service_instance_id
                FROM
                    service_metric sm
                    inner join prevt on sm.id = prevt.id
            ),
            todaym AS (
                SELECT
                    sm.id,
                    'today' cd_from,
                    -- sm.creation_date cd,
                    sm.creation_date ts,
                    UNIX_TIMESTAMP(sm.creation_date ) epoc ,
                    sm.value val,
                    sm.fk_metric_type_id ,
                    sm.fk_service_instance_id
                FROM
                    service_metric sm
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                WHERE
                    sm.creation_date >=  DATE(p_period)
                    AND sm.creation_date <  adddate(p_period,1)
            ),
            todayandlast AS (SELECT * FROM todaym UNION SELECT * FROM lastm),
            metricwt AS (
                SELECT
                    fk_service_instance_id,
                    fk_metric_type_id ,
                    ts,
                    CASE WHEN (LAG(epoc, 1) over (PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY id DESC))  IS NOT NULL
                            THEN (LAG(epoc, 1) OVER (PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY id DESC))
                        WHEN cd_from ='today'
                            THEN  UNIX_TIMESTAMP(adddate(p_period,1) )
                        ELSE NULL END  - epoc wt,
                    val
                FROM
                    todayandlast
            ),
            computed AS (
                SELECT
                    fk_metric_type_id,
                    fk_service_instance_id,
                    IFNULL(sum(val * wt) / sum(wt) , 0)  consumed
                FROM metricwt
                WHERE wt IS NOT NULL
                GROUP BY fk_service_instance_id , fk_metric_type_id
            )
            select
                NOW() creation_date,
                NOW() modification_date,
                NULL `expiry_date`,
                fk_metric_type_id ,
                0 cost,
                NOW() evaluation_date,
                fk_service_instance_id,
                p_account_id account_id,
                jobid,
                'daily',
                p_period period,
                1 fk_cost_type_id,
                consumed
            from
                computed ;
        COMMIT;
    END IF;
END
$$

DELIMITER ;
