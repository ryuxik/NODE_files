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
	config = ConfigParser.read('args.ini')
	connection = busComm.Connection(
									config.get('ConnectionInfo', 'plBus_vid'), config.get('ConnectionInfo', 'plBus_pid'),
									config.get('ConnectionInfo', 'plBus_packet_size'), config.get('ConnectionInfo', 'plBus_timeout'),
									config.get('ConnectionInfo', 'plBus_wendpoint'), config.get('ConnectionInfo', 'plBus_rendpoint'))

	dataFromBus = connection.updateReceived()
	valid = False
	##need to check if data is valid command, then set valid to true

	if valid:
		setValues(dataFromBus) #Set values according to data received
		
def setValues(dataFromBus):
	"""
	Parse data from PL and do things with data

	Args:
		dataFromBus(): data received from PL
	"""

	##need information about the format of the data!!
	pass

def alarms(old_counter, data):
	"""
	Checks data read for possible errors and returns report

	Args:
		old_counter(int): clock cycle count read last loop
		data(dict): memmory map location name to data read
	Returns: 
		diagnostics(list): 
	"""
	diagnostics = errorDetect.AlarmRaiser(old_counter, data)
	return diagnostics

def readTelemetry():
	"""
	Reads all addresses from memmory map and stores data in dictionary

	Returns:
		data(dict): memmory map location name to data read
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
	config = ConfigParser.read('args.ini')
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
		condition = None #implement condition for just scan or dither mode not sure which
		if condition:
			obslength = None #Don't know what this is yet
			opt.dither_mode(obslength)
		else:
			opt.scan_mode(obslength)
		
		configControl.closeComm(handle) #closes communication to fpga
	except: #connection open failed :(
		raise ConnectionError('Connection to the fpga failed')
		
def errorHandle(diagnostics):
	"""
	Corrects errors detected by diagnostics report from alarms(). Inlcudes call to optimization if necessary.

	Args:
		diagnostics(list): list containing error reports
	"""
	if diagnostics[0] != 0: #a device is taking too much current #list should be locations, PO1 PO2 PO3 PO4
		#switch off any device drawing too much power
		fpga, handle, opt = configControl.openComm()
		for loc in diagnostics[0]: #power each device off and on
			configControl.powerOff(handle, loc)
			configControl.powerOn(handle, loc)

	if diagnostics[1] != 0: #connection to the FPGA may have been lost
		isAwake = False
		while not isAwake: #atttempt to reconnect until FPGA responds
			attempt = configControl.openComm()
			if attempt != None:
				isAwake = True
				configControl.closeComm()
		main()

	if diagnostics[2][0]: #checks if optimization is needed, may need more conditions to actually run optimization.
		optimize(diagnostics[2][1])

#This main loop may be modified depending on the satellite's mode
def main(old_counter=0):
	planetLabBus = False
	while(True): #main control loop
		data = readTelemetry() #Read relevant data on RPi and Devices
		diagnostics = alarms(old_counter, data) #Check if system is in working conditions according to reading status fla
		old_counter = data['FRC'] #Set old counter to # clock cycles last read
		updateTelemetry(data, diagnostics) #Updates file holding all information which PL will be reading
		errorHandle(diagnostics) #Handle errors  
		
		if(commEnabled): #Is the sat in communication mode with connected devices
		##make logic for determining commEnabled!, may be set by data read from PL	
			processCamData() #Take data from camera centering and process in RPI
			updateFSM() #Update FSM according to data that was processed
			##The two proccesses above might be a single one, ask for clarification
			updateOthers() #Update other devices connected to FPGA or rpi
			sendData() #Send data to PL if this is needed

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