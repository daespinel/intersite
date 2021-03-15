import copy

baseDictionary={'user': '', 'I2P1':'', 'I2P2':'', 'I2P3':'', 'I2P4':'', 'I2P5':'', 'I2P6':'', 'I2P7':'', 'I2P8':'', 'I2P9':'', 'I2P10':'', 'I2P11':'', 'I2P12':'', 'I2P13':'', 'I2P14':'', 'I2P15':'', 'I2P16':'', 'I2P17':'', 'I2P18':'', 'I2P19':'', 'I2P20':'', 'I2P21':'', 'I2P22':'', 'I2P23':'', 'I2P24':'', 'I2P25':''}

def fix_my_mess():
    f = open("i2_responses.csv", "r", encoding="ISO-8859-1")
    user = ""
    storeDictionary=[]
    while f:
        line = f.readline()
        splitString = line.split("|")
        print(splitString)
        if splitString[0] != user:
            storeDictionary.append(copy.copy(baseDictionary))
            storeDictionary[-1]['user'] = splitString[0]
            user = splitString[0]
            
        print(type(splitString[1]))
        print(type('I2P1'))
        print('')        
        print('I2P1'.strip())
        print((str(splitString[1]).strip()))
        code=str("I2P1")
        code1=str(splitString[1]).strip()

        print(code == code1)
        #print(dir('I2P1'))
        #print(dir(str(splitString[1])))
        storeDictionary[-1][splitString[1]] = splitString[2]+'|'+splitString[3]
        if line == "":
            break

    f.close()
    print(storeDictionary)

fix_my_mess()