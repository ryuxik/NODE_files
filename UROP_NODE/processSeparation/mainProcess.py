"""
This is the main NODE control process.
"""
import errorDetect
import mmap
import busComm
import ConfigParser
import optimizer
import configControl
import logging
from usbSwitch import switch

def interrupt(config, connection, commands):
	"""
	Reads data incoming through PL Bus and updates necessary values according to data.
	
	Args:
		config(dict): dict with necessary configuration arguments
		connection(Connection): Connection object to represent link to PL Bus
		commands(dict): dict with mode to valid command map from commandChecker.ini
	"""
	data_from_bus = connection.updateReceived() #reads incoming info, stores it in the connection object, and returns the info
	valid = False #boolean value to check if the command received from PL is valid in the current mode of operation
	#iterates through configuration dictionary to find the current operating mode
	for option in config['ModeSettings']:
		b = config['ModeSettings'][option]
		if b:
			mode = b
			break
	
	##implement something here to pull command from data_from_bus
	#command = process(data_from_bus)
	command = 'foo'

	#checks if the command is valid in the current mode
	if command in commands[mode]:
		valid = True
	
	#executes valid commands in this section
	if valid:
		##implement switch here
		#if command is switch
			#switch()
			#masterOperationMode()
		#else:
			#figure out what to do with the valid command received
			#setValues(data_from_bus) #Set values according to data received

def prepDict(file):
	"""
	Create dictionary of dicts, each dict represents a section of whatever .ini file is given.
	
	Args:
		file(string): name of .ini file to read

	Returns:
		master(dict): dictionary representation of the .ini file
	"""

	#read file
	c = ConfigParser.RawConfigParser()
	c.read(file)

	#creates master dict representation of .ini file
	master = {}
	for section in c.sections():
		temp = {}
		for option in c.options(section):
			temp[option] = c.get(section, option)
		master[section] = temp

	return master
	# #updates master dict representation of args.ini file
	# for key in data_from_bus:
	# 	for tup in data_from_bus[key]:
	# 		master[key][tup[0]] = tup[1]

	# return master

# def setValues(data_from_bus):
# 	"""
# 	Update Values on args.ini file with data received from PL

# 	Args:
# 		data_from_bus(): data received from PL, 
# 			assuming data is in the form of a dict 
# 			with key being a section and list of (option, value) being write values to that key in the args.ini file
# 	"""
	
# 	prep = prepDict(data_from_bus) #parses existing data in args.ini and uses it to make updated dictionary repr
# 	c = ConfigParser.RawConfigParser()

# 	for section in prep: #writes the new args.ini file
# 		c.add_section(section)
# 		for option in prep[section]:
# 			c.set(section, option, prep[section][option])

# 	with open('args.ini', 'wb') as configfile: #writes out
# 		c.write(configfile)  

def alarms(data, config, old_counter):
	"""
	Checks data read for possible errors and returns report

	Args:
		old_counter(int): clock cycle count read last loop
		data(dict): memmory map location name to data read
		config(dict): dictionary representation of args.ini file
	Returns: 
		diagnostics(list): report of various possble error sources. 
					[currents_result is 0 if no errors else list of tuples with failues,
                    clock_cycles_since_reset is 0 if no error, int with other number if else,
                    oStatus is tbd]
	"""
	#initially the clock count should be 0
	if old_counter == None:
		old_counter = 0
	diagnostics = errorDetect.AlarmRaiser(data, old_counter, config, m) #Creates AlarmRaiser object which returns diagnostics report
	return diagnostics

def readTelemetry(m):
	"""
	Reads all addresses from memory map and stores data in dictionary
	
	Args:
		m(Tester): memmory map object used to read from locations

	Returns:
		data(dict): memory map location name to data read
	"""

    data = m.readAll() #the memmory map object reads all locations and returns the data
    return data

def updateTelemetry(data, diagnostics):
	"""
	Writes out telemetry to file so that PL can read it since we are configured as a slave
	"""

	f = open('telemetry','w')
	
	f.write('Data Read')
	for key in data: #mem_map loc to data read report
		new_line = key + ': ' + new_line[key] + '\n'
		f.write(new_line)
	
	f.write('Diagnostics')
	for tup in diagnostics[0]: #current draw error reports
		new_line = 'Current draw error at: ' + tup[0] + ' with value: ' + tup[1] + '\n'
		f.write(new_line)

	f.close()
		
def errorHandle(diagnostics, handle, opt):
	"""
	Corrects errors detected by diagnostics report from alarms(). Includes call to optimization if necessary.

	Args:
		diagnostics(list): list containing error reports
		handle(): An opaque reference to an internal structure representing the connection to the FPGA
		opt(Optimizer): Object that handles optimization algorithm controls
	"""
	
	if diagnostics[0] != 0: #a device is taking too much current #list should be locations, PO1 PO2 PO3 PO4
		#switch off any device drawing too much power
		logging.info('Device(s) is(are) drawing too much power.')
		for loc in diagnostics[0]:
			configControl.powerOff(handle, loc)

	if diagnostics[1] != 0: #connection to the FPGA may have been lost
		logging.info('Connection to FPGA was lost, re-starting cotrol setup.')
		controlLoop() #start up the connection again and make the necesary objects

	if diagnostics[2][0]: #checks if optimization is needed, may need more conditions to actually run optimization.
		logging.info('Optimization of SER was needed.')
		obs_length = 1 #constant that will be decided in the future, 1 might work fine
		opt.scan_mode(obs_length) #may need to still add condition to this function
		
def slaveOperationMode(m, handle, opt, config, connection, commands):
	"""
	Loop for slave operation mode for NODE

	Args:
		m(Tester): memmory map object
		handle(): An opaque reference to an internal structure representing the connection to the FPGA
		opt(Optimizer): Object that handles optimization algorithm controls
	"""
	old_counter = None
	while True:
		try:
			data = readTelemetry(m) #Read relevant data from FPGA
			logging.info('Data from FPGA was read and stored.')
		except:
			logging.info('Failed to read telemetry from FGPA.')
		try:
			diagnostics = alarms(data, old_counter, config, m) #Check if system is in working conditions according to reading status flags
			logging.info('Generated system diagnostics report from data read.')
		except:
			logging.info('Failed to produce diagnostics report.')
		old_counter = data['FRC'] #Set old counter to # clock cycles last read
		try:
			updateTelemetry(data, diagnostics) #Updates file holding all information which PL will be reading
			logging.info('Updated telemetry file.')
		except:
			logging.info('Failed to update telemetry.')
		try:
			errorHandle(diagnostics, handle, opt) #Handle errors
			logging.info('Errors were resolved.')
		except:
			logging.info('Failed to handle errors.')
		#if there is information incoming from PL
		try:
			interrupt(config, connection, commands) #Read incoming data from PL Bus
			logging.info('Incoming data was read and processed.')
		except:
			logging.info('Failed to read data from PL.')

def masterOperationMode():
	"""
	Loop for master opreation mode for NODE. This mode is for handling software updates.
	"""
	pass
		
#This main loop may be modified depending on the satellite mode
def controlLoop():
	"""
	Main control loop for NODE, this may be modified depending on the satellite's mode in the future.
	"""
	try:
		logging.basicConfig(format='%(asctime)s:%(message)s:', filename='mainProcess.log', level=logging.INFO) #sets up logger
		config = prepDict('args.ini') #creates the config dictionary
		logging.info('Created the configuration dictionary.')
		fpga, handle, opt = configControl.openComm(config) #opens connection to FPGA and returns NODEFPGA, handle, and Optimizer objects
		logging.info('Opened the connection to the FPGA and created NODEFPGA, handle, and Optimizer objects.')
		m = opt.getMemMap() #Returns the Tester object created by Optimizer object
		logging.info('Created the Tester object using the Optimizer object.')
		commands = prepDict('commandChecker.ini') #creates the commands dictionary
		logging.info('Created the command checker dictionary.')
		#opens connection to PL Bus and returns onject to handle it
		connection = busComm.Connection(
										config['ConnectionInfo']['plBus_vid'], config['ConnectionInfo']['plBus_pid'],
										config['ConnectionInfo']['plBus_packet_size'], config['ConnectionInfo']['plBus_timeout'],
										config['ConnectionInfo']['plBus_wendpoint'], config['ConnectionInfo']['plBus_rendpoint'])
		logging.info('Opened the connection to the PL Bus.')

	except:
		logging.info('Failed to create all objects needed for NODE operation.')
	#implement check for slave or master operation mode here

	#slave operation mode
	#if slave:
	try:
		logging.info('Entering slave operation mode.')
		slaveOperationMode(m, handle, opt, config, connection, commands)
	except:
		logging.info('Something failed, restarting setup for control.')
		controlLoop()

	