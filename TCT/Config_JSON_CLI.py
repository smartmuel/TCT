import json,os
class Json(object):
    json_data = {
    "BP_AppSim_Max_Number": 8,
    "BP_IP": "1.1.1.1",
    "BP_Password": "Password",
    "BP_Reserve_Port_1": 0,
    "BP_Reserve_Port_2": 1,
    "BP_Reserve_Slot": 3,
    "BP_Session_Max_Number": 8,
    "BP_Test": "Test_Name",
    "BP_Username": "Username",
    "BP_Test_ID": "Don't Fill",
    "DF_Password": "Password",
    "DF_Username": "Username",
    "DP_Password": "Password",
    "DP_Ports": [
        "T-1",
        "14"
    ],
    "DP_Username": "Username",
    "Driver_Path": "",
    "FD_IP": "1.1.1.1",
    "FD_Password": "Password",
    "FD_Username": "Username",
    "LOG_FILE": "syslog_AMS.log",
    "MSSP_Dash_URL": "https://1.1.1.1/dashboard#/dashboard?r=5e579021d29d2001cc0593b8",
    "MSSP_Password": "Password",
    "MSSP_Username": "Username",
    "SSH_IP": "1.1.1.1",
    "SSH_Password": "Password",
    "SSH_Username": "Username",
    "Syslog_IP": "",
    "Syslog_Start": [],
    "Syslog_End": [],
    "Vision_IP": "1.1.1.1",
    "Vision_Password": "Password",
    "Vision_Username": "Username",
    "OngoingProtections": 0,
    "Delay": 5,
    }
    try:
        with open("Config_Info.json","r") as file:

            pass
    except:
        with open("Config_Info.json","w") as file:
            data = {"Json_Folder_Path": "", "Json_Name": "Data_For_TCT.json"}
            json.dump(data, file, ensure_ascii=False, indent=4, sort_keys=True)
    def __init__(self,flag = True):
        """List = ["All","TestCases","Driver"]
        print("Please choose the number you'll be using:")
        while flag:
            for i,j in enumerate(List):
                print(f"{i+1}\t{j}")
            try:
                Index = int(input())
                if 0 < Index < len(List):
                    break
            except:
                print("That's not a valid option!")"""
        for i in [your_key for your_key in self.json_data.keys() if "Vision" in your_key]:
            self.json_data[i] = input(f"{i}:")
        List = ["All","Vision","FlowDetector","MSSP","DefenseFlow","DefencePro","BreakingPoint"]
        while True:
            for i,j in enumerate(List):
                print(f"{i+1}\t{j}")
            try:
                Index = input()
                if not Index:
                    break
                Index = int(Index)
                if 0 < Index < len(List):
                    for i in [your_key for your_key in self.json_data.keys() if List[Index-1] in your_key]:
                        data = input(f"{i}:")
                        if data:
                            self.json_data[i] = data
            except:
                print("That's not a valid option!")
        path = input("Please Enter the Full Folder Path:")
        name = input("Please Enter File Name:")
        with open("Config_Info.json", "r") as file:
            json1 = json.load(file)
            json1["Json_Folder_Path"] = path
            if name:
                json1["Json_Name"] = f"{name.replace('.json','')}.json"
        with open("Config_Info.json", "w") as file:
            json.dump(json1, file, ensure_ascii=False, indent=4, sort_keys=True)
        try:
            with open (os.path.join(json1["Json_Folder_Path"],json1["Json_Name"]),"w") as file:
                json.dump(self.json_data, file, ensure_ascii=False, indent=4, sort_keys=True)
        except:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), json1["Json_Name"]), "w") as file:
                json.dump(self.json_data, file, ensure_ascii=False, indent=4, sort_keys=True)

