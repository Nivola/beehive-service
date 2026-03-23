# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
import re


# from beehive.common.apimanager import ApiManagerError
from marshmallow import ValidationError
from typing import Callable, List, Union

V_UPPERCASE = "u"
V_LOWERCASE = "l"
V_MIXEDCASE = "m"
V_EXTRACHARS = "_"


def validate_ora_db_name(name: str):
    _validate_name(name=name, maxlenght=8, case=V_MIXEDCASE, alfanum=True)
    # if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
    #     raise ValidationError( "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters" )


def validate_pg_schema_name(name: str):
    if name.startswith("pg_"):
        raise ValidationError(f"The name {name} cannot begin with pg_")
    _validate_name(name=name, maxlenght=8, case=V_MIXEDCASE, alfanum=True)

    # if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
    #     raise ValidationError(
    #         "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters"
    #     )


def validate_pg_db_name(name: str):
    _validate_name(name=name, maxlenght=8, case=V_MIXEDCASE, alfanum=True)
    # if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
    #     raise ValidationError(
    #         "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters"
    #     )


def validate_ora_tbs_size(name: str):
    _validate_size(name=name)


def _validate_size(name: str, dim: str = "M"):
    if name[-1] != dim:
        raise ValidationError(f" {name} is not valid")
    try:
        int(name[:-1])
    except ValueError as ex:
        raise ValidationError(f" {name} is not valid") from ex


def _validate_name(
    name: str,
    minlenght: int = 0,
    maxlenght: int = 255,
    no_startwith: List[str] = None,
    case: str = V_UPPERCASE,
    extra: str = V_EXTRACHARS,
    alfanum: bool = True,
    firstalfa: bool = True,
):
    if no_startwith is not None:
        for exclude in no_startwith:
            if name.startswith(exclude):
                raise ValidationError(f" {name} cannot start with {exclude}")
    l = len(name)
    if l < minlenght:
        raise ValidationError(f" {name} is too short  min is {minlenght}")
    if l > maxlenght:
        raise ValidationError(f" {name} is too long max is {maxlenght}")
    # Define the base set of allowed characters
    if case == V_UPPERCASE:
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    elif case == V_LOWERCASE:
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz")
    else:
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    if firstalfa and name[0] not in allowed_chars:
        raise ValidationError(f" {name} must begin with alfa char")

    if alfanum:
        allowed_chars.update("0123456789_")
    if extra:
        allowed_chars.update(extra)

    if not any(char in allowed_chars for char in name):
        raise ValidationError(f" {name} contains character not allowed ")


def name_validator(
    minlenght: int = 0,
    maxlenght: int = 255,
    case: str = V_MIXEDCASE,
    extra: str = V_EXTRACHARS,
    no_startwith: List[str] = None,
    alfanum: bool = True,
    firstalfa: bool = True,
) -> Callable[[str], None]:
    return lambda a: _validate_name(
        name=a,
        minlenght=minlenght,
        maxlenght=maxlenght,
        no_startwith=no_startwith,
        case=case,
        extra=extra,
        alfanum=alfanum,
        firstalfa=firstalfa,
    )


# Example usage
input_str = "valid_string-123"
extra_chars = {"!"}  # Allow "!" in addition to default characters
max_len = 50
