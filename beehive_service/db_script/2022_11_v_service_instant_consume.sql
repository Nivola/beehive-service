-- service_stage.v_service_instant_consume_new source
CREATE OR REPLACE VIEW v_service_instant_consume AS
with vms as (
    select
        min(si.creation_date) AS creation_date,
        min(si.modification_date) AS modification_date,
        NULL AS expiry_date,
        min(si.id) AS id,
        'ComputeService' AS plugin_name,
        'vm_numero_vm_tot' AS metric_group_name,
        count(si.id) AS metric_instant_value,
        '#' AS metric_unit,
        count(si.id) AS metric_value,
        min(si.id) AS fk_service_instance_id,
        si.fk_account_id AS fk_account_id,
        1 AS fk_job_id
    from
        service_instance si
        join service_definition sd on (si.fk_service_definition_id = sd.id)
        join service_type st on (sd.fk_service_type_id = st.id)
        join service_plugin_type pt on (st.objclass = pt.objclass)
    where
        si.active = 1
        and pt.name_type = 'ComputeInstance'
    group by
        si.fk_account_id),
dbs as (
    select
        min(si.creation_date) AS creation_date,
        min(si.modification_date) AS modification_date,
        NULL AS expiry_date,
        min(si.id) AS id,
        'DatabaseService' AS plugin_name,
        'db_numero_istanze_tot' AS metric_group_name,
        count(si.id) AS metric_instant_value,
        '#' AS metric_unit,
        count(si.id) AS metric_value,
        min(si.id) AS fk_service_instance_id,
        si.fk_account_id AS fk_account_id,
        1 AS fk_job_id
    from
        service_instance si
        join service_definition sd on (si.fk_service_definition_id = sd.id)
        join service_type st on (sd.fk_service_type_id = st.id)
        join service_plugin_type pt on (st.objclass = pt.objclass)
    where
        si.active = 1
        and pt.name_type = 'DatabaseInstance'
    group by
        si.fk_account_id),
las as (
    select
        min(si.creation_date) AS creation_date,
        min(si.modification_date) AS modification_date,
        NULL AS expiry_date,
        min(si.id) AS id,
        min(pt2.name_type) AS plugin_name,
        min(me.name) AS metric_group_name,
        sum(ac.consumed) AS metric_instant_value,
        min(me.measure_unit) AS metric_unit,
        sum(ac.consumed) AS metric_value,
        min(ac.fk_service_instance_id) AS fk_service_instance_id,
        ac.fk_account_id AS fk_account_id,
        1 AS fk_job_id
    from
        aggregate_cost ac
        join service_instance si on (ac.fk_service_instance_id = si.id)
        join service_definition sd on (si.fk_service_definition_id = sd.id)
        join service_type st on (sd.fk_service_type_id = st.id)
        join service_plugin_type pt on (st.objclass = pt.objclass)
        join service_plugin_type pt2 on (pt.service_category  = pt2.service_category and pt2.category ='CONTAINER')
        left join service_metric_type me on (ac.fk_metric_type_id = me.id)
    where
        ac.period = curdate() + interval -1 day
        and ac.aggregation_type = 'daily'
    group by
        ac.fk_account_id,
        ac.fk_metric_type_id),
vdl as (
    select
        vms.creation_date AS creation_date,
        vms.modification_date AS modification_date,
        vms.expiry_date AS expiry_date,
        vms.id AS id,
        vms.plugin_name AS plugin_name,
        vms.metric_group_name AS metric_group_name,
        vms.metric_instant_value AS metric_instant_value,
        vms.metric_unit AS metric_unit,
        vms.metric_value AS metric_value,
        vms.fk_service_instance_id AS fk_service_instance_id,
        vms.fk_account_id AS fk_account_id,
        vms.fk_job_id AS fk_job_id
    from
        vms
    union all
    select
        dbs.creation_date AS creation_date,
        dbs.modification_date AS modification_date,
        dbs.expiry_date AS expiry_date,
        dbs.id AS id,
        dbs.plugin_name AS plugin_name,
        dbs.metric_group_name AS metric_group_name,
        dbs.metric_instant_value AS metric_instant_value,
        dbs.metric_unit AS metric_unit,
        dbs.metric_value AS metric_value,
        dbs.fk_service_instance_id AS fk_service_instance_id,
        dbs.fk_account_id AS fk_account_id,
        dbs.fk_job_id AS fk_job_id
    from
        dbs
    union all
    select
        las.creation_date AS creation_date,
        las.modification_date AS modification_date,
        las.expiry_date AS expiry_date,
        las.id AS id,
        las.plugin_name AS plugin_name,
        las.metric_group_name AS metric_group_name,
        las.metric_instant_value AS metric_instant_value,
        las.metric_unit AS metric_unit,
        las.metric_value AS metric_value,
        las.fk_service_instance_id AS fk_service_instance_id,
        las.fk_account_id AS fk_account_id,
        las.fk_job_id AS fk_job_id
    from
        las)
select
    vdl.creation_date AS creation_date,
    vdl.modification_date AS modification_date,
    cast(vdl.expiry_date as datetime) AS expiry_date,
    vdl.id AS id,
    vdl.plugin_name AS plugin_name,
    vdl.metric_group_name AS metric_group_name,
    cast(vdl.metric_instant_value as double) AS metric_instant_value,
    vdl.metric_unit AS metric_unit,
    cast(vdl.metric_value as double) AS metric_value,
    vdl.fk_service_instance_id AS fk_service_instance_id,
    vdl.fk_account_id AS fk_account_id,
    vdl.fk_job_id AS fk_job_id
from
    vdl;
