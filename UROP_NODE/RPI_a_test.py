"""
@Author: Santiago Munoz
@Date: 6/13/17
	
	Acceptance test for the Rasperry Pi Baseboard with the Modulator, Camera, and Bus.
"""
import test.busComm as comm
import test.fpga_link_test as flink
import test.mmap_test.py as mmap
from restruct.node import NodeFPGA 

if __name__ == "__main__":
	testsPassed = False
	progConfig = '' #replace with FPGA config file
	old_vid_pid = '1:0:1' # replace with proper vendor and product id and device id of FPGA board
	new_vid_pid = ''
	debug_level = 0 #replace with desired debug level for fl API
	busONE_directory = "b1" #replace with proper dir, represents intial directory of bus to master usb port
	busTWO_directory = 'b2' #replace with proper dir, represents directory of bus to slave usb hub
	camera_directory = "c" #replace with proper dir, repesents directory of camera to slave usb hub
	usb1_switch_directory = 'ss' #replace with proper dir, represents directory of switch for usb1.1
	usb2_switch_directory = 'ms' #replace with proper dir, represents directory of switch for usb2.0
	results = [] #array containing test results

	#Making instances of necessary connections for test
	busONE = comm.serialW(busONE_directory,True)
	busTWO = comm.serialW(busONE_directory)
	cam = comm.serialW(camera_directory)
	uONE = comm.serialW(usb1_switch_directory)
	uTWO = comm.serialW(usb2_switch_directory)
	mem = mmap.tester(old_vid_pid, new_vid_pid)

	init_fpga_board_tester = flink.board(vid_pid_did, debug_level, None)

	#Testing intial connection to bus
	try:
		busONE.testConnection()
	except:
		results.append('F','Initial connection to bus failed')

	#Testing connection to camera
	try:
		cam.testConnection()
	except:
		results.append('F','Connection to camera failed')

	#Testing connection to FPGA board
	try:
		results.extend(init_fpga_board_tester.init_com_test()) #run tests and return list of to extend results report
	except:
		results.append('F','FPGA inital connection test failed to run.')
	
	#Make tests using memmory map here!!
	try:
		results.extend(mem.test(progConfig))
	except:
		results.append('F','Memmory map command testing to FPGA test failed to run.')

	#Testing switch of bus to slave
	try:
		#implement a slave test here!!
		pass
	except:
		results.append('F','Switch of bus to slave failed')
		
	#Testing connection to bus as slave
	try:
		busTWO.testConnection()
	except:
		results.append('F','Connection to bus as slave failed')

	#print(results) #see results of tests

	#Check for F at as the first element of every statement, if so, add it to list of failures
	failures = [statement[1:] for statement in results if statement[0] == 'F']

	#Check if all tests have passed
	if len(failures) == 0:
		testsPassed = True

	#store results in text file
	f = open('results','w')
	if testsPassed:
		f.write('All tests passed')
	else:
		for r in failures:
			f.write(r)
	f.close()