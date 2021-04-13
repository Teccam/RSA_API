# Settings ####################################################
cf=227360000
refLevel=-20
bw=40.0e6
durationMsec = 1800000
fileDir='C:/RFRecordings'
projectName = 'TestRecording'
reference = 'internal' # default = internal




# Main ########################################################

from ctypes import *
from os import chdir
import os
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from RSA_API import *
from datetime import datetime
from matplotlib import __version__ as __mversion__
print('Matplotlib Version:', __mversion__)
print('Numpy Version:', np.__version__)


# C:\Tektronix\RSA_API\lib\x64 needs to be added to the
# PATH system environment variable
chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")

## prepare recording folder and fileName
now = datetime.now()
print("now =", now)
dt_string = now.strftime("%Y%m%d_%H%M%S")
path = fileDir + '/' + dt_string + '_' + str(cf) + '_Hz'
try:
    os.mkdir(path)
except OSError:
    print("Creation of directory %s failed" % path)
else:
    print("Directory created")
       
fileDir = path

fileName = projectName + '_' + dt_string + '_' + str(int(cf)) + 'Hz'

"""################CLASSES AND FUNCTIONS################"""
def err_check(rs):
    if ReturnStatus(rs) != ReturnStatus.noError:
        raise RSAError(ReturnStatus(rs).name)

def search_connect():
    numFound = c_int(0)
    intArray = c_int * DEVSRCH_MAX_NUM_DEVICES
    deviceIDs = intArray()
    deviceSerial = create_string_buffer(DEVSRCH_SERIAL_MAX_STRLEN)
    deviceType = create_string_buffer(DEVSRCH_TYPE_MAX_STRLEN)
    apiVersion = create_string_buffer(DEVINFO_MAX_STRLEN)

    rsa.DEVICE_GetAPIVersion(apiVersion)
    print('API Version {}'.format(apiVersion.value.decode()))

    err_check(rsa.DEVICE_Search(byref(numFound), deviceIDs,
                                deviceSerial, deviceType))

    if numFound.value < 1:
        # rsa.DEVICE_Reset(c_int(0))
        print('No instruments found. Exiting script.')
        exit()
    elif numFound.value == 1:
        print('One device found.')
        print('Device type: {}'.format(deviceType.value.decode()))
        print('Device serial number: {}'.format(deviceSerial.value.decode()))
        err_check(rsa.DEVICE_Connect(deviceIDs[0]))
    else:
        # corner case
        print('2 or more instruments found. Enumerating instruments, please wait.')
        for inst in deviceIDs:
            rsa.DEVICE_Connect(inst)
            rsa.DEVICE_GetSerialNumber(deviceSerial)
            rsa.DEVICE_GetNomenclature(deviceType)
            print('Device {}'.format(inst))
            print('Device Type: {}'.format(deviceType.value))
            print('Device serial number: {}'.format(deviceSerial.value))
            rsa.DEVICE_Disconnect()
        # note: the API can only currently access one at a time
        selection = 1024
        while (selection > numFound.value - 1) or (selection < 0):
            selection = int(raw_input('Select device between 0 and {}\n> '.format(numFound.value - 1)))
        err_check(rsa.DEVICE_Connect(deviceIDs[selection]))
    rsa.CONFIG_Preset()

"""################IQ STREAMING EXAMPLE################"""
def config_iq_stream(cf=cf, refLevel=refLevel, bw=bw, fileDir=fileDir,
                     fileName=fileName, dest=IQSOUTDEST.IQSOD_FILE_SIQ,
                     suffixCtl=IQSSDFN_SUFFIX_NONE,
                     dType=IQSOUTDTYPE.IQSODT_INT16,
                     durationMsec=1000,reference=reference):
    filenameBase = fileDir + '\\' + fileName
    bwActual = c_double(0)
    bufferSizeActual = c_int(0)
    sampleRate = c_double(0)
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))
    if reference == 'external':
        rsa.CONFIG_SetExternalRefEnable()
        
    # increase buffer size for highest data rate
    rsa.IQSTREAM_SetIQDataBufferSize(8*65536)
    rsa.IQSTREAM_GetIQDataBufferSize(byref(bufferSizeActual))
    print('BufferSize',bufferSizeActual)

    rsa.IQSTREAM_SetAcqBandwidth(c_double(bw))
    rsa.IQSTREAM_SetOutputConfiguration(dest, dType)
    rsa.IQSTREAM_SetDiskFilenameBase(c_char_p(filenameBase.encode()))
    rsa.IQSTREAM_SetDiskFilenameSuffix(suffixCtl)
    rsa.IQSTREAM_SetDiskFileLength(c_int(durationMsec))
    rsa.IQSTREAM_GetAcqParameters(byref(bwActual), byref(sampleRate))
    rsa.IQSTREAM_ClearAcqStatus()


def iqstream_status_parser(iqStreamInfo):
    # This function parses the IQ streaming status variable
    status = iqStreamInfo.acqStatus
    if status == 0:
        print('\nNo error.\n')
    if bool(status & 0x10000):  # mask bit 16
        print('\nInput overrange.\n')
    if bool(status & 0x40000):  # mask bit 18
        print('\nInput buffer > 75{} full.\n'.format('%'))
    if bool(status & 0x80000):  # mask bit 19
        print('\nInput buffer overflow. IQStream processing too slow, ',
              'data loss has occurred.\n')
    if bool(status & 0x100000):  # mask bit 20
        print('\nOutput buffer > 75{} full.\n'.format('%'))
    if bool(status & 0x200000):  # mask bit 21
        print('Output buffer overflow. File writing too slow, ',
              'data loss has occurred.\n')


def iq_stream_example(durationMsec):
    print('\n\n########IQ Stream Example########')
    search_connect()

    dest = IQSOUTDEST.IQSOD_FILE_SIQ_SPLIT

    waitTime = 0.1
    iqStreamInfo = IQSTREAM_File_Info()

    complete = c_bool(False)
    writing = c_bool(False)

    config_iq_stream(bw=bw, dest=dest, durationMsec=durationMsec)

    rsa.DEVICE_Run()
    rsa.IQSTREAM_Start()
    while not complete.value:
        sleep(waitTime)
        rsa.IQSTREAM_GetDiskFileWriteStatus(byref(complete), byref(writing))
    rsa.IQSTREAM_Stop()
    print('Streaming finished.')
    rsa.IQSTREAM_GetFileInfo(byref(iqStreamInfo))
    iqstream_status_parser(iqStreamInfo)
    rsa.DEVICE_Stop()
    rsa.DEVICE_Disconnect()


def main():
    iq_stream_example(durationMsec)

if __name__ == '__main__':
    main()
