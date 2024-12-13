/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------

DROP VIEW IF EXISTS  `v_aggregate_consumes`;

CREATE
    VIEW `v_aggregate_consumes`
AS with
    recursive tree as
    (
        select
            `t1`.`start_service_id` AS `parent_id`,
            `t1`.`start_service_id` AS `child_id`,
            0 AS `dep`
        from
            ( `service_link_inst` `t1`
                left join `service_link_inst` `t2` on(`t1`.`start_service_id` = `t2`.`end_service_id`))
        where
            `t2`.`id` is null
        group by
            `t1`.`start_service_id`
        union select
            `t1`.`start_service_id` AS `parent_id`,
            `t1`.`end_service_id` AS `child_id`,
            1 AS `dep`
        from
            (`service_link_inst` `t1`
                left join `service_link_inst` `t2` on(`t1`.`start_service_id` = `t2`.`end_service_id`))
        where
            `t2`.`id` is null
        union select
            `c`.`parent_id` AS `parent_id`,
            `t2`.`end_service_id` AS `child_id`,
            `c`.`dep` + 1 AS `dep`
        from
            (`tree` `c`
            join `service_link_inst` `t2` on(`t2`.`start_service_id` = `c`.`child_id`))
    ),
    pinfo as
    (
        select
            `pt`.`name_type` AS `name_type`,
            `pt`.`category` AS `category`,
            `st`.`name` AS `instance_type`,
            `si`.`id` AS `fk_service_id`,
            `si`.`uuid` AS `service_uuid`,
            `a`.`uuid` AS `account_uuid`,
            `d`.`uuid` AS `division_uuid`,
            `o`.`uuid` AS `organization_uuid`
        from
            ((((((`service_instance` `si`
                join `service_definition` `sd` on(`si`.`fk_service_definition_id` = `sd`.`id`))
                join `service_type` `st` on(`st`.`id` = `sd`.`fk_service_type_id`))
                join `service_plugin_type` `pt` on(`st`.`objclass` = `pt`.`objclass`))
                join `account` `a` on(`si`.`fk_account_id` = `a`.`id`))
                join `division` `d` on(`a`.`fk_division_id` = `d`.`id`))
                join `organization` `o` on(`d`.`fk_organization_id` = `o`.`id`))
    )
    select
        `p`.`organization_uuid` AS `organization_uuid`,
        `p`.`division_uuid` AS `division_uuid`,
        `p`.`account_uuid` AS `account_uuid`,
        max(`ac`.`creation_date`) AS `creation_date`,
        max(`ac`.`evaluation_date`) AS `evaluation_date`,
        max(`ac`.`modification_date`) AS `modification_date`,
        `ac`.`period` AS `period`,
        min(`me`.`name`) AS `metric`,
        sum(`ac`.`consumed`) AS `consumed`,
        min(`me`.`measure_unit`) AS `measure_unit`,
        min(`p`.`service_uuid`) AS `container_uuid`,
        min(`p`.`instance_type`) AS `container_instance_type`,
        min(`p`.`name_type`) AS `container_type`,
        min(`p`.`category`) AS `category`
    from
        (((`aggregate_cost` `ac`
            join `service_metric_type` `me` on(`ac`.`fk_metric_type_id` = `me`.`id`))
            join `tree` on(`ac`.`fk_service_instance_id` = `tree`.`child_id`))
            join `pinfo` `p` on(`tree`.`parent_id` = `p`.`fk_service_id`))
    group by
        `p`.`fk_service_id`,
        `p`.`organization_uuid`,
        `p`.`division_uuid`,
        `p`.`account_uuid`,
        `ac`.`period`,
        `me`.`id`
;