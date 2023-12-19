# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte
import re
from beehive.common.apimanager import ApiManagerError


def validate_ora_db_name(name: str):
    if re.compile(r"[A-Za-z][A-Za-z0-9]{0,7}").fullmatch(name) is None:
        raise ApiManagerError(
            "Specify a 8 character long Instance Name that starts with an alphabet and contains only alphanumeric characters",
            code=400,
        )
