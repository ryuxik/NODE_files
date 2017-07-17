"""
This is pseudocode trying to follow Rodrigo's sketch of how we will first approach the sat control
"""
import errorDetect
import mmap
import busComm
import ConfigParser

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
	#need to check if data is valid command, then set valid to true

	if valid:
		setValues(dataFromBus) #Set values according to data received
		
def setValues(dataFromBus):
	"""
	Parse bin data from PL and do things with data

	Args:
		dataFromBus()
	"""

	##need information about the format of the data!!
	pass

def alarms(old_counter, data):
	"""
	Checks data read for possible errors and returns report

	Args:
		old_counter(int): clock cycle count read last loop
		data(dict): memmory map location name to data read
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

def updateTelemetry():
	#not sure what this means yet
	pass

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

def optimize():
	"""
	Optimizes current and temperature for power efficiency.
	"""
	pass

def errorHandle(diagnostics):
	"""
	Corrects errors detected by diagnostics report from alarms(). Inlcudes call to optimization if necessary.

	Args:
		diagnostics(list): list containing error reports
	"""
	##do something with diagnostics 0 and 1.
	if diagnostics[2]: #checks if optimization is needed, may need more conditions to actually run optimization.
		optimize()

def main(old_counter=0):
	planetLabBus = False
	while(True): #main control loop
		data = readTelemetry() #Read relevant data on RPi and Devices
		diagnostics = alarms(old_counter, data) #Check if system is in working conditions according to reading status fla
		old_counter = data['FRC'] #Set old counter to # clock cycles last read
		errorHandle(diagnostics) #Handle errors  
		updateTelemetry() ##Ask rodrigo about this part!
		
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
"""