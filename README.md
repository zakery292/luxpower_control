# LuxPower Control & DB Addon for Home Assistant

## Introduction
The "LuxPower Control & DB" addon integrates seamlessly with the LuxPower charge control HACS integration. It is designed to create a database and host scripts that are crucial for calculating battery entities within the LuxPower charge control system.

For more details on the LuxPower charge control HACS integration, visit: [LuxPower Charge Control HACS Integration](https://github.com/zakery292/charge_controller).

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fzakery292%2Fcharge_controller)

## Features
- Creates and manages a database for storing essential calculation data.
- Easy access to the database via addon_config folder, accessible through Samba share.

## Prerequisites
- Home Assistant Supervisor installation.
- An operational MQTT broker (either Home Assistant's built-in broker or a separate one).
## If using not using Home Assistant Supervised
If your not using Home Assistant Supervised then you will need to build and mount your own docker image of this repo and then run it localy inside your docker instance. instructions for this will not be provided and no support will be given for such installations in this repo as you will be required to edit the code and bash scripts. The sole reason this was created was to make life easier for people wanting to use the battery forecasting.
## Installation Guide

### Step 1: Access Addon Store
Navigate to the addon store in your Home Assistant settings.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/9caf0ef3-7092-4adb-b15c-af80e29f94b5" alt="Step 1" width="200" height="300"/>

### Step 2: Open Addon Store
Click on the blue addon store icon.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/e378bc78-f2a1-4310-b898-b01e1379438f" alt="Step 2" width="200" height="300"/>

### Step 3: Add Repository
Click the three dots at the top and select 'Add Repository'.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/85dad2db-337f-4807-84b8-bf37354411f5" alt="Step 2" width="200" height="300"/>

### Step 4: Repository URL
Copy the URL of this page and paste it into the dialog box, then click 'Add'.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/c5d48ee9-58d2-4fe3-95f5-41e884ca2890" alt="Step 2" width="200" height="300"/>

### Step 5: Install Addon
Refresh the page. The addon should appear at the bottom of the list. Click on it and select 'Install'.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/b124b49b-b76b-4f0f-aa27-4a7514c6f6ee" alt="Step 2" width="200" height="300"/>

### Step 6: MQTT Setup
Configure the MQTT settings using either a local MQTT broker (like Mosquitto broker) or your own.

<img src="https://github.com/zakery292/charge_controller/assets/112213249/11892cab-46b8-48f7-a778-8ab7752f0480" alt="Step 2" width="200" height="300"/>

### Step 7: Starting the Addon
Select 'Save' and then 'Start' the addon.
#### Ensure you have the HACS integration installed.
#### Post-Installation
### Confirming Addon Operation
Check the Home Assistant logs to confirm that the addon has started without errors.
### MQTT Data Monitoring
Monitor the following MQTT topics to confirm data transmission:

battery_soc/request
battery_soc/response
battery_automation/grid_data
battery_automation/rates_data
battery_automation/soc_data
Reporting Issues
Encounter an issue? Please raise it on the GitHub repository under the 'Issues' section. Your feedback helps improve the addon.

