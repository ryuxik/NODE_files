import test.mmap_test.py as mmap
"""
This is to test the currents of devices during the alarms section of the cotrol code.
It reports errors when devices are not cosuming the current they should be consuming.
"""

#this dictionary holds the locations to be tested along with their respective bounds for acceptable currents
##need to find the lower and upper bound current for each of these and then store the results in an error report
bounds = {
			'CC1a': (0,0), 'CC1b': (0,0), 'CC2a': (0,0), 'CC3a': (0,0), 'CC3b': (0,0), 'CC4a': (0,0),
			'CC4b': (0,0), 'LCCa': (0,0), 'LCCb': (0,0)
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
	pass

def check_currents(old_vid_pid, new_vid_pid):
	"""
	Checks that the currents are correct and returns report

	Args:
		old_vid_pid(): vendor and product id
		new_vid_pid(): vendor and product id
	Returns
		0 if no errors
		out_of_range(list): list of tuples with (location, current) if they are out of bounds
	"""

	m = mmap.tester(old_vid_pid, new_vid_pid) #initialize memmory map
	out_of_range = [] #array to hold out of range failures
	for key in bounds:
		data = m.read(m.fpga, m.get_addr(key))
		current = code2current(data)
		if current < bounds[key][0] or current > bounds[key][1]:
			out_of_range.append((key, current))

	if len(out_of_range) > 0:
		return out_of_range
	return 0



