from . import TestCaseTools
from TestCaseTools  import *

number = 77


def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("#"*number)
        func(*args, **kwargs)
        print("#"*number)
    return wrapper

class DP_Check(object):
    
    @staticmethod
    @my_decorator
    def Port_Error(Legit_Only=False):
        flag = False  # output flag
        try:
            for i in DTCT.DP_Info.values():#For all DPs that the DF is in contact with 
                telnet = Telnet(i)
                c = telnet.Command("system inf-stats")
                
                for j in DTCT["DP_Ports"]:#For the ports the configured at Data_For_TCT.json
                    if (not re.search(rf"{j}\s+[0-9]+\s+0\s+0\s+[0-9]+\s+0\s+0", c, re.IGNORECASE)) and re.search(
                            rf"^{j}\s+", c, re.IGNORECASE):
                        print(f"{getframeinfo(currentframe()).lineno} Port Error:".center(number,"#"))
                        print(getframeinfo(currentframe()).lineno,c)
                        break
                        
                else:
                    if Legit_Only:
                        c = telnet.Command("system internal dpe-statistics total all", True)
                        if (not re.search(rf"DPE Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c,
                                          re.IGNORECASE)) and (
                        not re.search(rf"HW-Accelerator Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c,
                                      re.IGNORECASE)) and (
                        not re.search(rf"Total Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c, re.IGNORECASE)):
                            print(f"{getframeinfo(currentframe()).lineno} dpe-statistics Error:".center(number, '#'))
                            print(getframeinfo(currentframe()).lineno,c)
                            break
            else:
                flag = not flag
            return flag
        except:
            print(getframeinfo(currentframe()).lineno,"Unexpected error:", sys.exc_info()[0])
            return flag
        
class DF_Check(object):
    pass
class Vision_Check(object):
    pass
class FD_Check(object):
    pass
class Other_Check(object):
    @staticmethod
    def Ping_All_Components(HA_DF = False,Fail_Time=15):
        start = time.perf_counter()
        flag = True
        if HA_DF:
            Components_List = Vision_API.DF_IP()
        else:
            Components_List = [Vision_API.DF_IP()[0]]
        Components_List += [i for i in DTCT.DP_Info.values()]
        Components_List.append(DTCT["Vision_IP"])
        while (time.perf_counter() - start < (Fail_Time*60)):
            for i in Components_List:
                flag = flag and ping(i)
            if flag:
                break
            print("#" * number)
            time.sleep(1)
        return flag
