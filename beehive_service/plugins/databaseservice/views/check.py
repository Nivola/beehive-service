# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
import re

# from beehive.common.apimanager import ApiManagerError
from marshmallow import ValidationError


def validate_ora_db_name(name: str):
    if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
        raise ValidationError(
            "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters"
        )


def validate_pg_schema_name(name: str):
    if name.startswith("pg_"):
        raise ValidationError("The name cannot begin with pg_")

    if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
        raise ValidationError(
            "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters"
        )


def validate_pg_db_name(name: str):
    if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
        raise ValidationError(
            "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters"
        )
