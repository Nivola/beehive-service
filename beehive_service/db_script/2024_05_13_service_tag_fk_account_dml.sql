UPDATE service_tag
SET fk_account_id = (
	SELECT id
	FROM account
	WHERE SUBSTRING(service_tag.objid, 1, 34) = account.objid
)
WHERE fk_account_id = 1;
