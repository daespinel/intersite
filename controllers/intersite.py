from flask import make_response, abort
from keystoneauth1.adapter import Adapter
from keystoneauth1.exceptions import ClientException
from random import seed
from random import randint
from service import Resource, ResourceSchema, SubResource, Interconnexion, Parameter, LMaster, L2AllocationPool, L3Cidrs, ParamsSchema, SubResourcesSchema, InterconnectionsSchema, LMasterSchema, L2AllocationPoolSchema, L3CidrsSchema
from config import db
from sqlalchemy import exc
from flask.logging import default_handler
from threading import Lock
from operator import itemgetter
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
import threading
import concurrent.futures
import sys

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

# Handler to get the list of resources

def verticalReadAllResource():
    """
    This function responds to a GET request for /api/intersite-vertical
    with the complete lists of inter-site resources

    :return:        sorted list of inter-site resources
    """
    # Create the list of resources from our data
    resources = Resource.query.order_by(Resource.resource_global).all()

    # Serialize the data for the response
    resource_schema = ResourceSchema(many=True)
    data = resource_schema.dump(resources).data
    
    return data

# Create a handler for our read (GET) one resource by ID
# Possibility to add more information as ids of remote interconnection resources


def verticalReadOneResource(global_id):
    """
    This function responds to a GET request for /api/intersite-vertical/{global_id}
    with a single inter-site resource

    :return:        inter-site resource with global_id
    """
    resource = Resource.query.filter(Resource.resource_global == global_id).outerjoin(
        SubResource).outerjoin(Interconnexion).one_or_none()
    if resource is not None:
        resource_schema = ResourceSchema()
        data = resource_schema.dump(resource).data
        return data

    else:
        abort(404, "Resource with ID {id} not found".format(id=id))

# Handler to create a resource

def verticalCreateResource(resource):
    """
    This function responds to a POST request for /api/intersite-vertical/
    with a single inter-site resource creation

    :return:        freshly created inter-site resource
    """
    # Taking information from the API http POST request
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new resource creation request')
    app_log.info(
        'Starting: Retrieving and checking information provided by the user')
    local_subresource = ''
    resource_name = resource.get("name", None)
    resource_type = resource.get("type", None)
    # resource_subresources = resource.get("subresources", None)
    resource_subresources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
        (item.split(',')) for item in resource.get("subresources", None)))
    resource_subresources_list_search = copy.deepcopy(resource_subresources_list)
    app_log.info('SubResources list for the resource')
    app_log.info(resource_subresources_list)
    resource_remote_auth_endpoints = {}
    resource_remote_inter_endpoints = {}
    parameter_local_allocation_pool = ''
    parameter_local_cidr = ''
    parameter_local_cidr_temp = []
    lock = Lock()
    parameter_local_ipv = 'v4'
    local_interconnections_ids = []
    random_id = createRandomGlobalId()

    # Check if a resource exists with the requested subresources
    existing_resource, check_resource_id = checkExistingResource(
        resource_subresources_list)
    if(existing_resource):
        abort(404, "Resource with global ID {global_check} already connects the subresources".format(
            global_check=check_resource_id))

    to_resource = {
        'resource_name': resource_name,
        'resource_type': resource_type,
        'resource_global': random_id
    }

    for region, uuid in resource_subresources_list.items():
        if region == local_region_name:
            local_subresource = uuid
            break

    if(local_subresource == ''):
        abort(404, "There is no local subresource for the resource")

    auth = service_utils.get_auth_object(local_region_url)
    sess = service_utils.get_session_object(auth)

    app_log.info(
        'Finishing: Retrieving and checking information provided by the user. Time: ' + str(time.time() - start_time))

    # Authenticate
    auth_time = time.time()
    app_log.info(
        'Starting: Authenticating and looking for local subresource')
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
            '/v2.0/networks/' + local_subresource).json()['network']
    except ClientException as e:
        abort(404, "Exception when contacting the network adapter: " + e.message)

    if (network_temp_local == ''):
        abort(404, "There is no local subresource for the resource")

    app_log.info(
        'Finishing: Authenticating and looking for local subresource. Time: ' + str(time.time() - auth_time))

    # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalogue

    catalogue_time = time.time()
    app_log.info(
        'Starting: Saving Neutron and Keystone information from catalogue')

    for obj in catalog_endpoints:
        if obj['name'] == 'neutron':
            for endpoint in obj['endpoints']:
                for region_name in resource_subresources_list.keys():
                    if endpoint['region'] == region_name:
                        resource_remote_inter_endpoints[region_name] = endpoint['url']
                        resource_subresources_list_search.pop(region_name)
                        break
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in resource_subresources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        resource_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    # If a provided Region Name doesn't exist, exit the method
    if bool(resource_subresources_list_search):
        abort(404, "ERROR: Regions " + (" ".join(str(key)
                                                 for key in resource_subresources_list_search.keys())) + " are not found")

    app_log.info(
        'Finishing: Saving Neutron and Keystone information from catalogue. Time: ' + str(time.time() - catalogue_time))

    subnetworks = {}
    CIDRs_conditions = []
    CIDRs = []

    # Validation for the L3 routing resource
    # Use of the parallel request methods
    if resource_type == 'L3':

        # Retrieving the subnetwork information given the region name
        def parallel_subnetwork_request(item, value):
            app_log = logging.getLogger()
            starting_th_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_th_time)
            app_log.info(resource_remote_auth_endpoints[item])
            auth_remote = service_utils.get_auth_object(
                resource_remote_auth_endpoints[item])
            sess_remote = service_utils.get_session_object(auth_remote)
            app_log.info('Getting information from region ' + str(item))

            # Authenticate
            auth_remote.get_access(sess_remote)
            auth_ref = auth_remote.auth_ref
            net_adap_remote = Adapter(
                auth=auth_remote,
                session=sess_remote,
                service_type='network',
                interface='public',
                region_name=item)

            try:
                subnetworks_temp = net_adap_remote.get('/v2.0/subnets/').json()
            except ClientException as e:
                app_log.info(
                    "Exception when contacting the network adapter: " + e.message)

            for subnetwork in subnetworks_temp['subnets']:
                if(value == subnetwork['network_id']):
                    if (item == local_region_name):
                        parameter_local_cidr_temp.append(subnetwork['cidr'])
                    obj = [item, value, ipaddress.ip_network(
                        subnetwork['cidr'])]
                    CIDRs.append(obj)
                    break

        app_log.info("Starting: L3 routing resource to be done among the subresources: " +
                     (" ".join(str(value) for value in resource_subresources_list.values())))

        app_log.info(
            "Starting(L3): Using threads for remote subnetwork request.")
        remote_subnet_time = time.time()
        workers = len(resource_subresources_list.keys())
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for item, value in resource_subresources_list.items():
                executor.submit(parallel_subnetwork_request, item, value)
        app_log.info(
            'Finishing(L3): Using threads for remote subnetwork request. Time: ' + str(time.time() - remote_subnet_time))

        app_log.info("Starting(L3): Doing IP range validation.")
        l3_ip_valid_time = time.time()
        parameter_local_cidr = parameter_local_cidr_temp[0]
        app_log.info("The parameter_local_cidr is: " +
                     str(parameter_local_cidr))
        app_log.info("The parameter_local_cidr_temp in 0 is: " +
                     str(parameter_local_cidr_temp[0]))
        # Doing the IP range validation to avoid overlapping problems
        for a, b in itertools.combinations([item[2] for item in CIDRs], 2):
            if a.overlaps(b):
                abort(404, "ERROR: networks " + " " +
                      (str(a)) + " and "+(str(b)) + " overlap")

        app_log.info("Finishing(L3): Doing IP range validation. Time: " +
                     str(time.time() - l3_ip_valid_time))

    # Validation for the Layer 2 network extension
    # Use of the parallel request methods
    if resource_type == 'L2':

        app_log.info('Starting: L2 extension resource to be done among the subresources: ' +
                     (' ' .join(str(value) for value in resource_subresources_list.values())))

        app_log.info(
            'Starting(L2): Retrieving the local subnetwork informations.')
        l2_local_retrieve_time = time.time()
        # app_log.info(network_temp_local)
        # app_log.info('The local subresource uuid: ' +
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
            'Finishing(L2): Retrieving the local subnetwork informations. Time: ' + str(time.time() - l2_local_retrieve_time))

        # We do the horizontal validation with remote modules
        def parallel_horizontal_validation(obj):
            app_log = logging.getLogger()
            starting_th_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_th_time)
            print("fuck" + str(obj))
            if obj != local_region_name:
                remote_inter_instance = resource_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                remote_resource = {
                    'subresource_cidr': parameter_local_cidr, 'resource_type': resource_type, 'global_id': '', 'verification_type': 'CREATE'}
                # send horizontal verification request
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}
                r = requests.get(remote_inter_instance,
                                 params=remote_resource, headers=headers)
                CIDRs_conditions.append(r.json()['condition'])

        app_log.info(
            "Starting(L2): Using threads for horizontal verification request.")
        l2_hverif_time = time.time()
        workers = len(resource_subresources_list.keys())
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for obj in resource_subresources_list.keys():
                executor.submit(parallel_horizontal_validation, obj)
        app_log.info(
            'Finishing(L2): Using threads for horizontal verification request. Time: ' + str(time.time() - l2_hverif_time))

        app_log.info(
            "Starting(L2): Validating if remote modules already posses a resource with the cidr.")
        l2_cidrval_time = time.time()
        # Validating if the remote modules already possed an inter-site resource with the cidr
        if not all(rest == 'True' for rest in CIDRs_conditions):
            abort(404, "ERROR: CIDR is already used in one of the remote sites")
        app_log.info(
            "Finishing(L2): Validating if remote modules already posses a resource with the cidr. Time: " + str(time.time() - l2_cidrval_time))

        app_log.info("Starting(L2): L2 CIDR allocation pool split.")
        l2_cidralloc_time = time.time()
        main_cidr = parameter_local_cidr
        main_cidr_base = (main_cidr.split("/", 1)[0])
        main_cidr_prefix = (main_cidr.split("/", 1)[1])
        app_log.info(main_cidr_prefix)
        cidr_ranges = []
        # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
        ips_cidr_available = 2**(32-int(main_cidr_prefix))-3
        host_per_site = math.floor(
            ips_cidr_available/len(resource_subresources_list))
        host_per_site = math.floor(host_per_site/2)
        app_log.info("CIDR: " + str(cidr) + ", total available IPs: " + str(ips_cidr_available) +
                     " , Number of sites: " + str(len(resource_subresources_list)) + " , IPs per site:" + str(host_per_site))
        base_index = 3
        site_index = 1

        while base_index <= ips_cidr_available and site_index <= len(resource_subresources_list):
            cidr_ranges.append(
                str(cidr[base_index]) + "-" + str(cidr[base_index + host_per_site - 1]))
            base_index = base_index + int(host_per_site)
            site_index = site_index + 1
        cidr_ranges.append(str(cidr[base_index]) +
                           "-" + str(cidr[ips_cidr_available]))

        app_log.info('Next ranges will be used:')
        for element in cidr_ranges:
            app_log.info(element)

        cidr_range = 0
        l2allocation_list = {}
        sorted_allocation_pools = []
        for object_region in resource_subresources_list.keys():
            #app_log.info("Here we are selecting the allocation pools, the object is: " + str(object_region))
            to_add_l2allocation_pool = {
                'l2allocationpool_first_ip': cidr_ranges[cidr_range].split("-", 1)[0],
                'l2allocationpool_last_ip': cidr_ranges[cidr_range].split("-", 1)[1],
                'l2allocationpool_site': object_region
            }
            # We store the information of the allocation pool given to tha local deployment in order to do
            # the DHCP update latter
            if object_region == local_region_name:
                parameter_local_allocation_pool = cidr_ranges[cidr_range]
            app_log.info(to_add_l2allocation_pool)
            sorted_allocation_pools.append(to_add_l2allocation_pool)
            l2allocation_list[object_region] = cidr_ranges[cidr_range] + ";"
            cidr_range = cidr_range + 1

        app_log.info("Finishing(L2): L2 CIDR allocation pool split. Time: " +
                     str(time.time() - l2_cidralloc_time))

    def parallel_inters_creation_request(region, uuid):
        app_log = logging.getLogger()
        starting_th_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_th_time)
        if local_region_name != region:
            interconnection_data = {'interconnection': {
                'name': resource_name,
                'remote_keystone': resource_remote_auth_endpoints[region],
                'remote_region': region,
                'local_resource_id': local_subresource,
                'type': SERVICE_TYPE[resource_type],
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

    # Calling the interconnection resource plugin to create the necessary objects
    # This action is called here if the resource is an L3 resource
    if resource_type == 'L3':
        app_log.info(
            "Starting(L3): Using threads for local interconnection create request.")
        workers = len(resource_subresources_list.keys())
        start_interconnection_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for region, uuid in resource_subresources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing(L3): Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

    app_log.info("Starting: Creating the resource schema")
    schema_time = time.time()
    # Create a resource instance using the schema and the build resource
    resource_schema = ResourceSchema()
    new_resource = resource_schema.load(to_resource, session=db.session).data

    # Adding the subresources to the resource
    # Firstly done for the L3 resource
    if resource_type == 'L3':
        app_log.info(
            "Starting(L3): Adding the subresources and interconnections to the resource.")
        l3_resschema_time = time.time()
        for region, uuid in resource_subresources_list.items():
            subresource = {
                'subresource_region': region,
                'subresource_uuid': uuid
            }
            resource_subresources_schema = SubResourcesSchema()
            new_resource_subresources = resource_subresources_schema.load(
                subresource, session=db.session).data
            new_resource.resource_subresources.append(new_resource_subresources)

            to_delete_object = ""
            for interco in local_interconnections_ids:
                if interco[0] == uuid:
                    interconnexion = {
                        'interconnexion_uuid': interco[1],
                        'subresource': new_resource_subresources
                    }
                    new_resource_interconnections = Interconnexion(
                        interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                    new_resource.resource_interconnections.append(
                        new_resource_interconnections)
                    to_delete_object = interco
                    break
            if to_delete_object != "":
                local_interconnections_ids.remove(to_delete_object)

        app_log.info(
            "Finishing(L3): Adding the subresources and interconnections to the resource. Time: " + str(time.time() - l3_resschema_time))

    app_log.info("Starting: Creating the resource params schema")
    params_time = time.time()
    parameters = {
        'parameter_allocation_pool': parameter_local_allocation_pool,
        'parameter_local_cidr': parameter_local_cidr,
        'parameter_local_subresource': local_subresource,
        'parameter_ipv': parameter_local_ipv,
        'parameter_master': local_region_name,
        'parameter_master_auth': local_region_url[0:-12]+":7575"
    }

    resource_params_schema = ParamsSchema()
    new_resource_params = resource_params_schema.load(
        parameters, session=db.session).data
    resource_lmaster_schema = LMasterSchema()
    new_lmaster = {}
    new_lmaster_params = resource_lmaster_schema.load(
        new_lmaster, session=db.session).data

    if resource_type == 'L3':
        app_log.info(
            "Starting(L3): Adding the L3 resource master cidrs.")
        l3_master_time = time.time()
        resource_l3cidrs_schema = L3CidrsSchema()
        for element in CIDRs:
            to_add_l3cidr = {
                'l3cidrs_site': element[0],
                'l3cidrs_cidr': str(element[2])
            }
            new_l3cidrs_params = resource_l3cidrs_schema.load(
                to_add_l3cidr, session=db.session).data
            new_lmaster_params.lmaster_l3cidrs.append(
                new_l3cidrs_params)
        app_log.info(
            "Finishing(L3): Adding the L3 resource master cidrs. Time: " + str(time.time() - l3_master_time))

    # Adding the LMaster object if the resource type is L2
    if resource_type == 'L2':
        app_log.info(
            "Starting(L2): Adding the L2 resource master allocation pools.")
        l2_master_time = time.time()
        resource_l2allocation_pool_schema = L2AllocationPoolSchema()
        for object_alloc in sorted_allocation_pools:
            app_log.info(
                "Here we are selecting the allocation pools, the object is: " + str(object_alloc['l2allocationpool_site']))
            new_l2allocation_pool_params = resource_l2allocation_pool_schema.load(
                object_alloc, session=db.session).data
            new_lmaster_params.lmaster_l2allocationpools.append(
                new_l2allocation_pool_params)
        app_log.info(
            "Finishing(L2): Adding the l2 resource master allocation pools. Time: " + str(time.time() - l2_master_time))

    new_resource_params.parameter_lmaster.append(new_lmaster_params)
    app_log.info("Finishing: Creating the resource params schema. Time: " +
                 str(time.time() - params_time))

    if resource_type == 'L2':
        app_log.info(
            "Starting(L2): Updating the DHCP pool ranges for the local deployment.")
        l2_dhcp_time = time.time()
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
            "Finishing(L2): Updating the DHCP pool ranges for the local deployment. Time: " + str(time.time() - l2_dhcp_time))

    new_resource.resource_params.append(new_resource_params)
    app_log.info("Finishing: Creating the resource schema. Time: " +
                 str(time.time() - schema_time))
    remote_subresources_ids = []

    # Sending remote inter-site create requests to the distant nodes
    def parallel_horizontal_request(obj, alloc_pool):
        app_log = logging.getLogger()
        starting_th_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_th_time)
        if obj != service_utils.get_region_name():
            remote_inter_instance = resource_remote_inter_endpoints[obj].strip(
                '9696/')
            remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
            remote_params = {
                'parameter_allocation_pool': '',
                'parameter_local_cidr': '',
                'parameter_local_subresource': '',
                'parameter_ipv': parameter_local_ipv,
                'parameter_master': local_region_name,
                'parameter_master_auth': local_region_url[0:-12]+":7575"
            }
            if resource_type == 'L2':
                remote_params['parameter_allocation_pool'] = alloc_pool
                remote_params['parameter_local_cidr'] = parameter_local_cidr

            remote_resource = {'name': resource_name, 'type': resource_type, 'params': [str(remote_params)
                                                                                     ],
                              'global': random_id, 'subresources': resource.get("subresources", None)}
            # send horizontal (resource_remote_inter_endpoints[obj])
            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}

            r = requests.post(remote_inter_instance, data=json.dumps(
                remote_resource), headers=headers)

            if resource_type == 'L2':
                remote_res = {r.json()['local_region']: r.json()[
                    'local_subresource']}
                remote_subresources_ids.append(remote_res)

            app_log.info('Finishing thread at time:  %s %s', time.time() - starting_th_time, obj)

    start_horizontal_time = time.time()
    app_log.info("Starting: Using threads for horizontal creation request.")
    workers = len(resource_subresources_list.keys())
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for obj in resource_subresources_list.keys():
            if resource_type == 'L2':
                executor.submit(parallel_horizontal_request,
                                obj, l2allocation_list[obj])
            if resource_type == 'L3':
                executor.submit(parallel_horizontal_request, obj, "")
    end_horizontal_time = time.time()
    app_log.info('Finishing: Using threads for horizontal creation request.. Time: %s',
                 (end_horizontal_time - start_horizontal_time))

    # Because of the different needed workflows, here we continue with the L2 workflow
    if resource_type == 'L2':
        l2_updateres_time = time.time()
        app_log.info("Starting(L2): Updating the subresources list.")
        # For the L2 resource type, update the subresources compossing the resource
        for element in remote_subresources_ids:
            for key in element.keys():
                resource_subresources_list[key] = element[key]
        app_log.info(resource_subresources_list)
        app_log.info("Finishing(L2): Updating the subresources list. Time: " +
                     str(time.time() - l2_updateres_time))

        # For the L2 resource type, create the interconnections to remote modules and add them to the resource schema
        app_log.info(
            "Starting(L2): Using threads for local interconnection create request.")
        workers = len(resource_subresources_list.keys())
        start_interconnection_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for region, uuid in resource_subresources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing(L2): Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

        app_log.info(
            "Starting(L2): Updating the subresources and interconnections composing the resource.")
        l2_upd_resource_time = time.time()
        remote_l2_new_sites = []

        # Adding the subresources to the resource
        for region, uuid in resource_subresources_list.items():
            subresource = {
                'subresource_region': region,
                'subresource_uuid': uuid
            }
            new_resource_subresources = SubResource(
                subresource_region=region, subresource_uuid=uuid)
            #resource_subresources_schema = SubResourcesSchema()
            # new_resource_subresources = resource_subresources_schema.load(
            #    subresource, session=db.session).data
            new_resource.resource_subresources.append(new_resource_subresources)
            remote_l2_new_sites.append(region + "," + uuid)
            #app_log.info("The remote L2 objects are the following: " + str(remote_l2_new_sites))
            to_delete_object = ""
            for interco in local_interconnections_ids:
                if interco[0] == uuid:
                    new_resource_interconnections = Interconnexion(
                        interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                    new_resource.resource_interconnections.append(
                        new_resource_interconnections)
                    to_delete_object = interco
                    break
            if to_delete_object != "":
                local_interconnections_ids.remove(to_delete_object)

        app_log.info(
            "Finishing(L2): Updating the subresources and interconnections composing the resource. Time: " + str(time.time() - l2_upd_resource_time))

        # For the L2 resource type, send the horizontal put request in order to provide remotes instances with the subresources uuids for interconnections
        def parallel_horizontal_put_request(obj):
            app_log = logging.getLogger()
            starting_th_time = time.time()
            app_log.info('Starting thread at time:  %s', starting_th_time)
            if obj != service_utils.get_region_name():
                remote_inter_instance = resource_remote_inter_endpoints[obj].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + \
                    '7575/api/intersite-horizontal/' + str(random_id)
                remote_resource = {'name': resource_name, 'type': resource_type, 'params': [
                ], 'global': random_id, 'subresources': remote_l2_new_sites, 'post_create_refresh': 'True'}
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}

                r = requests.put(remote_inter_instance, data=json.dumps(
                    remote_resource), headers=headers)

        app_log.info(
            "Starting(L2): Using threads for horizontal put request.")
        workers = len(resource_subresources_list.keys())
        start_horizontal_put_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for k_remote in resource_subresources_list.keys():
                executor.submit(parallel_horizontal_put_request, k_remote)
        end_horizontal_put_time = time.time()
        app_log.info('Finishing(L2): Using threads for horizontal put request. Time: %s',
                     (end_horizontal_put_time - start_horizontal_put_time))

    # Add the resource to the database
    db.session.add(new_resource)
    db.session.commit()

    end_time = time.time()
    app_log.info('Finishing time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return resource_schema.dump(new_resource).data, 201


# Handler to update an existing resource

def verticalUpdateResource(global_id, resource):
    """
    This function responds to a PUT request for /api/intersite-vertical/{global_id}
    with a single inter-site resource update

    :return:        freshly modified inter-site resource
    """
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new resource update request.')
    app_log.info('Starting: Validating resource information.')
    resource_update = Resource.query.filter(
        Resource.resource_global == global_id).one_or_none()

    # Did we find a resource?
    if resource_update is not None:

        resource_schema_temp = ResourceSchema()
        data_from_db = resource_schema_temp.dump(resource_update).data
        resource_type = data_from_db['resource_type']
        resource_to_update_master = data_from_db['resource_params'][0]['parameter_master']
        # Check if the module is the master for that resource. If it isn't, return abort to inform that it can't execute the request
        if(resource_to_update_master != local_region_name):
            app_log.info(
                'ALERT: This module is not the master of the resource.')
            app_log.info('Finishing: Validating resource information.')
            abort(404, "This module is not the master of the resource, please redirect the request to: " +
                  resource_to_update_master + " module")

        app_log.info('Finishing: Validating resource information. Time: ' +
                     str(time.time() - start_time))
        app_log.info(
            'Starting: extracting information from the db and the user information.')
        db_info_time = time.time()
        to_resource_subresources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
            (item.split(',')) for item in resource.get("subresources", None)))
        resource_subresources_list_user = []
        for region, uuid in to_resource_subresources_list.items():
            resource_subresources_list_user.append(
                {'subresource_uuid': uuid, 'subresource_region': region})
        # app_log.info(resource_subresources_list_user)

        resource_subresources_list_db = []
        for element in data_from_db['resource_subresources']:
            resource_subresources_list_db.append(
                {'subresource_uuid': element['subresource_uuid'], 'subresource_region': element['subresource_region']})
        # We create two lists, the first one is for the subresources that will be deleted, the second one is for the ones that will be added
        list_subresources_remove = copy.deepcopy(resource_subresources_list_db)
        list_subresources_add = []
        resource_subresources_list = []

        for subresource_component in resource_subresources_list_user:
            contidion_temp = True
            for subresource_component_2 in resource_subresources_list_db:
                if subresource_component == subresource_component_2:
                    list_subresources_remove.remove(subresource_component_2)
                    contidion_temp = False
                    break
            if(contidion_temp == True):
                list_subresources_add.append(subresource_component)

        app_log.info(
            'Finishing: extracting information from the db and the user information. Time: ' + str(time.time() - db_info_time))
        app_log.info('INFO: Actual list of subresources' +
                     str(resource_subresources_list_db))
        app_log.info('INFO: SubResources to add' + str(list_subresources_add))
        app_log.info('INFO: SubResources to delete' + str(list_subresources_remove))

        # We analyze if the user is really doing a change to the resource by adding/removing subresources.
        if(list_subresources_remove == [] and list_subresources_add == []):
            abort(404, "No subresources are added/deleted.")

        app_log.info(
            'Starting: Validating if the local subresource is in the list.')
        localrsc_valid_time = time.time()
        search_local_subresource_delete = False
        local_subresource = data_from_db['resource_params'][0]['parameter_local_subresource']

        for element in list_subresources_remove:
            if(local_subresource in element['subresource_uuid']):
                search_local_subresource_delete = True

        app_log.info(
            'Finishing: Validating if the local subresource is in the list. Time: ' + str(time.time() - localrsc_valid_time))
        if search_local_subresource_delete:
            abort(404, 'The master local subresource can not be deleted.')

        app_log.info('Starting: Contacting keystone and creating net adapter.')
        keystone_time = time.time()
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
            'Finishing: Contacting keystone and creating net adapter. Time: ' + str(time.time() - keystone_time))

        # First delete the interconnections between the local subresource and the subresources that are going to be deleted
        if (list_subresources_remove):

            def parallel_inters_delete_request(subresource_delete):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                interconnection_db_delete = Interconnexion.query.outerjoin(Resource, Interconnexion.resource_id == Resource.resource_id).outerjoin(SubResource, SubResource.resource_id == Resource.resource_id).filter(
                    SubResource.subresource_uuid == subresource_delete['subresource_uuid']).filter(Interconnexion.resource_id == data_from_db['resource_id']).filter(Interconnexion.subresource_id == SubResource.subresource_id).one_or_none()
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
                # The same procedure is applied to the subresource to be deleted locally
                subresource_to_delete = SubResource.query.outerjoin(Resource, SubResource.resource_id == Resource.resource_id).filter(
                    Resource.resource_id == data_from_db['resource_id']).filter(SubResource.subresource_uuid == subresource_delete['subresource_uuid']).one_or_none()
                resource_subresources_list_db.remove(subresource_delete)
                # We do a per resource division because in every case we need to do different actions
                if subresource_to_delete:
                    if resource_type == 'L3':
                        app_log.info(
                            'Starting(L3): Deleting the L3 CIDRs of the remote subresources.')
                        l3_del_time = time.time()
                        l3cidrs_to_delete = L3Cidrs.query.outerjoin(LMaster, LMaster.lmaster_id == L3Cidrs.lmaster_id).outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                            Resource, Resource.resource_id == Parameter.resource_id).filter(Resource.resource_id == data_from_db['resource_id']).filter(L3Cidrs.l3cidrs_site == subresource_delete['subresource_region']).one_or_none()
                        if l3cidrs_to_delete:
                            db.session.delete(l3cidrs_to_delete)
                            db.session.commit()
                        app_log.info(
                            'Finishing(L3): Deleting the L3 CIDRs of the remote subresources. Time: ' + str(time.time() - l3_del_time))
                    if resource_type == 'L2':
                        app_log.info(
                            'Starting(L2): Deleting the L2 allocation pools of the remote subresources.')
                        l2_del_time = time.time()
                        l2allocation_to_delete = L2AllocationPool.query.outerjoin(LMaster, LMaster.lmaster_id == L2AllocationPool.lmaster_id).outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                            Resource, Resource.resource_id == Parameter.resource_id).filter(Resource.resource_id == data_from_db['resource_id']).filter(L2AllocationPool.l2allocationpool_site == subresource_delete['subresource_region']).one_or_none()
                        db.session.delete(l2allocation_to_delete)
                        db.session.commit()
                        app_log.info(
                            'Finishing(L2): Deleting the L2 allocation pools of the remote subresources. Time: ' + str(time.time() - l2_del_time))
                    db.session.delete(subresource_to_delete)
                    db.session.commit()

            # app_log.info(list_subresources_remove)
            app_log.info(
                'Starting: Deleting local interconnections and subresources.')
            workers = len(list_subresources_remove)
            start_interconnection_delete_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for subresource in list_subresources_remove:
                    executor.submit(parallel_inters_delete_request, subresource)
            end_interconnection_delete_time = time.time()
            app_log.info('Finishing: Deleting local interconnections and subresources. Time: %s',
                         (end_interconnection_delete_time - start_interconnection_delete_time))

        app_log.info(
            'Starting: Saving Neutron and Keystone information from catalogue.')
        keystone_cat_time = time.time()
        resource_remote_auth_endpoints = {}
        resource_remote_inter_endpoints = {}
        resource_subresources_list_search = copy.deepcopy(
            list_subresources_add)
        resource_subresources_list_db_search = copy.deepcopy(
            resource_subresources_list_db)

        for obj in catalog_endpoints:
            if obj['name'] == 'neutron':
                for endpoint in obj['endpoints']:
                    # Storing information of Neutrons of actual subresource list, subresources to add and subresources to delete
                    for existing_subresource in resource_subresources_list_db:
                        if endpoint['region'] == existing_subresource['subresource_region']:
                            resource_remote_inter_endpoints[existing_subresource['subresource_region']
                                                           ] = endpoint['url']
                            resource_subresources_list_db_search.remove(
                                existing_subresource)
                            break
                    for subresource_element in list_subresources_add:
                        if endpoint['region'] == subresource_element['subresource_region']:
                            resource_remote_inter_endpoints[subresource_element['subresource_region']
                                                           ] = endpoint['url']
                            resource_subresources_list_search.remove(
                                subresource_element)
                            break
                    for subresource_delete in list_subresources_remove:
                        if endpoint['region'] == subresource_delete['subresource_region']:
                            resource_remote_inter_endpoints[subresource_delete['subresource_region']
                                                           ] = endpoint['url']
                            break
            if obj['name'] == 'keystone':
                # Storing information of Keystone of actual subresource list, subresources to add and subresources to delete
                for endpoint in obj['endpoints']:
                    for existing_subresource in resource_subresources_list_db:
                        if endpoint['region'] == existing_subresource['subresource_region']:
                            resource_remote_auth_endpoints[existing_subresource['subresource_region']
                                                          ] = endpoint['url']+'/v3'
                            break
                    for subresource_element in list_subresources_add:
                        if endpoint['region'] == subresource_element['subresource_region'] and endpoint['interface'] == 'public':
                            resource_remote_auth_endpoints[subresource_element['subresource_region']
                                                          ] = endpoint['url']+'/v3'
                            break
                    for subresource_delete in list_subresources_remove:
                        if endpoint['region'] == subresource_delete['subresource_region']:
                            resource_remote_auth_endpoints[subresource_delete['subresource_region']
                                                          ] = endpoint['url'] + '/v3'
                            break

        if bool(resource_subresources_list_search):
            abort(404, "ERROR: Regions " + (" ".join(str(key['subresource_region'])
                                                     for key in resource_subresources_list_search)) + " are not found")

        if bool(resource_subresources_list_db_search):
            abort(404, "ERROR: Regions " + (" ".join(str(key['subresource_region'])
                                                     for key in resource_subresources_list_db_search)) + " are not found")

        app_log.info(
            'Finishing: Saving Neutron and Keystone information from catalogue. Time:' + str(time.time() - keystone_cat_time))

        # Do a new list with the actual subresources that are going to be used in the following part of the resource
        # then, verify the new subresources to add to the resource and add them
        # Depending on the resource type, the validation will be different
        resource_subresources_list = resource_subresources_list_db + list_subresources_add
        if(list_subresources_add):
            new_CIDRs = []
            actual_CIDRs = []
            local_interconnections_ids = []
            # Retrieving the subnetwork information given the region name

            def parallel_new_subnetwork_request(item):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                global parameter_local_cidr

                net_adap_remote = Adapter(
                    auth=auth,
                    session=sess,
                    service_type='network',
                    interface='public',
                    region_name=item["subresource_region"])

                try:
                    subnetworks_temp = net_adap_remote.get(
                        '/v2.0/subnets/').json()
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter: " + e.message)

                for subnetwork in subnetworks_temp['subnets']:
                    if(item["subresource_uuid"] == subnetwork['network_id']):
                        obj = [item["subresource_region"], item["subresource_uuid"],
                               ipaddress.ip_network(subnetwork['cidr'])]
                        new_CIDRs.append(obj)
                        break

            resource_subresources_list_params = []
            # Validation for the L3 routing resource
            # Use of the parallel request methods
            if(resource_type == 'L3'):
                l3_res_upd_time = time.time()
                app_log.info("Starting: L3 routing resource update, adding the subresources: " +
                             (" ".join(str(value) for value in [element["subresource_uuid"] for element in list_subresources_add])))

                # app_log.info(list_subresources_add)
                app_log.info(
                    "Starting(L3): Using threads for remote subnetwork request.")
                l3_th_time = time.time()
                workers = len(list_subresources_add)
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for item in list_subresources_add:
                        executor.submit(parallel_new_subnetwork_request, item)
                app_log.info(
                    'Finishing(L3): Using threads for remote subnetwork request. Time: ' + str(time.time() - l3_th_time))
                app_log.info(
                    "Starting(L3): Accesing information of actual list of subresources.")
                l3_list_retrieve_time = time.time()
                for element in data_from_db['resource_params'][0]['parameter_lmaster'][0]['lmaster_l3cidrs']:
                    obj = [element["l3cidrs_site"],
                           ipaddress.ip_network(element['l3cidrs_cidr'])]
                    actual_CIDRs.append(obj)
                app_log.info(
                    "Finishing(L3): Accesing information of actual list of subresources. Time: " + str(time.time() - l3_list_retrieve_time))
                app_log.info(
                    "Starting(L3): Doing IP range validation for L3 resource.")
                l3_ip_validation_time = time.time()
                # Doing the IP range validation to avoid overlapping problems
                check_cidrs = [item[2] for item in new_CIDRs] + \
                    [item[1] for item in actual_CIDRs]
                for a, b in itertools.combinations(check_cidrs, 2):
                    if a.overlaps(b):
                        abort(404, "ERROR: networks " + " " +
                              (str(a)) + " and "+(str(b)) + " overlap")
                app_log.info(
                    "Finishing(L3): Doing IP range validation for L3 resource. Time: " + str(time.time() - l3_ip_validation_time))

            if(resource_type == 'L2'):
                l2_update_resource_time = time.time()
                app_log.info('Starting: L2 extension resource to be done among the subresources: ' +
                             (' ' .join(str(value['subresource_region']) for value in resource_subresources_list)))

                app_log.info(
                    'Starting(L2): Retrieving the local subnetwork informations.')
                l2_list_retrieve_time = time.time()
                parameter_local_cidr = data_from_db['resource_params'][0]['parameter_local_cidr']
                app_log.info(
                    'Finishing(L2): Retrieving the local subnetwork informations. Time: ' + str(time.time() - l2_list_retrieve_time))

                CIDRs_conditions = []
                # We do the horizontal validation with new remote modules

                def parallel_horizontal_validation(obj):
                    app_log = logging.getLogger()
                    starting_th_time = time.time()
                    app_log.info('Starting thread at time:  %s',
                                 starting_th_time)

                    remote_inter_instance = resource_remote_inter_endpoints[obj].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                    remote_resource = {
                        'subresource_cidr': parameter_local_cidr, 'resource_type': resource_type, 'global_id': '', 'verification_type': 'CREATE'}
                    # send horizontal verification request
                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json'}
                    r = requests.get(remote_inter_instance,
                                     params=remote_resource, headers=headers)
                    CIDRs_conditions.append(r.json()['condition'])

                app_log.info(
                    "Starting(L2): Using threads for horizontal verification request with new modules.")
                l2_horizontal_verif_time = time.time()
                workers = len(resource_subresources_list)
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for obj in list_subresources_add:
                        executor.submit(parallel_horizontal_validation, obj)
                app_log.info(
                    'Finishing(L2): Using threads for horizontal verification request with new modules. Time: ' + str(time.time() - l2_horizontal_verif_time))

                app_log.info(
                    "Starting(L2): Validating if remote modules already posses a resource with the cidr.")
                l2_validation_time = time.time()
                # Validating if the remote modules already possed an inter-site resource with the cidr
                if not all(rest == 'True' for rest in CIDRs_conditions):
                    abort(404, "ERROR: CIDR is already used in one of the remote sites")
                app_log.info(
                    "Finishing(L2): Validating if remote modules already posses a resource with the cidr. Time: " + str(time.time() - l2_validation_time))

                def is_allocated(ip_address, pool_dicts_list):
                    condition = -1
                    initial = ''
                    end = ''
                    for pool_dict in pool_dicts_list:
                        initial = ipaddress.IPv4Address(
                            pool_dict['l2allocationpool_first_ip'])
                        end = ipaddress.IPv4Address(
                            pool_dict['l2allocationpool_last_ip'])
                        if ip_address >= initial and ip_address <= end:
                            app_log.info('address inside allocation pool')
                            condition = 1
                            break
                    return condition, initial, end

                app_log.info("Starting(L2): L2 CIDR allocation pool split.")
                l2_alloc_time = time.time()
                main_cidr = parameter_local_cidr
                cidr = ipaddress.ip_network(parameter_local_cidr)
                main_cidr_base = (main_cidr.split("/", 1)[0])
                main_cidr_prefix = (main_cidr.split("/", 1)[1])
                cidr_ranges = []
                # Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
                ips_cidr_total = 2**(32-int(main_cidr_prefix))-3
                ips_cidr_available = copy.deepcopy(ips_cidr_total)
                already_used_pools = data_from_db['resource_params'][0][
                    'parameter_lmaster'][0]['lmaster_l2allocationpools']
                used_alloc_pools = L2AllocationPool.query.outerjoin(LMaster, LMaster.lmaster_id == L2AllocationPool.lmaster_id).outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                    Resource, Resource.resource_id == Parameter.resource_id).filter(Resource.resource_id == data_from_db['resource_id']).all()
                l2allocationpool_schema = L2AllocationPoolSchema(many=True)
                already_used_pools = l2allocationpool_schema.dump(
                    used_alloc_pools).data
                sorted_already_used_pools = sorted(already_used_pools, key=lambda k: int(
                    ipaddress.IPv4Address(k['l2allocationpool_first_ip'])))
                #sorted_already_used_pools = sorted(already_used_pools, key=itemgetter('l2allocationpool_first_ip'))
                app_log.info(sorted_already_used_pools)

                for allocation_pool in already_used_pools:
                    used_ips = int(ipaddress.IPv4Address(allocation_pool["l2allocationpool_last_ip"])) - \
                        int(ipaddress.IPv4Address(
                            allocation_pool["l2allocationpool_first_ip"]))
                    ips_cidr_available = ips_cidr_available - used_ips
                    app_log.info('Already used IPS: ' + str(used_ips))
                    app_log.info(allocation_pool["l2allocationpool_last_ip"])
                    app_log.info(allocation_pool["l2allocationpool_first_ip"])
                app_log.info('Total available IPs: ' + str(ips_cidr_available))
                # If no more addresses are available, we can not proceed
                if ips_cidr_available == 0:
                    abort(404, "ERROR: 0 available IPs are left")
                if ips_cidr_available < len(list_subresources_add):
                    abort(
                        404, "ERROR: Less number of IPs than the number of sites to add are available")
                host_per_site = math.floor(
                    ips_cidr_available/len(list_subresources_add))
                host_per_site = math.floor(host_per_site/4)

                app_log.info("CIDR: " + str(main_cidr) + ", total available IPs: " + str(ips_cidr_total) + ", real available: " + str(ips_cidr_available) +
                             " , new number of sites: " + str(len(list_subresources_add)) + " , IPs per site:" + str(host_per_site))
                base_index = 3
                index = 0
                host_per_site_count = 0
                new_allocated_pools = {}

                for new_subresource in list_subresources_add:
                    new_allocated_pools[new_subresource['subresource_region']] = []
                    host_per_site_count = 0
                    host_count_temp = 0
                    new_initial_ip = ''
                    new_final_ip = ''
                    while host_per_site_count < host_per_site and base_index <= ips_cidr_total+1:
                        ip_to_inspect = cidr[base_index]
                        app_log.info(ip_to_inspect)
                        condition_granted, first_used, last_used = is_allocated(
                            ip_to_inspect, sorted_already_used_pools)
                        # If the condition is 1, it means that the analyzed IP lies in an already allocated pool
                        if condition_granted == 1:
                            difference = int(last_used) - int(ip_to_inspect)
                            base_index = base_index + difference + 1
                            if host_count_temp != 0:
                                app_log.info('saving the information of IPs')
                                new_allocated_pools[new_subresource['subresource_region']].extend(
                                    [str(new_initial_ip), str(new_final_ip)])
                            host_count_temp = 0
                        else:
                            base_index = base_index + 1
                            host_per_site_count = host_per_site_count + 1
                            app_log.info('host per site count ' +
                                         str(host_per_site_count))
                            if new_initial_ip == '' or host_count_temp == 0:
                                new_initial_ip = ip_to_inspect
                            host_count_temp = host_count_temp + 1
                            new_final_ip = ip_to_inspect
                            app_log.info('host count temp ' +
                                         str(host_count_temp))
                            if host_count_temp == host_per_site:
                                app_log.info('saving the information of IPs')
                                new_allocated_pools[new_subresource['subresource_region']].extend(
                                    [str(new_initial_ip), str(new_final_ip)])
                            else:
                                if host_per_site_count == host_per_site:
                                    app_log.info(
                                        'saving the information of IPs')
                                    new_allocated_pools[new_subresource['subresource_region']].extend(
                                        [str(new_initial_ip), str(new_final_ip)])
                    app_log.info('new initial ip: ' + str(new_initial_ip))
                    app_log.info('new final ip: ' + str(new_final_ip))
                    index = index + 1

                app_log.info(new_allocated_pools)
                # We define the L2 Allocation pools list as a dict in order to acces it from the parallel threads
                l2allocation_list = {}
                for alloc_pool_temp_key, alloc_list_value in new_allocated_pools.items():
                    alloc_list_str = ''
                    for i in range(0, int(len(alloc_list_value)/2)+1, 2):
                        alloc_list_str = alloc_list_str + \
                            str(alloc_list_value[i]) + '-' + \
                            str(alloc_list_value[i+1]) + ';'
                    l2allocation_list[alloc_pool_temp_key] = alloc_list_str
                app_log.info(l2allocation_list)
                app_log.info(
                    "Finishing(L2): L2 CIDR allocation pool split. Time: " + str(time.time() - l2_alloc_time))

            def parallel_inters_creation_request(obj):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                if local_region_name != obj["subresource_region"]:
                    interconnection_data = {'interconnection': {
                        'name': data_from_db["resource_name"],
                        'remote_keystone': resource_remote_auth_endpoints[obj["subresource_region"]],
                        'remote_region': obj["subresource_region"],
                        'local_resource_id': local_subresource,
                        'type': SERVICE_TYPE[resource_type],
                        'remote_resource_id': obj["subresource_uuid"],
                    }}

                    try:
                        inter_temp = net_adap.post(
                            url='/v2.0/inter/interconnections/', json=interconnection_data)
                    except ClientException as e:
                        app_log.info(
                            "Exception when contacting the network adapter: " + e.message)

                    local_interconnections_ids.append([obj["subresource_uuid"],
                                                       inter_temp.json()['interconnection']['id']])

            # Calling the interconnection resource plugin to create the necessary objects
            # This action is called here if the resource is an L3 resource
            if resource_type == 'L3':
                app_log.info(
                    "Starting(L3): Using threads for local interconnection create request.")
                workers = len(list_subresources_add)
                start_interconnection_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for obj in list_subresources_add:
                        executor.submit(parallel_inters_creation_request, obj)
                end_interconnection_time = time.time()
                app_log.info('Finishing(L3): Using threads for local interconnection create request. Time: %s',
                             (end_interconnection_time - start_interconnection_time))

            app_log.info("Starting: Updating the resource schema")
            schema_resource_time = time.time()
            # Adding the subresources to the resource
            # Firstly done for the L3 resource
            if resource_type == 'L3':
                app_log.info(
                    "Starting(L3): Adding the subresources and interconnections to the resource.")
                l3_res_inter_time = time.time()
                for element in list_subresources_add:
                    subresource = {
                        'subresource_region': element["subresource_region"],
                        'subresource_uuid': element["subresource_uuid"]
                    }
                    resource_subresources_schema = SubResourcesSchema()
                    new_resource_subresources = resource_subresources_schema.load(
                        subresource, session=db.session).data
                    resource_update.resource_subresources.append(
                        new_resource_subresources)

                    to_delete_object = ""
                    for interco in local_interconnections_ids:
                        # app_log.info(interco)
                        if interco[0] == element['subresource_uuid']:
                            interconnexion = {
                                'interconnexion_uuid': interco[1],
                                'subresource': new_resource_subresources
                            }
                            new_resource_interconnections = Interconnexion(
                                interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                            resource_update.resource_interconnections.append(
                                new_resource_interconnections)
                            to_delete_object = interco
                            break
                    if to_delete_object != "":
                        local_interconnections_ids.remove(to_delete_object)
                app_log.info(
                    "Finishing(L3): Adding the subresources and interconnections to the resource. Time: " + str(time.time() - l3_res_inter_time))
                app_log.info(
                    "Starting(L3): Adding the L3 resource master cidrs.")
                l3_master_upd_time = time.time()
                resource_lmaster = LMaster.query.outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                    Resource, Resource.resource_id == Parameter.resource_id).filter(Resource.resource_id == data_from_db['resource_id']).one_or_none()

                resource_l3cidrs_schema = L3CidrsSchema()
                for element in new_CIDRs:
                    to_add_l3cidr = {
                        'l3cidrs_site': element[0],
                        'l3cidrs_cidr': str(element[2])
                    }
                    new_l3cidrs_params = resource_l3cidrs_schema.load(
                        to_add_l3cidr, session=db.session).data
                    resource_lmaster.lmaster_l3cidrs.append(
                        new_l3cidrs_params)
                app_log.info(
                    "Finishing(L3): Adding the L3 resource master cidrs. Time: " + str(time.time() - l3_master_upd_time))
            db.session.commit()
            app_log.info("Finishing: Updating the resource schema. Time: " +
                         str(time.time() - schema_resource_time))

        remote_subresources_ids = []
        app_log.info('List of subresources and uuids: ')
        app_log.info('New list of subresources update: ' +
                     str(resource_subresources_list))
        app_log.info('SubResources to add: ' + str(list_subresources_add))
        app_log.info('SubResources to delete: ' + str(list_subresources_remove))
        # Sending remote inter-site create requests to the distant nodes

        def parallel_horizontal_put_request(method, obj, alloc_pool):
            app_log = logging.getLogger()
            starting_th_time = time.time()
            app_log.info(
                'Starting parallel horizontal put request thread at time:  %s', starting_th_time)
            app_log.info('The informations of this thread are: ' +
                         str(obj) + ' ' + str(method))
            if obj['subresource_region'] != local_region_name:
                remote_inter_instance = resource_remote_inter_endpoints[obj['subresource_region']].strip(
                    '9696/')
                remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}

                if method == 'CREATE':
                    remote_params = {
                        'parameter_allocation_pool': '',
                        'parameter_local_cidr': '',
                        'parameter_local_subresource': '',
                        'parameter_ipv': data_from_db['resource_params'][0]['parameter_ipv'],
                        'parameter_master': local_region_name,
                        'parameter_master_auth': local_region_url[0:-12]+":7575"
                    }
                    if resource_type == 'L2':
                        remote_params['parameter_allocation_pool'] = alloc_pool
                        remote_params['parameter_local_cidr'] = parameter_local_cidr

                    remote_resource = {'name': data_from_db['resource_name'], 'type': resource_type, 'params': [str(remote_params)
                                                                                                             ],
                                      'global': data_from_db['resource_global'], 'subresources': resource.get("subresources", None)}

                    r = requests.post(remote_inter_instance, data=json.dumps(
                        remote_resource), headers=headers)
                    app_log.info('Remote answer: ' + str(r.json()))

                    if resource_type == 'L2':
                        remote_res = {'subresource_region': r.json()['local_region'], 'subresource_uuid': r.json()[
                            'local_subresource']}
                        remote_subresources_ids.append(remote_res)

                if method == 'DELETE':
                    remote_inter_instance = remote_inter_instance + "/" +\
                        str(data_from_db['resource_global'])
                    remote_resource = {'name': data_from_db['resource_name'], 'type': resource_type, 'params': ['', '', ''],
                                      'global': data_from_db['resource_global'], 'subresources': [], 'post_create_refresh': 'False'}
                    r = requests.put(remote_inter_instance, data=json.dumps(
                        remote_resource), headers=headers)
                    app_log.info('Remote answer: ' + str(r.json()))

                if method == 'PUT':
                    remote_inter_instance = remote_inter_instance + "/" +\
                        str(data_from_db['resource_global'])
                    remote_resource = {'name': data_from_db['resource_name'], 'type': resource_type, 'params': ['', '', ''],
                                      'global': data_from_db['resource_global'], 'subresources': resource.get("subresources", None), 'post_create_refresh': 'False'}
                    r = requests.put(remote_inter_instance, data=json.dumps(
                        remote_resource), headers=headers)
                    app_log.info('Remote answer: ' + str(r.json()))

                if method == 'POST_CREATE':
                    remote_inter_instance = remote_inter_instance + "/" +\
                        str(data_from_db['resource_global'])
                    remote_resource = {'name': data_from_db['resource_name'], 'type': resource_type, 'params': ['', '', ''],
                                      'global': data_from_db['resource_global'], 'subresources': remote_l2_new_sites, 'post_create_refresh': 'True'}
                    r = requests.put(remote_inter_instance, data=json.dumps(
                        remote_resource), headers=headers)
                    app_log.info('Remote answer: ' + str(r.json()))

        # Sending remote inter-site create requests to the distant nodes
        start_horizontal_time = time.time()
        app_log.info(
            "Starting: Using threads for horizontal creation request.")
        resource_subresources_total_list = resource_subresources_list + list_subresources_remove
        app_log.info("The total list of subresources is the following: " +
                     str(resource_subresources_total_list))
        # subresources_to_string = [(",".join((subresource) for subresource in (
        #    (element['subresource_region'] + "," + element['subresource_uuid']) for element in resource_subresources_list)))]
        # print(subresources_to_string)
        workers = len(resource_subresources_total_list)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for obj in resource_subresources_total_list:
                if obj in list_subresources_remove:
                    executor.submit(parallel_horizontal_put_request, 'DELETE',
                                    obj, "")
                else:
                    if obj in list_subresources_add:
                        if resource_type == 'L2':
                            executor.submit(parallel_horizontal_put_request, 'CREATE',
                                            obj, l2allocation_list[obj['subresource_region']])
                        if resource_type == 'L3':
                            executor.submit(
                                parallel_horizontal_put_request, 'CREATE', obj, "")
                    else:
                        if resource_type == 'L3':
                            executor.submit(
                                parallel_horizontal_put_request, 'PUT', obj, "")
                        else:
                            if resource_type == 'L2':
                                executor.submit(
                                    parallel_horizontal_put_request, 'PUT', obj, "")
        end_horizontal_time = time.time()
        app_log.info('Finishing: Using threads for horizontal creation request.. Time: %s',
                     (end_horizontal_time - start_horizontal_time))

        # Because of the different needed workflows, here we continue with the L2 workflow
        if resource_type == 'L2':
            if(list_subresources_add):
                l2_rsc_update_time = time.time()
                app_log.info("Starting(L2): Updating the subresources list.")
                # For the L2 resource type, update the subresources compossing the resource
                for element in remote_subresources_ids:
                    app_log.info(element)
                    element_uuid, element_region = element['subresource_uuid'], element['subresource_region']
                    for i in range(len(resource_subresources_list)):
                        if resource_subresources_list[i]['subresource_region'] == element_region:
                            resource_subresources_list[i]['subresource_uuid'] = element_uuid
                            break
                    for i in range(len(list_subresources_add)):
                        if list_subresources_add[i]['subresource_region'] == element_region:
                            list_subresources_add[i]['subresource_uuid'] = element_uuid
                            break
                app_log.info("Updated list of subresources: " +
                             str(resource_subresources_list))
                app_log.info("Finishing(L2): Updating the subresources list. Time: " +
                             str(time.time() - l2_rsc_update_time))
                resource_lmaster = LMaster.query.outerjoin(Parameter, Parameter.parameter_id == LMaster.parameter_id).outerjoin(
                    Resource, Resource.resource_id == Parameter.resource_id).filter(Resource.resource_id == data_from_db['resource_id']).one_or_none()
                app_log.info(
                    "Starting(L2): Adding the L2 resource master allocation pools.")
                l2_master_allocs_time = time.time()
                resource_l2allocation_pool_schema = L2AllocationPoolSchema()
                for object_alloc, alloc_list in new_allocated_pools.items():
                    app_log.info(str(object_alloc) + str(alloc_list))
                    for i in range(0, int(len(alloc_list)/2)+1, 2):
                        print(alloc_list[i])
                        print(alloc_list[i+1])
                        #app_log.info("Here we are selecting the allocation pools, the object is: " + str(object_alloc))
                        construct_alloc_pool = {
                            'l2allocationpool_first_ip': alloc_list[i],
                            'l2allocationpool_last_ip': alloc_list[i+1],
                            'l2allocationpool_site': object_alloc
                        }
                        new_l2allocation_pool_params = resource_l2allocation_pool_schema.load(
                            construct_alloc_pool, session=db.session).data
                        resource_lmaster.lmaster_l2allocationpools.append(
                            new_l2allocation_pool_params)
                db.session.commit()
                app_log.info(
                    "Finishing(L2): Adding the l2 resource master allocation pools. Time: " + str(time.time() - l2_master_allocs_time))

                # For the L2 resource type, create the interconnections to remote modules and add them to the resource schema
                app_log.info(
                    "Starting(L2): Using threads for local interconnection create request.")
                workers = len(list_subresources_add)
                start_interconnection_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for obj in list_subresources_add:
                        executor.submit(parallel_inters_creation_request, obj)
                end_interconnection_time = time.time()
                app_log.info('Finishing(L2): Using threads for local interconnection create request. Time: %s',
                             (end_interconnection_time - start_interconnection_time))

                app_log.info(
                    "Starting(L2): Updating the subresources and interconnections composing the resource.")
                l2_update_resinter_time = time.time()
                remote_l2_new_sites = []

                # Adding the subresources to the resource
                for obj in resource_subresources_list:
                    remote_l2_new_sites.append(
                        obj['subresource_region'] + "," + obj['subresource_uuid'])
                    if obj in list_subresources_add:
                        new_resource_subresources = SubResource(
                            subresource_region=obj['subresource_region'], subresource_uuid=obj['subresource_uuid'])
                        resource_update.resource_subresources.append(
                            new_resource_subresources)

                        to_delete_object = ""
                        for interco in local_interconnections_ids:
                            if interco[0] == obj['subresource_uuid']:
                                new_resource_interconnections = Interconnexion(
                                    interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                                resource_update.resource_interconnections.append(
                                    new_resource_interconnections)
                                to_delete_object = interco
                                break
                        if to_delete_object != "":
                            local_interconnections_ids.remove(to_delete_object)
                #app_log.info("The remote L2 objects are the following: " + str(remote_l2_new_sites))
                db.session.commit()
                app_log.info(
                    "Finishing(L2): Updating the subresources and interconnections composing the resource. Time: " + str(time.time() - l2_update_resinter_time))

                # Calling again the horizontal put to send the freshly updated list of subresources to remote sites
                app_log.info(
                    'Starting: Using threads for horizontal post-create request.')
                start_horizontal_time = time.time()
                workers = len(resource_subresources_list)
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for obj in resource_subresources_list:
                        executor.submit(parallel_horizontal_put_request, 'POST_CREATE',
                                        obj, "")
                end_horizontal_time = time.time()
                app_log.info('Finishing: Using threads for horizontal post-create request.. Time: %s',
                             (end_horizontal_time - start_horizontal_time))

        db.session.commit()
        end_time = time.time()
        app_log.info('Finishing time: %s', end_time)
        app_log.info('Total time spent: %s', end_time - start_time)
        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        abort(404, "Resource not found with global ID: {global_id}")

# Handler to delete a resource


def verticalDeleteResource(global_id):
    """
    This function responds to a DELETE request for /api/intersite-vertical/{global_id}
    with a single inter-site resource deletion

    :return:        deleted inter-site resource with global_id
    """
    app_log.info('Starting: Deleting a resource vertical request.')
    start_time = time.time()
    resource_remote_inter_endpoints = {}
    resource = Resource.query.filter(
        Resource.resource_global == global_id).one_or_none()
    if resource is not None:
        resource_schema = ResourceSchema()
        resource_data = resource_schema.dump(resource).data

        # A resource can only be deleted from the master instance
        if resource_data['resource_params'][0]['parameter_master'] == local_region_name:
            subresources_list_to_delete = resource_data['resource_subresources']
            # app_log.info(subresources_list_to_delete)
            interconnections_delete = resource_data['resource_interconnections']

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
                        for region_name in subresources_list_to_delete:
                            # app_log.info(region_name)
                            if endpoint['region'] == region_name['subresource_region']:
                                resource_remote_inter_endpoints[region_name['subresource_region']
                                                               ] = endpoint['url']
                                break

            # Sending remote inter-site delete requests to the distant nodes
            # If the resource is of L2 type, firstly we need to verify that remote created networks can be deleted
            delete_conditions = []

            def parallel_horizontal_validation(obj):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                if obj != local_region_name:
                    remote_inter_instance = resource_remote_inter_endpoints[obj].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + '7575/api/intersite-horizontal'
                    remote_resource = {
                        'subresource_cidr': '', 'resource_type': resource_data['resource_type'], 'global_id': global_id, 'verification_type': 'DELETE'}
                    # send horizontal verification request

                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json'}
                    r = requests.get(remote_inter_instance,
                                     params=remote_resource, headers=headers)
                    app_log.info(r.json()['result'])
                    delete_conditions.append(r.json()['result'])

            workers = len(subresources_list_to_delete)
            app_log.info(
                "Starting: Using threads for horizontal delete validation request.")
            threads_del_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for obj in subresources_list_to_delete:
                    executor.submit(
                        parallel_horizontal_validation, obj['subresource_region'])
            app_log.info(
                'Finishing: Using threads for horizontal delete validation request. Time: ' + str(time.time() - threads_del_time))

            if not all(rest == 'True' for rest in delete_conditions):
                abort(
                    404, "Resource can not be deleted, remote instances still have plugged ports")

            # Deleting the interconnections
            def parallel_interconnection_del(obj):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                try:
                    inter_del = net_adap.delete(
                        url='/v2.0/inter/interconnections/' + obj)
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter" + e.message)

            workers = len(interconnections_delete)
            app_log.info(
                "Starting: Using threads for local interconnection delete.")
            inter_del_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for obj in interconnections_delete:
                    executor.submit(
                        parallel_interconnection_del, obj['interconnexion_uuid'])
            app_log.info(
                'Finishing: Using threads for local interconnection delete. Time: ' + str(time.time() - inter_del_time))

            # Locally deleting the resource
            db.session.delete(resource)
            db.session.commit()

            def parallel_horizontal_delete_request(obj):
                app_log = logging.getLogger()
                starting_th_time = time.time()
                app_log.info('Starting thread at time:  %s', starting_th_time)
                remote_inter_instance = ''
                if obj['subresource_region'] != service_utils.get_region_name():
                    remote_inter_instance = resource_remote_inter_endpoints[obj['subresource_region']].strip(
                        '9696/')
                    remote_inter_instance = remote_inter_instance + \
                        '7575/api/intersite-horizontal/' + global_id
                    # send horizontal delete (resource_remote_inter_endpoints[obj])
                    headers = {'Accept': 'text/html'}
                    r = requests.delete(remote_inter_instance, headers=headers)

            workers = len(subresources_list_to_delete)
            app_log.info(
                "Starting: Using threads for horizontal delete request.")
            horizontal_del_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for obj in subresources_list_to_delete:
                    executor.submit(parallel_horizontal_delete_request, obj)
            app_log.info(
                'Finishing: Using threads for horizontal delete request. Time: ' + str(time.time() - horizontal_del_time))

            app_log.info(
                'Finishing: Deleting a resource vertical request. Time: ' + str(time.time() - start_time))

            return make_response("{id} successfully deleted".format(id=global_id), 200)

        else:
            app_log.info(
                'Finishing: Deleting a resource vertical request. This is not the master module.')
            abort(404, "This module is not the master for the resource with ID {id}, please address this request to {region} module".format(
                id=global_id, region=resource_data['resource_params'][0]['parameter_master']))
    else:
        app_log.info(
            'Finishing: Deleting a resource vertical request. There is a problem with the ID.')
        abort(404, "Resource with ID {id} not found".format(id=global_id))


# /intersite-horizontal
# Handler for inter-site resource creation request

def horizontalCreateResource(resource):
    """
    This function responds to a POST request for /api/intersite-horizontal/
    with a single inter-site resource creation

    :return:        freshly created inter-site resource
    """
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal resource creation request')
    app_log.info('Starting: Retrieving information for the resource.')
    local_region_name = service_utils.get_region_name()
    local_subresource = ''
    resource_name = resource.get("name", None)
    resource_type = resource.get("type", None)
    resource_params = ast.literal_eval(resource.get("params", None)[0])
    # app_log.info(resource_params)
    resource_global = resource.get("global", None)
    # resource_subresources = resource.get("subresources", None)
    resource_subresources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
        (item.split(',')) for item in resource.get("subresources", None)))
    resource_remote_auth_endpoints = {}
    local_interconnections_ids = []

    to_resource = {
        'resource_name': resource_name,
        'resource_type': resource_type,
        'resource_global': resource_global
    }

    # Extracting the local subresource if the resource is of type L3
    if resource_type == 'L3':
        for region, uuid in resource_subresources_list.items():
            if region == local_region_name:
                local_subresource = uuid
                break

    app_log.info('Finishing: Retrieving information for the resource. Time: ' +
                 str(time.time() - start_time))

    app_log.info('Starting: Contacting keystone catalog.')
    catalog_time = time.time()
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

    app_log.info('Finishing: Contacting keystone catalog. Time: ' +
                 str(time.time() - catalog_time))

    app_log.info('Starting: Saving Keystone information from catalog')
    keystone_time = time.time()
    for obj in catalog_endpoints:
        if obj['name'] == 'keystone':
            for endpoint in obj['endpoints']:
                for region_name in resource_subresources_list.keys():
                    if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                        resource_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                        break

    app_log.info('Finishing: Saving Keystone information from catalogue. Time: ' +
                 str(time.time() - keystone_time))

    if resource_type == 'L2':
        app_log.info('Starting(L2): Creating local network element')
        l2_netcreate_time = time.time()
        # Local network creation
        network_data = {'network': {
            'name': resource_name + '_net',
            'admin_state_up': True,
        }}
        try:
            network_inter = net_adap.post(
                url='/v2.0/networks', json=network_data)
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter: " + e.message)
        # Local subnetwork creation
        local_subresource = network_inter.json()['network']['id']
        subnetwork_data = {'subnet': {
            'name': resource_name + '_subnet',
            'network_id': local_subresource,
            'ip_version': 4,
            'cidr': resource_params['parameter_local_cidr'],
        }}

        try:
            subnetwork_inter = net_adap.post(
                url='/v2.0/subnets', json=subnetwork_data)
        except ClientException as e:
            app_log.info(
                "Exception when contacting the network adapter" + e.message)

        # Adding the local network identifier to the subresources list
        resource_subresources_list[local_region_name] = local_subresource

        app_log.info('Finishing(L2): Creating local network element. Time: ' +
                     str(time.time() - l2_netcreate_time))

    # calling the interconnection resource plugin to create the necessary objects
    def parallel_inters_creation_request(region, uuid):
        app_log = logging.getLogger()
        starting_th_time = time.time()
        app_log.info('Starting thread at time:  %s', starting_th_time)
        app_log.info(region + " " + uuid)
        if local_region_name != region:
            interconnection_data = {'interconnection': {
                'name': resource_name,
                'remote_keystone': resource_remote_auth_endpoints[region],
                'remote_region': region,
                'local_resource_id': local_subresource,
                'type': SERVICE_TYPE[resource_type],
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
                [uuid, inter_temp.json()['interconnection']['id']])

    # calling the interconnection resource plugin to create the necessary objects
    # At this point, this is done only for the L3 routing resource
    if resource_type == 'L3':
        workers = len(resource_subresources_list.keys())
        start_interconnection_time = time.time()
        app_log.info(
            "Starting: Using threads for local interconnection create request.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for region, uuid in resource_subresources_list.items():
                executor.submit(parallel_inters_creation_request, region, uuid)
        end_interconnection_time = time.time()
        app_log.info('Finishing: Using threads for local interconnection create request. Time: %s',
                     (end_interconnection_time - start_interconnection_time))

    app_log.info("Starting: Creating the resource schema")
    resource_schema_time = time.time()
    # Create a resource instance using the schema and the build resource
    resource_schema = ResourceSchema()
    new_resource = resource_schema.load(to_resource, session=db.session).data

    # Adding the subresources to the resource
    app_log.info('Starting: Adding the subresources to the resource')
    rsc_add_time = time.time()
    for region, uuid in resource_subresources_list.items():
        subresource = {
            'subresource_region': region,
            'subresource_uuid': uuid
        }
        resource_subresources_schema = SubResourcesSchema()
        new_resource_subresources = resource_subresources_schema.load(
            subresource, session=db.session).data
        new_resource.resource_subresources.append(new_resource_subresources)

        to_delete_object = ""
        for interco in local_interconnections_ids:
            if interco[0] == uuid:
                interconnexion = {
                    'interconnexion_uuid': interco[1],
                    'subresource': new_resource_subresources
                }
                new_resource_interconnections = Interconnexion(
                    interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                new_resource.resource_interconnections.append(
                    new_resource_interconnections)
                to_delete_object = interco
                break
        if to_delete_object != "":
            local_interconnections_ids.remove(to_delete_object)

    app_log.info('Finishing: Adding the subresources to the resource. Time: ' +
                 str(time.time() - rsc_add_time))

    # Adding the interconnections to the resource
    app_log.info(
        'Starting: Adding the interconnections to the resource schema.')
    inter_add_time = time.time()
    for element in local_interconnections_ids:
        interconnexion = {
            'interconnexion_uuid': element
        }
        resource_interconnections_schema = InterconnectionsSchema()
        new_resource_interconnections = resource_interconnections_schema.load(
            interconnexion, session=db.session).data
        new_resource.resource_interconnections.append(
            new_resource_interconnections)
    app_log.info('Finishing: Adding the interconnections to the resource schema. Time: ' +
                 str(time.time() - inter_add_time))
    # Adding the parameters to the resource

    if(resource_type == 'L3'):
        app_log.info('(L3) Starting: Retrieving subnetwork CIDR.')
        l3_cidr_time = time.time()
        network_temp = net_adap.get(
            '/v2.0/networks/' + local_subresource).json()['network']
        subnet_id = network_temp['subnets'][0]

        subnetwork_temp = net_adap.get('/v2.0/subnets/' + subnet_id).json()
        subnet = subnetwork_temp['subnet']
        resource_params['parameter_local_cidr'] = subnet['cidr']

        app_log.info('(L3) Finishing: Retrieving subnetwork CIDR. Time: ' +
                     str(time.time() - l3_cidr_time))

    # Since every kind of resource has a local subresource, we store it without the loop
    resource_params['parameter_local_subresource'] = local_subresource

    resource_params_schema = ParamsSchema()
    new_resource_params = resource_params_schema.load(
        resource_params, session=db.session).data
    new_resource.resource_params.append(new_resource_params)

    # Add the resource to the database
    db.session.add(new_resource)
    db.session.commit()

    answer_resource = {'global_id': resource_global, 'type': resource_type,
                      'local_region': local_region_name, 'local_subresource': local_subresource}

    app_log.info("Finishing: Creating the resource schema. Time: " +
                 str(time.time() - resource_schema_time))

    # If the resource is from L2 type, do the local DHCP change
    # This is done here because if doing this at the POST subnet request will take one additional IP address for the DHCP resource, if instead we do this now, the DHCP resource will be by default assigned to the second available IP address of the network
    if resource_type == 'L2':
        app_log.info(
            "(L2) Starting: Updating the DHCP pool ranges for the local deployment.")
        dhcp_upd_time = time.time()
        local_allocation_polls = resource_params['parameter_allocation_pool'].split(
            ';')
        local_allocation_polls.pop()
        local_allocs_list = []
        for element in local_allocation_polls:
            alloc_struct = {'start': element.split("-", 1)[0], 'end': element.split("-", 1)[1]
                            }
            local_allocs_list.append(alloc_struct)
        body = {'subnet': {'allocation_pools': local_allocs_list}}
        network_temp = net_adap.get(
            '/v2.0/networks/' + local_subresource).json()['network']
        subnet_id = network_temp['subnets'][0]

        app_log.info(str(subnet_id))

        dhcp_change = net_adap.put(url='/v2.0/subnets/'+subnet_id, json=body)
        app_log.info(
            "(L2) Finishing: Updating the DHCP pool ranges for the local deployment. Time: " + str(time.time() - dhcp_upd_time))

    end_time = time.time()
    app_log.info('Finishing time: %s', end_time)
    app_log.info('Total time spent: %s', end_time - start_time)

    return answer_resource, 201

# Handler to update a resource horizontal


def horizontalUpdateResource(global_id, resource):
    """
    This function responds to a PUT request for /api/intersite-horizontal/{global_id}
    with a single inter-site resource modification

    :return:        freshly modified inter-site resource with global_id
    """
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal update request')
    app_log.info('Starting: Validating resource information.')
    resource_update = Resource.query.filter(
        Resource.resource_global == global_id).one_or_none()

    # Did we find a resource?
    if resource_update is not None:
        app_log.info('Finishing: Validating resource information. Time: ' +
                     str(time.time() - start_time))
        app_log.info(
            'Starting: extracting information from the db and the user information.')
        resource_info_time = time.time()
        resource_remote_auth_endpoints = {}

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

        resource_schema_temp = ResourceSchema()
        data_from_db = resource_schema_temp.dump(resource_update).data
        resource_type = data_from_db['resource_type']
        resource_subresources_db_objects = data_from_db['resource_subresources']
        resource_subresources_ids_db_list = []
        for element in resource_subresources_db_objects:
            resource_subresources_ids_db_list.append(element['subresource_uuid'])
        to_resource_subresources_list = dict((region.strip(), uuid.strip()) for region, uuid in (
            (item.split(',')) for item in resource.get("subresources", None)))

        app_log.info('The list of subresources sent by the Master module is: ' +
                     str(to_resource_subresources_list))
        local_subresource = data_from_db['resource_params'][0]['parameter_local_subresource']
        app_log.info(
            'Finishing: extracting information from the db and the user information. Time: ' + str(time.time() - resource_info_time))

        # Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalogue
        app_log.info('Starting: Saving Keystone information from catalog')
        catalog_time = time.time()
        for obj in catalog_endpoints:
            if obj['name'] == 'keystone':
                for endpoint in obj['endpoints']:
                    for region_name in to_resource_subresources_list.keys():
                        if endpoint['region'] == region_name and endpoint['interface'] == 'public':
                            resource_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
                            break
        app_log.info('Finishing: Saving Keystone information from catalog. Time: ' +
                     str(time.time() - catalog_time))

        local_interconnections_ids = []

        def parallel_inters_creation_request(region, uuid):
            app_log = logging.getLogger()
            starting_th_time = time.time()
            app_log.info(
                'Starting local interconnection creation thread at time:  %s', starting_th_time)
            if local_region_name != region:
                interconnection_data = {'interconnection': {
                    'name': data_from_db['resource_name'],
                    'remote_keystone': resource_remote_auth_endpoints[region],
                    'remote_region': region,
                    'local_resource_id': local_subresource,
                    'type': SERVICE_TYPE[data_from_db['resource_type']],
                    'remote_resource_id': uuid,
                }}
                #app_log.info('The information of this interconnection is: ' + str(interconnection_data))
                try:
                    inter_temp = net_adap.post(
                        url='/v2.0/inter/interconnections/', json=interconnection_data)
                except ClientException as e:
                    app_log.info(
                        "Exception when contacting the network adapter: " + e.message)

                local_interconnections_ids.append(
                    [uuid, inter_temp.json()['interconnection']['id']])

        if resource.get("post_create_refresh") == 'True':
            app_log.info(
                "Starting: Updating the resource with post create refresh condition.")
            post_create_time = time.time()
            # Using the already parsed information to create the interconnections
            workers = len(to_resource_subresources_list.keys())
            start_interconnection_time = time.time()
            app_log.info(
                "Starting: Using threads for local interconnection create request.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                for region, uuid in to_resource_subresources_list.items():
                    inter_obj_test = Interconnexion.query.outerjoin(Resource, Resource.resource_id == Interconnexion.resource_id).outerjoin(
                        SubResource, SubResource.subresource_id == Interconnexion.subresource_id).filter(Interconnexion.resource_id == data_from_db['resource_id'], SubResource.subresource_uuid == uuid).one_or_none()
                    if inter_obj_test is None:
                        executor.submit(
                            parallel_inters_creation_request, region, uuid)
            end_interconnection_time = time.time()
            app_log.info('Finishing: Using threads for local interconnection create request. Time: %s',
                         (end_interconnection_time - start_interconnection_time))

            app_log.info('Starting: Updating subresources and interconnections.')
            rsc_upd_time = time.time()
            # Taking the information of the resource subresources list to save it into the subresource schema
            for update_subresource_region, update_subresource_uuid in to_resource_subresources_list.items():

                res_update = SubResource.query.outerjoin(Resource, Resource.resource_id == SubResource.resource_id).filter(
                    SubResource.resource_id == data_from_db['resource_id'], SubResource.subresource_region == update_subresource_region).one_or_none()
                res_update.subresource_uuid = update_subresource_uuid

                res_update_schema = SubResourcesSchema()
                data_from_res = res_update_schema.dump(res_update).data
                app_log.info(data_from_res)

                to_delete_object = ""
                for interco in local_interconnections_ids:
                    if interco[0] == update_subresource_uuid:
                        interconnexion = {
                            'interconnexion_uuid': interco[1],
                            'subresource': res_update
                        }
                        new_resource_interconnections = Interconnexion(
                            interconnexion_uuid=str(interco[1]), subresource=res_update)
                        resource_update.resource_interconnections.append(
                            new_resource_interconnections)
                        to_delete_object = interco
                        break
                if to_delete_object != "":
                    local_interconnections_ids.remove(to_delete_object)

            app_log.info(to_resource_subresources_list)
            app_log.info('Finishing: Updating subresources and interconnections. Time:' +
                         str(time.time() - rsc_upd_time))
            app_log.info(
                "Finishing: Updating the resource with post create refresh condition. Time: " + str(time.time() - post_create_time))

            db.session.commit()

        # If the post_create_refresh condition is false, then we proceed to update the resource in the default way

        if resource.get("post_create_refresh") == 'False':
            app_log.info(
                "Starting: Updating the resource with default behavior.")
            default_time = time.time()
            app_log.info(
                'Starting: extracting information from the db and the user information.')
            resource_subresources_list_user = []
            new_params = resource.get("params", None)
            # app_log.info(str(new_params))

            for region, uuid in to_resource_subresources_list.items():
                resource_subresources_list_user.append(
                    {'subresource_uuid': uuid, 'subresource_region': region})

            resource_subresources_list_db = []
            for element in data_from_db['resource_subresources']:
                resource_subresources_list_db.append(
                    {'subresource_uuid': element['subresource_uuid'], 'subresource_region': element['subresource_region']})

            list_subresources_remove = copy.deepcopy(resource_subresources_list_db)
            list_subresources_add = []

            for subresource_component in resource_subresources_list_user:
                contidion_temp = True
                for subresource_component_2 in resource_subresources_list_db:
                    if subresource_component == subresource_component_2:
                        # app_log.info(subresource_component)
                        list_subresources_remove.remove(subresource_component_2)
                        contidion_temp = False
                        break
                if(contidion_temp == True):
                    list_subresources_add.append(subresource_component)

            app_log.info('Actual list of subresources: ' +
                         str(resource_subresources_list_db))
            if list_subresources_add != []:
                app_log.info('SubResources to add: ' + str(list_subresources_add))
            if list_subresources_remove != []:
                app_log.info('SubResources to delete: ' +
                             str(list_subresources_remove))
            search_local_subresource_delete = False

            if(list_subresources_remove == [] and list_subresources_add == []):
                abort(404, "No subresources are added/deleted")

            for element in list_subresources_remove:
                if(local_region_name in element['subresource_region']):
                    search_local_subresource_delete = True

            app_log.info(
                'Finishing: extracting information from the db and the user information. Time: ' + str(time.time() - start_time))

            # If one of the subresource is the local one, we only need to delete the entire resource locally
            if(search_local_subresource_delete):

                def parallel_inters_delete_request(inter_delete):
                    app_log = logging.getLogger()
                    starting_th_time = time.time()
                    app_log.info(
                        'Starting interconnection delete thread at time:  %s', starting_th_time)
                    try:
                        inter_del = net_adap.delete(
                            '/v2.0/inter/interconnections/' + inter_delete)
                    except ClientException as e:
                        app_log.info(
                            "Exception when contacting the network adapter: " + e.message)

                # Once we do the request to Neutron, we do the query to delete the interconnexion locally
                app_log.info(
                    'Starting: Deleting the local subresource from the resource')
                inter_del_time = time.time()
                interconnections_delete = data_from_db['resource_interconnections']
                app_log.info(
                    'Starting: Deleting local interconnections and subresources.')
                workers = len(interconnections_delete)
                start_interconnection_delete_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    for interco in interconnections_delete:
                        executor.submit(
                            parallel_inters_delete_request, interco['interconnexion_uuid'])
                end_interconnection_delete_time = time.time()
                app_log.info('Finishing: Deleting local interconnections and subresources. Time: %s',
                             (end_interconnection_delete_time - start_interconnection_delete_time))
                if data_from_db['resource_type'] == 'L2':
                    local_subresource = data_from_db['resource_params'][0]['parameter_local_subresource']
                    network_del = net_adap.delete(
                        url='/v2.0/networks/' + local_subresource)
                db.session.delete(resource_update)
                db.session.commit()

                end_time = time.time()
                app_log.info(
                    'Finishing: Deleting the local subresource from the resource. Time: ' + str(time.time() - inter_del_time))
                app_log.info(
                    "Finishing: Updating the resource with default behavior. Time: " + str(time.time() - default_time))
                app_log.info('Finishing time: %s', end_time)
                app_log.info('Total time spent: %s', end_time - start_time)
                return make_response("{id} successfully updated".format(id=global_id), 200)

            else:
                if (list_subresources_remove):
                    # Do this if the local subresource is not being deleted from the resource
                    def parallel_inters_delete_request(subresource_delete):
                        app_log = logging.getLogger()
                        starting_th_time = time.time()
                        app_log.info(
                            'Starting interconnection delete thread at time:  %s', starting_th_time)
                        interconnection_db_delete = Interconnexion.query.outerjoin(Resource, Interconnexion.resource_id == Resource.resource_id).outerjoin(SubResource, SubResource.resource_id == Resource.resource_id).filter(
                            SubResource.subresource_uuid == subresource_delete['subresource_uuid']).filter(Interconnexion.resource_id == data_from_db['resource_id']).filter(Interconnexion.subresource_id == SubResource.subresource_id).one_or_none()
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
                        # The same procedure is applied to the subresource to be deleted locally
                        subresource_to_delete = SubResource.query.outerjoin(Resource, SubResource.resource_id == Resource.resource_id).filter(
                            Resource.resource_id == data_from_db['resource_id']).filter(SubResource.subresource_uuid == subresource_delete['subresource_uuid']).one_or_none()
                        resource_subresources_list_db.remove(subresource_delete)
                        db.session.delete(subresource_to_delete)
                        db.session.commit()

                    app_log.info(list_subresources_remove)
                    app_log.info(
                        'Starting: Deleting local interconnections and subresources.')
                    workers = len(list_subresources_remove)
                    start_interconnection_delete_time = time.time()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                        for subresource in list_subresources_remove:
                            executor.submit(
                                parallel_inters_delete_request, subresource)
                    end_interconnection_delete_time = time.time()
                    app_log.info('Finishing: Deleting local interconnections and subresources. Time: %s',
                                 (end_interconnection_delete_time - start_interconnection_delete_time))

                app_log.info(
                    'Starting: Saving Neutron and Keystone information from catalogue.')
                keystone_cat_time = time.time()
                resource_remote_auth_endpoints = {}
                resource_remote_inter_endpoints = {}
                resource_subresources_list_search = copy.deepcopy(
                    list_subresources_add)
                resource_subresources_list_db_search = copy.deepcopy(
                    resource_subresources_list_db)

                for obj in catalog_endpoints:
                    if obj['name'] == 'neutron':
                        for endpoint in obj['endpoints']:
                            # Storing information of Neutrons of actual subresource list, subresources to add and subresources to delete
                            for existing_subresource in resource_subresources_list_db:
                                if endpoint['region'] == existing_subresource['subresource_region']:
                                    resource_remote_inter_endpoints[existing_subresource['subresource_region']
                                                                   ] = endpoint['url']
                                    resource_subresources_list_db_search.remove(
                                        existing_subresource)
                                    break
                            for subresource_element in list_subresources_add:
                                if endpoint['region'] == subresource_element['subresource_region']:
                                    resource_remote_inter_endpoints[subresource_element['subresource_region']
                                                                   ] = endpoint['url']
                                    resource_subresources_list_search.remove(
                                        subresource_element)
                                    break
                            for subresource_delete in list_subresources_remove:
                                if endpoint['region'] == subresource_delete['subresource_region']:
                                    resource_remote_inter_endpoints[subresource_delete['subresource_region']
                                                                   ] = endpoint['url']
                                    break
                    if obj['name'] == 'keystone':
                        # Storing information of Keystone of actual subresource list, subresources to add and subresources to delete
                        for endpoint in obj['endpoints']:
                            for existing_subresource in resource_subresources_list_db:
                                if endpoint['region'] == existing_subresource['subresource_region']:
                                    resource_remote_auth_endpoints[existing_subresource['subresource_region']
                                                                  ] = endpoint['url']+'/v3'
                                    break
                            for subresource_element in list_subresources_add:
                                if endpoint['region'] == subresource_element['subresource_region'] and endpoint['interface'] == 'public':
                                    resource_remote_auth_endpoints[subresource_element['subresource_region']
                                                                  ] = endpoint['url']+'/v3'
                                    break
                            for subresource_delete in list_subresources_remove:
                                if endpoint['region'] == subresource_delete['subresource_region']:
                                    resource_remote_auth_endpoints[subresource_delete['subresource_region']
                                                                  ] = endpoint['url'] + '/v3'
                                    break

                if bool(resource_subresources_list_search):
                    abort(404, "ERROR: Regions " + (" ".join(str(key['subresource_region'])
                                                             for key in resource_subresources_list_search)) + " are not found")

                if bool(resource_subresources_list_db_search):
                    abort(404, "ERROR: Regions " + (" ".join(str(key['subresource_region'])
                                                             for key in resource_subresources_list_db_search)) + " are not found")

                app_log.info(
                    'Finishing: Saving Neutron and Keystone information from catalogue. Time: ' + str(time.time() - keystone_cat_time))

                if(list_subresources_add):
                    def parallel_inters_creation_request(obj):
                        app_log = logging.getLogger()
                        starting_th_time = time.time()
                        app_log.info(
                            'Starting thread at time:  %s', starting_th_time)
                        if local_region_name != obj["subresource_region"]:
                            interconnection_data = {'interconnection': {
                                'name': data_from_db["resource_name"],
                                'remote_keystone': resource_remote_auth_endpoints[obj["subresource_region"]],
                                'remote_region': obj["subresource_region"],
                                'local_resource_id': local_subresource,
                                'type': SERVICE_TYPE[resource_type],
                                'remote_resource_id': obj["subresource_uuid"],
                            }}
                            app_log.info(
                                'Interconnection info for this thread: ' + str(interconnection_data))
                            try:
                                inter_temp = net_adap.post(
                                    url='/v2.0/inter/interconnections/', json=interconnection_data)
                            except ClientException as e:
                                app_log.info(
                                    "Exception when contacting the network adapter: " + e.message)

                            local_interconnections_ids.append([obj["subresource_uuid"],
                                                               inter_temp.json()['interconnection']['id']])

                    if resource_type == 'L3':
                        # Calling the interconnection resource plugin to create the necessary objects
                        app_log.info(
                            "Starting(L3): Using threads for local interconnection create request.")
                        workers = len(list_subresources_add)
                        start_interconnection_time = time.time()
                        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                            for obj in list_subresources_add:
                                executor.submit(
                                    parallel_inters_creation_request, obj)
                        end_interconnection_time = time.time()
                        app_log.info('Finishing(L3): Using threads for local interconnection create request. Time: %s',
                                     (end_interconnection_time - start_interconnection_time))

                    app_log.info("Starting: Updating the resource schema")
                    schema_upd_time = time.time()
                    # Adding the subresources to the resource
                    app_log.info(
                        "Starting(L3): Adding the subresources and interconnections to the resource.")
                    for element in list_subresources_add:
                        subresource = {
                            'subresource_region': element["subresource_region"],
                            'subresource_uuid': element["subresource_uuid"]
                        }
                        resource_subresources_schema = SubResourcesSchema()
                        new_resource_subresources = resource_subresources_schema.load(
                            subresource, session=db.session).data
                        resource_update.resource_subresources.append(
                            new_resource_subresources)

                        to_delete_object = ""
                        for interco in local_interconnections_ids:
                            if interco[0] == element["subresource_uuid"]:
                                interconnexion = {
                                    'interconnexion_uuid': interco[1],
                                    'subresource': new_resource_subresources
                                }
                                new_resource_interconnections = Interconnexion(
                                    interconnexion_uuid=str(interco[1]), subresource=new_resource_subresources)
                                resource_update.resource_interconnections.append(
                                    new_resource_interconnections)
                                to_delete_object = interco
                                break
                        if to_delete_object != "":
                            local_interconnections_ids.remove(to_delete_object)
                    app_log.info(
                        "Finishing: Adding the subresources and interconnections to the resource. Time: " + str(time.time() - schema_upd_time))
                db.session.commit()
                app_log.info("Finishing: Updating the resource schema. Time: " +
                             str(time.time() - schema_upd_time))

            app_log.info(
                "Finishing: Updating the resource with default behavior. Time: " + str(time.time() - default_time))

        end_time = time.time()
        app_log.info('Finishing time: %s', end_time)
        app_log.info('Total time spent: %s', end_time - start_time)
        return make_response("{id} successfully updated".format(id=global_id), 200)

    else:
        app_log.info('Finishing: Validating resource information.')
        abort(404, "Resource with ID {id} not found".format(id=global_id))


# Handler to delete a resource horizontal


def horizontalDeleteResource(global_id):
    """
    This function responds to a DELETE request for /api/intersite-horizontal/{global_id}
    with a single inter-site resource deletion

    :return:        delete inter-site resource with global_id
    """
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal delete request')
    resource_remote_inter_endpoints = {}
    resource = Resource.query.filter(
        Resource.resource_global == global_id).one_or_none()
    if resource is not None:
        resource_schema = ResourceSchema()
        resource_data = resource_schema.dump(resource).data
        subresources_list_to_delete = resource_data['resource_subresources']
        # app_log.info(subresources_list_to_delete)
        interconnections_delete = resource_data['resource_interconnections']

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

        if resource_data['resource_type'] == 'L2':
            local_subresource = resource_data['resource_params'][0]['parameter_local_subresource']
            network_del = net_adap.delete(
                url='/v2.0/networks/' + local_subresource)

        db.session.delete(resource)
        db.session.commit()
        app_log.info('Finishing horizontal delete request. Time: ' +
                     str(time.time() - start_time))
        return make_response("{id} successfully deleted".format(id=global_id), 200)

    else:
        abort(404, "Resource with ID {id} not found".format(id=global_id))


def horizontalReadParameters(global_id):
    """
    This function responds to a GET request for /api/intersite-horizontal/{global_id}
    with the parameters information of an inter-site resource

    :return:        parameters information of an inter-site resource with global_id
    """
    start_time = time.time()
    app_log.info('Starting: horizontal read parameters request')
    resource = Resource.query.filter(Resource.resource_global == global_id).outerjoin(
        SubResource).outerjoin(Interconnexion).one_or_none()
    if resource is not None:
        resource_schema = ResourceSchema()
        data = resource_schema.dump(resource).data['resource_params']
        app_log.info('Finishing: horizontal read parameters request. Time: ' +
                     str(time.time() - start_time))
        return data, 200

    else:
        app_log.info('Finishing: horizontal read parameters request. Time: ' +
                     str(time.time() - start_time))
        abort(404, "Resource with ID {id} not found".format(id=id))


def horizontalVerification(subresource_cidr, resource_type, global_id, verification_type):
    """
    This function responds to a GET request for /api/intersite-horizontal/
    with a boolean along with context information

    :return:        answer to verification request 'true' or 'false' with information for context
    """
    start_time = time.time()
    app_log.info('Starting time: %s', start_time)
    app_log.info('Starting a new horizontal verification request')
    # Depending on the verification type, the answer will answer two different questions: Can you create your resource side? Can you delete the resource at your side? By default the answer will the True until something we found prouves contrary
    answer = {'condition': 'True', 'information': ''}
    if verification_type == 'CREATE':
        resources = Resource.query.outerjoin(Parameter, Resource.resource_id == Parameter.resource_id).filter(
            Resource.resource_type == resource_type, Parameter.parameter_local_cidr == subresource_cidr).all()
        if resources is not None:
            # Serialize the data for the response
            resource_schema = ResourceSchema(many=True)
            data = resource_schema.dump(resources).data
            if data != []:
                answer['condition'], answer['information'] = 'False', 'The CIDR is already being used by other resource'

    if verification_type == 'DELETE':
        resource = Resource.query.filter(Resource.resource_global == global_id).outerjoin(
            SubResource).outerjoin(Interconnexion).one_or_none()
        if resource is not None:
            resource_schema = ResourceSchema()
            resource_data = resource_schema.dump(resource).data
            local_subresource = resource_data['resource_params'][0]['parameter_local_subresource']

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
                'network_id': local_subresource, 'device_owner': 'compute:nova'}

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


def checkExistingResource(subresource_list):
    """
    This function querries the local database for a similar resource composed
    by the given list of sub resources

    :return:        boolean
    """
    resources = Resource.query.all()
    resource_schema = ResourceSchema(many=True)
    data = resource_schema.dump(resources).data
    search_list_dict = {}
    for element in data:
        temp_dict = {}
        for next_subresource in element['resource_subresources']:
            temp_dict[next_subresource['subresource_region']
                      ] = next_subresource['subresource_uuid']
        search_list_dict[element['resource_global']] = temp_dict
    for key, value in search_list_dict.items():
        # app_log.info(key)
        if(value == subresource_list):
            return True, key
    return False, ''


def createRandomGlobalId(stringLength=28):
    """
    This function creates a random Global identifier composed of four concateneted strings

    :return:        global identifier
    """
    lettersAndDigits = string.ascii_lowercase[0:5] + string.digits
    result = ''.join(random.choice(lettersAndDigits) for i in range(8))
    result1 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result2 = ''.join(random.choice(lettersAndDigits) for i in range(4))
    result3 = ''.join(random.choice(lettersAndDigits) for i in range(12))
    global_random_id = result + '-' + result1 + '-' + result2 + '-'+result3

    return global_random_id

# DEPRECATED Since the recomposition of cidrs allocation pools has been left aside, this is no longer usefull

def reorderCidrs(list_subresources):

    size = len(list_subresources)
    for i in range(size):
        for j in range(size):
            first_elem = ipaddress.IPv4Address(
                list_subresources[i]['param'].split('-')[0])
            second_elem = ipaddress.IPv4Address(
                list_subresources[j]['param'].split('-')[0])

            if first_elem < second_elem:
                temp = list_subresources[i]
                list_subresources[i] = list_subresources[j]
                list_subresources[j] = temp
