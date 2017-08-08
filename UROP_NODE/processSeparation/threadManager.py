"""
This is the process manager for NODE. It starts both the main control process
and the cam fsm process.
"""
import multiprocessing

from mainProcess import controlLoop
##from camFSMcontrolProcess import ???

if __name__ == '__main__':
	
	#setting up Processes
	m = multiprocessing.Process(name='controlLoop',target=controlLoop)
	c = multiprocessing.Process(name='camFSMloop',target=??) #this target should be the wrapper that we write for Ondrej's camera tracking
	
	m.start()
	c.start()