import logging
import multiprocessing

from multiprocessing import Process, Lock, Event
from usbSwitchProcess import switch
from mainProcess import controlLoop
##from camFSMcontrolProcess import ???
##from optimizingProcess import ???

if __name__ == '__main__':
	#setup logging for debugging purposes
	multiprocessing.log_to_stderr()
	logger = multiprocessing.get_logger()
	logger.setLevel(logging.INFO)

	#use locks for optimization and usbSwitch
	lock = Lock()
	#use event for camFSM and controlLoop
	camFSMevent = Event()
	controlLoopEvent = Event()

	#setting up Processes
	##figure out what to do with default arg to controlLoop 
	m = Process(target=controlLoop, args=())
	s = Process(target=switch, args=(lock,))