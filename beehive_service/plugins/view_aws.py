# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import re
import logging
from beehive.common.apimanager import ApiView, ApiManagerWarning
from beehive_service.views import ServiceApiView
from flasgger import Schema, fields
from flask import request
from six.moves.urllib.parse import urlencode

base = "/v1.0/nws"

mappingActions = {
    "runinstance": {
        "uri": "%s/computeservices/instance/runinstances" % base,
        "method": "POST",
        "root": "instance",
        "params": [{"params_uri": "oid", "args": "ImageId"}],
    },
    "describeinstance": {
        "uri": "%s/computeservices/instance/describeinstances" % base,
        "method": "GET",
        "root": None,
        "params": [],
    },
}


# get
class GetAWSRequestSchema(Schema):
    Action = fields.String(required=True, context="query")
    Description = fields.String(required=True, context="query")


class GetAWSParamsResponseSchema(Schema):
    pass


class GetAWSResponseSchema(Schema):
    aws = fields.String(required=True)


class WrapperAWS(ServiceApiView):
    tags = ["aws"]
    definitions = {
        "GetAWSParamsResponseSchema": GetAWSParamsResponseSchema,
    }
    parameters_schema = GetAWSRequestSchema
    responses = ServiceApiView.setResponses({200: {"description": "success", "schema": GetAWSResponseSchema}})

    def get(self, controller, data, *args, **kvargs):
        """
        Get AWS Wrapper
        Call this api to get a specific aws wrapper
        """
        root = None
        aws_params = request.args
        action = data.get("Action")
        response = None

        self.logger.info("******************************")
        self.logger.info("kvargs")
        self.logger.info(kvargs)
        self.logger.info("data")
        self.logger.info(data)
        self.logger.info("aws_params")
        self.logger.info(aws_params)
        self.logger.info("******************************")
        # TODO verifica creazione tabella o file properties per getsione mapping info: action, method, uri nivola
        # TODO costruzione di un json param con query field aws
        # TODO individuazione oid nivola
        # TODO redirect to RESTAPI nivola
        # TODO gestione xml response trasformation

        uri_map = mappingActions.get(action)
        if uri_map is not None:
            location = uri_map.get("uri")
            params = uri_map.get("params")
            method = uri_map.get("method").upper()
            root = uri_map.get("root")
            self.logger.info(root)
            if len(params) > 0:
                for par in params:
                    if aws_params.get(par.get("args")) is None:
                        raise ApiManagerWarning(
                            "Param %s in aws params uri %s not present" % (par.get("args"), location)
                        )
                    location = location.replace("<%s>" % par.get("params_uri"), aws_params.get(par.get("args")))
            if method:
                if method.lower() == "get":
                    parser = Ec2ParserGet(aws_params)
                    resp_dict = parser.parse_filter()
                    response = controller.api_client.admin_request(
                        "service",
                        location,
                        method,
                        data=urlencode(resp_dict, doseq=True),
                        other_headers=None,
                    )
                else:
                    parser = Ec2ParserPost(aws_params)
                    resp_dict = {root: parser.parse()}
                    response = controller.api_client.admin_request(
                        "service", location, method, data=resp_dict, other_headers=None
                    )
            else:
                raise ApiManagerWarning("http method not valid.")
            for par in params:
                if kvargs.get(par.get("args")) is not None:
                    location.replace("<%s>" % par.get("params_uri"), kvargs.get(par.get("args")))
                else:
                    self.logger.warn("Params uri <%s> not found" % par.get("params_uri"))
        else:
            raise ApiManagerWarning("Unrecognized action")
        resp = response.update({"aws": "OK"})
        return resp


class WrapperAwsAPI(ApiView):
    @staticmethod
    def register_api(module, dummyrules=None, **kwargs):
        base = "nws"
        rules = [
            ("%s/wrapperaws" % base, "GET", WrapperAWS, {}),
        ]
        ApiView.register_api(module, rules, **kwargs)


class Ec2ParserGet:
    """
    Parser delle chiamate GET di Amazon EC2
    """

    def __init__(self, aws_params):
        self.aws_params = aws_params
        self.filter = []
        self.response = []
        self.resp_dict = {}
        self.result = ""
        self.log = logging.getLogger("ServiceApiView")

    def parse_filter(self):
        name = ""
        value = ""
        lst_params = sorted(self.aws_params.keys())
        for key in lst_params:
            record = key + "=" + self.aws_params.get(key)
            for campi in re.split("Filter.[\d]+.", record):
                if len(campi) > 0:
                    n = re.split("=", campi)
                    self.filter.append(n)
        for f in self.filter:
            if str(f[0]).lower() == "name":
                name = str(f[1])
            elif str(f[0]).lower().__contains__("value"):
                obj_search = re.search(r"Value.\d", str(f[0]), re.I | re.U)
                if obj_search is not None and obj_search.group().split(".")[1] == "1":
                    name += ".N"
                value = str(f[1])
                self.add_dict(name, value)
            else:
                self.add_dict(str(f[0]), str(f[1]))
        return self.resp_dict

    def add_dict(self, key, value):
        lst_value = []
        if self.resp_dict.__contains__(key):
            lst_value = self.resp_dict.get(key)
        if isinstance(lst_value, list):
            if key.__contains__(".N") > 0:
                lst_value.append(value)
                self.resp_dict.update({key: lst_value})
            else:
                self.resp_dict.update({key: value})
        else:
            raise TypeError("The object must be list Type, %s occurred." % type(lst_value))


class Ec2ParserPost(object):
    """
    Parser delle chiamate POST di Amazon EC2
    """

    def __init__(self, ec2_url):
        self.qstring = ec2_url

    def parse(self):
        resp_dict = {}
        dict_param = self.qstring.to_dict(flat=False)
        sorted_dict_param = sorted(dict_param)
        for k in sorted_dict_param:
            list_keys = k.split(".")
            self.__build_structure(resp_dict, list_keys, dict_param.get(k))
        return resp_dict

    def __build_structure(self, resp_dict, list_keys, value, liv=0):
        key = list_keys[liv]
        if key.isdigit():
            if len(list_keys) - 1 == liv:
                if int(key) == 0:
                    tmp = [value[0]]
                else:
                    tmp = resp_dict
                    tmp.append(value[0])
                return tmp
            else:
                if len(resp_dict) <= int(key):
                    if int(key) == 0:
                        tmp = []
                        tmp.append(self.__build_structure(resp_dict, list_keys, value, liv + 1))
                    else:
                        tmp = resp_dict
                        tmp.append(self.__build_structure({}, list_keys, value, liv + 1))
                    return tmp
                else:
                    if isinstance(resp_dict, list):
                        tmp = resp_dict[int(key) - 1]
                        self.__build_structure(tmp, list_keys, value, liv + 1)
                        return resp_dict
                    else:
                        raise TypeError("The object must be list Type, %s occurred." % type(resp_dict))
        liv += 1
        if resp_dict.__contains__(key):
            if len(list_keys) == liv:
                return resp_dict
            else:
                resp_dict.update({key: self.__build_structure(resp_dict.get(key), list_keys, value, liv)})
                return resp_dict
        else:
            if len(list_keys) == liv:
                resp_dict.update({key: value[0]})
                return resp_dict
            else:
                resp_dict.update({key: self.__build_structure({}, list_keys, value, liv)})
                return resp_dict
