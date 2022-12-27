-- # SPDX-License-Identifier: EUPL-1.2
-- #
-- # (C) Copyright 2021-2022 CSI-Piemonte

DROP PROCEDURE service.`expose_consumes`;

DELIMITER $$
CREATE DEFINER=`service`@`%` PROCEDURE `service`.`expose_consumes`(in p_period varchar(10) )
BEGIN
    -- IN order to be idempotent
    DELETE FROM mv_aggregate_consumes WHERE period = p_period;
   	commit;
    INSERT INTO mv_aggregate_consumes
        (organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
        modification_date, period, metric, consumed, measure_unit, container_uuid,
        container_instance_type, container_type, category)
	SELECT
        min(o.uuid)  AS organization_uuid,
        min(d.uuid)  AS division_uuid,
        min(a.uuid)  AS account_uuid,
        max(ac.creation_date) AS creation_date,
        max(ac.evaluation_date) AS evaluation_date,
        max(ac.modification_date) AS modification_date,
        ac.period AS period,
        min(me.name) AS metric,
        sum(ac.consumed) AS consumed,
        min(me.measure_unit) AS measure_unit,
        null  AS container_uuid,
        min(me.group_name) AS container_instance_type,
        min(me.group_name) AS container_type,
        null AS category
    FROM
        aggregate_cost ac
        INNER JOIN account a ON ac.fk_account_id = a.id
        INNER JOIN division d ON a.fk_division_id = d.id
        INNER JOIN organization o ON d.fk_organization_id = o.id
        left OUTER  JOIN service_metric_type me ON ac.fk_metric_type_id = me.id
    WHERE
    	ac.period  = p_period
    	and ac.aggregation_type = 'daily'
    GROUP BY
        ac.period, ac.fk_account_id ,  ac.fk_metric_type_id
    ;
    COMMIT;
END
$$