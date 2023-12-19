DROP PROCEDURE IF EXISTS service.svecchia_dati;
DELIMITER $$
CREATE PROCEDURE service.svecchia_dati()
BEGIN
    call service.svecchia_metriche();
    call service.svecchia_consumi();
    call service.svecchia_consumiaggregati();
END;
$$
DELIMITER ;


DROP PROCEDURE IF EXISTS service.svecchia_consumi;
DELIMITER $$
CREATE PROCEDURE service.svecchia_consumi()
BEGIN
    DECLARE dtarget VARCHAR ;
    DECLARE afected INTEGER;
    DECLARE itercount INTEGER;
    DECLARE minid INTEGER;
    DECLARE maxid INTEGER;
    select least(
        min(period),
        date_add(CURDATE(), INTERVAL -370 DAY)
        ) INTO dtarget
    from aggregate_cost;
    select  CONCAT('DELETING  aggregate_cost UNTIL ',dtarget) AS MSG;
    SELECT  min(id) INTO minid FROM aggregate_cost ac WHERE period  = dtarget;
    SELECT 0 INTO itercount;
    REPEAT
        SELECT id INTO maxid FROM aggregate_cost ac WHERE id >= minid AND period  = dtarget ORDER BY id LIMIT 5000,1;
        IF maxid is NULL THEN
            DELETE FROM aggregate_cost WHERE period = dtarget;
            SELECT ROW_COUNT() INTO afected;
            SELECT itercount + 1 INTO itercount;
            SELECT CONCAT('DELETING LAST aggregate_cost UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
        ELSE
            DELETE FROM aggregate_cost WHERE id BETWEEN minid AND maxidand period = dtarget;
            SELECT ROW_COUNT() INTO afected;
            SELECT itercount + 1 INTO itercount;
            SELECT CONCAT('DELETING aggregate_cost UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
            DO SLEEP(0.5);
        END IF;
    UNTIL maxid is NULL
    END REPEAT;
    END;
$$
DELIMITER ;

DROP PROCEDURE IF EXISTS service.svecchia_consumiaggregati;
DELIMITER $$
CREATE PROCEDURE service.svecchia_consumiaggregati()
BEGIN
    DECLARE dtarget date ;
       DECLARE afected INTEGER;
       DECLARE itercount INTEGER;
    -- mv_aggregate_consumes
    select least(
        date_add(date(min(creation_date)), INTERVAL 1 DAY),
        date_add(CURDATE(), INTERVAL -370 DAY)
        ) INTO dtarget
    from mv_aggregate_consumes;
    select 0 INTO itercount;
    select  CONCAT('DELETING  mv_aggregate_consumes UNTIL ',dtarget) AS MSG;
    REPEAT
         delete from mv_aggregate_consumes WHERE creation_date<dtarget LIMIT 5000;
         select ROW_COUNT() INTO afected;
         select itercount + 1 INTO itercount;
         SELECT CONCAT('DELETING mv_aggregate_consumes UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
         DO SLEEP(0.5);
    UNTIL afected < 5000 END REPEAT;
END;
$$
DELIMITER ;