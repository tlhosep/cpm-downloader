#!/usr/bin/python3
'''
The CP/M downloader is an application to simple do what the name would expect:
    - open a receiving serial connetion on any PC
    - receive a binary information provided by the CP/M pip command, could be a file
    - Wait for a specific string to check the filename the file has to be stored
    - store the file
    - continue with the next file or quit

Created on 12.01.2024

@author: th.lueth@tlc-it-consulting.com
'''
import os
import logging
import argparse
import serial
import playsound
import sys
from subprocess import run
from pathlib import Path


logger = logging.getLogger(__name__)


class Command():
    """
    Commandline interface for the main app

    """
    help = "Runs CP/M downloader app at 19200 Baud on /dev/cu.usbserial-143230 with log-level 20"
    @staticmethod
    def add_arguments(parser):
        '''
        Add the commandline arguments that will be executed

        :param parser: commandline parser
        '''
        parser.add_argument('--baud', help="Set the baudrate", type=int,choices=[300,600,1200,2400,4800,9600,19200],
                            required=False, action='store', default=19200)
        parser.add_argument('--loglevel', help="Define the logging level, the higher the less", 
                            type=int, choices=[0,10,20,30,40,50], default=20)
        parser.add_argument('--version', help="Returns current git version and terminates",
                            required=False, action='store_true')
        parser.add_argument('--use_logfile', help=
                            "Logs various messages into logfile and messages on screen",
                            required=False, action='store_true')
        parser.add_argument('--device', help="Serial device", default="/dev/cu.usbserial-143230",
                            required=False, action='store')
        parser.add_argument('--path', help="Output path", default=".",
                            required=False, action='store')
 
    @staticmethod
    def get_git_version():
        '''
        retrieve the current git provided version, based on the latest tag
        :returns: Version as string, eg. 0.1.0-97-g1d18af9 or empty in case of error
        '''
        completed_process=run(['git','--no-pager', 'describe', '--tags', '--always'],
               capture_output=True)
        if completed_process.returncode != 0:
            return ""
        return completed_process.stdout.decode('utf-8')

    @staticmethod
    def handle(*args, **options):  # @UnusedVariable pylint: disable=unused-argument
        """
        Main loop to process the commandline

        """
        fail_sound=None      
        if options['version']:
            print("The current version is: "+Command.get_git_version())
            return
        
        #: Location for logfiles
        
        log_level=options['loglevel']
        ser_device=options['device']
        ser_baud=options['baud']
        file_path=options['path']
        try:
            Path(file_path).mkdir(parents=True, exist_ok=True)
        except Exception as err:
            logger.exception("path " +file_path+" could not be made: "+str(err))
            return

        current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        stop_sep=b'>>>+++STOP+++<<<'
        go_sep=b'<<<+++GO+++>>>'
        quit_cmd='quit'
        subfolder_cmd='#_'
        ok_sound=os.path.join(current_path,'tones','ok.mp3')
        fail_sound=os.path.join(current_path,'tones','fail.mp3')
        log_file=os.path.join(current_path,"log","cpm_downloader.log")

        use_logfile=options['use_logfile']
        if use_logfile:
            #define filehandler first
            logging.basicConfig(filename=log_file, level=log_level,
                                format='%(asctime)s;%(filename)-16.16s;%(lineno)04d;'+\
                                '%(levelname)-8s;%(message)s'
                                )
            # define a Handler which writes INFO messages or higher to the sys.stderr
            console = logging.StreamHandler()
             # set a format which is simpler for console use
            formatter = logging.Formatter('%(levelname)-8s %(message)s')
            # tell the handler to use this format
            console.setFormatter(formatter)
            # add the handler to the root logger
            logging.getLogger().addHandler(console)
        else:
            #log to console only
            logging.basicConfig(level=log_level,
                                format='%(asctime)s;%(filename)-16.16s;%(lineno)04d;'+\
                                '%(levelname)-8s;%(message)s'
                                )
        logger.info("Starting the app now")
        logger.info("Logging to"+": "+str(log_file)+" "+"at level"+": "+str(log_level))
        logger.info("File storage: "+file_path)
        logger.info("Connecting to the serial port "+ser_device)
        try:
            with serial.Serial(ser_device, ser_baud, rtscts=1) as ser:
                if ser.is_open:
                    logger.info("Serial line now open to accept reuests")
                logger.info("Application now in endless loop")
                subfolder=file_path
                while True:
                    ser_content=ser.read_until(stop_sep)
                    ser_content=ser_content[:-len(stop_sep)]
                    ser_filename=ser.read_until(go_sep)
                    ser_filename=ser_filename[:-len(go_sep)].decode('ascii').lower().strip() #cut seperator
                    if ser_filename == quit_cmd:
                        break
                    if ser_filename[0:2] == subfolder_cmd:
                        subfoldername=ser_filename[2:].strip()
                        subfolder=os.path.join(file_path,subfoldername)
                        Path(subfolder).mkdir(parents=True, exist_ok=True)
                        logger.info("Path has been set to "+subfolder)
                        continue
                    try:
                        ser_filename=ser_filename
                        ser_path=os.path.join(subfolder,ser_filename)
                        with open(ser_path,'wb') as bin_file:
                            bin_file.write(ser_content)
                        logger.info(str(len(ser_content))+" Bytes now written to: "+ser_filename+" onfolder "+subfolder)
                        #playsound.playsound(ok_sound)

                    except (IOError, OSError) as ferr:
                        logger.exception("file " +ser_path+" could not be written: "+str(ferr))
                        playsound.playsound(fail_sound)
                        break              
    
        except (ValueError, serial.SerialException, IOError) as err:
            logger.exception("I am sorry to inform you that the serial line could not be opened, cause: "+str(err))
            playsound.playsound(fail_sound)
            return
 
        logger.info("Application terminated now")
        playsound.playsound(ok_sound)
def main():
    '''
    Main function executed when the python script will be called

    '''
    cmd = Command()
    # Define parser and determine help
    parser = argparse.ArgumentParser(description=cmd.help)

    # Add now commandline args to be checked
    cmd.add_arguments(parser)
    options = parser.parse_args()
    cmd_options = vars(options)
    # Move positional args out of options to mimic legacy optparse
    args = cmd_options.pop('args', ())
    cmd.handle(*args,**cmd_options)

if __name__ == "__main__":
    main()
