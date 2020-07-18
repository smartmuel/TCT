# !/usr/bin/env python

import os, pathlib, logging, socketserver, re, json, time, threading, paramiko, requests
from sys import exc_info
from shutil import rmtree
from inspect import currentframe, getframeinfo
from zipfile import ZipFile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bps_restpy.bps_restpy_v1.bpsRest import BPS
from io import StringIO
from pandas import read_csv
from . import Config_JSON_CLI as CLI

"""cwd = current work directory"""
cwd, DP_index, debug_prints_flag = os.getcwd(), "0", False
print(f"cwd: {cwd}")

with open("Config_Info.json", "r") as file:
    Config_Json = json.load(file)


# context managers for changing directory
class cd(object):
    def __init__(self, path):
        os.chdir(path)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(cwd)
# the IP that can connect to 8.8.8.8
def get_ip_address():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def ping(host):
    from platform import system
    param = '-n' if system().lower() == 'windows' else '-c'
    command = f"ping {param} 1 {host}"
    response = os.popen(command).read().lower()
    return 'unreachable' not in response and "100%" not in response

# json read class
class Configuration(object):
    def __init__(self, json_file):
        self.path, self.DP_Info, self.DF_Info, self.DF_HA, self.json_file = os.getcwd(), {}, {}, False, json_file
        with open(json_file, "r") as read_file:
            self.json = json.load(read_file)
        self.json["Syslog_IP"] = self.json["Syslog_IP"] if self.json["Syslog_IP"] else get_ip_address()
        print("json file in:", os.getcwd())
        try:
            # DP_Info
            url = f"https://{self.json['Vision_IP']}/mgmt/system/user/login"
            fill_json = {"username": self.json["Vision_Username"], "password": self.json["Vision_Password"]}
            response = requests.post(url, verify=False, data=None, json=fill_json)
            cookie = response.cookies
            url = f"https://{self.json['Vision_IP']}/mgmt/device/df/config/MitigationDevices"
            response = requests.get(url, verify=False, data=None, cookies=cookie).json()
            try:
                for i in response["MitigationDevices"]:
                    if i["type"] == "DefensePro":
                        self.DP_Info[i["dp_name"]] = i["address"]
            except:
                print(getframeinfo(currentframe()).lineno, "NO DP device detected, please check configuration")
            self.DF_Info_Update()

        except NameError:
            print(getframeinfo(currentframe()).lineno, "Check if paramiko installed")
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

    def __setitem__(self, key, value):
        self.json[key] = value

    def __getitem__(self, item):
        return self.json[item]

    def DF_Info_Update(self):
        url = f"https://{self.json['Vision_IP']}/mgmt/system/user/login"
        fill_json = {"username": self.json["Vision_Username"], "password": self.json["Vision_Password"]}
        response = requests.post(url, verify=False, data=None, json=fill_json)
        cookie = response.cookies

        url = f"https://{self.json['Vision_IP']}/mgmt/device/df/config?prop=HA_ENABLED"
        response = requests.get(url, verify=False, data=None, cookies=cookie).json()
        self.DF_HA = bool(response["STANDBY_IP"])
        for i in [response['LOCAL_NODE_IP'], response["STANDBY_IP"]]:
            if i:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                for _ in range(10):
                    try:
                        ssh.connect(i, port=22, username=self.json["DF_Username"], password=self.json["DF_Password"])
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
                else:
                    continue
                stdin, stdout, stderr = ssh.exec_command("ifconfig")
                string = "".join(stdout.readlines())
                match = re.search(r'G2.*', "".join(string), re.DOTALL)
                match = re.search(r'\d+\.\d+\.\d+\.\d+', match.group(0))
                self.DF_Info[i] = match.group(0)

        url = f"https://{self.json['Vision_IP']}/mgmt/system/user/logout"
        requests.post(url, verify=False, cookies=cookie)

    def save(self):
        with cd(self.path):
            self.json["Syslog_Start"] = list(Check.start)
            self.json["Syslog_End"] = list(Check.end)
            with open(self.json_file, 'w') as outfile:
                json.dump(DTCT.json, outfile, ensure_ascii=False, indent=4, sort_keys=True)


# Reading the configuration from json
try:
    with cd(Config_Json["Json_Folder_Path"]):
        DTCT = Configuration(Config_Json["Json_Name"])
except:
    try:
        with cd(".."):
            DTCT = Configuration(Config_Json["Json_Name"])
    except:
        try:
            with cd(os.path.dirname(os.path.realpath(__file__))):
                DTCT = Configuration(Config_Json["Json_Name"])
        except:
            try:
                os.chdir(cwd)
                path = pathlib.Path().absolute()
                DTCT_Path = ""
                for r, d, f in os.walk(path):
                    if Config_Json["Json_Name"] in f:
                        DTCT_Path = os.path.join(r, "Data_For_TCT.json")
                        break
                DTCT = Configuration(DTCT_Path)
            except:
                CLI.Json()
                try:
                    with cd(Config_Json["Json_Folder_Path"]):
                        DTCT = Configuration(Config_Json["Json_Name"])
                except:
                    os.chdir(cwd)
                    path = pathlib.Path().absolute()
                    DTCT_Path = ""
                    for r, d, f in os.walk(path):
                        if Config_Json["Json_Name"] in f:
                            DTCT_Path = os.path.join(r, "Data_For_TCT.json")
                            break
                    DTCT = Configuration(DTCT_Path)

#Check if File Downloaded and if it a zip there is an extraction flag
def file_check(extract=True, delay=5):
    start = time.perf_counter()
    flag = False
    try:
        while time.perf_counter() - start < delay * 60:
            for file in os.listdir(os.getcwd()):
                if file.endswith(".crdownload"):
                    time.sleep(0.5)
                    break
            else:
                for file in os.listdir(os.getcwd()):
                    if file.endswith(".zip"):
                        if os.path.getsize(file) > 0:
                            # time.sleep(3)
                            if extract:
                                with ZipFile(file, 'r') as zip:
                                    zip.extractall()
                            os.remove(file)
                            break
                    elif file.endswith(".tar.gz") or file.endswith(".csv"):
                        if os.path.getsize(file) > 0:
                            os.remove(file)
                            break
                else:
                    continue
                flag = True
                break
    except:
        print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
    finally:
        return flag

# Context Managers Class
class CM(object):
    # Driver Context Manager
    class Chrome(object):
        def __init__(self, url="", allure=True, Name="Test", base_resolution=100):
            self.driver = Driver(url=url, allure=allure, Name=Name)

        def __enter__(self):
            return self.driver

        def __exit__(self, type, value, traceback):
            self.driver.Close()

    # Context managers for entering iframe
    class iframe(object):
        def __init__(self, driver, frame, delay=10):
            try:
                self.driver = driver
                WebDriverWait(self.driver, delay).until(EC.frame_to_be_available_and_switch_to_it(frame))
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            try:
                self.driver.switch_to.default_content()
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

    # SSH Context Manager
    class SSH(object):
        def __init__(self, IP=DTCT["SSH_IP"], USER=DTCT["SSH_Username"], PASSWORD=DTCT["SSH_Password"]):
            self.ssh = SSH(IP=IP, USER=USER, PASSWORD=PASSWORD)

        def __enter__(self):
            return self.ssh

        def __exit__(self, type, value, traceback):
            self.ssh.Close()

    # Context managers timer
    class timer(object):
        def __init__(self, TIME, Delay=None):
            self.TIME = TIME
            self.start = time.perf_counter()
            self.Delay = Delay if Delay else TIME
            time.sleep(int(Delay))

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            try:
                time.sleep(self.TIME - int(time.perf_counter() - self.start))
            except:
                pass  # silenced

# Decorator for ScreenShots and more
def prefix_decorator(prefix=""):
    def decorator_test(function):
        def wrapper_test(self, *args, **kwargs):
            start = time.perf_counter()
            self.Vision()
            result = function(self, *args, **kwargs)
            if self.allure:
                self.image = self.driver.get_screenshot_as_png()
                if "DP_Current_Attack" in prefix or "DP_Traffic" in prefix:
                    self.Name = f"{prefix}_{DP_index}"
                else:
                    self.Name = prefix
            else:
                if prefix:
                    try:
                        os.makedirs(os.path.join(self.path, self.Main_Name, self.Name))
                    except FileExistsError:
                        pass
                    os.chdir(os.path.join(self.path, self.Main_Name, self.Name))
                    if "DP_Current_Attack" in prefix or "DP_Traffic" in prefix:
                        N = f"{self.Name}_{prefix}_{DP_index}.png"
                    else:
                        N = f"{self.Name}_{prefix}.png"
                    # fix
                    self.driver.save_screenshot(N)
                    os.chdir(cwd)
            if self.flag_change_size:
                self.Screen_Size()
            print(getframeinfo(currentframe()).lineno, time.perf_counter() - start, prefix)
            return result

        return wrapper_test

    return decorator_test

class Driver(object):

    def __init__(self, Name="Test", url="", allure=False, Headless_Flag=False, base_resolution=100):
        import chromedriver_autoinstaller
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        try:
            os.mkdir("ScreenShots")
        except FileExistsError:
            pass
        self.path, self.flag_change_size,self.base_resolution, self.start = os.path.join(cwd, "ScreenShots"), False,base_resolution, time.perf_counter()

        # Opening Chrome Driver
        options = Options()
        options.headless = Headless_Flag
        options.add_experimental_option("prefs", {
            "download.default_directory": rf"{cwd}",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        options.add_argument('--ignore-certificate-errors')
        try:
            chromedriver_autoinstaller.install()
            self.driver = webdriver.Chrome(chrome_options=chrome_options)
        except:
            try:
                self.driver = webdriver.Chrome(DTCT["Driver_Path"], options=options)
            except:
                # finding chromedriver location
                os.chdir(os.path.dirname(os.path.realpath(__file__)))
                os.chdir("..")
                path = pathlib.Path().absolute()
                for r, d, f in os.walk(path):
                    if "chromedriver.exe" in f:
                        DTCT["Driver_Path"] = os.path.join(r, "chromedriver.exe")
                        self.driver = webdriver.Chrome(DTCT["Driver_Path"], chrome_options=options)
                        break
                else:
                    print(getframeinfo(currentframe()).lineno, "You need to have chromedriver to open chrome.")
                    exit()
        finally:
            os.chdir(cwd)

        self.Name, self.Main_Name, self.Password_Done, self.allure, self.image = Name, Name.split("_")[
            0], False, allure, None

        if url == "":
            self.Vision()
        if url != "":
            self.Get(url)

    def __call__(self):
        return self.driver

    def Get(self, URL):
        if "://" not in URL:
            URL = f"http://{URL}"
        self.driver.get(URL)
        self.driver.fullscreen_window()

    def Screen_Size(self, size=100):
        if size != 100:
            try:
                self.Get("chrome://settings/")
                self.driver.execute_script(f'chrome.settingsPrivate.setDefaultZoom({(size*self.base_resolution) / 10000:.1f});')
                # self.driver.execute_script(f"document.body.style.zoom='{size}%'")
                self.flag_change_size = True
            except:
                print(getframeinfo(currentframe()).lineno, "Screen_Size_Error")
        else:
            self.Get("chrome://settings/")
            self.driver.execute_script(f'chrome.settingsPrivate.setDefaultZoom({self.base_resolution / 100:.1f});')
            # self.driver.execute_script("document.body.style.zoom='100%'")
            self.flag_change_size = False

    def Close(self):
        self.driver.close()
        self.driver.quit()
        DTCT.save()

    # Driver enter Vision
    def Vision(self, delay=5):
        self.Get(f"https://{DTCT['Vision_IP']}/")
        if time.perf_counter() - self.start > 1200:
            self.Password_Done = False
        if not self.Password_Done:
            try:
                if self.Wait(
                        "#visionAppRoot > div > div > div > div > form > div.sc-eNQAEJ.ifpxog > div.content.sc-hMqMXs.gNeJno > div > div:nth-child(1) > div > div > input"):
                    self.Fill(
                        "#visionAppRoot > div > div > div > div > form > div.sc-eNQAEJ.ifpxog > div.content.sc-hMqMXs.gNeJno > div > div:nth-child(1) > div > div > input",
                        DTCT["Vision_Username"], click=False, Enter=False)
                    self.Fill(
                        "#visionAppRoot > div > div > div > div > form > div.sc-eNQAEJ.ifpxog > div.content.sc-hMqMXs.gNeJno > div > div:nth-child(2) > div > div > input",
                        DTCT["Vision_Password"], click=False)
                    self.ClickIf(
                        "#visionAppRoot > div > div > div > div > form > div.sc-eNQAEJ.ifpxog > div.content.sc-hMqMXs.gNeJno > div > div.Loginstyle__ButtonContainer-pg1d8l-13.jRBrip > button")
            except:
                print(getframeinfo(currentframe()).lineno, "Loading Vision took too much time!")
            try:
                self.driver.find_element_by_css_selector(
                    "#visionAppRoot > div > div > div > div > form > div.sc-eNQAEJ.ifpxog > div.sc-kEYyzF.LcMkd > div > di")
                if time.perf_counter() - self.start > 1200:
                    self.Close()
                    exit()
                self.Vision()
            except:
                pass
            self.start = time.perf_counter()
            self.Password_Done = True
        try:
            self.Wait("gwt-debug-DevicesTree_Node_" + list(DTCT.DP_Info.keys())[0], "ID", 10)
            try:
                self.driver.find_element_by_id('gwt-debug-TopicsNode_dp.setup.tree.sw_management-content')
                self.Wait('gwt-debug-rsFSapplList_Header', "ID")
            except:
                try:
                    self.driver.find_element_by_id(
                        'gwt-debug-TopicsNode_am.system.tree.generalSettings.basicParameters-content')
                    self.Wait('gwt-debug-managementIp_Widget', "ID")
                except:
                    print(getframeinfo(currentframe()).lineno, "Fix")
            print(getframeinfo(currentframe()).lineno, "HOME is ready!")
        except:
            print(getframeinfo(currentframe()).lineno, "HOME took too much time!")

    # Driver enter MSSP
    def MSSP(self, delay=5):
        self.Get(DTCT["MSSP_Dash_URL"])
        try:
            self.Wait('username', Type="name", delay=delay)
            print(getframeinfo(currentframe()).lineno, "MSSP is ready!")
            self.driver.find_element_by_name("username").send_keys(DTCT["MSSP_Username"])
            self.driver.find_element_by_name("password").send_keys(DTCT["MSSP_Password"])
            self.driver.find_element_by_class_name("btnLogin").click()
        except:
            print(getframeinfo(currentframe()).lineno, "MSSP took too much time!")
        self.driver.fullscreen_window()

    # Fill Text
    def Fill(self, ID, Text, Type="auto", Enter=True, click=True, Arrow_Down_After=0, Arrow_Down_Before=0, delay=5,
             **kwargs):
        from selenium.webdriver.common.keys import Keys
        def IFs(myElem, Enter, click, Arrow_Down_After, Arrow_Down_Before):
            if click:
                myElem.click()
            myElem.clear()
            myElem.send_keys(Text)
            if Arrow_Down_Before:
                for j in range(Arrow_Down_Before):
                    myElem.send_keys(Keys.ARROW_DOWN)
            if Enter:
                myElem.send_keys(Keys.ENTER)
            if Arrow_Down_After:
                for j in range(Arrow_Down_After):
                    myElem.send_keys(Keys.ARROW_DOWN)

        ID = ID.strip()
        Type = Type.lower()
        if "auto" in Type:
            for i in range(10):
                if ID[0] == "#" or " > " in ID:
                    if self.Wait(ID, "CSS", delay):
                        try:
                            myElem = self.driver.find_element_by_css_selector(ID)
                            IFs(myElem, Enter, click, Arrow_Down_After, Arrow_Down_Before)
                            break
                        except:
                            print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                elif ID[0] == "/":
                    if self.Wait(ID, "xpath", delay):
                        try:
                            myElem = self.driver.find_element_by_xpath(ID)
                            IFs(myElem, Enter, click, Arrow_Down_After, Arrow_Down_Before)
                            break
                        except:
                            print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                else:
                    if self.Wait(ID, "ID", delay):
                        try:
                            myElem = self.driver.find_element_by_id(ID)
                            IFs(myElem, Enter, click, Arrow_Down_After, Arrow_Down_Before)
                            break
                        except:
                            print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                    elif self.Wait(ID, "Class", delay):
                        try:
                            myElem = self.driver.find_element_by_class_name(ID)
                            IFs(myElem, Enter, click, Arrow_Down_After, Arrow_Down_Before)
                            break
                        except:
                            print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))

        else:
            for i in range(1000):
                if "css" in Type:
                    try:
                        self.Wait(ID)
                        myElem = self.driver.find_element_by_css_selector(ID).click()
                        myElem.send_keys(Text)
                        if Enter:
                            myElem.send_keys(Keys.ENTER)
                        # Fail = False
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                        # Fail = True

                elif "id" in Type:
                    try:
                        self.Wait(ID)
                        myElem = self.driver.find_element_by_id(ID)
                        if Arrow_Down_Before:
                            myElem.send_keys(Keys.ARROW_DOWN)
                        if Text != False:
                            myElem.send_keys(Text)
                        if Enter:
                            myElem.send_keys(Keys.ENTER)
                        if Arrow_Down_After > 0:
                            for j in range(Arrow_Down_After):
                                myElem.send_keys(Keys.ARROW_DOWN)
                            myElem.send_keys(Keys.ENTER)
                        # Fail = False
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                        # Fail = True

                else:
                    try:
                        self.Wait(ID)
                        myElem = self.driver.find_element_by_class_name(ID)
                        myElem.send_keys(Text)
                        myElem.send_keys(Keys.ENTER)
                        # Fail = False
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "didn't click" + str(i))
                        # Fail = True

    # Wait for target Element type in current page
    def Wait(self, ID, Type="auto", delay=10, **kwargs):
        from selenium.webdriver.common.by import By
        Type = Type.lower()
        ID = ID.strip()
        if "auto" in Type:
            if ID[0] == "#" or " > " in ID:
                try:
                    myElem = WebDriverWait(self.driver, delay).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ID)))
                    return True
                except:
                    print(getframeinfo(currentframe()).lineno, "Wait False", ID)
            elif ID[0] == "/":
                try:
                    myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.XPATH, ID)))
                    return True
                except:
                    print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                    return False
            else:
                try:
                    myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, ID)))
                    return True
                except:
                    print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                    return False
        elif "css" in Type:
            try:
                myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, ID)))
                return True
            except:
                print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                return False
        elif "class" in Type:
            try:
                myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, ID)))
                return True
            except:
                print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                return False
        elif "id" in Type:
            try:
                myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, ID)))
                return True
            except:
                print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                return False
        elif "xpath" in Type:
            try:
                myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.XPATH, ID)))
                return True
            except:
                print(getframeinfo(currentframe()).lineno, "Wait False", ID)
                return False
        elif "name" in Type:
            try:
                myElem = WebDriverWait(self.driver, delay).until(
                    EC.presence_of_element_located((By.Name, ID)))
                return True
            except:
                print(getframeinfo(currentframe()).lineno, "Wait False", ID)

    # Clicking on target Element type in current page
    def Click(self, ID, Type="auto", wait="No", delay=5, tries=3, **kwargs):
        ID = ID.strip()
        Type = Type.lower()
        if "auto" in Type:
            for i in range(tries):
                if ID[0] == "#" or " > " in ID:
                    try:
                        self.Wait(ID)
                        self.driver.find_element_by_css_selector(ID).click()
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                elif ID[0] == "/":
                    try:
                        self.Wait(ID)
                        self.driver.find_element_by_xpath(ID).click()
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                else:
                    try:
                        self.Wait(ID)
                        self.driver.find_element_by_id(ID).click()
                        break
                    except:
                        print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)

            if ID == '#global-menu > nav > ul > li.sub-menu-expanded.sc-gldTML.bYAUWd > div.sc-cJOK.bVfJMK > div:nth-child(2) > div':
                self.Wait("gwt-debug-TopicsNode_Configuration.Operation.PendingActions-content", "ID", delay=5)

            elif ID == "gwt-debug-TopicsStack_TrafficMonitoring_tab":
                try:
                    myElem = self.driver.find_element_by_css_selector(
                        '#gwt-debug-TopicsNode_bdos-traffic-monitoring-reports-content')
                    if myElem.is_displayed():
                        self.Click("gwt-debug-TopicsStack_TrafficMonitoring_tab")
                except:
                    try:
                        myElem = self.driver.find_element_by_css_selector(
                            '#gwt-debug-TopicsNode_security-dashboard-table-content')
                        if myElem.is_displayed():
                            self.Click("gwt-debug-TopicsStack_TrafficMonitoring_tab")
                    except:
                        pass

            elif ID == 'gwt-debug-Global_defenseFlow_Old':
                self.Wait("gwt-debug-TopicsNode_Configuration.Operation.PendingActions-content", "ID", delay=5)

            elif 'gwt-debug-DevicesTree_Node_' in ID:
                self.Click("gwt-debug-SoftwareList")

            elif ID == "gwt-debug-TopicsNode_traffic-utilization-report-content":
                try:
                    with CM.iframe(self.driver, "Concurrent_Connections_Report"):
                        self.Wait(
                            "body > div.main-view.ng-scope > ng-include > section > side-tabs > div > div.tab-bar > span")
                    self.Click('gwt-debug-TopicsNode_traffic-utilization-report-content')
                except:
                    print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

            elif wait != "No":
                self.Wait(wait)

        elif "css" in Type:
            for i in range(1000):
                try:
                    self.Wait(ID)
                    self.driver.find_element_by_css_selector(ID).click()
                    # Fail = False
                    break
                except:
                    print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                    # Fail = True
            else:
                print(getframeinfo(currentframe()).lineno, "Didn't click " + Type + " " + ID)

            if ID == '#global-menu > nav > ul > li.sub-menu-expanded.sc-gldTML.bYAUWd > div.sc-cJOK.bVfJMK > div:nth-child(2) > div':
                self.Wait("gwt-debug-TopicsNode_Configuration.Operation.PendingActions-content", "ID", delay=5)

            elif wait != "No":
                self.Wait(wait, Type)

        elif "id" in Type:
            for i in range(1000):
                try:
                    self.Wait(ID)
                    self.driver.find_element_by_id(ID).click()
                    # Fail = False
                    break
                except:
                    print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                    # Fail = True
            else:
                if ID == 'gwt-debug-TopicsNode_traffic-utilization-report-content':
                    # Fail = False
                    self.Click('gwt-debug-TopicsStack_TrafficMonitoring_tab')
                    self.Click('gwt-debug-TopicsNode_traffic-utilization-report-content')
                else:
                    print(getframeinfo(currentframe()).lineno, "Didn't click " + Type + " " + ID)

            if ID == "gwt-debug-TopicsStack_TrafficMonitoring_tab":
                try:
                    myElem = self.driver.find_element_by_css_selector(
                        '#gwt-debug-TopicsNode_bdos-traffic-monitoring-reports-content')
                    if myElem.is_displayed():
                        self.Click("gwt-debug-TopicsStack_TrafficMonitoring_tab")
                except:
                    try:
                        myElem = self.driver.find_element_by_css_selector(
                            '#gwt-debug-TopicsNode_security-dashboard-table-content')
                        if myElem.is_displayed():
                            self.Click("gwt-debug-TopicsStack_TrafficMonitoring_tab")
                    except:
                        pass

            elif ID == 'gwt-debug-Global_defenseFlow_Old':
                self.Wait("gwt-debug-TopicsNode_Configuration.Operation.PendingActions-content", "ID", delay=5)

            elif 'gwt-debug-DevicesTree_Node_' in ID:
                self.Click("gwt-debug-SoftwareList")

            elif ID == "gwt-debug-TopicsNode_traffic-utilization-report-content":
                try:
                    with CM.iframe(self.driver, "Concurrent_Connections_Report"):
                        self.Wait(
                            "body > div.main-view.ng-scope > ng-include > section > side-tabs > div > div.tab-bar > span")
                    self.Click('gwt-debug-TopicsNode_traffic-utilization-report-content')
                except:
                    print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

            elif wait != "No":
                self.Wait(wait, Type)

        elif "class" in Type:
            for i in range(1000):
                try:
                    self.Wait(ID, Type="class")
                    self.driver.find_element_by_class_name(ID).click()
                    # Fail = False
                    break
                except:
                    print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                    # Fail = True
            else:
                print(getframeinfo(currentframe()).lineno, "Didn't click " + Type + " " + ID)
            if wait != "No":
                self.Wait(wait, Type)

        elif "xpath" in Type:
            for i in range(1000):
                try:
                    self.Wait(ID)
                    self.driver.find_element_by_xpath(ID).click()
                    # Fail = False
                    break
                except:
                    print(getframeinfo(currentframe()).lineno, "Failed to Click" + str(i) + ID)
                    # Fail = True
            else:
                print(getframeinfo(currentframe()).lineno, "Didn't click " + Type + " " + ID)

            if wait != "No":
                self.Wait(wait, Type)

        else:
            print(getframeinfo(currentframe()).lineno, "No Such Type as " + Type)

    # Clicking on target Element if displayed
    def ClickIf(self, ID, delay=5, tries=1, **kwargs):
        if self.Wait(ID, delay=delay):
            self.Click(ID, tries=tries)

    # Experimental
    def Displayed(self, ID):
        ID = ID.strip()
        if self.Wait(ID):
            if ID[0] == "#" or " > " in ID:
                try:
                    while (self.driver.find_element_by_css_selector(ID).is_displayed()):
                        time.sleep(1)
                except:
                    pass
            elif ID[0] == "/":
                try:
                    while (self.driver.find_element_by_xpath(ID).is_displayed()):
                        time.sleep(1)
                except:
                    pass
            else:
                try:
                    while (self.driver.find_element_by_id(ID).is_displayed()):
                        time.sleep(1)
                except:
                    pass

    ################################################################
    # _________DF_Screenshots_______________

    def DF_Configuration(self):
        self.Click(
            '#global-menu > nav > ul > li:nth-child(5) > div.sub-menu-children.sc-feryYK.cwTrTn > div > div > div.NavItemContentstyle__StyledIcon-ob11v-0.gzJDwN',
            "CSS")
        self.Click(
            '#global-menu > nav > ul > li.sub-menu-expanded.sc-gldTML.bYAUWd > div.sc-cJOK.bVfJMK > div:nth-child(2) > div',
            Type="CSS")

    @prefix_decorator("DF_OP")
    def DF_Attack_Mitigation_Operation(self):
        self.Click(
            '#global-menu > nav > ul > li:nth-child(5) > div.sub-menu-children.sc-feryYK.cwTrTn > div > div > div.NavItemContentstyle__StyledIcon-ob11v-0.gzJDwN',
            "CSS")
        self.Click(
            "#global-menu > nav > ul > li.sub-menu-expanded.sc-gldTML.bYAUWd > div.sc-cJOK.bVfJMK > div:nth-child(1) > div",
            Type="CSS")
        self.Wait(
            "#df > div > div.dfc-main-content > div > div.dfc-dashboard-content > div > div:nth-child(1) > div > div.ReactVirtualized__Table__headerRow.sc-kPVwWT.cwEtzk",
            Type="CSS", delay=100)
        try:
            elem = self.driver.find_element_by_css_selector(
                '#df > div > div.dfc-main-content > div > div.dfc-dashboard-content > div > div.sc-hwwEjo.dlaYLh.sc-hqyNC.dvtIqr > div')
            if elem.is_displayed():
                self.DF_Attack_Mitigation_Operation()
        except:
            pass

    @prefix_decorator("DF_PO_ON")
    def DF_Ongoing_Protections(self):
        self.DF_Configuration()
        self.Click('gwt-debug-TopicsNode_Configuration.Operation.OngoingProtections-content',
                   wait='gwt-debug-OngoingProtections_RowID_0_CellID_SEQUENCE')

    @prefix_decorator("DF_PO")
    def DF_Protected_Objects(self):
        self.DF_Configuration()
        self.Click("gwt-debug-TopicsNode_Configuration.Operation.ProtectedObjects-content",
                   wait="gwt-debug-OperationsProtectedObjectsTable_RowID_0_CellID_name")

    @prefix_decorator("DF_Traffic")
    def DF_Traffic_Utillization(self):
        self.DF_Configuration()
        self.Click("gwt-debug-Security Monitoring")
        self.Click("gwt-debug-TopicsStack_TrafficMonitoring_tab")
        self.Click("#gwt-debug-TopicsNode_traffic-utilization-report-content", "CSS")
        with CM.iframe(self.driver, "Traffic_Utilization"):
            self.Click(
                "body > div.main-view.ng-scope > ng-include > section > side-tabs > div > div.tab-panel-container > section:nth-child(1) > div.content > div.top-left > div > select")
            self.Click(
                "body > div.main-view.ng-scope > ng-include > section > side-tabs > div > div.tab-panel-container > section:nth-child(1) > div.content > div.top-left > div > select > option:nth-child(7)")
            self.Click(
                'body > div.main-view.ng-scope > ng-include > section > side-tabs > div > div.tab-panel-container > section:nth-child(1) > div.content > rw-line-chart > div > svg.main > g > rect')

    @prefix_decorator("DF_HA")
    def DF_High_Availity(self):
        self.DF_Configuration()
        self.Click('gwt-debug-Configuration')
        self.Click('#gwt-debug-TopicsNode_Configuration\.HA-content', 'CSS')
        self.Wait('#gwt-debug-STANDBY_IP_Widget')

    @prefix_decorator("DF_Attack_Table")
    def DF_Current_Attack_Table(self):
        self.DF_Configuration()
        self.Click("gwt-debug-Security Monitoring")
        with CM.iframe(self.driver, 'security-dashboard-table'):
            self.Wait(
                'body > div.main-view.ng-scope > ng-include > section > section > section:nth-child(2) > div.the-table > rw-table2 > section > div.table-wrapper > div.table-body-wrapper > table > tbody > tr:nth-child(1)')
        self.Click("#gwt-debug-ConfigTab_Tab", "CSS")

    @prefix_decorator("DF_Workflow_Rules")
    def DF_Workflow_Rules(self):
        self.DF_Configuration()
        self.Click("gwt-debug-Configuration")
        self.Click("gwt-debug-TopicsStack_Configuration.SecuritySettings")
        self.Click("gwt-debug-TopicsNode_Configuration.SecuritySettings.Workflows-content")
        self.Click("gwt-debug-Workflows_RowID_0")  # FIX
        self.Click("gwt-debug-Workflows_EDIT")
        time.sleep(5)

    @prefix_decorator("DF_BGP_Flowspec")
    def DF_BGP_Flowspec(self):
        self.DF_Configuration()
        self.Click("gwt-debug-TopicsNode_Monitoring.Operation.BGP-content")
        self.Click("gwt-debug-TopicsNode_Monitoring.Operation.BGP.FlowSpecs-content")

    ################################################################
    # _________DP_Screenshots_______________

    def DP_Screenshots(self):
        global DP_index
        for i in DTCT.DP_Info.keys():
            DP_index = i
            self.One_DP_Traffic_Utillization()
            self.One_DP_Current_Attack_Table()

    @prefix_decorator("DP_Traffic")
    def One_DP_Traffic_Utillization(self):
        self.Click(f"gwt-debug-DevicesTree_Node_{DP_index}")
        self.Click('gwt-debug-Security Monitoring')
        self.Click('#gwt-debug-TopicsStack_TrafficMonitoring_tab', "CSS")
        self.Click('gwt-debug-TopicsNode_traffic-utilization-report-content')
        with CM.iframe(self.driver, 'Traffic_Utilization_Report'):
            self.Wait('legend-group', Type='class')
        try:
            myElem = self.driver.find_element_by_css_selector('#loading-image')
            while myElem.is_displayed():
                pass
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

    @prefix_decorator("DP_Current_Attack")
    def One_DP_Current_Attack_Table(self):
        self.Click(f"gwt-debug-DevicesTree_Node_{DP_index}")
        self.Click('gwt-debug-Security Monitoring')
        with CM.iframe(self.driver, 'security-dashboard-table'):
            self.Wait('table-row', Type='class')

    ################################################################
    # _________AMS_Screenshots_______________

    @prefix_decorator("DP_Monitoring")
    def DP_Monitoring(self):
        self.Get(f"https://{DTCT['Vision_IP']}/dpMonitoring")
        self.Wait("vertical-legend__area", Type="Class")
        self.Wait("policiesListContent", Type='Class')
        self.Wait(
            "#bf2c5f9d-ccf3-47a9-bfb4-73dcf33681f5 > div.wrapper > div > div.area-chart__wrapper > canvas.chartjs-render-monitor",
            delay=15)

    @prefix_decorator("DF_Analytics")
    def DF_Analytics(self):
        self.Screen_Size(90)
        self.Get(f"https://{DTCT['Vision_IP']}/dfAnalytics")
        self.Wait(
            "#\\32 4307c07-ab22-4f0b-9f17-e9c7d7b48687 > div.wrapper > div > div.horizontal-legend.regular-mode > div > div:nth-child(2) > div > div",
            delay=60)

    ################################################################
    # _________External_Screenshots_______________

    @prefix_decorator("MSSP")
    def MSSP_Dashboard_Screenshot(self):
        self.MSSP()
        self.Wait(
            "body > div.main-wrapper > div.content-wrapper.ng-scope.dashboard > div > div > div > div.gridster-content > ul > li:nth-child(6) > div.box.large > div.box-content > div > div.mediumContent.ng-scope.extendHeight > div.trafficMonitorFlotContainer > flot > div > canvas.flot-overlay")
        self.Click(
            "body > div.main-wrapper > div.content-wrapper.ng-scope.dashboard > div > div > div > div.gridster-content > ul > li:nth-child(6) > div.box.large > div.box-content > div > div.mediumContent.ng-scope.extendHeight > div.trafficMonitorFlotContainer > flot > div > canvas.flot-overlay",
            "CSS")

    ################################################################
    # _________Web_Configuration_______________

    @prefix_decorator
    def Config_Syslog_DP(self, fill):
        self.Click("gwt-debug-DevicesTree_Node_" + elf.DP_Names[0])
        self.Click("gwt-debug-TopicsNode_dp.setup.ReportingSettings-content")
        self.Click("gwt-debug-TopicsNode_dp.setup.tree.syslogdp")
        self.Click("gwt-debug-lockbutton")
        self.Click("gwt-debug-rdwrSyslogServerTable_NEW")
        self.Fill("gwt-debug-rdwrSyslogServerAddress_Widget", fill)
        self.Click("gwt-debug-ConfigTab_NEW_rdwrSyslogServerTable_Submit")
        self.Click("gwt-debug-rdwrSyslogServerTable_RowID_0")
        self.Click("gwt-debug-rdwrSyslogServerTable_DELETE")
        self.Click("gwt-debug-Dialog_Box_Yes")
        self.Click("gwt-debug-lockbutton")

    @prefix_decorator
    def Config_Syslog_DF(self, fill):
        self.DF_Configuration()
        self.Click("gwt-debug-Configuration")
        self.Click("gwt-debug-TopicsNode_Configuration.System.SyslogAlerts-content")
        self.Click("gwt-debug-SyslogAlerts_NEW")
        self.Fill("gwt-debug-ip_Widget", fill)
        self.Click("gwt-debug-ConfigTab_NEW_SyslogAlerts_Submit")
        self.Click("gwt-debug-SyslogAlerts_RowID_0")
        self.Click("gwt-debug-SyslogAlerts_DELETE")
        self.Click("gwt-debug-Dialog_Box_Yes")

    ################################################################
    # _________Custom_______________

    def Screenshots(self, Name="", MSSP=True):
        if Name:
            self.Name = Name
        self.DF_Current_Attack_Table()
        self.DF_Ongoing_Protections()
        self.DF_Protected_Objects()
        self.DF_Attack_Mitigation_Operation()
        self.DF_Traffic_Utillization()
        self.DP_Monitoring()
        self.DF_Analytics()
        self.DP_Screenshots()
        if MSSP:
            self.MSSP_Dashboard_Screenshot()


class BP(object):

    @staticmethod
    def Start(AppSim=[], Session=[], Appsim_MAX=DTCT["BP_AppSim_Max_Number"] + 1,
              Session_MAX=DTCT["BP_Session_Max_Number"] + 1, Test_Name=DTCT["BP_Test"]):
        bps = BPS((DTCT["BP_IP"]), (DTCT["BP_Username"]), (DTCT["BP_Password"]))
        # login
        bps.login()
        # showing current port reservation state
        bps.portsState()
        # reserving the ports.
        bps.reservePorts(slot=DTCT["BP_Reserve_Slot"],
                         portList=[DTCT["BP_Reserve_Port_1"], DTCT["BP_Reserve_Port_2"]],
                         group=1, force=True)
        # running the canned test 'AppSim' using group 1
        # please note the runid generated. It will be used for many more functionalities
        bps.setNormalTest(NN_name=Test_Name)
        bps.viewNormalTest()
        NORUN = []
        append = NORUN.append
        for i in range(1, Appsim_MAX):
            if i not in AppSim:
                append(i)
        for i in NORUN:
            bps.modifyNormalTest(componentId=(f'appsim_{i}'), elementId='active', Value='false')
        for i in AppSim:
            bps.modifyNormalTest(componentId=(f'appsim_{i}'), elementId='active', Value='true')
        NORUN = []
        append = NORUN.append
        for i in range(1, Session_MAX):
            if i not in Session:
                append(i)
        for i in NORUN:
            bps.modifyNormalTest(componentId=(f'sessionsender_{i}'), elementId='active', Value='false')
        for i in Session:
            bps.modifyNormalTest(componentId=(f'sessionsender_{i}'), elementId='active', Value='true')
        bps.saveNormalTest(name_=Test_Name, force='True')
        DTCT["BP_Test_ID"] = bps.runTest(modelname=Test_Name, group=1)
        bps.logout()

    @staticmethod
    def Stop(csv=False):
        try:
            bps = BPS(DTCT["BP_IP"], DTCT["BP_Username"], DTCT["BP_Password"])
            # login
            bps.login()
            # stopping test
            bps.stopTest(testid=DTCT["BP_Test_ID"])
            # logging out
            if csv:
                bps.exportTestReport(DTCT["BP_Test_ID"], "Test_Report.csv", "Test_Report")
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
        finally:
            try:
                bps.logout()
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])

    @staticmethod
    def CSV_Export():
        try:
            bps = BPS((DTCT["BP_IP"]), (DTCT["BP_Username"]), (DTCT["BP_Password"]))
            # login
            bps.login()
            bps.exportTestReport(DTCT["BP_Test_ID"], "Test_Report.csv", "Test_Report")
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
        finally:
            bps.logout()


class SSH(object):
    """
    Class for SSH
    """

    def __init__(self, IP=DTCT["SSH_IP"], USER=DTCT["SSH_Username"], PASSWORD=DTCT["SSH_Password"]):
        """
        Support only ipV4
        :param IP:
        :param USER:
        :param PASSWORD:
        """
        self.IP = IP
        self.USER = USER
        self.PASSWORD = PASSWORD
        self.NOT_IP = True
        if re.search(r'[0-2]?[0-9]?[0-9]?\.[0-2]?[0-9]?[0-9]?\.[0-2]?[0-9]?[0-9]?\.[0-2]?[0-9]?[0-9]?', IP):
            self.NOT_IP = False
            self.ssh_connect(IP, USER, PASSWORD)

    def ssh_connect(self, IP=DTCT["SSH_IP"], USER=DTCT["SSH_Username"], PASSWORD=DTCT["SSH_Password"]):
        """
        ssh connection
        """
        if self.NOT_IP:
            return None
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            flag = True
            while flag:
                try:
                    self.ssh.connect(IP, port=22, username=USER, password=PASSWORD)
                    flag = False
                except:
                    pass
        except:
            print(getframeinfo(currentframe()).lineno, "ssh_connect failed")

    def command(self, COM, Close=False):
        """
        :param COM: the command
        :param Close: if you want to close the connection
        :return: returns the output of the command - not working all the time
        """
        if self.NOT_IP:
            return None
        try:
            stdin, stdout, stderr = self.ssh.exec_command(COM)
            return stdout.readlines()
        except:
            self.ssh_connect(self.IP, self.USER, self.PASSWORD)
            self.command(COM)
        finally:
            if Close:
                self.Close()

    @staticmethod
    def PeakFlow():
        """
        PeakFlow Syslogs from remote linux server
        """
        try:
            ssh = SSH(IP="10.170.19.111")
            ssh.command("python3 Attack_start.py")
            ssh.Close()
        except:
            ssh.Close()
            SSH.PeakFlow()

    @staticmethod
    def Reboot(DF=True, Vision=True):
        if DF:
            try:
                ssh = SSH(Vision_API.DF_IP()[0], "root", "radware")
                ssh.command("sudo reboot", True)
            except:
                ssh.Close()
        if Vision:
            try:
                ssh = SSH(DTCT["Vision_IP"], "root", "radware")
                ssh.command("sudo reboot", True)
            except:
                ssh.Close()

    def Close(self):
        if self.NOT_IP:
            return None
        flag = True
        while flag:
            try:
                self.ssh.close()
                flag = False
            except:
                pass


class Telnet(object):

    def __init__(self, HOST, user=DTCT["DP_Username"], password=DTCT["DP_Password"]):
        import telnetlib
        self.tn = telnetlib.Telnet()
        self.tn.open(HOST)
        self.tn.read_until(b"User:")
        self.tn.write(user.encode('ascii') + b"\n")
        self.tn.read_until(b"Password:")
        self.tn.write(password.encode('ascii') + b"\n")
        debug_print = self.tn.read_until(b"#", 60).decode('utf-8')
        if debug_prints_flag:
            print(getframeinfo(currentframe()).lineno, debug_print)

    def Command(self, command, close=False):
        self.tn.write(command.encode('ascii') + b"\n")
        output = self.tn.read_until(b"#", 30).decode('utf-8')
        if close:
            self.tn.close()
        return output

    @staticmethod
    def DP_Syslog_ADD():
        for i in DTCT.DP_Info.values():
            telnet = Telnet(i, user=DTCT["DP_Username"], password=DTCT["DP_Password"])
            ip = DTCT["Syslog_IP"] if DTCT["Syslog_IP"] else get_ip_address()
            output = telnet.Command(f"manage syslog destination add {ip}", True)
            if debug_prints_flag:
                print(getframeinfo(currentframe()).lineno, output)

    @staticmethod
    def DP_Syslog_DELETE():
        for i in DTCT.DP_Info.values():
            telnet = Telnet(i, user=DTCT["DP_Username"], password=DTCT["DP_Password"])
            ip = DTCT["Syslog_IP"] if DTCT["Syslog_IP"] else get_ip_address()
            output = telnet.Command(f"manage syslog destination del {ip}", True)
            if debug_prints_flag:
                print(getframeinfo(currentframe()).lineno, output)

    @staticmethod
    def DP_Check_Port_Error(Legit_Only=False):
        for i in DTCT.DP_Info.values():
            flag = False
            telnet = Telnet(i, user=DTCT["DP_Username"], password=DTCT["DP_Password"])
            c = telnet.Command("system inf-stats")
            for j in DTCT["DP_Ports"]:
                if (not re.search(rf"{j}\s+[0-9]+\s+0\s+0\s+[0-9]+\s+0\s+0", c, re.IGNORECASE)) and re.search(
                        rf"^{j}\s+", c, re.IGNORECASE):
                    print(getframeinfo(currentframe()).lineno, "Port Error:")
                    print(getframeinfo(currentframe()).lineno, c)
                    break
            else:
                if Legit_Only:
                    c = telnet.Command("system internal dpe-statistics total all", True)
                    if (not re.search(rf"DPE Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c,
                                      re.IGNORECASE)) and (
                            not re.search(rf"HW-Accelerator Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c,
                                          re.IGNORECASE)) and (
                            not re.search(rf"Total Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", c,
                                          re.IGNORECASE)):
                        print(getframeinfo(currentframe()).lineno, "dpe-statistics Error:")
                        print(getframeinfo(currentframe()).lineno, c)
                        break

        else:
            flag = not flag
        return flag

    def Close(self):
        self.tn.close()


class Vision_API(object):
    """
    Login/Logout/Get from Vision with REST API
    """
    # flag that indicate the success of the login to vision
    flag = False

    def __init__(self, Vision=DTCT["Vision_IP"]):
        self.Vision = Vision
        url = f"https://{self.Vision}/mgmt/system/user/login"
        fill_json = {"username": DTCT["Vision_Username"], "password": DTCT["Vision_Password"]}
        response = requests.post(url, verify=False, data=None, json=fill_json)
        # self.flag = response.status_code
        self.cookie = response.cookies
        if "jsessionid" not in response.text:
            self.flag = False
        else:
            self.flag = True
            if debug_prints_flag:
                print(getframeinfo(currentframe()).lineno, response.text)

    def Get(self, url, Logout=False):
        response = requests.get(url, verify=False, data=None, cookies=self.cookie)
        if Logout:
            self.Logout()
        return response.json()

    @staticmethod
    def Syslog_ADD(IP=DTCT["Syslog_IP"], Level="DEBUG"):
        url = f"https://{DTCT['Vision_IP']}/mgmt/device/df/config/SyslogAlerts/add"
        json = {
            "ip": IP,
            "port": "514",
            "severity": Level,
            "description": ""
        }
        api = Vision_API()
        response = requests.post(url, verify=False, data=None, json=json, cookies=api.cookie)
        api.Logout()
        if debug_prints_flag:
            print(getframeinfo(currentframe()).lineno, response.text)

    @staticmethod
    def Syslog_DELETE(IP=DTCT["Syslog_IP"]):
        url = f"https://{DTCT['Vision_IP']}/mgmt/device/df/config/SyslogAlerts/{IP}"
        api = Vision_API()
        response = requests.delete(url, verify=False, data=None, cookies=api.cookie)
        api.Logout()
        if debug_prints_flag:
            print(getframeinfo(currentframe()).lineno, response.text)

    @staticmethod
    def DF_IP():
        api = Vision_API()
        output = api.Get(f"https://{DTCT['Vision_IP']}/mgmt/device/df/config?prop=HA_ENABLED", True)
        return [output['LOCAL_NODE_IP'], output["STANDBY_IP"]]

    @staticmethod
    def HTTP_Check(TIME=8):
        try:
            while not ping(DTCT['Vision_IP']):
                pass
            api = Vision_API()
            api.Logout()
            time.sleep(5)
            while not api.flag:
                api = Vision_API()
                api.Logout()
                time.sleep(5)
        except:
            time.sleep(5)
            Vision_API.HTTP_Check()
        time.sleep(TIME * 60)

    def Logout(self):
        url = f"https://{self.Vision}/mgmt/system/user/logout"
        response = requests.post(url, verify=False, cookies=self.cookie)
        # self.flag = response.status_code
        if self.flag:
            if debug_prints_flag:
                print(getframeinfo(currentframe()).lineno, response.text)


class BSN_API(object):
    """
    BSN API Functions
    """

    def __init__(self, IP=DTCT["BSN_IP"]):
        self.IP = IP
        self.headers = {'content-type': 'application/json', 'Accept': 'application/json'}
        url = f'https://{self.IP}:8443/api/v1/auth/login'
        fill = {"user": DTCT["BSN_Username"], "password": DTCT["BSN_Password"]}
        init_headers = {'content-type': 'application/json', 'Accept': '*/*'}
        response = requests.post(url, data=json.dumps(fill), headers=init_headers, verify=False)
        self.cookie = response.cookies

    @staticmethod
    def GET_Rules():
        BSN = BSN_API()
        url = f'https://{BSN.IP}:8443/api/v1/data/controller/applications/bigtap/policy[name="{DTCT["Dirty_Policy"]}"]/rule'
        BSN.response = requests.get(url, headers=BSN.headers, cookies=BSN.cookie, verify=False).json()
        return BSN

    @staticmethod
    def Del_Rules():
        BSN = BSN_API.GET_Rules()
        for i in BSN.response:
            url = f'https://{BSN.IP}:8443/api/v1/data/controller/applications/bigtap/policy[name="{DTCT["Dirty_Policy"]}"]/rule[sequence={i["sequence"]}]'
            requests.delete(url, headers=BSN.headers, cookies=BSN.cookie, verify=False)


class SyslogUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = bytes.decode(self.request[0].strip())
        socket = self.request[1]
        self.data = str(data)
        self.match()
        # print(getframeinfo(currentframe()).lineno,"%s : " % self.client_address[0], self.data)
        logging.info(self.data)

    def match(self):
        if "ERROR" in self.data:
            Check.error.add(self.data)
        elif "attack started" in self.data:
            matches = re.compile(
                r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+').finditer(
                self.data)
            for match in matches:
                Check.start.add(match.group(0))
        elif "attack ended" in self.data:
            matches = re.compile(
                r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+').finditer(self.data)
            for match in matches:
                Check.end.add(match.group(0))
        elif "Imported successfully" in self.data:
            Check.Import += 1
        elif " term " in self.data:
            Check.dp_term += 1


class Syslog(object):

    def __init__(self):
        Telnet.DP_Syslog_ADD()
        Vision_API.Syslog_ADD()
        t1 = threading.Thread(target=self.Server)
        t1.start()

    # Setting the Syslog server
    def Server(self):
        try:
            try:
                os.remove("syslog_AMS.log")
            except:pass#Silenced
            logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='', filename=DTCT["LOG_FILE"],
                                filemode='a')
            self.server = socketserver.UDPServer((DTCT["Syslog_IP"], 514), SyslogUDPHandler)
            self.server.serve_forever(poll_interval=0.5)
        except (IOError, SystemExit):
            raise
        except KeyboardInterrupt:
            print(getframeinfo(currentframe()).lineno, "Crtl+C Pressed. Shutting down.")

    # Closing the Server and Saves Configuration
    def DELETE(self):
        try:
            Telnet.DP_Syslog_DELETE()
            Vision_API.Syslog_DELETE()
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
        try:
            self.server.shutdown()
        except:
            print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
        api = Vision_API()
        com = api.Get(f"https://{DTCT['Vision_IP']}/mgmt/device/df/config/OngoingProtections", True)
        DTCT["OngoingProtections"] = len(com["OngoingProtections"])
        DTCT.save()


class Check(object):
    """
    Class For All The Tests
    """

    # Count of Syslog Start Detection from DF
    start = set()

    # Count of Syslog End Detection from DF
    end = set()

    # Count of total Syslog errors
    error = set()

    # Count of total Imports to DP
    Import = 0

    # Count of total DP terminations
    dp_term = 0

    class DP(object):
        """
        DP Tests
        """

        @staticmethod
        def Port_Error(Legit_Only=False):
            flag = True  # output flag
            try:
                for i in DTCT.DP_Info.values():  # For all DPs that the DF is in contact with
                    telnet = Telnet(i)
                    com = telnet.Command("system inf-stats")

                    for j in DTCT["DP_Ports"]:  # For the ports the configured at Data_For_TCT.json
                        if (not re.search(rf"{j}\s+[0-9]+\s+0\s+0\s+[0-9]+\s+0\s+0", com, re.IGNORECASE)) and re.search(
                                rf"^{j}\s+", com, re.IGNORECASE):
                            print(f"{getframeinfo(currentframe()).lineno} Port Error:")
                            print(getframeinfo(currentframe()).lineno, com)
                            return False

                    else:
                        if Legit_Only:
                            com = telnet.Command("system internal dpe-statistics total all", True)
                            if (not re.search(rf"DPE Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", com,
                                              re.IGNORECASE)) and (
                                    not re.search(
                                        rf"HW-Accelerator Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", com,
                                        re.IGNORECASE)) and (
                                    not re.search(rf"Total Counters\s+: Forwards\s+=\s+[0-9]+\s+Discards\s+=\s+0", com,
                                                  re.IGNORECASE)):
                                print(
                                    f"{getframeinfo(currentframe()).lineno} dpe-statistics Error:")
                                print(getframeinfo(currentframe()).lineno, com)
                                return False
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

        @staticmethod
        def No_BDOS_Attack():
            flag = False
            try:
                for i in list(DTCT.DP_Info.values()):
                    telnet = Telnet(i)
                    com = telnet.Command("system internal security bdos attacks", True).split("\n")
                    if len(com) > 4:
                        print(f"{getframeinfo(currentframe()).lineno} BDOS ATTACK:")
                        print(getframeinfo(currentframe()).lineno, com)
                        break
                else:
                    flag = True
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

        @staticmethod
        def BDOS_Attacks():
            flag = False
            try:
                for i in list(DTCT.DP_Info.values()):
                    telnet = Telnet(i)
                    com = telnet.Command("system internal security bdos attacks", True).split("\n")
                    if len(com) < 5:
                        print(f"{getframeinfo(currentframe()).lineno} BDOS ATTACK:")
                        print(getframeinfo(currentframe()).lineno, com)
                        break
                else:
                    flag = True
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

        @staticmethod
        def Support_File_Extract():
            flag = False
            try:
                driver = Driver()
                for i in DTCT.DP_Info.keys():
                    driver.Click(f"gwt-debug-DevicesTree_Node_{i}")
                    driver.ClickIf('//*[@title="Click to lock the device"]', delay=3)
                    driver.Click("gwt-debug-DeviceControlBar_Operations")
                    while not driver.Wait("gwt-debug-DeviceControlBar_Operations_getFileFromDevice_Support", delay=10):
                        driver.Click("gwt-debug-DeviceControlBar_Operations")
                    driver.Click("gwt-debug-DeviceControlBar_Operations_getFileFromDevice_Support")
                    flag = file_check()
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                driver.Close()
                return flag

    class DF(object):
        """
        DF Tests
        """

        @staticmethod
        def BGP_Established():
            flag = False
            try:
                api = Vision_API()
                response = api.Get(f'https://{DTCT["Vision_IP"]}/mgmt/device/df/config/BgpPeers')
                for i in response["BgpPeers"]:
                    if i["state"] != "ESTABLISHED":
                        break
                else:
                    flag = True
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

        @staticmethod
        def BGP_Announcements():
            flag = False
            api = Vision_API()
            response1 = api.Get(f'https://{DTCT["Vision_IP"]}/mgmt/device/df/config/BgpPeers')
            response2 = api.Get(f'https://{DTCT["Vision_IP"]}/mgmt/device/df/config/Announcements', True)
            if len(response1["BgpPeers"]) * (len(Check.start) + DTCT["OngoingProtections"]) <= len(
                    response2["Announcements"]):
                """peers = dict()
                for i in response1["BgpPeers"]:
                    try:
                        if i["state"] == "ESTABLISHED":
                            peers[i["localIp"]].add(i["ip"])
                    except KeyError:
                        peers[i["localIp"]] = (i["ip"])
                for i in response2["Announcements"]:
                    if i["status"] == "SUCCESS":"""
                flag = True
            return flag

        @staticmethod
        def Support_File_Extract():
            flag = False
            try:
                driver = Driver()
                driver.DF_Configuration()
                driver.Click("#gwt-debug-Configuration")
                driver.Click("gwt-debug-TopicsNode_dfc-vision-support-content")
                if not driver.Wait("gwt-debug-TopicsNode_dfc-vision-support-content", delay=3):
                    driver.Click("gwt-debug-Configuration")
                driver.Click("gwt-debug-TopicsNode_dfc-vision-support-content")
                while not driver.Wait(
                        "#dfc-vision-support > div > div > div:nth-child(1) > div > div > div:nth-child(1) > button"):
                    driver.Click("gwt-debug-TopicsNode_dfc-vision-support-content")
                driver.Click(
                    "#dfc-vision-support > div > div > div:nth-child(1) > div > div > div:nth-child(1) > button")
                driver.Click(
                    "body > div.ReactModalPortal > div > div > div > div:nth-child(4) > div:nth-child(1) > div > div:nth-child(1) > button")
                flag = file_check(extract=False)
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                driver.Close()
                return flag

    class Vision(object):
        """
        Vision Tests
        """

        @staticmethod
        def Graph_Comparison_BP(Legit_Only=False, driver=None):
            flag = False
            driver_flag = True

            def delete():
                for file in os.listdir(os.getcwd()):
                    if file.endswith(".zip") or file.endswith(".crdownload") or file.endswith(".csv"):
                        os.remove(file)
                try:
                    rmtree("Test_Report")
                except:
                    pass

            try:
                # Downloading Report from Vision
                if not driver:
                    driver = Driver()
                else:
                    driver_flag = False
                driver.Click(
                    "#global-menu > nav > ul > li:nth-child(3) > div.sub-menu-children.sc-feryYK.cwTrTn > div > div > div.NavItemContentstyle__StyledIcon-ob11v-0.WNjlY")
                driver.Click(
                    "#global-menu > nav > ul > li.sub-menu-expanded.sc-gldTML.bYAUWd > div.sc-cJOK.bVfJMK > div:nth-child(8) > div > div.NavItemContentstyle__StyledLabelContainer-ob11v-1.erVzTj")
                if driver.Wait(f'//*[@data-debug-id="vrm-forensics-views-list-item-expand_{DTCT["Fill_Name"]}"]'):
                    driver.Click(f'//*[@data-debug-id="vrm-forensics-views-list-item-expand_{DTCT["Fill_Name"]}"]')
                else:
                    driver.Click(
                        "#main-content > div.vrm-reports-container > div.reports-main-content > div.reports-list-placeholder > div > div.vrm-report-list-title-wrapper > button")
                    driver.Fill(
                        "#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > div > div.wizard-form-content > div.wizard-form-content--header.not-valid > div > div.form-content-header--content > div > div.wizard-form-content-header--input-wrapper > div.new-filter-wrapper > input",
                        DTCT["Fill_Name"])
                    driver.Click('//*[@data-debug-id="template_"]')
                    time.sleep(1)
                    driver.Click('//*[@data-debug-id="template_DefenseFlow Analytics Dashboard"]')
                    driver.Click('#visionAppRoot > div > div > div.footer > button:nth-child(2)')
                    driver.Click(
                        '#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > div > div.wizard-form-content > div.wizard-form-content--main > div > div:nth-child(1) > div.tab-header.collapsed-header.with-error')
                    driver.Click(
                        '#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > div > div.wizard-form-content > div.wizard-form-content--main > div > div:nth-child(1) > div.tab-body.expanded > div > div > div.device-filter-search-bar-container > div > label')
                    driver.Click(
                        '#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > div > div.wizard-form-content > div.wizard-form-content--main > div > div:nth-child(5) > div.tab-header.collapsed-header')
                    driver.Click('#csv')
                    driver.Click(
                        '#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > div > div.wizard-form-footer > div > button.form-button.form-submit')
                    driver.Click(f'//*[@data-debug-id="vrm-forensics-views-list-item-expand_{DTCT["Fill_Name"]}"]')
                driver.Click(
                    "#main-content > div.vrm-reports-container > div.reports-main-content > div.reports-list-placeholder > div > ul > li > div.vrm-reports-item-expaneded-details > div > div.vrm-reports-item-expaneded-details-header > div > button")
                driver.Displayed("div > div > div > div > div.loading-dots--dot-yellow")
                driver.Click(
                    "#main-content > div.vrm-reports-container > div.reports-main-content > div.reports-list-placeholder > div > ul > li > div.vrm-reports-item-expaneded-details > div > div.reports-logs > div > div > ul > li:nth-child(1) > li > a")
                driver.Click(
                    "#main-content > div.vrm-reports-container > div.reports-main-content > div.report-preview > div > div > header > button")
                if not file_check():
                    delete()
                    return flag
                driver.Click(f'//*[@data-debug-id="vrm-forensics-delete-item-button_{DTCT["Fill_Name"]}"]')
                driver.Click(
                    '#main-content > div.vrm-reports-container > div.reports-main-content > div.reports-list-placeholder > div > ul > li > div.vrm-reports-item-main-details.selected > div.vrm-reports-list-item-actions-container > div.vrm-forensics-delete-item-wrapper > div > div.vrm-forensics-delete-item-confirm')
                # Turning the csv files to dataframes
                with open("Traffic_Bandwidth.csv", "r") as csv:
                    TB = read_csv(csv).astype("float64")
                with open("Traffic_Rate.csv", "r") as csv:
                    TR = read_csv(csv).astype("float64")
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
                delete()
                if driver_flag:
                    driver.Close()
                return flag
            try:
                if not os.path.isdir("Test_Report"):
                    BP.CSV_Export()
                with open(os.path.join(cwd, "Test_Report", "Test_Report.csv"), "r") as file:
                    data = file.readlines()
                # index list for slicing the Test_Report later
                index = []
                # indicators where to slice
                strings = ["6.1.2.3. Frames/s", "6.1.2.4. Megabits/s", "6.1.3. [interface=2]", "6.1.3.3. Frames/s",
                           "6.1.3.4. Megabits/s", "6.2. "]
                for k in strings:
                    for i, j in enumerate(data):
                        if k in j:
                            if "Frames/s" in j:
                                index.append(i + 2)
                            else:
                                index.append(i)
                            if "Megabits/s" in j:
                                index.append(i + 2)
                            break
                # TR - Trafic Rate , TB - Trafic Bandwidth
                int1_TR = read_csv(StringIO("".join(data[index[0]:index[1]]))).replace(to_replace=r',', value='',
                                                                                       regex=True).astype(
                    "float64")
                int1_TB = read_csv(StringIO("".join(data[index[2]:index[3]]))).replace(to_replace=r',', value='',
                                                                                       regex=True).astype(
                    "float64")
                # int2_TR = read_csv(StringIO("".join(data[index[4]:index[5]]))).replace(to_replace=r',', value='',
                #                                                                            regex=True).astype(
                #   "float64")
                # int2_TB = read_csv(StringIO("".join(data[index[6]:index[7]]))).replace(to_replace=r',', value='',
                #                                                                            regex=True).astype(
                #   "float64")
                if Legit_Only:
                    Frames = TR[TR['inbound'] > TR['inbound'].max() * 0.5]['inbound'].mean() / \
                             int1_TR[int1_TR['ethTxFrameRate'] > int1_TR['ethTxFrameRate'].max() * 0.5][
                                 'ethTxFrameRate'].mean() > 0.95
                    BW = TB[TB['inbound'] > TB['inbound'].max() * 0.5]['inbound'].mean() / 1000 / \
                         int1_TB[int1_TB['ethTxFrameDataRate'] > int1_TB['ethTxFrameDataRate'].max() * 0.5][
                             'ethTxFrameDataRate'].mean() > 0.91
                    flag = Frames and BW
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                delete()
                if driver_flag:
                    driver.Close()
                return flag

    class FD(object):
        """
        FD Tests
        """

        @staticmethod
        def No_Detection():
            flag = False
            try:
                response = requests.get(f'http://{DTCT["FD_IP"]}:10007/blackhole',
                                        auth=(DTCT["FD_Username"], DTCT["FD_Password"]))
                if len(response.json()["values"]) == 0:
                    flag = True
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

        @staticmethod
        def Detection_Syslog_DF():
            flag = False
            try:
                response = requests.get(f'http://{DTCT["FD_IP"]}:10007/blackhole',
                                        auth=(DTCT["FD_Username"], DTCT["FD_Password"]))
                flag = len(response.json()["values"]) == len(Check.start)
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag

    class BSN(object):
        """
        BSN Tests
        """
        pass

    class Other(object):
        """
        Other Tests
        """

        @staticmethod
        def Ping_All_Components(Fail_Time=5, MSSP=True):
            start = time.perf_counter()
            flag = True
            try:
                if DTCT.DF_HA:
                    Components_List = Vision_API.DF_IP()
                else:
                    Components_List = [Vision_API.DF_IP()[0]]
                Components_List += [i for i in DTCT.DP_Info.values()]
                Components_List.append(DTCT["Vision_IP"])
                if MSSP:
                    match = re.search(r'\d+\.\d+\.\d+\.\d+', DTCT["MSSP_Dash_URL"])
                    Components_List.append(match.group(0))
                while (time.perf_counter() - start < (Fail_Time * 60)):
                    for i in Components_List:
                        flag = flag and ping(i)
                    if flag:
                        break
                    time.sleep(1)
            except:
                print(getframeinfo(currentframe()).lineno, "Unexpected error:", exc_info()[0])
            finally:
                return flag
