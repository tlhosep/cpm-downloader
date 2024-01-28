"""
**Utility collection**

Content
#######
This module contains some utility functions for convenience

Info
####
* **author:** (c) Thomas Lüth 2024
* **email:** info@tlc-it-consulting.com
* **created:** 2024-01-25

Code
####
"""
import argparse
from subprocess import run

def get_git_version():
    '''
    retrieve the current git provided version, based on the latest tag
    :returns: Version as string, eg. 0.1.0-97-g1d18af9 or empty in case of error
    '''
    completed_process=run(['git','--no-pager', 'describe', '--tags', '--always'],
            capture_output=True, check=False)
    if completed_process.returncode != 0:
        return ""
    return completed_process.stdout.decode('utf-8')

def add_parser_log_args(parser,default_loglevel=20):
    """Add commandline parsing arguments for logging

    Args:
        parser ( argparse.ArgumentParser): The parser class to be defined
    """
    parser.add_argument('--use_logfile', help=
                        "Logs various messages into logfile and messages on screen",
                        required=False, action='store_true')
    parser.add_argument('--loglevel', help="Define the logging level, the higher the less",
                        type=int, choices=[0,10,20,30,40,50], default=default_loglevel)
    parser.add_argument('--version', help="Returns current git version and terminates",
                        required=False, action='store_true')

def cmdline_main(cmd):
    """Main function content for a commandline handling app

    Args:
        cmd (class): Command-class that processes the parameter provided and runs the app
    """
    # Define parser and determine help
    parser = argparse.ArgumentParser(description=cmd.help)

    # Add now commandline args to be checked
    cmd.add_arguments(parser)
    options = parser.parse_args()
    cmd_options = vars(options)
    # Move positional args out of options to mimic legacy optparse
    args = cmd_options.pop('args', ())
    cmd.handle(*args,**cmd_options)

def configure_logging(use_logfile,logging,log_file,log_level):
    """Configue logging for a logfile and console or console

    Args:
        use_logfile (Bool): If true write a logfile
        logging (Logger): Logger for the app = logging.getLogger(__name__)
        log_file (str): full path and logfilename
        log_level (int): log level the higher the more severe
    """
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
 