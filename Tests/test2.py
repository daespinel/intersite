import random
import datetime
from random import seed
from random import randint
import time
from datetime import datetime

def checkEqualElement(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True,"something"
    return all(first == rest for rest in iterator),"else"

CIDRs_conditions = ['False', 'False', 'False']

print(str(checkEqualElement(CIDRs_conditions)[0]) + '  ' + checkEqualElement(CIDRs_conditions)[1])

if not checkEqualElement(CIDRs_conditions)[0]:
    print("ERROR: CIDR is not the same for all the resources")

print(all(rest[1]  == 'True' for rest in CIDRs_conditions))

test_array = []

