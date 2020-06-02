from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from common import utils as service_utils

local_region_name = service_utils.get_region_name()
local_region_url = service_utils.get_local_keystone()
#local_region_name = "RegionOne"
#local_region_url = "http://192.168.57.6/identity/v3"

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


key_client = get_keystone_client(
    local_region_url, local_region_name, "admin", "secret", "demo")
services_list = key_client.services.list()

print(services_list)

for i in range(len(services_list)):
    print(services_list[i])
    if services_list[i].to_dict()['name'] == 'keystone':
        keystone_service_id = services_list[i].to_dict()['id']
    if services_list[i].to_dict()['name'] == 'neutron':
        neutron_service_id = services_list[i].to_dict()['id']

print('keystone service id' + keystone_service_id)
print('neutron service id' + neutron_service_id)

new_endpoint_object = {
    'service': '',
    'url': '',
    'interface': 'public',
    'region': ''
}


with open("/opt/stack/os_list.txt") as file:
#with open("os_list.txt") as file_os:
    region_name_list = []
    line = file_os.readline()
    while line:
        region_name, region_ip = line.split(":", 2)
        if region_name != local_region_name:
            try:
                key_client.endpoints.create(
                keystone_service_id, 'http://' + region_ip + '/identity/v3', 'public', region_name)
            except:
                print("Can not create the endpoint")

            try:
                key_client.endpoints.create(
                neutron_service_id, 'http://' + region_ip + ':9696', 'public', region_name)
            except:
                print("Can not create the endpoint")
        
        line = file_os.readline()




