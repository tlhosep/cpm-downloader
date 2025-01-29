# cpm downloader

## Background (why I needed this tool)
Back in the 80ies I bought a CP/M system (PROF80) and added certain hardware and finally also a harddisc (20MB, very expensive). Now after more than 40 years I pulled the old system out of the rack and started it. OK, system clock did no longer work (battery wass off duty) but it booted :) Lucky me.
Out of historic reasons I wanted to backup the contained data from the system...

But the system lacked any valid interfaces like USB... 

The only interfaces to export old data from the harddisc were Floppy-drives that worked in a way, but not optimal and 5,25" discs are hard to read, the 3,5" floppy did not work for unknown reasons... 

But nevertheless the system had an **serial adapter** with 25 pins. This adapter still worked, at least it was able to send data. Receiving data was a bit too much as I had to use the adapter that used CPU wait cycles to interpret the incoming data. The interfaces connected to some better working SIO hardware could not establish a connection as the baudrates were weird :( 

Thus I ended in the situation that the only way is to push forward the data over the serial line from the CP/M system to my Mac...

Thats where the whole story started. Please read ahead if you might face a similar problem with old systems...

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
pip3 install pyObjC
```
If not, the sound could not be played...

The module is no longer part of the requirements.txt as that hinders the build pipeline from working.

## Protocol
The format to be send over the line from CP/M to MAC:

```
<Bytes….>
>>>+++STOP+++<<<
Filename | quit | #_<folder>
<<<+++GO+++>>>
<Bytes…>
```

## Server (CP/M)
### Prepare
Setup files (using wordstar or any other editor) with these contents:

|Filename|Content|
|--------|-------|
|STOP.SEP|>>>+++STOP+++<<<|
|GO.SEP|<<<+++GO+++>>>|

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

## Finally
Have fun :)