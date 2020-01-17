import random
import datetime
from random import seed
from random import randint
import time

print(datetime.datetime.now())

regions_list = ["RegionOne","RegionTwo","RegionThree","RegionFour","RegionFive","RegionSix","RegionSeven","RegionEigth","RegionNine"]

test_type = "L3"
test_size = 2
test_number = 5

end = time.time()
print(end)

if(test_type == "L3"):
    for i in range(test_number):
        seed(datetime.datetime.now())
        selected_index = randint(1,len(regions_list))
        print(selected_index)