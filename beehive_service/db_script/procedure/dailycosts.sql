/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/
-- -----------------------------------------------------------
-- -----------------------------------------------------------

DROP PROCEDURE service.`dailycosts`;

DELIMITER $$
CREATE  PROCEDURE `dailycosts`(in p_period varchar(10), in jobid  INTEGER )
BEGIN
    CALL dailyconsumes(p_period , jobid );
   -- solo consumi

    COMMIT;
END
$$

DELIMITER ;
