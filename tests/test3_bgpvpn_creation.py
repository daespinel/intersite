#!/usr/bin/env python3
import sys
import getopt
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneauth1.adapter import Adapter
from keystoneclient.v3 import client as keystoneclient
import swagger_client
from swagger_client.configuration import Configuration
from swagger_client.rest import ApiException
import time
from random import seed
from random import randint
import random
import datetime
import threading
import concurrent.futures
import sys


def main(argv):
    #FIRST_REGION_NAME = "RegionOne"
    #KEYSTONE_ENDPOINT = "http://192.168.57.6/identity/v3"
    FIRST_REGION_NAME = "RegionTwo"
    KEYSTONE_ENDPOINT = "http://192.168.57.9/identity/v3"

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

    local_net_adap = Adapter(
            auth=auth,
            session=sess,
            service_type='network',
            interface='public',
            region_name=FIRST_REGION_NAME)

    catalog_endpoints = auth_ref.service_catalog.catalog
    #print("Service catalog: %s" % catalog_endpoints)

    regions_list_neu = []
    regions_list_key = []
    regions_list = []

    for obj in catalog_endpoints:

        if obj['name'] == 'neutron':
            for endpoint in obj['endpoints']:
                # print(endpoint)
                new_endpoint_obj = {
                    'region_name': endpoint["region"], 'neutron_url': endpoint["url"]}
                regions_list_neu.append(new_endpoint_obj)

        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                if endpoint['interface'] == 'public':
                    new_endpoint_obj = {
                        'region_name': endpoint["region"], 'keystone_url': endpoint["url"]}
                    regions_list_key.append(new_endpoint_obj)
                    # print(endpoint)

    print(regions_list_neu)
    print(regions_list_key)

    for i in range(len(regions_list_neu)):
        neutron_endpoint = regions_list_neu[i]
        print(neutron_endpoint)
        for j in range(len(regions_list_key)):
            keystone_endpoint = regions_list_key[j]
            print(keystone_endpoint)
            if neutron_endpoint['region_name'] == keystone_endpoint['region_name']:
                new_end = {'region_name': neutron_endpoint['region_name'],
                           'keystone_url': keystone_endpoint['keystone_url'], 'neutron_url': neutron_endpoint['neutron_url']}
                regions_list.append(new_end)

    print(regions_list)

    cidrs_region_network_information = {'10.0.0.0/24': [], '20.0.0.0/24': [], '30.0.0.0/24': [], '40.0.0.0/24': [], '50.0.0.0/24': [], '60.0.0.0/24': [], '70.0.0.0/24': [], '80.0.0.0/24': [
    ], '90.0.0.0/24': [], '100.0.0.0/24': [], '110.0.0.0/24': [], '120.0.0.0/24': [], '130.0.0.0/24': [], '140.0.0.0/24': [], '150.0.0.0/24': [], '160.0.0.0/24': [], '170.0.0.0/24': [], '180.0.0.0/24': []}


    # For every region find the networks created manually
    for i in range(len(regions_list)):
        region_name, region_auth_endpoint, region_neutron_endpoint = regions_list[i]['region_name'], regions_list[i]['keystone_url']+'/v3', regions_list[i]['neutron_url']
        auth = get_auth_object(region_auth_endpoint)
        sess = get_session_object(auth)
        print('Getting information from region ' + str(region_name))
        # Authenticate
        auth.get_access(sess)
        auth_ref = auth.auth_ref
            
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
            subnet_cidr = per_net_subnet['subnet']['cidr']
            #print(subnet_cidr)
            test_object = {
                'region_name': region_name,
                'net_uuid': net_ID,
                'keystone': region_auth_endpoint

            }
            cidrs_region_network_information[subnet_cidr].append(test_object)

    print('starting tests')
    print(cidrs_region_network_information)

    def parallel_inters_creation_request(uuid, resources):
    
        starting_time = time.time()
        local_resource = ''
        remote_region = ''
        remote_uuid = ''
        remote_keystone = ''
        first_obj = resources[0]
        second_obj = resources[1]

        if first_obj['region_name'] == FIRST_REGION_NAME:
            local_resource = first_obj['net_uuid']
            remote_region = second_obj['region_name']
            remote_uuid = second_obj['net_uuid']
            remote_keystone = second_obj['keystone']
        else:
            local_resource = second_obj['net_uuid']
            remote_region = first_obj['region_name']
            remote_uuid = first_obj['net_uuid']
            remote_keystone = first_obj['keystone']

        print('Starting thread at time: ' + str(starting_time))
        interconnection_data = {'interconnection': {
            'name': 'test',
            'remote_keystone': remote_keystone,
            'remote_region': remote_region,
            'local_resource_id': local_resource,
            'type': 'network_l2',
            'remote_resource_id': remote_uuid,
        }}
        print(interconnection_data)

        try:
            inter_temp = local_net_adap.post(
                url='/v2.0/inter/interconnections/', json=interconnection_data)
        except ClientException as e:
            print(
                "Exception when contacting the network adapter: " + e.message)


    workers = len(cidrs_region_network_information)
    start_interconnection_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for uuid, resources in cidrs_region_network_information.items():
            executor.submit(parallel_inters_creation_request, uuid, resources)
    end_interconnection_time = time.time()



if __name__ == "__main__":
   main(sys.argv[1:])