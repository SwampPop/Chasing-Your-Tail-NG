import sqlite3
import glob
import json
import os
import pathlib

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

### Check for/make subdirectories for logs, ignore lists etc.
cyt_sub = pathlib.Path('./ignore_lists')
cyt_sub.mkdir(parents=True, exist_ok=True)

non_alert_list = []
non_alert_ssid_list = []

### Get DB path from config
db_path = config['paths']['kismet_logs']

######Find Newest Kismet DB file
list_of_files = glob.glob(db_path)
latest_file = max(list_of_files, key=os.path.getctime)
print('Pulling from: {}'.format(latest_file))

con = sqlite3.connect(latest_file) ## kismet DB to point at

def sql_fetch(con):

    cursorObj = con.cursor()

    cursorObj.execute("SELECT devmac FROM devices")

    rows = cursorObj.fetchall()

    for row in rows:

        #print(row)
        stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
        non_alert_list.append(stripped_val)

sql_fetch(con)

print ('Added {} MACs to the ignore list.'.format(len(non_alert_list)))

# Fix - write to ignore_lists directory
ignore_list = open(pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['mac'], "w")
ignore_list.write("ignore_list = " + str(non_alert_list))
ignore_list.close()

def grab_all_probes(con): 
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac, type, device FROM devices") 
    rows = cursorObj.fetchall()
    for row in rows:
        raw_device_json = json.loads(row[2])
        if 'dot11.probedssid.ssid' in str(row):
            ssid_probed_for = raw_device_json["dot11.device"]["dot11.device.last_probed_ssid_record"]["dot11.probedssid.ssid"] ### Grabbed SSID Probed for
            if ssid_probed_for == '':
                pass
            else:
                non_alert_ssid_list.append(ssid_probed_for)

grab_all_probes(con)

print ('Added {} Probed SSIDs to the ignore list.'.format(len(non_alert_ssid_list)))
# Fix - write to ignore_lists directory
ignore_list_ssid = open(pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['ssid'], "w")
ignore_list_ssid.write("non_alert_ssid_list = " + str(non_alert_ssid_list))
ignore_list_ssid.close()
