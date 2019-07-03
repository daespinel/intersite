import configparser

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient

config = configparser.ConfigParser()
config.read('services.config')

def get_local_keystone():
    return config['DEFAULT']['auth_url']

def get_region_name():
    return config['DEFAULT']['region_name']

def get_neutron_client(keystone_endpoint, region):
    # Use keystone session because Neutron is not yet fully integrated with
    # Keystone v3 API
    sess = get_auth_object(keystone_endpoint)
    return neutronclient.Client(
        session=sess,
        region_name=region
    )

def get_keystone_client(keystone_endpoint, region):
    sess = get_auth_object(keystone_endpoint)
    return keystoneclient.Client(
        session=sess,
        region_name=region
    )

def get_auth_object(keystone_endpoint):
    return v3.Password(
        username=config['DEFAULT']['username'],
        password=config['DEFAULT']['password'],
        project_name=config['DEFAULT']['project'],
        auth_url=keystone_endpoint,
        user_domain_id="default",
        project_domain_id="default",
        include_catalog=True,
        reauthenticate=True
    )

def get_session_object(auth_param):    
    return session.Session(auth=auth_param)

def get_keystone_catalog(keystone_endpoint):
    auth = get_auth_object(keystone_endpoint)
    sess = get_session_object(auth)
    #Auth process
    auth.get_access(sess)
    auth_ref = auth.auth_ref
    return auth_ref.service_catalog.catalog