#!/usr/bin/env python3
#
# get_state.py: retrieve and save the master state from a DC/OS cluster
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]
#
# Get the masters state from a DC/OS cluster. Provide a list of
# the Total, Active and Inactive agents.

# This uses three arguments passed as environment variables :
# TEST_IP: server to check -one of the DC/OS masters in a cluster-
# TOKEN: authentication token to be used against the cluster
# EXPECTED_NUMBER_OF_NUM_MASTERS: expected number of masters

#reference:
#http://mesos.apache.org/documentation/latest/endpoints/master/slaves/

#prereqs on redhat7
# rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
# yum install -y epel-release
# yum install -y git python-pip python34 jq nginx
# curl https://bootstrap.pypa.io/get-pip.py | python3.4
# pip3 install --upgrade pip jsonschema requests

import sys
import os
import requests
import json

#Load configuration from environment variables
if ('DCOS_IP' in os.environ) and ('NUM_MASTERS' in os.environ) and ('DCOS_TOKEN' in os.environ):
	DCOS_IP=os.environ['DCOS_IP']
	NUM_MASTERS=os.environ['NUM_MASTERS']
	DCOS_TOKEN=os.environ['DCOS_TOKEN']
else:
	print('**ERROR: required variables DCOS_IP, NUM_MASTERS, \
	DCOS_TOKEN not set appropriately. Please set and re-run')
	sys.exit(1)
NUM_MASTERS=int(NUM_MASTERS)

#CHECK #1
#check from zookeeper the number of servers and leaders matches what is expected.
EXHIBITOR_STATUS_URL = 'http://'+DCOS_IP+':8181/exhibitor/v1/cluster/status'
#get the actual cluster size from zookeeper
try:
	response = requests.get(EXHIBITOR_STATUS_URL)
except (
	requests.exceptions.ConnectionError ,\
	requests.exceptions.Timeout ,\
	requests.exceptions.TooManyRedirects ,\
	requests.exceptions.RequestException ,\
	ConnectionRefusedError
	) as error:
	print('**ERROR: Could not connect to exhibitor: {}'.format(error))
	sys.exit(1)
if str(response.status_code)[0] != '2':
	print('**ERROR: Could not get exhibitor status: {}, Status code: {}'.format( EXHIBITOR_STATUS_URL, response.status_code ) )
	sys.exit(1)
data = response.json()
# #1 - parseable output
exhibitor_status={'exhibitor_status': data }
# #1 - EXAMPLE PARSING
print("\n\n**OUTPUT:\n{0}".format( json.dumps(exhibitor_status) ))
#count the number of serving nodes and leaders
serving = 0
leaders = 0
for node in data:
	if node['isLeader']:
		leaders += 1
	if node['description'] == 'serving':
		serving += 1

if serving != NUM_MASTERS or leaders != 1:
		print('**ERROR: Expected {0} servers and 1 leader, got {1} servers and {2} leaders. Exiting.'.format( NUM_MASTERS, serving, leaders ) )
		sys.exit(1)
else:
		print('**INFO: server/leader check OK: {0} servers and {1} leader.'.format( serving, leaders ) )

#CHECK #2
#https://docs.mesosphere.com/1.8/administration/installing/cloud/aws/upgrading/
#METRICS: "registrar" has the metric/registrar/log recovered with a value of 1.0
#http://<dcos_master_private_ip>:5050/metrics/snapshot
#api_endpoint=':5050/metrics/snapshot'
api_endpoint='/mesos/metrics/snapshot'
url = 'http://'+DCOS_IP+api_endpoint
headers = {
	'Content-type': 'application/json',
	'Authorization': 'token='+DCOS_TOKEN,
}
try:
	response = requests.get(
		url,
		headers=headers,
		)
	#show progress after request
	print( '**INFO: GET Metrics: {0} \n'.format( response.status_code ) )
except requests.exceptions.HTTPError as error:
	print ('**ERROR: GET Metrics: {} \n'.format( response.text ) )

if str(response.status_code)[0] == '2':	#2xx HTTP status code is success
	# #2 - parseable output
	data=response.json()
	metrics={'metrics': data }
	print("\n\n**OUTPUT:\n{0}".format(json.dumps(metrics)))
	# #2 - EXAMPLE PARSING
	if 'registrar/log/recovered' in data:
		if data['registrar/log/recovered'] == int(1.0):
			print('**INFO: Log Recovered check OK')
		else:
			print('**ERROR: Log NOT recovered. Value is {0}'.format( data['registrar/log/recovered'] ) )
	else:
		print('**ERROR: Registrar Log not found in response' )
else:
	print ('**ERROR: GET Health: {} \n'.format( response.text ) ) 	

#CHECK #3
#Get health report of the system and make sure EVERYTHING is Healthy. 
#Display where it's Unhealthy otherwise.
api_endpoint = '/system/health/v1/report'
url = 'http://'+DCOS_IP+api_endpoint
headers = {
	'Content-type': 'application/json',
	'Authorization': 'token='+DCOS_TOKEN,
}
try:
	response = requests.get(
		url,
		headers=headers,
		)
	#show progress after request
	print( '**INFO: GET Health Report: {0} \n'.format( response.status_code ) )
except requests.exceptions.HTTPError as error:
	print ('**ERROR: GET Health Report: {} \n'.format( response.text ) ) 

if str(response.status_code)[0] == '2':	#2xx HTTP status code is success
	# #3 - parseable output
	data=response.json()
	health_report={'health_report': data}
	print("\n\n**OUTPUT:\n{0}".format( json.dumps( health_report ) ) )	
	# #3 - EXAMPLE PARSING
	for unit in data['Units']:
		print('Name: {0:48}			State: {1}'.format( \
			data['Units'][unit]['UnitName'], data['Units'][unit]['Health'] ) )
		if data['Units'][unit]['Health']: #not 0 means unhealthy, print all children
#D			for node in unit['Nodes']:
#D				print('Name: {0:48}			IP: {1}		State: {2}'.format( \
#D					data['Units:'][unit]['UnitName'], response_dict['Units'][unit][node]['IP'], \
#D					data['Units'][unit][node]['Health'] ) )
			for node in data['Units'][unit]['Nodes']:
				print( ' Name: {0:48}		IP: {1}		State: {2}'.format( \
					data['Units'][unit]['UnitName'], node['IP'], node['Health'] ) )
else:
	print ('**ERROR: GET Health: {} \n'.format( response.text ) ) 	

print( '\n** INFO: GET System Health: 							Done. \n' )





