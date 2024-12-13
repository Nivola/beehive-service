/*
SPDX-License-Identifier: EUPL-1.2

(C) Copyright 2018-2024 CSI-Piemonte

*/


CREATE TABLE perm_tag (
  id int(11) NOT NULL AUTO_INCREMENT,
  value varchar(100) COLLATE latin1_general_ci DEFAULT NULL,
  explain varchar(400) COLLATE latin1_general_ci DEFAULT NULL,
  creation_date datetime DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY value (value)
) ENGINE=InnoDB ;

CREATE TABLE perm_tag_entity (
  id int(11) NOT NULL AUTO_INCREMENT,
  tag int(11) DEFAULT NULL,
  entity int(11) DEFAULT NULL,
  type varchar(200) COLLATE latin1_general_ci DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_tag_entity (tag,entity)
) ENGINE=InnoDB ;