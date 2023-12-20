/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2020-2023 CSI-Piemonte

*/


-- DROP DROP TABLE IF EXISTS service.v_service_instant_consume;

CREATE OR REPLACE VIEW `v_service_instant_consume` AS
with recursive tree as (
    select
        `t1`.`start_service_id` AS `parent_id`, `t1`.`start_service_id` AS `child_id`, 0 AS `dep`
    from
        (`service_link_inst` `t1`
        left join `service_link_inst` `t2` on (`t1`.`start_service_id` = `t2`.`end_service_id`))
    where
        `t2`.`id` is null
    group by
        `t1`.`start_service_id`
    union
    select
        `t1`.`start_service_id` AS `parent_id`, `t1`.`end_service_id` AS `child_id`, 1 AS `dep`
    from
        (`service_link_inst` `t1`
        left join `service_link_inst` `t2` on (`t1`.`start_service_id` = `t2`.`end_service_id`))
    where
        `t2`.`id` is null
    union
    select
        `c`.`parent_id` AS `parent_id`, `t2`.`end_service_id` AS `child_id`, `c`.`dep` + 1 AS `dep`
    from
        (`tree` `c`
        join `service_link_inst` `t2` on (`t2`.`start_service_id` = `c`.`child_id`))),
lsm as (
    select straight_join
        max(`sm`.`id`) AS `id`, `si`.`fk_account_id` AS `fk_account_id`, `si`.`id` AS `fk_service_id`, min(`si`.`fk_service_definition_id`) AS `fk_service_definition_id`, `sm`.`fk_metric_type_id` AS `fk_metric_type_id`
    from
        (`service_instance` `si`
        join `service_metric` `sm` on (`sm`.`fk_service_instance_id` = `si`.`id`))
    where
        `sm`.`creation_date` > current_timestamp() - interval 1 day
    group by
        `si`.`fk_account_id`, `si`.`id`, `sm`.`fk_metric_type_id`),
bymetrics as (
    select straight_join
        `sm`.`creation_date` AS `creation_date`, `sm`.`modification_date` AS `modification_date`, NULL AS `expiry_date`, `sm`.`id` AS `id`, `pt`.`name_type` AS `plugin_name`, `mt`.`name` AS `metric_group_name`, `sm`.`value` AS `metric_instant_value`, `mt`.`measure_unit` AS `metric_unit`, NULL AS `metric_value`, `psi`.`id` AS `fk_service_instance_id`, `lsm`.`fk_account_id` AS `fk_account_id`, `sm`.`fk_job_id` AS `fk_job_id`
    from
        (((((((`lsm`
        join `tree` on (`lsm`.`fk_service_id` = `tree`.`child_id`))
        join `service_metric` `sm` on (`lsm`.`id` = `sm`.`id`))
        join `service_instance` `psi` on (`psi`.`id` = `tree`.`parent_id`))
        join `service_definition` `sd` on (`psi`.`fk_service_definition_id` = `sd`.`id`))
        join `service_type` `st` on (`sd`.`fk_service_type_id` = `st`.`id`))
        join `service_plugin_type` `pt` on (`pt`.`objclass` = `st`.`objclass`))
        join `service_metric_type` `mt` on (`sm`.`fk_metric_type_id` = `mt`.`id`))),
dbs as (
    select straight_join
        min(`si`.`creation_date`) AS `creation_date`, min(`si`.`modification_date`) AS `modification_date`, NULL AS `expiry_date`, min(`si`.`id`) AS `id`, min(`cpt`.`name_type`) AS `plugin_name`, concat('db_', trim(both '"' from json_extract(min(`cf`.`json_cfg`), '$.dbinstance.Engine')), '_istanze_tot') AS `metric_group_name`, count(`si`.`id`) AS `metric_instant_value`, '#' AS `metric_unit`, NULL AS `metric_value`, `sc`.`id` AS `fk_service_instance_id`, min(`si`.`fk_account_id`) AS `fk_account_id`, NULL AS `fk_job_id`
    from
        (((((((((`service_plugin_type` `pt`
        join `service_type` `st` on (`st`.`objclass` = `pt`.`objclass`))
        join `service_definition` `sd` on (`sd`.`fk_service_type_id` = `st`.`id`))
        join `service_instance` `si` on (`si`.`fk_service_definition_id` = `sd`.`id`))
        join `service_instance_config` `cf` on (`cf`.`fk_service_instance_id` = `si`.`id`))
        join `tree` on (`si`.`id` = `tree`.`child_id`))
        join `service_instance` `sc` on (`tree`.`parent_id` = `sc`.`id`))
        join `service_definition` `scd` on (`sc`.`fk_service_definition_id` = `scd`.`id`))
        join `service_type` `sct` on (`scd`.`fk_service_type_id` = `sct`.`id`))
        join `service_plugin_type` `cpt` on (`sct`.`objclass` = `cpt`.`objclass`))
    where
        `si`.`active` = 1
        and `sct`.`flag_container` = 1
        and `pt`.`name_type` = 'DatabaseInstance'
    group by
        `sc`.`id`, json_extract(`cf`.`json_cfg`, '$.dbinstance.Engine')),
vms as (
    select
        min(`pa`.`creation_date`) AS `creation_date`, min(`pa`.`modification_date`) AS `modification_date`, NULL AS `expiry_date`, min(`pa`.`id`) AS `id`, min(`ppt`.`name_type`) AS `plugin_name`, 'vm_numero_vm_tot' AS `metric_group_name`, count(`ch`.`id`) AS `metric_instant_value`, '#' AS `metric_unit`, NULL AS `metric_value`, `pa`.`id` AS `fk_service_instance_id`, `pa`.`fk_account_id` AS `fk_account_id`, NULL AS `fk_job_id`
    from
        ((((((((`tree`
        join `service_instance` `pa` on (`tree`.`parent_id` = `pa`.`id`))
        join `service_definition` `psd` on (`pa`.`fk_service_definition_id` = `psd`.`id`))
        join `service_type` `pst` on (`psd`.`fk_service_type_id` = `pst`.`id`))
        join `service_plugin_type` `ppt` on (`pst`.`objclass` = `ppt`.`objclass`))
        join `service_instance` `ch` on (`tree`.`child_id` = `ch`.`id`))
        join `service_definition` `sd` on (`ch`.`fk_service_definition_id` = `sd`.`id`))
        join `service_type` `st` on (`sd`.`fk_service_type_id` = `st`.`id`))
        join `service_plugin_type` `pt` on (`st`.`objclass` = `pt`.`objclass`))
    where
        `pa`.`active` = 1
        and `ch`.`active` = 1
        and `pt`.`name_type` = 'ComputeInstance'
    group by
        `pa`.`id`, `pa`.`fk_account_id`),
t as (
    select
        `bymetrics`.`creation_date` AS `creation_date`, `bymetrics`.`modification_date` AS `modification_date`, `bymetrics`.`expiry_date` AS `expiry_date`, `bymetrics`.`id` AS `id`, `bymetrics`.`plugin_name` AS `plugin_name`, `bymetrics`.`metric_group_name` AS `metric_group_name`, `bymetrics`.`metric_instant_value` AS `metric_instant_value`, `bymetrics`.`metric_unit` AS `metric_unit`, `bymetrics`.`metric_value` AS `metric_value`, `bymetrics`.`fk_service_instance_id` AS `fk_service_instance_id`, `bymetrics`.`fk_account_id` AS `fk_account_id`, `bymetrics`.`fk_job_id` AS `fk_job_id`
    from
        `bymetrics`
    union all
    select
        `dbs`.`creation_date` AS `creation_date`, `dbs`.`modification_date` AS `modification_date`, `dbs`.`expiry_date` AS `expiry_date`, `dbs`.`id` AS `id`, `dbs`.`plugin_name` AS `plugin_name`, `dbs`.`metric_group_name` AS `metric_group_name`, `dbs`.`metric_instant_value` AS `metric_instant_value`, `dbs`.`metric_unit` AS `metric_unit`, `dbs`.`metric_value` AS `metric_value`, `dbs`.`fk_service_instance_id` AS `fk_service_instance_id`, `dbs`.`fk_account_id` AS `fk_account_id`, `dbs`.`fk_job_id` AS `fk_job_id`
    from
        `dbs`
    union all
    select
        `vms`.`creation_date` AS `creation_date`, `vms`.`modification_date` AS `modification_date`, `vms`.`expiry_date` AS `expiry_date`, `vms`.`id` AS `id`, `vms`.`plugin_name` AS `plugin_name`, `vms`.`metric_group_name` AS `metric_group_name`, `vms`.`metric_instant_value` AS `metric_instant_value`, `vms`.`metric_unit` AS `metric_unit`, `vms`.`metric_value` AS `metric_value`, `vms`.`fk_service_instance_id` AS `fk_service_instance_id`, `vms`.`fk_account_id` AS `fk_account_id`, `vms`.`fk_job_id` AS `fk_job_id`
    from
        `vms`
)
select
    `t`.`creation_date` AS `creation_date`,
    `t`.`modification_date` AS `modification_date`,
    `t`.`expiry_date` AS `expiry_date`,
    `t`.`id` AS `id`,
    `t`.`plugin_name` AS `plugin_name`,
    `t`.`metric_group_name` AS `metric_group_name`,
    `t`.`metric_instant_value` AS `metric_instant_value`,
    `t`.`metric_unit` AS `metric_unit`,
    `t`.`metric_value` AS `metric_value`,
    `t`.`fk_service_instance_id` AS `fk_service_instance_id`,
    `t`.`fk_account_id` AS `fk_account_id`,
    `t`.`fk_job_id` AS `fk_job_id`
from
    `t`;
