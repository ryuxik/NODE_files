import fl

"""
@Author: Santiago Munoz
@Date: 6/19/2017

	This is to test the connection from the rpi to the FPGA board over USB using the fl library. 
"""

class Board(object):
	"""
	FPGA board class

	Args: 
		vid_pid_did: vendor id and product id and device id of FPGA board
		debug_level(int): specifies to fl library functions the log level to report
		conduit(int): specifies the conduit used for implementing comm protocols
	"""
	def __init__(self, vid_pid_did, debug_level, conduit):
		self.vid_pid_did = vid_pid_did #has this format ==> 1D50:602B:0001
		self.debug_level = debug_level
		if conduit == None:
			self.conduit = 1
		else:
			self.conduit = conduit
		
	def initComTest(self):
	"""
	Test intial connection capabilities to FPGA board over USB.

	Returns:
		results(list): list of strings representing reports of passed and failed tests.

	"""
		results = []
		fl.flInitialise(self.debug_level) #initializes library
		if fl.flIsDeviceAvailable(self.vid_pid_did): #checks if fpga is available
			results.append('P','USB bus with: ', self.vid_pid_did,' was found.')
			try:
				handle = fl.flOpen(self.vid_pid_did) #opens connection to FPGA board
				results.append('P','Successfully opened connection to FPGA board.')
				if fl.flIsNeroCapable(handle): #checks if device is Nero capable
					results.append('P', 'Device is Nero capable.')
				else:
					results.append('F', 'Device is not Nero capable.')
				if fl.flIsCommCapable(handle, self.conduit): #checks if FPGA board is capable of communication
					results.append('P','FPGA board supports functions: flIsFPGARunning(), flReadChannel(), flWriteChannel(), flSetAsyncWriteChunkSize(), flWriteChannelAsync(), flFlushAsyncWrites(), \c flAwaitAsyncWrites(), \c flReadChannelAsyncSubmit(),flReadChannelAsyncAwait().')
					try:
						fl.flSelectConduit(handle, self.conduit) #selects given conduit 
						results.append('P','Selected conduit ', self.conduit)
						if fl.flIsFPGARunning(handle): #checks if board is ready to acccept commands
							results.append('P','FPGA board is ready to accept commands.')
					except:
						results.append('F','Conduit was out of range or device did not respond.')			
				else:
					results.append('F','FPGA board cannot communicate.')
				fl.flClose(handle) #closes connection to FPGA board to avoid errors
				results.append('P','Connection to the FPGA board was closed.')
			except:
				results.append('F','Connection to FPGA board failed.')
		else:
			results.append('F','The VID:PID:DID ', self.vid_pid_did,' is invalid or no USB buses were found.')
		return results



