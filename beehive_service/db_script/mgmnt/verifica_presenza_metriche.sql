select min (creation_date)  from service_metric sm   ;


select min (period)  from aggregate_cost ac ;


select min (period)  from aggregate_cost_store ac ;





set @dtp='2022-09-01';
set @dtm='2022-09-27';

with  p as (
SELECT  
	ac.fk_metric_type_id id, 
	min(smt.name) name,
	count(ac.id) num
from 
	aggregate_cost ac
	inner join service_metric_type smt  on ac.fk_metric_type_id  = smt.id
where 
	ac.period = @dtp
group by ac.fk_metric_type_id
), m as (
SELECT  
	ac.fk_metric_type_id id, 
	min(smt.name) name,
	count(ac.id) num
from 
	aggregate_cost ac
	inner join service_metric_type smt  on ac.fk_metric_type_id  = smt.id
where 
	ac.period = @dtm
group by ac.fk_metric_type_id
)
select p.id, p.name, p.num, m.num  from p left outer join m on p.id = m.id
order by p.name
;


SELECT  id, name, status from service_job sj order by id desc;


-- CALL  dailyconsumes('2020-07-03', 208328) ;



SELECT id, period,  creation_date , evaluation_date from aggregate_cost ac  order by id DESC ; 


with a as (
	SELECT fk_account_id , COUNT(*) cc
	from aggregate_cost ac  
	where period  ='2020-07-02'
	group by fk_account_id  
), b as (
	SELECT fk_account_id , COUNT(*) cc
	from aggregate_cost ac  
	where period  ='2020-07-01'
	group by fk_account_id  
)
SELECT  b.fk_account_id , a.cc acc, b.cc bcc
from b left outer join a on a.fk_account_id = b.fk_account_id
;
	
--- verifica presnza metriche 

Set @per='2021-06-01';

SELECT  date(@per);
SELECT  adddate(@per, 1);


SELECT si.fk_account_id , COUNT(*) 
from 
	service_metric sm  inner join service_instance si  on sm.fk_service_instance_id  = si.id  
where sm.creation_date > date(@per) and sm.creation_date  < ADDDATE(@per, 1)
GROUP  by si.fk_account_id 
order by si.fk_account_id 
;

SELECT  * from aggregate_cost ac  where fk_account_id  = @acc and period  = @per;

SEt @per='2020-07-01';
set @acc=29;

-- simulazione 
SELECT  * from account a  where id = 287;

SELECT 
	sm.creation_date , sm.id -- COUNT(*) -- into smetrics
FROM
    service_metric sm
    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id
WHERE
	sm.creation_date >=  DATE(@per)
    AND sm.creation_date <  adddate(@per,1) AND si.fk_account_id = @acc
order by sm.id  desc ;


SELECT 
	@per, COUNT(*) 
from 
	service_metric sm  
where 
	sm.creation_date >=  DATE(@per)
    AND sm.creation_date <  adddate(@per,1)
;

    SELECT
                NOW() creation_date,
                NOW() modification_date,
                NULL, 
                dd.fk_metric_type_id fk_metric_type_id,
                0,  
                NOW() evaluation_date,
                dd.fk_service_instance_id fk_service_instance_id,
                min(dd.account_id) account_id,
                -- jobid,  
                'daily',  
                @per,  
                CASE count(*) WHEN 1 THEN 2 else 1 end fk_cost_type_id,
                ifnull(sum(value * wt) / sum(wt) , 0)  consumed           
            FROM ( 
                    SELECT 
                        
                        sm.creation_date,
                        UNIX_TIMESTAMP(nm.creation_date)- UNIX_TIMESTAMP(DATE(@per)) wt,
                        sm.value,
                        sm.fk_metric_type_id ,
                        sm.fk_service_instance_id,
                        si.fk_account_id account_id
                    FROM
                        service_metric sm
                        INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = @acc
                        INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                        INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                        INNER JOIN ( SELECT
                                    max(sm.creation_date) creation_date,
                                    sm.fk_metric_type_id ,
                                    sm.fk_service_instance_id
                                FROM
                                    service_metric sm
                                    INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = @acc
                                WHERE sm.creation_date <  DATE(@per)
                                GROUP BY sm.fk_metric_type_id, sm.fk_service_instance_id) prevt
                        ON sm.creation_date=prevt.creation_date AND sm.fk_metric_type_id = prevt.fk_metric_type_id
                            AND sm.fk_service_instance_id = prevt.fk_service_instance_id
                union
                    SELECT 
                        
                        sm.creation_date,
                        CASE 
			            	WHEN sm.creation_date = nm.creation_date THEN 1
			            	WHEN nm.creation_date < adddate(@per,1) THEN UNIX_TIMESTAMP(nm.creation_date)- UNIX_TIMESTAMP(sm.creation_date)
			            	ELSE abs(UNIX_TIMESTAMP(adddate(@per,1))- UNIX_TIMESTAMP(sm.creation_date)) END wt,
			            sm.value,
                        sm.fk_metric_type_id ,
                        sm.fk_service_instance_id,
                        si.fk_account_id account_id
                    FROM
                        service_metric sm
                        INNER JOIN service_metric_next_service_metric rn ON sm.id = rn.fk_sm_id
                        INNER JOIN service_metric nm ON nm.id = rn.next_sm_id
                        INNER JOIN service_instance si ON sm.fk_service_instance_id = si.id AND si.fk_account_id = @acc
                    WHERE
                        sm.creation_date >=  DATE(@per)
                        AND sm.creation_date <  adddate(@per,1)
                    ) dd 
                    GROUP by dd.fk_metric_type_id, dd.fk_service_instance_id
                ;