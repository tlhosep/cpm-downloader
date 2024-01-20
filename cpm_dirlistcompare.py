#!/usr/bin/python3
'''
The CP/M dir list compare is an application to compare two directory lists provided via parameter.
Lists have been generated on CP/M level with the command
put console file list.lst
dir [drive=(f.g,h),NOOAGE,FULL,USER=ALL]

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


Created on 19.01.2024

@author: th.lueth@tlc-it-consulting.com
'''
import os
import logging
import argparse
import serial
import playsound
import sys
import re
from subprocess import run
from pathlib import Path


logger = logging.getLogger(__name__)

class DirFileState:
    def __init__(self, action):
        self.action = action
    def __str__(self): return self.action
     # in order to make this class usable as a
    # dictionary key:
    def __hash__(self):
        return hash(self.action)


class Command():
    """
    Commandline interface for the main app

    """
    help = "Compares 2 files with CP/M structure dir-listings and looks for differences"
    @staticmethod
    def add_arguments(parser):
        '''
        Add the commandline arguments that will be executed

        :param parser: commandline parser
        '''
        parser.add_argument('--loglevel', help="Define the logging level, the higher the less", 
                            type=int, choices=[0,10,20,30,40,50], default=20)
        parser.add_argument('--version', help="Returns current git version and terminates",
                            required=False, action='store_true')
        parser.add_argument('--use_logfile', help=
                            "Logs various messages into logfile and messages on screen",
                            required=False, action='store_true')
        parser.add_argument('--file1', help="First file to compare", default="",
                            required=True, action='store')
        parser.add_argument('--file2', help="Second file to compare", default="",
                            required=True, action='store')
    @staticmethod 
    def extract_file(filename, indicator=None):
        """Extract the dir-entries from given file

        Args:
            filename (String): full filename with path from file to analyze
            indicator (String): File 1 or 2 or None

        Returns:
            list: List of filenames; <Drive><User>_<filename>_<Indicator for File>
        """        
        DirFileState.start=DirFileState("start")
        dir_string_regex=re.compile("Directory For Drive (\S):  User \s+(\d)")
        DirFileState.dirheader=DirFileState("header")
        dir_list_start="------------ ------ ------"
        DirFileState.dirlist=DirFileState("dirlist")
        "ALLFILES LST     0k      0 Dir RW       CCP      COM     4k     25 Sys RW      "
        # 1=fil, 2=filsub, 3=sizek, 4= blocks, 5=attrs (12 char)
        dir_list_files_regex=re.compile("((\S+)\s+(\S+)\s+(\d+)k\s+(\d+) (.{12})\s*)")
        empty_line_regex=re.compile("^\s*$")
        filelist=[]
        try:
            state=DirFileState.start
            with open(filename,"r") as f1:
                while True: 
                    line=f1.readline()
                    if len(line)==0:
                        #end of file indicator
                        break
                    if empty_line_regex.match(line):
                        #skip empty lines
                        continue
                    if state==DirFileState.start:
                        matches=dir_string_regex.match(line)
                        if matches==None:
                            continue #read next line
                        drive=matches.group(1)
                        user=f'{int(matches.group(2)):02d}'
                        state=DirFileState.dirheader
                        continue
                    if state==DirFileState.dirheader:
                        if line.startswith(dir_list_start):
                            state=DirFileState.dirlist
                            continue
                    if state==DirFileState.dirlist:
                        matches=dir_list_files_regex.findall(line)
                        if len(matches)==0:
                            #end of list reached
                            state=DirFileState.start
                            continue
                        else:
                            for ngroup in range(len(matches)):
                                dirfilename=drive+str(user)+"_"+matches[ngroup][1]+"."+matches[ngroup][2]
                                if indicator is not None:
                                    dirfilename=dirfilename+"_"+indicator
                                filelist.append(dirfilename)
                    
        except (OSError, IOError) as err:
            logger.exception("I am sorry to inform you that the file could not be opened, cause: "+str(err))
            return None
        return filelist

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
        if options['version']:
            print("The current version is: "+Command.get_git_version())
            return
        log_level=options['loglevel']
        filename1=options['file1']
        filename2=options['file2']
        current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        log_file=os.path.join(current_path,"log","cpm_downloader.log")
        file1=os.path.join(current_path,filename1)
        file2=os.path.join(current_path,filename2)
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
        filelist1=Command.extract_file(file1)
        filelist2=Command.extract_file(file2)
        targetlist=[]
        #next check filelist2 for missing entries and report them
        for filename in filelist1:
            if filename not in filelist2:
                if filename[0:3] not in ["F02","F04","F06","F07","F08","F09","F11","F13","F14",
                                        "F15","G07","G08","G09","G10","G11","H01","H03","H04","H07"] and \
                    filename[-3:] != "BAK":
                   targetlist.append(filename) 

        print("\nResults\n")
        for name in targetlist:
            print(name)
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
