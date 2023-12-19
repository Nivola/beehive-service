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

DROP PROCEDURE IF EXISTS service.svecchia_metriche;
DELIMITER $$
CREATE PROCEDURE service.svecchia_metriche()
BEGIN
    DECLARE dtarget date ;
   	DECLARE afected integer;
   	DECLARE itercount integer;
    select least(
        date_add(date(min(creation_date)), INTERVAL 1 DAY),
        date_add(CURDATE(), INTERVAL -110 DAY)
        ) into dtarget
    from service_metric;
    select  CONCAT('DELETING service_metric UNTIL ',dtarget) AS MSG;
    select 0 into itercount;
	REPEAT
         delete from service_metric where creation_date<dtarget LIMIT 5000;
         select ROW_COUNT() into afected;
         select itercount + 1 into itercount;
         SELECT CONCAT('DELETING service_metric UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
         DO SLEEP(0.5);
    UNTIL afected < 5000 END REPEAT;
END;
$$
DELIMITER ;

DROP PROCEDURE IF EXISTS service.svecchia_consumi;
DELIMITER $$
CREATE PROCEDURE service.svecchia_consumi()
BEGIN
    DECLARE dtarget date ;
   	DECLARE afected integer;
   	DECLARE itercount integer;
    select least(
        date_add(date(min(creation_date)), INTERVAL 1 DAY),
        date_add(CURDATE(), INTERVAL -370 DAY)
        ) into dtarget
    from aggregate_cost;
    select  CONCAT('DELETING  aggregate_cost UNTIL ',dtarget) AS MSG;
    select 0 into itercount;
	REPEAT
         delete from aggregate_cost where creation_date<dtarget LIMIT 5000;
         select ROW_COUNT() into afected;
         select itercount + 1 into itercount;
         SELECT CONCAT('DELETING aggregate_cost UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
         DO SLEEP(0.5);
    UNTIL afected < 5000 END REPEAT;
    END;
$$
DELIMITER ;

DROP PROCEDURE IF EXISTS service.svecchia_consumiaggregati;
DELIMITER $$
CREATE PROCEDURE service.svecchia_consumiaggregati()
BEGIN
    DECLARE dtarget date ;
   	DECLARE afected integer;
   	DECLARE itercount integer;
    -- mv_aggregate_consumes
    select least(
        date_add(date(min(creation_date)), INTERVAL 1 DAY),
        date_add(CURDATE(), INTERVAL -370 DAY)
        ) into dtarget
    from mv_aggregate_consumes;
    select 0 into itercount;
    select  CONCAT('DELETING  mv_aggregate_consumes UNTIL ',dtarget) AS MSG;
	REPEAT
         delete from mv_aggregate_consumes where creation_date<dtarget LIMIT 5000;
         select ROW_COUNT() into afected;
         select itercount + 1 into itercount;
         SELECT CONCAT('DELETING mv_aggregate_consumes UNTIL ',dtarget, ' deleted ', afected,  ' rows at' , now(), ' iter ', itercount)  AS MSG;
         DO SLEEP(0.5);
    UNTIL afected < 5000 END REPEAT;
END;
$$
DELIMITER ;