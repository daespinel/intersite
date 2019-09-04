import os
from config import db
from service import Service, Resource, Interconnexion

# Data to initialize database with
SERVICES = [
    {
        "name": "Service1",
        "type": "L3",
        "global": "a842c6f0-44a2-bc21-568a56c54de0",
        "params": "",
        "resources": [("id1", "RegionOne"), ("id2", "RegionTwo"), ("id3", "RegionThree")],
        "interconnections": ["z1", "z2"]

    },
    {
        "name": "Service2",
        "type": "L3",
        "global": "02b98df2-03a8-974c-d2569f7e44e0",
        "params": "",
        "resources": [("id10", "RegionOne"), ("id15", "RegionTen"), ("id16", "RegionSixTen")],
        "interconnections": ["Y1", "Y2"]
    },
    {
        "name": "Service3",
        "type": "L3",
        "global": "220ac9d3-58c9-d640-0369b6b58c71",
        "params": "",
        "resources": [("id21", "RegionOne"), ("id24", "RegionFour"), ("id25", "RegionFive"), ("id28", "RegionTwentyEight")],
        "interconnections": ["x1", "x2", "x3"]
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
    # ,service['resources'],service['interconnections']
    for interco in service.get("interconnections"):
        s.service_interconnections.append(
            Interconnexion(interconnexion_uuid=interco))
    db.session.add(s)

db.session.commit()
