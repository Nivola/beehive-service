-- # SPDX-License-Identifier: EUPL-1.2
-- #
-- # (C) Copyright 2021-2022 CSI-Piemonte



CREATE TABLE IF NOT EXISTS parameter_monit (
  parameter VARCHAR(50) NOT NULL,
  tval TEXT,
  nval REAL,
  PRIMARY KEY (parameter)
);

CREATE TABLE IF NOT EXISTS log_monit (
  period  varchar(10) NOT NULL,
  msg TEXT,
  recipient TEXT,
  PRIMARY KEY (period)
);


-- CALL do_monit();
-- SELECT msg, recipent FROM log_monit WHERE period = DATE_SUB(DATE(NOW()), INTERVAL 1 DAY);

SELECT log_monit.period AS log_monit_period, log_monit.msg AS log_monit_msg, log_monit.recipient AS log_monit_recipient
FROM log_monit
WHERE log_monit.period = '';

DROP PROCEDURE service.do_monit;
DELIMITER $$
CREATE PROCEDURE do_monit(  )
BEGIN
    DECLARE v_account_ok INT;
    DECLARE v_metric_ok INT;
    DECLARE v_service_ok INT;
    DECLARE v_threshold  real;
    DECLARE v_res  TEXT;
    DECLARE v_recipeinets  TEXT;

    SET v_res = '';
    SET v_threshold = 0.33;
    SET v_recipeinets = 'gianni.doria@consulenti.csi.it';
    WITH
    a AS (
        SELECT
            period,
            COUNT(*) num,
            count(DISTINCT fk_account_id) accounts,
            count(DISTINCT fk_service_instance_id) services,
            COUNT( DISTINCT fk_metric_type_id) metrics
        FROM
            aggregate_cost ac
        WHERE ac.period  =  DATE_SUB(date(now()), INTERVAL 3 day)
        GROUP BY ac.period
    ),
    b AS (
        SELECT
            period,
            COUNT(*) num,
            count(DISTINCT fk_account_id) accounts,
            count(DISTINCT fk_service_instance_id) services,
            COUNT( DISTINCT fk_metric_type_id) metrics
        FROM
            aggregate_cost ac
        WHERE period  =  DATE_SUB(date(now()), INTERVAL 2 day)
        GROUP BY period
    )
    SELECT
        (a.metrics <= b.metrics  ) AS metrics_ok,
        (abs(a.accounts - b.accounts) >  (a.accounts * 0.33) ) AS accounts_ok,
        (abs(a.services - b.services) <  (a.services * 0.33) ) AS service_ok
    INTO
        v_metric_ok,
        v_account_ok,
        v_service_ok
    FROM a, b ;

    IF (v_metric_ok = 0) THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi giornalieri, anomalia nella cardinalità delle metriche' );
    END IF;
    IF (v_account_ok = 0) THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi giornalieri, anomalia nella cardinalità degli accounts');
    END IF;
    IF (v_service_ok = 0) THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi giornalieri, anomalia nella cardinalità dei services');
    END IF;

    -- consumi esposti
    WITH
    a AS (
        SELECT
            period,
            COUNT(*) num,
            count(DISTINCT account_uuid ) accounts,
            count(DISTINCT container_uuid ) services,
            COUNT( DISTINCT metric ) metrics
        FROM
            mv_aggregate_consumes
        WHERE period  =  DATE_SUB(date(now()), INTERVAL 3 day)
        GROUP BY period
    ),
    b AS (
        SELECT
            period,
            COUNT(*) num,
            count(DISTINCT account_uuid) accounts,
            count(DISTINCT container_uuid) services,
            COUNT( DISTINCT metric) metrics
        FROM
            mv_aggregate_consumes
        WHERE period  =  DATE_SUB(date(now()), INTERVAL 1 DAY)
        GROUP BY period
    )
    SELECT
        (a.metrics <= b.metrics  ) AS metrics_ok,
        (abs(a.accounts - b.accounts) <  (a.accounts * 0.33) ) AS accounts_ok,
        (abs(a.services - b.services) <  (a.services * 0.33) ) AS service_ok
    INTO
        v_metric_ok,
        v_account_ok,
        v_service_ok
    FROM a, b ;

    IF    v_metric_ok = 0 THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi esposti, anomalia nella cardinalità delle metriche' );
    END IF;
    IF    v_account_ok = 0 THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi esposti, anomalia nella cardinalità degli accounts');
    END IF;
    IF    v_service_ok = 0 THEN
        SET v_res = CONCAT(v_res, 'Attenzione! consumi esposti, anomalia nella cardinalità dei services');
    END IF;
    IF  (LENGTH(v_res) > 0) THEN
        BEGIN
            DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
                UPDATE  log_monit
                SET msg =  v_res, recipent = v_recipeinets
                WHERE period = DATE_SUB(date(now()), INTERVAL 1 DAY);
            INSERT INTO
                log_monit ( period  , msg , recipent )
            VALUES
                (DATE_SUB(date(now()), INTERVAL 1 DAY), v_res, v_recipeinets);
        END;
    END IF;
END
$$

DELIMITER ;
