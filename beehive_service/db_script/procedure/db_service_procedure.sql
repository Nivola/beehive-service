-- MySQL dump 10.16  Distrib 10.1.48-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: 10.138.144.135    Database: service
-- ------------------------------------------------------
-- Server version	10.4.11-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping routines for database 'service'
--
/*!50003 DROP PROCEDURE IF EXISTS `dailyconsumes` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailyconsumes`( IN p_period VARCHAR(10), IN p_jobid  INTEGER )
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_account_id INT;
    DECLARE cur_account CURSOR FOR SELECT id FROM account WHERE creation_date < DATE(p_period) AND (expiry_date IS NULL OR expiry_date > DATE(p_period));
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur_account;

    account_loop: LOOP
        FETCH cur_account INTO v_account_id;
        IF done THEN
            LEAVE account_loop;
        END IF;
            
            CALL dailyconsumes_by_account_new( v_account_id, p_period, p_jobid) ;
            
    END LOOP;
    CLOSE cur_account;

    COMMIT;

  	CALL patch_db(p_period);
    -- CALL normalize_os(p_period);
    commit;
 	CALL expose_consumes(p_period);
    COMMIT;
    
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `dailyconsumes_by_account` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailyconsumes_by_account`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `dailyconsumes_by_account_new` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailyconsumes_by_account_new`( in p_account_id integer, in p_period varchar(10), in jobid  INTEGER )
BEGIN
    DECLARE smetrics INT;
   	-- commit;
    select count(*) into smetrics  from aggregate_cost ac where period  = p_period and fk_account_id  = p_account_id ;

    IF smetrics = 0 THEN
    	start transaction;
        
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `dailyconsumes_one_transaction` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailyconsumes_one_transaction`( in p_period varchar(10), in jobid  INTEGER )
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `dailycosts` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailycosts`(in p_period varchar(10), in jobid  INTEGER )
BEGIN
    CALL dailyconsumes(p_period , jobid );
   -- solo consumi
   
    COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `dailycosts_by_account` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `dailycosts_by_account`(in p_period varchar(10), in p_accountid  INTEGER, in jobid  INTEGER )
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `do_monit` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `do_monit`(  )
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `expose_consumes` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `expose_consumes`(in p_period varchar(10) )
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
        INNER JOIN service_metric_type me ON ac.fk_metric_type_id = me.id
    WHERE 
    	ac.period = p_period 
    	and ac.aggregation_type = 'daily'
    GROUP BY
        ac.period, ac.fk_account_id ,  ac.fk_metric_type_id
    ;
    COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `expose_consumes_metric` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `expose_consumes_metric`(in p_period varchar(10), in metrictype int )
BEGIN
 	declare metricname varchar(50);
	
	select name into metricname from service_metric_type where id = metrictype;
	DELETE from mv_aggregate_consumes where period=p_period and metric = metricname;
	insert into mv_aggregate_consumes 
		    (organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date, 
		    modification_date, `period`, metric, consumed, measure_unit, container_uuid, 
	    	container_instance_type, container_type, category
			)
	select organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date, 
	    modification_date, `period`, metric, consumed, measure_unit, container_uuid, 
	    container_instance_type, container_type, category
	from v_aggregate_consumes  
	where period = p_period and metric=metricname;
	commit;

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `normalize_os` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `normalize_os`( IN p_period VARCHAR(10))
BEGIN
    -- insert vm mancanti
    insert into tmp_os_ (fk_service_id, metric_type)
    SELECT  
        si.id , 
        CONCAT('vm_',
        case 		
            when json_value( simc.json_cfg, '$.resource_oid') like 'Centos%' then 'centos'
            when json_value( simc.json_cfg, '$.resource_oid') like 'Ubuntu%' then 'ubuntu'
            when json_value( simc.json_cfg, '$.resource_oid') like '%Win%' then 'windows'
            when json_value( simc.json_cfg, '$.resource_oid') like 'windows%' then 'windows'
            when json_value( simc.json_cfg, '$.resource_oid') like 'mssql%' then 'db_mssql'
            when json_value( simc.json_cfg, '$.resource_oid') like 'RedhatLinux%' then 'redhatlinux'
            when json_value( simc.json_cfg, '$.resource_oid') like 'OracleLinux%' then 'oraclelinux'		
            when json_value( simc.json_cfg, '$.resource_oid') like 'Oracle%' then 'db_oracle'		
            else 'nd' 
        end, '_', 	COALESCE (json_value( sic.json_cfg, '$.type'), 'nd'))   
    from 
        service_instance si
        inner join service_instance_config sic on sic.fk_service_instance_id  = si.id 
        inner join service_definition sd  on sd.id = si.fk_service_definition_id
        inner join service_instance sim on sim.uuid = json_value( sic.json_cfg, '$.instance.ImageId')
        inner join service_instance_config simc on simc.fk_service_instance_id  = sim.id 
        INNER  JOIN service_type st  on st.id = sd.fk_service_type_id 
        left outer join tmp_os_ ts on si.id = ts.fk_service_id
    where
        ts.fk_service_id is null
        and si.active=1 
        and st.name = 'ComputeInstanceSync'
        and json_value( sic.json_cfg, '$.type') is not null
    ;
    commit;

    -- calcola 
    UPDATE tmp_os_ 
    set fk_metric_type_id = (select smt.id from service_metric_type smt where smt.name = tmp_os_.metric_type)
    where fk_metric_type_id is null;

    update 
        aggregate_cost ac 
        inner join tmp_os_ ts  on ac.fk_service_instance_id = ts.fk_service_id
    set 
        ac.fk_metric_type_id  = ts.fk_metric_type_id 
    where 
        ac.consumed > 0
        and ac.fk_metric_type_id  = ac.was_metric_type_id 
        and ac.fk_metric_type_id  in  (4, 6)  
        and period = p_period ;
    commit;

  COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `patch_db` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `patch_db`(IN p_period VARCHAR(10))
BEGIN

    UPDATE  aggregate_cost  SET was_metric_type_id = fk_metric_type_id  WHERE was_metric_type_id  IS NULL and period =p_period  ;
    UPDATE
        service.aggregate_cost ac
        INNER JOIN  service.tmp_databases_  d ON d.fk_service_instance_id = ac.fk_service_instance_id
        INNER JOIN  service.tmp_metric_map_ m  ON ac.fk_metric_type_id =  m.from_id AND m.dbtype = d.dbtype and m.active = 1
        SET fk_metric_type_id = m.to_id
    WHERE
        ac.fk_metric_type_id = ac.was_metric_type_id
        AND d.active = 1
        AND ac.fk_metric_type_id !=  m.to_id
        AND ac.period = p_period
        and ac.fk_cost_type_id = 1
        AND ac.consumed  > 0
       ;

	commit;
     
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `smsmpopulate` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_unicode_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'IGNORE_SPACE,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `smsmpopulate`(in parlimit  INTEGER )
BEGIN
    -- populate: LOOP

       -- INSERT INTO service_metric_next_service_metric(fk_sm_id, next_sm_id)
       -- SELECT sm.id, min(nm.id)
       -- FROM
       --     service_metric sm
       --     INNER JOIN service_metric nm ON
       --         nm.fk_metric_type_id = sm.fk_metric_type_id
       --         AND nm.fk_service_instance_id = sm.fk_service_instance_id
       --         AND nm.id  > sm.id
       -- where sm.need_next
       -- GROUP by sm.id
       -- limit parlimit;
       --           
       -- IF row_count() > 0 THEN
       --     update service_metric  m inner join service_metric_next_service_metric mm on m.id = mm.fk_sm_id
       --     set m.need_next = null where m.need_next ;
       --
       --     COMMIT;
       --     ITERATE populate;
       -- END IF;
       -- LEAVE populate;
    -- END LOOP populate;
    COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `svecchia_consumi` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `svecchia_consumi`()
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
    END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `svecchia_consumiaggregati` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `svecchia_consumiaggregati`()
BEGIN
    DECLARE dtarget date ;
   	DECLARE afected integer;
   	DECLARE itercount integer;
    
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `svecchia_dati` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `svecchia_dati`()
BEGIN
    call service.svecchia_metriche();
    call service.svecchia_consumi();
    call service.svecchia_consumiaggregati();
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `svecchia_metriche` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = latin1 */ ;
/*!50003 SET character_set_results = latin1 */ ;
/*!50003 SET collation_connection  = latin1_swedish_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`service`@`%` PROCEDURE `svecchia_metriche`()
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
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-10-12 13:50:49
