#!/usr/bin/python3
from neutronclient.common import exceptions as neutronclient_exc
from random import seed
from random import randint
from service import Service, ServiceSchema, Resource, Interconnexion, Parameter, ServiceParamssSchema, ServiceResourcesSchema, ServiceInterconnectionsSchema
from config import db
import common.utils as service_utils
import copy
import math
import json
import ipaddress
import itertools
import string
import random
import requests

SERVICE_TYPE = {'L2': 'network_l2', 'L3': 'network_l3'}

# Data used for the first connection to the keystone catalog
local_region_name = service_utils.get_region_name()
local_region_url = service_utils.get_local_keystone()

neutron_endpoints = []

# Saving info for Neutron and Keystone endpoints to be contacted based on keystone catalog
catalog_endpoints = service_utils.get_keystone_catalog(local_region_url)
for obj in catalog_endpoints:
    if obj['name'] == 'neutron':
        for endpoint in obj['endpoints']:
            neutron_endpoints.append(endpoint['url'])

print(neutron_endpoints)


    #if obj['name'] == 'keystone':
    #    for endpoint in obj['endpoints']:
    #        for region_name in service_resources_list.keys():
    #            if endpoint['region'] == region_name and endpoint['interface'] == 'public':
    #                service_remote_auth_endpoints[region_name] = endpoint['url']+'/v3'
    #                break