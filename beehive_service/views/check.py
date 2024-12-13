# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
import re
from beehive.common.apimanager import ApiManagerError


def validate_acronym(value: str):
    validate_name_default(value, "acronym")


def validate_account_name(name: str):
    validate_name_default(name)


def validate_div_name(name: str):
    validate_name_default(name)


def validate_org_name(name: str):
    validate_name_default(name)


def validate_name_default(value: str, name: str = "name"):
    char_re = re.compile(r"[^a-zA-Z0-9\-]")
    data = char_re.search(value)
    valid = not bool(data)
    if not valid:
        raise ApiManagerError(
            "The %s must contain only alphanumeric characters, numbers or the hyphen" % name, code=400
        )


# s1 = "org-namePippo"
# s2 = "org-name Pippo"
# s3 = "org-namePippo!"
# validate_org_name(s3)
