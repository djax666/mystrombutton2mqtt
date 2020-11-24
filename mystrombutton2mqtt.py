from flask import Flask, request, Response,  render_template
from functools import wraps
import ssl
import time

import logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.DEBUG)

import mqttlib
import json.decoder
import os
from os import path
import fileinput

app = Flask(__name__)

global conn
VALID_USERS = dict()
VALID_TOPICS = set()
VALID_EVENTS = set()
MACS = dict()
LEVEL = dict()
LEVEL_MIN = dict()
LEVEL_MAX = dict()
ACTIONS = dict()
TYPES = dict()

SUBSCRIBED_TOPICS = dict()

PREFIX = ""


def mqtt_message_callback(msg_topic, msg_payload):
    if msg_topic in SUBSCRIBED_TOPICS:
        SUBSCRIBED_TOPICS[msg_topic] = msg_payload


# ----------------------------------------------------------------------------------------------------------------------
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username in VALID_USERS and password == VALID_USERS[username]


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'POST':
            if check_auth(request.form['username'], request.form['password']):
                return f(*args, **kwargs)
        elif request.method == 'GET':
            if check_auth(request.args.get('username',''), request.args.get('password','')):
                return f(*args, **kwargs)
        return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401)

    return decorated


# ----------------------------------------------------------------------------------------------------------------------

@app.route('/')
def root():
    return render_template('index.html')
    
@app.route('/api/mystrom/gen')
def gen():
    """ receive an generic event from a button and publish it on the MQTT Broker """
    logging.debug("################### START ###################") 
    if request.method != 'GET':
        return ("Err (not a GET method")

    event=None
    mac= request.args['mac']
    logging.debug ("mac: "+ mac)
    action= request.args['action']
    logging.debug ("action: "+ action)
    if action in ACTIONS:
        event = ACTIONS.get(action)

    logging.debug ("event: "+ event)

    if mac in MACS:
        item= MACS.get(mac)
    else:
        item= 'unknown'
    logging.debug ("item: "+item)

    battery = request.args['battery']

    if action == "5" and 'wheel' in request.args: 
        # if it's "wheel" event
        wheel = request.args['wheel']
        LEVEL[mac] += int(wheel)
        if LEVEL[mac] > LEVEL_MAX[mac]:
            LEVEL[mac] = LEVEL_MAX[mac]
        if LEVEL[mac] < LEVEL_MIN[mac]:
            LEVEL[mac] = LEVEL_MIN[mac]
        
        conn.publish( topic="myStrom/wifi_buttons/"+item+"_"+mac+"/wheel", payload=wheel     ,retain=False )
        conn.publish( topic="myStrom/wifi_buttons/"+item+"_"+mac+"/level", payload=LEVEL[mac],retain=True  )
        conn.publish( topic="myStrom/wifi_buttons/"+item+"_"+mac+"/battery", payload=battery ,retain=True  )  
    elif action == "6": 
        # if it's the heartbeat action
        conn.publish( topic="myStrom/wifi_buttons/"+item+"_"+mac+"/battery", payload=battery,retain=True )  
    else: 
        # if it's the other events (nor heartbeat, nor wheel)
        conn.publish(topic="myStrom/wifi_buttons/"+item+"_"+mac+"/battery", payload=battery,retain=True ) 
        topic = "myStrom/wifi_buttons/"+item+"_"+mac+"/"+event
        conn.publish(topic=topic, payload='ON', retain=False)
        # reset the event to "OFF" that is needed because HA automation is triggered by a change of state
        # normally the MQTT configuration variable "off_delay" should do that, but seems to have been cancelled on 15th of Nov 2018:
        # - https://community.home-assistant.io/t/mqtt-button-automations-issues/80893/16.
        # - https://github.com/home-assistant/home-assistant/pull/18389
        # but it's still in the doc in 2020. Why??? https://www.home-assistant.io/integrations/binary_sensor.mqtt/#off_delay
        #  
        time.sleep(1) 
        conn.publish(topic=topic, payload='OFF', retain=False) 
        
    logging.debug("################### END ################### ") 
    return "Ok"

def publish_discovery_sensor(mac,item,action_name,default_action_value,model,unit_of_measurement,device_class,icon,prefix, retain=False):
    """ publish a Home Assistant Sensor Discovery topic """
    if device_class =="None":
        device_class_template =''
    else:
        device_class_template='"device_class": "'+device_class+'",'

    icon_template= '' #'"ic":"'+icon+'",'
    
    msg_json = '{"name": "myStrom Wifi Button '+item+' ('+mac+') '+action_name+'", \
'+ icon_template +'\
'+ device_class_template +' \
"uniq_id" : "'+mac+'_'+action_name+'",\
"unit_of_measurement":"'+unit_of_measurement+'",\
"device": {\
"identifiers": ["'+mac+'"],"connections":[["mac","'+nice_macaddress(mac)+'"]],\
"model" : "'+model+'",\
"name":"Wifi Button '+item+'",\
"manufacturer":"myStrom AG"}, \
"~":"myStrom/wifi_buttons/'+item+"_"+mac+'/",\
"state_topic": "~'+action_name+'",\
"value_template":"{{ value  | upper }}"}'
    #Configuration topic: 
    conn.publish( topic=prefix+"/sensor/myStrom/"+mac+"_"+action_name+"/config",payload=msg_json,retain=True)
    #State topic: 
    conn.publish("myStrom/wifi_buttons/"+item+"_"+mac+"/"+action_name , default_action_value,retain=retain )

def nice_macaddress(mac):
    """ MAc address in shape 01:23:45:67:AB """
    text = mac.replace('.', '').replace('-','').upper()   # a little pre-processing
    # chunk into groups of 2 and re-join
    out = ':'.join([text[i : i + 2] for i in range(0, len(text), 2)])  
    return out


def publish_discovery_binary_sensor( mac,item,action_name,default_action_value,model,icon,prefix):
    """ publish a Home Assistant Binary_Sensor Discovery topic """

    icon_template= '' #'"ic":"'+icon+'",'

    msg_json = '{"name": "myStrom Wifi Button '+item+' ('+mac+') '+action_name+'", \
 '+ icon_template +'\
"uniq_id" : "'+mac+'_'+action_name+'",\
"device": {\
"identifiers": ["'+mac+'"],"connections":[["mac","'+nice_macaddress(mac)+'"]],\
"model" : "'+model+'",\
"name":"Wifi Button '+item+'",\
"manufacturer":"myStrom AG"\
}, \
"~":"myStrom/wifi_buttons/'+item+"_"+mac+'/",\
"state_topic": "~'+action_name+'",\
"value_template":"{{ value  | upper }}",\
"payload_on":"ON",\
 "payload_off":"OFF",\
 "off_delay": 1 }'
    #Configuration topic: 
    conn.publish(topic=prefix+"/binary_sensor/myStrom/"+mac+"_"+action_name+"/config",payload=msg_json,retain=True)
    #State topic: 
    conn.publish("myStrom/wifi_buttons/"+item+"_"+mac+"/"+action_name, default_action_value)

def publish_discovery_button_plus( mac,item):
    """ publish Home Assistant Discory topics for a button plus """
    publish_discovery_button( mac,item,"Button Plus")
    publish_discovery_binary_sensor(mac,item,"touch","OFF","Button Plus","mdi:gesture-tap", PREFIX)
    publish_discovery_binary_sensor(mac,item,"wheel_final","OFF","Button Plus","mdi:sync", PREFIX)
    publish_discovery_sensor(mac=mac,item=item,action_name="wheel",default_action_value="0",\
        model="Button Plus",unit_of_measurement="",device_class="None",icon="mdi:sync",prefix=PREFIX)
    publish_discovery_sensor(mac=mac,item=item,action_name="level",default_action_value=LEVEL[mac],\
        model="Button Plus",unit_of_measurement="",device_class="None",icon="mdi:label-percent",prefix=PREFIX,retain=True)


def publish_discovery_button( mac,item,model):    
    """ publish Home Assistant Discory topics for a button """
    publish_discovery_binary_sensor(mac,item,"single","OFF",model,"mdi:radiobox-blank",PREFIX)
    publish_discovery_binary_sensor(mac,item,"double","OFF",model,"mdi:circle-double",PREFIX)
    publish_discovery_binary_sensor(mac,item,"long","OFF",model, "mdi:radiobox-marked",PREFIX)
    publish_discovery_sensor(mac=mac,item=item,action_name="battery", default_action_value="-1",\
        model=model,unit_of_measurement=" %",device_class="battery",icon="mdi:battery-60",prefix=PREFIX,retain=True)

def publish_discovery():
    """ publish Home Assistant Discory topics for every button plus and every button """
    for mac in TYPES:
        if TYPES[mac] == "button":
            publish_discovery_button(mac, MACS[mac],"Button")
        elif TYPES[mac] =="button+":
            publish_discovery_button_plus(mac, MACS[mac])


if __name__ == '__main__':
    # parse input
    data = str()
    for line in fileinput.input():
        data = data + line

    settings = None
    levels_json_path = "./resources/levels.json"

    try:
        settings = json.loads(data)

        if not 'version' in settings:
            print("The version of the settings must be specified.")
            exit(1)
            
        if  settings["version"] != 3:
           print('Please update the settings file to the version 3')
           exit(1) 
        
        PREFIX = settings["mqtt"]["discoveryprefix"]
        # users
        # for user in settings["http"]["valid_users"]:
        #     VALID_USERS[user] = settings["http"]["valid_users"][user]

        # topics
        for topic in settings["mqtt"]["valid_topics"]:
            VALID_TOPICS.add(topic)


        for mac in settings["mystrom"]["button"]:
            MACS[mac.upper()] =  settings["mystrom"]["button"][mac]["name"]
            TYPES[mac.upper()] =  "button"
        

        if os.path.exists(levels_json_path) and os.path.isfile(levels_json_path):
            with open(levels_json_path) as json_file:
                LEVEL = json.load(json_file)

        if "button+" in settings["mystrom"]:
            for mac in settings["mystrom"]["button+"] or []:
              MACS[mac.upper()] =  settings["mystrom"]["button+"][mac]["name"]
              LEVEL_MIN[mac.upper()] = settings["mystrom"]["button+"][mac]["level_min"]
              LEVEL_MAX[mac.upper()] = settings["mystrom"]["button+"][mac]["level_max"]
              if not mac.upper() in LEVEL:
                  LEVEL[mac.upper()] = settings["mystrom"]["button+"][mac]["level"]
              TYPES[mac.upper()] =  "button+"

        for subscribed_topic in settings["mqtt"]["subscribed_topics"]:
            SUBSCRIBED_TOPICS[subscribed_topic] = b''
    except json.decoder.JSONDecodeError as e:
        print('Invalid json file! Please check your settings!')
        print(e)
        exit(1)

    if settings["http"]["ssl"] == "true":
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.load_cert_chain(settings["http"]["certfilepath"], settings["http"]["keyfilepath"])
    else:
        context = None

    VALID_EVENTS = [ "single",   "double",   "long",   "touch",   "wheel",   "wheel_final"]
    ACTIONS= {
        "1"  : "single",
        "2"  : "double",
        "3"  : "long",
        "4"  : "touch",
        "5"  : "wheel",
        "11" : "wheel_final",
        "6"  : "battery"
    }

    conn = mqttlib.MqttConnection(settings["mqtt"], mqtt_message_callback)

    conn.connect()
    logging.debug ("Publish discovery topics")
    publish_discovery()

    app.run(ssl_context=context, port=settings["http"]["port"], host='0.0.0.0')

    conn.disconnect()

    with open(levels_json_path, 'w') as outfile:
        json.dump(LEVEL, outfile)
        logging.debug( "Levels written on:" + levels_json_path)

    logging.debug( "Clean exit!!! Bye...")
    
