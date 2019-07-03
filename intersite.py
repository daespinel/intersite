import utils as service_utils
import copy
# Data to serve with our API
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
def read():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    return [SERVICES[key] for key in sorted(SERVICES.keys())]


def create(service):
    local_region_name = service_utils.get_region_name()
    local_region_url = service_utils.get_local_keystone()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k,v in ((item.split(',')) for item in service_resources))
    service_resources_list_search = copy.deepcopy(service_resources_list)
    service_remote_auth_endpoints = {}
    service_remote_inter_endpoints = {}
    
    for k,v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            print(local_resource)
            break

    #keystone_client = service_utils.get_keystone_client(
    #        local_region_url,
    #        local_region_name
    #    )

    #remote_keystone_endpoints = keystone_client.endpoints.list()
    #for obj in remote_keystone_endpoints:
    #    print("this is a new object")
    #    print(obj)
    
    catalog_endpoints = service_utils.get_keystone_catalog(local_region_url)
    for obj in catalog_endpoints:
        if obj['name']=='neutron':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name:
                        service_remote_inter_endpoints[region_name]=endpoint['url']
                        service_resources_list_search.pop(region_name)
                        print("Neutron_endpoints %s %s" %(region_name, service_remote_inter_endpoints[region_name]))
                        break
        if obj['name']=='keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface']== 'public':
                        service_remote_auth_endpoints[region_name]=endpoint['url']+'/v3'
                        print("keystone_endpoints %s %s" %(region_name, service_remote_auth_endpoints[region_name]))
                        break

    if bool(service_resources_list_search):
        return "ERROR: Regions " + ("".join(str(key) for key in service_resources_list_search.keys())) + " are not found"

    if service_type == 'L3':
        print ("L3 routing service to be done among the resources: " + (" ".join(str(value) for value in service_resources_list.values())))

    neutron_client = service_utils.get_neutron_client(
            local_region_url,
            local_region_name
        )

    for item,value in service_resources_list.items():
        print(value, item)

        #remote_interconnection_data = copy.deepcopy(interconnection_data)
        #remote_interconnection_data['remote_resource_id'] = interconnection_data['local_resource_id']
        #remote_interconnection_data['local_resource_id'] = interconnection_data['remote_resource_id']
        #remote_interconnection_data['name'] = interconnection_data['name'] + '_symmetric'
        #remote_interconnection_data['remote_region'] = inter_utils.get_local_region_name()
        #remote_interconnection_data['remote_keystone'] = inter_utils.get_local_keystone() + '/v3'
        #LOG.debug('this is the local  interconnection object %s', interconnection_data)
        #LOG.debug('this is the remote interconnection object %s', remote_interconnection_data)

        #neutron_client = inter_utils.get_neutron_client(
        #    interconnection_obj.remote_keystone,
        #    interconnection_obj.remote_region
        #)

        #remote_interconnection_obj = {'interconnection': remote_interconnection_data}

        #try:
        #    remote_interconnection = (
        #        neutron_client.create_interconnection(
        #            remote_interconnection_obj)
        #    )
        #except neutronclient_exc.ConnectionFailed:
        #    LOG.error("Can't connect to remote neutron")
        #except neutronclient_exc.Unauthorized:
        #    LOG.error("Connection refused to remote neutron")
