from flask import Flask, request, Response,  render_template
from functools import wraps
import ssl
import time
import mqttlib
import json.decoder
import fileinput

app = Flask(__name__)

global conn
VALID_USERS = dict()
VALID_TOPICS = set()
VALID_EVENTS = set()
MACS = dict()
ACTIONS = dict()
TYPES = dict()

SUBSCRIBED_TOPICS = dict()


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

    print("################### START ###################") 
    if request.method != 'GET':
        return ("Err (not a GET method")


    event=None
    msg = 'ON'
    mac= request.args['mac']
    print ("mac: "+ mac)
    action= request.args['action']
    print ("action: "+ action)
    if action in ACTIONS:
        event = ACTIONS.get(action)

    print ("event: "+ event)

    if action == 5 and 'wheel' in request.args:
       msg = request.args['wheel']
    print ("msg: "+msg)

    if mac in MACS:
        item= MACS.get(mac)
    else:
        item= 'unknown'
    print ("item: "+item)

    battery = request.args['battery']

    print("battery: "+ battery)
    topik = "myStrom/wifi_buttons/"+item+"_"+mac+"/"+event
    #print ("topic: " + topik)
    if action != 6:
        con.publish(topik,msg,False)
        conn.publish( topic="myStrom/wifi_buttons/"+item+"_"+mac+"/battery",payload=battery,remain=True )
    else:
        conn.publish(topik,msg,True)
    print("################### END ################### ") 
    return "Ok"
    

# publish a Home Assistant Sensor Discory topic
def publish_discovery_sensor(mac,item,action_name,default_action_value,model,unit_of_measurement,device_class,icon):
    if device_class =="None":
        device_class_template =''
    else:
        device_class_template='"device_class": "'+device_class+'",'

    msg_json = '{ \
        "name": "myStrom Wifi Button '+item+' ('+mac+') '+action_name+'", \
        "uniq_id" : "'+mac+'_'+action_name+'",\
        '+ device_class_template +' \
        "unit_of_measurement":"'+unit_of_measurement+'",\
        "device": {\
            "identifiers": ["'+mac+'"],"connections":[["mac","'+nice_macaddress(mac)+'"]],\
            "model" : "'+model+'",\
            "name":"Wifi Button '+item+'",\
            "manufacturer":"myStrom AG"\
        }, \
        "~":"myStrom/wifi_buttons/'+item+"_"+mac+'/",\
        "state_topic": "~'+action_name+'",\
        "value_template":"{{ value  | upper }}"\
        }'
    #Configuration topic: 
    conn.publish( topic="homeassistant/sensor/"+mac+"_"+action_name+"/config",payload=msg_json,remain=True)
    #State topic: 
    conn.publish("myStrom/wifi_buttons/"+item+"_"+mac+"/"+action_name , default_action_value )


# MAc address in shape 01:23:45:67:AB
def nice_macaddress(mac):
    text = mac.replace('.', '').replace('-','').upper()   # a little pre-processing
    # chunk into groups of 2 and re-join
    out = ':'.join([text[i : i + 2] for i in range(0, len(text), 2)])  
    return out

# publish a Home Assistant Binary_Sensor Discory topic
def publish_discovery_binary_sensor( mac,item,action_name,default_action_value,model,icon):
    
    msg_json = '{ \
        "name": "myStrom Wifi Button '+item+' ('+mac+') '+action_name+'", \
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
        "off_delay": 1 \
        }'
    #Configuration topic: 
    conn.publish( topic="homeassistant/binary_sensor/"+mac+"_"+action_name+"/config",payload=msg_json,remain=True)
    #State topic: 
    conn.publish("myStrom/wifi_buttons/"+item+"_"+mac+"/"+action_name, default_action_value)
    

def publish_discovery_button_plus( mac,item):
    publish_discovery_button( mac,item,"Button Plus")
    publish_discovery_binary_sensor(mac,item,"touch","OFF","Button Plus","mdi:gesture-tap")
    publish_discovery_binary_sensor(mac,item,"wheel_final","OFF","Button Plus","mdi:sync")
    publish_discovery_sensor(mac=mac,item=item,action_name="wheel",default_action_value="",model="Button Plus",unit_of_measurement="",device_class="None",icon="mdi:sync")

def publish_discovery_button( mac,item,model):
    publish_discovery_binary_sensor(mac,item,"single","OFF",model,"mdi:radiobox-blank")
    publish_discovery_binary_sensor(mac,item,"double","OFF",model,"mdi:circle-double")
    publish_discovery_binary_sensor(mac,item,"long","OFF",model, "mdi:radiobox-marked")
    publish_discovery_sensor(mac=mac,item=item,action_name="battery", default_action_value="",model=model,unit_of_measurement=" %",device_class="battery",icon="mdi:battery-60")

def publish_discovery():
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

    try:
        settings = json.loads(data)

        # users
#        for user in settings["http"]["valid_users"]:
#            VALID_USERS[user] = settings["http"]["valid_users"][user]

        # topics
        for topic in settings["mqtt"]["valid_topics"]:
            VALID_TOPICS.add(topic)


        for mac in settings["mystrom"]["button"]:
            MACS[mac.upper()] =  settings["mystrom"]["button"][mac]
            TYPES[mac.upper()] =  "button"
        for mac in settings["mystrom"]["button+"]:
            MACS[mac.upper()] =  settings["mystrom"]["button+"][mac]
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
    print ("Action Map:")
    print (ACTIONS)
    print ("MAC Map:")
    print (MACS)
    conn = mqttlib.MqttConnection(settings["mqtt"], mqtt_message_callback)

    conn.connect()
    print ("Publish discovery topics")
    publish_discovery()

    app.run(ssl_context=context, port=settings["http"]["port"], host='0.0.0.0')
    conn.disconnect()
