import os
from config import db
from service import Service, Resource, Interconnexion, Parameter, L2AllocationPool, L2Master

# Data to initialize database with
SERVICES1 = [
    {
        "name": "Service1",
        "type": "L2",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": ["10.0.0.3-10.0.0.108", "10.0.0.0/24", "v4"],
        "resources": [("id589", "RegionOne")],
        "interconnections": ["z1"]

    },
    {
        "name": "Service2",
        "type": "L3",
        "global": "02b98df2-03a8-974c-d2569f7e44e0",
        "params": ["", "20.0.0.0/24", "v4"],
        "resources": [("id10", "RegionOne"), ("id15", "RegionTen"), ("id16", "RegionSixTen")],
        "interconnections": ["Y1", "Y2"]
    },
    {
        "name": "Service3",
        "type": "L3",
        "global": "220ac9d3-58c9-d640-0369b6b58c71",
        "params": ["", "30.0.0.0/24", "v4"],
        "resources": [("id21", "RegionOne"), ("id24", "RegionFour"), ("id25", "RegionFive"), ("id28", "RegionTwentyEight")],
        "interconnections": ["x1", "x2", "x3"]
    }
]

SERVICES = [
    {
        "name": "Service1",
        "type": "L2",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": ["10.0.0.3-10.0.0.108", "10.0.0.0/24", "v4", "RegionOne", "http://192.168.57.6:7575"],
        "resources": [("id589", "RegionOne"),("id16", "RegionSixTen")],
        "interconnections": ["z1"]

    }
]

# Delete database file if it exists currently
if os.path.exists('service.db'):
    os.remove('service.db')

db.create_all()

# Iterate over the service structure and populate the database
for service in SERVICES:
    s = Service(service_name=service['name'],
                service_type=service['type'],
                service_global=service['global'])
    for resource in service.get("resources"):
        resource_uuid, region_name = resource
        s.service_resources.append(
            Resource(resource_region=region_name, resource_uuid=resource_uuid))
    
    param_allocation, param_local_cidr, param_ipv, param_master, param_master_auth = service.get("params")[0],service.get("params")[1],service.get("params")[2],service.get("params")[3],service.get("params")[4]
    s.service_params.append(Parameter(parameter_allocation_pool=param_allocation,
                                          parameter_local_cidr=param_local_cidr, parameter_ipv=param_ipv, parameter_master=param_master, parameter_master_auth=param_master_auth))

    print()
    for interco in service.get("interconnections"):
        s.service_interconnections.append(
            Interconnexion(interconnexion_uuid=interco))
    db.session.add(s)

db.session.commit()
