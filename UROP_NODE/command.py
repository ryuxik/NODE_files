"""
This is pseudocode trying to follow Rodrigo's sketch of how we will first approach the sat control
"""
import errorDetect
import mmap
import 

def interrupt(): 
	# Data is coming in through PL bus, trigger interupt to handle it
	setValues(dataFromBus) 
		# Set values according to data received, return to while loop at end

def alarms():
	diagnostics = errorDetect.AlarmRaiser()
	#do something with the diagnostic report

def readTelemetry():
	t = mmap.Tester()
    data = t.readAll()
    t.end()
    return data

def updateTelemetry():
	pass

def processCamData():
	pass

def updateFSM():
	pass

def updateOthers():
	pass

def sendData():
	pass

def main():
	while(True): #main control loop
		data = readTelemetry()
			# Read relevant data on RPi and Devices, ask rodrigo about this
		alarms() 
			# 1. Check if system is in working conditions according to reading status flags
			# 2. Handle errors 
			     	#ex. Device drawing too much power
			
			#if currents_errors != 0:
				##implement currents error handling here
				#handle()

			# (possible errors)
			# Check FRC and see if it matches the stored value of clock cycles since last intentional reset

			# Check CC1a, CC1b, CC2a, CC3a, CC4a, CC4b, LCCa, LCCb

		updateTelemetry() 
			# Update devices according to data read from PL Bus
		if(commEnabled): 
			# Is the sat in communication mode with connected devices
			processCamData() 
				# Take data from camera centering and process in RPI
			updateFSM() 
				# Update FSM according to data that was processed
			#The two proccesses above might be a single one
			updateOthers() 
				# Update other devices connected to FPGA or rpi
			sendData() 
				# Send data

		if(planetLabBus):
			interrupt()

if __name__ == '__main__':
	main()

"""
General Notes:
	
	Need to figure out how to communicate with PL Bus as slave, how to handle interrupts. Check if there is a FIFO at bus to act as buffer if data is received during control
	loop or if an immediate interrupt is required to handle incoming data without loss.
"""