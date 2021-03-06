from tkinter import *
from tkinter.ttk import *
from tkinter import scrolledtext
import json,time,pathlib,os
import Config_JSON_CLI

"""path = pathlib.Path().absolute()
DTCT_Path = ""
for r, d, f in os.walk(path):
	if "Data_For_TCT.json" in f:
		DTCT_Path = os.path.join(r, "Data_For_TCT.json")
		break"""
with open("Config_Info.json","r") as file:
    Config_Json = json.load(file)

# context managers for changing directory
class cd(object):
    def __init__(self, path):
        os.chdir(path)
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        os.chdir(cwd)

try:
    with open(Config_Json["Json_Name"], "r") as read_file:
        DTCT1 = json.load(read_file)
except:
    try:
        with cd(Config_Json["Json_Folder_Path"]):
            with open(Config_Json["Json_Name"], "r") as read_file:
                DTCT1 = json.load(read_file)
    except:
        with open(Config_Json["Json_Name"], "w") as read_file:
            json.dump(Config_JSON_CLI.Json.json_data, read_file, ensure_ascii=False, indent=4, sort_keys=True)
            DTCT1 = Config_JSON_CLI.Json.json_data

os.chdir(os.getcwd())

DTCT = DTCT1

window = Tk()

scrollbar = Scrollbar(window)

window.title("Configuration for TestCaseTools")

window.geometry('1300x420')

txt = scrolledtext.ScrolledText(window, width=120)

txt.insert(INSERT,json.dumps(DTCT, indent=4, sort_keys=True))

txt.grid(column=0, row=1)

Dictionaty = {"Vision": "Vision_", "FlowDetector": "FD_", "MSSP": "MSSP_", "DefenseFlow": "DF_", "DefencePro": "DP_",
              "BreakingPoint": "BP_", "BSN": "BSN_"}

def clicked():

    if combo.get() == "ALL":
        txt.delete('1.0', END)
        txt.insert(INSERT, json.dumps(DTCT, indent=4))

    elif combo.get() in Dictionaty.keys():
        txt.delete('1.0', END)
        JSON = {your_key: DTCT[your_key] for your_key in DTCT.keys() if Dictionaty[combo.get()] in your_key}
        txt.insert(INSERT, json.dumps({key: JSON[key] for key in sorted(JSON.keys(), reverse=True)}, indent=4))

    else:
        txt.delete('1.0', END)
        JSON = {your_key: DTCT[your_key] for your_key in DTCT.keys() if combo.get() in your_key}
        txt.insert(INSERT, json.dumps({key: JSON[key] for key in sorted(JSON.keys(), reverse=True)}, indent=4))

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

combo['values']= ("Vision", "MSSP", "DefenseFlow", "DefencePro", "BreakingPoint","FlowDetector","BSN", "ALL")

combo.grid(column=0, row=0)

btn = Button(window, text="Change", command=clicked1)

btn1 = Button(window, text="Select", command=clicked)

btn2 = Button(window, text="Save", command=clicked2)

btn.grid(column=2, row=0)
btn1.grid(column=1, row=0)
btn2.grid(column=3, row=0)
window.mainloop()