import optimizer
import configControl

def op():
	while True:
		try: #need to open connection
			fpga, handle, opt = configControl.openComm() #opens connection and returns fpga, handle, and optimizer objects
			obs_length = 1 #constant that will be decided in the future, 1 might work fine
			opt.scan_mode(obs_length) #may need to still add condition to this function, but don't need two separate functions
			configControl.closeComm(handle) #closes communication to fpga
		except: #connection open failed :(
			raise ConnectionError('Connection to the fpga failed')

