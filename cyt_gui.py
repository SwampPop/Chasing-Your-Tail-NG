import tkinter as tk
import subprocess
import os
import pathlib
import sqlite3
import glob
import json
import time

# Load config once at startup
with open('config.json', 'r') as f:
    config = json.load(f)

def check_status():
    print("Checking Status")
    subprocess.call(["lxterminal", "-e", "./monitor.sh"])
    
def delete_ignore_lists():
    print("Deleting Ignore Lists")
    ignore_dir = pathlib.Path('./ignore_lists')
    try:
        # Delete mac list using config path
        mac_list = ignore_dir / config['paths']['ignore_lists']['mac']
        if mac_list.exists():
            os.remove(mac_list)
            
        # Delete SSID list using config path   
        ssid_list = ignore_dir / config['paths']['ignore_lists']['ssid']
        if ssid_list.exists():
            os.remove(ssid_list)
            
        print("Ignore lists deleted successfully")
    except Exception as e:
        print(f"Error deleting ignore lists: {e}")
    
def check_kismet_db():
    """Check if Kismet database exists and is accessible."""
    db_path = config['paths']['kismet_logs']
    list_of_files = glob.glob(db_path)
    if not list_of_files:
        return None, "No Kismet database files found. Make sure Kismet is running and creating log files."
    try:
        latest_file = max(list_of_files, key=os.path.getctime)
        # Test if we can connect to the database
        with sqlite3.connect(latest_file) as con:
            cursor = con.cursor()
            cursor.execute("SELECT COUNT(*) FROM devices")
        return latest_file, None
    except sqlite3.OperationalError:
        return None, f"Found database at {latest_file} but couldn't read it. Make sure Kismet has permissions to write logs."
    except Exception as e:
        return None, f"Unexpected error accessing database: {str(e)}"

def create_ignore_lists():
    print("Creating Ignore Lists")
    
    # Check Kismet DB first
    db_file, error = check_kismet_db()
    if error:
        print(f"Error: {error}")
        return
        
    # Create ignore_lists directory if it doesn't exist
    ignore_dir = pathlib.Path('./ignore_lists')
    ignore_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize lists
    non_alert_list = []
    non_alert_ssid_list = []
    
    # Find newest Kismet DB file
    db_path = config['paths']['kismet_logs']
    list_of_files = glob.glob(db_path)
    if not list_of_files:
        print("No Kismet database files found!")
        return
        
    latest_file = max(list_of_files, key=os.path.getctime)
    print('Pulling from: {}'.format(latest_file))
    
    # Connect to database
    with sqlite3.connect(latest_file) as con:
        # Get ALL MAC addresses
        cursor = con.cursor()
        cursor.execute("SELECT devmac FROM devices")
        rows = cursor.fetchall()
        
        total_devices = len(rows)
        for row in rows:
            stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
            if stripped_val not in non_alert_list:  # Avoid duplicates
                non_alert_list.append(stripped_val)
            
        print(f'Added {len(non_alert_list)} MACs to the ignore list.')
        
        # Get ALL probe requests
        cursor.execute("SELECT devmac, type, device FROM devices")
        rows = cursor.fetchall()
        
        for row in rows:
            raw_device_json = json.loads(row[2])
            dot11_device = raw_device_json.get('dot11.device', {})
            if dot11_device:  # If it's a WiFi device
                last_probe = dot11_device.get('dot11.device.last_probed_ssid_record', {})
                ssid = last_probe.get('dot11.probedssid.ssid')
                if ssid and ssid not in non_alert_ssid_list:  # If there's a new probe SSID
                    non_alert_ssid_list.append(ssid)
                    
        print(f'Added {len(non_alert_ssid_list)} Probed SSIDs to the ignore list.')
    
    # Write the ignore lists with correct filenames from config
    with open(ignore_dir / config['paths']['ignore_lists']['mac'], 'w') as f:
        f.write("ignore_list = " + str(non_alert_list))
        
    with open(ignore_dir / config['paths']['ignore_lists']['ssid'], 'w') as f:
        f.write("non_alert_ssid_list = " + str(non_alert_ssid_list))
    
def run_cyt():
    print("Running CYT")
    subprocess.call(["python3", "./chasing_your_tail.py"])

root = tk.Tk()
root.title('Chasing Your Tail Viewer')
frame = tk.Frame(root)
frame.pack()

button_quit = tk.Button(frame, 
                       text="QUIT", 
                       width=15,
                       height=5,
                       fg="red",
                       relief="groove",
                       command=quit)
button_quit.pack(side=tk.LEFT)

check_status = tk.Button(frame,
                       text="Check Status",
                           width=15,
                           height=5,
                           fg="green",
                           relief="groove",
                           command=check_status)
check_status.pack(side=tk.LEFT)

frame = tk.Frame(root)
frame.pack()

button = tk.Button(frame,
    relief="groove",
    text="Delete Ignore Lists",
    width=15,
    height=5,
    fg="red",
    command=delete_ignore_lists)
button.pack(side=tk.LEFT)

create_ignore = tk.Button(frame,
                       width=15,
                       height=5,
                       text="Create Ignore Lists",
                       relief="groove",
                       command=create_ignore_lists)
create_ignore.pack(side=tk.LEFT)

butn_run_cyt = tk.Button(frame,
                       width=16,
                       height=5,
                       fg="green",
                       text="Run Chasing Your Tail",
                       relief="groove",
                       command=run_cyt)
butn_run_cyt.pack(side=tk.LEFT)

root.mainloop()
