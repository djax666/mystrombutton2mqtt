# mystrombutton2mqtt : A gateway for myStrom Wifi Button to MQTT for Home Assistant integration

## Intro

Home Assistant has some support for myStrom products. But I couldn't get functioning the buttons, I get a 401 error. I tried different options :
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
  - mystrom
```
but it doesn't work and the [legacy_api_password](https://www.home-assistant.io/docs/authentication/providers/#legacy-api-password) will be deprecated.

## Preparation of the button

You need to have a mystrom wifi button with the minimal Firmware version: 2.74.10.

Please note the MAC address of your button. (only the numbers or letters). It will be know as __BUTTON_MAC__
You find this address on the purchase box or in myStrom application.
![MAC address on a box](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/macaddress_box.jpg) or 
![MAC address in the app.](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/macaddress_android.jpg)

Identify the IP address of your wifi button. it will be known as __BUTTON_IP__
Identify the IP address of this GATEWAY. It will be known as __GATEWAY_IP__
Note that the port 8321 is the default port of the GATEWAY and can be modified in the settings files.
The following command will erase the previous actions of the button (single , double , long click and touch) and replace them by a generic action.
Run the command :
``` bash
curl -v -d "generic=get://GATEWAY_IP:8321/api/mystrom/gen&single=&double=&long=&touch=" http://BUTTON_IP/api/v1/device/BUTTON_MAC
```

For the myStrom Wifi Button, the button has to be plugged to a charger and press to communicate with your Wifi.
For the myStrom Wifi Button +, you should remove the batteries and insert them again.

## Update and rename the resources/settings.json.sample in settings.json

Please add the __MAC_BUTTON__ and a short uniq name of your choice __CHOOSEN_NAME__ in the section "button" or "buttons+" of the file resources/settings.json

## Running

Start the daemon with the command:
``` bash
python3 mystrombutton2mqtt.py ./resources/settings.json
```
Once the gateway started, Home Assistant (with the option "discovery:" in configuration.yaml and the same MQTT broker as the gateway ) will show the button(s) in "Configuration" > "Device" as "Wifi Button __CHOOSEN_NAME__" with MQTT in the integration column and "myStrom AG" as the manufacturer

![Wifi Buttons in Devices](https://raw.githubusercontent.com/djax666/mystrombutton2mqtt/master/static/devices.png)
