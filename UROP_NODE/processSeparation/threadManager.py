import logging
import multiprocessing

from multiprocessing import Process, Lock, Event
from usbSwitchProcess import switch
from mainProcess import controlLoop
##from camFSMcontrolProcess import ???
from optimizingProcess import op

if __name__ == '__main__':
	#setup logging for debugging purposes
	multiprocessing.log_to_stderr()
	logger = multiprocessing.get_logger()
	logger.setLevel(logging.INFO)

	#use locks for optimization
	lock = Lock()
	#use event for camFSM and controlLoop
	event = Event()

	#setting up Processes
	##need to test if we can run camFSM stuff all the time concurrently with main
	##figure out what to do with default arg to controlLoop 
	m = Process(target=controlLoop, args=(lock, event))
	o = Process(target=op, args=(lock,))
	#fix this
	c = Process(target=???, args=(camFSMevent,))

	m.start()
	o.start()
	c.start()

	#think about concurrency issues when camFSM code does things to rpi pins as main loop runs,
	#may have to use locks to ensure pin writing doesnt cause errors