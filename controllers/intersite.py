from flask import make_response, abort
from neutronclient.common import exceptions as neutronclient_exc
from random import seed
from random import randint
from service import Service, ServiceSchema, Resource, Interconnexion, Parameter, ServiceParamssSchema, ServiceResourcesSchema, ServiceInterconnectionsSchema
from config import db
import common.utils as service_utils
import copy
import math
import json
import ipaddress
import itertools
import string
import random
import requests


# Data to serve with our API
SERVICE_TYPE = {'L2': 'network_l2', 'L3': 'network_l3'}
local_region_name = service_utils.get_region_name()
# /intersite-vertical/
# Create a handler for our read (GET) services


def read_region_name():
    var_temp = service_utils.get_region_name()
    # print(var_temp)
    return var_temp


def vertical_read_all_service():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    services = Service.query.order_by(Service.service_global).all()

    # Serialize the data for the response
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    # print(data)
    return data

# Create a handler for our read (GET) one service by ID
# Possibility to add more information as ids of remote interconnection resources


def vertical_read_one_service(global_id):
    service = Service.query.filter(Service.service_global == global_id).outerjoin(
        Resource).outerjoin(Interconnexion).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        data = service_schema.dump(service).data
        return data

    else:
        abort(404, "Service with ID {id} not found".format(id=id))


def vertical_create_service(service):
    # Taking information from the API http POST request
    local_region_url = service_utils.get_local_keystone()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    #service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k, v in (
        (item.split(',')) for item in service.get("resources", None)))
    service_resources_list_search = copy.deepcopy(service_resources_list)
    # print(service_resources_list)
    service_remote_auth_endpoints = {}
    service_remote_inter_endpoints = {}
    parameter_local_allocation_pool = ''
    parameter_local_cidr = ''
    parameter_local_ipv = 'v4'
    local_interconnections_ids = []
    random_id = create_random_global_id()

    # Check if a service exists with the requested resources
    existing_service, check_service_id = check_existing_service(
        service_resources_list)
    if(existing_service):
        abort(404, "Service with global ID {global_check} already connects the resources".format(
            global_check=check_service_id))

    to_service = {
        # 'id': id,
        'service_name': service_name,
        'service_type': service_type,
        'service_global': random_id
        # 'service_resources': service_resources_list,
        # 'service_interconnections': local_interconnections_ids
    }

    for k, v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            break

    # if(local_resource == ''):
    #    abort(404, "There is no local resource for the service")

    # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalog
    catalog_endpoints = service_utils.get_keystone_catalog(local_region_url)
    for obj in catalog_endpoints:
        if obj['name'] == 'neutron':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name:
                        service_remote_inter_endpoints[region_name] = endpoint['url']
                        service_resources_list_search.pop(region_name)
                        break
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    # If a provided Region Name doesn't exist, exit the method
    if bool(service_resources_list_search):
        abort(404, "ERROR: Regions " + (" ".join(str(key)
                                                 for key in service_resources_list_search.keys())) + " are not found")

    subnetworks = {}
    CIDRs = []
    # Retrieving information for networks given the region name
    for item, value in service_resources_list.items():
        neutron_client = service_utils.get_neutron_client(
            service_remote_auth_endpoints[item],
            item
        )

        try:
            network_temp = (
                neutron_client.show_network(network=value
                                            )
            )
            subnet = network_temp['network']
            subnetworks[item] = subnet['subnets'][0]

        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

        # Retrieving the subnetwork information given the region name
    for item, value in subnetworks.items():
        neutron_client = service_utils.get_neutron_client(
            service_remote_auth_endpoints[item],
            item
        )
        try:
            subnetwork_temp = (
                neutron_client.show_subnet(subnet=value)
            )

            subnet = subnetwork_temp['subnet']
            CIDRs.append(ipaddress.ip_network(subnet['cidr']))
            if (item == local_region_name):
                parameter_local_cidr = subnet['cidr']
        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

    # Validation for the L3 routing service
    if service_type == 'L3':

        print("L3 routing service to be done among the resources: " +
              (" ".join(str(value) for value in service_resources_list.values())))
        print(subnetworks)

        # Doing the IP range validation to avoid overlapping problems
        for a, b in itertools.combinations(CIDRs, 2):
            if a.overlaps(b):
                return "ERROR: networks " + " " + (str(a)) + " and "+(str(b)) + " overlap"

    # Validation for the Layer 2 network extension
    if service_type == 'L2':

        print("L2 extension service to be done among the resources: " +
              (" ".join(str(value) for value in service_resources_list.values())))

        # Validating if the networks have the same CIDR
        if not check_equal_element(CIDRs):
            return "ERROR: CIDR is not the same for all the resources"

        # test
        #CIDRs = [ipaddr.IPNetwork("20.0.0.0/23"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24")]
        #service_resources_list = [5,4,2,5,6,7,5,5,5,8,5,2,6,5,8,4,5,8]
        cidr = CIDRs[0]
        parameter_local_cidr = str(cidr)
        main_cidr = str(CIDRs[0])
        main_cidr_base = ((str(CIDRs[0])).split("/", 1)[0])
        main_cidr_prefix = ((str(CIDRs[0])).split("/", 1)[1])
        cidr_ranges = []
        # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
        ips_cidr_available = 2**(32-int(main_cidr_prefix))-3
        host_per_site = math.floor(
            ips_cidr_available/len(service_resources_list))
        print("CIDR: " + str(cidr) + ", total available IPs: " + str(ips_cidr_available) +
              " , Number of sites: " + str(len(service_resources_list)) + " , IPs per site:" + str(host_per_site))
        base_index = 3
        site_index = 1
        while base_index <= ips_cidr_available and site_index <= len(service_resources_list):
            cidr_ranges.append(
                str(cidr[base_index])+"-"+str(cidr[base_index+host_per_site-1]))
            base_index = base_index + int(host_per_site)
            site_index = site_index + 1

        parameter_local_allocation_pool = cidr_ranges[0]

        print('Next ranges will be used:')
        for element in cidr_ranges:
            print(element)

    # calling the interconnection service plugin to create the necessary objects
    id_temp = 1
    for k, v in service_resources_list.items():

        if local_region_name != k:
            neutron_client = service_utils.get_neutron_client(
                local_region_url,
                local_region_name
            )
            interconnection_data = {'interconnection': {
                'name': service_name+str(id_temp),
                'remote_keystone': service_remote_auth_endpoints[k],
                'remote_region': k,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': v,

            }}
            id_temp = id_temp+1
            try:
                inter_temp = (
                    neutron_client.create_interconnection(interconnection_data)
                )
                # print(inter_temp)
                local_interconnections_ids.append(
                    inter_temp['interconnection']['id'])

            except neutronclient_exc.ConnectionFailed:
                print("Can't connect to neutron %s" %
                      service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %
                      service_remote_inter_endpoints[item])

    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    for k, v in service_resources_list.items():
        resource = {
            'resource_region': k,
            'resource_uuid': v
        }
        service_resources_schema = ServiceResourcesSchema()
        new_service_resources = service_resources_schema.load(
            resource, session=db.session).data
        new_service.service_resources.append(new_service_resources)

    # Adding the parameters to the service
    parameters = {
        'parameter_allocation_pool': parameter_local_allocation_pool,
        'parameter_local_cidr': parameter_local_cidr,
        'parameter_ipv': parameter_local_ipv
    }
    service_params_schema = ServiceParamssSchema()
    new_service_params = service_params_schema.load(
        parameters, session=db.session).data
    new_service.service_params.append(new_service_params)

    # Adding the interconnections to the service
    for element in local_interconnections_ids:
        interconnexion = {
            'interconnexion_uuid': element
        }
        service_interconnections_schema = ServiceInterconnectionsSchema()
        new_service_interconnections = service_interconnections_schema.load(
            interconnexion, session=db.session).data
        new_service.service_interconnections.append(
            new_service_interconnections)

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    # Updating the DHCP pool ranges for the local deployment
    if service_type == 'L2':
        allocation_start = cidr_ranges[0].split("-", 1)[0]
        allocation_end = cidr_ranges[0].split("-", 1)[1]
        try:
            body = {'subnet': {'allocation_pools': [
                {'start': allocation_start, 'end': allocation_end}]}}
            dhcp_change = (
                neutron_client.update_subnet(
                    subnetworks[local_region_name], body=body)
            )
            # print(inter_temp)
        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

        nova_client = service_utils.get_nova_client(service_utils.get_local_keystone(),
                                                    service_utils.get_region_name())

        # Check if there are hot-plugged VMs with IPs outside the allocation pool

        try:
            nova_list = nova_client.servers.list()

        except novaclient.exceptions.NotFound:
            print("Can't connect to nova %s" %
                  service_remote_inter_endpoints[item])
        except novaclient.exceptions.Unauthorized:
            print("Connection refused to nova %s" %
                  service_remote_inter_endpoints[item])

        vms_with_ip_in_network = []
        for element in nova_list:
            vm_name = str(element).split(' ', 1)[1][0:-1]
            answer = nova_client.servers.interface_list(element.id)
            for element1 in answer:
                list_with_meta = element1.to_dict()
                if(list_with_meta['net_id'] == local_resource):
                    vms_with_ip_in_network.append({'id': element.id, 'name': element.name, 'port_id': list_with_meta['port_id'], 'net_id': list_with_meta[
                        'net_id'], 'ip': list_with_meta['fixed_ips'][0]['ip_address'], 'subnet_id': list_with_meta['fixed_ips'][0]['subnet_id']})

        for machine_opts in vms_with_ip_in_network:
            if((ipaddress.IPv4Address(machine_opts['ip']) < ipaddress.IPv4Address(allocation_start)) or (ipaddress.IPv4Address(machine_opts['ip']) > ipaddress.IPv4Address(allocation_end))):
                print('Changing the IPs for VMs in the local deployment')
                print(machine_opts['name'], machine_opts['ip'])
                detach_interface = nova_client.servers.interface_detach(
                    machine_opts['id'], machine_opts['port_id'])
                attach_interface = nova_client.servers.interface_attach(
                    machine_opts['id'], port_id='', net_id=machine_opts['net_id'], fixed_ip='')

                # As for the test scenario, CirrOS can't renew its IP address, need to test this in another scenario
                # restart_machine = nova_client.servers.reboot(
                #    machine_opts['id'])

    index_cidr = 1
    # Sending remote inter-site create requests to the distant nodes
    for obj in service_resources_list.keys():
        if obj != service_utils.get_region_name():
            remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                '9696/')
            remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'

            if service_type == 'L2':
                remote_service = {'name': service_name, 'type': service_type, 'params': [cidr_ranges[index_cidr], parameter_local_cidr, parameter_local_ipv],
                                  'global': random_id, 'resources': service.get("resources", None)}
                index_cidr = index_cidr + 1
            else:
                remote_service = {'name': service_name, 'type': service_type, 'params': ['', '', parameter_local_ipv],
                                  'global': random_id, 'resources': service.get("resources", None)}
            # send horizontal (service_remote_inter_endpoints[obj])
            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}
            r = requests.post(remote_inter_instance, data=json.dumps(
                remote_service), headers=headers)
            # print(r.json())
            print(service_schema.dump(new_service).data)

    return service_schema.dump(new_service).data, 201


# Handler to update an existing service


def vertical_update_service(global_id, service):

    service_update = Service.query.filter(
        Service.service_global == global_id).one_or_none()

    # Did we find a service?
    if service_update is not None:
        # turn the passed in service into a db object
        service_schema = ServiceSchema()
        to_update = service_schema.load(service, session=db.session).data

        service_schema_temp = ServiceSchema()
        data_from_db = service_schema_temp.dump(service_update).data

        # print(data_from_db['service_resources'])

        to_service_resources_list = dict((k.strip(), v.strip()) for k, v in (
            (item.split(',')) for item in service.get("resources", None)))
        service_resources_list_user = []
        for key, value in to_service_resources_list.items():
            service_resources_list_user.append(
                {'resource_uuid': value, 'resource_region': key})
        # print(service_resources_list_user)

        service_resources_list_db = []
        for element in data_from_db['service_resources']:
            service_resources_list_db.append(
                {'resource_uuid': element['resource_uuid'], 'resource_region': element['resource_region']})
        # print(service_resources_list_db)
        list_resources_remove = copy.deepcopy(service_resources_list_db)
        list_resources_add = []

        for resource_component in service_resources_list_user:
            contidion_temp = True
            for resource_component_2 in service_resources_list_db:
                if resource_component == resource_component_2:
                    # print(resource_component)
                    list_resources_remove.remove(resource_component_2)
                    contidion_temp = False
                    break
            if(contidion_temp == True):
                list_resources_add.append(resource_component)

        print('actual list of resources', service_resources_list_db)
        print('resources to add', list_resources_add)
        print('resources to delete', list_resources_remove)
        search_local_resource_delete = False
        search_local_resource_uuid = ''

        for element in service_resources_list_db:
            if(local_region_name in element['resource_region']):
                search_local_resource_uuid = element['resource_uuid']
                break
        # TODO change local_region_name for search_local_resource_uuid
        for element in list_resources_remove:
            if(local_region_name in element['resource_region']):
                search_local_resource_delete = True

        if(search_local_resource_delete):
            print('local resource ' + search_local_resource_uuid + ' will be deleted and with it, the service '+ data_from_db['service_global'])
            interconnections_delete = data_from_db['service_interconnections']
            for element in interconnections_delete:
                inter = element['interconnexion_uuid']
                neutron_client = service_utils.get_neutron_client(
                    service_utils.get_local_keystone(),
                    service_utils.get_region_name()
                )
                try:
                    inter_del = (
                        neutron_client.delete_interconnection(inter))

                except neutronclient_exc.ConnectionFailed:
                    print("Can't connect to neutron %s" %
                        service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    print("Connection refused to neutron %s" %
                        service_remote_inter_endpoints[item])
                except neutronclient_exc.NotFound:
                    print("Element not found %s" % inter)

            db.session.delete(service_update)
            db.session.commit()

        else:
            print('TODO')

        # Set the id to the service we want to update
        #to_update.service_id = service_update.service_id
        #to_update.service_global = service_update.service_global

        # Merge the new object into the old and commit it into the DB
        #db.session.merge(to_update)
        #db.session.commit()

        #service_data = service_schema.dump(service_update)

        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        abort(404, "Service not found with global ID: {global_id}")

# Handler to delete a service


def vertical_delete_service(global_id):
    local_region_url = service_utils.get_local_keystone()
    service_remote_inter_endpoints = {}
    service = Service.query.filter(
        Service.service_global == global_id).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        service_data = service_schema.dump(service).data
        resources_list_to_delete = service_data['service_resources']
        # print(resources_list_to_delete)
        interconnections_delete = service_data['service_interconnections']
        for element in interconnections_delete:
            inter = element['interconnexion_uuid']
            neutron_client = service_utils.get_neutron_client(
                service_utils.get_local_keystone(),
                service_utils.get_region_name()
            )
            try:
                inter_del = (
                    neutron_client.delete_interconnection(inter))

            except neutronclient_exc.ConnectionFailed:
                print("Can't connect to neutron %s" %
                      service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %
                      service_remote_inter_endpoints[item])

        db.session.delete(service)
        db.session.commit()

        catalog_endpoints = service_utils.get_keystone_catalog(
            local_region_url)
        for obj in catalog_endpoints:
            if obj['name'] == 'neutron':
                for endpoint in obj['endpoints']:
                    # print(endpoint)
                    for region_name in resources_list_to_delete:
                        # print(region_name)
                        if endpoint['region'] == region_name['resource_region']:
                            service_remote_inter_endpoints[region_name['resource_region']
                                                           ] = endpoint['url']
                            break

        # print(service_remote_inter_endpoints)
        # Sending remote inter-site delete requests to the distant nodes
        for obj in resources_list_to_delete:
            remote_inter_instance = ''
            if obj['resource_region'] != service_utils.get_region_name():
                remote_inter_instance = service_remote_inter_endpoints[obj['resource_region']].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal/' + global_id
                # send horizontal delete (service_remote_inter_endpoints[obj])
                headers = {'Accept': 'text/html'}
                r = requests.delete(remote_inter_instance, headers=headers)

        return make_response("{id} successfully deleted".format(id=global_id), 200)

    else:
        abort(404, "Service with ID {id} not found".format(id=global_id))


# /intersite-horizontal
# Handler for inter-site service creation request

def horizontal_create_service(service):
    local_region_name = service_utils.get_region_name()
    local_region_url = service_utils.get_local_keystone()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    service_params = service.get("params", None)
    print(service_params)
    service_global = service.get("global", None)
    #service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k, v in (
        (item.split(',')) for item in service.get("resources", None)))
    service_remote_auth_endpoints = {}
    local_interconnections_ids = []

    to_service = {
        'service_name': service_name,
        'service_type': service_type,
        'service_global': service_global
    }

    for k, v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            break

    # Saving info for Keystone endpoints to be contacted based on keystone catalog
    catalog_endpoints = service_utils.get_keystone_catalog(local_region_url)
    for obj in catalog_endpoints:
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    # calling the interconnection service plugin to create the necessary objects
    for k, v in service_resources_list.items():
        if local_region_name != k:
            neutron_client = service_utils.get_neutron_client(
                local_region_url,
                local_region_name
            )
            interconnection_data = {'interconnection': {
                'name': service_name,
                'remote_keystone': service_remote_auth_endpoints[k],
                'remote_region': k,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': v,

            }}
            try:
                inter_temp = (
                    neutron_client.create_interconnection(
                        interconnection_data)
                )
                # print(inter_temp)
                local_interconnections_ids.append(
                    inter_temp['interconnection']['id'])

            except neutronclient_exc.ConnectionFailed:
                print("Can't connect to neutron %s" %
                      service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %
                      service_remote_inter_endpoints[item])

            

    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    for k, v in service_resources_list.items():
        resource = {
            'resource_region': k,
            'resource_uuid': v
        }
        service_resources_schema = ServiceResourcesSchema()
        new_service_resources = service_resources_schema.load(
            resource, session=db.session).data
        new_service.service_resources.append(new_service_resources)

    # Adding the interconnections to the service
    for element in local_interconnections_ids:
        interconnexion = {
            'interconnexion_uuid': element
        }
        service_interconnections_schema = ServiceInterconnectionsSchema()
        new_service_interconnections = service_interconnections_schema.load(
            interconnexion, session=db.session).data
        new_service.service_interconnections.append(
            new_service_interconnections)

    # Adding the parameters to the service
    parameters = {
        'parameter_allocation_pool': service_params[0],
        'parameter_local_cidr': '',
        'parameter_ipv': service_params[2]
    }
    if(service_type=='L2'):
        parameters['parameter_local_cidr']=service_params[1]
    else:
        neutron_client = service_utils.get_neutron_client(
            service_remote_auth_endpoints[item],
            item
        )

        try:
            network_temp = (
                neutron_client.show_network(network=local_resource
                                            )
            )
            subnet_id = network_temp['network']['subnets'][0]

        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

        try:
            subnetwork_temp = (
                neutron_client.show_subnet(subnet=subnet_id)
            )

            subnet = subnetwork_temp['subnet']
            parameters['parameter_local_cidr'] = subnet['cidr']
            
        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

    service_params_schema = ServiceParamssSchema()
    new_service_params = service_params_schema.load(
        parameters, session=db.session).data
    new_service.service_params.append(new_service_params)

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    # If the service is from L2 type, do the local DHCP change

    if service_type == 'L2':
        try:
            body = {'subnet': {'allocation_pools': [{'start': parameters['allocation_pool'].split(
                "-", 1)[0], 'end': parameters['allocation_pool'].split("-", 1)[1]}]}}

            network_temp = (
                neutron_client.show_network(network=local_resource
                                            )
            )
            subnet = network_temp['network']['subnets'][0]
            print(subnet)

            dhcp_change = (
                neutron_client.update_subnet(
                    subnet, body=body)
            )
            # print(inter_temp)
        except neutronclient_exc.ConnectionFailed:
            print("Can't connect to neutron %s" %
                  service_remote_inter_endpoints[item])
        except neutronclient_exc.Unauthorized:
            print("Connection refused to neutron %s" %
                  service_remote_inter_endpoints[item])

        # Check if there are hot-plugged VMs with IPs outside the allocation pool

        nova_client = service_utils.get_nova_client(service_utils.get_local_keystone(),
                                                    service_utils.get_region_name())

        try:
            nova_list = nova_client.servers.list()

        except novaclient.exceptions.NotFound:
            print("Can't connect to nova %s" %
                  service_remote_inter_endpoints[item])
        except novaclient.exceptions.Unauthorized:
            print("Connection refused to nova %s" %
                  service_remote_inter_endpoints[item])

        vms_with_ip_in_network = []
        for element in nova_list:
            vm_name = str(element).split(' ', 1)[1][0:-1]
            answer = nova_client.servers.interface_list(element.id)
            for element1 in answer:
                list_with_meta = element1.to_dict()
                if(list_with_meta['net_id'] == local_resource):
                    vms_with_ip_in_network.append({'id': element.id, 'name': element.name, 'port_id': list_with_meta['port_id'], 'net_id': list_with_meta[
                        'net_id'], 'ip': list_with_meta['fixed_ips'][0]['ip_address'], 'subnet_id': list_with_meta['fixed_ips'][0]['subnet_id']})

        for machine_opts in vms_with_ip_in_network:
            if((ipaddress.IPv4Address(machine_opts['ip']) < ipaddress.IPv4Address(service_params['parameter_allocation_pool'].split(
                "-", 1)[0])) or (ipaddress.IPv4Address(machine_opts['ip']) > ipaddress.IPv4Address(service_params.split(
                    "-", 1)[1]))):
                print('Changing the IPs for VMs in the local deployment')
                print(machine_opts['name'], machine_opts['ip'])
                detach_interface = nova_client.servers.interface_detach(
                    machine_opts['id'], machine_opts['port_id'])
                attach_interface = nova_client.servers.interface_attach(
                    machine_opts['id'], port_id='', net_id=machine_opts['net_id'], fixed_ip='')
                restart_machine = nova_client.servers.reboot(
                    machine_opts['id'])

    return service_schema.dump(new_service).data, 201

# Handler to delete a service


def horizontal_delete_service(global_id):
    local_region_url = service_utils.get_local_keystone()
    service_remote_inter_endpoints = {}
    service = Service.query.filter(
        Service.service_global == global_id).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        service_data = service_schema.dump(service).data
        resources_list_to_delete = service_data['service_resources']
        # print(resources_list_to_delete)
        interconnections_delete = service_data['service_interconnections']
        for element in interconnections_delete:
            inter = element['interconnexion_uuid']
            neutron_client = service_utils.get_neutron_client(
                service_utils.get_local_keystone(),
                service_utils.get_region_name()
            )
            try:
                inter_del = (
                    neutron_client.delete_interconnection(inter))

            except neutronclient_exc.ConnectionFailed:
                print("Can't connect to neutron %s" %
                      service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %
                      service_remote_inter_endpoints[item])

        db.session.delete(service)
        db.session.commit()

        return make_response("{id} successfully deleted".format(id=global_id), 200)

    else:
        abort(404, "Service with ID {id} not found".format(id=global_id))

# Utils


def check_equal_element(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)


def check_existing_service(resource_list):

    services = Service.query.all()
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    search_list_dict = {}
    for element in data:
        temp_dict = {}
        for next_resource in element['service_resources']:
            temp_dict[next_resource['resource_region']
                      ] = next_resource['resource_uuid']
        search_list_dict[element['service_global']] = temp_dict
    for key, value in search_list_dict.items():
        # print(key)
        if(value == resource_list):
            return True, key
    return False, ''


def create_random_global_id(stringLength=28):
    lettersAndDigits = string.ascii_lowercase[0:5] + string.digits
    result = ''.join(random.choice(lettersAndDigits) for i in range(8))
    result1 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result2 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result3 = ''.join(random.choice(lettersAndDigits) for i in range(12))
    global_random_id = result + '-' + result1 + '-' + result2 + '-'+result3

    return global_random_id
