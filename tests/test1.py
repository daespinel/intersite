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
import requests
import logging
import ast
from flask.logging import default_handler
import threading
import concurrent.futures
from threading import Lock

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

local_region_url = service_utils.get_local_keystone()
local_region_name = service_utils.get_region_name()

auth = service_utils.get_auth_object(local_region_url)
sess = service_utils.get_session_object(auth)

# Authenticate
auth.get_access(sess)
auth_ref = auth.auth_ref

CIDRs = []
parameter_local_cidr_temp = []

parallel_subnetwork_request("RegionOne", "3b8360e6-e29a-4063-a8bc-7bbd0785d08b")
print(CIDRs)
print(parameter_local_cidr_temp)