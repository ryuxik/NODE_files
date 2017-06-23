import fl
import argparse
import time
import struct
import csv
from datetime import datetime
from node import NodeFPGA
import sys
import math as m
from bench import LaserController
from mmap import tester

DEBUG = False

# FPGA image
#FPGA_IMAGE = "/home/kingryan/Dropbox/grad_school/fpga/makestuff/hdlmake/apps/roamingryan/swled/bist/vhdl/top_level.xsvf"


# File-reader which yields chunks of data
def readFile(fileName):
    with open(fileName, "rb") as f:
        while True:
            chunk = f.read(32768)
            if chunk:
                yield chunk
            else:
                break

def code2byte(code):
    fb = code/256
    sb = code%256
    return fb, sb

def update_SPI(handle, channels, byte_array):
    MSB_channel = channels[0]
    LSB_channel = channels[1]
    fl.flWriteChannel(handle, MSB_channel, byte_array[0])
    fl.flWriteChannel(handle, LSB_channel, byte_array[1])

def read_SPI(handle, channels):
    MSB_channel = channels[0]
    LSB_channel = channels[1]
    rxm = fl.flReadChannel(handle, MSB_channel)
    rxl = fl.flReadChannel(handle, LSB_channel)
    return [rxm, rxl]

def voltage2code(v):
    max_code = 2**12 #assuming 12-bit ADC
    V_cc = 3.3  #assuming 3.3V source
    return v*(max_code/3.3)

def code2voltage(c):
    max_code = 2**12 #assuming 12-bit ADC
    V_cc = 3.3 #assuming 3.3V source
    return c*(V_cc/max_code)

print("NODE FPGA SPI Commander\n")
parser = argparse.ArgumentParser(description='Load FX2LP firmware, load the FPGA, interact with the FPGA.')
parser.add_argument('-i', action="store", nargs=1, metavar="<VID:PID>", help="vendor ID and product ID (e.g 1443:0007)")
parser.add_argument('-v', action="store", nargs=1, required=True, metavar="<VID:PID>", help="VID, PID and opt. dev ID (e.g 1D50:602B:0001)")
#parser.add_argument('-d', action="store", nargs=1, metavar="<port+>", help="read/write digital ports (e.g B13+,C1-,B2?)")
parser.add_argument('-q', action="store", nargs=1, metavar="<jtagPorts>", help="query the JTAG chain")
parser.add_argument('-p', action="store", nargs=1, metavar="<config>", help="program a device")
parser.add_argument('-c', action="store", nargs=1, metavar="<conduit>", help="which comm conduit to choose (default 0x01)")
parser.add_argument('-f', action="store", nargs=1, metavar="<dataFile>", help="binary data to write to channel 0")
argList = parser.parse_args()

print (argList)


handle = fl.FLHandle()
try:
    fl.flInitialise(0)

    vp = argList.v[0]
    print("Attempting to open connection to FPGALink device {}...".format(vp))
    try:
        handle = fl.flOpen(vp)
    except fl.FLException as ex:
        if argList.i:
            ivp = argList.i[0]
            print("Loading firmware into {}...".format(ivp))
            fl.flLoadStandardFirmware(ivp, vp)
            mem_map = tester(ivp,vp)

            # Long delay for renumeration
            # TODO: fix this hack.  The timeout value specified in flAwaitDevice() below doesn't seem to work
            time.sleep(3)
            
            print("Awaiting renumeration...")
            if not fl.flAwaitDevice(vp, 10000):
                raise fl.FLException("FPGALink device did not renumerate properly as {}".format(vp))

            print("Attempting to open connection to FPGALink device {} again...".format(vp))
            handle = fl.flOpen(vp)
        else:
            raise fl.FLException("Could not open FPGALink device at {} and no initial VID:PID was supplied".format(vp))
    
    # if ( argList.d ):
    #     print("Configuring ports...")
    #     rb = "{:0{}b}".format(fl.flMultiBitPortAccess(handle, argList.d[0]), 32)
    #     print("Readback:   28   24   20   16    12    8    4    0\n          {} {} {} {}  {} {} {} {}".format(
    #         rb[0:4], rb[4:8], rb[8:12], rb[12:16], rb[16:20], rb[20:24], rb[24:28], rb[28:32]))
    #     fl.flSleep(100)

    conduit = 1
    if argList.c:
        conduit = int(argList.c[0])

    isNeroCapable = fl.flIsNeroCapable(handle)
    isCommCapable = fl.flIsCommCapable(handle, conduit)
    fl.flSelectConduit(handle, conduit)
   
    if argList.f and not(isCommCapable):
        raise fl.FLException("Data file load requested but device at {} does not support CommFPGA".format(vp))

    if isCommCapable and fl.flIsFPGARunning(handle):
        fpga = NodeFPGA(handle)
        #Test setting LD Bias to 0.150A (channels 26, 27)
        curr = 0.150
        code = curr/(4.096*1.1*((1/6.81)+(1/16500)))*4096
        first_byte, second_byte = code2bytes(code)
        spi_data = [first_byte, second_byte]
        update_SPI(handle, [mem_map.get_addr('LCCa'),mem_map.get_addr('LCCb')], spi_data) ####
        #Test reading LD Bias (channels 64 and 65)
        rx_bias = read_SPI(handle, [100,101])
        for r in rx_bias:
            print "Bias bytes read: ", r
        print (rx_bias[1]*256 + rx_bias[0])/4096 * (4.096*1.1*((1/6.81)+(1/16500)))

        #Test writing/reading to LD Temp
        #TODO Constants are estimated; may need to verify with vendor
        R_known = 10000
        Vcc = 0.8
        B = 3900
        R_0 = 10000
        T_0 = 25 
        #writing temp 35C
        T = 35
        V_set = Vcc/(((m.exp(B/T)*(R_0 * m.exp(-B/T_0)))/R_known)+1)
        V_code = voltage2code(V_set) #convert voltage to code
        fb, sb = code2byte(V_code) #convert code to bytes
        update_SPI(handle, [mem_map.get_addr('LTSa'),mem_map.get_addr('LTSb')], [fb, sb])

        #reading temp
        bytes__meas = read_SPI(handle, [mem_map.get_addr('LTMa'),mem_map.get_addr('LTMb')]) #read ADC value
        code_meas = bytes_meas[1]*256 + bytes_meas[0]#convert bytes to double
		V_meas = code2voltage(code_meas) #convert ADC to voltage

        R_t = R_known * (Vcc/V_meas - 1)
        T = B/m.log(R_t/R_0 * m.exp(-B/T_0))
        print ("Temp read: ", T)


        #Test reading from RTD
        A = 3.81e-3 #from datasheet
        B = -6.02e-7 #from datasheet
        R_t0 = 1000
        T_bm = read_SPI(handle, [mem_map.get_addr('TE1a'),mem_map.get_addr('TE1b')]) #temp code measured
		T_cm = 256*T_bm[1] + T_bm[0] #convert bytes to double
        T_meas = code2voltage(T_cm) #convert ADC to voltage
        R_T = R_known * (Vcc/T_meas - 1)
        C = 1 -( R_T/R_t0)
        T_R = (-A + (A**2-(4*B*C))**0.5) / (2*B)
        print ("RTD temp: ", T_R)

except fl.FLException as ex:
    print(ex)
finally:
    fl.flClose(handle)