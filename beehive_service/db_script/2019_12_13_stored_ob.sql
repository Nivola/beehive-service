/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2023 CSI-Piemonte

*/


DROP PROCEDURE IF EXISTS `dailycosts`;
DROP PROCEDURE IF EXISTS `dailyconsumes_by_account`;
DROP PROCEDURE IF EXISTS `dailyconsumes`;
DROP PROCEDURE IF EXISTS `dailyconsumes_one_transaction`;
DROP PROCEDURE IF EXISTS `smsmpopulate`;

DELIMITER $$

CREATE PROCEDURE `dailyconsumes`( in p_period varchar(10), in p_jobid  INTEGER )
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_account_id INT;
    DECLARE cur_account CURSOR FOR SELECT id FROM account WHERE creation_date < DATE(p_period) AND (`expiry_date` IS NULL OR `expiry_date` > DATE(p_period));
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur_account;

    account_loop: LOOP
        FETCH cur_account INTO v_account_id;
        IF done THEN

        LEAVE account_loop;
        END IF;
            call dailyconsumes_by_account( v_account_id, p_period, p_jobid) ;
    END LOOP;
  CLOSE cur_account;

  COMMIT;

  UPDATE  aggregate_cost  set was_metric_type_id = fk_metric_type_id  where was_metric_type_id  is null;
  UPDATE  service.aggregate_cost ac
  	join  service.tmp_metric_map_ m  on ac.fk_metric_type_id =  m.from_id
		set fk_metric_type_id = m.to_id
	where
		ac.fk_metric_type_id = ac.was_metric_type_id
		and ac.fk_service_instance_id  in (SELECT fk_service_instance_id from service.tmp_databases_ )
		and ac.period = p_period;

  -- in order to be idempotent
  DELETE from mv_aggregate_consumes where period =p_period;
  insert into mv_aggregate_consumes
	    (organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
	    modification_date, `period`, metric, consumed, measure_unit, container_uuid,
	    container_instance_type, container_type, category
	)
	select organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
	    modification_date, `period`, metric, consumed, measure_unit, container_uuid,
	    container_instance_type, container_type, category
	from v_aggregate_consumes
	where period = p_period;
	commit;
END$$

CREATE PROCEDURE `dailyconsumes_by_account`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
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
END$$

CREATE PROCEDURE `dailyconsumes_one_transaction`( in p_period varchar(10), in jobid  INTEGER )
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
END$$

CREATE PROCEDURE `dailycosts`(in p_period varchar(10), in jobid  INTEGER )
BEGIN
    CALL dailyconsumes(p_period , jobid );
   -- solo consumi

    COMMIT;
END$$

CREATE PROCEDURE `dailycosts_by_account`(in p_period varchar(10), in p_accountid  INTEGER, in jobid  INTEGER )
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
END$$

CREATE  PROCEDURE `smsmpopulate`(in parlimit  INTEGER )
BEGIN
    populate: LOOP

        INSERT INTO service_metric_next_service_metric(fk_sm_id, next_sm_id)
        SELECT sm.id, min(nm.id)
        FROM
            service_metric sm
            INNER JOIN service_metric nm ON
                nm.fk_metric_type_id = sm.fk_metric_type_id
                AND nm.fk_service_instance_id = sm.fk_service_instance_id
                AND nm.id  > sm.id
        where sm.need_next
        GROUP by sm.id
        limit parlimit;




















        IF row_count() > 0 THEN
            update service_metric  m inner join service_metric_next_service_metric mm on m.id = mm.fk_sm_id
            set m.need_next = null where m.need_next ;

            COMMIT;
            ITERATE populate;
        END IF;
        LEAVE populate;
    END LOOP populate;
    COMMIT;
END$$

-- modficata per mariadb
CREATE PROCEDURE `dailyconsumes_by_account_new`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
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

        INSERT INTO aggregate_cost (creation_date, modification_date, `expiry_date`, fk_metric_type_id, cost,
            evaluation_date, fk_service_instance_id, fk_account_id, fk_job_id, aggregation_type, period,
            fk_cost_type_id, consumed)
            WITH
            lastm AS (
                SELECT
                    'lastm' cd_from,
                    FIRST_VALUE(sm.creation_date ) OVER (PARTITION BY sm.fk_service_instance_id , sm.fk_metric_type_id  ORDER BY sm.creation_date DESC ) cd,
                    FIRST_VALUE(sm.metric_num ) OVER (PARTITION BY sm.fk_service_instance_id , sm.fk_metric_type_id  ORDER BY sm.creation_date DESC ) metric_num ,
                    DATE(p_period) ts,
                    UNIX_TIMESTAMP(DATE(p_period)) epoc,
                    FIRST_VALUE(sm.value ) OVER (PARTITION BY sm.fk_service_instance_id , sm.fk_metric_type_id  ORDER BY sm.creation_date DESC ) val,
                    sm.fk_metric_type_id ,
                    sm.fk_service_instance_id
                FROM
                    service_metric sm
                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = p_account_id
                WHERE
                    sm.creation_date  < DATE(p_period)
                GROUP BY sm.fk_metric_type_id, sm.fk_service_instance_id ),
            todaym AS (
                SELECT
                    'today' cd_from,
                    sm.creation_date cd,
                    sm.metric_num,
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
                    metric_num,
                    ts,
                    CASE
                        WHEN LAG (epoc, 1) OVER (  PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY cd DESC)  IS NOT NULL
                            THEN LAG (epoc, 1) OVER (  PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY cd DESC)
                        WHEN cd > DATE(p_period) THEN  UNIX_TIMESTAMP(adddate(p_period,1) )
                        ELSE NULL END  - epoc wt,
                    cd,
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
                computed;
                ;
        COMMIT;
    END IF;
END$$

CREATE DEFINER=`service`@`%` PROCEDURE `service`.`dailyconsumes_by_account_new`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
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
                    -- metric_num,
                    ts,
                    CASE
                        WHEN LAG (epoc, 1) OVER (  PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY id DESC)  IS NOT NULL
                            THEN LAG (epoc, 1) OVER (  PARTITION BY fk_service_instance_id, fk_metric_type_id  ORDER BY id DESC)
                        WHEN cd_from ='today' THEN  UNIX_TIMESTAMP(adddate(p_period,1) )
                        ELSE NULL END  - epoc wt,
                    -- cd,
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
END$$

DELIMITER ;
