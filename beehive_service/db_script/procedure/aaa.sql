DROP PROCEDURE IF EXISTS service.svecchia_consumi;
DELIMITER ;;
CREATE PROCEDURE service.svecchia_consumi()
BEGIN
    DECLARE dtarget varchar(10);
    DECLARE afected integer;
   	DECLARE itercount integer;

    DECLARE max_id integer;
   	DECLARE min_id integer;

    select least( min(period), date_add(CURDATE(), INTERVAL -370 DAY) ) INTO dtarget from aggregate_cost ;



    select  CONCAT('DELETING  aggregate_cost UNTIL ',dtarget) AS MSG;
    SELECT  min(id) INTO min_id FROM aggregate_cost ac WHERE period  = dtarget;
    SELECT 0 INTO itercount;
    REPEAT
        SELECT id INTO max_id  FROM aggregate_cost ac WHERE id >= min_id AND period = dtarget ORDER BY id LIMIT 5000,1;
        IF max_id  is NULL THEN
            DELETE FROM aggregate_cost WHERE period = dtarget;
            SELECT ROW_COUNT() INTO afected;
            SELECT itercount + 1 INTO itercount;
            SELECT CONCAT('DELETING LAST aggregate_cost UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
        ELSE
            DELETE FROM aggregate_cost WHERE id BETWEEN min_id AND max_id and period = dtarget;
            SELECT ROW_COUNT() INTO afected;
            SELECT itercount + 1 INTO itercount;
            SELECT CONCAT('DELETING aggregate_cost UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
            DO SLEEP(0.5);
        END IF;
    UNTIL max_id  is NULL
    END REPEAT;
END;


;;
DELIMITER ;