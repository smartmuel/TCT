import json,shutil
with open("Data_For_TCT.json","w") as read_file:
    TCT_json = {
    "Attack_Number": 10,
    "BP_AppSim_Max_Number": 8,
    "BP_AppSim_legit": [
        1,
        2
    ],
    "BP_IP": "10.174.180.45",
    "BP_Password": "shmuel",
    "BP_Reserve_Port_1": 0,
    "BP_Reserve_Port_2": 1,
    "BP_Reserve_Slot": 3,
    "BP_Session_Max_Number": 8,
    "BP_Test": "SAM_FD",
    "BP_Username": "shmuel",
    "DF_IP_Secondary": "10.170.19.117",
    "DF_Password": "radware",
    "DF_Username": "root",
    "DP_Password": "radware1",
    "DP_Ports": [
        "T-1",
        "14"
    ],
    "DP_Username": "radware",
    "Driver_Path": "E:\\Hi\\Driver\\chromedriver.exe",
    "FD_IP": "10.170.19.104",
    "LOG_FILE": "syslog_AMS.log",
    "MSSP_Dash_URL": "https://10.170.17.114/dashboard#/dashboard?r=5e579021d29d2001cc0593b8",
    "MSSP_Password": "radware",
    "MSSP_Username": "admin@radware.com",
    "OngoingProtections": 1,
    "PO_Attack_Number": 1,
    "SSH_IP": "10.170.9.136",
    "SSH_Password": "radware",
    "SSH_Username": "root",
    "Syslog_IP": "10.170.19.52",
    "Test_OngoingProtections": 1,
    "Vision_IP": "10.170.19.115",
    "Vision_Password": "radware!Q2w3e4r",
    "Vision_Username": "TCT"
}
    json.dump(TCT_json, read_file, ensure_ascii=False, indent=4, sort_keys=True)
        
from TestCaseTools import *
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

if __name__ == "__main__":
    print(Other_Check.Ping_All_Components(True))
    print(DP_Check.Port_Error(True))
    os.remove("Data_For_TCT.json")
    os.rmdir("ScreenShots")
    shutil.rmtree("__pycache__", ignore_errors=True)