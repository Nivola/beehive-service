DROP PROCEDURE IF EXISTS service.svecchia_dati;

DELIMITER $$
CREATE OR REPLACE PROCEDURE service.svecchia_dati()
BEGIN
    DECLARE dtarget date ;
    select least(
        date_add(date(min(creation_date)), INTERVAL 1 DAY),
        date_add(CURDATE(), INTERVAL -365 DAY)
        ) into dtarget
    from service_metric;
    select 'deleting  until' || dtarget;
	-- REPEAT
    --     delete from service_metric where creation_date<dtarget LIMIT 5000;
    --     SELECT ' deleted '|| ROW_COUNT() || ' rows at' || now() ;
    --     DO SLEEP(1);
    -- UNTIL ROW_COUNT() = 0 END REPEAT;
END$$
DELIMITER ;

CALL service.svecchia_dati()
