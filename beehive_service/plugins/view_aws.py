# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

# import six
# from six.moves.urllib.parse import parse_qs
# from beehive_service.plugins.computeservice.views.instance import DescribeInstances, \
#     RunInstances
# from beecell.swagger import SwaggerHelper
import re
import logging
from beehive.common.apimanager import ApiView, ApiManagerWarning
from beehive_service.views import ServiceApiView
from flasgger import  Schema, fields  # , SwaggerView, Swagger
from flask import request #, redirect   , url_for, Flask
from six.moves.urllib.parse import urlencode

base = u'/v1.0/nws'

mappingActions = {
        u'runinstance':{u'uri':u'%s/computeservices/instance/runinstances' % base, u'method':u'POST', u'root':u'instance', u'params':[{u'params_uri':u'oid', u'args':u'ImageId'}]},
        u'describeinstance':{u'uri':u'%s/computeservices/instance/describeinstances' % base, u'method':u'GET', u'root':None, u'params':[]}
    }


#get
class GetAWSRequestSchema(Schema):
    Action = fields.String(required=True, context=u'query')
    Description = fields.String(required=True, context=u'query')


class GetAWSParamsResponseSchema(Schema):
    pass


class GetAWSResponseSchema(Schema):
#     aws = fields.Nested(GetAWSParamsResponseSchema,required=True)
    aws = fields.String(required=True)


class WrapperAWS(ServiceApiView):
    tags = [u'aws']
    definitions = {
        u'GetAWSParamsResponseSchema': GetAWSParamsResponseSchema,
    }
#     parameters = SwaggerHelper().get_parameters(GetAWSRequestSchema)
    parameters_schema = GetAWSRequestSchema
    responses = ServiceApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetAWSResponseSchema
        }
    })

    def get(self, controller, data, *args, **kvargs):
        """
        Get AWS Wrapper
        Call this api to get a specific aws wrapper
        """
        root = None
        aws_params = request.args
        action = data.get(u'Action')
        response = None

        self.logger.info('******************************')
        self.logger.info(u'kvargs')
        self.logger.info(kvargs)
#         self.logger.info(u'args')
#         self.logger.info(args)
        self.logger.info(u'data')
        self.logger.info(data)
        self.logger.info('aws_params')
        self.logger.info(aws_params)
        self.logger.info('******************************')
        # TODO verifica creazione tabella o file properties per getsione mapping info: action, method, uri nivola
        # TODO costruzione di un json param con query field aws
        # TODO individuazione oid nivola
        # TODO redirect to RESTAPI nivola
        # TODO gestione xml response trasformation

        uriMap = mappingActions.get(action)
        if uriMap is not None:
            location = uriMap.get(u'uri')
            params = uriMap.get(u'params')
            method = uriMap.get(u'method').upper()
            root = uriMap.get(u'root')
            self.logger.info(root)
            if len(params) > 0:
                for par in params:
                    if aws_params.get(par.get(u'args')) is None:
                        raise ApiManagerWarning(u'Param %s in aws params uri %s not present' % (par.get(u'args'), location))
                    location = location.replace(u'<%s>' % par.get(u'params_uri'), aws_params.get(par.get(u'args')))
#             self.logger.warn(u'location: ' + location)
            if method:
                if method.lower() == 'get':
                    parser = Ec2ParserGet(aws_params)
                    resp_dict = parser.parse_filter()
                    response = controller.api_client.admin_request(
                        u'service', location, method, data=urlencode(resp_dict, doseq=True), other_headers=None)
                else:
                    parser = Ec2ParserPost(aws_params)
                    resp_dict = {root:parser.parse()}
                    response = controller.api_client.admin_request(
                        u'service', location, method, data=resp_dict, other_headers=None)
            else:
                raise ApiManagerWarning('http method not valid.')
#             self.logger.info('******************************')
#             self.logger.warn(params)
            for par in params:
                if kvargs.get(par.get(u'args')) is not None:
                    location.replace(u'<%s>' % par.get(u'params_uri'), kvargs.get(par.get(u'args')))
                else:
                    self.logger.warn(u'Params uri <%s> not found' % par.get(u'params_uri'))
                    # TODO raise Error()
        else:
            raise ApiManagerWarning(u'Unrecognized action')
#             self.logger.warn(location)
#         return response
        resp = response.update({u'aws':u'OK'})
        return resp


class WrapperAwsAPI(ApiView):

    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = u'nws'
        rules = [
            (u'%s/wrapperaws' % base, u'GET', WrapperAWS, {}),
        ]
        ApiView.register_api(module, rules, **kwargs)


class Ec2ParserGet:
    '''
        Parser delle chiamate GET di Amazon EC2
    '''

    def __init__(self, aws_params):
        self.aws_params = aws_params
        self.filter = []
        self.response = []
        self.resp_dict = {}
        self.result = ''
        self.log = logging.getLogger(u'ServiceApiView')

    def parse_filter(self):
        name = ''
        value = ''
        lst_params = sorted(self.aws_params.keys())
#         dict_param = self.aws_params.to_dict(flat=True)
        for key in lst_params:
            record = key + '=' + self.aws_params.get(key)
            for campi in re.split('Filter.[\d]+.', record):
                if len(campi) > 0:
                    n = re.split('=', campi)
                    self.filter.append(n)
        for f in self.filter:
            if str(f[0]).lower() == 'name':
                name = str(f[1])
            elif str(f[0]).lower().__contains__('value'):
                obj_search = re.search(r'Value.\d', str(f[0]), re.I | re.U)
                if obj_search:
                    if obj_search.group().split('.')[1] == '1':
                        name += u'.N'
                value = str(f[1])
                self.add_dict(name, value)
#                 self.response.append('&')
#                 self.response.append(name)
#                 self.response.append('=')
#                 self.response.append(value)
            else:
                self.add_dict(str(f[0]), str(f[1]))
#                 if len(f) == 1:
#                     self.response.append('&')
#                     self.response.append(str(f[0]))
#                 else:
#                     self.response.append('&')
#                     self.response.append(str(f[0]))
#                     self.response.append('=')
#                     self.response.append(str(f[1]))
        return self.resp_dict


    def add_dict(self, key, value):
        lst_value = []
        if self.resp_dict.__contains__(key):
            lst_value = self.resp_dict.get(key)
        if isinstance(lst_value, list):
            if key.__contains__('.N') > 0:
                lst_value.append(value)
                self.resp_dict.update({key:lst_value})
            else:
                self.resp_dict.update({key: value})
        else:
            raise TypeError('The object must be list Type, %s occurred.' % type(lst_value))


class Ec2ParserPost(object):
    '''
        Parser delle chiamate POST di Amazon EC2
    '''

    def __init__(self, ec2_url):
        self.qstring = ec2_url

    def parse(self):
        resp_dict = {}
        dict_param = self.qstring.to_dict(flat=False)
        sorted_dict_param = sorted(dict_param)
        for k in sorted_dict_param:
            list_keys = k.split('.')
            self.__build_structure(resp_dict, list_keys, dict_param.get(k))
        return resp_dict

#     @staticmethod
#     def _decode_dict(self, d):
#         decoded = {}
#         for key, value in d.items():
#             if isinstance(key, six.binary_type):
#                 newkey = key.decode("utf-8")
#             elif isinstance(key, (list, tuple)):
#                 newkey = []
#                 for k in key:
#                     if isinstance(k, six.binary_type):
#                         newkey.append(k.decode('utf-8'))
#                     else:
#                         newkey.append(k)
#             else:
#                 newkey = key
#             if isinstance(value, six.binary_type):
#                 newvalue = value.decode("utf-8")
#             elif isinstance(value, (list, tuple)):
#                 newvalue = []
#                 for v in value:
#                     if isinstance(v, six.binary_type):
#                         newvalue.append(v.decode('utf-8'))
#                     else:
#                         newvalue.append(v)
#             else:
#                 newvalue = value
#             decoded[newkey] = newvalue
#         return decoded

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
                        raise TypeError('The object must be list Type, %s occurred.' % type(resp_dict))
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
