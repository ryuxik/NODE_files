"""
@Author: Santiago Munoz
@Date: 6/13/17
	
	Acceptance test for the Rasperry Pi Baseboard with the Modulator, Camera, and Bus.
"""
import test.busComm as comm
import test.fpga_link_test as flink

if __name__ == "__main__":
	testsPassed = False
	vid_pid = 101 # replace with proper vendor and product id of FPGA board
	debug_level = 0 #replace with desired debug level for fl API
	busONE_directory = "b1" #replace with proper dir
	busTWO_directory = 'b2' #replace with proper dir
	camera_directory = "c" #replace with proper dir
	modulator_directory = "m" #replace with proper dir
	slave_switch_directory = 'ss' #replace with proper dir
	master_switch_directory = 'ms' #replace with proper dir
	results = [] #array containing test results

	#Making instances of necessary connections for test
	#these are using serial, may want to use fl instead
	busONE = comm.serialW(busONE_directory,True)
	busTWO = comm.serialW(busONE_directory)
	cam = comm.serialW(camera_directory)
	mod = comm.serialW(modulator_directory)
	ss = comm.serialW(slave_switch_directory)
	ms = comm.serialW(master_switch_directory)

	fpga = flink.board(vid_pid, debug_level, None)


	#Testing intial connection to bus
	try:
		#busONE.testConnection()
		r = fpga.init_com_test()
		results.extend(r)
	except:
		results.append('F','Initial connection to bus failed')

	#Testing switch of bus to slave
	try:
		#implement a slave test here!!
		results.append('P','Switch of bus to slave successfull')
	except:
		results.append('F','Switch of bus to slave failed')
		
	#Testing connection to bus as slave
	try:
		busTWO.testConnection()
		results.append('P','Connection to bus as slave successfull')
	except:
		results.append('F','Connection to bus as slave failed')

	#Testing connection to camera
	try:
		cam.testConnection()
		results.append('P','Connection to camera successfull')
	except:
		results.append('F','Connection to camera failed')

	#Testing connection to modulator
	try:
		mod.testConnection()
		results.append('P','Connection to modulator successfull')
	except:
		results.append('F','Connection to modulator failed')

	#Make tests using memmory map here!!
	#or implement those tests as part of the connection tests


	#print(results) #see results of tests
	failures = [statement[1:] for statement in results if statement[0] == 'F']
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