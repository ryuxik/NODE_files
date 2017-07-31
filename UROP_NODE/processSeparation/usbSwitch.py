import pinController

def switch():
	"""
	Switches rpi connection from slave to master or vice-versa.
	Uses lock to ensure only this process is running
	"""
	try:
		if pinController.isBusMaster():
			pinController.makeBusSlave()
		elif pinController.isBusSlave():
			pinController.makeBusMaster()
	except:
		raise NameError('Switch failed.') 