/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2023 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------
DROP PROCEDURE IF EXISTS `smsmpopulate`;

DELIMITER $$
CREATE  PROCEDURE `smsmpopulate`(in parlimit  INTEGER )
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
END
$$
DELIMITER ;

