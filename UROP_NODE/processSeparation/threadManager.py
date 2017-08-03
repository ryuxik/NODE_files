import logging
import multiprocessing

from mainProcess import controlLoop
##from camFSMcontrolProcess import ???

if __name__ == '__main__':
	#setup logging for debugging purposes
	multiprocessing.log_to_stderr()
	logger = multiprocessing.get_logger()
	logger.setLevel(logging.INFO)

	#setting up Processes
	m = multiprocessing.Process(name='controlLoop',target=controlLoop)
	c = multiprocessing.Process(name='camFSMloop',target=??) #this target should be the wrapper that we write for Ondrej's camera tracking
	
	m.start()
	c.start()