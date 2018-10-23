from __future__ import print_function
import numpy as np
import struct
import sys
import time


handle=open('/home/glicka/sis3316/data/SESSION2018-05-31T11_27_09-0700/NSC/Data_180531_112713_SESSION2018-05-31T11_27_09-0700.bin','rb')
#handle=open('/home/glicka/.local/share/Trash/files/SESSION2018-05-02T11_37_16-0700/NSC/Data_180502_113721_SESSION2018-05-02T11_37_16-0700.bin','rb')
# data=handle.read(92) # whole record read
rawData = []
timeData = []
lineNum = 0
tic = time.time()
while True:
    data=handle.read(4)
    #if len(data) == 0:
    if lineNum == 10:
        import h5py
        fileName = 'parseAttempt.h5'
        with h5py.File(fileName,'w') as f:
            #f = h5py.File(fileName, "w")
            f.create_dataset('timestamps',data=timeData)
            f.create_dataset('raw data',data=rawData)
        handle.close()
        break
    format_bits=np.frombuffer(data,dtype=np.uint32)[0]
    #print(bin(format_bits))
    format_bit0 = (format_bits >> 0) & 0x1
    format_bit1 = (format_bits >> 1) & 0x1
    format_bit2 = (format_bits >> 2) & 0x1
    format_bit3 = (format_bits >> 3) & 0x1
    for i in range(0,4):
        print( "format_bit%d"%i, format_bits>>i&(0x1))
        if format_bits>>i&(0x1) == 0:
            raise ValueError(
                'Format bits are unexpected: {}{}{}{} instead of 1111'.format(
                    format_bit0, format_bit1, format_bit2, format_bit3
                ))

    data=handle.read(4)
    ts=np.frombuffer(data,dtype=np.uint32)
    #print( "timestamp %d"%ts )
    timeData += [ts]

    if(format_bits&0x1): # ask for the first format bit
        data=handle.read(4)
        dt=np.dtype( {'names':['ind','val'], 'formats':[np.uint16,np.uint16] } )
        #print( data )
        pk=np.frombuffer(data,dtype=dt)
        #print( "pk info", pk['ind'], pk['val'] )

        data=handle.read(4)
        dt=np.dtype( {'names':['inf','upper_gate1','lower_gate1'], 'formats':[np.uint8,np.uint8,np.uint16] } )
        infgate=np.frombuffer(data,dtype=dt)
        gate1=infgate['upper_gate1']<<16+infgate['lower_gate1']
        info=infgate['inf']
        #print( "gate info", gate1, info )

        for i in range(2,7):
            data=handle.read(4)
            #print( "Gate %d data:"%i )
            gate_val=np.frombuffer(data,dtype=np.uint32)[0]
            #print("data consistency: ", 0x0 == gate_val&(0b1111<<28) )
            #print(gate_val)

    if(format_bits>>1&0x1):
        for i in range(7,9):
            data=handle.read(4)
            #print( "Gate %d data:"%i )
            gate_val=np.frombuffer(data,dtype=np.uint32)[0]
            #print("data consistency: ", 0x0 == gate_val&(0b1111<<28) )
            #print(gate_val)
        #print("not implemented!")
    if(format_bits>>2&0x1):
        for i in range(0,3):
            data=handle.read(4)
            #print( "MAW %d data:"%i )
            gate_val=np.frombuffer(data,dtype=np.uint32)[0]
            #print("data consistency: ", 0x0 == gate_val&(0b1111<<28) )
            #print(gate_val)
        #print("not implemented!")
    if(format_bits>>3&0x1):
        handle.read(4)
        handle.read(4)
        #print("not implemented!")

    data=handle.read(4)
    #print( data )
    temp_var=np.frombuffer(data,dtype=np.uint32)[0]
    #print( "0xE for upper 4 bits: ", hex(temp_var>>28) )
    #print("Number of samples", temp_var&0x3FFFFFF)
    num_samples=temp_var&0x3FFFFFF
      # Handle edge case of odd num_samples (round up to nearest even number)
    num_samples_rounded = num_samples + num_samples % 2
    sum_=0
    rawWave = []
    print('num_samples = ',num_samples)
    for i in range(0,int(num_samples/2.)):
        sum_+=2

        # Read binary data from file
        data=handle.read(2 * num_samples_rounded)
        # Parse binary data into numpy array
        rawWave = np.frombuffer(data, dtype=np.uint32)
        # Slice off extra binary data if necessary (assuming padded at the END)
        rawWave = rawWave[:num_samples]
        #print(rawWave)
        #words = struct.unpack("<HH",data)
        #print("words = ",words)

    #    if len(data) == 4: #and words[0] == '':
    #        try:
                #parseData = [int('0' + words[i],16) for i in range(len(words)) if words[i] != '' and i%2!=0]
    #            parseData = list(words)
    #            print(parseData)
        #arr[index] for index in range(len(arr)) if index % 2 == 0
                #print("parseData = ", parseData)
        #rawWave += [i for i in parseData if i != 3]
    #            rawWave += parseData
                #print("rawWave = ",rawWave)
    #        except:
    #            pass
        #fmt = '<I'
        #print("Length of data is %d bytes"%len(data))
        #print("Data can fit into 1 int, or 2 short ints, or 4 characters")

        #print("As an integer: %d"%struct.unpack("<I",data))
        #print("As two short ints: ", struct.unpack("<HH",data))
        #print("As four characters:",struct.unpack("<cccc",data))
        #parsed_int = struct.unpack(fmt,data)
        #print('parsed_int = ',parsed_int)
    #print("Number of samples read: ",sum_)
    if len(rawWave) == sum_:
        rawData += [np.array(rawWave)]
        print('rawData =',len(rawData))

#From Ryan:
#        fmt='<I' # little endian implied by < and unsigned int implied by I
#        parsed_int=struct.unpack(fmt,data)
#        print('parsed_int = ',parsed_int)
    handle.read(4) # MAW Test Data
    handle.read(8) # 8 bytes that aren't documented
    #print( handle.tell() )
    lineNum += 1
    if lineNum%100000 == 0:
        print('lines read = ', lineNum)
        print('time elapsed = ',time.time()-tic)


#    data=handle.read(4)
#    print(data)
#    format_bits=np.frombuffer(data,dtype=np.uint32)[0]
#    print(bin(format_bits))
#    for i in range(0,4):
#        print( "format_bit%d"%i, format_bits>>i&(0x1))
