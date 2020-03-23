#!/usr/bin/python3

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient

FIRST_REGION_NAME = "RegionOne"
#KEYSTONE_ENDPOINT = "http://{{keystone_ip_node}}/identity/v3"
KEYSTONE_ENDPOINT = "http://192.168.57.6/identity/v3"


def get_session_object(auth_param):
    return session.Session(auth=auth_param)


def get_keystone_catalog(keystone_endpoint, username, password, project):
    auth = get_auth_object(keystone_endpoint, username, password, project)
    sess = get_session_object(auth)
    # Auth process
    auth.get_access(sess)
    auth_ref = auth.auth_ref
    return auth_ref.service_catalog.catalog


def get_keystone_client(keystone_endpoint, region, username, password, project):
    sess = get_session_object(get_auth_object(
        keystone_endpoint, username, password, project))
    return keystoneclient.Client(
        session=sess,
        region_name=region
    )


def get_auth_object(keystone_endpoint, username, password, project):
    return v3.Password(
        username=username,
        password=password,
        project_name=project,
        auth_url=keystone_endpoint,
        user_domain_id="default",
        project_domain_id="default",
        include_catalog=True,
        reauthenticate=True
    )


region_name_list = []
catalog_endpoints = get_keystone_catalog(
    KEYSTONE_ENDPOINT, "admin", "secret", "demo")

for obj in catalog_endpoints:
    if obj['name'] == 'neutron':
        for endpoint in obj['endpoints']:
            region_name_list.append(endpoint['region'])

key_client = get_keystone_client(
    KEYSTONE_ENDPOINT, "RegionOne", "admin", "secret", "demo")
services_list = key_client.services.list()


for i in range(len(services_list)):
    if services_list[i].to_dict()['name'] == 'keystone':
        service_id = services_list[i].to_dict()['id']
        break

new_endpoint_object = {
    'service': service_id,
    'url': KEYSTONE_ENDPOINT[0:-3],
    'interface': 'public',
    'region': ''
}

for region in region_name_list:
    new_endpoint_object['region'] = region

    try:
        key_client.endpoints.create(
            new_endpoint_object['service'], new_endpoint_object['url'], new_endpoint_object['interface'], new_endpoint_object['region'])

    except:
        print("Can not create the endpoint")

