# -*- coding: utf-8 -*-
__author__ = 'mshadish'
"""
Server tracker class definition

This is the class that we will use to keep track of the various servers
for which we want heartbeats (i.e., which servers to track,
which servers are offline, how frequently to ping each server, etc.)

Note that, when keeping track of the servers, we will use dictionaries
where the key is the server name and the value is a list of 2 elements
(first element being how many "seconds" has elapsed since the server was
last pinged, second element being the interval of time between pings).
So the structure of each dictionary element looks like:

    {server_name: [time elapsed since last ping, ping wait time interval]}


Methods:
--------
readInServers()
    - will attempt to read in our globally-defined heartbeat server dump file
    which will serve as a way of recovering known server information
    in the case that the heartbeat server goes down
    
writeOutServers()
    - this will be called any time there is a change in the servers being
    tracked
    - writes out the current list of servers tracked as well as their statuses
    
addServer(server name)
    - adds the given server name to our set of tracked servers,
    determining whether or not the server is currently online or offline
    - uses the default time interval between pings of that server
    - calls writeOutServers() if there were any changes
    
removeServer(server name)
    - removes the given server name from our set of tracked servers,
    unless it doesn't exist (in which case there is nothing to remove)
    - also calls writeOutServers() if there were any changes
    
updatePingInterval(server name, ping time interval)
    - updates the time interval between pings for a given server
    - if the server isn't already tracked, we will track it
    - will call writeOutServers(), since the ping time interval has presumably
    been changed (or a new server may have been added to tracking)
    
incrementTimers()
    - increments the first element in the list associated with each server
    - the idea is to show that, relative to each server's specified wait
    time interval, some amount of time has passed
    
pingAllDueServers()
    - for each server, we'll send a ping (in our case, an HTTP GET request)
    to check the status of any server for which the time that has elapsed
    since the last ping to that server is equal to or greater than
    that server's specified time interval between pings
    - once the pings have been sent out, we'll update the status (online vs.
    offline) of any servers that changed
    
printStatus()
    - prints the status of all servers
    - returned for GET requests and used for writing out to the dump file
"""
# imports
import StringIO
import requests
import csv
import os

# global for default length of time between pings, in seconds
default_ping_interval = 30
# global for tracker file
server_tracker_file = 'heartbeat_server_dump.csv'


def sendPing(server):
    """
    Pings a given server (using HTTP), returns the status of the server
    
    Returns either 'Online' or 'Offline'
    """
    server_status = None
    
    # build the url
    url = 'http://{0}'.format(server)
    # send the ping via HTTP
    try:
        health = requests.get(url)
    except requests.ConnectionError:
        return 'Offline'
    # depending on the health of the system, respond accordingly
    if health.ok:
        server_status = 'Online'
    else:
        server_status = 'Offline'
    
    return server_status


class ServerTracker:

    def __init__(self):
        """
        Initialization function
        """
        # we'll use a dictionary to keep track of the servers to track,
        # where the value represents how long to wait between pings
        # note that these will be considered 'online' servers
        # i.e., we will keep track of servers that have disconnected separately
        self.online_servers = {}
        # we'll also keep track of the servers that have disconnected
        # this too will be a dictionary -- in this way, we can keep track
        # of any servers that have gone offline but come back online
        self.offline_servers = {}
        
    def readInServers(self):
        """
        Will look for the global "tracker" file in the current working dir
        and read in its contents, presumed to be of the format:
            Server,Ping Interval,Status
            machine1,10,Offline
            google.com,15,Online
            
        If the header is any different, we won't read the file in
            
        This is a way of remembering previously-known servers in the event
        that our heartbeat server goes down and we have to restart it
        (i.e., this can serve as a pseudo memory dump file)
        """
        # we'll be using the global server tracker file
        global server_tracker_file
        # first, grab a list of all files in the current working directory
        current_dir = os.listdir('.')
        # verify that our server tracker file exists here
        if server_tracker_file not in current_dir:
            # if there's nothing to read in, simply return
            return
            
        # read in the csv
        with open(server_tracker_file, 'rb') as infile:
            # initialize the reader
            reader = csv.reader(infile)
            # verify that the header looks exactly as we expect
            header = reader.next()
            if header != ['Server','Ping Interval','Status']:
                # if this isn't the case, we won't try to read the file
                return
            else:
                # update our servers with the records we know about
                # while we update, we'll keep a count of how many
                # we can successfully read in
                server_count = 0
                for record in reader:
                    # pull out the server name and ping interval
                    server = record[0]
                    try:
                        interval = int(record[1])
                    except ValueError:
                        continue
                    # ping the server to determine whether it is online
                    # or offline
                    status = sendPing(server)
                    if status == 'Online':
                        # allocate to online
                        self.online_servers[server] = [0, interval]
                    else:
                        # allocate to offline
                        self.offline_servers[server] = [0, interval]
                    # udpate our count
                    server_count += 1
                # repeat for every record from our pseudo memory dump file
                # report and return
                print 'Read in {0} known servers'.format(server_count)
                
        # file read complete
        return
        
        
    def writeOutServers(self):
        """
        Writes out our pseudo memory dump file such that, in case the
        heartbeat server ever goes down, we can remember all of the servers
        we are tracking
        
        Overwrites any existing copy of that file
        """
        # we'll be writing out to the server tracker file, overwriting
        # anything that may exist in it
        global server_tracker_file
        
        with open(server_tracker_file, 'wb') as outfile:
            # let's leverage the printStatus method we have
            outfile.write(self.printStatus())
            
        return
        
        
    def addServer(self, server_name):
        """
        This function adds a server to our dictionary of online servers
        and initializes the ping wait time to the default time
        
        :param server_name = name of the server to be tracked
        
        Returns nothing
        """
        # initialize a return body on requests
        return_body = None
        # make sure we're not already tracking the server
        if server_name in self.online_servers or server_name in self.offline_servers:
            # if so, print a message to the console and return
            return_body = '{0} already being tracked'.format(server_name)
        else:
            # otherwise, send a ping to the server to determine status
            server_status = sendPing(server_name)
            # and classify accordingly
            if server_status == 'Online':
                self.online_servers[server_name] = [0, default_ping_interval]
            else:
                self.offline_servers[server_name] = [0, default_ping_interval]

            return_body = '{0} added with interval {1}'.format(server_name,
                                                               default_ping_interval)
                                                               
        # write out our pseudo dump file
        self.writeOutServers()
        print 'New server written to dump file'
        
        return return_body
        
        
    def removeServer(self, server_name):
        """
        This function will remove a server from our set of tracked servers
        
        :param server_name = name of the server we wish to stop tracking
        
        Returns a message to send to the requestor
        """
        # check the online servers
        if server_name in self.online_servers:
            self.online_servers.pop(server_name)
        # check the offline servers
        elif server_name in self.offline_servers:
            self.offline_servers.pop(server_name)
        else:
            return 'Server already not currently tracked'
            
        # report, write out, and return
        self.writeOutServers()
        return 'Server {0} removed from tracking'.format(server_name)
        
        
    def updatePingInterval(self, server_name, ping_interval):
        """
        Updates the ping wait time interval for a particular server
        If that server is not currently being tracked, we will add it to our
        dictionary of tracked servers.
        Also writes out our server tracker file.
        
        :param server_name = name of the server to add/update
        :param ping_interval = time interval to wait between pings to this
        server
        
        Returns a message for the requestor
        """
        # initialize the return body we will send on requests
        return_body = '{0} updated with interval {1}'.format(server_name,
                                                             ping_interval)
        # find out whether it is in the online or offline dictionary
        if server_name in self.online_servers:
            # update the online dictionary
            self.online_servers[server_name] = [self.online_servers[server_name][0], ping_interval]
        elif server_name in self.offline_servers:
            # update the offline dictionary
            self.offline_servers[server_name] = [self.offline_servers[server_name][0], ping_interval]
        else:
            # if it does not exist, we'll add it instead
            return_body = '{0} added with interval {1}'.format(server_name,
                                                               ping_interval)
            # check the status
            server_status = sendPing(server_name)
            # classify accordingly
            if server_status == 'Online':
                self.online_servers[server_name] = [0, ping_interval]
            else:
                self.offline_servers[server_name] = [0, ping_interval]
                
        # write to the pseudo dump file
        self.writeOutServers()
        print 'New/updated server written to dump file'
            
        return return_body
        
        
    def incrementTimers(self):
        """
        Simply updates the counter by +1 for each server
        
        We will subsequently ping all servers for which the counter is at
        or exceeds the ping interval specified for the given server
        """
        # online servers
        for server in self.online_servers:
            self.online_servers[server][0] += 1
        # offline servers
        for server in self.offline_servers:
            self.offline_servers[server][0] += 1
            
        return
        
        
    def pingAllDueServers(self):
        """
        This function will increment the timing counter
        associated with each server.  If the amount of time elapsed
        since the last ping equals or exceeds the ping time interval,
        then ping that server and reset our timing counter
        
        For all servers that are no longer online, we will move them to offline
        and vice versa
        """
        # initialize lists to keep track of newly online and offline servers
        newly_online = []
        newly_offline = []
        
        # step through the online servers
        for server in self.online_servers:
            # if this counter equals or exceeds the ping time interval,
            # then we must ping the server and update the status
            if self.online_servers[server][0] >= self.online_servers[server][1]:
                status = sendPing(server)
                # reset the counter
                self.online_servers[server][0] = 0
                
                # update the status accordingly
                if status == 'Offline':
                    # remove from the online servers
                    # and add to the offline servers simultaneously
                    newly_offline.append({server: self.online_servers[server]})
        # repeat for every online server
        # remove the newly offline servers from the online tracker
        for offline in newly_offline:
            self.online_servers.pop(offline.keys()[0])
                
        # step through the offline servers
        for server in self.offline_servers:
            # again, ping the server if the amount of time elapsed equals
            # or exceeds the ping time interval
            if self.offline_servers[server][0] >= self.offline_servers[server][1]:
                status = sendPing(server)
                # reset the counter
                self.offline_servers[server][0] = 0
                
                # update the status accordingly
                if status == 'Online':
                    # remove from the offline servers
                    # and add to the online servers
                    newly_online.append({server: self.offline_servers[server]})
        # repeat for every offline server
        # remove the newly online servers from the offline tracker
        for online in newly_online:
            self.offline_servers.pop(online.keys()[0])
                    
        # update the server tracking dictionaries accordingly
        for on_server in newly_online:
            self.online_servers.update(on_server)
        for off_server in newly_offline:
            self.offline_servers.update(off_server)
            
        return
        
        
    def printStatus(self):
        """
        Prints out the status of all of the servers
        as well as the specified wait time intervals
        """
        output = StringIO.StringIO()
        # use a csv writer to write out each row
        writer = csv.writer(output, lineterminator = '\n')
        
        # write the header
        writer.writerow(['Server','Ping Interval','Status'])
        
        # write out the online servers
        for server, interval in self.online_servers.iteritems():
            writer.writerow([server, interval[1], 'Online'])
            
        # write out the offline servers
        for server, interval in self.offline_servers.iteritems():
            writer.writerow([server, interval[1], 'Offline'])
            
        return output.getvalue()