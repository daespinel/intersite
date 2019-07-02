import configparser

from keystoneauth1.identity import v3
from keystoneauth1 import session

from neutronclient.v2_0 import client as neutronclient

config = configparser.ConfigParser()
config.read('services.config')

cfg.CONF.import_group('neutron_interconnection',
                      'neutron_interconnection.services.common.config')


def get_local_keystone():
    return config['auth_url']

def get_neutron_client(keystone_endpoint, region):
    # Use keystone session because Neutron is not yet fully integrated with
    # Keystone v3 API
    auth = v3.Password(
        username=config['username'],
        password=config['password'],
        project_name=config['project'],
        auth_url=keystone_endpoint,
        user_domain_id="default",
        project_domain_id="default"
    )
    sess = session.Session(auth=auth)

    return neutronclient.Client(
        session=sess,
        region_name=region
    )

def get_region_name():
    return config['DEFAULT']['region_name']