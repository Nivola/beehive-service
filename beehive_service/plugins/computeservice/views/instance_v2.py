# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from typing import Dict
from flasgger import fields, Schema
from marshmallow import validates_schema, ValidationError
from beehive_service.views import ServiceApiView
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import SwaggerApiView, ApiView, ApiManagerError
from marshmallow.validate import OneOf, Length
from beehive_service.model import SrvStatusType
from beehive.common.data import operation
from beehive_service.controller import ServiceController
from beehive_service.plugins.computeservice.controller import ApiComputeInstance, ApiComputeService
from .instance import ModifyInstanceAttribute, TerminateInstances, StartInstances, StopInstances, \
    RebootInstances, DescribeInstanceSnapshots, CreateInstanceSnapshots, DeleteInstanceSnapshots, \
    RevertInstanceSnapshots, MonitorInstances, ForwardLogInstances, UnmonitorInstances


class InstanceProductCodesResponseSchema(Schema):
    productCode = fields.String(required=False, allow_none=True, example='',
                                description='product code AMI used to launch the instance')
    type = fields.String(required=False, allow_none=True, example='', description='type of product code')


class InstancePlacementsResponseSchema(Schema):
    affinity = fields.String(required=False, allow_none=True, example='',
                             description='affinity setting for the instance on the dedicated host')
    availabilityZone = fields.String(required=False, allow_none=True, example='',
                                     description='availability zone of the instance id')
    groupName = fields.String(required=False, allow_none=True, example='',
                              description='name of the placement group the instance')
    spreadDomain = fields.String(required=False, allow_none=True, example='', description='instance id')
    hostId = fields.String(required=False, allow_none=True, example='',
                           description='host id on which the instance reside')
    tenancy = fields.String(required=False, allow_none=True, example='',
                            description='tenancy of the instance (if the instance is running in a VPC)')


class InstanceMonitoringResponseSchema(Schema):
    state = fields.String(required=False, allow_none=True, example='', description='status of monitoring')


class InstanceGroupSetResponseSchema(Schema):
    groupName = fields.String(required=False, allow_none=True, example='', description='security group name')
    groupId = fields.String(required=False, allow_none=True, example='', description='security group id')


class InstanceBlockDeviceMappingV20Item1ResponseSchema(Schema):
    volumeId = fields.String(required=False, allow_none=True, example='', description='id volume ebs')
    status = fields.String(required=False, allow_none=True, example='', description='attachment status')
    attachTime = fields.DateTime(required=False, allow_none=True, example='', description='attachment timestamp')
    deleteOnTermination = fields.Boolean(required=False, description='boolean to know if the volume is deleted on '
                                                                     'instance termination.')
    volumeSize = fields.Integer(required=False, allow_none=True, example=10,
                                description='The size of the volume, in GiB.')


class InstanceBlockDeviceMappingV20ResponseSchema(Schema):
    deviceName = fields.String(required=False, allow_none=True, example='', description='device name')
    ebs = fields.Nested(InstanceBlockDeviceMappingV20Item1ResponseSchema, many=False, required=False)


class InstanceTagSetResponseSchema(Schema):
    key = fields.String(required=False, description='tag key')
    value = fields.String(required=False, description='tag value')


class InstanceAssociationResponseSchema(Schema):
    publicIp = fields.String(required=False, allow_none=True, example='', description='public IP address ')


class InstancePrivateIpAddressesSetResponseSchema(Schema):
    privateIpAddress = fields.String(required=False, allow_none=True, example='',
                                     description='private IPv4 address associated with the network interface')
    association = fields.Nested(InstanceAssociationResponseSchema, many=True, required=False)


class InstanceNetworkInterfaceSetResponseSchema(Schema):
    networkInterfaceId = fields.String(required=False, allow_none=True, example='', description='network interface id')
    subnetId = fields.String(required=False, allow_none=True, example='', description='subnet id')
    vpcId = fields.String(required=False, allow_none=True, example='', description='vpc id')
    status = fields.String(required=False, allow_none=True, example='', description='status of the network interface')
    privateDnsName = fields.String(required=False, allow_none=True, example='',
                                   description='private DNS name of the network interface')
    groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)
    association = fields.Nested(InstanceAssociationResponseSchema, many=False, required=False)
    privateIpAddressesSet = fields.Nested(InstancePrivateIpAddressesSetResponseSchema, many=False, required=False)


class InstanceStateResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, example='0', description='code of instance state')
    name = fields.String(required=False, example='pending | running | ....', description='name of instance state',
                         validate=OneOf(['pending', 'running', 'shutting-down', 'terminated', 'stopping',
                                         'stopped', 'error', 'unknown']))


class InstanceTypeExtResponseSchema(Schema):
    vcpus = fields.Integer(required=False, example='1', description='number of virtual cpu')
    bandwidth = fields.Integer(required=False, example='0', description='bandwidth')
    memory = fields.Integer(required=False, example='0', description='RAM')
    disk_iops = fields.Integer(required=False, example='0', description='available disk IOPS')
    disk = fields.Integer(required=False, example='0', description='number of virtual disk')
    name = fields.String(required=False, example='vm.m4.large')


class StateReasonResponseSchema(Schema):
    code = fields.Integer(required=False, allow_none=True, example='400')
    message = fields.String(required=False, allow_none=True, example='Parent instance <ServiceInstance at 0x7f3158628d90> is not bound to a Session')


class InstanceInstancesSetResponseSchema(Schema):
    instanceId = fields.String(required=False, allow_none=True, example='', description='instance id')
    imageId = fields.String(required=False, allow_none=True, example='', description='image instance id')
    instanceState = fields.Nested(InstanceStateResponseSchema, many=False, required=False)
    privateDnsName = fields.String(required=False, allow_none=True, example='',
                                   description='private dns name assigned to the instance')
    dnsName = fields.String(required=False, allow_none=True, example='',
                            description='public dns name assigned to the instance')
    reason = fields.String(required=False, allow_none=True, example='',
                           description='reason for the current state of the instance')
    keyName = fields.String(required=False, allow_none=True, example='',
                            description='name of the key pair used to create the instance')
    instanceType = fields.String(required=False, allow_none=True, example='',
                                 description='instance definition for the instance')
    productCodes = fields.Nested(InstanceProductCodesResponseSchema, many=False, required=False)
    launchTime = fields.DateTime(required=False, example='', description='the timestamp the instance was launched')
    placement = fields.Nested(InstancePlacementsResponseSchema, many=False, required=False)
    monitoring = fields.Nested(InstanceMonitoringResponseSchema, many=False, required=False)
    subnetId = fields.String(required=False, allow_none=True, example='', description='subnet id ')
    vpcId = fields.String(required=False, allow_none=True, example='', description='vpc id ')
    privateIpAddress = fields.String(required=False, allow_none=True, example='192.168.1.78', description='')
    ipAddress = fields.String(required=False, allow_none=True, example='192.168.1.98', description='')
    groupSet = fields.Nested(InstanceGroupSetResponseSchema, many=True, required=False)
    architecture = fields.String(required=False, allow_none=True, example='i386 | x86_64', description='')
    rootDeviceType = fields.String(required=False, allow_none=True, example='ebs',
                                   description='root device type used by the AMI.')
    blockDeviceMapping = fields.Nested(InstanceBlockDeviceMappingV20ResponseSchema, many=True, required=False)
    virtualizationType = fields.String(required=False, allow_none=True, example='hvm | paravirtual',
                                       description='virtualization type of the instance')
    tagSet = fields.Nested(InstanceTagSetResponseSchema, many=True, required=False)
    hypervisor = fields.String(required=False, allow_none=True, example='vmware | openstack',
                               description='type of the hypervisor')
    networkInterfaceSet = fields.Nested(InstanceNetworkInterfaceSetResponseSchema, many=True, required=False)
    ebsOptimized = fields.Boolean(required=False,
                                  description='indicates whether the instance is optimized for Amazon EBS I/O')
    nvl_name = fields.String(required=False, allow_none=True, example='',
                             description='name of the instance', data_key='nvl-name')
    nvl_subnetName = fields.String(required=False, allow_none=True, example='',
                                   description='subnet name of the instance', data_key='nvl-subnetName')
    nvl_vpcName = fields.String(required=False, allow_none=True, example='',
                                description='vpc name of the instance', data_key='nvl-vpcName')
    nvl_imageName = fields.String(required=False, allow_none=True, example='',
                                  description='image name of the instance', data_key='nvl-imageName')
    nvl_ownerAlias = fields.String(required=False, allow_none=True, example='',
                                   description='name of the account that owns the instance', data_key='nvl-ownerAlias')
    nvl_ownerId = fields.String(required=False, allow_none=True, example='',
                                description='ID of the account that owns the instance', data_key='nvl-ownerId')
    nvl_resourceId = fields.String(required=False, allow_none=True, example='',
                                   description='ID of the instance resource', data_key='nvl-resourceId')
    nvl_InstanceTypeExt = fields.Nested(InstanceTypeExtResponseSchema, many=False, required=True,
                                        data_key='nvl-InstanceTypeExt', description='flavor attributes')
    nvl_MonitoringEnabled = fields.Boolean(required=True, exampel=True, data_key='nvl-MonitoringEnabled',
                                           description='if True monitoring is enabled')
    nvl_LoggingEnabled = fields.Boolean(required=True, exampel=True, data_key='nvl-LoggingEnabled',
                                        description='if True log forward is enabled')
    nvl_BackupEnabled = fields.Boolean(required=True, exampel=True, data_key='nvl-BackupEnabled',
                                       description='if True backup is enabled')
    nvl_HostGroup = fields.String(example='oracle', missing=None, required=False, data_key='nvl-HostGroup',
                                  description='hypervisor host group')
    stateReason = fields.Nested(StateReasonResponseSchema, many=False, required=False)


class InstanceReservationSetResponseSchema(Schema):
    groupSet = fields.Nested(InstanceGroupSetResponseSchema, required=False, many=True, allow_none=True)
    instancesSet = fields.Nested(InstanceInstancesSetResponseSchema, required=False, many=True, allow_none=True)
    ownerId = fields.String(required=False, description='')
    requesterId = fields.String(required=False, description='')
    reservationId = fields.String(required=False, description='')
    nvl_instanceTotal = fields.Integer(required=True, data_key='nvl-instanceTotal', example='', description='')


class DescribeInstancesV20Api1ResponseSchema(Schema):
    nextToken = fields.String(required=True, allow_none=True)
    requestId = fields.String(required=True)
    reservationSet = fields.Nested(InstanceReservationSetResponseSchema, many=True, required=True, allow_none=False)
    xmlns = fields.String(required=False, data_key='__xmlns')


class DescribeInstancesV20ApiResponseSchema(Schema):
    DescribeInstancesResponse = fields.Nested(DescribeInstancesV20Api1ResponseSchema, required=True, many=False,
                                              allow_none=False)


# class BlockDeviceMappingV20ApiRequestSchema(Schema):
#     attach_time = fields.List(fields.DateTime(), required=False, description='attachment timestamp')
#     delete_on_termination = fields.List(fields.Boolean(), required=False,
#                                         description='boolean to know if the volume is deleted on instance '
#                                                     'termination.')
#     device_name = fields.List(fields.String(), required=False, description='device name')
#     status = fields.List(fields.String(), required=False, description='attachment status')
#     volume_id = fields.List(fields.String(), required=False, description='id volume ebs')
#

class IamInstanceProfileApiRequestSchema(Schema):
    arn = fields.List(fields.String(), required=False, description='')


# class InstanceSecurityGroupApiRequestSchema(Schema):
#     group_id = fields.List(fields.String(), required=False, description='security group id')
#     group_name = fields.List(fields.String(), required=False, description='security group name')


class NetworkInterfaceAddresses2ApiRequestSchema(Schema):
    public_ip = fields.List(fields.String(), required=False, description='network public IPv4 address')
    ip_owner_id = fields.List(fields.String(), required=False, description='owner of the IPv4 associated with the '
                                                                           'network interface')


class NetworkInterfaceAddresses1ApiRequestSchema(Schema):
    private_ip_address = fields.List(fields.String(), required=False, description='network private IPv4 address')
    primary = fields.List(fields.Boolean(), required=False, description='Specify if the IPv4 address of the network '
                                                                        'interface is the primary private IPv4 '
                                                                        'address')
    association = fields.Nested(NetworkInterfaceAddresses2ApiRequestSchema, required=False, context='query')


class NetworkInterfaceAssociationApiRequestSchema(Schema):
    public_ip = fields.List(fields.String(), required=False, description='network public IPv4 address')
    ip_owner_id = fields.List(fields.String(), required=False,
                              description='owner of the IPv4 associated with the network interface')
    allocation_id = fields.List(fields.String(), required=False,
                                description='allocation ID for the network IPv4 address')
    association_id = fields.List(fields.String(), required=False,
                                 description='association ID for the network IPv4 address')


class NetworkInterfaceAttachmentApiRequestSchema(Schema):
    attachment_id = fields.List(fields.String(), required=False, description='')
    instance_id = fields.List(fields.String(), required=False, description='')
    instance_owner_id = fields.List(fields.String(), required=False, description='')
    device_index = fields.List(fields.String(), required=False, description='')
    status = fields.List(fields.String(), required=False, description='')
    attach_time = fields.List(fields.DateTime(), required=False, description=''),
    delete_on_termination = fields.List(fields.Boolean(), required=False, description='')


class NetworkInterfaceIpv6ApiRequestSchema(Schema):
    ipv6_address = fields.List(fields.String(), required=False, description='')


class NetworkInterfaceApiRequestSchema(Schema):
    addresses = fields.Nested(NetworkInterfaceAddresses1ApiRequestSchema, required=False, context='query')
    association = fields.Nested(NetworkInterfaceAssociationApiRequestSchema, required=False, context='query')
    attachment = fields.Nested(NetworkInterfaceAttachmentApiRequestSchema, required=False, context='query')
    availability_zone = fields.List(fields.String(), required=False, description='availability zone')
    description = fields.List(fields.String(), required=False, description='')
    group_id = fields.List(fields.String(), required=False, description='security group id')
    group_name = fields.List(fields.String(), required=False, description='security group name')
    ipv6_addresses = fields.Nested(NetworkInterfaceIpv6ApiRequestSchema, required=False, context='query')
    mac_address = fields.List(fields.String(), required=False, description='')
    network_interface_id = fields.List(fields.String(), required=False, description='')
    owner_id = fields.List(fields.String(), required=False, description='')
    private_dns_name = fields.List(fields.String(), required=False, description='')
    requester_id = fields.List(fields.String(), required=False, description='')
    requester_managed = fields.List(fields.String(), required=False, description='')
    status = fields.List(fields.String(), required=False, description='')
    source_dest_check = fields.List(fields.String(), required=False, description='')
    subnet_id = fields.List(fields.String(), required=False, description='subnet id')
    vpc_id = fields.List(fields.String(), required=False, description='vpc id')


class DescribeInstancesV20ApiRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, default=10, description='', context='query')
    NextToken = fields.String(required=False, default='0', description='', context='query')
    owner_id_N = fields.List(fields.String(example=''), required=False, allow_none=False, context='query',
                             collection_format='multi', data_key='owner-id.N',
                             description='account ID of the instance owner')
    name_N = fields.List(fields.String(), required=False,  example='', description='name of the instance',
                         allow_none=True, context='query', collection_format='multi', data_key='name.N')
    name_pattern = fields.String(required=False,  example='', description='name of the instance',
                                 allow_none=True, context='query', collection_format='multi', data_key='name-pattern')
    # availability_zone_N = fields.List(fields.String(example=''), required=False, allow_none=True,
    #                                   context='query', collection_format='multi', data_key='availability-zone.N',
    #                                   description='avalaibility zone of the instance')
    # dns_name_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                          collection_format='multi', data_key='dns_name.N',
    #                          description='public DNS name of the instance')
    # hypervisor_N = fields.List(fields.String(example='', validate=OneOf(['openstack', 'vmware'])), required=False,
    #                            allow_none=True, context='query', collection_format='multi', data_key='hypervisor.N',
    #                            description='hypervisor type')
    # image_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                          collection_format='multi', data_key='image-id.N', description='image id')
    InstanceId_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                               collection_format='multi', data_key='instanceId.N', description='instance id')
    instance_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                collection_format='multi', data_key='instance-id.N', description='instance id')
    instance_state_name_N = fields.List(fields.String(example='',
                                        validate=OneOf(['pending', 'running', 'terminated', 'error'])),
                                        required=False, allow_none=True, context='query', collection_format='multi',
                                        data_key='instance-state-name.N', description='state name of the instance')
    instance_type_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                  collection_format='multi', data_key='instance-type.N',
                                  description='instance type')
    launch_time_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                collection_format='multi', data_key='launch-time.N',
                                description='time when the instance was created')
    requester_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                                 collection_format='multi', data_key='requester-id.N',
                                 description='ID of the entity that launched the instance')
    # subnet_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                           collection_format='multi', data_key='subnet-id.N', description=' ID of the subnet')
    tag_key_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                            collection_format='multi', data_key='tag-key.N',
                            description='value of a tag assigned to the resource')
    # vpc_id_N = fields.List(fields.String(example=''), required=False, allow_none=False, context='query',
    #                        collection_format='multi', data_key='vpc-id.N',
    #                        description='ID of the VPC that the instance is running in')
    # affinity = fields.List(fields.String(), required=False, example='',
    #                        description='affinity setting for the instance on the dedicated host')
    # architecture = fields.List(fields.String(), required=False, example='i386 | x86_64', description='')
    # client_token_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                              collection_format='multi', data_key='client_token.N', description='volume ID')
    # key_name_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                          collection_format='multi', data_key='launch-index.N',
    #                          description='name of the key pair used when the instance was launched')
    # launch_index_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                              collection_format='multi', data_key='launch-time.N',
    #                              description='index for the instance in the launch group')
    # ip_address_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                            collection_format='multi', data_key='ip-address.N',
    #                            description='ipv4 of the instance ')
    group_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                             collection_format='multi', data_key='instance.group-id.N',
                             description='ID of the security group. Only one is supported for the moment')
    group_name_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                               collection_format='multi', data_key='instance.group-name.N',
                               description='Name of the security group. Only one is supported for the moment')
    # host_id_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                         collection_format='multi', data_key='host-id.N',
    #                         description='ID of the host on which the instance is running')
    # monitoring_state_N = fields.List(fields.String(example='', validate=OneOf(['disabled', 'enabled'])),
    #                                  required=False, allow_none=True, context='query', collection_format='multi',
    #                                  data_key='monitoring-state.N',
    #                                  description='indicates whether monitoring is enabled')
    # placement_group_name_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
    #                                      collection_format='multi', data_key='placement-group-name.N',
    #                                      description='name of the placement group for the instance')


class DescribeInstancesV20(ServiceApiView):
    summary = 'Describe compute instance'
    description = 'Describe compute instance'
    tags = ['computeservice']
    definitions = {
        'DescribeInstancesV20ApiRequestSchema': DescribeInstancesV20ApiRequestSchema,
        'DescribeInstancesV20ApiResponseSchema': DescribeInstancesV20ApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeInstancesV20ApiRequestSchema)
    parameters_schema = DescribeInstancesV20ApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeInstancesV20ApiResponseSchema
        }
    })
    response_schema = DescribeInstancesV20ApiResponseSchema
    # TODO filter to select only instances of a specific owner

    def get(self, controller: ServiceController, data: Dict, *args, **kwargs):
        data_search = {}
        data_search['size'] = data.get('MaxResults', 10)
        data_search['page'] = int(data.get('NextToken', 0))

        # check Account
        account_id_list = data.get('owner_id_N', [])
        account_id_list.extend(data.get('requester_id_N', []))
        # if data.get('owner_id', None) is not None:
        #     account_id_list.extend([data.get('owner_id', None)])
        # account_id_list, zone_list = self.get_account_list(controller, data, ApiComputeService)

        # get instance identifier
        instance_id_list = data.get('instance_id_N', [])
        instance_id_list.extend(data.get('InstanceId_N', []))

        # get instance name
        instance_name_list = data.get('name_N', [])

        # get instance name pattern
        instance_name_pattern = data.get('name_pattern', None)

        # get instance service definition
        instance_def_list = data.get('instance_type_N', [])
        instance_def_list = [controller.get_service_def(instance_def).oid for instance_def in instance_def_list]

        # get instance launch time
        instance_launch_time_list = data.get('launch_time_N', [])
        if not isinstance(instance_launch_time_list, list):
            instance_launch_time_list = [instance_launch_time_list]
        instance_launch_time_start = None
        instance_launch_time_stop = None
        if len(instance_launch_time_list) == 1:
            instance_launch_time_start, instance_launch_time_stop = instance_launch_time_list[0].split(':')
        elif len(instance_launch_time_list) > 1:
            self.logger.warn('For the moment only one instance_launch_time can be submitted as filter')

        # get tags
        tag_values = data.get('tag_key_N', None)
        # resource_tags = ['nws$%s' % t for t in tag_values]

        # get security groups
        sgs = data.get('group_id_N', [])
        sgs.extend(data.get('group_name_N', []))
        if len(sgs) > 1:
            self.logger.warn('For the moment only one security group can be submitted as filter')

        # make search using security group
        if len(sgs) > 0 and sgs[0] is not None:
            sg = controller.get_service_instance(sgs[0])
            res, total = sg.get_linked_services(link_type='sg', filter_expired=False)
            for instSrv in res:
                instance_id_list.append(instSrv.uuid)

        # get status
        status_mapping = {
            'pending': SrvStatusType.PENDING,
            'running': SrvStatusType.ACTIVE,
            # 'stopping': SrvStatusType.STOPPING,
            # 'stopped': SrvStatusType.STOPPED,
            # 'shutting-down': SrvStatusType.SHUTTINGDOWN,
            'terminated': SrvStatusType.TERMINATED,
            'error': SrvStatusType.ERROR
        }

        status_name_list = None
        status_list = data.get('instance_state_name_N', None)
        if status_list is not None:
            status_name_list = [status_mapping[i] for i in status_list if i in status_mapping.keys()]

        # resource_uuid_list
        resource_uuid_list = None

        # get instances list
        res, total = controller.get_service_type_plugins(service_uuid_list=instance_id_list,
                                                         service_name_list=instance_name_list,
                                                         name=instance_name_pattern,
                                                         account_id_list=account_id_list,
                                                         filter_creation_date_start=instance_launch_time_start,
                                                         filter_creation_date_stop=instance_launch_time_stop,
                                                         service_definition_id_list=instance_def_list,
                                                         servicetags_or=tag_values,
                                                         service_status_name_list=status_name_list,
                                                         plugintype=ApiComputeInstance.plugintype,
                                                         resource_uuid_list=resource_uuid_list,
                                                         **data_search)

        # format result
        instances_set = [r.aws_info(version='v2.0') for r in res]

        res = {
            'DescribeInstancesResponse': {
                '__xmlns': self.xmlns,
                'nextToken': str(data_search['page'] + 1),
                'requestId': operation.id,
                'reservationSet': [{
                    'requesterId': '',
                    'reservationId': '',
                    'ownerId': '',
                    'groupSet': [{}],
                    'instancesSet': instances_set,
                    'nvl-instanceTotal': total
                }]
            }
        }
        return res


class EbsBlockDeviceMappingV20ApiRequestSchema(Schema):
    DeleteOnTermination = fields.Boolean(required=False, allow_none=True, example=True, missing=True,
                                         description='Indicates whether the EBS volume is deleted on instance '
                                                     'termination.')
    Encrypted = fields.Boolean(required=False, allow_none=True, example=False, missing=False,
                               description='Indicates whether the EBS volume is encrypted')
    Iops = fields.Integer(required=False, allow_none=True, example=10,
                          description='The number of I/O operations per second (IOPS) that the volume supports.')
    KmsKeyId = fields.String(required=False, allow_none=True, example='',
                             description='Identifier (key ID, key alias, ID ARN, or alias ARN) for a user-managed '
                                         'CMK under which the EBS volume is encrypted. ')
    SnapshotId = fields.String(required=False, allow_none=True, example='',
                               description='The ID of the snapshot.')
    Nvl_VolumeId = fields.String(required=False, allow_none=True, example='',
                                 description='The ID of the volume to clone')
    VolumeSize = fields.Integer(required=False, allow_none=True, example=10,
                                description='The size of the volume, in GiB.')
    VolumeType = fields.String(required=False, allow_none=True, example='default', missing=None,
                               description='The volume type: default, oracle.')


class BlockDeviceMappingV20ApiRequestSchema(Schema):
    DeviceName = fields.String(required=False, allow_none=True, example='/dev/sdh',
                               description='The device name (for example, /dev/sdh or xvdh).')
    Ebs = fields.Nested(EbsBlockDeviceMappingV20ApiRequestSchema, required=False, allow_none=True, example='',
                        description='Parameters used to automatically set up EBS volumes when the instance is '
                                    'launched.')
    NoDevice = fields.String(required=False, allow_none=True, example='',
                             description='Suppresses the specified device included in the block device mapping of '
                                         'the AMI.')
    VirtualName = fields.String(required=False, allow_none=True, example='/dev/sdh',
                                description='The virtual device name (ephemeralN). Instance store volumes are '
                                            'numbered starting from 0. An instance type with 2 available instance '
                                            'store volumes can specify mappings for ephemeral0 and ephemeral1.The '
                                            'number of available instance store volumes depends on the instance type. '
                                            'After you connect to the instance, you must mount the volume.')


class TagRequestSchemaV20(Schema):
    Key = fields.String(required=True, validate=Length(max=127), example='', description='tag key')
    # Value = fields.String(required=False, validate=Length(max=255), example='', description='tag value')

    @validates_schema
    def validate_unsupported_parameters(self, data, *args, **kvargs):
        keys = data.keys()
        if 'Value' in keys:
            raise ValidationError('Parameters Tags.Value is not supported. Can be used only the parameter '
                                  'Parameters Tags.Key')


class TagSpecificationMappingV20ApiRequestSchema(Schema):
    ResourceType = fields.String(required=False, example='', missing='instance', validate=OneOf(['instance']),
                                 description='type of resource to tag')
    Tags = fields.Nested(TagRequestSchemaV20, missing=[], required=False, many=True, allow_none=False,
                         description='list of tags to apply to the resource')


class RunInstancesV20ApiParamRequestSchema(Schema):
    Name = fields.String(required=False, allow_none=True, missing='default istance name', description='instance name')
    AdditionalInfo = fields.String(required=False, allow_none=True, description='instance description')
    SubnetId = fields.String(required=False, example='12', description='instance id or uuid of the subnet')
    # AccountId managed by AWS Wrapper
    owner_id = fields.String(required=True, example='1', data_key='owner-id',
                             description='account id or uuid associated to compute zone')
    # PlacementAvailabilityZone managed by AWS Wrapper
    # PlacementAvailabilityZone = fields.String(required=False, default='')
    InstanceType = fields.String(required=True, example='small2', description='service definition of the instance')
    AdminPassword = fields.String(required=False, example='myPwd1$', description='admin password to set')
    ImageId = fields.String(required=True, example='12', description='instance id or uuid of the image')
    SecurityGroupId_N = fields.List(fields.String(example='12'), required=False, allow_none=False,
                                    data_key='SecurityGroupId.N', description='list of instance security group ids')
    KeyName = fields.String(required=False, example='1ffd', description='The name of the key pair')
    # KeyValue = fields.String(required=False, example='1ffd', description='The public ssh key to inject')
    PrivateIpAddress = fields.String(required=False, example='10.102.90.23',
                                     description='The primary IPv4 address. You must specify a value from the IPv4 '
                                                 'address range of the subnet. ')
    # UserData = fields.String(required=False, example='',
    #                          description='The user data to make available to the instance. You must provide '
    #                                      'base64-encoded text.')
    BlockDeviceMapping_N = fields.Nested(BlockDeviceMappingV20ApiRequestSchema, required=False, many=True,
                                         data_key='BlockDeviceMapping.N', allow_none=True)
    # TagSpecification_N = fields.Nested(TagSpecificationMappingV20ApiRequestSchema, required=False, many=True,
    #                                    allow_none=False, data_key='TagSpecification.N',
    #                                    description='The tags to apply to the resources during launch')
    Nvl_Hypervisor = fields.String(example='openstack', missing='openstack', required=False,
                                   validate=OneOf(['openstack', 'vsphere']), description='hypervisor type')
    Nvl_Metadata = fields.Dict(example='{"cluster":"","dvp":""}', allow_none=True, required=False,
                               description='custom configuration keys')
    Nvl_MultiAvz = fields.Boolean(example=True, missing=True, required=False,
                                  description='Define if instance must be deployed to work in all the availability '
                                              'zone or only in the selected one')
    Nvl_HostGroup = fields.String(example='oracle', missing=None, required=False, description='hypervisor host group')


class RunInstancesV20ApiRequestSchema(Schema):
    instance = fields.Nested(RunInstancesV20ApiParamRequestSchema, context='body')


class RunInstancesV20ApiBodyRequestSchema(Schema):
    body = fields.Nested(RunInstancesV20ApiRequestSchema, context='body')


class RunInstancesV20Api3ResponseSchema(Schema):
    code = fields.Integer(required=False, default=0)
    name = fields.String(required=True, example='PENDING')


class RunInstancesV20Api2ResponseSchema(Schema):
    instanceId = fields.String(required=True)
    currentState = fields.Nested(RunInstancesV20Api3ResponseSchema, required=True)


class RunInstancesV20Api1ResponseSchema(Schema):
    requestId = fields.String(required=True, allow_none=True)
    instancesSet = fields.Nested(RunInstancesV20Api2ResponseSchema, many=True, required=True)


class RunInstancesV20ApiResponseSchema(Schema):
    RunInstanceResponse = fields.Nested(RunInstancesV20Api1ResponseSchema, required=True)


class RunInstancesV20(ServiceApiView):
    summary = 'Create compute instance'
    description = 'Create compute instance'
    tags = ['computeservice']
    definitions = {
        'RunInstancesV20ApiRequestSchema': RunInstancesV20ApiRequestSchema,
        'RunInstancesV20ApiResponseSchema': RunInstancesV20ApiResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(RunInstancesV20ApiBodyRequestSchema)
    parameters_schema = RunInstancesV20ApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': RunInstancesV20ApiResponseSchema
        }
    })
    response_schema = RunInstancesV20ApiResponseSchema

    def post(self, controller: ServiceController, data: dict, *args, **kwargs):
        inner_data = data.get('instance')

        service_definition_id = inner_data.get('InstanceType')
        account_id = inner_data.get('owner_id')
        name = inner_data.get('Name')
        if name is None:
            raise ApiManagerError('The Name of the VM cannot be None')

        desc = inner_data.get('AdditionalInfo')
        if desc is None:
            desc = ''

        block_device_mappings = inner_data.get('BlockDeviceMapping_N')
        if block_device_mappings is None or len(block_device_mappings) == 0:
            raise ApiManagerError('BlockDeviceMapping_N cannot be None, should be provided with EBS information')

        # check instance with the same name already exists
        # self.service_exist(controller, name, ApiComputeInstance.plugintype)

        # check account
        account, parent_plugin = self.check_parent_service(controller, account_id,
                                                           plugintype=ApiComputeService.plugintype)
        data['computeZone'] = parent_plugin.resource_uuid

        # check service definition
        service_defs, total = controller.get_paginated_service_defs(
            service_definition_uuid_list=[service_definition_id], plugintype=ApiComputeInstance.plugintype)
        self.logger.warn(service_defs)
        if total < 1:
            raise ApiManagerError('InstanceType is wrong')

        # create service instance
        inst = controller.add_service_type_plugin(service_definition_id, account_id, name=name, desc=desc,
                                                  parent_plugin=parent_plugin, instance_config=data, account=account)

        instances_set = [{
            'instanceId': inst.instance.uuid,
            'currentState': {
                'name': inst.instance.status
            }
        }]
        res = self.format_create_response('RunInstanceResponse', instances_set)

        return res, 202


class ModifyInstanceAttributeV20(ModifyInstanceAttribute):
    pass


class TerminateInstancesV20(TerminateInstances):
    pass


class StartInstancesV20(StartInstances):
    pass


class StopInstancesV20(StopInstances):
    pass


class RebootInstancesV20(RebootInstances):
    pass


class GetConsoleV20Api2ResponseSchema(Schema):
    url = fields.String(required=True, example='https://localhost:443/vnc_auto.html?path=%3Ftoken%3D2317d'
                                               '94c-b82a-4262-8193-f7fc01a03874', description='console url')
    type = fields.String(required=True, example='novnc', description='console type')
    protocol = fields.String(required=True, example='vnc', description='console protocol')


class GetConsoleV20Api1ResponseSchema(Schema):
    requestId = fields.String(required=True, default='', description='request id')
    instancesId = fields.String(required=False, description='instance id')
    console = fields.Nested(GetConsoleV20Api2ResponseSchema, required=True, many=False, description='console data')
    instanceId = fields.String(required=False, description='elk-04-ubuntu')
    xmlns = fields.String(required=False, data_key='__xmlns')


class GetConsoleV20ApiResponseSchema(Schema):
    GetConsoleResponse = fields.Nested(GetConsoleV20Api1ResponseSchema, required=True, many=False, allow_none=False)


class GetConsoleV20ApiRequestSchema(Schema):
    owner_id = fields.String(required=False, context='query', description='account ID of the instance owner')
    InstanceId = fields.String(required=True, context='query', description='instance id')


class GetConsoleV20(ServiceApiView):
    summary = 'Get instance native console'
    description = 'Get instance native console'
    tags = ['computeservice']
    definitions = {
        'GetConsoleV20ApiRequestSchema': GetConsoleV20ApiRequestSchema,
        'GetConsoleV20ApiResponseSchema': GetConsoleV20ApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetConsoleV20ApiRequestSchema)
    parameters_schema = GetConsoleV20ApiRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': GetConsoleV20ApiResponseSchema
        }
    })
    response_schema = GetConsoleV20ApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        instance_id = data.pop('InstanceId')
        type_plugin = controller.get_service_type_plugin(instance_id)
        console = type_plugin.get_console()

        res = {
            'GetConsoleResponse': {
                '__xmlns': self.xmlns,
                'requestId': operation.id,
                'instanceId': instance_id,
                'console': console,
            }
        }
        return res


class InstanceTypeFeatureResponseSchema (Schema):
    vcpus = fields.String(required=False, allow_none=True, example='', description='')
    ram = fields.String(required=False, allow_none=True, example='', description='')
    disk = fields.String(required=False, allow_none=True, example='', description='')


class InstanceTypeResponseSchema(Schema):
    id = fields.Integer(required=True, example='', description='')
    uuid = fields.String(required=True, example='', description='')
    name = fields.String(required=True, example='', description='')
    resource_id = fields.String(required=False, allow_none=True, example='', description='')
    description = fields.String(required=True, allow_none=True, example='', description='')
    features = fields.Nested(InstanceTypeFeatureResponseSchema, required=True, many=False, allow_none=False)


class DescribeInstanceTypesV20Api1ResponseSchema(Schema):
    requestId = fields.String(required=True)
    instanceTypesSet = fields.Nested(InstanceTypeResponseSchema, required=True, many=True, allow_none=True)
    instanceTypesTotal = fields.Integer(required=True)
    xmlns = fields.String(required=False, data_key='$xmlns')


class DescribeInstanceTypesV20ApiResponseSchema(Schema):
    DescribeInstanceTypesResponse = fields.Nested(DescribeInstanceTypesV20Api1ResponseSchema, required=True,
                                                  many=False, allow_none=False)


class DescribeInstanceTypesV20ApiRequestSchema(Schema):
    MaxResults = fields.Integer(required=False, default=10, missing=10, description='entities list page size',
                                context='query')
    NextToken = fields.Integer(required=False, default=0, missing=0, description='entities list page selected',
                               context='query')
    owner_id = fields.String(example='d35d19b3-d6b8-4208-b690-a51da2525497', required=True, context='query',
                             data_key='owner-id', description='account id of the instance type owner')
    InstanceType = fields.String(example='d35d19b3-d6b8-4208-b690-a51da2525497', required=False, context='query',
                                 missing=None, data_key='InstanceType', description='instance type id')


class DescribeInstanceTypesV20(ServiceApiView):
    summary = 'Describe compute instance types'
    description = 'Describe compute instance types'
    tags = ['computeservice']
    definitions = {
        'DescribeInstanceTypesV20ApiRequestSchema': DescribeInstanceTypesV20ApiRequestSchema,
        'DescribeInstanceTypesV20ApiResponseSchema': DescribeInstanceTypesV20ApiResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(DescribeInstanceTypesV20ApiRequestSchema)
    parameters_schema = DescribeInstanceTypesV20ApiRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': DescribeInstanceTypesV20ApiResponseSchema
        }
    })
    response_schema = DescribeInstanceTypesV20ApiResponseSchema

    def get(self, controller, data, *args, **kwargs):
        account_id = data.pop('owner_id')
        size = data.pop('MaxResults')
        page = data.pop('NextToken')
        def_id = data.pop('InstanceType')
        account = controller.get_account(account_id)

        instance_types_set, total = account.get_definitions(plugintype=ApiComputeInstance.plugintype,
                                                            service_definition_id=def_id, size=size, page=page)

        res_type_set = []
        for r in instance_types_set:
            res_type_item = {
                'id': r.oid,
                'uuid': r.uuid,
                'name': r.name,
                'description': r.desc
            }

            features = []
            if r.desc is not None:
                features = r.desc.split(' ')

            feature = {}
            for f in features:
                try:
                    k, v = f.split(':')
                    feature[k] = v
                except ValueError:
                    pass

            res_type_item['features'] = feature
            res_type_set.append(res_type_item)

        if total == 1:
            res_type_set[0]['config'] = instance_types_set[0].get_main_config().params

        res = {
            'DescribeInstanceTypesResponse': {
                '$xmlns': self.xmlns,
                'requestId': operation.id,
                'instanceTypesSet': res_type_set,
                'instanceTypesTotal': total
            }
        }
        return res


class DescribeInstanceSnapshotsV20(DescribeInstanceSnapshots):
    pass


class CreateInstanceSnapshotsV20(CreateInstanceSnapshots):
    pass


class DeleteInstanceSnapshotsV20(DeleteInstanceSnapshots):
    pass


class RevertInstanceSnapshotsV20(RevertInstanceSnapshots):
    pass


class MonitorInstancesV20(MonitorInstances):
    pass


class UnmonitorInstancesV20(UnmonitorInstances):
   pass


class ForwardLogInstancesV20(ForwardLogInstances):
    pass


#class UnforwardLogInstancesV20(UnforwardLogInstances):
#    pass


class ComputeInstanceV2API(ApiView):
    @staticmethod
    def register_api(module, rules=None, **kwargs):
        base = module.base_path + '/computeservices/instance'
        rules = [
            # instance
            ('%s/describeinstances' % base, 'GET', DescribeInstancesV20, {}),
            ('%s/runinstances' % base, 'POST', RunInstancesV20, {}),
            ('%s/modifyinstanceattribute' % base, 'PUT', ModifyInstanceAttributeV20, {}),
            ('%s/terminateinstances' % base, 'DELETE', TerminateInstancesV20, {}),
            ('%s/startinstances' % base, 'PUT', StartInstancesV20, {}),
            ('%s/stopinstances' % base, 'PUT', StopInstancesV20, {}),
            ('%s/rebootinstances' % base, 'PUT', RebootInstancesV20, {}),

            # instance console
            ('%s/getconsole' % base, 'GET', GetConsoleV20, {}),

            # instance types
            ('%s/describeinstancetypes' % base, 'GET', DescribeInstanceTypesV20, {}),

            # instance snapshot
            ('%s/describeinstancesnapshots' % base, 'GET', DescribeInstanceSnapshotsV20, {}),
            ('%s/createinstancesnapshots' % base, 'PUT', CreateInstanceSnapshotsV20, {}),
            ('%s/deleteinstancesnapshots' % base, 'PUT', DeleteInstanceSnapshotsV20, {}),
            ('%s/revertinstancesnapshots' % base, 'PUT', RevertInstanceSnapshotsV20, {}),

            # instance monitoring
            ('%s/monitorinstances' % base, 'PUT', MonitorInstancesV20, {}),
            ('%s/unmonitorinstances' % base, 'PUT', UnmonitorInstancesV20, {}),

            # instance forward log
            ('%s/forwardloginstances' % base, 'PUT', ForwardLogInstancesV20, {}),
            # ('%s/unforwardloginstances' % base, 'PUT', UnforwardLogInstancesV20, {})
        ]
        kwargs["version"]='v2.0'
        ApiView.register_api(module, rules, **kwargs)
