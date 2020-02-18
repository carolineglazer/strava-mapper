#Python standard libraries
import json
import os
import sqlite3

#Third-party libraries
from flask import Flask, redirect, request, url_for, render_template
from flask_login import (
	LoginManager,
	current_user,
	login_required,
	login_user,
	logout_user,
)

from oauthlib.oauth2 import WebApplicationClient
import requests

#Import secrets.py function to access secrets API
from access_secrets import access_secret_version

#No DB or SQL for now
#Internal imports
#from db import init_db_command
#from user import User

#Configuration
STRAVA_CLIENT_ID = access_secret_version('strava-mapper', 'strava-client-id', 'latest')
STRAVA_CLIENT_SECRET = access_secret_version('strava-mapper', 'strava-client-secret', 'latest')

#set environment variable DEBUG to enable testing on localhost
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#Flask app setup
app = Flask(__name__)
#(not including this for now...) - 11/12/19
#app.secret_key = os.urandom(24)

#User session management setup
login_manager = LoginManager()
login_manager.init_app(app)

#No db or SQL for now
'''
#Naive database setup
try:
	init_db_command()
except sqlite3.OperationalError:
	#Assume it's already been created
	pass
'''

#Oauth2 client setup
client = WebApplicationClient(STRAVA_CLIENT_ID)

#Flask-Login helper to retrieve a user from our db
#@login_manager.user_loader
#def load_user(user_id):
#	return User.get(user_id)

@app.route("/")
def index():
	'''
	if current_user.is_authenticated:
		return (
			#omit variable HTML for now
			"Hello user!"
		)
	else:
		return '<a class="button" href="/login">Login to Strava</a>'
	'''
	return render_template('index.html')

@app.route("/login")
def login():
	#Use library to construct the request for Strava login and provide scopes
	request_uri = client.prepare_request_uri(
		"https://www.strava.com/oauth/authorize",
		redirect_uri=request.base_url + "/callback",
		scope=["activity:read"])
	return redirect(request_uri)

@app.route("/login/callback")
def callback():
	#Get authorization code Strava sends back with redirect uri
	code = request.args.get("code") 

	#Exchange authorization code for a refresh token and short-lived access token
	token_url, headers, body = client.prepare_token_request(
		"https://www.strava.com/oauth/token",
		#force HTTPS when creating callback URL (https://stackoverflow.com/questions/49071504/google-app-engine-flask-ssl-and-oauth2-problems)
		#authorization_response=request.url.replace('http','https'),
		redirect_url=request.base_url,
		code=code,
		#Note: this is where Strava token request differs from Google token request -
		#Strava requires that the client_secret be included in the body of the POST,
		#not just in the auth, presumably - 11/12/19
		client_secret=STRAVA_CLIENT_SECRET
	)
	
	token_response = requests.post(
		token_url,
		headers=headers,
		data=body,
		auth=(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET)
	)

	#Parse the tokens!
	client.parse_request_body_response(json.dumps(token_response.json()))

	#Hit /athlete/activities with newly acquired access token
	useractivities_endpoint = "https://www.strava.com/api/v3/athlete/activities"
	uri, headers, body = client.add_token(useractivities_endpoint)
	user_activities_response = requests.get(uri, headers=headers, data=body)

	#CAROLINE I THINK YOU CAN DELETE THIS BLOCK DECIDE LATER
	#json.dumps the activities response, and create a new List object with activity names
	user_activities = user_activities_response.json()
	activity_names = {}
	for i in user_activities:
		activity_names[str(i["name"])] = str(i["map"]["summary_polyline"])
	
	#also create a list of activity ids
	activity_ids = {}
	for i in user_activities:
		activity_ids[str(i["id"])] = str(i["name"])
		
	#Hit /athlete to get the athlete's info
	athlete_endpoint = ("https://www.strava.com/api/v3/athlete")
	uri, headers, body = client.add_token(athlete_endpoint)
	athlete_response = requests.get(uri, headers=headers, data=body)

	#Parse athlete response for first and last name and photo
	athlete = athlete_response.json()
	athlete_firstname = athlete["firstname"]
	athlete_lastname = athlete["lastname"]
	athlete_photo = athlete["profile"]

	return render_template('routes.html', athlete_firstname=athlete_firstname, athlete_lastname=athlete_lastname, athlete_photo=athlete_photo, activity_names=activity_names, activity_ids=activity_ids)

@app.route("/displayroutes", methods=['GET','POST'])
def displayroutes():
	if request.method == 'POST':
		selected_ids = list(request.form.items())

		#Hit /activites/[id] with every activity id checked in /routes
		#Produce selected_routes: id x polyline, selected_names: id x name, 
		#selected_dist: id x distance, selected_vert: id x elevation,
		#selected_dates: id x date
		selected_routes = {}
		selected_names = {}
		selected_dist = {}
		selected_vert = {}
		selected_dates = {}
		for i in selected_ids:
			try:
				activityids_endpoint = "https://www.strava.com/api/v3/activities/" + i[0]
				uri, headers, body = client.add_token(activityids_endpoint)
				activity_response = requests.get(uri, headers=headers, data=body)
				activity = activity_response.json()
				selected_routes[str(activity["id"])] = str(activity["map"]["summary_polyline"])
				selected_names[str(activity["id"])] = str(activity["name"])
				selected_dist[str(activity["id"])] = float(str(round((activity["distance"]/1609.34),2)))
				selected_vert[str(activity["id"])] = int(str(round((activity["total_elevation_gain"]*3.28))))
				selected_dates[str(activity["id"])] = activity["start_date"][5:7]+"/"+activity["start_date"][8:10]+"/"+activity["start_date"][:4]
			except:
				pass

		#Make a list of just the summary polylines
		encoded_routes = []
		for i in selected_routes:
			#reformatted = selected_routes[i].replace("\\","\\\\")
			encoded_routes.append(selected_routes[i])
			#encoded_routes.append(reformatted)

		return render_template('displayroutes.html', selected_routes=selected_routes, encoded_routes=encoded_routes, names=selected_names, dist=selected_dist, vert=selected_vert, dates=selected_dates)

if __name__ == '__main__':
	app.run()
