#Python standard libraries
import json
import os
import sqlite3
import datetime
import calendar
import random

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
from access_secrets import access_secret_version, add_secret_version

#Configuration
STRAVA_CLIENT_ID = access_secret_version('everysingleroute', 'strava-client-id', 'latest')
STRAVA_CLIENT_SECRET = access_secret_version('everysingleroute', 'strava-client-secret', 'latest')
fake_hash=str(random.getrandbits(128))

#set environment variable DEBUG to enable testing on localhost
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#Flask app setup
app = Flask(__name__)

#Oauth2 client setup
client = WebApplicationClient(STRAVA_CLIENT_ID)

@app.route("/")
def index():
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
		#redirect_url=request.base_url,
		redirect_url=request.path,
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
	response = client.parse_request_body_response(json.dumps(token_response.json()))
		
	#Gather info on the athlete before loading hello.html
	athlete = response["athlete"]
	athlete_firstname = athlete["firstname"]
	athlete_lastname = athlete["lastname"]
	athlete_photo = athlete["profile"]

	#Load hello.html
	return render_template('hello.html', athlete_firstname=athlete_firstname, athlete_lastname=athlete_lastname, athlete_photo=athlete_photo)

@app.route("/routes", methods=['GET','POST'])
def select_routes():
	if request.method == 'POST':
		start_year = int(request.form['start_year'])
		start_month = int(request.form['start_month'])
		end_year = int(request.form['end_year'])
		end_month = int(request.form['end_month'])
		per_page = int(request.form['per_page'])
	#Convert to epoch timestamp
	end_day = calendar.monthrange(end_year, end_month)[1]
	start = int(datetime.datetime(start_year, start_month, 1, 0, 0).timestamp())
	end = int(datetime.datetime(end_year, end_month, end_day, 0, 0).timestamp())

	if end > start:
		#Hit /athlete/activities with newly acquired access token
		useractivities_endpoint = "https://www.strava.com/api/v3/athlete/activities"
		uri, headers, body = client.add_token(useractivities_endpoint)
		activity_ids = {}	
		params = {'per_page':per_page, 'after':start, 'before':end, 'page':1}
		user_activities_response = requests.get(uri, headers=headers, data=body, params=params)
	else:
		return render_template('hello.html')

	#Add the activities to a dict activity ids (id x name)
	user_activities = user_activities_response.json()
	for i in user_activities:
		activity_ids[str(i["id"])] = str(i["name"])
	
	return render_template('routes.html', activity_ids=activity_ids)

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
		for i in sorted(selected_ids):
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

		return render_template('displayroutes.html', selected_routes=selected_routes, names=selected_names, dist=selected_dist, vert=selected_vert, dates=selected_dates)

if __name__ == '__main__':
	app.run()
