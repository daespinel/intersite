import random
import datetime
from random import seed
from random import randint
import time
from datetime import datetime

datetime_str = '2020-02-19,16:17:18.640'

datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d,%H:%M:%S.%f')

print(type(datetime_object))
print(datetime_object)  # printed in default format

datetime_str2 = '2020-02-19,16:17:19.452'

datetime_object2 = datetime.strptime(datetime_str2, '%Y-%m-%d,%H:%M:%S.%f')

print(type(datetime_object2))
print(datetime_object2)  # printed in default format

print(datetime_object2-datetime_object)