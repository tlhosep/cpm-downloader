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
import time
import traceback
import argparse
import serial
import playsound


logger = logging.getLogger(__name__)


class Command():
    """
    Commandline interface for the main app

    """
    help = "Runs CP/M downloader app at 9600 Baud on /dev/cu.usbserial-143230 with log-level 20"
    @staticmethod
    def add_arguments(parser):
        '''
        Add the commandline arguments that will be executed

        :param parser: commandline parser
        '''
        parser.add_argument('--baud', help="Set the baudrate", type=int,choices=[300,600,1200,2400,4800,9600,19200],
                            required=False, action='store', default=9600)
        parser.add_argument('--loglevel', help="Define the logging level, the higher the less", 
                            type=int, choices=[0,10,20,30,40,50], default=20)
        parser.add_argument('--version', help="Returns current git version and terminates",
                            required=False, action='store_true')
        parser.add_argument('--use_logfile', help=
                            "Logs various messages into logfile and messages on screen",
                            required=False, action='store_true')
        parser.add_argument('--device', help="Serial device", default="/dev/cu.usbserial-143230",
                            required=False, action='store')
 
    @staticmethod
    def handle(*args, **options):  # @UnusedVariable pylint: disable=unused-argument
        """
        Main loop to process the commandline

        """
      
        if options['version']:
            #print(_("The current version is")+": "+Settings.get_git_version())
            return
        #: Location for logfiles
        log_file="./log/cpm_ldownloader.log"
        log_level=options['loglevel']
        ser_device=options['device']
        ser_baud=options['baud']
        stop_sep=b'>>>+++STOP+++<<<'
        go_sep=b'<<<+++GO+++>>>'
        quit_=b'quit'

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
        logger.info("Connecting to the serial port "+ser_device)
        try:
            with serial.Serial(ser_device, ser_baud, rtscts=1) as ser:
                if ser.is_open:
                    logger.info("Serial line now open to accept reuests")
                logger.info("Application now in endless loop")
                go=False
                while go:
                    ser_content=ser.read_until(stop_sep)
                    ser_filename=ser.read_until(go_sep)
                    ser_filename=ser_filename[:-1] #cut last char as that would be ^Z
                    if ser_filename == quit:
                        go=False
                        break
                    try:
                        with open(ser_filename,'wb') as bin_file:
                            bin_file.write(ser_content)
                        logger.info("Bytes now written to: "+ser_filename)
                        playsound.playsound('./tones/ok.mp3')

                    except (IOError, OSError) as ferr:
                        logger.exception("file could not be written: "+str(ferr))
                        playsound.playsound('./tones/fail.mp3')                      
    
        except (ValueError, serial.SerialException) as err:
            logger.exception("I am sorry to inform you that the serial line could not be opened, cause: "+str(err))
            playsound.playsound('./tones/fail.mp3')
 
        logger.info("Application terminated now")

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
