-- # SPDX-License-Identifier: EUPL-1.2
-- #
-- # (C) Copyright 2020-2023 CSI-Piemonte

-- run on Auth
-- #################################################
-- Create sysobject_type for AccountServiceDefinition
insert into sysobject_type  (objtype, objdef, creation_date)
select
	'service',
	'Organization.Division.Account.CATEGORY.AccountServiceDefinition',
	now()
from
	(select 1) as a
	left outer join sysobject_type st on  st.objtype =	'service' and st.objdef ='Organization.Division.Account.CATEGORY.AccountServiceDefinition'
where
	st.id  is null
;

-- #################################################
SELECT  max(id) from sysobject s ; -- => 13911
-- create sysobject  for generic AccountServiceDefinition one for each Account object
INSERT INTO sysobject (creation_date, modification_date, expiry_date, uuid, objid, `desc`, active, name, type_id)
SELECT
	now() creation_date,
	now() modification_date,
	null expiry_date,
	uuid() uuid,
	concat(s.objid, '//*//*') objid,
	s.desc `desc`,
	1 active,
	s.name name,
	st2.id type_id
from
	sysobject s
	inner join sysobject_type st  on s.type_id  = st.id 
	inner join sysobject_type st2 on st2.objdef = 'Organization.Division.Account.CATEGORY.AccountServiceDefinition'
	left outer join sysobject s2  on s2.objid  = concat(s.objid, '//*//*') and s2.type_id  = st2.id 
WHERE
	s2.id  is null and st.objdef ='Organization.Division.Account'
;

-- #################################################
-- create permisions for all AccountServiceDefinition which has no permission
-- usually all permission are created but only 1,2 (*, view)  are used for service objects -- and sa.id in (1,2)
INSERT INTO sysobject_permission (obj_id, action_id)
SELECT
 s.id, sa.id
from
	(sysobject s
	inner join sysobject_type st on st.objdef = 'Organization.Division.Account.CATEGORY.AccountServiceDefinition' and s.type_id  = st.id
	left outer join sysobject_permission sp  on sp.obj_id = s.id  ),
	sysobject_action sa
WHERE
	sp.obj_id is NULL
;

-- #################################################
-- Create role permissions permit for the AccountServiceDefinition the same action permitted for Account
INSERT INTO role_permission (role_id, permission_id)
SELECT
	rp.role_id, sp2.id
from
	role_permission rp
	inner join sysobject_permission sp1 on rp.permission_id = sp1.id
	inner join 	sysobject s1 on sp1.obj_id = s1.id
	inner join sysobject_type st1 on s1.type_id  = st1.id  and  st1.objdef ='Organization.Division.Account'
	inner join sysobject s2 on s2.objid  = concat(s1.objid, '//*//*')
	inner join sysobject_type st2 on s2.type_id  = st2.id  and  st2.objdef ='Organization.Division.Account.CATEGORY.AccountServiceDefinition'
	inner JOIN  sysobject_permission sp2 on sp1.action_id  = sp2.action_id  and sp2.obj_id  = s2.id
	left outer JOIN  role_permission rp2 on rp2.permission_id  = sp2.id
where
	rp2.id  is null
;
