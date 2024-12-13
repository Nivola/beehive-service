/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
set @dt='2022-09-30';

select min (period)  from aggregate_cost ac ;



select min (period)  from aggregate_cost_store ac ;



-- SELECT count(*) from (select id from aggregate_cost ac where period  = @dt and fk_account_id  = 9999 limit 4) a ;
-- select count(*)  from aggregate_cost ac where period  = @dt and fk_account_id  = 69 ;
-- SELECT count(*) from (select id from aggregate_cost ac where period  = @dt and fk_account_id  = 9999 limit 4) a ;

-- consumi_servizio_gioralieri
with a as (
    SELECT
        ac.period,
        COUNT(*) num,
        count(DISTINCT ac.fk_account_id) accounts,
        count(DISTINCT ac.fk_service_instance_id) services,
        COUNT( DISTINCT ac.fk_metric_type_id) metrics
    FROM
        aggregate_cost ac
    WHERE period  >= @dt
    GROUP BY period
)
SELECT
    a.period prd,
    DATEDIFF(lag(a.period) over (order by period) , a.period) = -1 ckprd,
    a.num,
    abs(lag(a.num) over (order by period) - a.num) < (0.2* a.num) cknum ,
    a.accounts acc,
    abs(lag(a.accounts) over (order by period) - a.accounts) < (0.05* a.accounts) ckacc,
    a.services srv,
    abs(lag(a.services) over (order by period) - a.services) < (0.2* a.services) cksrv,
    a.metrics mts,
    abs(lag(a.metrics) over (order by period) - a.metrics) = 0 ckmts
FROM
    a
order by period
;

-- consumi_account_giornalieri
with a as (
	SELECT
	    mac.period,
	    COUNT(*) num,
	    count(DISTINCT mac.account_uuid) accounts,
	    COUNT( DISTINCT mac.metric) metrics
	FROM
	    mv_aggregate_consumes mac
	WHERE period  >= @dt
	GROUP BY period
)
SELECT
    a.period prd,
    DATEDIFF(lag(a.period) over (order by period) , a.period) = -1 ckprd,
    a.num,
    abs(lag(a.num) over (order by period) - a.num) < (0.2* a.num) cknum ,
    a.accounts acc,
    abs(lag(a.accounts) over (order by period) - a.accounts) < (0.05* a.accounts) ckacc,
    a.metrics mts,
    abs(lag(a.metrics) over (order by period) - a.metrics) = 0 ckmts
FROM
    a
order by period
;

set @dtm='2022-06-18';
set @dtp='2022-06-17';
select GROUP_CONCAT(distinct metric)
from mv_aggregate_consumes mac
where period  ='2022-06-17';

SELECT
	ac.fk_metric_type_id id,
	min(smt.name) name,
	count(*) num
from
	aggregate_cost ac
	inner join service_metric_type smt  on ac.fk_metric_type_id  = smt.id
where ac.period = @dtp
group by ac.fk_metric_type_id
;

select 1;

call dailyconsumes ('2022-09-15',1);

-- call dailyconsumes ('2021-10-21',1);

-- CALL expose_consumes('2021-09-28');
-- CALL expose_consumes('2021-09-29');


-- SELECT
-- 	ac.period ,
-- 	GROUP_CONCAT(distinct ac.fk_metric_type_id  order by fk_metric_type_id  ),
-- 	GROUP_CONCAT(distinct smt.name order by fk_metric_type_id  )
-- from
-- 	aggregate_cost	ac
-- 	inner join service_metric_type smt  on ac.fk_metric_type_id  = smt.id
-- where  ac.period in ('2021-09-17','2021-09-18','2021-09-19')
-- GROUP by ac.period
-- ;


-- SELECT
-- 	smt.id, smt.name
-- from service_metric_type smt
-- where id in (40,41,42,43,53)
-- ;


-- SELECT COUNT(*) from aggregate_cost ac  where period = '2021-07-02';

set @dt='2021-12-28';
set @soglia=0.9;

select DATE_ADD(@dt, INTERVAL -1 DAY);

-- accont mancanti a @dt
with
	a as (select DISTINCT ac.fk_account_id from aggregate_cost ac WHERE period = DATE_ADD(@dt, INTERVAL -1 DAY)),
 	b as (select DISTINCT ac.fk_account_id from aggregate_cost ac WHERE period = @dt)
SELECT
	a.fk_account_id
from a left outer join b on a.fk_account_id = b.fk_account_id
where b.fk_account_id is null
;




SELECT
	date(sm.creation_date),
	sm.fk_metric_type_id, smt.name ,avg(sm.value) , si.fk_account_id, count(*)
from
	service_metric sm
	inner join service_instance si  on si.id = sm.fk_service_instance_id
	inner join service_metric_type smt  on sm.fk_metric_type_id  = smt.id
group by date(sm.creation_date), sm.fk_metric_type_id, smt.name,  si.fk_account_id
where sm.creation_date  > '2021-06-29'
and si.fk_account_id  in (844, 847, 850, 853, 856, 859, 862, 868, 871, 877, 880,
883, 886, 892, 895, 898, 906, 909, 912, 915, 917, 920,
926, 933, 936, 939, 944, 950, 953, 959, 962, 965)
order by sm.creation_date, si.fk_account_id
;

-- comparazione per consume giornalieri di accouant
with
 a as (SELECT
 account_uuid , metric , period, sum(consumed) consumed
from
	mv_aggregate_consumes mac
where mac.period  = DATE_ADD(@dt, INTERVAL -1  DAY)
group by
	account_uuid , metric , period
),
 b as (SELECT
 account_uuid , metric , period, sum(consumed) consumed
from
	mv_aggregate_consumes mac
where mac.period  = @dt
group by
	account_uuid , metric , period
)
select
	a.account_uuid ,
	a.metric ,
	a.period,
	b.period,
	a.consumed,
	b.consumed
from
 	a
 	left outer join b on a.account_uuid=b.account_uuid and  a.metric=b.metric
 where
 	b.consumed is null
 	or b.consumed < (a.consumed* @soglia)
order by a.account_uuid , a.metric
 ;


-- comparazione tra consumi_giornalieri
with
 a as (SELECT
 c.fk_account_id ,  c.fk_metric_type_id,  t.name metric , c.period, sum(c.consumed) consumed
from
	aggregate_cost c
	inner join service_metric_type t on t.id=c.fk_metric_type_id
where c.period  = DATE_ADD(@dt, INTERVAL -1  DAY)
group by
	c.fk_account_id , c.fk_metric_type_id , t.name  , c.period
),
 b as (SELECT
 c.fk_account_id ,  c.fk_metric_type_id,  t.name metric , c.period, sum(c.consumed) consumed
from
	aggregate_cost c
	inner join service_metric_type t on t.id=c.fk_metric_type_id
where c.period  = @dt
group by
	c.fk_account_id , c.fk_metric_type_id, t.name , c.period)
select
	a.fk_account_id ,
	a.fk_metric_type_id,
	a.metric,
	a.period,
	b.period,
	a.consumed,
	b.consumed
from
 	a
 	left outer join b on a.fk_account_id = b.fk_account_id  and  a.fk_metric_type_id = b.fk_metric_type_id
 where
 	b.consumed is null
 	or b.consumed < (a.consumed* @soglia )
order by a.fk_account_id , a.fk_metric_type_id
 ;


SELECT  @dt;
SELECT  count(*) from mv_aggregate_consumes mac  where period  = @dt;
SELECT  count(*) from mv_aggregate_consumes mac  where period  = DATE_ADD(@dt, INTERVAL -1 DAY);

SELECT  * from mv_aggregate_consumes mac  where period  = @dt;



set @v_l_id=(SELECT  max(id) from service_metric sm  where creation_date < @p_date);
set @v_f_id=(SELECT  min(id) from service_metric sm  where creation_date < @p_date);

set @mid=(select max(id) from service_metric sm  where creation_date < date('2021-01-01'));
SELECT * from service_metric sm where id <= @mid order by id;



select count(*) from service_metric sm  where creation_date  BETWEEN   '2022-06-06' and '2022-06-07';




SELECT
st.name tipo, sd.name  def, si.name serv, ac.period ,  smt.name  metrica , ac.consumed  value, ac.fk_metric_type_id , ac.fk_service_instance_id
FROM
	aggregate_cost ac
	inner join	service_instance si  on ac.fk_service_instance_id  = si .id
	inner join  service_metric_type smt  on ac.fk_metric_type_id  = smt.id
	INNER JOIN  service_definition sd  on si.fk_service_definition_id  = sd.id
	inner join service_type st  on sd.fk_service_type_id  = st.id
	inner join account a  on si.fk_account_id  = a.id
where
 a.uuid = '<uuid>'
 and period = '2022-05-30'
 and smt.name  like 'vm_gb%'
 and consumed  > 0
 order by ac.fk_service_instance_id , period ;


select * from service_metric sm
where
	fk_metric_type_id  =17
	and fk_service_instance_id = 113942
	and period = '2022-05-30';




<uuid>



select a.name , a.uuid , si.name , si.uuid , si.resource_uuid
from
	service_instance si
	INNER JOIN  service_definition sd  on si.fk_service_definition_id  = sd.id
	inner join service_type st  on sd.fk_service_type_id  = st.id
	inner join account a  on si.fk_account_id  = a.id
where
	st.name = 'NetworkGatewaySync';

select * from service_type st ;
