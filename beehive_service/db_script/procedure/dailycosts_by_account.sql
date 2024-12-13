/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `dailycosts_by_account`;
DELIMITER $$
CREATE PROCEDURE `dailycosts_by_account`(IN p_period VARCHAR(10), IN p_accountid  INTEGER, IN jobid  INTEGER )
BEGIN
    DELETE FROM report_cost WHERE  report_cost.period = p_period and fk_account_id = p_accountid ;
    COMMIT;

    INSERT INTO report_cost (creation_date, modification_date, `expiry_date`, fk_account_id, plugin_name, `value`, cost, fk_metric_type_id, note, report_date, `period`, fk_job_id)
    SELECT
        NOW() creation_date,
        NOW() modification_date,
        NULL `expiry_date`,
        dd.account_id fk_account_id,
        dd.pluginname plugin_name,
        sum(dd.consumed)value,
        sum(dd.consumed) / min(divisor) * max(ifnull(dd.price, 0)) cost,
        dd.fk_metric_type_id,
        NULL note,
        NULL report_date,
        p_period period,
        jobid fk_job_id
    FROM ( SELECT

                ag.fk_account_id account_id,
                ag.fk_service_instance_id,
                ag.fk_metric_type_id,
                ag.consumed,
                pr.id pricelist,
                IFNULL(sc.id, si.id) containerid,
                IFNULL(cpt.name_type, pt.name_type) pluginname,
                prm.id prmid,
                prm.price,
                CASE prm.time_unit WHEN 'YEAR' THEN 365  WHEN 'WEEK' THEN 365 WHEN 'DAY' THEN 1 ELSE 365 END divisor,
                bm.value,
                prm.time_unit

            FROM
                aggregate_cost ag

                INNER JOIN account ac ON ag.fk_account_id = ac.id
                INNER JOIN service_instance si ON ag.fk_service_instance_id = si.id

                INNER JOIN service_definition sd ON si.fk_service_definition_id = sd.id
                INNER JOIN service_type st ON sd.fk_service_type_id = st.id
                INNER JOIN service_plugin_type pt ON st.objclass  = pt.objclass

                LEFT OUTER JOIN applied_bundle b ON ag.fk_account_id = b.fk_account_id AND b.start_date < DATE(p_period)  AND ( b.end_date is NULL OR b.end_date > DATE(p_period))
                LEFT OUTER JOIN service_metric_type_limit bm ON bm.parent_id = b.fk_metric_type_id AND bm.fk_metric_type_id = ag.fk_metric_type_id

                LEFT OUTER JOIN account_pricelist apl  ON apl.start_date < DATE(p_period) AND (apl.end_date is NULL OR apl.end_date < DATE(p_period)) AND apl.fk_account_id = ag.fk_account_id
                LEFT OUTER JOIN division_pricelist dpl ON dpl.start_date < DATE(p_period) AND (dpl.end_date is NULL OR dpl.end_date < DATE(p_period)) AND dpl.fk_division_id = ac.fk_division_id
                LEFT OUTER JOIN service_pricelist pr ON pr.id = IFNULL(apl.fk_price_list_id, dpl.fk_price_list_id)
                LEFT OUTER JOIN service_price_metric prm ON prm.fk_price_list_id = pr.id AND prm.fk_metric_type_id = ag.fk_metric_type_id

                LEFT OUTER JOIN service_link_inst  li ON li.end_service_id  = si.id
                LEFT OUTER JOIN service_instance sc ON li.start_service_id  = sc.id
                LEFT OUTER JOIN service_definition scd ON sc.fk_service_definition_id = scd.id
                LEFT OUTER JOIN service_type sct ON scd.fk_service_type_id = sct.id
                LEFT OUTER JOIN service_plugin_type cpt ON sct.objclass  = cpt.objclass
            WHERE
                bm.id IS NULL
                AND prm.price_type = 'SIMPLE'
                AND ag.period = p_period
                AND ag.fk_account_id = p_accountid
    ) dd
    GROUP BY dd.account_id, dd.pluginname, fk_metric_type_id
    ;

    INSERT INTO report_cost (creation_date, modification_date, `expiry_date`, fk_account_id, plugin_name, `value`, cost, fk_metric_type_id, note, report_date, `period`, fk_job_id)
    SELECT
        NOW() creation_date,
        NOW() modification_date,
        NULL `expiry_date`,
        dd.account_id fk_account_id,
        dd.pluginname plugin_name,
        sum(dd.consumed)value,
        sum(dd.consumed)/ min(divisor)* max(dd.price) cost,
        dd.fk_metric_type_id,
        NULL note,
        NULL report_date,
        p_period period,
        jobid fk_job_id
    FROM (
            SELECT
                ac.id account_id,
                mt.id  fk_metric_type_id,
                1  consumed,
                pr.id pricelist,
                mt.group_name pluginname,
                prm.id prmid,
                prm.price,
                CASE prm.time_unit WHEN 'YEAR' THEN 365  WHEN 'WEEK' THEN 365 WHEN 'DAY' THEN 1 ELSE 365 END divisor,
                prm.time_unit
            FROM
                account ac
                inner JOIN applied_bundle b ON ac.id = b.fk_account_id AND b.start_date < DATE(p_period)  AND (b.end_date is NULL OR b.end_date > DATE(p_period))
                inner JOIN service_metric_type mt ON  b.fk_metric_type_id = mt.id
                LEFT OUTER JOIN account_pricelist apl  ON apl.start_date < DATE(p_period) AND (apl.end_date is NULL OR apl.end_date < DATE(p_period)) AND apl.fk_account_id = ac.id
                LEFT OUTER JOIN division_pricelist dpl ON dpl.start_date < DATE(p_period) AND (dpl.end_date is NULL OR dpl.end_date < DATE(p_period)) AND dpl.fk_division_id = ac.fk_division_id
                LEFT OUTER JOIN service_pricelist pr ON pr.id = IFNULL(apl.fk_price_list_id, dpl.fk_price_list_id)
                LEFT OUTER JOIN service_price_metric prm ON prm.fk_price_list_id = pr.id AND prm.fk_metric_type_id = mt.id
            WHERE
                ac.id = p_accountid
        ) dd
    GROUP BY dd.account_id, dd.pluginname, fk_metric_type_id;


    INSERT INTO report_cost (creation_date, modification_date, `expiry_date`, fk_account_id, plugin_name, `value`, cost, fk_metric_type_id, note, report_date, `period`, fk_job_id)
    SELECT
        NOW() creation_date,
        NOW() modification_date,
        NULL `expiry_date`,
        dd.account_id fk_account_id,
        dd.pluginname plugin_name,
        sum(dd.consumed) - max(dd.threshold) value,
        (sum(dd.consumed) - max(dd.threshold)) / min(divisor)* max(dd.price) cost,
        dd.fk_metric_type_id,
        NULL note,
        NULL report_date,
        p_period period,
        jobid fk_job_id
    FROM (
            SELECT
                ag.fk_account_id account_id,
                ag.fk_metric_type_id,
                ag.consumed,
                bm.value threshold,
                IFNULL(sc.id, si.id) containerid,
                IFNULL(cpt.name_type, pt.name_type) pluginname,
                prm.price,
                CASE prm.time_unit WHEN 'YEAR' THEN 365  WHEN 'WEEK' THEN 365 WHEN 'DAY' THEN 1 ELSE 365 END divisor
            FROM
                aggregate_cost ag

                INNER JOIN account ac ON ag.fk_account_id = ac.id
                INNER JOIN service_instance si ON ag.fk_service_instance_id = si.id

                INNER JOIN service_definition sd ON si.fk_service_definition_id = sd.id
                INNER JOIN service_type st ON sd.fk_service_type_id = st.id
                INNER JOIN service_plugin_type pt ON st.objclass  = pt.objclass

                inner JOIN applied_bundle b ON ag.fk_account_id = b.fk_account_id AND b.start_date < DATE(p_period)  AND (b.end_date is NULL OR b.end_date > DATE(p_period))
                inner JOIN service_metric_type_limit bm ON bm.parent_id = b.fk_metric_type_id AND bm.fk_metric_type_id = ag.fk_metric_type_id

                LEFT OUTER JOIN account_pricelist apl  ON apl.start_date < DATE(p_period) AND (apl.end_date is NULL OR apl.end_date < DATE(p_period)) AND apl.fk_account_id = ag.fk_account_id
                LEFT OUTER JOIN division_pricelist dpl ON dpl.start_date < DATE(p_period) AND (dpl.end_date is NULL OR dpl.end_date < DATE(p_period)) AND dpl.fk_division_id = ac.fk_division_id
                LEFT OUTER JOIN service_pricelist pr ON pr.id = IFNULL(apl.fk_price_list_id, dpl.fk_price_list_id)
                LEFT OUTER JOIN service_price_metric prm ON prm.fk_price_list_id = pr.id AND prm.fk_metric_type_id = ag.fk_metric_type_id

                LEFT OUTER JOIN service_link_inst  li ON li.end_service_id  = si.id
                LEFT OUTER JOIN service_instance sc ON li.start_service_id  = sc.id
                LEFT OUTER JOIN service_definition scd ON sc.fk_service_definition_id = scd.id
                LEFT OUTER JOIN service_type sct ON scd.fk_service_type_id = sct.id
                LEFT OUTER JOIN service_plugin_type cpt ON sct.objclass  = cpt.objclass
            WHERE
                ag.period = p_period
                AND ag.fk_account_id = p_accountid
    ) dd
    GROUP BY dd.account_id, dd.pluginname, fk_metric_type_id
    having sum(dd.consumed) > max(dd.threshold);


    INSERT INTO report_cost (creation_date, modification_date, `expiry_date`, fk_account_id, plugin_name, `value`, cost, fk_metric_type_id, note, report_date, `period`, fk_job_id)
    SELECT
        NOW() creation_date,
        NOW() modification_date,
        NULL `expiry_date`,
        dd.account_id fk_account_id,
        IFNULL(cpt.name_type, pt.name_type) plugin_name,
        dd.consumed  value,
        (dd.consumed / dd.divisor * spmt.price) cost,
        dd.fk_metric_type_id,
        concat('applicata fascia a ', spmt.price) note,
        NULL report_date,
        p_period period,
        jobid fk_job_id
    FROM
        ((((((((((( SELECT
            ag.fk_account_id account_id,
            min(ag.fk_service_instance_id) fk_service_instance_id,
            ag.fk_metric_type_id,
            sum(ag.consumed) consumed,
            CASE min(prm.time_unit) WHEN 'YEAR' THEN 365  WHEN 'WEEK' THEN 7 WHEN 'DAY' THEN 1 ELSE 365 END divisor,
            prm.id fk_service_price_metric_id
        FROM
            (((((aggregate_cost ag

            INNER JOIN account ac ON ag.fk_account_id = ac.id)

            LEFT OUTER JOIN account_pricelist apl
                ON apl.start_date < DATE(p_period)
                    AND (apl.end_date is NULL OR apl.end_date < DATE(p_period))
                    AND apl.fk_account_id = ag.fk_account_id )
            LEFT OUTER JOIN division_pricelist dpl
                ON dpl.start_date < DATE(p_period)
                    AND (dpl.end_date is NULL OR dpl.end_date < DATE(p_period))
                    AND dpl.fk_division_id = ac.fk_division_id )
            INNER JOIN service_pricelist pr ON pr.id = IFNULL(apl.fk_price_list_id, dpl.fk_price_list_id) )
            INNER JOIN service_price_metric prm ON prm.fk_price_list_id = pr.id AND prm.fk_metric_type_id = ag.fk_metric_type_id )
        WHERE
            prm.price_type = 'THRESHOLD'
            AND ag.period = p_period
            AND ag.fk_account_id = p_accountid
        GROUP BY ag.fk_account_id , ag.fk_metric_type_id, prm.id
        ) dd
        inner JOIN service_price_metric_thresholds spmt on
            dd.fk_service_price_metric_id = spmt.fk_service_price_metric_id
            and dd.consumed >= spmt.from_ammount and dd.consumed < spmt.till_ammount)
        INNER JOIN service_instance si ON dd.fk_service_instance_id = si.id)

        INNER JOIN service_definition sd ON si.fk_service_definition_id = sd.id)
        INNER JOIN service_type st ON sd.fk_service_type_id = st.id)
        INNER JOIN service_plugin_type pt ON st.objclass  = pt.objclass)

        LEFT OUTER JOIN service_link_inst  li ON li.end_service_id  = si.id)
        inner JOIN service_instance sc ON li.start_service_id  = sc.id)
        inner JOIN service_definition scd ON sc.fk_service_definition_id = scd.id)
        inner JOIN service_type sct ON scd.fk_service_type_id = sct.id)
        inner JOIN service_plugin_type cpt ON sct.objclass  = cpt.objclass);
    COMMIT;
END
$$
DELIMITER ;
