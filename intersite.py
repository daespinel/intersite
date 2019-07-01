from datetime import datetime

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))

# Data to serve with our API
SERVICES = {
    "Service1": {
        "type": "L3",
        "name": "Service1",
        "resources": ["id1,RegionOne","id2,RegionTwo","id3,RegionThree"]
    },
    "Service2": {
        "type": "L3",
        "name": "Service2",
        "resources": ["id10,RegionOne","id15,RegionTen","id16,RegionSixTen"]
    },
    "Service3": {
        "type": "L3",
        "name": "Service3",
        "resources": ["id21,RegionOne","id24,RegionFour","id25,RegionFive","id28,RegionTwentyEight"]
    }
}

# Create a handler for our read (GET) people
def read():
    """
    This function responds to a request for /api/intersite
    with the complete lists of inter-site services

    :return:        sorted list of inter-site services
    """
    # Create the list of people from our data
    return [SERVICES[key] for key in sorted(SERVICES.keys())]


def create(service):
    service.get("name", None)
    