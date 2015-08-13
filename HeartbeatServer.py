#!/usr/bin/env python
__author__ = 'mshadish'
"""
Heartbeat Server
================
This is a prototype heartbeat server that will check the status of specified
servers using HTTP GET requests.  We will abstract the the concept of
a responsive server to be either "Online" (in our case, successfully handling
GET requests) or "Offline" (for some reason or another, unable to handle
our GET request pings).

This prototype uses Flask to run the web application and imports a class
that is defined in the script ServerTracker.py.  This separate class will
handle the maintenance of the different servers to track, pinging the servers,
and reading/writing to a dump file that will act as a pseudo memory file in
the case that the heartbeat server fails.

Notable features:
    - add servers to be tracked/'pinged' every x seconds (x can be defined)
    - remove servers to be tracked
    - pings (via HTTP GET requests) all servers currently being tracked
    (this is done passively using a background thread)
    - keeps track of all known servers using a file stored in the
    same directory as the ServerTracker.py file (the file name
    of this dump 'tracking' file is defined in ServerTracker.py file as well)
    
Note: the structure of the ServerTracker attributes have been defined
such that each server will have an associated list of two elements,
    [time that has elapsed since last ping, ping wait time interval]
This will allow us to ping different servers at different time intervals.

To interact with the application, the user can use HTTP GET, POST, and DELETE
requests.  Note that this heartbeat has been created with the intention
that there would be a single user who is interested in checking in on the
status of all other servers, and so he/she will interact with this
heartbeat server for periodic updates.  However, I have not implemented
any sort of security handshakes or anything of that nature, and so
a server that is being tracked could very well send a POST request to the
heartbeat server to 


------------
USAGE NOTES:
------------
GET requests to the server will tell the requestor the status
of the different servers
============
POST requests to the server will be used to either add a new server to be
tracked or update the wait time interval between pings for a given server.
Note that 'pings' are sent via HTTP requests, and we will automatically
prefix a server name with the http:// to specify protocol

Example POST request bodies:
    {"server":"google.com"}
    {"server":"python.org","interval":28}
    
If no wait time interval between pings is specified, we'll use a default
of 30 (which is specified in the ServerTracker class definition)
============
DELETE requests to the server will remove a specified server from tracking.
All we must be given is a server name

Example DELETE request body:
    {"server":"facebook.com"}
"""
# standard imports
from flask import Flask, request
# imports for threading (in order to run the heartbeat every second)
import threading
# import the server tracker class
from ServerTracker import ServerTracker

########################
# GLOBAL VARIABLES HERE
########################
# keep track of the servers
server_tracker = ServerTracker()
# and try to read in server tracker pseudo memory dump file
server_tracker.readInServers()

# background thread to support heartbeats every second
background_thread = threading.Thread()
# initialize a lock for dealing with the server tracker updates
lock = threading.Lock()


def heartbeatCheck():
    """
    This function is to be called every second
    and will ping all of the servers being tracked for which the 
    specified ping interval time has elapsed
    
    Note that, in order to run the background, we'll use a background thread
    """
    # specify global server, thread, and lock
    global server_tracker
    global background_thread
    global lock
    
    # run the incrementTimers()
    # and pingAllDueServers() functions in this separate thread
    # to be run every second
    with lock:
        # increment our timing counters
        server_tracker.incrementTimers()
        server_tracker.pingAllDueServers()

    # start the next thread
    background_thread = threading.Timer(1, heartbeatCheck)
    background_thread.start()
    return


# initialize the Flask application
my_app = Flask(__name__)

# we will accept GET requests (return the status of all servers)
# POST requests (change the ping time interval of a server)
# and DELETE requests (remove servers from tracking)
@my_app.route('/', methods = ['GET', 'POST', 'DELETE'])
def handleRequest():
    # specify the global server and lock
    global server_tracker
    global lock
    
    # initialize the return body
    return_body = None
    
    # GET request
    if request.method == 'GET':
        # return the status of all servers
        return_body = server_tracker.printStatus()
        
    # POST request
    elif request.method == 'POST':
        # get the parameters as a dictionary
        params = request.get_json(force = True)
        
        # check the fields that were given
        if 'server' in params and 'interval' in params:
            # given the server name and ping interval, we can update
            # first, verify that the interval is indeed a number
            try:
                ping_int = int(float(params['interval']))
            except ValueError:
                return_body = 'Ping time interval invalid'
                return return_body
                
            # update our set of tracked servers
            with lock:
                return_body = server_tracker.updatePingInterval(params['server'],
                                                                ping_int)
            
        elif 'server' in params:
            # given only the server, we'll try and track the server
            with lock:
                return_body = server_tracker.addServer(params['server'])
            
        else:
            # otherwise, we can't do anything with the request
            return_body = 'Invalid request.  Must contain server and interval'
            
    # DELETE request
    elif request.method == 'DELETE':
        # get the parameters
        params = request.get_json(force = True)
        
        # make sure we were given a server
        if 'server' in params:
            # if so, remove the server
            return_body = server_tracker.removeServer(params['server'])
        
        
    # before returning, convert any newlines to HTML newlines
    return_body = return_body.replace('\n', '<br />')
    return return_body
    
    
    
if __name__ == '__main__':
    heartbeatCheck()
    my_app.run()