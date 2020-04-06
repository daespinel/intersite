from flask import make_response, abort
from keystoneauth1.adapter import Adapter
from keystoneauth1.exceptions import ClientException
from random import seed
from random import randint
from service import Service, ServiceSchema, Resource, Interconnexion, Parameter, LMaster, L2AllocationPool, L3Cidrs, ParamsSchema, ResourcesSchema, InterconnectionsSchema, LMasterSchema, L2AllocationPoolSchema, L3CidrsSchema
from config import db
from sqlalchemy import exc
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
import sys
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
    # Create the list of services from our data
    services = Service.query.order_by(Service.service_global).all()

    # Serialize the data for the response
    service_schema = ServiceSchema(many=True)
    data = service_schema.dump(services).data
    #app_log.info('The data from service schema: ' + str(data))
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
    app_log.info(
        'Starting: Retrieving and checking information provided by the user')
    local_resource = ''
    service_name = service.get("name", None)
    service_type = service.get("type", None)
    # service_resources = service.get("resources", None)
    service_resources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
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

    for region, uuid in service_resources_list.items():
        if region == local_region_name:
            local_resource = uuid
            break

    if(local_resource == ''):
        abort(404, "There is no local resource for the service")

    auth = service_utils.get_auth_object(local_region_url)
    sess = service_utils.get_session_object(auth)

    app_log.info(
        'Finishing: Retrieving and checking information provided by the user')

    # Authenticate
    app_log.info(
        'Starting: Authenticating and looking for local resource')
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
        network_temp_local = net_adap.get(
            '/v2.0/networks/' + local_resource).json()['network']
    except ClientException as e:
        abort(404, "Exception when contacting the network adapter: " + e.message)

    if (network_temp_local == ''):
        abort(404, "There is no local resource for the service")

    app_log.info(
        'Finishing: Authenticating and looking for local resource')

    # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalogue

    app_log.info(
        'Starting: Saving Neutron and Keystone information from catalogue')

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

    # If a provided Region Name doesn't exist, exit the method
    if bool(service_resources_list_search):
        abort(404, "ERROR: Regions " + (" ".join(str(key)
                                                 for key in service_resources_list_search.keys())) + " are not found")

    app_log.info(
        'Finishing: Saving Neutron and Keystone information from catalogue')

    subnetworks = {}
    CIDRs_conditions = []
    CIDRs = []

    # Validation for the L3 routing service
    # Use of the parallel request methods
    if service_type == 'L3':

        # Retrieving the subnetwork information given the region name
        def parallel_subnetwork_request(item, value):
            app_log = logging.getLogger()
            starting_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_time)
            net_adap_remote = Adapter(
                auth=auth,
                session=sess,
                service_type='network',
                interface='public',
                region_name=item)

            try:
                subnetworks_temp = net_adap_remote.get('/v2.0/subnets/').json()
            except ClientException as e:
                app_log.info(
                    "Exception when contacting the network adapter: " + e.message)

            for subnetwork in subnetworks_temp['subnets']:
                if (item == local_region_name):
                    parameter_local_cidr_temp.append(subnetwork['cidr'])
                if(value == subnetwork['network_id']):
                    obj = [item, value, ipaddress.ip_network(
                        subnetwork['cidr'])]
                    CIDRs.append(obj)
                    break

        app_log.info("Starting: L3 routing service to be done among the resources: " +
                     (" ".join(str(value) for value in service_resources_list.values())))

        app_log.info(
            "Starting(L3): Using threads for remote subnetwork request.")
        workers1 = len(service_resources_list.keys())
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers1) as executor:
            for item, value in service_resources_list.items():
                executor.submit(parallel_subnetwork_request, item, value)
        app_log.info(
            'Finishing(L3): Using threads for remote subnetwork request')

        app_log.info("Starting(L3): Doing IP range validation.")
        parameter_local_cidr = parameter_local_cidr_temp[0]
        # Doing the IP range validation to avoid overlapping problems
        for a, b in itertools.combinations([item[2] for item in CIDRs], 2):
            if a.overlaps(b):
                abort(404, "ERROR: networks " + " " +
                      (str(a)) + " and "+(str(b)) + " overlap")

        app_log.info("Finishing(L3): Doing IP range validation.")

    # Validation for the Layer 2 network extension
    # Use of the parallel request methods
    if service_type == 'L2':

        app_log.info('Starting: L2 extension service to be done among the resources: ' +
                     (' ' .join(str(value) for value in service_resources_list.values())))

        app_log.info(
            'Starting(L2): Retrieving the local subnetwork informations.')
        # app_log.info(network_temp_local)
        # app_log.info('The local resource uuid: ' +
        #             str(network_temp_local['subnets'][0]))

        net_adap_local = Adapter(
            auth=auth,
            session=sess,
            service_type='network',
            interface='public',
            region_name=local_region_name)

        # Defining an empty dict for the subnetwork information
        subnetwork_temp = {}

        try:
            subnetwork_temp = net_adap_local.get(
                '/v2.0/subnets/' + str(network_temp_local['subnets'][0])).json()['subnet']
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter: " + e.message)

        #app_log.info('The local subnetwork informations')
        # app_log.info(subnetwork_temp)

        # Taking the information of the subnet CIDR
        cidr = ipaddress.ip_network(subnetwork_temp['cidr'])
        parameter_local_cidr = str(cidr)

        app_log.info(
            'Finishing(L2): Retrieving the local subnetwork informations.')

        # We do the horizontal validation with remote modules
        def parallel_horizontal_validation(obj):
            app_log = logging.getLogger()
            starting_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_time)
            print("fuck" + str(obj))
            if obj != local_region_name:
                remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                remote_service = {
                    'resource_cidr': parameter_local_cidr, 'service_type': service_type, 'global_id': '', 'verification_type': 'CREATE'}
                # send horizontal verification request
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}
                r = requests.get(remote_inter_instance,
                                 params=remote_service, headers=headers)
                CIDRs_conditions.append(r.json()['condition'])

        app_log.info(
            "Starting(L2): Using threads for horizontal verification request.")
        workers2 = len(service_resources_list.keys())
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers2) as executor:
            for obj in service_resources_list.keys():
                executor.submit(parallel_horizontal_validation, obj)
        app_log.info(
            'Finishing(L2): Using threads for horizontal verification request.')

        app_log.info(
            "Starting(L2): Validating if remote modules already posses a service with the cidr.")
        # Validating if the remote modules already possed an inter-site service with the cidr
        if not all(rest == 'True' for rest in CIDRs_conditions):
            abort(404, "ERROR: CIDR is already used in one of the remote sites")
        app_log.info(
            "Finishing(L2): Validating if remote modules already posses a service with the cidr.")

        app_log.info("Starting(L2): L2 CIDR allocation pool split.")
        main_cidr = parameter_local_cidr
        main_cidr_base = (main_cidr.split("/", 1)[0])
        main_cidr_prefix = (main_cidr.split("/", 1)[1])
        app_log.info(main_cidr_prefix)
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

        while base_index <= ips_cidr_available and site_index <= len(service_resources_list):
            app_log.info('the cidr in this case is: ' + str(cidr))
            cidr_ranges.append(
                str(cidr[base_index]) + "-" + str(cidr[base_index + host_per_site - 1]))
            base_index = base_index + int(host_per_site)
            site_index = site_index + 1
        cidr_ranges.append(str(cidr[base_index]) +
                           "-" + str(cidr[ips_cidr_available]))

        parameter_local_allocation_pool = cidr_ranges[0]

        #app_log.info('Next ranges will be used:')
        # for element in cidr_ranges:
        #    app_log.info(element)

        app_log.info("Finishing(L2): L2 CIDR allocation pool split.")

    def parallel_inters_creation_request(region, uuid):
        app_log = logging.getLogger()
        starting_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_time)
        if local_region_name != region:
            interconnection_data = {'interconnection': {
                'name': service_name,
                'remote_keystone': service_remote_auth_endpoints[region],
                'remote_region': region,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': uuid,
            }}

            try:
                inter_temp = net_adap.post(
                    url='/v2.0/inter/interconnections/', json=interconnection_data)
            except ClientException as e:
                app_log.info(
                    "Exception when contacting the network adapter: " + e.message)

            local_interconnections_ids.append([uuid,
                                               inter_temp.json()['interconnection']['id']])

    # Calling the interconnection service plugin to create the necessary objects
    # This action is called here if the service is an L3 service
    if service_type == 'L3':
        app_log.info(
            "Starting(L3): Using threads for local interconnection create request.")
        workers3 = len(service_resources_list.keys())
        start_interconnection_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
            for region, uuid in service_resources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing(L3): Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

    app_log.info("Starting: Creating the service schema")
    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    # Firstly done for the L3 service
    if service_type == 'L3':
        app_log.info(
            "Starting(L3): Adding the resources and interconnections to the service.")
        for region, uuid in service_resources_list.items():
            resource = {
                'resource_region': region,
                'resource_uuid': uuid
            }
            service_resources_schema = ResourcesSchema()
            new_service_resources = service_resources_schema.load(
                resource, session=db.session).data
            new_service.service_resources.append(new_service_resources)

            to_delete_object = ""
            for interco in local_interconnections_ids:
                if interco[0] == uuid:
                    interconnexion = {
                        'interconnexion_uuid': interco[1],
                        'resource': new_service_resources
                    }
                    new_service_interconnections = Interconnexion(
                        interconnexion_uuid=str(interco[1]), resource=new_service_resources)
                    new_service.service_interconnections.append(
                        new_service_interconnections)
                    to_delete_object = interco
                    break
            if to_delete_object != "":
                local_interconnections_ids.remove(to_delete_object)

        app_log.info(
            "Finishing(L3): Adding the resources and interconnections to the service.")

    app_log.info("Starting: Creating the service params schema")
    parameters = {
        'parameter_allocation_pool': parameter_local_allocation_pool,
        'parameter_local_cidr': parameter_local_cidr,
        'parameter_local_resource': local_resource,
        'parameter_ipv': parameter_local_ipv,
        'parameter_master': local_region_name,
        'parameter_master_auth': local_region_url[0:-12]+":7575"
    }

    service_params_schema = ParamsSchema()
    new_service_params = service_params_schema.load(
        parameters, session=db.session).data
    service_lmaster_schema = LMasterSchema()
    new_lmaster = {}
    new_lmaster_params = service_lmaster_schema.load(
        new_lmaster, session=db.session).data
    app_log.info("Finishing: Creating the service params schema")

    if service_type == 'L3':
        app_log.info(
            "Starting(L3): Adding the L3 service master cidrs.")
        service_l3cidrs_schema = L3CidrsSchema()
        for element in CIDRs:
            to_add_l3cidr = {
                'l3cidrs_site': element[0],
                'l3cidrs_cidr': str(element[2])
            }
            new_l3cidrs_params = service_l3cidrs_schema.load(
                to_add_l3cidr, session=db.session).data
            new_lmaster_params.lmaster_l3cidrs.append(
                new_l3cidrs_params)
        app_log.info(
            "Finishing(L3): Adding the L3 service master cidrs.")

    # Adding the LMaster object if the service type is L2
    if service_type == 'L2':
        app_log.info(
            "Starting(L2): Adding the L2 service master allocation pools.")
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
            new_lmaster_params.lmaster_l2allocationpools.append(
                new_l2allocation_pool_params)
            l2allocation_list[objet_region] = cidr_ranges[cidr_range]

            cidr_range = cidr_range + 1
        '''
        DEPRECATED because free slots can be a problem when updating the service
        while cidr_range < len(cidr_ranges):

            to_add_l2allocation_pool = {
                'l2allocationpool_first_ip': cidr_ranges[cidr_range].split("-", 1)[0],
                'l2allocationpool_last_ip': cidr_ranges[cidr_range].split("-", 1)[1],
                'l2allocationpool_site': "free"
            }

            cidr_range = cidr_range + 1

            new_l2allocation_pool_params = service_l2allocation_pool_schema.load(
                to_add_l2allocation_pool, session=db.session).data
            new_lmaster_params.lmaster_l2allocationpools.append(
                new_l2allocation_pool_params)
        '''
        app_log.info(
            "Finishing(L2): Adding the l2 service master allocation pools.")

    new_service_params.parameter_lmaster.append(new_lmaster_params)

    if service_type == 'L2':
        app_log.info(
            "Starting(L2): Updating the DHCP pool ranges for the local deployment.")
        allocation_start = cidr_ranges[0].split("-", 1)[0]
        allocation_end = cidr_ranges[0].split("-", 1)[1]
        body = {'subnet': {'allocation_pools': [
                {'start': allocation_start, 'end': allocation_end}]}}

        try:
            dhcp_change = net_adap.put(
                url='/v2.0/subnets/'+str(network_temp_local['subnets'][0]), json=body)
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter: " + e.message)

        app_log.info(
            "Finishing(L2): Updating the DHCP pool ranges for the local deployment.")

    new_service.service_params.append(new_service_params)
    app_log.info("Finishing: Creating the service schema")
    remote_resources_ids = []

    # Sending remote inter-site create requests to the distant nodes
    def parallel_horizontal_request(obj, alloc_pool):
        app_log = logging.getLogger()
        starting_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_time)
        if obj != service_utils.get_region_name():
            remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                '9696/')
            remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
            remote_params = {
                'parameter_allocation_pool': '',
                'parameter_local_cidr': '',
                'parameter_local_resource': '',
                'parameter_ipv': parameter_local_ipv,
                'parameter_master': local_region_name,
                'parameter_master_auth': local_region_url[0:-12]+":7575"
            }
            if service_type == 'L2':
                remote_params['parameter_allocation_pool'] = alloc_pool
                remote_params['parameter_local_cidr'] = parameter_local_cidr

            remote_service = {'name': service_name, 'type': service_type, 'params': [str(remote_params)
                                                                                     ],
                              'global': random_id, 'resources': service.get("resources", None)}
            # send horizontal (service_remote_inter_endpoints[obj])
            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}

            r = requests.post(remote_inter_instance, data=json.dumps(
                remote_service), headers=headers)

            if service_type == 'L2':
                remote_res = {r.json()['local_region']: r.json()[
                    'local_resource']}
                remote_resources_ids.append(remote_res)

    start_horizontal_time = time.time()
    app_log.info("Starting: Using threads for horizontal creation request.")
    workers2 = len(service_resources_list.keys())
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers2) as executor:
        for obj in service_resources_list.keys():
            if service_type == 'L2':
                executor.submit(parallel_horizontal_request,
                                obj, l2allocation_list[obj])
            if service_type == 'L3':
                executor.submit(parallel_horizontal_request, obj, "")
    end_horizontal_time = time.time()
    app_log.info('Finishing: Using threads for horizontal creation request.. Time: %s',
                 (end_horizontal_time - start_horizontal_time))

    # Because of the different needed workflows, here we continue with the L2 workflow
    if service_type == 'L2':

        app_log.info("Starting(L2): Updating the resources list.")
        # For the L2 service type, update the resources compossing the service
        for element in remote_resources_ids:
            for key in element.keys():
                service_resources_list[key] = element[key]
        app_log.info(service_resources_list)
        app_log.info("Finishing(L2): Updating the resources list.")

        # For the L2 service type, create the interconnections to remote modules and add them to the service schema
        app_log.info(
            "Starting(L2): Using threads for local interconnection create request.")
        workers3 = len(service_resources_list.keys())
        start_interconnection_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
            for region, uuid in service_resources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing(L2): Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

        app_log.info(
            "Starting(L2): Updating the resources and interconnections composing the service.")
        remote_l2_new_sites = []

        # Adding the resources to the service
        for region, uuid in service_resources_list.items():
            resource = {
                'resource_region': region,
                'resource_uuid': uuid
            }
            new_service_resources = Resource(
                resource_region=region, resource_uuid=uuid)
            #service_resources_schema = ResourcesSchema()
            # new_service_resources = service_resources_schema.load(
            #    resource, session=db.session).data
            new_service.service_resources.append(new_service_resources)
            remote_l2_new_sites.append(region + "," + uuid)

            to_delete_object = ""
            for interco in local_interconnections_ids:
                if interco[0] == uuid:
                    new_service_interconnections = Interconnexion(
                        interconnexion_uuid=str(interco[1]), resource=new_service_resources)
                    new_service.service_interconnections.append(
                        new_service_interconnections)
                    to_delete_object = interco
                    break
            if to_delete_object != "":
                local_interconnections_ids.remove(to_delete_object)

        app_log.info(
            "Finishing(L2): Updating the resources and interconnections composing the service.")

        # For the L2 service type, send the horizontal put request in order to provide remotes instances with the resources uuids for interconnections
        def parallel_horizontal_put_request(obj):
            app_log = logging.getLogger()
            starting_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_time)
            if obj != service_utils.get_region_name():
                remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal/' + str(random_id)
                remote_service = {'name': service_name, 'type': service_type, 'params': [
                ], 'global': random_id, 'resources': remote_l2_new_sites, 'post_create_refresh': 'True'}
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}

                r = requests.put(remote_inter_instance, data=json.dumps(
                    remote_service), headers=headers)

        app_log.info(
            "Starting(L2): Using threads for horizontal put request.")
        workers4 = len(service_resources_list.keys())
        start_horizontal_put_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers4) as executor:
            for k_remote in service_resources_list.keys():
                executor.submit(parallel_horizontal_put_request, k_remote)
        end_horizontal_put_time = time.time()
        app_log.info('Finishing(L2): Using threads for horizontal put request. Time: %s',
                     (end_horizontal_put_time - start_horizontal_put_time))

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    end_time = time.time()
    app_log.info('Finishing time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return service_schema.dump(new_service).data, 201


# Handler to update an existing service

# TODO DOING Need to refactor this, only modify using the master
def verticalUpdateService(global_id, service):
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new service update request.')
    app_log.info('Starting: Validating service information.')
    service_update = Service.query.filter(
        Service.service_global == global_id).one_or_none()

    # Did we find a service?
    if service_update is not None:

        service_schema_temp = ServiceSchema()
        data_from_db = service_schema_temp.dump(service_update).data

        service_to_update_master = data_from_db['service_params'][0]['parameter_master']
        # Check if the module is the master for that service. If it isn't, return abort to inform that it can't execute the request
        if(service_to_update_master != local_region_name):
            app_log.info(
                'ALERT: This module is not the master of the service.')
            app_log.info('Finishing: Validating service information.')
            abort(404, "This module is not the master of the service, please redirect the request to: " +
                  service_to_update_master + " module")

        app_log.info('Finishing: Validating service information.')
        app_log.info(
            'Starting: extracting information from the db and the user information.')

        to_service_resources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
            (item.split(',')) for item in service.get("resources", None)))
        service_resources_list_user = []
        for region, uuid in to_service_resources_list.items():
            service_resources_list_user.append(
                {'resource_uuid': uuid, 'resource_region': region})
        # app_log.info(service_resources_list_user)

        service_resources_list_db = []
        for element in data_from_db['service_resources']:
            service_resources_list_db.append(
                {'resource_uuid': element['resource_uuid'], 'resource_region': element['resource_region']})
        # We create two lists, the first one is for the resources that will be deleted, the second one is for the ones that will be added
        list_resources_remove = copy.deepcopy(service_resources_list_db)
        list_resources_add = []
        service_resources_list = []

        for resource_component in service_resources_list_user:
            contidion_temp = True
            for resource_component_2 in service_resources_list_db:
                if resource_component == resource_component_2:
                    list_resources_remove.remove(resource_component_2)
                    contidion_temp = False
                    break
            if(contidion_temp == True):
                list_resources_add.append(resource_component)

        app_log.info(
            'Finishing: extracting information from the db and the user information.')
        app_log.info('INFO: Actual list of resources' +
                     str(service_resources_list_db))
        app_log.info('INFO: Resources to add' + str(list_resources_add))
        app_log.info('INFO: Resources to delete' + str(list_resources_remove))

        # We analyze if the user is really doing a change to the service by adding/removing resources.
        if(list_resources_remove == [] and list_resources_add == []):
            abort(404, "No resources are added/deleted.")

        app_log.info(
            'Starting: Validating if the local resource is in the list.')
        search_local_resource_delete = False
        local_resource = data_from_db['service_params'][0]['parameter_local_resource']

        for element in list_resources_remove:
            if(local_resource in element['resource_uuid']):
                search_local_resource_delete = True

        app_log.info(
            'Finishing: Validating if the local resource is in the list.')
        if search_local_resource_delete:
            abort(404, 'The master local resource can not be deleted.')

        app_log.info('Starting: Contacting keystone and creating net adapter.')
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

        app_log.info(
            'Finishing: Contacting keystone and creating net adapter.')

        # First delete the interconnections between the local resource and the resources that are going to be deleted
        if (list_resources_remove):

            def parallel_inters_delete_request(resource_delete):
                app_log = logging.getLogger()
                starting_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_time)
                interconnection_db_delete = Interconnexion.query.outerjoin(Service, Interconnexion.service_id == Service.service_id).outerjoin(Resource, Resource.service_id == Service.service_id).filter(
                    Resource.resource_uuid == resource_delete['resource_uuid']).filter(Interconnexion.service_id == data_from_db['service_id']).filter(Interconnexion.resource_id == Resource.resource_id).one_or_none()
                if interconnection_db_delete:
                    interconnection_schema_temp = InterconnectionsSchema()
                    data_from_inter = interconnection_schema_temp.dump(
                        interconnection_db_delete).data
                    interconnection_uuid_to_delete = data_from_inter['interconnexion_uuid']
                    # app_log.info(data_from_inter)
                    # We delete the interconnexion with the given uuid
                    try:
                        inter_del = net_adap.delete(
                            '/v2.0/inter/interconnections/' + interconnection_uuid_to_delete)
                    except ClientException as e:
                        app_log.info(
                            "Exception when contacting the network adapter: " + e.message)
                    # Once we do the request to Neutron, we do the query to delete the interconnexion locally
                    db.session.delete(interconnection_db_delete)
                    db.session.commit()
                # The same procedure is applied to the resource to be deleted locally
                resource_to_delete = Resource.query.outerjoin(Service, Resource.service_id == Service.service_id).filter(
                    Service.service_id == data_from_db['service_id']).filter(Resource.resource_uuid == resource_delete['resource_uuid']).one_or_none()
                service_resources_list_db.remove(resource_delete)
                # We do a per service division because in every case we need to do different actions
                if resource_to_delete:
                    if data_from_db['service_type'] == 'L3':
                        app_log.info(
                            'Starting(L3): Deleting the L3 CIDRs of the remote resources.')
                        l3cidrs_to_delete = L3Cidrs.query.outerjoin(LMaster, LMaster.lmaster_id == L3Cidrs.lmaster_id).outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                            Service, Service.service_id == Parameter.service_id).filter(Service.service_id == data_from_db['service_id']).filter(L3Cidrs.l3cidrs_site == resource_delete['resource_region']).one_or_none()
                        if l3cidrs_to_delete:
                            db.session.delete(l3cidrs_to_delete)
                            db.session.commit()
                        app_log.info(
                            'Finishing(L3): Deleting the L3 CIDRs of the remote resources.')
                    if data_from_db['service_type'] == 'L2':
                        app_log.info(
                            'Starting(L2): Deleting the L2 allocation pools of the remote resources.')
                        l2allocation_to_delete = L2AllocationPool.query.outerjoin(LMaster, LMaster.lmaster_id == L2AllocationPool.lmaster_id).outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                            Service, Service.service_id == Parameter.service_id).filter(Service.service_id == data_from_db['service_id']).filter(L2AllocationPool.l2allocationpool_site == resource_delete['resource_region']).one_or_none()
                        db.session.delete(l2allocation_to_delete)
                        db.session.commit()
                        app_log.info(
                            'Finishing(L2): Deleting the L2 allocation pools of the remote resources.')
                    db.session.delete(resource_to_delete)
                    db.session.commit()

            app_log.info(list_resources_remove)
            app_log.info(
                'Starting: Deleting local interconnections and resources.')
            workers3 = len(list_resources_remove)
            start_interconnection_delete_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
                for resource in list_resources_remove:
                    executor.submit(parallel_inters_delete_request, resource)
            end_interconnection_delete_time = time.time()
            app_log.info('Finishing: Deleting local interconnections and resources. Time: %s',
                         (end_interconnection_delete_time - start_interconnection_delete_time))

        app_log.info(
            'Starting: Saving Neutron and Keystone information from catalogue.')

        service_remote_auth_endpoints = {}
        service_remote_inter_endpoints = {}
        service_resources_list_search = copy.deepcopy(
            list_resources_add)
        service_resources_list_db_search = copy.deepcopy(
            service_resources_list_db)

        for obj in catalog_endpoints:
            if obj['name'] == 'neutron':
                for endpoint in obj['endpoints']:
                    # Storing information of Neutrons of actual resource list, resources to add and resources to delete
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
            # TODO the keystone remote auth can be stored locally along in the resource class
            if obj['name'] == 'keystone':
                # Storing information of Keystone of actual resource list, resources to add and resources to delete
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

        app_log.info(
            'Finishing: Saving Neutron and Keystone information from catalogue.')

        # Do a new list with the actual resources that are going to be used in the following part of the service
        # then, verify the new resources to add to the service and add them
        # Depending on the service type, the validation will be different
        if(list_resources_add):
            new_CIDRs = []
            actual_CIDRs = []
            local_interconnections_ids = []
            # Retrieving the subnetwork information given the region name

            def parallel_new_subnetwork_request(item):
                app_log = logging.getLogger()
                starting_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_time)
                global parameter_local_cidr

                net_adap_remote = Adapter(
                    auth=auth,
                    session=sess,
                    service_type='network',
                    interface='public',
                    region_name=item["resource_region"])

                try:
                    subnetworks_temp = net_adap_remote.get(
                        '/v2.0/subnets/').json()
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter: " + e.message)

                for subnetwork in subnetworks_temp['subnets']:
                    if(item["resource_uuid"] == subnetwork['network_id']):
                        obj = [item["resource_region"], item["resource_uuid"],
                               ipaddress.ip_network(subnetwork['cidr'])]
                        new_CIDRs.append(obj)
                        break

            service_resources_list = service_resources_list_db + list_resources_add
            service_resources_list_params = []
            # Validation for the L3 routing service
            # Use of the parallel request methods
            if(data_from_db['service_type'] == 'L3'):
                app_log.info("Starting: L3 routing service update, adding the resources: " +
                             (" ".join(str(value) for value in [element["resource_uuid"] for element in list_resources_add])))

                app_log.info(list_resources_add)
                app_log.info(
                    "Starting(L3): Using threads for remote subnetwork request.")
                workers1 = len(list_resources_add)
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers1) as executor:
                    for item in list_resources_add:
                        executor.submit(parallel_new_subnetwork_request, item)
                app_log.info(
                    'Finishing(L3): Using threads for remote subnetwork request')
                app_log.info(
                    "Starting(L3): Accesing information of actual list of resources.")
                for element in data_from_db['service_params'][0]['parameter_lmaster'][0]['lmaster_l3cidrs']:
                    obj = [element["l3cidrs_site"],
                           ipaddress.ip_network(element['l3cidrs_cidr'])]
                    actual_CIDRs.append(obj)
                app_log.info(
                    "Finishing(L3): Accesing information of actual list of resources.")
                app_log.info(
                    "Starting(L3): Doing IP range validation for L3 service.")
                # Doing the IP range validation to avoid overlapping problems
                check_cidrs = [item[2] for item in new_CIDRs] + \
                    [item[1] for item in actual_CIDRs]
                for a, b in itertools.combinations(check_cidrs, 2):
                    if a.overlaps(b):
                        abort(404, "ERROR: networks " + " " +
                              (str(a)) + " and "+(str(b)) + " overlap")
                app_log.info(
                    "Finishing(L3): Doing IP range validation for L3 service.")

            if(data_from_db['service_type'] == 'L2'):
                # TODO do the L2 service update
                app_log.info('Starting: L2 extension service to be done among the resources: ' +
                             (' ' .join(str(value) for value in service_resources_list.values())))

                app_log.info(
                    'Starting(L2): Retrieving the local subnetwork informations.')
                parameter_local_cidr = data_from_db['service_params'][0]['parameter_local_cidr']
                app_log.info(
                    'Finishing(L2): Retrieving the local subnetwork informations.')

                CIDRs_conditions = []
                # We do the horizontal validation with new remote modules

                def parallel_horizontal_validation(obj):
                    app_log = logging.getLogger()
                    starting_time = time.time()
                    app_log.info('Starting thread at time:  %s', starting_time)

                    remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                    remote_service = {
                        'resource_cidr': parameter_local_cidr, 'service_type': data_from_db['service_type'], 'global_id': '', 'verification_type': 'CREATE'}
                    # send horizontal verification request
                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json'}
                    r = requests.get(remote_inter_instance,
                                     params=remote_service, headers=headers)
                    CIDRs_conditions.append(r.json()['condition'])

                app_log.info(
                    "Starting(L2): Using threads for horizontal verification request with new modules.")
                workers2 = len(service_resources_list.keys())
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers2) as executor:
                    for obj in list_resources_add:
                        executor.submit(parallel_horizontal_validation, obj)
                app_log.info(
                    'Finishing(L2): Using threads for horizontal verification request with new modules.')

                app_log.info(
                    "Starting(L2): Validating if remote modules already posses a service with the cidr.")
                # Validating if the remote modules already possed an inter-site service with the cidr
                if not all(rest == 'True' for rest in CIDRs_conditions):
                    abort(404, "ERROR: CIDR is already used in one of the remote sites")
                app_log.info(
                    "Finishing(L2): Validating if remote modules already posses a service with the cidr.")

                app_log.info("Starting(L2): L2 CIDR allocation pool split.")
                main_cidr = parameter_local_cidr
                main_cidr_base = (main_cidr.split("/", 1)[0])
                main_cidr_prefix = (main_cidr.split("/", 1)[1])
                cidr_ranges = []
                # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
                ips_cidr_total = 2**(32-int(main_cidr_prefix))-3
                ips_cidr_available = copy.deepcopy(ips_cidr_total)
                # TODO change the allocation starting with the analysis of available addresses given that some sites already exist
                already_used_pools = data_from_db['service_params'][0][
                    'parameter_lmaster'][0]['lmaster_l2allocationpools']

                for allocation_pool in already_used_pools:
                    used_ips = allocation_pool["l2allocationpool_last_ip"] - \
                        allocation_pool["l2allocationpool_first_ip"]
                    ips_cidr_available = ips_cidr_available - used_ips
                # If no more addresses are available, we can not proceed
                if ips_cidr_available == 0:
                    abort(404, "ERROR: 0 available IPs are left")
                if ips_cidr_available < len(list_resources_add):
                    abort(
                        404, "ERROR: Less number of IPs than the number of sites to add are available")
                host_per_site = math.floor(
                    ips_cidr_available/len(list_resources_add))

                host_per_site = math.floor(host_per_site/2)
                app_log.info("CIDR: " + str(cidr) + ", available IPs: " + str(ips_cidr_available) +
                             " , new number of sites: " + str(len(list_resources_add)) + " , IPs per site:" + str(host_per_site))
                base_index = 3
                site_index = 1
                abort(404, "For devs pouposes")
                while base_index <= ips_cidr_available and site_index <= len(list_resources_add):
                    app_log.info('the cidr in this case is: ' + str(cidr))
                    cidr_ranges.append(
                        str(cidr[base_index]) + "-" + str(cidr[base_index + host_per_site - 1]))
                    base_index = base_index + int(host_per_site)
                    site_index = site_index + 1
                cidr_ranges.append(str(cidr[base_index]) +
                                   "-" + str(cidr[ips_cidr_available]))

                parameter_local_allocation_pool = cidr_ranges[0]

                #app_log.info('Next ranges will be used:')
                # for element in cidr_ranges:
                #    app_log.info(element)

                app_log.info("Finishing(L2): L2 CIDR allocation pool split.")

            def parallel_inters_creation_request(obj):
                app_log = logging.getLogger()
                starting_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_time)
                if local_region_name != obj["resource_region"]:
                    interconnection_data = {'interconnection': {
                        'name': data_from_db["service_name"],
                        'remote_keystone': service_remote_auth_endpoints[obj["resource_region"]],
                        'remote_region': obj["resource_region"],
                        'local_resource_id': local_resource,
                        'type': SERVICE_TYPE[data_from_db["service_type"]],
                        'remote_resource_id': obj["resource_uuid"],
                    }}

                    try:
                        inter_temp = net_adap.post(
                            url='/v2.0/inter/interconnections/', json=interconnection_data)
                    except ClientException as e:
                        app_log.info(
                            "Exception when contacting the network adapter: " + e.message)

                    local_interconnections_ids.append([obj["resource_uuid"],
                                                       inter_temp.json()['interconnection']['id']])

            # Calling the interconnection service plugin to create the necessary objects
            # This action is called here if the service is an L3 service
            if data_from_db['service_type'] == 'L3':
                app_log.info(
                    "Starting(L3): Using threads for local interconnection create request.")
                workers3 = len(list_resources_add)
                start_interconnection_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
                    for obj in list_resources_add:
                        executor.submit(parallel_inters_creation_request, obj)
                end_interconnection_time = time.time()
                app_log.info('Finishing(L3): Using threads for local interconnection create request. Time: %s',
                             (end_interconnection_time - start_interconnection_time))

            app_log.info("Starting: Updating the service schema")
            # Adding the resources to the service
            # Firstly done for the L3 service
            if data_from_db['service_type'] == 'L3':
                app_log.info(
                    "Starting(L3): Adding the resources and interconnections to the service.")
                for element in list_resources_add:
                    resource = {
                        'resource_region': element["resource_region"],
                        'resource_uuid': element["resource_uuid"]
                    }
                    service_resources_schema = ResourcesSchema()
                    new_service_resources = service_resources_schema.load(
                        resource, session=db.session).data
                    service_update.service_resources.append(
                        new_service_resources)

                    to_delete_object = ""
                    for interco in local_interconnections_ids:
                        if interco[0] == element["resource_region"]:
                            interconnexion = {
                                'interconnexion_uuid': interco[1],
                                'resource': new_service_resources
                            }
                            new_service_interconnections = Interconnexion(
                                interconnexion_uuid=str(interco[1]), resource=new_service_resources)
                            service_update.service_interconnections.append(
                                new_service_interconnections)
                            to_delete_object = interco
                            break
                    if to_delete_object != "":
                        local_interconnections_ids.remove(to_delete_object)
                app_log.info(
                    "Finishing(L3): Adding the resources and interconnections to the service.")
                app_log.info(
                    "Starting(L3): Adding the L3 service master cidrs.")
                service_lmaster = LMaster.query.outerjoin(Parameter, Parameter.parameter_id == LMaster.lmaster_id).outerjoin(
                    Service, Service.service_id == Parameter.service_id).filter(Service.service_id == data_from_db['service_id']).one_or_none()
                service_l3cidrs_schema = L3CidrsSchema()
                for element in new_CIDRs:
                    to_add_l3cidr = {
                        'l3cidrs_site': element[0],
                        'l3cidrs_cidr': str(element[2])
                    }
                    new_l3cidrs_params = service_l3cidrs_schema.load(
                        to_add_l3cidr, session=db.session).data
                    service_lmaster.lmaster_l3cidrs.append(
                        new_l3cidrs_params)
                app_log.info(
                    "Finishing(L3): Adding the L3 service master cidrs.")
            db.session.commit()
            app_log.info("Finishing: Updating the service schema")
            # I'M HERE

        app_log.info(service_resources_list)
        app_log.info(list_resources_add)
        app_log.info(list_resources_remove)
        abort(404, "For devs pouposes")
        # Sending remote inter-site create requests to the distant nodes
        # TODO update this method

        def parallel_horizontal_request(method, obj, alloc_pool):
            app_log = logging.getLogger()
            starting_time = time.time()
            app_log.info(
                'Starting parallel horizontal request thread at time:  %s', starting_time)
            if obj != local_region_name:
                remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'

                if method == 'POST':
                    # TODO implement the post request, this is used for resources freshly added to the service
                    remote_params = {
                        'parameter_allocation_pool': '',
                        'parameter_local_cidr': '',
                        'parameter_local_resource': '',
                        'parameter_ipv': data_from_db['parameter_local_ipv'],
                        'parameter_master': local_region_name,
                        'parameter_master_auth': local_region_url[0:-12]+":7575"
                    }
                    if service_type == 'L2':
                        remote_params['parameter_allocation_pool'] = alloc_pool
                        remote_params['parameter_local_cidr'] = parameter_local_cidr

                    remote_service = {'name': data_from_db['service_name'], 'type': data_from_db['service_type'], 'params': [str(remote_params)
                                                                                                                             ],
                                      'global': data_from_db['service_global'], 'resources': service_resources_list}
                    # send horizontal (service_remote_inter_endpoints[obj])
                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json'}

                    r = requests.post(remote_inter_instance, data=json.dumps(
                        remote_service), headers=headers)

                    if service_type == 'L2':
                        remote_res = {r.json()['local_region']: r.json()[
                            'local_resource']}
                        remote_resources_ids.append(remote_res)
                if method == 'PUT':
                    app_log.info('what')
                    # TODO implement the put request

        # Sending remote inter-site create requests to the distant nodes starting by the POST
        # TODO update this part to send post and put requests
        start_horizontal_time = time.time()
        app_log.info(
            "Starting: Using threads for horizontal creation request.")
        service_resource_total_list = service_resources_list + list_resources_remove
        workers2 = len(service_resources_total_list)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers2) as executor:
            for obj in service_resources_total_list:
                if obj in list_resources_remove:
                    executor.submit(parallel_horizontal_request, "PUT",
                                    obj, "")
                else:
                    if obj in list_resources_add:
                        if service_type == 'L2':
                            executor.submit(parallel_horizontal_request, "POST",
                                            obj, l2allocation_list[obj])
                        if service_type == 'L3':
                            executor.submit(
                                parallel_horizontal_request, "POST", obj, "")
                    else:
                        executor.submit(
                            parallel_horizontal_request, "PUT", obj, "")
        end_horizontal_time = time.time()
        app_log.info('Finishing: Using threads for horizontal creation request.. Time: %s',
                     (end_horizontal_time - start_horizontal_time))

        end_time = time.time()
        app_log.info('Finishing time: %s', end_time)
        app_log.info('Total time spent: %s', end_time - start_time)
        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        abort(404, "Service not found with global ID: {global_id}")

# Handler to delete a service


def verticalDeleteService(global_id):
    app_log.info('Starting: Deleting a service vertical request.')
    service_remote_inter_endpoints = {}
    service = Service.query.filter(
        Service.service_global == global_id).one_or_none()
    if service is not None:
        service_schema = ServiceSchema()
        service_data = service_schema.dump(service).data

        # A service can only be deleted from the master instance
        if service_data['service_params'][0]['parameter_master'] == local_region_name:
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

            # Sending remote inter-site delete requests to the distant nodes
            # If the service is of L2 type, firstly we need to verify that remote created networks can be deleted
            delete_conditions = []

            def parallel_horizontal_validation(obj):
                app_log = logging.getLogger()
                starting_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_time)
                if obj != local_region_name:
                    remote_inter_instance = service_remote_inter_endpoints[obj].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                    remote_service = {
                        'resource_cidr': '', 'service_type': service_data['service_type'], 'global_id': global_id, 'verification_type': 'DELETE'}
                    # send horizontal verification request

                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json'}
                    r = requests.get(remote_inter_instance,
                                     params=remote_service, headers=headers)
                    app_log.info(r.json()['result'])
                    delete_conditions.append(r.json()['result'])

            workers = len(resources_list_to_delete)
            app_log.info(
                "Starting: Using threads for horizontal delete validation request.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for obj in resources_list_to_delete:
                    executor.submit(
                        parallel_horizontal_validation, obj['resource_region'])
            app_log.info(
                'Finishing: Using threads for horizontal delete validation request.')

            if not all(rest == 'True' for rest in delete_conditions):
                abort(
                    404, "Service can not be deleted, remote instances still have plugged ports")

            # Deleting the interconnections
            for element in interconnections_delete:
                inter = element['interconnexion_uuid']

                try:
                    inter_del = net_adap.delete(
                        url='/v2.0/inter/interconnections/' + inter)
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter" + e.message)

            # Locally deleting the service
            db.session.delete(service)
            db.session.commit()

            def parallel_horizontal_delete_request(obj):
                app_log = logging.getLogger()
                starting_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_time)
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
            app_log.info(
                "Starting: Using threads for horizontal delete request.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for obj in resources_list_to_delete:
                    executor.submit(parallel_horizontal_delete_request, obj)
            app_log.info(
                'Finishing: Using threads for horizontal delete request.')

            return make_response("{id} successfully deleted".format(id=global_id), 200)

        else:
            app_log.info('Finishing: Deleting a service vertical request.')
            abort(404, "This module is not the master for the service with ID {id}, please address this request to {region} module".format(
                id=global_id, region=service_data['service_params'][0]['parameter_master']))
    else:
        app_log.info('Finishing: Deleting a service vertical request.')
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
    service_resources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
        (item.split(',')) for item in service.get("resources", None)))
    service_remote_auth_endpoints = {}
    local_interconnections_ids = []

    to_service = {
        'service_name': service_name,
        'service_type': service_type,
        'service_global': service_global
    }

    # Extracting the local resource if the service is of type L3
    if service_type == 'L3':
        for region, uuid in service_resources_list.items():
            if region == local_region_name:
                local_resource = uuid
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

    if service_type == 'L2':
        # Local network creation
        network_data = {'network': {
            'name': service_name + '_net',
            'admin_state_up': True,
        }}
        try:
            network_inter = net_adap.post(
                url='/v2.0/networks', json=network_data)
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter: " + e.message)
        # Local subnetwork creation
        local_resource = network_inter.json()['network']['id']
        subnetwork_data = {'subnet': {
            'name': service_name + '_subnet',
            'network_id': local_resource,
            'ip_version': 4,
            'cidr': service_params['parameter_local_cidr'],
        }}
        try:
            subnetwork_inter = net_adap.post(
                url='/v2.0/subnets', json=subnetwork_data)
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter" + e.message)

        # Adding the local network identifier to the resources list
        service_resources_list[local_region_name] = local_resource

    # calling the interconnection service plugin to create the necessary objects
    def parallel_inters_creation_request(region, uuid):
        app_log = logging.getLogger()
        starting_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_time)
        app_log.info(region + " " + uuid)
        if local_region_name != region:
            interconnection_data = {'interconnection': {
                'name': service_name,
                'remote_keystone': service_remote_auth_endpoints[region],
                'remote_region': region,
                'local_resource_id': local_resource,
                'type': SERVICE_TYPE[service_type],
                'remote_resource_id': uuid,
            }}
            app_log.info(interconnection_data)
            try:
                inter_temp = net_adap.post(
                    url='/v2.0/inter/interconnections/', json=interconnection_data)
            except ClientException as e:
                app_log.info(
                    "Exception when contacting the network adapter: " + e.message)

            app_log.info(inter_temp)
            local_interconnections_ids.append(
                inter_temp.json()['interconnection']['id'])

    # calling the interconnection service plugin to create the necessary objects
    # At this point, this is done only for the L3 routing service
    if service_type == 'L3':
        workers3 = len(service_resources_list.keys())
        start_interconnection_time = time.time()
        app_log.info(
            "Starting: Using threads for local interconnection create request.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers3) as executor:
            for region, uuid in service_resources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing: Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

    app_log.info("Starting: Creating the service schema")
    # Create a service instance using the schema and the build service
    service_schema = ServiceSchema()
    new_service = service_schema.load(to_service, session=db.session).data

    # Adding the resources to the service
    for region, uuid in service_resources_list.items():
        resource = {
            'resource_region': region,
            'resource_uuid': uuid
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

        network_temp = net_adap.get(
            '/v2.0/networks/' + local_resource).json()['network']
        subnet_id = network_temp['subnets'][0]

        subnetwork_temp = net_adap.get('/v2.0/subnets/' + subnet_id).json()
        subnet = subnetwork_temp['subnet']
        service_params['parameter_local_cidr'] = subnet['cidr']
    # Since every kind of service has a local resource, we store it without the loop
    service_params['parameter_local_resource'] = local_resource

    service_params_schema = ParamsSchema()
    new_service_params = service_params_schema.load(
        service_params, session=db.session).data
    new_service.service_params.append(new_service_params)

    # Add the service to the database
    db.session.add(new_service)
    db.session.commit()

    answer_service = {'global_id': service_global, 'type': service_type,
                      'local_region': local_region_name, 'local_resource': local_resource}

    app_log.info("Finishing: Creating the service schema")

    # If the service is from L2 type, do the local DHCP change
    # This is done here because if doing this at the POST subnet request will take one additional IP address for the DHCP service, if instead we do this now, the DHCP service will be by default assigned to the second available IP address of the network
    if service_type == 'L2':
        app_log.info(
            "Starting: Updating the DHCP pool ranges for the local deployment.")
        body = {'subnet': {'allocation_pools': [{'start': service_params['parameter_allocation_pool'].split(
                "-", 1)[0], 'end': service_params['parameter_allocation_pool'].split("-", 1)[1]}]}}

        network_temp = net_adap.get(
            '/v2.0/networks/' + local_resource).json()['network']
        subnet_id = network_temp['subnets'][0]

        app_log.info(str(subnet_id))

        dhcp_change = net_adap.put(url='/v2.0/subnets/'+subnet_id, json=body)
        app_log.info(
            "Finishing: Updating the DHCP pool ranges for the local deployment.")

    end_time = time.time()
    app_log.info('Finishing time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return answer_service, 201

# Handler to update a service horizontal


def horizontalUpdateService(global_id, service):
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal update request')
    service_update = Service.query.filter(
        Service.service_global == global_id).one_or_none()

    # Did we find a service?
    if service_update is not None:

        service_remote_auth_endpoints = {}

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

        service_schema_temp = ServiceSchema()
        data_from_db = service_schema_temp.dump(service_update).data

        to_service_resources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
            (item.split(',')) for item in service.get("resources", None)))

        local_resource = ''

        # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalogue

        app_log.info('Starting: Saving Keystone information from catalogue')
        for obj in catalog_endpoints:
            if obj['name'] == 'keystone':
                for endpoint in obj['endpoints']:
                    for region_name in to_service_resources_list.keys():
                        if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                            service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                            break
        app_log.info('Finishing: Saving Keystone information from catalogue')

        for region, uuid in to_service_resources_list.items():
            if region == local_region_name:
                local_resource = uuid
                break

        local_interconnections_ids = []

        def parallel_inters_creation_request(region, uuid):
            app_log = logging.getLogger()
            starting_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_time)
            if local_region_name != region:
                interconnection_data = {'interconnection': {
                    'name': data_from_db['service_name'],
                    'remote_keystone': service_remote_auth_endpoints[region],
                    'remote_region': region,
                    'local_resource_id': local_resource,
                    'type': SERVICE_TYPE[data_from_db['service_type']],
                    'remote_resource_id': uuid,
                }}
                try:
                    inter_temp = net_adap.post(
                        url='/v2.0/inter/interconnections/', json=interconnection_data)
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter: " + e.message)

                local_interconnections_ids.append(
                    inter_temp.json()['interconnection']['id'])

        if service.get("post_create_refresh") == 'True':
            app_log.info(
                "Starting: Updating the service with post create refresh condition.")

            # Taking the information of the service resources list to save it into the resource schema
            for update_resource_region, update_resource_uuid in to_service_resources_list.items():

                res_update = Resource.query.outerjoin(Service, Service.service_id == Resource.service_id).filter(
                    Resource.service_id == data_from_db['service_id'], Resource.resource_region == update_resource_region).one_or_none()
                res_update.resource_uuid = update_resource_uuid

                res_update_schema = ResourcesSchema()
                data_from_res = res_update_schema.dump(res_update).data
                app_log.info(data_from_res)

            app_log.info(to_service_resources_list)

            # Using the already parsed information to create the interconnections
            workers = len(to_service_resources_list.keys())
            start_interconnection_time = time.time()
            app_log.info(
                "Starting: Using threads for local interconnection create request.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for region, uuid in to_service_resources_list.items():
                    executor.submit(
                        parallel_inters_creation_request, region, uuid)
            end_interconnection_time = time.time()
            app_log.info('Finishing: Using threads for local interconnection create request. Time: %s',
                         (end_interconnection_time - start_interconnection_time))

            # Adding the interconnections to the service
            app_log.info(
                "Starting: Adding the interconnections to the service.")
            for element in local_interconnections_ids:
                interconnexion = {
                    'interconnexion_uuid': element
                }
                service_interconnections_schema = InterconnectionsSchema()
                new_service_interconnections = service_interconnections_schema.load(
                    interconnexion, session=db.session).data
                service_update.service_interconnections.append(
                    new_service_interconnections)
            app_log.info(
                "Finishing: Adding the interconnections to the service.")
            app_log.info(
                "Finishing: Updating the service with post create refresh condition.")

            db.session.commit()

        else:
            app_log.info(
                "Starting: Updating the service with default behavior.")
            # TODO update all the mess of the default behavior
            service_resources_list_user = []
            new_params = service.get("params", None)
            # app_log.info(str(new_params))

            for region, uuid in to_service_resources_list.items():
                service_resources_list_user.append(
                    {'resource_uuid': uuid, 'resource_region': region})

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

            app_log.info('actual list of resources: ' +
                         str(service_resources_list_db))
            if list_resources_add != []:
                app_log.info('resources to add: ' + str(list_resources_add))
            if list_resources_remove != []:
                app_log.info('resources to delete: ' +
                             str(list_resources_remove))
            search_local_resource_delete = False
            search_local_resource_uuid = ''

            if(list_resources_remove == [] and list_resources_add == []):
                abort(404, "No resources are added/deleted")

            for element in service_resources_list_db:
                if(local_region_name in element['resource_region']):
                    search_local_resource_uuid = element['resource_uuid']
                    break

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
                    except ClientException as e:
                        app_log.info("Can't connect to neutron: " + e.message)

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

                        except ClientException as e:
                            app_log.info(
                                "Can't connect to neutron: " + e.message)

                        # app_log.info(remote_resource_to_delete['resource_uuid'])
                        resource_delete = Resource.query.outerjoin(Service, Resource.service_id == Service.service_id).filter(
                            Service.service_id == data_from_db['service_id']).filter(Resource.resource_uuid == remote_resource_to_delete['resource_uuid']).one_or_none()

                        service_resources_list_db.remove(
                            remote_resource_to_delete)

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

                            except ClientException as e:
                                app_log.info(
                                    "Can't connect to neutron: " + e.message)

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
                    data_from_param = param_update_schema.dump(
                        param_update).data
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
                    except ClientException as e:
                        app_log.info("Can't connect to neutron: " + e.message)

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
                    except ClientException as e:
                        app_log.info("Can't connect to neutron: " + e.message)

            app_log.info(
                "Finishing: Updating the service with default behavior.")

        end_time = time.time()
        app_log.info('Finishing time: %s', end_time)
        app_log.info('Total time spent: %s', end_time - start_time)
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

            inter_del = net_adap.delete(
                url='/v2.0/inter/interconnections/' + inter)

        if service_data['service_type'] == 'L2':
            local_resource = service_data['service_params'][0]['parameter_local_resource']
            network_del = net_adap.delete(
                url='/v2.0/networks/' + local_resource)

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
        return data, 200

    else:
        abort(404, "Service with ID {id} not found".format(id=id))


def horizontalVerification(resource_cidr, service_type, global_id, verification_type):
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal verification request')
    # Depending on the verification type, the answer will answer two different questions: Can you create your service side? Can you delete the service at your side? By default the answer will the True until something we found prouves contrary
    answer = {'condition': 'True', 'information': ''}
    if verification_type == 'CREATE':
        services = Service.query.outerjoin(Parameter, Service.service_id == Parameter.service_id).filter(
            Service.service_type == service_type, Parameter.parameter_local_cidr == resource_cidr).all()
        if services is not None:
            # Serialize the data for the response
            service_schema = ServiceSchema(many=True)
            data = service_schema.dump(services).data
            if data != []:
                answer['condition'], answer['information'] = 'False', 'The CIDR is already being used by other service'

    if verification_type == 'DELETE':
        service = Service.query.filter(Service.service_global == global_id).outerjoin(
            Resource).outerjoin(Interconnexion).one_or_none()
        if service is not None:
            service_schema = ServiceSchema()
            service_data = service_schema.dump(service).data
            local_resource = service_data['service_params'][0]['parameter_local_resource']

            # Authenticate
            auth = service_utils.get_auth_object(local_region_url)
            sess = service_utils.get_session_object(auth)

            auth.get_access(sess)
            auth_ref = auth.auth_ref

            net_adap = Adapter(
                auth=auth,
                session=sess,
                service_type='network',
                interface='public',
                region_name=local_region_name)

            query_parameters = {
                'network_id': local_resource, 'device_owner': 'compute:nova'}

            port_list = []
            try:
                port_list = net_adap.get(
                    url='/v2.0/ports', params=query_parameters).json()['ports']
            except ClientException as e:
                app_log.info(
                    "Exception when contacting the network adapter: " + e.message)

            if port_list != []:
                answer['condition'], answer['information'] = 'False', 'Plugged ports existing'

    end_time = time.time()
    app_log.info('Finishing time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)
    return answer, 200

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
