from flask import make_response, abort
from keystoneauth1.adapter import Adapter
from random import seed
from random import randint
from service import Service, ServiceSchema, Resource, Interconnexion, Parameter, L2Master, L2AllocationPool, ParamsSchema, ResourcesSchema, InterconnectionsSchema, L2MasterSchema, L2AllocationPoolSchema
from config import db
import common.utils as service_utils
import copy
import math
import json
import ipaddress
import itertools
import string
import random
import time
import requests
import logging
import ast
from flask.logging import default_handler
import threading
import concurrent.futures
from threading import Lock


app_log = logging.getLogger()
# Data to serve with our API
SERVICE_TYPE = {'L2': 'network_l2', 'L3': 'network_l3'}
local_region_name = service_utils.get_region_name()
local_region_url = service_utils.get_local_keystone()
# /intersite-vertical/
# Create a handler for our read (GET) services


def readRegionName():
    var_temp = service_utils.get_region_name()
    # app_log.info(var_temp)
    return var_temp


def verticalReadAllService():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    services = Service.query.order_by(Service.service_global).all()

    # Serialize the data for the response
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    app_log.info('The data from service schema: ' + str(data))
    return data

# Create a handler for our read (GET) one service by ID
# Possibility to add more information as ids of remote interconnection resources


def verticalReadOneService(global_id):
    service = Service.query.filter(Service.service_global == global_id).outerjoin(
        Resource).outerjoin(Interconnexion).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        data = service_schema.dump(service).data
        return data

    else:
        abort(404, "Service with ID {id} not found".format(id=id))


def verticalCreateService(service):
    # Taking information from the API http POST request
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new service creation request')
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    # service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k, v in (
        (item.split(',')) for item in service.get("resources", None)))
    service_resources_list_search = copy.deepcopy(service_resources_list)
    app_log.info('Resources list for the service')
    app_log.info(service_resources_list)
    service_remote_auth_endpoints = {}
    service_remote_inter_endpoints = {}
    parameter_local_allocation_pool = ''
    parameter_local_cidr = ''
    parameter_local_cidr_temp = []
    lock = Lock()
    parameter_local_ipv = 'v4'
    local_interconnections_ids = []
    random_id = createRandomGlobalId()

    # Check if a service exists with the requested resources
    existing_service, check_service_id = checkExistingService(
        service_resources_list)
    if(existing_service):
        abort(404, "Service with global ID {global_check} already connects the resources".format(
            global_check=check_service_id))

    to_service = {
        'service_name': service_name,
        'service_type': service_type,
        'service_global': random_id
    }

    for k, v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            break

    if(local_resource == ''):
        abort(404, "There is no local resource for the service")

    auth = service_utils.get_auth_object(local_region_url)
    sess = service_utils.get_session_object(auth)

    # Authenticate
    auth.get_access(sess)
    auth_ref = auth.auth_ref

    catalog_endpoints = auth_ref.service_catalog.catalog

    net_adap = Adapter(
        auth=auth,
        session=sess,
        service_type='network',
        interface='public',
        region_name=local_region_name)

    try:
        network_temp_local = net_adap.get('/v2.0/networks/' + local_resource).json()['network']
    except:
        app_log.info("Exception when contacting the network adapter")


    if (network_temp_local == ''):
        abort(404, "There is no local resource for the service")

    # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalogue
    
    app_log.info('Starting: Saving Neutron and Keystone information from catalogue')

    for obj in catalog_endpoints:
        if obj['name'] == 'neutron':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name:
                        service_remote_inter_endpoints[region_name] = endpoint['url']
                        service_resources_list_search.pop(region_name)
                        break
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    app_log.info('Finishing: Saving Neutron and Keystone information from catalogue')

    # If a provided Region Name doesn't exist, exit the method
    if bool(service_resources_list_search):
        abort(404, "ERROR: Regions " + (" ".join(str(key)
                                                 for key in service_resources_list_search.keys())) + " are not found")

    subnetworks = {}
    CIDRs = []

    # Retrieving the subnetwork information given the region name
    def parallel_subnetwork_request(item, value):
        
        global parameter_local_cidr

        net_adap_remote = Adapter(
        auth=auth,
        session=sess,
        service_type='network',
        interface='public',
        region_name=item)

        try:
            subnetworks_temp = net_adap_remote.get('/v2.0/subnets/').json()
        except:
            app_log.info("Exception when contacting the network adapter")

        for subnetwork in subnetworks_temp['subnets']:
            if (item == local_region_name):
                parameter_local_cidr_temp.append(subnetwork['cidr'])
            if(value == subnetwork['network_id']): 
                CIDRs.append(ipaddress.ip_network(subnetwork['cidr']))
                break        

    # Validation for the L3 routing service
    # Use of the parallel request methods
    if service_type == 'L3':

        app_log.info("Starting: L3 routing service to be done among the resources: " +
                    (" ".join(str(value) for value in service_resources_list.values())))
        
        workers1 = len(service_resources_list.keys())
        app_log.info("Starting: Using threads for remote subnetwork request.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers1) as executor:
            for item, value in service_resources_list.items():
                executor.submit(parallel_subnetwork_request, item, value)
        app_log.info('Finishing: Using threads for remote subnetwork request')

        parameter_local_cidr = parameter_local_cidr_temp[0]

        # Doing the IP range validation to avoid overlapping problems
        for a, b in itertools.combinations(CIDRs, 2):
            if a.overlaps(b):
                abort(404, "ERROR: networks " + " " +
                      (str(a)) + " and "+(str(b)) + " overlap")

    # Validation for the Layer 2 network extension
    if service_type == 'L2':

        app_log.info("Starting: L2 extension service to be done among the resources: " +
                     (" ".join(str(value) for value in service_resources_list.values())))

        app_log.info(network_temp_local)
        app_log.info('The local resource uuid: ' + str(network_temp_local['subnets'][0]))

        net_adap_local = Adapter(
        auth=auth,
        session=sess,
        service_type='network',
        interface='public',
        region_name=local_region_name)

        # Defining an empty dict for the subnetwork information
        subnetwork_temp = {}

        try:
            subnetwork_temp = net_adap_local.get('/v2.0/subnets/' + str(network_temp_local['subnets'][0])).json()['subnet']
        except:
            app_log.info("Exception when contacting the network adapter")

        app_log.info('The local subnetwork informations')
        app_log.info(subnetwork_temp)

        # Taking the information of the subnet CIDR
        cidr = subnetwork_temp['cidr']
        parameter_local_cidr = str(cidr)



        # Validating if the networks have the same CIDR
        if not checkEqualElement(CIDRs):
            abort(404, "ERROR: CIDR is not the same for all the resources")

        # test
        # CIDRs = [ipaddr.IPNetwork("20.0.0.0/23"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24"),ipaddr.IPNetwork("20.0.0.0/24")]
        # service_resources_list = [5,4,2,5,6,7,5,5,5,8,5,2,6,5,8,4,5,8]
        
        main_cidr = str(CIDRs[0])
        main_cidr_base = ((str(CIDRs[0])).split("/", 1)[0])
        main_cidr_prefix = ((str(CIDRs[0])).split("/", 1)[1])
        cidr_ranges = []
        # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
        ips_cidr_available = 2**(32-int(main_cidr_prefix))-3
        host_per_site = math.floor(
            ips_cidr_available/len(service_resources_list))
        # TODO change this rather static and simple division method and search a better way to divide the block
        host_per_site = math.floor(host_per_site/2)
        app_log.info("CIDR: " + str(cidr) + ", total available IPs: " + str(ips_cidr_available) +
                     " , Number of sites: " + str(len(service_resources_list)) + " , IPs per site:" + str(host_per_site))
        base_index = 3
        site_index = 1

        app_log.info("Starting: L2 CIDR allocation pool split.")
        while base_index <= ips_cidr_available and site_index <= len(service_resources_list):
            cidr_ranges.append(
                str(cidr[base_index]) + "-" + str(cidr[base_index + host_per_site - 1]))
            base_index = base_index + int(host_per_site)
            site_index = site_index + 1
        cidr_ranges.append(str(cidr[base_index]) + "-" + str(cidr[ips_cidr_available]))
        app_log.info("Finishing: L2 CIDR allocation pool split.")

        parameter_local_allocation_pool = cidr_ranges[0]

        app_log.info('Next ranges will be used:')
        for element in cidr_ranges:
            app_log.info(element)

    def parallel_inters_creation_request(k,v):
        if local_region_name != k:
            
            interconnection_data = {'interconnection': {
                'name': service_name,
                'remote_keystone': service_remote_auth_endpoints[k],
                'remote_region': k,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': v,

            }}

            try:
                inter_temp = net_adap.post(url='/v2.0/inter/interconnections/', json=interconnection_data)
            except:
                app_log.info("Exception when contacting the network adapter")
            
            #app_log.info(inter_temp)
            local_interconnections_ids.append(inter_temp.json()['interconnection']['id'])

    # calling the interconnection service plugin to create the necessary objects
    
    workers3 = len(service_resources_list.keys())
    start_interconnection_time = time.time()
    app_log.info("Starting: Using threads for local interconnection create request.")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
        for k, v in service_resources_list.items():
            executor.submit(parallel_inters_creation_request, k, v)
    end_interconnection_time = time.time()
    app_log.info('Finishing: Using threads for local interconnection create request. Time: %s', (end_interconnection_time - start_interconnection_time))

    app_log.info("Starting: Creating the service schema")
    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    for k, v in service_resources_list.items():
        resource = {
            'resource_region': k,
            'resource_uuid': v
        }
        service_resources_schema = ResourcesSchema()
        new_service_resources = service_resources_schema.load(
            resource, session=db.session).data
        new_service.service_resources.append(new_service_resources)

    # Adding the parameters to the service
    #app_log.info("Adding the parameters to the service")
    parameters = {
        'parameter_allocation_pool': parameter_local_allocation_pool,
        'parameter_local_cidr': parameter_local_cidr,
        'parameter_ipv': parameter_local_ipv,
        'parameter_master' : '',
        'parameter_master_auth' : ''
        # TODO attention to this, because for the L3 service we have not defined if the master will be also used 
        #'parameter_master': local_region_name, 
        #'parameter_master_auth': local_region_url[0:-12]+":7575"
    }
    #app_log.info(parameters)


    service_params_schema = ParamsSchema()
    new_service_params = service_params_schema.load(
        parameters, session=db.session).data

    app_log.info("Finishing: Creating the service schema")

    # Adding the L2 Master object if the service type is L2
    if service_type == 'L2':

        app_log.info("Starting: Adding the service master.")
        new_service_params.parameter_master = local_region_name
        new_service_params.parameter_master_auth = local_region_url[0:-12]+":7575"

        service_l2master_schema = L2MasterSchema()
        new_l2master = {}
        new_l2master_params = service_l2master_schema.load(
            new_l2master, session=db.session).data
        service_l2allocation_pool_schema = L2AllocationPoolSchema()
        cidr_range = 0
        l2allocation_list = {}

        for objet_region in service_resources_list.keys():

            to_add_l2allocation_pool = {
                'l2allocationpool_first_ip': cidr_ranges[cidr_range].split("-", 1)[0],
                'l2allocationpool_last_ip': cidr_ranges[cidr_range].split("-", 1)[1],
                'l2allocationpool_site': objet_region
            }
            

            new_l2allocation_pool_params = service_l2allocation_pool_schema.load(
                to_add_l2allocation_pool, session=db.session).data
            new_l2master_params.l2master_l2allocationpools.append(
                new_l2allocation_pool_params)
            l2allocation_list[objet_region] = cidr_ranges[cidr_range]

            cidr_range = cidr_range + 1

        while cidr_range < len(cidr_ranges):
            
            to_add_l2allocation_pool = {
                'l2allocationpool_first_ip': cidr_ranges[cidr_range].split("-", 1)[0],
                'l2allocationpool_last_ip': cidr_ranges[cidr_range].split("-", 1)[1],
                'l2allocationpool_site': "free"
            }
            
            cidr_range = cidr_range + 1

            new_l2allocation_pool_params = service_l2allocation_pool_schema.load(
                to_add_l2allocation_pool, session=db.session).data
            new_l2master_params.l2master_l2allocationpools.append(
                new_l2allocation_pool_params)

        new_service_params.parameter_l2master.append(new_l2master_params)

        app_log.info("Finishing: Adding the service master.")

    new_service.service_params.append(new_service_params)

    app_log.info("Starting: Adding the interconnections to the service.")
    # Adding the interconnections to the service
    for element in local_interconnections_ids:
        interconnexion = {
            'interconnexion_uuid': element
        }
        service_interconnections_schema = InterconnectionsSchema()
        new_service_interconnections = service_interconnections_schema.load(
            interconnexion, session=db.session).data
        new_service.service_interconnections.append(
            new_service_interconnections)
    app_log.info("Finishing: Adding the interconnections to the service.")

    # Updating the DHCP pool ranges for the local deployment

    app_log.info("Starting: Updating the DHCP pool ranges for the local deployment.")
    if service_type == 'L2':
        allocation_start = cidr_ranges[0].split("-", 1)[0]
        allocation_end = cidr_ranges[0].split("-", 1)[1]

        body = {'subnet': {'allocation_pools': [
                {'start': allocation_start, 'end': allocation_end}]}}

        try:        
            dhcp_change = net_adap.put(url='/v2.0/subnets/'+subnetworks[local_region_name],json=body)
        except:
            app_log.info("Exception when contacting the network adapter")

    app_log.info("Finishing: Updating the DHCP pool ranges for the local deployment.")
 
    # Sending remote inter-site create requests to the distant nodes

    def parallel_horizontal_request(obj, alloc_pool):
        if obj != service_utils.get_region_name():
            remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                '9696/')
            remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
            remote_params = {
                'parameter_allocation_pool': '',
                'parameter_local_cidr': '',
                'parameter_ipv': parameter_local_ipv,
                'parameter_master': '',
                'parameter_master_auth': ''
            }
            # TODO Need to check the cidr_ranges
            if service_type == 'L2':
                remote_params['parameter_allocation_pool'] = alloc_pool
                
                remote_params['parameter_local_cidr'] = parameter_local_cidr
                remote_params['parameter_master'] = local_region_name
                remote_params['parameter_master_auth'] = local_region_url[0:-12]+":7575"

            remote_service = {'name': service_name, 'type': service_type, 'params': [str(remote_params)
                                                                                     ],
                              'global': random_id, 'resources': service.get("resources", None)}
            # send horizontal (service_remote_inter_endpoints[obj])
            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}

            r = requests.post(remote_inter_instance, data=json.dumps(
                remote_service), headers=headers)


    #app_log.info("Preparing to use the following l2")
    #app_log.info(l2allocation_list)

    workers2 = len(service_resources_list.keys())
    app_log.info("Starting: Using threads for horizontal creation request.")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers2) as executor:
        for obj in service_resources_list.keys():
            if service_type == 'L2':    
                executor.submit(parallel_horizontal_request, obj, l2allocation_list[obj])
            if service_type == 'L3':
                executor.submit(parallel_horizontal_request, obj, "")
    app_log.info('Finishing: Using threads for horizontal creation request.')    

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    end_time = time.time()
    app_log.info('Ending time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return service_schema.dump(new_service).data, 201


# Handler to update an existing service

# TODO Need to refactor this, only modify using the master
def verticalUpdateService(global_id, service):

    service_update = Service.query.filter(
        Service.service_global == global_id).one_or_none()

    # Did we find a service?
    if service_update is not None:

        service_schema_temp = ServiceSchema()
        data_from_db = service_schema_temp.dump(service_update).data

        service_to_update_type = data_from_db['service_params'][0]['parameter_master']
        # For the L2 service, check if the module is the master for that service. If it isn't, return abort to inform that it can't execute the request
        if(data_from_db['service_type'] == 'L2'):
            if(service_to_update_type != local_region_name):
                app_log.info('This module is not the master of the service')
                abort(404, "This module is not the master of the service, please redirect the request to: " + service_to_update_type + " module")

        to_service_resources_list = dict((k.strip(), v.strip()) for k, v in (
            (item.split(',')) for item in service.get("resources", None)))
        service_resources_list_user = []
        for key, value in to_service_resources_list.items():
            service_resources_list_user.append(
                {'resource_uuid': value, 'resource_region': key})
        # app_log.info(service_resources_list_user)

        service_resources_list_db = []
        # app_log.info(data_from_db['service_resources'])
        for element in data_from_db['service_resources']:
            service_resources_list_db.append(
                {'resource_uuid': element['resource_uuid'], 'resource_region': element['resource_region']})
        # app_log.info(service_resources_list_db)
        list_resources_remove = copy.deepcopy(service_resources_list_db)
        list_resources_add = []
        service_resources_list = []

        for resource_component in service_resources_list_user:
            contidion_temp = True
            for resource_component_2 in service_resources_list_db:
                if resource_component == resource_component_2:
                    # app_log.info(resource_component)
                    list_resources_remove.remove(resource_component_2)
                    contidion_temp = False
                    break
            if(contidion_temp == True):
                list_resources_add.append(resource_component)

        app_log.info('actual list of resources' +
                     str(service_resources_list_db))
        app_log.info('resources to add' + str(list_resources_add))
        app_log.info('resources to delete' + str(list_resources_remove))
        search_local_resource_delete = False
        search_local_resource_uuid = ''

        if(list_resources_remove == [] and list_resources_add == []):
            abort(404, "No resources are added/deleted")

        for element in service_resources_list_db:
            if(local_region_name in element['resource_region']):
                search_local_resource_uuid = element['resource_uuid']
                break

        # TODO change local_region_name for search_local_resource_uuid
        for element in list_resources_remove:
            if(local_region_name in element['resource_region']):
                search_local_resource_delete = True

        auth = service_utils.get_auth_object(local_region_url)
        sess = service_utils.get_session_object(auth)

        # Authenticate
        auth.get_access(sess)
        auth_ref = auth.auth_ref

        catalog_endpoints = auth_ref.service_catalog.catalog

        net_adap = Adapter(
            auth=auth,
            session=sess,
            service_type='network',
            interface='public',
            region_name=local_region_name)


        # If one of the resource is the local one, we only need to delete the entire service locally
        # For the moment we're going to avoid this with L2 services
        if(search_local_resource_delete):
            if(service_to_update_type=='L3'):
                interconnections_delete = data_from_db['service_interconnections']
                for element in interconnections_delete:

                    inter = element['interconnexion_uuid']

                    try:
                        inter_del = net_adap.delete('/v2.0/inter/interconnections/' + inter)
                    except:
                        app_log.info("Exception when contacting the network adapter")

                    for element in list_resources_remove:
                        if(local_region_name in element['resource_region']):
                            service_resources_list_db.remove(element)
                            list_resources_remove.remove(element)
                            break

                db.session.delete(service_update)
                db.session.commit()

            else:
                app_log.info('The resource belonging to the master node can not be deleted, Please rework the request')
                abort(404,'The resource belonging to the master node can not be deleted, Please rework the request')

        # First delete the interconnections between the local resource and the resources that are going to be deleted
        if (list_resources_remove):
            # Do this if the local resource is not being deleted from the service
            if (search_local_resource_delete != True):
                for remote_resource_to_delete in list_resources_remove:

                    filters = {'local_resource_id': search_local_resource_uuid,
                                'remote_resource_id': remote_resource_to_delete['resource_uuid']}
                    
                    try:
                        inter_del_list = net_adap.get(url='/v2.0/inter/interconnections/', json=filters).json()['interconnections']
                    except:
                        app_log.info("Exception when contacting the network adapter")

                    if inter_del_list:
                        interco_delete = inter_del_list.pop()
                        interconnection_uuid_to_delete = interco_delete['id']

                        try:
                            inter_del = net_adap.delete('/v2.0/inter/interconnections/' + interconnection_uuid_to_delete)
                        except:
                            app_log.info("Exception when contacting the network adapter")

                        interconnection_delete = Interconnexion.query.outerjoin(Service, Interconnexion.service_id == Service.service_id).filter(
                            Interconnexion.interconnexion_uuid == interconnection_uuid_to_delete).filter(Interconnexion.service_id == data_from_db['service_id']).one_or_none()

                        if interconnection_delete:
                            db.session.delete(interconnection_delete)
                            db.session.commit()


                # app_log.info(remote_resource_to_delete['resource_uuid'])
                resource_delete = Resource.query.outerjoin(Service, Resource.service_id == Service.service_id).filter(
                    Service.service_id == data_from_db['service_id']).filter(Resource.resource_uuid == remote_resource_to_delete['resource_uuid']).one_or_none()

                service_resources_list_db.remove(remote_resource_to_delete)

                if resource_delete:
                    db.session.delete(resource_delete)
                    db.session.commit()

        
        service_remote_auth_endpoints = {}
        service_remote_inter_endpoints = {}
        service_resources_list_search = copy.deepcopy(
            list_resources_add)
        service_resources_list_db_search = copy.deepcopy(
            service_resources_list_db)

        for obj in catalog_endpoints:
            if obj['name'] == 'neutron':
                for endpoint in obj['endpoints']:
                    for existing_resource in service_resources_list_db:
                        if endpoint['region'] == existing_resource['resource_region']:
                            service_remote_inter_endpoints[existing_resource['resource_region']
                                                            ] = endpoint['url']
                            service_resources_list_db_search.remove(
                                existing_resource)
                            break
                    for resource_element in list_resources_add:
                        if endpoint['region'] == resource_element['resource_region']:
                            service_remote_inter_endpoints[resource_element['resource_region']
                                                            ] = endpoint['url']
                            service_resources_list_search.remove(
                                resource_element)
                            break
                    for resource_delete in list_resources_remove:
                        if endpoint['region'] == resource_delete['resource_region']:
                            service_remote_inter_endpoints[resource_delete['resource_region']
                                                            ] = endpoint['url']
                            break
            if obj['name'] == 'keystone':
                for endpoint in obj['endpoints']:
                    for existing_resource in service_resources_list_db:
                        if endpoint['region'] == existing_resource['resource_region']:
                            service_remote_auth_endpoints[existing_resource['resource_region']
                                                            ] = endpoint['url']+'/v3'
                            break
                    for resource_element in list_resources_add:
                        if endpoint['region'] == resource_element['resource_region'] and endpoint['interface'] == 'public':
                            service_remote_auth_endpoints[resource_element['resource_region']
                                                            ] = endpoint['url']+'/v3'
                            break
                    for resource_delete in list_resources_remove:
                        if endpoint['region'] == resource_delete['resource_region']:
                            service_remote_auth_endpoints[resource_delete['resource_region']
                                                            ] = endpoint['url'] + '/v3'
                            break

        if bool(service_resources_list_search):
            abort(404, "ERROR: Regions " + (" ".join(str(key['resource_region'])
                                                        for key in service_resources_list_search)) + " are not found")

        if bool(service_resources_list_db_search):
            abort(404, "ERROR: Regions " + (" ".join(str(key['resource_region'])
                                                        for key in service_resources_list_db_search)) + " are not found")

        
        # Do a new list with the actual resources that are going to be used in the following part of the service
        # then, verify the new resources to add to the service and add them
        # Depending on the service type, the validation will be different
        if(list_resources_add):

            new_subnetworks = {}
            new_CIDRs = {}
            # Retrieving information for networks given the region name
            for item in list_resources_add:

                neutron_client = service_utils.get_neutron_client(
                    service_remote_auth_endpoints[item['resource_region']],
                    item['resource_region']
                )

                try:
                    network_temp = (
                        neutron_client.show_network(network=item['resource_uuid']
                                                    )
                    )
                    subnet = network_temp['network']
                    new_subnetworks[item['resource_region']
                                    ] = subnet['subnets'][0]

                except neutronclient_exc.ConnectionFailed:
                    app_log.info("Can't connect to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    app_log.info("Connection refused to neutron %s" %
                                 service_remote_inter_endpoints[item])

                # Retrieving the subnetwork information given the region name
            for item, value in new_subnetworks.items():
                neutron_client = service_utils.get_neutron_client(
                    service_remote_auth_endpoints[item],
                    item
                )
                try:
                    subnetwork_temp = (
                        neutron_client.show_subnet(subnet=value)
                    )

                    subnet = subnetwork_temp['subnet']
                    new_CIDRs[item] = ipaddress.ip_network(subnet['cidr'])
                except neutronclient_exc.ConnectionFailed:
                    app_log.info("Can't connect to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    app_log.info("Connection refused to neutron %s" %
                                 service_remote_inter_endpoints[item])

            # query distant sites composing the service to give their params

            service_resources_list = service_resources_list_db + list_resources_add
            service_resources_list_params = []
            for obj in service_resources_list_db:
                remote_inter_instance = ''
                if obj['resource_region'] != service_utils.get_region_name():
                    remote_inter_instance = service_remote_inter_endpoints[obj['resource_region']].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + \
                        '7575/api/intersite-horizontal/' + global_id
                    # send horizontal to get info (service_remote_inter_endpoints[obj])
                    headers = {'Accept': 'text/html'}
                    r = requests.get(
                        remote_inter_instance, headers=headers)
                    if data_from_db['service_type'] == 'L2':
                        service_resources_list_params.append(
                            {'resource_region': obj['resource_region'], 'param': r.json()[0]['parameter_allocation_pool']})
                    if data_from_db['service_type'] == 'L3':
                        service_resources_list_params.append(
                            {'resource_region': obj['resource_region'], 'param': r.json()[0]['parameter_local_cidr']})

            if(data_from_db['service_type'] == 'L2'):
                if(search_local_resource_delete != True):
                    service_resources_list_params.append(
                        {'resource_region': local_region_name, 'param': data_from_db['service_params'][0]['parameter_allocation_pool']})
                check_cidrs = [key for key in new_CIDRs.values()]
                check_cidrs.append(ipaddress.ip_network(
                    data_from_db['service_params'][0]['parameter_local_cidr']))

                if not checkEqualElement(check_cidrs):
                    abort(
                        404, "ERROR: CIDR is not the same for all the resources")

                # app_log.info(service_remote_auth_endpoints)
                # app_log.info(horizontal_read_parameters(
                #    data_from_db['service_global']))

                cidr = ipaddress.ip_network(
                    data_from_db['service_params'][0]['parameter_local_cidr'])
                main_cidr = str(cidr)
                main_cidr_base = ((str(cidr)).split("/", 1)[0])
                main_cidr_prefix = ((str(cidr)).split("/", 1)[1])
                cidr_ranges = []
                # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
                ips_cidr_available = 2**(32-int(main_cidr_prefix))-3
                host_per_site = math.floor(
                    ips_cidr_available/len(service_resources_list))
                app_log.info("CIDR: " + str(cidr) + ", total available IPs: " + str(ips_cidr_available) +
                             " , Number of sites: " + str(len(service_resources_list)) + " , IPs per site:" + str(host_per_site))
                base_index = 3
                site_index = 1
                while base_index <= ips_cidr_available and site_index <= len(service_resources_list):
                    cidr_ranges.append(
                        str(cidr[base_index])+"-"+str(cidr[base_index+host_per_site-1]))
                    base_index = base_index + int(host_per_site)
                    site_index = site_index + 1

                parameter_local_cidr = main_cidr

                app_log.info('Next ranges will be used:')
                for element in cidr_ranges:
                    app_log.info(element)

                check_cidrs = [key['param']
                               for key in service_resources_list_params]
                reorder_cidrs(service_resources_list_params)

                for element in list_resources_add:
                    service_resources_list_params.append(
                        {'resource_region': element['resource_region'], 'param': ''})

                if(search_local_resource_delete != True):
                    # Search the most suitable range for the local resource
                    for i in range(len(service_resources_list_params)):
                        if(service_resources_list_params[i]['resource_region'] == local_region_name):
                            new_local_param_index = i
                            break

            if(data_from_db['service_type'] == 'L3'):
                if(search_local_resource_delete != True):
                    service_resources_list_params.append(
                        {'resource_region': local_region_name, 'param': data_from_db['resource_params'][0]['parameter_local_cidr']})
                check_cidrs = [key['param']
                               for key in service_resources_list_params]
                for a, b in itertools.combinations(check_cidrs, 2):
                    if a.overlaps(b):
                        abort(404, "ERROR: networks " + " " +
                              (str(a)) + " and "+(str(b)) + " overlap")

            for element in service_resources_list_db:
                if(local_region_name in element['resource_region']):
                    local_resource = element['resource_uuid']
                    break

            # In case the local resource is not being deleted, we create the local resources
            if(search_local_resource_delete != True):
                # Calling the interconnection plugin in both cases
                id_temp = 1
                local_interconnections_ids = []
                for element in list_resources_add:

                    if local_region_name != element['resource_region']:
                        neutron_client = service_utils.get_neutron_client(
                            local_region_url,
                            local_region_name
                        )
                        interconnection_data = {'interconnection': {
                            'name': data_from_db['service_name']+str(id_temp),
                            'remote_keystone': service_remote_auth_endpoints[element['resource_region']],
                            'remote_region': element['resource_region'],
                            'local_resource_id': local_resource,
                            'type': SERVICE_TYPE[data_from_db['service_type']],
                            'remote_resource_id': element['resource_uuid'],

                        }}
                        id_temp = id_temp+1
                        try:
                            inter_temp = (
                                neutron_client.create_interconnection(
                                    interconnection_data)
                            )
                            # app_log.info(inter_temp)
                            local_interconnections_ids.append(
                                inter_temp['interconnection']['id'])

                        except neutronclient_exc.ConnectionFailed:
                            app_log.info("Can't connect to neutron %s" %
                                         service_remote_inter_endpoints[item])
                        except neutronclient_exc.Unauthorized:
                            app_log.info("Connection refused to neutron %s" %
                                         service_remote_inter_endpoints[item])

                for element in list_resources_add:
                    resource = {
                        'resource_region': element['resource_region'],
                        'resource_uuid': element['resource_uuid']
                    }
                    service_resources_schema = ResourcesSchema()
                    new_service_resources = service_resources_schema.load(
                        resource, session=db.session).data
                    service_update.service_resources.append(
                        new_service_resources)

                param_update = Parameter.query.filter(
                    Parameter.service_id == data_from_db['service_id']).one_or_none()
                param_update_schema = ParamsSchema()
                data_from_param = param_update_schema.dump(param_update).data
                param_update.parameter_allocation_pool = cidr_ranges[new_local_param_index]

                # Adding the interconnections to the service
                for element in local_interconnections_ids:
                    interconnexion = {
                        'interconnexion_uuid': element
                    }
                    service_interconnections_schema = InterconnectionsSchema()
                    new_service_interconnections = service_interconnections_schema.load(
                        interconnexion, session=db.session).data
                    service_update.service_interconnections.append(
                        new_service_interconnections)

            db.session.commit()

            # Updating the DHCP pool ranges for the local deployment
            if(search_local_resource_delete != True):
                if data_from_db['service_type'] == 'L2':

                    neutron_client = service_utils.get_neutron_client(
                        local_region_url, local_region_name
                    )

                    try:
                        network_temp = (
                            neutron_client.show_network(network=local_resource
                                                        )
                        )
                        subnet = network_temp['network']
                        local_subnetwork_id = subnet['subnets'][0]

                    except neutronclient_exc.ConnectionFailed:
                        app_log.info("Can't connect to neutron %s" %
                                     service_remote_inter_endpoints[item])
                    except neutronclient_exc.Unauthorized:
                        app_log.info("Connection refused to neutron %s" %
                                     service_remote_inter_endpoints[item])

                    new_local_range = cidr_ranges[new_local_param_index]
                    allocation_start = new_local_range.split("-", 1)[0]
                    allocation_end = new_local_range.split("-", 1)[1]
                    try:
                        body = {'subnet': {'allocation_pools': [
                            {'start': allocation_start, 'end': allocation_end}]}}
                        dhcp_change = (
                            neutron_client.update_subnet(
                                local_subnetwork_id, body=body)
                        )
                        # app_log.info(inter_temp)
                    except neutronclient_exc.ConnectionFailed:
                        app_log.info("Can't connect to neutron %s" %
                                     service_remote_inter_endpoints[item])
                    except neutronclient_exc.Unauthorized:
                        app_log.info("Connection refused to neutron %s" %
                                     service_remote_inter_endpoints[item])

        # Sending remote inter-site create requests to the distant nodes
        print('Here we are sending the horizontal put requests')
        print('Service resource list: ' + str(service_resources_list))
        print('Service resource remove: ' + str(list_resources_remove))
        for index in range(len(service_resources_list)):
            obj = service_resources_list[index]
            if index != new_local_param_index:
                remote_inter_instance = service_remote_inter_endpoints[obj['resource_region']].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal'

                if obj in list_resources_add:
                    if data_from_db['service_type'] == 'L2':
                        remote_service = {'name': data_from_db['service_name'], 'type': data_from_db['service_type'], 'params': [
                            cidr_ranges[index], parameter_local_cidr, data_from_db['service_params'][0]['parameter_ipv']], 'global': global_id, 'resources': service.get("resources", None)}
                        #index_cidr = index_cidr + 1
                    else:
                        remote_service = {'name': data_from_db['service_name'], 'type': data_from_db['service_type'], 'params': [
                            '', '', data_from_db['service_params'][0]['parameter_ipv']], 'global': global_id, 'resources': service_resources_list}
                    # send horizontal (service_remote_inter_endpoints[obj])
                    headers = {'Content-Type': 'application/json',
                                'Accept': 'application/json'}
                    r = requests.post(remote_inter_instance, data=json.dumps(
                        remote_service), headers=headers)

                else:
                    remote_inter_instance = remote_inter_instance + \
                        '/' + str(global_id)
                    if data_from_db['service_type'] == 'L2':
                        remote_service = {'params': [cidr_ranges[index], parameter_local_cidr, data_from_db['service_params'][0]['parameter_ipv']],
                                            'resources': service_resources_list}
                        # index_cidr = index_cidr + 1
                    else:
                        remote_service = {'params': ['', '', ''],
                                            'resources': service_resources_list}
                    # send horizontal (service_remote_inter_endpoints[obj])
                    headers = {'Content-Type': 'application/json',
                                'Accept': 'application/json'}
                    r = requests.put(remote_inter_instance, data=json.dumps(
                        remote_service), headers=headers)
                    # app_log.info(r.json())

        for obj in list_resources_remove:
            remote_inter_instance = service_remote_inter_endpoints[obj['resource_region']].strip(
                    '9696/')
            remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal/' + str(global_id)
            print(obj)

            remote_service = {'name': data_from_db['service_name'], 'type': data_from_db['service_type'], 'params': [
                            '', '', ''], 'global': global_id, 'resources': service.get("resources", None)}

            headers = {'Content-Type': 'application/json',
                                'Accept': 'application/json'}
            r = requests.put(remote_inter_instance, data=json.dumps(
                        remote_service), headers=headers)
            # service_data = service_schema.dump(service_update)

        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        abort(404, "Service not found with global ID: {global_id}")

# Handler to delete a service


def verticalDeleteService(global_id):
    service_remote_inter_endpoints = {}
    service = Service.query.filter(
        Service.service_global == global_id).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        service_data = service_schema.dump(service).data
        resources_list_to_delete = service_data['service_resources']
        # app_log.info(resources_list_to_delete)
        interconnections_delete = service_data['service_interconnections']

        auth = service_utils.get_auth_object(local_region_url)
        sess = service_utils.get_session_object(auth)

        # Authenticate
        auth.get_access(sess)
        auth_ref = auth.auth_ref

        catalog_endpoints = auth_ref.service_catalog.catalog

        net_adap = Adapter(
            auth=auth,
            session=sess,
            service_type='network',
            interface='public',
            region_name=local_region_name)

        for element in interconnections_delete:
            inter = element['interconnexion_uuid']
            
            try:
                inter_del = net_adap.delete(url='/v2.0/inter/interconnections/' + inter)
            except:
                app_log.info("Exception when contacting the network adapter")

        db.session.delete(service)
        db.session.commit()

        for obj in catalog_endpoints:
            if obj['name'] == 'neutron':
                for endpoint in obj['endpoints']:
                    # app_log.info(endpoint)
                    for region_name in resources_list_to_delete:
                        # app_log.info(region_name)
                        if endpoint['region'] == region_name['resource_region']:
                            service_remote_inter_endpoints[region_name['resource_region']
                                                           ] = endpoint['url']
                            break

        # app_log.info(service_remote_inter_endpoints)
        # Sending remote inter-site delete requests to the distant nodes

        def parallel_horizontal_delete_request(obj):
            remote_inter_instance = ''
            if obj['resource_region'] != service_utils.get_region_name():
                remote_inter_instance = service_remote_inter_endpoints[obj['resource_region']].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal/' + global_id
                # send horizontal delete (service_remote_inter_endpoints[obj])
                headers = {'Accept': 'text/html'}
                r = requests.delete(remote_inter_instance, headers=headers)

        workers = len(resources_list_to_delete)
        app_log.info("Using threads for horizontal delete request. Starting.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for obj in resources_list_to_delete:
                executor.submit(parallel_horizontal_delete_request, obj)
        app_log.info('Horizontal threads finished, proceeding')    
            

        return make_response("{id} successfully deleted".format(id=global_id), 200)

    else:
        abort(404, "Service with ID {id} not found".format(id=global_id))


# /intersite-horizontal
# Handler for inter-site service creation request

def horizontalCreateService(service):
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal service creation request')
    local_region_name = service_utils.get_region_name()
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    service_params = ast.literal_eval(service.get("params", None)[0])
    # app_log.info(service_params)
    service_global = service.get("global", None)
    # service_resources = service.get("resources", None)
    service_resources_list = dict((k.strip(), v.strip()) for k, v in (
        (item.split(',')) for item in service.get("resources", None)))
    service_remote_auth_endpoints = {}
    local_interconnections_ids = []

    to_service = {
        'service_name': service_name,
        'service_type': service_type,
        'service_global': service_global
    }

    for k, v in service_resources_list.items():
        if k == local_region_name:
            local_resource = v
            break

    # Saving info for Keystone endpoints to be contacted based on keystone catalog
    auth = service_utils.get_auth_object(local_region_url)
    sess = service_utils.get_session_object(auth)

    # Authenticate
    auth.get_access(sess)
    auth_ref = auth.auth_ref

    catalog_endpoints = auth_ref.service_catalog.catalog

    net_adap = Adapter(
        auth=auth,
        session=sess,
        service_type='network',
        interface='public',
        region_name=local_region_name)

    app_log.info('Starting: Saving Keystone information from catalogue')
    for obj in catalog_endpoints:
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in service_resources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    app_log.info('Finishing: Saving Keystone information from catalogue')

    # calling the interconnection service plugin to create the necessary objects
    def parallel_inters_creation_request(k,v):
        if local_region_name != k:
            
            interconnection_data = {'interconnection': {
                'name': service_name,
                'remote_keystone': service_remote_auth_endpoints[k],
                'remote_region': k,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': v,

            }}

            try:
                inter_temp = net_adap.post(url='/v2.0/inter/interconnections/', json=interconnection_data)
            except:
                app_log.info("Exception when contacting the network adapter")
            
            #app_log.info(inter_temp)
            local_interconnections_ids.append(inter_temp.json()['interconnection']['id'])
            

    # calling the interconnection service plugin to create the necessary objects
    
    workers3 = len(service_resources_list.keys())
    start_interconnection_time = time.time()
    app_log.info("Starting: Using threads for local interconnection create request.")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
        for k, v in service_resources_list.items():
            executor.submit(parallel_inters_creation_request, k, v)
    end_interconnection_time = time.time()
    app_log.info('Finishing: Using threads for local interconnection create request. Time: %s', (end_interconnection_time - start_interconnection_time))
    

    app_log.info("Starting: Creating the service schema")
    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    for k, v in service_resources_list.items():
        resource = {
            'resource_region': k,
            'resource_uuid': v
        }
        service_resources_schema = ResourcesSchema()
        new_service_resources = service_resources_schema.load(
            resource, session=db.session).data
        new_service.service_resources.append(new_service_resources)

    # Adding the interconnections to the service
    for element in local_interconnections_ids:
        interconnexion = {
            'interconnexion_uuid': element
        }
        service_interconnections_schema = InterconnectionsSchema()
        new_service_interconnections = service_interconnections_schema.load(
            interconnexion, session=db.session).data
        new_service.service_interconnections.append(
            new_service_interconnections)

    # Adding the parameters to the service

    if(service_type == 'L3'):
        

        network_temp = net_adap.get('/v2.0/networks/' + local_resource).json()['network']
        subnet_id = network_temp['subnets'][0]

        subnetwork_temp = net_adap.get('/v2.0/subnets/' + subnet_id).json()
        subnet = subnetwork_temp['subnet']
        service_params['parameter_local_cidr'] = subnet['cidr']


    service_params_schema = ParamsSchema()
    new_service_params = service_params_schema.load(
        service_params, session=db.session).data
    new_service.service_params.append(new_service_params)

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    app_log.info("Finishing: Creating the service schema")

    # If the service is from L2 type, do the local DHCP change
    
    if service_type == 'L2':
        app_log.info("Starting: Updating the DHCP pool ranges for the local deployment.")
        body = {'subnet': {'allocation_pools': [{'start': service_params['parameter_allocation_pool'].split(
                "-", 1)[0], 'end': service_params['parameter_allocation_pool'].split("-", 1)[1]}]}}

        network_temp = net_adap.get('/v2.0/networks/' + local_resource).json()['network']
        subnet_id = network_temp['subnets'][0]
            
        app_log.info(str(subnet_id))

        dhcp_change = net_adap.put(url='/v2.0/subnets/'+subnet_id,json=body)
        app_log.info("Finishing: Updating the DHCP pool ranges for the local deployment.")

    end_time = time.time()
    app_log.info('Ending time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return service_schema.dump(new_service).data, 201

# Handler to update a service horizontal


def horizontalUpdateService(global_id, service):
    service_update = Service.query.filter(
        Service.service_global == global_id).one_or_none()

    # Did we find a service?
    if service_update is not None:
        service_schema_temp = ServiceSchema()
        data_from_db = service_schema_temp.dump(service_update).data

        to_service_resources_list = dict((k.strip(), v.strip()) for k, v in (
            (item.split(',')) for item in service.get("resources", None)))
        service_resources_list_user = []

        new_params = service.get("params", None)
        app_log.info(str(new_params))

        for key, value in to_service_resources_list.items():
            service_resources_list_user.append(
                {'resource_uuid': value, 'resource_region': key})

        service_resources_list_db = []
        for element in data_from_db['service_resources']:
            service_resources_list_db.append(
                {'resource_uuid': element['resource_uuid'], 'resource_region': element['resource_region']})

        list_resources_remove = copy.deepcopy(service_resources_list_db)
        list_resources_add = []

        for resource_component in service_resources_list_user:
            contidion_temp = True
            for resource_component_2 in service_resources_list_db:
                if resource_component == resource_component_2:
                    # app_log.info(resource_component)
                    list_resources_remove.remove(resource_component_2)
                    contidion_temp = False
                    break
            if(contidion_temp == True):
                list_resources_add.append(resource_component)

        app_log.info('actual list of resources',
                     str(service_resources_list_db))
        app_log.info('resources to add', str(list_resources_add))
        app_log.info('resources to delete', str(list_resources_remove))
        search_local_resource_delete = False
        search_local_resource_uuid = ''

        if(list_resources_remove == [] and list_resources_add == []):
            abort(404, "No resources are added/deleted")

        for element in service_resources_list_db:
            if(local_region_name in element['resource_region']):
                search_local_resource_uuid = element['resource_uuid']
                break

        # TODO change local_region_name for search_local_resource_uuid
        for element in list_resources_remove:
            if(local_region_name in element['resource_region']):
                search_local_resource_delete = True

        # If one of the resource is the local one, we only need to delete the entire service locally
        if(search_local_resource_delete):
            interconnections_delete = data_from_db['service_interconnections']
            for element in interconnections_delete:
                inter = element['interconnexion_uuid']
                neutron_client = service_utils.get_neutron_client(
                    service_utils.get_local_keystone(),
                    service_utils.get_region_name()
                )
                try:
                    inter_del = (
                        neutron_client.delete_interconnection(inter))

                except neutronclient_exc.ConnectionFailed:
                    app_log.info("Can't connect to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    app_log.info("Connection refused to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.NotFound:
                    app_log.info("Element not found %s" % inter)

                for element in list_resources_remove:
                    if(local_region_name in element['resource_region']):
                        service_resources_list_db.remove(element)
                        list_resources_remove.remove(element)
                        break

            db.session.delete(service_update)
            db.session.commit()

            return make_response("{id} successfully updated".format(id=global_id), 200)

        else:

            if (list_resources_remove):
                # Do this if the local resource is not being deleted from the service
                for remote_resource_to_delete in list_resources_remove:

                    neutron_client = service_utils.get_neutron_client(
                        service_utils.get_local_keystone(),
                        service_utils.get_region_name()
                    )
                    try:

                        filters = {'local_resource_id': search_local_resource_uuid,
                                   'remote_resource_id': remote_resource_to_delete['resource_uuid']}
                        inter_del_list = (
                            neutron_client.list_interconnections(**filters))['interconnections']

                        if inter_del_list:
                            interco_delete = inter_del_list.pop()
                            interconnection_uuid_to_delete = interco_delete['id']

                            inter_del = (neutron_client.delete_interconnection(
                                interconnection_uuid_to_delete))

                            interconnection_delete = Interconnexion.query.outerjoin(Service, Interconnexion.service_id == Service.service_id).filter(
                                Interconnexion.interconnexion_uuid == interconnection_uuid_to_delete).filter(Interconnexion.service_id == data_from_db['service_id']).one_or_none()

                            if interconnection_delete:
                                db.session.delete(interconnection_delete)
                                db.session.commit()

                    except neutronclient_exc.ConnectionFailed:
                        app_log.info("Can't connect to neutron %s" %
                                     service_remote_inter_endpoints[item])
                    except neutronclient_exc.Unauthorized:
                        app_log.info("Connection refused to neutron %s" %
                                     service_remote_inter_endpoints[item])
                    except neutronclient_exc.NotFound:
                        app_log.info("Element not found %s" % inter_del_list)

                    # app_log.info(remote_resource_to_delete['resource_uuid'])
                    resource_delete = Resource.query.outerjoin(Service, Resource.service_id == Service.service_id).filter(
                        Service.service_id == data_from_db['service_id']).filter(Resource.resource_uuid == remote_resource_to_delete['resource_uuid']).one_or_none()

                    service_resources_list_db.remove(remote_resource_to_delete)

                    if resource_delete:
                        db.session.delete(resource_delete)
                        db.session.commit()

            if(list_resources_add):
                service_remote_auth_endpoints = {}
                service_remote_inter_endpoints = {}
                service_resources_list_search = copy.deepcopy(
                    list_resources_add)
                service_resources_list_db_search = copy.deepcopy(
                    service_resources_list_db)
                catalog_endpoints = service_utils.get_keystone_catalog(
                    local_region_url)

                for obj in catalog_endpoints:
                    if obj['name'] == 'neutron':
                        for endpoint in obj['endpoints']:
                            for existing_resource in service_resources_list_db:
                                if endpoint['region'] == existing_resource['resource_region']:
                                    service_remote_inter_endpoints[existing_resource['resource_region']
                                                                   ] = endpoint['url']
                                    service_resources_list_db_search.remove(
                                        existing_resource)
                                    break
                            for resource_element in list_resources_add:
                                if endpoint['region'] == resource_element['resource_region']:
                                    service_remote_inter_endpoints[resource_element['resource_region']
                                                                   ] = endpoint['url']
                                    service_resources_list_search.remove(
                                        resource_element)
                                    break
                    if obj['name'] == 'keystone':
                        for endpoint in obj['endpoints']:
                            for existing_resource in service_resources_list_db:
                                if endpoint['region'] == existing_resource['resource_region']:
                                    service_remote_auth_endpoints[existing_resource['resource_region']
                                                                  ] = endpoint['url']+'/v3'
                                    break
                            for resource_element in list_resources_add:
                                if endpoint['region'] == resource_element['resource_region'] and endpoint['interface'] == 'public':
                                    service_remote_auth_endpoints[resource_element['resource_region']
                                                                  ] = endpoint['url']+'/v3'
                                    break

                if bool(service_resources_list_search):
                    abort(404, "ERROR: Regions " + (" ".join(str(key['resource_region'])
                                                             for key in service_resources_list_search)) + " are not found")

                if bool(service_resources_list_db_search):
                    abort(404, "ERROR: Regions " + (" ".join(str(key['resource_region'])
                                                             for key in service_resources_list_db_search)) + " are not found")

                id_temp = 1
                local_interconnections_ids = []
                for element in list_resources_add:

                    if local_region_name != element['resource_region']:
                        neutron_client = service_utils.get_neutron_client(
                            local_region_url,
                            local_region_name
                        )
                        interconnection_data = {'interconnection': {
                            'name': data_from_db['service_name']+str(id_temp),
                            'remote_keystone': service_remote_auth_endpoints[element['resource_region']],
                            'remote_region': element['resource_region'],
                            'local_resource_id': search_local_resource_uuid,
                            'type': SERVICE_TYPE[data_from_db['service_type']],
                            'remote_resource_id': element['resource_uuid'],

                        }}
                        id_temp = id_temp+1
                        try:
                            inter_temp = (
                                neutron_client.create_interconnection(
                                    interconnection_data)
                            )
                            # app_log.info(inter_temp)
                            local_interconnections_ids.append(
                                inter_temp['interconnection']['id'])

                        except neutronclient_exc.ConnectionFailed:
                            app_log.info("Can't connect to neutron %s" %
                                         service_remote_inter_endpoints[item])
                        except neutronclient_exc.Unauthorized:
                            app_log.info("Connection refused to neutron %s" %
                                         service_remote_inter_endpoints[item])

                for element in list_resources_add:
                    resource = {
                        'resource_region': element['resource_region'],
                        'resource_uuid': element['resource_uuid']
                    }
                    service_resources_schema = ResourcesSchema()
                    new_service_resources = service_resources_schema.load(
                        resource, session=db.session).data
                    service_update.service_resources.append(
                        new_service_resources)

                # Adding the interconnections to the service
                for element in local_interconnections_ids:
                    interconnexion = {
                        'interconnexion_uuid': element
                    }
                    service_interconnections_schema = InterconnectionsSchema()
                    new_service_interconnections = service_interconnections_schema.load(
                        interconnexion, session=db.session).data
                    service_update.service_interconnections.append(
                        new_service_interconnections)

            # Adding the parameter to the service
            if(data_from_db['service_params'][0]['parameter_allocation_pool'] != new_params[1]):
                param_update = Parameter.query.filter(
                    Parameter.service_id == data_from_db['service_id']).one_or_none()
                param_update_schema = ParamsSchema()
                data_from_param = param_update_schema.dump(param_update).data
                param_update.parameter_allocation_pool = new_params[1]

            db.session.commit()

            if data_from_db['service_type'] == 'L2' and new_params[1] != data_from_db['service_params'][0]['parameter_allocation_pool']:

                neutron_client = service_utils.get_neutron_client(
                    local_region_url, local_region_name
                )

                try:
                    network_temp = (
                        neutron_client.show_network(network=search_local_resource_uuid
                                                    )
                    )
                    subnet = network_temp['network']
                    local_subnetwork_id = subnet['subnets'][0]

                except neutronclient_exc.ConnectionFailed:
                    app_log.info("Can't connect to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    app_log.info("Connection refused to neutron %s" %
                                 service_remote_inter_endpoints[item])

                new_local_range = new_params[1]
                allocation_start = new_local_range.split("-", 1)[0]
                allocation_end = new_local_range.split("-", 1)[1]
                try:
                    body = {'subnet': {'allocation_pools': [
                        {'start': allocation_start, 'end': allocation_end}]}}
                    dhcp_change = (
                        neutron_client.update_subnet(
                            local_subnetwork_id, body=body)
                    )
                    # app_log.info(inter_temp)
                except neutronclient_exc.ConnectionFailed:
                    app_log.info("Can't connect to neutron %s" %
                                 service_remote_inter_endpoints[item])
                except neutronclient_exc.Unauthorized:
                    app_log.info("Connection refused to neutron %s" %
                                 service_remote_inter_endpoints[item])

        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        abort(404, "Service with ID {id} not found".format(id=global_id))


# Handler to delete a service horizontal


def horizontalDeleteService(global_id):
    service_remote_inter_endpoints = {}
    service = Service.query.filter(
        Service.service_global == global_id).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        service_data = service_schema.dump(service).data
        resources_list_to_delete = service_data['service_resources']
        # app_log.info(resources_list_to_delete)
        interconnections_delete = service_data['service_interconnections']

        auth = service_utils.get_auth_object(local_region_url)
        sess = service_utils.get_session_object(auth)

        # Authenticate
        auth.get_access(sess)
        auth_ref = auth.auth_ref

        catalog_endpoints = auth_ref.service_catalog.catalog

        net_adap = Adapter(
            auth=auth,
            session=sess,
            service_type='network',
            interface='public',
            region_name=local_region_name)

        for element in interconnections_delete:
            inter = element['interconnexion_uuid']
            
            inter_del = net_adap.delete(url='/v2.0/inter/interconnections/' + inter)

        db.session.delete(service)
        db.session.commit()

        return make_response("{id} successfully deleted".format(id=global_id), 200)

    else:
        abort(404, "Service with ID {id} not found".format(id=global_id))


def horizontalReadParameters(global_id):

    service = Service.query.filter(Service.service_global == global_id).outerjoin(
        Resource).outerjoin(Interconnexion).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        data = service_schema.dump(service).data['service_params']
        return data

    else:
        abort(404, "Service with ID {id} not found".format(id=id))


# Utils


def checkEqualElement(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)


def checkExistingService(resource_list):

    services = Service.query.all()
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    search_list_dict = {}
    for element in data:
        temp_dict = {}
        for next_resource in element['service_resources']:
            temp_dict[next_resource['resource_region']
                      ] = next_resource['resource_uuid']
        search_list_dict[element['service_global']] = temp_dict
    for key, value in search_list_dict.items():
        # app_log.info(key)
        if(value == resource_list):
            return True, key
    return False, ''


def createRandomGlobalId(stringLength=28):
    lettersAndDigits = string.ascii_lowercase[0:5] + string.digits
    result = ''.join(random.choice(lettersAndDigits) for i in range(8))
    result1 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result2 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result3 = ''.join(random.choice(lettersAndDigits) for i in range(12))
    global_random_id = result + '-' + result1 + '-' + result2 + '-'+result3

    return global_random_id

# DEPRECATED Since the recomposition of cidrs allocation pools has been left aside, this is no longer usefull
def reorderCidrs(list_resources):

    size = len(list_resources)
    for i in range(size):
        for j in range(size):
            first_elem = ipaddress.IPv4Address(
                list_resources[i]['param'].split('-')[0])
            second_elem = ipaddress.IPv4Address(
                list_resources[j]['param'].split('-')[0])

            if first_elem < second_elem:
                temp = list_resources[i]
                list_resources[i] = list_resources[j]
                list_resources[j] = temp
