import fl

class board(object):
	"""
	FPGA board class

	Args: 
		vid_pid: vendor id and product id of FPGA board
		debug_level(int): specifies to fl library functions the log level to report
		conduit(int): specifies the conduit used for implementing comm protocols
	"""
	def __init__(self, vid_pid, debug_level, conduit):
		self.vid_pid = vid_pid
		self.debug_level = debug_level
		if conduit == None:
			self.conduit = 1
		else:
			self.conduit = conduit
		
	def init_com_test(self):
	"""
	Test intial connection capabilities to FPGA board over USB.

	Returns:
		results(list): list of strings representing reports of passed and failed tests.

	"""
		results = []
		fl.flInitialise(self.debug_level) #initializes library
		if fl.flIsDeviceAvailable(self.vid_pid): #checks if fpga is available
			results.append('USB bus with: ', self.vid_pid,' was found.')
			try:
				handle = fl.flOpen(self.vid_pid) #opens connection to FPGA board
				results.append('Successfully opened connection to FPGA board.')
				if fl.flIsCommCapable(handle, self.conduit): #checks if FPGA board is capable of communication
					results.append('FPGA board supports functions: flIsFPGARunning(), flReadChannel(), flWriteChannel(), flSetAsyncWriteChunkSize(), flWriteChannelAsync(), flFlushAsyncWrites(), \c flAwaitAsyncWrites(), \c flReadChannelAsyncSubmit(),flReadChannelAsyncAwait().')
					try:
						fl.flSelectConduit(handle, self.conduit) #selects given conduit 
						results.append('Selected conduit ', self.conduit)
						if fl.flIsFPGARunning(handle): #checks if board is ready to acccept commands
							results.append('FPGA board is ready to accept commands.')
					except:
						results.append('Conduit was out of range or device did not respond.')			
				else:
					results.append('FPGA board cannot communicate.')
				fl.flClose(handle) #closes connection to FPGA board to avoid errors
				results.append('Connection to the FPGA board was closed.')
			except:
				results.append('Connection to FPGA board failed.')
		else:
			results.append('The VID:PID: ', self.vid_pid,' is invalid or no USB buses were found.')
		return results



