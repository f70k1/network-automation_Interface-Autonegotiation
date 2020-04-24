from time import time
import sys
import ipaddress

import threading
from multiprocessing.dummy import Pool as ThreadPool

import csv

from netmiko import ConnectHandler
from getpass import getpass
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from netmiko.ssh_exception import AuthenticationException
import re
#------------------------------------------------------------------------------
def config_worker( CONFIG_PARAMS_LIST):
    IP_ADDRESS_DEVICE = CONFIG_PARAMS_LIST [0]
    USERNAME = CONFIG_PARAMS_LIST [1]
    PASSWORD = CONFIG_PARAMS_LIST [2]

    ios_devices = {
        "device_type": "cisco_ios",
        "ip": IP_ADDRESS_DEVICE,
        "username": USERNAME,
        "password": PASSWORD
    }
    for i in range (1,2):
        try:
            net_connect = ConnectHandler(**ios_devices)
        except (AuthenticationException):
            print ("**** Error: Authentication failure: " + IP_ADDRESS_DEVICE + " ****")
            continue
        except (NetMikoTimeoutException):
            print ("**** Error: Timeout to device: " + IP_ADDRESS_DEVICE + " ****")
            continue
        except (EOFError):
            print ("**** Error: End of file while attempting device: " + IP_ADDRESS_DEVICE + " ****")
            continue
        except (SSHException):
            print ("**** Error: SSH Issue. Are you sure SSH is enabled?:  " + IP_ADDRESS_DEVICE + " ****")
            continue
        except Exception as unknown_error:
            print ("**** Error: Some other error " + IP_ADDRESS_DEVICE + " ****")
            continue

        #get hostname
        net_connect.send_config_set("terminal length 0")
        output_hostname = net_connect.send_command("show run | i hostname")
        output_hostname = output_hostname.replace("\r","").replace("\n","").split(" ")
        hostname =  (output_hostname[1])
        #get interface
        output_interface = net_connect.send_command("show ip interface brief")
        intf_pattern = "^[lLgGeEfF]\S+[0-9]/?[0-9]*"
        regex = re.compile(intf_pattern)
        for row in output_interface.splitlines():
            if regex.search(row):
                INTERFACE = row.split()[0]
                STATUS = row.split()[4]
                PROTOCOL = row.split()[5]
                
                if "up" == STATUS:
                    output_interface_config = net_connect.send_command("show running-config interface " + INTERFACE)
                    interface_config = output_interface_config.find("negotiation auto")
                    if interface_config > 0:
                        negotiation = ("OK")
                    else:
                        negotiation = ("NOK")
                    interface_config = output_interface_config.find("speed auto")
                    if interface_config > 0:
                        speed = ("OK")
                    else:
                        speed = ("NOK")
                    interface_config = output_interface_config.find("duplex auto")
                    if interface_config > 0:
                        duplex = ("OK")
                    else:
                        duplex = ("NOK")
                        
                        
                    if INTERFACE.find("Loop") < 0:
                         if negotiation ==("NOK") and speed == ("NOK") and duplex == ("NOK"):
                             print (hostname + " " + INTERFACE + " no auto port")
                         elif negotiation == ("NOK") and speed == ("NOK") or duplex == ("NOK"):
                             print (hostname + " " + INTERFACE + " Speed or duplex wrong")

        net_connect.disconnect()

    return


#==============================================================================
# ---- Main: Get Configuration
#==============================================================================
print ("check Interface mode ('auto') \n this tool connects to network components and check if the interface in auto")

USERNAME = input("Enter your SSH-Username (cisco): ") or "cisco"
PASSWORD = getpass("Enter your SSH-Password (cisco): ") or "cisco"

#read IP-address-list, any seperator possible
IP_ADDRESS_CSV_FILE = input ("Input CSV filename (ip-device.csv) :  ") or "ip-device.csv"
SPLIT = input ("seperator (,): ") or ","
try:
    IP_ADDRESS_CSV=open(IP_ADDRESS_CSV_FILE)
except:
    print("**** Error: can't open IP-address-file ****")
    sys.exit()
IP_ADDRESS_LIST_RAW = IP_ADDRESS_CSV.read()
IP_ADDRESS_CSV.close()
#format list
IP_ADDRESS_LIST_LINE = IP_ADDRESS_LIST_RAW.split(chr(10))
IP_ADDRESS_LIST = []
for LINE in IP_ADDRESS_LIST_LINE:
    if LINE:
        IP_ADDRESS_LIST.append(LINE.split(SPLIT))
print(IP_ADDRESS_LIST[0])
#take the right column
try:
    IP_ADDRESS_COLUMN = int(input("Column with IP-address (3): ") or "3")
except:
    print("**** Error: Input-type ****")
    sys.exit()
try:
    THREAD_NUMBER = int(input("How many Threats parallel (3): ") or "3")
except:
    print("**** Error: Input-type ****")
    sys.exit()
print ("")
#Technicians start counting at 1, computer scientists at 0
IP_ADDRESS_COLUMN = IP_ADDRESS_COLUMN - 1
#take the ip-address and start threads

#Threadpool config
CONFIG_PARAMS_LIST = []
threads = ThreadPool( THREAD_NUMBER )

#Start Action
starting_time = time()
try:
    for row in IP_ADDRESS_LIST:
        IP_ADDRESS = str.strip(str(row[IP_ADDRESS_COLUMN]))
        try:
            print ('Creating thread for:', ipaddress.ip_address(IP_ADDRESS))
            CONFIG_PARAMS_LIST.append( ( IP_ADDRESS, USERNAME, PASSWORD) )

        except:
            print ("**** Error: no IP-address: " + IP_ADDRESS + " ****")
except:
    print ("**** Error: seperator ****")

print ("\n--- Creating threadpool and launching ----\n")
results = threads.map( config_worker, CONFIG_PARAMS_LIST)

threads.close()
threads.join()

print ("\n---- End threadpool, elapsed time= " + str(round(time()-starting_time)) + "sec ----")
