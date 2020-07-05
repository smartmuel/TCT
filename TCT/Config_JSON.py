from tkinter import *
from tkinter.ttk import *
from tkinter import scrolledtext
import json,time,pathlib,os

"""path = pathlib.Path().absolute()
DTCT_Path = ""
for r, d, f in os.walk(path):
	if "Data_For_TCT.json" in f:
		DTCT_Path = os.path.join(r, "Data_For_TCT.json")
		break"""
os.chdir(os.path.dirname(os.path.realpath(__file__)))
try:
    with open("Data_For_TCT.json", "r") as read_file:
        DTCT1 = json.load(read_file)
except:
    with open("Data_For_TCT.json", "a") as read_file:
        TCT_json={
    "Attack_Number": 10,
    "BP_AppSim_Max_Number": 8,
    "BP_AppSim_legit": [
        1,
        2
    ],
    "BP_IP": "1.1.1.1",
    "BP_Password": "Password",
    "BP_Reserve_Port_1": 0,
    "BP_Reserve_Port_2": 1,
    "BP_Reserve_Slot": 3,
    "BP_Session_Max_Number": 8,
    "BP_Test": "Test_Name",
    "BP_Username": "Username",
    "DF_IP_Secondary": "1.1.1.1",
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
    "LOG_FILE": "syslog_AMS.log",
    "MSSP_Dash_URL": "https://1.1.1.1/dashboard#/dashboard?r=5e579021d29d2001cc0593b8",
    "MSSP_Password": "Password",
    "MSSP_Username": "Username",
    "OngoingProtections": 1,
    "PO_Attack_Number": 1,
    "SSH_IP": "1.1.1.1",
    "SSH_Password": "Password",
    "SSH_Username": "Username",
    "Syslog_IP": "1.1.1.1",
    "Test_OngoingProtections": 1,
    "Vision_IP": "1.1.1.1",
    "Vision_Password": "Password",
    "Vision_Username": "Username"
}
        json.dump(TCT_json, read_file, ensure_ascii=False, indent=4, sort_keys=True)
        DTCT1 = TCT_json

os.chdir(os.getcwd())

DTCT = DTCT1

window = Tk()

scrollbar = Scrollbar(window)

window.title("Configuration for TestCaseTools")

window.geometry('1300x420')

txt = scrolledtext.ScrolledText(window, width=120)

txt.insert(INSERT,json.dumps(DTCT, indent=4, sort_keys=True))

txt.grid(column=0, row=1)

def clicked():
    if combo.get() == "Must_Config":
        txt.delete('1.0', END)
        txt.insert(INSERT,json.dumps(DTCT,  indent=4, sort_keys=True))

    elif combo.get() == "ALL":
        txt.delete('1.0', END)
        txt.insert(INSERT, json.dumps(DTCT, indent=4, sort_keys=True))

    elif combo.get() == "Vision":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "Vision_" in your_key}, indent=4,
                              sort_keys=True))

    elif combo.get() == "FlowDetector":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "FD_" in your_key}, indent=4,
                              sort_keys=True))

    elif combo.get() == "MSSP":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "MSSP_" in your_key}, indent=4,
                              sort_keys=True))

    elif combo.get() == "DefenseFlow":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "DF_" in your_key}, indent=4,
                              sort_keys=True))

    elif combo.get() == "DefencePro":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "DP_" in your_key}, indent=4,
                              sort_keys=True))

    elif combo.get() == "BreakingPoint":
        txt.delete('1.0', END)
        txt.insert(INSERT,
                   json.dumps({your_key: DTCT[your_key] for your_key in DTCT.keys() if "BP_" in your_key}, indent=4,
                              sort_keys=True))

def clicked1():
    d = json.loads(txt.get("0.1", END))
    for key in d.keys():
        if d[key] != DTCT[key]:
            DTCT[key] = d[key]
    txt.delete('1.0', END)
    txt.insert(INSERT, json.dumps(DTCT, indent=4, sort_keys=True))

def clicked2():
    with open('Data_For_TCT_old.json', 'w') as outfile:
        json.dump(DTCT1, outfile, ensure_ascii=False, indent=4)
    with open('Data_For_TCT.json', 'w') as outfile:
        json.dump(DTCT1, outfile, ensure_ascii=False, indent=4)

combo = Combobox(window, width=40)

combo['values']= ("Must_Config", "Vision", "MSSP", "DefenseFlow", "DefencePro", "BreakingPoint","FlowDetector", "ALL")

combo.grid(column=0, row=0)

btn = Button(window, text="Change", command=clicked1)

btn1 = Button(window, text="Select", command=clicked)

btn2 = Button(window, text="Save", command=clicked2)

btn.grid(column=2, row=0)
btn1.grid(column=1, row=0)
btn2.grid(column=3, row=0)
window.mainloop()