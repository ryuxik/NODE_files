import test.mmap_test.py as mmap
from test.constants import ALL_C
"""
This is to test the currents of devices during the alarms section of the cotrol code.
It reports errors when devices are not cosuming the current they should be consuming.
"""

#this dictionary holds the locations to be tested along with their respective bounds for acceptable currents
##need to find the lower and upper bound current for each of these and then store the results in an error report
bounds = {
			'CC1a': (ALL_C['CC1a_LOW'],ALL_C['CC1a_HIGH']), 'CC1b': (ALL_C['CC1b_LOW'],ALL_C['CC1b_HIGH']), 'CC2a': (ALL_C['CC2a_LOW'],ALL_C['CC2a_HIGH']),
			'CC2b': (ALL_C['CC2b_LOW'],ALL_C['CC2b_HIGH']), 'CC3a': (ALL_C['CC3a_LOW'],ALL_C['CC3a_HIGH']), 'CC3b': (ALL_C['CC3b_LOW'],ALL_C['CC3b_HIGH']),
			'CC4a': (ALL_C['CC4a_LOW'],ALL_C['CC4a_HIGH']), 'CC4b': (ALL_C['CC4b_LOW'],ALL_C['CC4b_HIGH']), 'LCCa': (ALL_C['LCCa_LOW'],ALL_C['LCCa_HIGH']),
			'LCCb': (ALL_C['LCCb_LOW'],ALL_C['LCCb_HIGH'])
		}


def code2current(code):
	"""
	Takes data received from a channel and converts it to a current

	Args:
		code(): data received from channel
	Returns
		current(double): current derived from code
	"""
	##need to implement converter from data read to current
	##something like this
	# def code2byte(code):
 #    	fb = code/256
 #    	sb = code%256
 #    	return fb, sb
	# def code2voltage(c):
 #    	max_code = 2**12 #assuming 12-bit ADC
 #    	V_cc = 3.3 #assuming 3.3V source
 #    	return c*(V_cc/max_code)


	pass

def start(old_vid_pid, new_vid_pid):
	m = mmap.tester(old_vid_pid, new_vid_pid) #initialize memmory map
	return m

def end(m):
	m.end(m.fpga)


def clock_cycles_since_reset(m, old_counter):
	counter = m.read(m.fpga, m.get_addr('FRC'))
	if old_counter == counter:
		#'Error: counter since last reset has not changed, possible comm loss'
		return counter
	elif old_counter < counter:
		#'Counter increased to: ', counter, 'delta: ', (counter- old_counter)
		return 0
	else:
		#'Counter decreased to: ', counter, 'delta: ', (counter-old_counter) 
		return 0

def read_SEM(m):
	flags = m.read(m.fpga, m.get_addr('SFL'))
	status = m.read(m.fpga, m.get_addr('SST'))

	return (flags, status)
def check_currents(m):
	"""
	Checks that the currents are correct and returns report

	Args:
		old_vid_pid(): vendor and product id
		new_vid_pid(): vendor and product id
	Returns
		0 if no errors
		out_of_range(list): list of tuples with (location, current) if they are out of bounds
	"""

	
	out_of_range = [] #array to hold out of range failures
	for key in bounds:
		data = m.read(m.fpga, m.get_addr(key))
		current = code2current(data)
		if current < bounds[key][0] or current > bounds[key][1]:
			out_of_range.append((key, current))
	if len(out_of_range) > 0:
		return out_of_range
	return 0



