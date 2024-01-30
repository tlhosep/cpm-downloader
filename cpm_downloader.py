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
import sys
import logging
from pathlib import Path
import serial
import playsound
from tlu_utils import get_git_version,add_parser_log_args,cmdline_main,configure_logging

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
        add_parser_log_args(parser)
        parser.add_argument('--baud', help="Set the baudrate", type=int,
                            choices=[300,600,1200,2400,4800,9600,19200],
                            required=False, action='store', default=19200)
        parser.add_argument('--device', help="Serial device", default="/dev/cu.usbserial-143230",
                            required=False, action='store')
        parser.add_argument('--path', help="Output path", default=".",
                            required=False, action='store')


    @staticmethod
    def handle(*args, **options):
        # @UnusedVariable pylint: disable=unused-argument, too-many-locals, too-many-statements
        """
        Main loop to process the commandline

        """
        fail_sound=None
        if options['version']:
            print("The current version is: "+get_git_version())
            return

        #: Location for logfiles
        log_level=options['loglevel']
        ser_device=options['device']
        ser_baud=options['baud']
        file_path=options['path']
        try:
            Path(file_path).mkdir(parents=True, exist_ok=True)
        except OSError as err:
            logger.exception("path %s could not be made: %s",file_path,str(err))
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
        configure_logging(use_logfile,logging, log_file, log_level)
        logger.info("Starting the app now")
        logger.info("Logging to:%s  at level: %s",str(log_file),str(log_level))
        logger.info("File storage: %s",file_path)
        logger.info("Connecting to the serial port %s",ser_device)
        try:
            with serial.Serial(ser_device, ser_baud, rtscts=1) as ser:
                if ser.is_open:
                    logger.info("Serial line now open to accept requests")
                else:
                    logger.error("serial line could not be opened")
                    playsound.playsound(fail_sound)
                    return
                logger.info("Application now in endless loop")
                subfolder=file_path
                while True:
                    ser_content=ser.read_until(stop_sep)
                    ser_content=ser_content[:-len(stop_sep)]
                    ser_filename=ser.read_until(go_sep)
                    ser_filename=ser_filename[:-len(go_sep)].decode('ascii').\
                        lower().strip() #cut seperator
                    if ser_filename == quit_cmd:
                        break
                    if ser_filename[0:2] == subfolder_cmd:
                        subfoldername=ser_filename[2:].strip()
                        subfolder=os.path.join(file_path,subfoldername)
                        Path(subfolder).mkdir(parents=True, exist_ok=True)
                        logger.info("Path has been set to %s",subfolder)
                        continue
                    try:
                        ser_path=os.path.join(subfolder,ser_filename)
                        with open(ser_path,'wb') as bin_file:
                            bin_file.write(ser_content)
                        logger.info(str(len(ser_content))+" Bytes now written to: "+\
                            ser_filename+" onfolder "+subfolder)
                        #playsound.playsound(ok_sound)

                    except (IOError, OSError, TypeError) as ferr:
                        logger.exception("file %s could not be written: %s",ser_path,str(ferr))
                        playsound.playsound(fail_sound)
                        break

        except (ValueError, serial.SerialException, IOError) as err:
            logger.exception("I am sorry to inform you that the serial line could not be opened,"\
                " cause: %s",str(err))
            playsound.playsound(fail_sound)
            return

        logger.info("Application terminated now")
        playsound.playsound(ok_sound)
def main():
    '''
    Main function executed when the python script will be called

    '''
    cmd = Command()
    cmdline_main(cmd)

if __name__ == "__main__": # pragma: no cover
    main()
