#!/usr/bin/env python3
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneauth1.adapter import Adapter
from keystoneclient.v3 import client as keystoneclient

FIRST_REGION_NAME = "RegionOne"
#KEYSTONE_ENDPOINT = "http://{{keystone_ip_node}}/identity/v3"
KEYSTONE_ENDPOINT = "http://192.168.57.6/identity/v3"


def get_session_object(auth_param):
    return session.Session(auth=auth_param)


def get_auth_object(keystone_endpoint):
    return v3.Password(
        username="admin",
        password="secret",
        project_name="demo",
        auth_url=keystone_endpoint,
        user_domain_id="default",
        project_domain_id="default",
        include_catalog=True,
        # Allow fetching a new token if the current one is going to expire
        reauthenticate=True
    )


auth = get_auth_object(KEYSTONE_ENDPOINT)
sess = get_session_object(auth)

# Authenticate
auth.get_access(sess)
auth_ref = auth.auth_ref
#print("Auth token: %s" %auth_ref.auth_token)

catalog_endpoints = auth_ref.service_catalog.catalog
#print("Service catalog: %s" % catalog_endpoints)

regions_list = {}

for obj in catalog_endpoints:
    if obj['name'] == 'neutron':
        for endpoint in obj['endpoints']:
            regions_list[endpoint["region"]] = endpoint["url"]

#print(regions_list)

cidrs_region_network_information = {'10.0.1.0/24': {}, '10.0.2.0/24': {}, '10.0.3.0/24': {}, '10.0.4.0/24': {
}, '10.0.5.0/24': {}, '10.0.6.0/24': {}, '10.0.7.0/24': {}, '10.0.8.0/24': {}, '10.0.9.0/24': {}, '20.0.0.0/24':{}}

# For every region find the networks created with heat
for region_name, region_endpoint in regions_list.items():
    net_adap = Adapter(
        auth=auth,
        session=sess,
        service_type='network',
        interface='public',
        region_name=region_name)

    per_region_net_list = net_adap.get('/v2.0/networks').json()
    region_network = per_region_net_list['networks']
    
    # For every network find the cidr of the subnetwork it has
    for index in range(len(region_network)):   
        net_ID = region_network[index]['id']
        subnet_ID = region_network[index]['subnets'][0]

        per_net_subnet = net_adap.get('/v2.0/subnets/'+subnet_ID).json()
        print(per_net_subnet)