#!/usr/bin/env python3
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneauth1.adapter import Adapter
from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from neutronclient.common import exceptions as neutronclient_exc

FIRST_REGION_NAME = "RegionOne"
#KEYSTONE_ENDPOINT = "http://{{keystone_ip_node}}/identity/v3"
KEYSTONE_ENDPOINT = "http://192.168.57.6/identity/v3"


def get_session_object(auth_param):
    return session.Session(auth=auth_param)


def get_keystone_catalog(keystone_endpoint):
    auth = get_auth_object(keystone_endpoint)
    sess = get_session_object(auth)
    # Auth process
    auth.get_access(sess)
    auth_ref = auth.auth_ref
    return auth_ref.service_catalog.catalog


def get_keystone_client(keystone_endpoint, region):
    sess = get_session_object(get_auth_object(
        keystone_endpoint, username, password, project))
    return keystoneclient.Client(
        session=sess,
        region_name=region
    )


def get_auth_object(keystone_endpoint):
    return v3.Password(
        username="admin",
        password="secret",
        project_name="demo",
        auth_url=keystone_endpoint,
        user_domain_id="default",
        project_domain_id="default",
        include_catalog=True,
        reauthenticate=True
    )

def get_neutron_client(keystone_endpoint, region):
    # Use keystone session because Neutron is not yet fully integrated with
    # Keystone v3 API
    sess = get_session_object(get_auth_object(keystone_endpoint))
    return neutronclient.Client(
        session=sess,
        region_name=region
    )


regions_list = {}
catalog_endpoints = get_keystone_catalog(
    KEYSTONE_ENDPOINT)

for obj in catalog_endpoints:
    if obj['name'] == 'neutron':
        for endpoint in obj['endpoints']:
            print(endpoint["url"])
            regions_list[endpoint["region"]] = endpoint["url"]

print(regions_list)

ks_adap = Adapter(
    auth=auth,
    session=sess,
    service_type='identity',
    interface='admin',
    region_name=OS['name'])
    
for region_name,region_endpoint in regions_list.items():
    #neutron_client = get_neutron_client(
    #    KEYSTONE_ENDPOINT, region_name
    #)
    
    try:
        network_temp_list = (
            neutron_client.list_networks()
        )

    except neutronclient_exc.ConnectionFailed:
        app_log.info("Can't connect to neutron %s" %
                     service_remote_inter_endpoints[item])
    except neutronclient_exc.Unauthorized:
        app_log.info("Connection refused to neutron %s" %
                     service_remote_inter_endpoints[item])
