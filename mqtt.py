import time
import os
import json
import paho.mqtt.client as mqtt
from datetime import datetime as dt

from tcsession import TCSSession
from api_models import ZoneStatusEnum

session_key = os.getenv("SESSION_KEY")
app_id      = int(os.getenv("APPID"))
pin         = os.getenv("PIN")
sleep       = int(os.getenv("UPDATE_SLEEP_SECONDS"))

mqtt_host     = os.getenv("MQTT_HOST")
mqtt_port     = int(os.getenv("MQTT_PORT"))
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
mqtt_qos      = int(os.getenv("MQTT_QOS"))
mqtt_retain   = os.getenv("MQTT_RETAIN").lower() == 'true'

mqtt_topic_base     = 'tecnoalarm'
mqtt_topic_centrale = 'centrale'
mqtt_topic_zone     = 'zones'
mqtt_topic_program  = 'programs'

s = TCSSession(session_key, app_id)
s.get_centrali()
centrale = s.centrali[pin]
s.select_centrale(centrale.tp)

def clean_name(str):
    return str \
        .replace(" ", "_") \
        .replace(".", "_") \
        .replace("-", "_") \
        .lower()

if __name__ == '__main__':
    mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttClient.username_pw_set(mqtt_username, mqtt_password)
    mqttClient.connect(mqtt_host, mqtt_port, sleep+60)
    mqttClient.loop_start()

    topic   = "{}/{}".format(mqtt_topic_base, mqtt_topic_centrale)
    message = centrale.tp.model_dump()
    message.pop('status', None)
    message = json.dumps(message)
    res = mqttClient.publish(topic, message, mqtt_qos, mqtt_retain)

    while True:
        time.sleep(sleep)
        z = s.get_zones()
        for zone in z.root:
            if zone.status == ZoneStatusEnum.UNKNOWN or not zone.allocated:
                continue
            
            name    = clean_name(zone.description)
            topic   = "{}/{}/{}".format(mqtt_topic_base, mqtt_topic_zone, name)
            message = json.dumps(zone.__dict__)
            res = mqttClient.publish(topic, message, mqtt_qos, mqtt_retain)

        p = s.get_programs()
        for programstatus, programdata in zip(p.root, centrale.tp.status.programs):
            if len(programdata.zones) == 0:
                continue
            
            name    = clean_name(programdata.description)
            program = {}
            program['data']   = programdata.__dict__
            program['status'] = programstatus.__dict__
            topic   = "{}/{}/{}".format(mqtt_topic_base, mqtt_topic_program, name)
            message = json.dumps(program)
            res = mqttClient.publish(topic, message, mqtt_qos, mqtt_retain)

        print(dt.now())

    mqttClient.disconnect()
    mqttClient.loop_stop()
