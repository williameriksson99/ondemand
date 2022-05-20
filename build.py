from os import fdopen
from cmath import pi
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask.json import jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask.globals import current_app 
from geopy.geocoders import Nominatim
import time
import redis
import pickle
import json
import requests

app = Flask(__name__)
CORS(app)
app.secret_key = 'dljsaklqk24e21cjn!Ew@@dsa5'

# change this so that you can connect to your redis server
# ===============================================
redis_server = redis.Redis(host="localhost", port="6379", decode_responses=True, charset="unicode_escape")
# ===============================================

geolocator = Nominatim(user_agent="my_request")
region = ", Lund, Skåne, Sweden"


# Translate OSM coordinate (longitude, latitude) to SVG coordinates (x,y).
# Input coords_osm is a tuple (longitude, latitude).
def translate(coords_osm):
    x_osm_lim = (13.143390664, 13.257501336)
    y_osm_lim = (55.678138854000004, 55.734680845999996)

    x_svg_lim = (212.155699, 968.644301)
    y_svg_lim = (103.68, 768.96)

    x_osm = coords_osm[0]
    y_osm = coords_osm[1]

    x_ratio = (x_svg_lim[1] - x_svg_lim[0]) / (x_osm_lim[1] - x_osm_lim[0])
    y_ratio = (y_svg_lim[1] - y_svg_lim[0]) / (y_osm_lim[1] - y_osm_lim[0])
    x_svg = x_ratio * (x_osm - x_osm_lim[0]) + x_svg_lim[0]
    y_svg = y_ratio * (y_osm_lim[1] - y_osm) + y_svg_lim[0]

    return x_svg, y_svg

@app.route('/', methods=['GET'])
def map():
    return render_template('index.html')


@app.route('/drone13')
def drone13():
    return render_template('drone13.html')

@app.route('/get_drones', methods=['GET'])
def get_drones():
    #=============================================================================================================================================
    # Get the information of all the drones from redis server and update the dictionary `drone_dict' to create the response 
    # drone_dict should have the following format:
    # e.g if there are two drones in the system with IDs: DRONE1 and DRONE2
    # drone_dict = {'DRONE_1':{'longitude': drone1_logitude_svg, 'latitude': drone1_logitude_svg, 'status': drone1_status},
    #               'DRONE_2': {'longitude': drone2_logitude_svg, 'latitude': drone2_logitude_svg, 'status': drone2_status}
    #              }
    # use function translate() to covert the coodirnates to svg coordinates
    #=============================================================================================================================================
    drone1_logitude_svg, drone1_latitude_svg = translate((float(redis_server.get('Longitude12')),float(redis_server.get('Latitude12'))))
    drone1_status = redis_server.get('Status12')
    drone1_time = redis_server.get('Time12')
    drone2_logitude_svg, drone2_latitude_svg = translate((float(redis_server.get('Longitude13')),float(redis_server.get('Latitude13'))))
    drone2_status = redis_server.get('Status13')
    drone2_time = redis_server.get('Time13')
    drone_dict = {
        '12':{'longitude': drone1_logitude_svg, 'latitude': drone1_latitude_svg, 'status': drone1_status, 'time': drone1_time},
        '13': {'longitude': drone2_logitude_svg, 'latitude': drone2_latitude_svg, 'status': drone2_status, 'time': drone2_time}
        }
    print(drone_dict.get('12').get('time'))
    return jsonify(drone_dict)


# Example to send coords as request to the drone
def send_request(drone_url, coords):
    with requests.Session() as session:
        resp = session.post(drone_url, json=coords)
        
def time_left(dist):
    sec = dist/14
    minutes = int(sec/60)
    rest_sec = int(sec % 60)
    message = (str(minutes) + ' Minutes, ' + str(rest_sec) + ' Seconds')
    return message
        
def findDrone():
    if redis_server.get('Status12') == 'idle':
        return 12
    elif redis_server.get('Status13') == 'idle':
        return 13
    else:
        return -1
    
def dist_min():
    dist12 = float(redis_server.get('Dist12'))
    dist13 = 100000#float(redis_server.get('Dist13'))
    if (dist12 > dist13):
        return dist13
    else:
        return dist12
    
@app.route('/drone12')
def drone12():
    return render_template('drone12.html')

@app.route('/planner', methods=['POST', 'GET'])
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
                return "drone12"
            except Exception as e:
                print(e)
                return "Could not connect to the drone, please try again"
        
        
       
        else:
            message = 'No available drone right now, Next available drone: ' + str(time_left(dist_min())) 
        
       
        # else:
            # 2. Get the IP of available drone, 
        #DRONE_URL = 'http://' + DRONE_IP+':5000'
            # 3. Send coords to the URL of available drone
        #message = 'Got address and sent request to the drone'
    return message
        # ======================================================================

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port='5000')
