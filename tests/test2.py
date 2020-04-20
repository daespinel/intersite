import random
import datetime
from random import seed
from random import randint
import time
from datetime import datetime

resources = [{'region_name':'RegionOne', 'region_uuid':'123456'},{'region_name':'RegionTwo','region_uuid':'456789'}]

resources_str_list = (",".join(str(resource) for resource in ("\"" + str(element['region_name'] + "," + element['region_uuid'] + "\"") for element in resources)))

print(resources_str_list)