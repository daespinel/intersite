from flask import make_response, abort
from neutronclient.common import exceptions as neutronclient_exc
import utils as service_utils
import copy
import json
import ipaddr
import itertools


# Data to serve with our API
SERVICE_TYPE = {'L2':'network_l2','L3':'network_l3'}

SERVICES = {
    "Service1": {
        "type": "L3",
        "name": "Service1",
        "resources": ["id1,RegionOne","id2,RegionTwo","id3,RegionThree"]
    },
    "Service2": {
        "type": "L3",
        "name": "Service2",
        "resources": ["id10,RegionOne","id15,RegionTen","id16,RegionSixTen"]
    },
    "Service3": {
        "type": "L3",
        "name": "Service3",
        "resources": ["id21,RegionOne","id24,RegionFour","id25,RegionFive","id28,RegionTwentyEight"]
    }
}

# Create a handler for our read (GET) people
def read_all():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    return [SERVICES[key] for key in sorted(SERVICES.keys())]


def create(service):
    # Taking information from the API http POST request
    local_region_name = service_utils.get_region_name()
    local_region_url = service_utils.get_local_keystone()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    #service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k,v in ((item.split(',')) for item in service.get("resources", None)))
    service_resources_list_search = copy.deepcopy(service_resources_list)
    service_remote_auth_endpoints = {}
    service_remote_inter_endpoints = {}
    local_interconnections_ids = []

    service = {
        'id':'',
        'name': service_name,
        'type': service_type,
        'interconnected_resources': service_resources_list,
        'local_interconnections': local_interconnections_ids
        }
    
    for k,v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            break

    # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalog
    catalog_endpoints = service_utils.get_keystone_catalog(local_region_url)
    for obj in catalog_endpoints:
        if obj['name']=='neutron':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name:
                        service_remote_inter_endpoints[region_name]=endpoint['url']
                        service_resources_list_search.pop(region_name)
                        break
        if obj['name']=='keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface']== 'public':
                        service_remote_auth_endpoints[region_name]=endpoint['url']+'/v3'
                        break

    # If a provided Region Name doesn't exist, exit the method
    if bool(service_resources_list_search):
        return "ERROR: Regions " + ("".join(str(key) for key in service_resources_list_search.keys())) + " are not found"

    # Validation for the L3 routing service
    if service_type == 'L3':
        print ("L3 routing service to be done among the resources: " + (" ".join(str(value) for value in service_resources_list.values())))
        subnetworks = {}
        CIDRs = []
        
        # Retrieving information for networks given the region name
        for item,value in service_resources_list.items():
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
                print("Can't connect to neutron %s" %service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %service_remote_inter_endpoints[item])

        # Retrieving the subnetwork information given the region name
        for item,value in subnetworks.items():
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
                print("Can't connect to neutron %s" %service_remote_inter_endpoints[item])
            except neutronclient_exc.Unauthorized:
                print("Connection refused to neutron %s" %service_remote_inter_endpoints[item])
        
        # Doing the IP range validation to avoid overlapping problems
        for a,b in itertools.combinations(CIDRs,2):
            if a.overlaps(b):
                return "ERROR: networks " + " ".join(str(a)) + " ".join(str(b)) + " overlap"

        # calling the interconnection service plugin to create the necessary objects
        id_temp = 1
        for k,v in service_resources_list.items():
            
            if local_region_name != k:
                neutron_client = service_utils.get_neutron_client(
                    local_region_url,
                    local_region_name
                )
                interconnection_data = {'interconnection':{
                    'name':service_name+str(id_temp),
                    'remote_keystone':service_remote_auth_endpoints[k],
                    'remote_region':k,
                    'local_resource_id':local_resource,
                    'type':SERVICE_TYPE[service_type],
                    'remote_resource_id':v,

                }}
                id_temp=id_temp+1
                try:
                    inter_temp = (
                        neutron_client.create_interconnection(interconnection_data)
                    )
                    #print(inter_temp)
                    local_interconnections_ids.append(inter_temp['interconnection']['id'])
                    

                except neutronclient_exc.ConnectionFailed:
                    print("Can't connect to neutron %s" %service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    print("Connection refused to neutron %s" %service_remote_inter_endpoints[item])

        service['local_interconnections']=local_interconnections_ids

        return make_response(json.dumps(service),201)

def check_existing_service(resource_list):
    print("ja")