import random
import datetime
import copy
import math
import ipaddress
from random import seed
from operator import itemgetter
from random import randint
import time
from datetime import datetime

def is_allocated(ip_address,pool_dicts_list):
    condition = -1
    initial = ''
    end = ''
    for pool_dict in pool_dicts_list:
        initial = ipaddress.IPv4Address(pool_dict['l2allocationpool_first_ip'])
        end = ipaddress.IPv4Address(pool_dict['l2allocationpool_last_ip'])
        if ip_address >= initial and ip_address <= end:
            print('address inside allocation pool')
            condition = 1
            break
    return condition, initial, end

print("Starting(L2): L2 CIDR allocation pool split.")
cidr = ipaddress.ip_network('10.0.0.0/24')
parameter_local_cidr = '10.0.0.0/24'
list_resources_add = [{'resource_region':'RegionTwo','resource_uuid':''},{'resource_region':'RegionThree','resource_uuid':''}]
main_cidr = parameter_local_cidr
main_cidr_base = (main_cidr.split("/", 1)[0])
main_cidr_prefix = (main_cidr.split("/", 1)[1])
cidr_ranges = []
# Available IPs are without the network address, the broadcast address, and the first address (for globally known DHCP)
ips_cidr_total = 2**(32-int(main_cidr_prefix))-3
ips_cidr_available = copy.deepcopy(ips_cidr_total)
already_used_pools = []
already_used_pools.append(
    {'l2allocationpool_first_ip' : '10.0.0.4',
    'l2allocationpool_last_ip' : '10.0.0.65',
    'l2allocationpool_site' : 'RegionOne'
    }
)
#already_used_pools.append(
#    {'l2allocationpool_first_ip' : '10.0.0.110',
#    'l2allocationpool_last_ip' : '10.0.0.128',
#    'l2allocationpool_site' : 'RegionFour'
#    }
#)
#already_used_pools.append(
#    {'l2allocationpool_first_ip' : '10.0.0.70',
#    'l2allocationpool_last_ip' : '10.0.0.100',
#    'l2allocationpool_site' : 'RegionFive'
#    }
#)

sorted_already_used_pools = sorted(already_used_pools, key=lambda k:int(ipaddress.IPv4Address(k['l2allocationpool_first_ip'])))
#sorted_already_used_pools = sorted(already_used_pools, key=itemgetter('l2allocationpool_first_ip'))
print(sorted_already_used_pools)
used_ips = 61
ips_cidr_available = ips_cidr_available - used_ips
print('Total available IPs: ' + str(ips_cidr_available))
# If no more addresses are available, we can not proceed
host_per_site = math.floor(
    ips_cidr_available/len(list_resources_add))

host_per_site = math.floor(host_per_site/2)
print("CIDR: " + str(main_cidr) + ", total available IPs: " + str(ips_cidr_total) + ", real available: " + str(ips_cidr_available) +
                " , new number of sites: " + str(len(list_resources_add)) + " , IPs per site:" + str(host_per_site))
base_index = 3
index = 0
host_per_site_count = 0
new_allocated_pools = {}

for new_resource in list_resources_add:
    new_allocated_pools[new_resource['resource_region']] = []
    host_per_site_count = 0
    host_count_temp = 0
    new_initial_ip = ''
    new_final_ip = ''
    while host_per_site_count < host_per_site and base_index <= ips_cidr_total+1:
        ip_to_inspect = cidr[base_index]
        print(ip_to_inspect)
        condition_granted, first_used, last_used = is_allocated(ip_to_inspect,sorted_already_used_pools)
        # If the condition is 1, it means that the analyzed IP lies in an already allocated pool
        if condition_granted == 1:
            difference = int(last_used) - int(ip_to_inspect)
            base_index = base_index + difference + 1
            if host_count_temp != 0:
                print('saving the information of IPs')
                new_allocated_pools[new_resource['resource_region']].extend([str(new_initial_ip), str(new_final_ip)])
            host_count_temp = 0
        else:
            base_index = base_index + 1 
            host_per_site_count = host_per_site_count + 1
            print('host per site count ' + str(host_per_site_count))
            if new_initial_ip == '' or host_count_temp == 0:
                new_initial_ip = ip_to_inspect
            host_count_temp = host_count_temp + 1
            new_final_ip = ip_to_inspect
            print('host count temp ' + str(host_count_temp))
            if host_count_temp == host_per_site:
                print('saving the information of IPs')
                new_allocated_pools[new_resource['resource_region']].extend([str(new_initial_ip), str(new_final_ip)])
            else:
                if host_per_site_count == host_per_site:
                    print('saving the information of IPs')
                    new_allocated_pools[new_resource['resource_region']].extend([str(new_initial_ip), str(new_final_ip)])
    print('new initial ip: ' + str(new_initial_ip))
    print('new final ip: ' + str(new_final_ip))
    index = index + 1
    
print(new_allocated_pools)

for object_alloc,alloc_list in new_allocated_pools.items():
    print(object_alloc + str(alloc_list))
    for i in range(0, int(len(alloc_list)/2)+1,2 ):
        print(alloc_list[i])
        print(alloc_list[i+1])
    

#app_log.info('Next ranges will be used:')
# for element in cidr_ranges:
#    app_log.info(element)

print("Finishing(L2): L2 CIDR allocation pool split.")

service_params={}
service_params['parameter_allocation_pool']='10.0.0.49-10.0.0.64;10.0.0.70-10.0.0.71;'

splitted_allocs = service_params['parameter_allocation_pool'].split(';')
splitted_allocs.pop()
print(splitted_allocs)