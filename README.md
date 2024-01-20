# cpm downloader

## Purpose
The tool is needed when there is no real application on the other end to care about a real protocol like Kermit.
The tool is also needed when the ability to transfer data to the other PC is somehow limited due to the serial line not fully working
in order to accept bytes from the serial interface due to missing Interrupts etc.

To transfer files from the other PC back to here needs only a serial line connected via crossed null modem cable and
the ability to setup an aux interface to transfer some data over it. Something like this:

```
TxD pin	2  -------\/----------- pin 2 TxD
RxD pin	3  -------/\----------- pin 3 RxD
GND pin	7  -------------------- pin 7 GND
DTR pin	20 ----|         |----- pin 20 DTR
DSR pin	6  ----|         |----- pin 6 DSR
RTS pin	4  -|  |         |   |- pin 4 RTS
CTS pin	5  -|  |         |   |- pin 5 CTS
DCD pin	8  ----|         |----- pin 8 DCD
```
Or better with crossed rts/cts for a hardware protocol like this (RTS/CTS enabled by default):
```
TxD pin	2  -------\/----------- pin 2 TxD
RxD pin	3  -------/\----------- pin 3 RxD
GND pin	7  -------------------- pin 7 GND
DTR pin	20 ----|         |----- pin 20 DTR
DSR pin	6  ----|         |----- pin 6 DSR
RTS pin	4  ----|--\/-----|----- pin 4 RTS
CTS pin	5  ----|--/\-----|----- pin 5 CTS
DCD pin	8  ----|         |----- pin 8 DCD
```


## MacOS
If you try to run the app on MacOs, the following library has to be installed:
```
pip3 install pyObjC`
```
If not, the sound could not be played...

The module is no longer part of the requirements.txt as that hinders the build pipeline from working.

## Protocol
The format to be send over the line:

```
<Bytes….>
>>>+++STOP+++<<<
Filename | quit | #_<folder>
<<<+++GO+++>>>
<Bytes…>
```

## Server (CP/M)
### Prepare
Setup files using workstation or any other editor with these contents:

```
Filename	Content
Stop.sep	>>>+++STOP+++<<<
Go.sep	<<<+++GO+++>>>
```
Prepare the aux device to use 9600, 8N1 as the default setup

### Manual sequence
Then on the server issue these commands:

```
pip aux:=<filename.ext>[O]
pip aux:=Stop.sep[U0R]
pip aux:=con:
pip aux:=go.sep[U0R]
```

### Stop the transfer
In order to stop the transfer just pip the stop.sep twice and then enter quit (lowercase) ^Z followed by

```
pip aux:=go.sep
```

### Change to subdirectory
```
>>>+++STOP+++<<<
#_G01
<<<+++GO+++>>>
<Bytes…>
```
This sequence will generate the subfolder G01 and use this for subsequent file-storages

### Automated approach using Sub
write this script on CP/M end: and call it trans.sub

```
pip aux:=$1[O],STOP.SEP
pip aux:=con:
pip aux:=GO.SEP
```

## Client
On client end we have to implement a small python application to read the byes from the provided serial port until the stop sequence could be found.

* If found, read the filename or quit command while waiting for the go separator. We will also check for the command to change the subdirectory
* If quit had been detected, discard the buffer, close the line and return to the comandline
* If a command to create a subdirectory had been found, create it and use this to store the files
* If a filename had been detected: Write the buffer into the to be created filename. If the file already exists issue an error and discard the buffer.

# CP/M directory listing comparer
cpm_dirlistcompare.py

Compare 2 files, generated via 

```
put console file list.lst
dir [drive=(f,g,h),NOOAGE,FULL,USER=ALL]

The structure of the file has to look like this:

Scanning Directory...

Sorting  Directory...

Directory For Drive F:  User  0

    Name     Bytes   Recs   Attributes      Name     Bytes   Recs   Attributes 
------------ ------ ------ ------------ ------------ ------ ------ ------------
ALLFILES LST     0k      0 Dir RW       CCP      COM     4k     25 Sys RW      

Total Bytes     =    540k  Total Records =    3104  Files Found =   63
Total 1k Blocks =    421   Used/Max Dir Entries For Drive F:  583/2048


Directory For Drive F:  User  1

```
And list all files not contained in file 2 in the following way:

```
 H02_CCPZ802.REL

 <Drive-Letter><User>_<file>.<extension>
```
Major command-line parameter:
```
 --file1 <Full path to file> --file2 <Full path to file>
```