import pinController

#Single Loop of Process goes here
##Implement Threading later

def switch(lock):
	if pinController.isBusMaster():
		pinController.makeBusSlave()
	elif pinController.isBusSlave():
		pinController.makeBusMaster()
