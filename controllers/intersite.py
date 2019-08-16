from flask import make_response, abort
from neutronclient.common import exceptions as neutronclient_exc
from random import seed
from random import randint
from service import Service, ServiceSchema, Resource, Interconnexion, ServiceResourcesSchema, ServiceInterconnectionsSchema
from config import db
import common.utils as service_utils
import copy
import json
import ipaddr
import itertools
import string
import random
import requests


# Data to serve with our API
SERVICE_TYPE = {'L2': 'network_l2', 'L3': 'network_l3'}

# /intersite-vertical/
# Create a handler for our read (GET) services


def vertical_read_all_service():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    services = Service.query.order_by(Service.service_name).all()

    # Serialize the data for the response
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    print(data)
    return data

# Create a handler for our read (GET) one service by ID
# Possibility to add more information as ids of remote interconnection resources


def vertical_read_one_service(global_id):
    service = Service.query.filter(Service.service_global == global_id).outerjoin(
        Resource).outerjoin(Interconnexion).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        data = service_schema.dump(service).data
        print(data)
        return data

    else:
        abort(404, "Service with ID {id} not found".format(id=id))


def vertical_create_service(service):
    # Taking information from the API http POST request
    local_region_name = service_utils.get_region_name()
    local_region_url = service_utils.get_local_keystone()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    #service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k, v in (
        (item.split(',')) for item in service.get("resources", None)))
    service_resources_list_search = copy.deepcopy(service_resources_list)
    service_remote_auth_endpoints = {}
    service_remote_inter_endpoints = {}
    local_interconnections_ids = []
    random_id = create_random_global_id(12)

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
        return "ERROR: Regions " + ("".join(str(key) for key in service_resources_list_search.keys())) + " are not found"

    # Validation for the L3 routing service
    if service_type == 'L3':
        print("L3 routing service to be done among the resources: " +
              (" ".join(str(value) for value in service_resources_list.values())))
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
                CIDRs.append(ipaddr.IPNetwork(subnet['cidr']))

            except neutronclient_exc.ConnectionFailed:
                print("Can't connect to neutron %s" %
                      service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %
                      service_remote_inter_endpoints[item])

        # Doing the IP range validation to avoid overlapping problems
        for a, b in itertools.combinations(CIDRs, 2):
            if a.overlaps(b):
                return "ERROR: networks " + " ".join(str(a)) + " ".join(str(b)) + " overlap"

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

        # Add the service to the database
        db.session.add(new_service)
        db.session.commit()

        # Sending remote inter-site create requests to the distant nodes
        for obj in service_resources_list.keys():
            if obj != service_utils.get_region_name():
                remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                remote_service = {'name': service_name, 'type': service_type,
                                  'global': random_id, 'resources': service.get("resources", None)}
                # send horizontal (service_remote_inter_endpoints[obj])
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}
                r = requests.post(remote_inter_instance, data=json.dumps(remote_service), headers=headers)
                print(r.json())

        return service_schema.dump(new_service).data, 201

# Handler to update an existing service


def vertical_update_service(id, service_resources_list):
    print("TO BE DONE")

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
                r = requests.delete(remote_inter_instance,headers=headers)
                
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

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

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


def check_existing_service(resource_list):
    print("ja")


def create_random_global_id(stringLength=8):
    lettersAndDigits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))
