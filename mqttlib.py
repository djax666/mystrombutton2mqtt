# MQTT

import ssl
import paho.mqtt.client as mqtt
import logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.DEBUG)


class MqttConnection(object):
    def __init__(self, settings, callback=None):
        self._ip = settings["brokeraddress"]
        self._port = settings["brokerport"]
        self._connected = False
        self._subscribed_topics = settings["subscribed_topics"]
        self._callback = callback
        self._mqttc = mqtt.Client()
        self._mqttc.on_connect = self._onconnect
        self._mqttc.on_disconnect = self._ondisconnect
        self._mqttc.on_message = self._onmessage

        if "brokerusername" in settings:
            self._mqttc.username_pw_set(settings["brokerusername"], settings["brokerpassword"])

        if settings["brokerssl"]:
            self._mqttc.tls_set(ca_certs=settings["cafilepath"], certfile=settings["certfilepath"],
                                keyfile=settings["keyfilepath"], cert_reqs=ssl.CERT_NONE)
            self._mqttc.tls_insecure_set(True)
        logging.debug('MQTTClient initialized')

    def _onconnect(self, mqttc, userdata, flags, rc):
        self._connected = True
        logging.debug('MqttConnection.onConnected()')

        for t in self._subscribed_topics:
            self.subscribe(t)

    def _ondisconnect(self, mqttc, userdata, rc):
        self._connected = False
        if rc != 0:
            logging.debug('MqttConnection.onDisconnected() -> error! Reconnecting...')
            # self.connect()  # Done automatically!

    def _onmessage(self, mqttc, obj, msg):
        logging.debug('MqttConnection.onMessage() %s %s' % (str(msg.topic), str(msg.payload)))
        if self._callback:
            self._callback(msg.topic, msg.payload)

    def isConnected(self):
        return self._connected

    def connect(self):
        self._mqttc.connect(self._ip, self._port)
        self._mqttc.loop_start()
        logging.debug('MQTTClient connected')

    def disconnect(self):
        self._mqttc.loop_stop(True)
        logging.debug('MQTTClient disconnected')

    def publish(self, topic, payload=None):
        logging.info('MqttConnection.publish(%s, %s)' % (str(topic), str(payload)))
        a, b = self._mqttc.publish(topic, payload)
        return a == mqtt.MQTT_ERR_SUCCESS

    def subscribe(self, topic):
        logging.info('MqttConnection.subscribe(%s)' % str(topic))
        a,b = self._mqttc.subscribe(topic)
        return a == mqtt.MQTT_ERR_SUCCESS

    def unsubscribe(self, topic):
        logging.info('MqttConnection.unsubscribe(%s)' % str(topic))
        a,b = self._mqttc.unsubscribe(topic)
        return a == mqtt.MQTT_ERR_SUCCESS

    # ------------------------------------------------------------------------------------------------------------------
