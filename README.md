# mystrombutton2mqtt : a gateway from myStrom Wifi Button to MQTT for Home Assistant integration

## Intro

Home Assistant has some [support](https://www.home-assistant.io/integrations/mystrom#binary-sensor) for myStrom products. But I couldn't get functioning the buttons, I get a 401 error. I tried different combinations :
``` yaml
homeassistant:
    - type: trusted_networks
      trusted_networks:
        - 192.168.0.0/21
        - 192.168.1.40
        - 172.17.0.0/24
        - fd00::/8
  - type: legacy_api_password
    api_password: !secret api_password
http:
binary_sensor:
  - platform: mystrom
```
but it doesn't work and the [legacy_api_password](https://www.home-assistant.io/docs/authentication/providers/#legacy-api-password) is deprecated and will be dropped in a future release.

So I decided to create this gateway.
![Schema](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/schema.png)

The goal is to have binary_sensors for single, double, long, _touch_, _wheel_final_ event and sensors for battery level and _wheel event_ (_italic_ only available for Button Plus) automatically created in Devices of Home Assistant. So Home Assistant can suggest Automations.

## Preparation of the button

You need to have a myStrom Wifi button with the minimal Firmware version: 2.74.10.

Please note the MAC address of your button. (only the numbers or letters). It will be know as __\[BUTTON_MAC\]__
You find this address on the purchase box or in myStrom application.
![MAC address on a box](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/macaddress_box.jpg) or 
![MAC address in the app.](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/macaddress_android.jpg)



Identify the IP address of your wifi button. It will be known as __\[BUTTON_IP\]__ .

Identify the IP address of this GATEWAY. It will be known as __\[GATEWAY_IP\]__ .

Note that the port __8321__ is the default port of the gateway and can be modified in the settings.json file.

The following command will erase the previous actions of the button (single , double , long click and touch) and replace them by a generic action.

The actions created in the app seem to be working independently. 

Run the command :
```console
curl -v -d "generic=get://[GATEWAY_IP]:8321/api/mystrom/gen&single=&double=&long=&touch=" http://[BUTTON_IP]/api/v1/device/[BUTTON_MAC]
```

For the myStrom Wifi Button, the button has to be plugged to a charger and press to communicate with your Wifi.

For the myStrom Wifi Button +, you should remove the batteries and insert them again.

## Setting of the gateway

Update and rename the "resources/settings.json.sample" into "resources/settings.json"

Please add the __\[BUTTON_MAC\]__ and a short uniq name of your choice __\[CHOOSEN_NAME\]__ in the section "button" or "buttons+" of the file "resources/settings.json". Personnally I have chosen the color of the rubber band as __\[CHOOSEN_NAME\]__.

## Running

Start the gateway with the command:
```console
python3 mystrombutton2mqtt.py ./resources/settings.json
```
### On the MQTT Broker

The following topics for each button will be published:
```python
## The Discovery Topics
## --------------------
homeassistant/sensor/[BUTTON_MAC]_battery/config
# only if it's a "Button Plus"
homeassistant/sensor/[BUTTON_MAC]_wheel/config  

homeassistant/binary_sensor/[BUTTON_MAC]_single/config 
homeassistant/binary_sensor/[BUTTON_MAC]_double/config 
homeassistant/binary_sensor/[BUTTON_MAC]_long/config
# only if it's a "Button Plus"
homeassistant/binary_sensor/[BUTTON_MAC]_touch/config  
homeassistant/binary_sensor/[BUTTON_MAC]_final_wheel/config  
## The state topics
## ----------------
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/single
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/double
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/long
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/battery
# only if it's a "Button Plus"
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/touch
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/wheel
myStrom/wifi_buttons/[CHOOSEN_NAME]_[BUTTON_MAC]/wheel_final
```

### On Home Assistant
Once the gateway started, Home Assistant (with the option "discovery:" in configuration.yaml and the same MQTT broker as the gateway ) will show the button(s) in "Configuration" > "Device" as "Wifi Button __\[CHOOSEN_NAME\]__" with "MQTT" in the integration column and "myStrom AG" as the manufacturer

![Wifi Buttons in Devices](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/devices.png)

The battery information will be updated after each button action or every 12 hours when the button does a heartbeat.

## mystrombutton2mqtt as a service
If you run the gateway on a raspberry pi, you may want to run is as a service. To do so, create a file:
```console
sudo vi  /lib/systemd/system/mystrombutton2mqtt.service
```

Paste this code and replace the __\[DIRECTORY_PATH\]__ by the correct one:
```ini
[Unit]
Description=myStrom Wifi Buttons 2 MQTT Gateway Service
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=idle
User=pi
WorkingDirectory=[DIRECTORY_PATH]
ExecStart=/usr/bin/python3 [DIRECTORY_PATH]/mystrombutton2mqtt.py [DIRECTORY_PATH]/resources/settings.json

Restart=always

[Install]
WantedBy=multi-user.target
```
Enable the service:
```bash
sudo systemctl enable mystrombutton2mqtt.service
```
Start the service:
```console
sudo systemctl start mystrombutton2mqtt.service
```
Check if it's active:
```console
sudo systemctl status mystrombutton2mqtt.serviceca
```
## Postscritum
Note that I don't have a "Button Plus", so I didn't test it. It is based on the API doc found on [myStrom](https://api.mystrom.ch/?version=latest).
