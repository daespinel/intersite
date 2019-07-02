import utils as service_utils

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
    local_region = service_utils.get_region_name()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k,v in ((item.split(',')) for item in service_resources))
    service_remote_auth_endpoints
    
    for k,v in service_resources_list.items():
        if v == local_region:
            local_resource = k
            print(local_resource)
            break

    neutron_client = service_utils.get_neutron_client(
            interconnection_obj.remote_keystone,
            interconnection_obj.remote_region
        )


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
