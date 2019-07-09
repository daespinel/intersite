import os
from config import db
from service import Service

# Data to initialize database with
SERVICES = [
    {
        "name": "Service1",
        "type": "L3",
        "resources": ["id1,RegionOne", "id2,RegionTwo", "id3,RegionThree"],
        "interconnections": ["z1", "z2"]

    },
    {
        "name": "Service2",
        "type": "L3",
        "resources": ["id10,RegionOne", "id15,RegionTen", "id16,RegionSixTen"],
        "interconnections": ["Y1", "Y2"]
    },
    {
        "name": "Service3",
        "type": "L3",
        "resources": ["id21,RegionOne", "id24,RegionFour", "id25,RegionFive", "id28,RegionTwentyEight"],
        "interconnections": ["x1", "x2", "x3"]
    }
]

# Delete database file if it exists currently
if os.path.exists('service.db'):
    os.remove('service.db')

db.create_all()

# Iterate over the service structure and populate the database
for service in SERVICES:
    s = Service(service_name = service['name'], service_type = service['type'], service_resources = service['resources'], service_interconnections = service['interconnections'])
    print(s)
    db.session.add(s)

db.session.commit()