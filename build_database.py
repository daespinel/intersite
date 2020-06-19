import os
from config import db
from service import Resource, SubResource, Interconnexion, Parameter, L2AllocationPool, LMaster

# Data to initialize database with
local_region_name = "RegionOne"

RESOURCES = [
    {
        "name": "Service1",
        "type": "L2",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": ["10.0.0.3-10.0.0.108", "10.0.0.0/24", "v4"],
        "subresources": [("id589", "RegionOne")],
        "interconnections": ["z1"]

    },
    {
        "name": "Service2",
        "type": "L3",
        "global": "02b98df2-03a8-974c-d2569f7e44e0",
        "params": ["", "20.0.0.0/24", "v4"],
        "subresources": [("id10", "RegionOne"), ("id15", "RegionTen"), ("id16", "RegionSixTen")],
        "interconnections": ["Y1", "Y2"]
    },
    {
        "name": "Service3",
        "type": "L3",
        "global": "220ac9d3-58c9-d640-0369b6b58c71",
        "params": ["", "30.0.0.0/24", "v4"],
        "subresources": [("id21", "RegionOne"), ("id24", "RegionFour"), ("id25", "RegionFive"), ("id28", "RegionTwentyEight")],
        "interconnections": ["x1", "x2", "x3"]
    }
]

RESOURCES1 = [
    {
        "name": "Service1",
        "type": "L2",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": ["10.0.0.3-10.0.0.108", "10.0.0.0/24","3b8360e6-e29a-4063-a8bc-7bbd0785d08b", "v4", "RegionOne", "http://192.168.57.6:7575"],
        "l2allocs": [{"first_ip": "10.0.0.3", "last_ip": "10.0.0.108", "site": "RegionOne"}, {"first_ip": "10.0.0.109", "last_ip": "10.0.0.153", "site": "RegionTwo"}, {"first_ip": "10.0.0.110", "last_ip": "10.0.0.253", "site": "free"}],
        "subresources": [("ads360e6-e29a-4063-a8bc-7bbd0785d08b", "RegionOne",""), ("829c3a52-c7de-4430-b721-fb85b7dcf60f", "RegionTwo","z1-523513-561561")]

    }
]

RESOURCES2 = [
    {
        "name": "Service1",
        "type": "L2",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": ["10.0.0.3-10.0.0.108", "10.0.0.0/24", "v4", "RegionTwo", "http://192.168.57.6:7575"],
        "subresources": [("3b8360e6-e29a-4063-a8bc-7bbd0785d08b", "RegionOne"), ("829c3a52-c7de-4430-b721-fb85b7dcf60f", "RegionTwo")],
        "interconnections": ["z1"]

    }
]

RESOURCES3 = [
    {
        "name": "Service1",
        "type": "L3",
        "global": "713ebc06-57cc-ba54-8886571b1489",
        "params": ["", "10.0.0.0/24", "v4", "", ""],
        "subresources": [("3b8360e6-e29a-4063-a8bc-7bbd0785d08b", "RegionOne"), ("3feae7ca-e66c-4006-aced-5f3a819c91f6", "RegionTwo")],
        "interconnections": ["90f6db5c-0012-44b6-aa94-d164bdefe8db"]

    }
]

# Delete database file if it exists currently
if os.path.exists('service.db'):
    os.remove('service.db')

db.create_all()

create_test = False

if(create_test):
    # Iterate over the resour structure and populate the database
    for resource in RESOURCES1:
        s = Resource(resource_name=resour['name'],
                    resource_type=resour['type'],
                    resource_global=resour['global'])
        for subresource in resource.get("subresources"):
            subresource_uuid, region_name, interconnexion_uuid = subresource
            res = SubResource(subresource_region=region_name, subresource_uuid=subresource_uuid)
            if region_name != local_region_name:
                inter = Interconnexion(interconnexion_uuid=interconnexion_uuid, resource=res)
                s.resource_subresources.append(res)
                s.resource_interconnections.append(inter)
            else:
                s.resour_resources.append(res)

        param_allocation, param_local_cidr, param_local_resource, param_ipv, param_master, param_master_auth = resour.get(
            "params")[0], resour.get("params")[1], resour.get("params")[2], resour.get("params")[3], resour.get("params")[4], resour.get("params")[5]
        param = Parameter(parameter_allocation_pool=param_allocation,
                        parameter_local_cidr=param_local_cidr, parameter_local_resource=param_local_resource, parameter_ipv=param_ipv, parameter_master=param_master, parameter_master_auth=param_master_auth)
        
        if('l2allocs' in resour.keys()):
            lmaster = LMaster()
            for allocationpool in resour.get("l2allocs"):

                allocation_first_ip, allocation_last_ip, allocation_site = allocationpool.get("first_ip"), allocationpool.get("last_ip"), allocationpool.get("site")
                lmaster.lmaster_l2allocationpools.append(L2AllocationPool(l2allocationpool_first_ip=allocation_first_ip, l2allocationpool_last_ip=allocation_last_ip, l2allocationpool_site = allocation_site))
            param.parameter_lmaster.append(lmaster)
        s.resour_params.append(param)
        
        #
        #for interco in resour.get("interconnections"):
        #    s.resour_interconnections.append(
        #        Interconnexion(interconnexion_uuid=interco))
        
        db.session.add(s)

    db.session.commit()
