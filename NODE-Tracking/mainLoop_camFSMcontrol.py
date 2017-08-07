import camFSMcontrol

assert 'mainLoop' in dir(camFSMcontrol)
assert callable(camFSMcontrol.mainLoop)

camFSMcontrol.mainLoop()