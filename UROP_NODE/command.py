"""
This is pseudocode trying to follow Rodrigo's sketch of how we will first approach the sat control
"""
import errorDetect
import mmap
import busComm
import ConfigParser
import optimizer
import configControl

def interrupt():
	"""
	Reads data incoming through PL Bus and updates necessary values according to data.

	"""

	config = ConfigParser.RawConfigParser()
	config.read('args.ini')
	connection = busComm.Connection(
									config.get('ConnectionInfo', 'plBus_vid'), config.get('ConnectionInfo', 'plBus_pid'),
									config.get('ConnectionInfo', 'plBus_packet_size'), config.get('ConnectionInfo', 'plBus_timeout'),
									config.get('ConnectionInfo', 'plBus_wendpoint'), config.get('ConnectionInfo', 'plBus_rendpoint'))

	data_from_bus = connection.updateReceived()
	valid = False
	for option in config.options('ModeSettings'):
		b = config.getboolean('ModeSettings',option)
		if b:
			mode = b
			break

	##need to check if data is valid command, then set valid to true
	c = ConfigParser.RawConfigParser()
	c.read('commandChecker.ini')
	##implement something here to pull command from data_from_bus
	#command = process(data_from_bus)
	if command in c.options(mode):
		valid = True
	#need to change the format of data_from_bus
	if valid:
		setValues(data_from_bus) #Set values according to data received

def prepDict(data_from_bus):
	"""
	Create dictionary of dicts, each dict represents a section of the args.ini file.

	Args:
		data_from_bus: data received from PL, 
			assuming data is in the form of a dict 
			with key being a section and list of (option, value) being write values to that key in the args.ini file
	"""

	#read file
	c = ConfigParser.RawConfigParser()
	c.read('args.ini')

	#creates master dict representation of args.ini file
	master = {}
	for section in c.sections():
		temp = {}
		for option in c.options(section):
			temp[option] = c.get(section, option)
		master[section] = temp

	#updates master dict representation of args.ini file
	for key in data_from_bus:
		for tup in data_from_bus[key]:
			master[key][tup[0]] = tup[1]

	return master

def setValues(data_from_bus):
	"""
	Update Values on args.ini file with data received from PL

	Args:
		data_from_bus(): data received from PL, 
			assuming data is in the form of a dict 
			with key being a section and list of (option, value) being write values to that key in the args.ini file
	"""
	
	prep = prepDict(data_from_bus) #parses existing data in args.ini and uses it to make updated dictionary repr
	c = ConfigParser.RawConfigParser()

	for section in prep: #writes the new args.ini file
		c.add_section(section)
		for option in prep[section]:
			c.set(section, option, prep[section][option])

	with open('args.ini', 'wb') as configfile: #writes out
		c.write(configfile)  

def alarms(old_counter, data):
	"""
	Checks data read for possible errors and returns report

	Args:
		old_counter(int): clock cycle count read last loop
		data(dict): memmory map location name to data read
	Returns: 
		diagnostics(list): report of various possble error sources. 
					[currents_result is 0 if no errors else list of tuples with failues,
                    clock_cycles_since_reset is 0 if no error, int with other number if else,
                    oStatus is tbd]
	"""

	diagnostics = errorDetect.AlarmRaiser(old_counter, data)
	return diagnostics

def readTelemetry():
	"""
	Reads all addresses from memory map and stores data in dictionary

	Returns:
		data(dict): memory map location name to data read
	"""

	t = mmap.Tester()
    data = t.readAll()
    t.end()
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

##the following two functions probably will be merged into 1, these will use Ondrej's code
def processCamData():
	pass

def updateFSM():
	pass

def updateOthers():
	pass

def sendData():
	"""
	Sends data to PL
	"""

	config = ConfigParser.RawConfigParser()
	config.read('args.ini')
	connection = busComm.Connection(
									config.get('ConnectionInfo', 'plBus_vid'), config.get('ConnectionInfo', 'plBus_pid'),
									config.get('ConnectionInfo', 'plBus_packet_size'), config.get('ConnectionInfo', 'plBus_timeout'),
									config.get('ConnectionInfo', 'plBus_wendpoint'), config.get('ConnectionInfo', 'plBus_rendpoint'))
	data = None ##figure out what data to send here!! will probably depend on what is sent by PL
	connection.updateData(data) #updates data held by object and sends it to PL Bus, might not actually need this!
	##figure out how to actually send data!! try using code from node or control

def optimize(ser):
	"""
	Optimizes current and temperature for power efficiency.

	Args:
		ser(float): slot error rate, needed for condition
	"""
	
	try: #need to open connection
		fpga, handle, opt = configControl.openComm() #opens connection and returns fpga, handle, and optimizer objects
		#make call to optimize here in whichever mode is most appropriate depending on efficiency
		condition = None ##implement condition for just scan or dither mode not sure which
		if condition:
			obs_length = None #Don't know what this is yet
			opt.dither_mode(obs_length)
		else:
			opt.scan_mode(obs_length)
		
		configControl.closeComm(handle) #closes communication to fpga
	except: #connection open failed :(
		raise ConnectionError('Connection to the fpga failed')
		
def errorHandle(diagnostics):
	"""
	Corrects errors detected by diagnostics report from alarms(). Includes call to optimization if necessary.

	Args:
		diagnostics(list): list containing error reports
	"""
	
	if diagnostics[0] != 0: #a device is taking too much current #list should be locations, PO1 PO2 PO3 PO4
		#switch off any device drawing too much power
		fpga, handle, opt = configControl.openComm()
		for loc in diagnostics[0]: #power each device off and on
			configControl.powerOff(handle, loc)
			configControl.powerOn(handle, loc)
		configControl.closeComm(handle)

	if diagnostics[1] != 0: #connection to the FPGA may have been lost
		is_awake = False
		while not is_awake: #atttempt to reconnect until FPGA responds
			attempt = configControl.openComm()
			if attempt != None:
				is_awake = True
				configControl.closeComm(attempt[1])
		main()

	if diagnostics[2][0]: #checks if optimization is needed, may need more conditions to actually run optimization.
		optimize(diagnostics[2][1])

#This main loop may be modified depending on the satellite's mode
def main(old_counter=0):
	"""
	Main control loop for NODE, this may be modified depending on the satellite's mode in the future.

	Args:
		old_counter(int): last clock cycle count read from FPGA
	"""
	while(True): #main control loop
		data = readTelemetry() #Read relevant data on RPi and Devices
		diagnostics = alarms(old_counter, data) #Check if system is in working conditions according to reading status fla
		old_counter = data['FRC'] #Set old counter to # clock cycles last read
		updateTelemetry(data, diagnostics) #Updates file holding all information which PL will be reading
		errorHandle(diagnostics) #Handle errors  

		#Find if NODE sat is communications enabled
		c = ConfigParser.RawConfigParser()
		c.read('args.ini')
		comm_enabled = c.getboolean('ModeSettings', 'comm_enabled')

		if(comm_enabled): #Is the sat in communication mode with connected devices	
			processCamData() #Take data from camera centering and process in RPI
			updateFSM() #Update FSM according to data that was processed
			##The two proccesses above might be a single one, ask for clarification
			updateOthers() #Update other devices connected to FPGA or rpi
			sendData() #Send data to PL if this is needed, dont know how this would work if we are configured as a slave

		#if there is information incoming from PL
		## might need to implement this in a different way depending on the latency, ex. break while loop and handle immediately if necessary
		interrupt() #Read incoming data and then return to while loop

if __name__ == '__main__':
	main()

"""
General Notes:
	
	Need to figure out how to communicate with PL Bus as slave, how to handle interrupts. Check if there is a FIFO at bus to act as buffer if data is received during control
	loop or if an immediate interrupt is required to handle incoming data without loss.

	ONdrejs loop will always be running
"""