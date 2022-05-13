from cmath import pi
from flask import Flask, request, render_template, jsonify
from flask.globals import current_app 
from geopy.geocoders import Nominatim
from flask_cors import CORS
import redis
import json
import requests

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'dljsaklqk24e21cjn!Ew@@dsa5'

# change this to connect to your redis server
# ===============================================
redis_server = redis.Redis(host="localhost", port="6379", decode_responses=True, charset="unicode_escape")
# ===============================================

geolocator = Nominatim(user_agent="my_request")
region = ", Lund, Skåne, Sweden"

# Example to send coords as request to the drone
def send_request(drone_url, coords):
    with requests.Session() as session:
        resp = session.post(drone_url, json=coords)
        
def findDrone():
    if redis_server.get('Status12') == 'idle':
        return 12
    elif redis_server.get('Status13') == 'idle':
        return 13
    else:
        return -1

@app.route('/planner', methods=['POST'])
def route_planner():
    Addresses =  json.loads(request.data.decode())
    FromAddress = Addresses['faddr']
    ToAddress = Addresses['taddr']
    from_location = geolocator.geocode(FromAddress + region, timeout=None)
    to_location = geolocator.geocode(ToAddress + region, timeout=None)
    if from_location is None:
        message = 'Departure address not found, please input a correct address'
        return message
    elif to_location is None:
        message = 'Destination address not found, please input a correct address'
        return message
    else:
        # If the coodinates are found by Nominatim, the coords will need to be sent the a drone that is available
        coords = {'from': (from_location.longitude, from_location.latitude),
                  'to': (to_location.longitude, to_location.latitude),
                  }
        # ======================================================================
        # Here you need to find a drone that is availale from the database. You need to check the status of the drone, there are two status, 'busy' or 'idle', only 'idle' drone is available and can be sent the coords to run delivery
        # 1. Find avialable drone in the database
        # if no drone is availble:
        
        if findDrone() == 12:
            DRONE_URL = 'http://' + redis_server.get('DroneIP12') + ':5000'
            message = 'Got address and sent request to the drone'
            
            try:
                with requests.session() as session:
                    resp = session.post(DRONE_URL, json=coords)
                    print(resp.text)
                return message
            except Exception as e:
                print(e)
                return "Could not connect to the drone, please try again"
        
        elif findDrone() == 13:
            DRONE_URL = 'http://' + redis_server.get('DroneIP13') + ':5000'
            message = 'Got address and sent request to the drone'
            
            try:
                with requests.session() as session:
                    resp = session.post(DRONE_URL, json=coords)
                    print(resp.text)
                return message
            except Exception as e:
                print(e)
                return "Could not connect to the drone, please try again"
       
        else:
            message = 'No available drone, try later'
        
       
        # else:
            # 2. Get the IP of available drone, 
        #DRONE_URL = 'http://' + DRONE_IP+':5000'
            # 3. Send coords to the URL of available drone
        #message = 'Got address and sent request to the drone'
    return message
        # ======================================================================


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port='5002')
