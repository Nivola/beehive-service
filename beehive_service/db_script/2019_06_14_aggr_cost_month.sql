/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/


DROP TABLE IF EXISTS `v_aggr_cost_month`;
CREATE OR REPLACE VIEW `v_aggr_cost_month` AS select
    `aggregate_cost`.`id` AS `id`,
    `aggregate_cost`.`fk_metric_type_id` AS `fk_metric_type_id`,
    `service_instance`.`fk_account_id` AS `fk_account_id`,
    sum(`aggregate_cost`.`cost`) AS `cost`,
    max(`aggregate_cost`.`fk_cost_type_id`) AS `fk_cost_type_id`,
    substr(`aggregate_cost`.`period`, 1, 7) AS `period`,
    now() AS `evaluation_date`
from
    (`aggregate_cost`
join `service_instance` on
    ((`aggregate_cost`.`fk_service_instance_id` = `service_instance`.`id`)))
group by
    `aggregate_cost`.`id`,
    `aggregate_cost`.`fk_metric_type_id`,
    `service_instance`.`fk_account_id`,
    substr(`aggregate_cost`.`period`, 1, 7);