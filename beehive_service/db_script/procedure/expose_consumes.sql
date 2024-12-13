/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `expose_consumes`;
DELIMITER $$
CREATE  PROCEDURE `expose_consumes`(in p_period varchar(10) )
BEGIN
    -- IN order to be idempotent
    DELETE FROM mv_aggregate_consumes WHERE `period` = p_period;
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
        min(csi.uuid) AS container_uuid,
        min(cst.name ) AS container_instance_type,
        min(cspt.name_type) AS container_type,
        min(cspt.category) AS category
    FROM
        aggregate_cost ac
        INNER JOIN account a ON ac.fk_account_id = a.id
        INNER JOIN division d ON a.fk_division_id = d.id
        INNER JOIN organization o ON d.fk_organization_id = o.id
        INNER JOIN service_metric_type me ON ac.fk_metric_type_id = me.id
        INNER JOIN service_instance si ON ac.fk_service_instance_id  = si.id
        INNER JOIN service_definition sd  ON si.fk_service_definition_id  = sd.id
        INNER JOIN service_type st ON sd.fk_service_type_id  = st.id
        INNER JOIN service_plugin_type spt ON spt.objclass  = st.objclass
        INNER JOIN service_instance csi ON csi.fk_account_id = si.fk_account_id and csi.active = 1
        INNER JOIN service_definition csd  ON csi.fk_service_definition_id  = csd.id
        INNER JOIN service_type cst ON csd.fk_service_type_id  = cst.id
        INNER JOIN service_plugin_type cspt ON cspt.objclass  = cst.objclass  and cspt.name_type  = case spt .name_type
        WHEN 'ComputeService' THEN 'ComputeService'
        WHEN 'ComputeInstance' THEN 'ComputeService'
        WHEN 'ComputeImage' THEN 'ComputeService'
        WHEN 'ComputeVPC' THEN 'ComputeService'
        WHEN 'ComputeSubnet' THEN 'ComputeService'
        WHEN 'ComputeSecurityGroup' THEN 'ComputeService'
        WHEN 'ComputeVolume' THEN 'ComputeService'
        WHEN 'ComputeKeyPairs' THEN 'ComputeService'
        WHEN 'ComputeLimits' THEN 'ComputeService'
        WHEN 'ComputeAddress' THEN 'ComputeService'
        WHEN 'DatabaseService' THEN 'DatabaseService'
        WHEN 'DatabaseInstance' THEN 'DatabaseService'
        WHEN 'DatabaseSchema' THEN 'DatabaseService'
        WHEN 'DatabaseUser' THEN 'DatabaseService'
        WHEN 'DatabaseBackup' THEN 'DatabaseService'
        WHEN 'DatabaseLog' THEN 'DatabaseService'
        WHEN 'DatabaseSnapshot' THEN 'DatabaseService'
        WHEN 'DatabaseTag' THEN 'DatabaseService'
        WHEN 'StorageService' THEN 'StorageService'
        WHEN 'StorageEFS' THEN 'StorageService'
        WHEN 'ComputeTag' THEN 'StorageService'
        WHEN 'AppEngineService' THEN 'AppEngineService'
        WHEN 'AppEngineInstance' THEN 'AppEngineService'
        WHEN 'ComputeTemplate' THEN 'ComputeService'
        WHEN 'NetworkService' THEN 'NetworkService'
        WHEN 'NetworkGateway' THEN 'NetworkService'
        WHEN 'VirtualService' THEN 'ComputeService'
        ELSE 'ComputeService'
        END
    WHERE ac.`period`  = p_period
    GROUP BY
        ac.period, ac.fk_account_id ,  ac.fk_metric_type_id , csi.id
    ;

    -- SELECT
    --     organization_uuid, division_uuid, account_uuid, creation_date, evaluation_date,
    --     modification_date, period, metric, consumed, measure_unit, container_uuid,
    --     container_instance_type, container_type, category
    -- FROM
    --     v_aggregate_consumes
    -- WHERE
    --     period = p_period;

    COMMIT;
END
$$
DELIMITER ;
