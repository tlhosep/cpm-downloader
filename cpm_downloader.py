#!/usr/bin/python3
'''
E-paper application to use a waveshare epaper display for various information screens like
    - home (basic infos)
    - news
    - weather (currently supporting homematic only)
    - homematic (typical settings like doors open, temp, rain etc)
    - menu (intermediate menu screen to get to a new level and to provide structure)

Created on 16.04.2021

@author: th.lueth@tlc-it-consulting.com
'''
import os
import logging
from subprocess import check_call
import time
import traceback
from time import sleep
import sys
import signal
import locale
import argparse
import threading
import gettext
import schedule
from tlu_services.tlu_homematic import start_homematic, homematic_working,\
    stop_homematic
from tlu_services.tlu_local_settings import Settings #get_git_version, MYBASE_DIR, LOCALE_DIR
from tlu_services.tlu_epd_module import EpdSupport, FAKE_IO
from tlu_services.tlu_threads import start_thread, abort_thread
from tlu_pages.tlu_screen_type import ScreenType
from tlu_pages.tlu_screen_factory import ScreenFactory

#: global vars
#: Settings structure read from file or using defaults
MY_SETTINGS=None
##: holds Thread that is updating the screen in intervals like 180 seconds
REFRESH_THREAD=None
#: Indicates that a screen-refresh is currenty in action, so no new refresh could take place
REFRESH_IN_ACTION=False
#: Another thread that tries to put the device into sleep at a certain time and awakens it,
#: when time is up
CONTINUOUS_THREAD=None
#: Interval to refresh the screen in seconds
REFRESH_INTERVALL=60
#: epd-support, contains buttons, epd and gpio
EPD_SUPPORT=None
#: Sxcheduler for sleep and awake-cycle
STOP_SCHEDULER=None
#: Define MESSAGE log level to replace print()
MESSAGE = 25


class MyLogger(logging.Logger):
    '''
    Logger-Class to support new level "MESSAGE" which is 25

    '''
    def message(self, msg, *args, **kwargs):
        '''
        Additional message-class to support MESSAGE
        :param msg:
        '''
        if self.isEnabledFor(MESSAGE):
            self._log(MESSAGE, msg, args, **kwargs)

logging.setLoggerClass(MyLogger)

logger = logging.getLogger(__name__)


# Set up translation
_ = gettext.gettext
gettext.bindtextdomain('epaper', Settings.LOCALE_DIR)
gettext.textdomain('epaper')


def init_buttons():
    '''
    Setup the reactions for the 4 buttons on the device:
        - Button on top is pin 5, followed by 6, 13 and 19
        - All are saved as buttons to global btn1..4
        - btn1..4 call handle_button for action

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    # Define the buttons
    EPD_SUPPORT.button1.when_pressed=handle_button
    EPD_SUPPORT.button2.when_pressed=handle_button
    EPD_SUPPORT.button3.when_pressed=handle_button
    EPD_SUPPORT.button4.when_pressed=handle_button
    logger.debug("Buttons initialized")

def handle_button(btn):
    '''
    Handling of the event that a button had been pressed
    If a refresh is currently going on: ignore the event

    :param btn: button class that caused the event
    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    global MY_SETTINGS  #pylint: disable=global-statement
    global REFRESH_IN_ACTION #pylint: disable=global-statement

    if REFRESH_IN_ACTION:
        logger.warning('There is an refresh running, button ignored')
        return
    next_page_name=EPD_SUPPORT.get_pagename_by_button(btn)
    logger.info('Button pressed and page found: '+next_page_name)  # pylint: disable=logging-not-lazy
    if len(next_page_name) < 1:
        logger.critical('A button pressed but no page name found')
        return #do nothing
    homematic=start_homematic(MY_SETTINGS,EPD_SUPPORT)
    if next_page_name.isdecimal():
        #potential homematic function
        if homematic is not None:
            button_structure=EPD_SUPPORT.get_settings_by_button(btn)
            hm_settings=button_structure.get('homematic',{})
            if len(hm_settings)>1:
                homematic.execute_program(hm_settings)
                return
    screen_type=ScreenType()
    next_page_type=screen_type.get_type(next_page_name)
    if next_page_type==ScreenType.ACTION_TYPE:
        if next_page_name==ScreenType.MENU_EXIT:
            exit_app()
        elif next_page_name==ScreenType.MENU_HALT:
            shutdown()
        elif next_page_name==ScreenType.MENU_EMPTY:
            return
    if next_page_type==ScreenType.FIXED_ACTION_TYPE:
        if next_page_name==ScreenType.MENU_SLEEP:
            soft_sleep_epd(EPD_SUPPORT,MY_SETTINGS)
        elif next_page_name==ScreenType.MENU_WAKEUP:
            soft_awake_epd()
        elif next_page_name==ScreenType.MENU_HOME:
            next_page_name=EPD_SUPPORT.screen_factory.get_home_screen_id()
            EPD_SUPPORT.set_current_page(next_page_name)
            show() #show new image
        return
    EPD_SUPPORT.set_current_page(next_page_name)
    show() #show new image

def init_epd(screenname="HOM"):
    '''
    Initialize the epd and show the given screen

    :param screenname: screen to show (technical name of the screen)
    :returns: True if OK, else False

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    EPD_SUPPORT.initial_epd_start()
    return EPD_SUPPORT.set_current_page(screenname)

def sleep_epd(clear=True,hardend=False):
    '''
    Putting the epd into sleep mode:
        - abort refresh thread
        - if clear: Clear the screen
        - if hardend: resetting GPIO

    :param clear: True: show white screen
    :param hardend: True: Close GPIO

    '''
    global REFRESH_THREAD #pylint: disable=global-statement
    global REFRESH_IN_ACTION #pylint: disable=global-statement
    global EPD_SUPPORT  #pylint: disable=global-statement
    logger.message(_("Going to sleep"))
    logger.info("EPD Sleep requested")
    abort_thread(REFRESH_THREAD,5)
    REFRESH_THREAD=None
    while REFRESH_IN_ACTION:
        sleep(1)
    if clear:
        logger.message(_("Clearing the screen"))
        logger.debug("EPD will be cleared")
        EPD_SUPPORT.epd.init(False) #no hard init and not 4 gray-mode!
        EPD_SUPPORT.epd.Clear(0xFF)

    EPD_SUPPORT.epd.sleep(hardend)
    logger.message(_("Sleeping now"))
    logger.debug("EPD now sleeping")

def soft_sleep_epd(epd_support, settings):
    '''
    Disable homematic and show refresh page.
    No additional traffic is generated

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    global MY_SETTINGS  #pylint: disable=global-statement
    stop_homematic(MY_SETTINGS,EPD_SUPPORT)
    EPD_SUPPORT.set_current_page(ScreenType.MENU_SLEEP)
    show()

def soft_awake_epd():
    '''
    Enable homematic and show home-page

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    global MY_SETTINGS  #pylint: disable=global-statement
    start_homematic(MY_SETTINGS,EPD_SUPPORT)
    EPD_SUPPORT.set_current_page(ScreenType.MENU_HOME)
    show()

def exit_app():
    '''
    Command to just exit the application:
        - clear the screen
        - stop buttons
        - stop threads
        - send signal to exit

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    global MY_SETTINGS  #pylint: disable=global-statement
    stop_homematic(MY_SETTINGS,EPD_SUPPORT)
    sleep_epd(True,True)
    EPD_SUPPORT.close_buttons()
    EPD_SUPPORT.gpio.cleanup()
    logger.message(_("Now signalling the end"))
    logger.info("SIGNAL 1 send to terminate pause and the application")
    os.kill(os.getpid(), signal.SIGUSR1)

def shutdown():
    '''
    Shutdown the application

    use sudo poweroff

    '''
    global EPD_SUPPORT  #pylint: disable=global-statement
    sleep_epd(True,False) #only epaper cleanup
    #putting raspi to bed
    logger.fatal("Shutting down upon request")
    logger.info("sudo poweroff tried...")
    if not FAKE_IO:
        check_call(['sudo', 'poweroff'])

    #Finally kill the pause
    logger.message(_("Now signalling the end"))
    logger.info("SIGNAL 1 send to terminate pause and the application")
    os.kill(os.getpid(), signal.SIGUSR1)

def check_current_page(check_time,next_time):
    '''
    Check if current page has to be changed according to the
    menu definitions for a specific day of week and time

    :param check_time: current time
    :param next_time: next planned time when the page shall refresh on the screen

    '''
    global EPD_SUPPORT #pylint: disable=global-statement
    assert check_time is not None and isinstance(check_time, float)
    assert next_time is not None and isinstance(next_time, float)

    current_page_id=EPD_SUPPORT.get_current_page_technical_name()
    new_page_id=EPD_SUPPORT.screen_factory.get_screen_for_time_span(check_time, next_time)
    if len(new_page_id) > 0 and new_page_id != current_page_id:
        EPD_SUPPORT.set_current_page(new_page_id)

def every(delay, task):
    '''
    Method to be called by REFRESH_THREAD

    :param delay: pause between two subsequent calls of...
    :param task: Task to be executed when time is up

    '''
    global REFRESH_THREAD #pylint: disable=global-statement
    mydelay=delay
    if mydelay is None or mydelay<30:
        logger.error("given delay is beyond lower limit: "+str(mydelay))  #pylint: disable=logging-not-lazy
        mydelay=30 #minimum refresh-cycle
    next_time = time.time() + mydelay
    while True:
        #calculate the seconds to wait, min 1 second to avoid exceptions
        seconds2wait=max(1, int(next_time - time.time()))
        logger.message("Seconds:"+str(seconds2wait))
        current_time=time.time()
        check_current_page(current_time,next_time)
        for _ in range(seconds2wait):  # @UnusedVariable
            if getattr(REFRESH_THREAD, "is_aborted", False):
                return
            time.sleep(1)
        try:
            task()
            time.sleep(1)
        except Exception as err:  #pylint: disable=broad-except
            traceback.print_exc()
            logger.exception("Problem while executing repetitive task: "+str(err))  #pylint: disable=logging-not-lazy

        # skip tasks if we are behind schedule:
        new_delay=((time.time() - next_time) % mydelay)
        new_delay=max(1,mydelay-new_delay) #stay positive
        next_time = time.time() + new_delay           
        #next_time += (((time.time() - next_time) // mydelay) * mydelay) + mydelay

def show():
    '''
    Main method to show content given by currentpage

    Is not going to show anything if a refresh is currently being performed

    '''
    global EPD_SUPPORT #pylint: disable=global-statement
    global REFRESH_IN_ACTION #pylint: disable=global-statement

    if REFRESH_IN_ACTION:
        logger.error(_("Refresh running too long"))
        return

    try:
        logger.message(_("Build image")+": "+EPD_SUPPORT.current_page.name())
        REFRESH_IN_ACTION=True
        EPD_SUPPORT.show_current_page()
    except Exception as err:  #pylint: disable=broad-except
        traceback.print_exc()
        logger.exception("Problem while executing repetitive task: "+str(err))  #pylint: disable=logging-not-lazy
        EPD_SUPPORT.set_current_page(ScreenType.MENU_ERROR)
        logger.message(_("Build image")+": "+EPD_SUPPORT.current_page.name())
        REFRESH_IN_ACTION=True
        EPD_SUPPORT.show_current_page()

    finally:
        REFRESH_IN_ACTION=False

def run_schedule(interval=1):
    """
    This method is going to handle the sleep and wakeup settings.

    Continuously run, while executing pending jobs at each
    elapsed time interval.

    Please note that it is intended behavior that run_schedule()
    does not run missed jobs.
    For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.

    :param interval: Seconds between checks to wait
    :returns: cease_continuous_run: threading. Event which can
        be set to cease continuous run.

    """
    global CONTINUOUS_THREAD  #pylint: disable=global-statement
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        '''
        Internal method to check for events that should be processed
        '''
        @staticmethod
        def run():
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    CONTINUOUS_THREAD = ScheduleThread()
    CONTINUOUS_THREAD.start()
    return cease_continuous_run

def handle_exit_sig(exitsignal, codeframe):  # @UnusedVariable pylint: disable=unused-argument
    '''
    Handler if a specific system-signal occured

    :param exitsignal: Signal received
    :param codeframe: indicator where the signal was raised

    '''
    global REFRESH_THREAD  #pylint: disable=global-statement
    global REFRESH_IN_ACTION  #pylint: disable=global-statement
    global STOP_SCHEDULER  #pylint: disable=global-statement
    global CONTINUOUS_THREAD  #pylint: disable=global-statement
    global EPD_SUPPORT
    global MY_SETTINGS
    logger.message(_("Application termination requested, please be patient"))
    if STOP_SCHEDULER is not None:
        STOP_SCHEDULER.set()
    if CONTINUOUS_THREAD is not None:
        CONTINUOUS_THREAD.join()
    abort_thread(REFRESH_THREAD,5)
    REFRESH_THREAD=None
    while REFRESH_IN_ACTION:
        sleep(0.5)
    stop_homematic(MY_SETTINGS,EPD_SUPPORT)
    sleep_epd(True,True)
    if EPD_SUPPORT is not None:
        EPD_SUPPORT.close_buttons()
        EPD_SUPPORT.gpio.cleanup()
    logger.message(_("Application terminated now by signal")+": "+str(exitsignal))
    sys.exit(0)

def wait_for_key():
    '''
    Wait for a key being pressed as part of the hardware-emulation.

    '''
    keymap={'1':EPD_SUPPORT.button1,'2':EPD_SUPPORT.button2,
            '3':EPD_SUPPORT.button3,'4':EPD_SUPPORT.button4}
    print(_('Keyboard-simulation for hardware-keys'))
    print(_("1..4=Buttons, t=terminate"))
    while True:
        try:
            key = sys.stdin.read(1) #input()
            if key is not None and key=='t':
                print("\n")
                print(_("Terminate keyboard input"))
                return
            if key:
                if key in keymap:
                    handle_button(keymap[key])
            else:
                print(_("Key not supported, only 1..4 allowed, t=terminate"))
            time.sleep(0.2) #wait for next check
        except KeyboardInterrupt:
            print('\n')
            print(_("No more keys awaited due to interrupt"))
            return
        except Exception as err:  #pylint: disable=broad-except
            print('\n')
            print(_("No more keys awaited due to exception")+":"+str(err))
            return

class Command():
    """
    Commandline interface for the main app

    """
    help = _("Runs epaper app")
    @staticmethod
    def add_arguments(parser):
        '''
        Add the commandline arguments that will be executed

        :param parser: commandline parser
        '''
        parser.add_argument('--savescreens', help=_("Save each image to directory screens"),
                            required=False, action='store_true')
        parser.add_argument('--language', help=_("The to be used language"), required=False)
        parser.add_argument('--startscreen', help=_("The to be used screen at startup"),
                            required=False)
        parser.add_argument('--showscreens',
            help=_("Show several, comma separated, screens one after the other and terminates"),
                            required=False)
        parser.add_argument('--showallscreens', help=_("Show all available screens once"),
                            required=False, action='store_true')
        parser.add_argument('--version', help=_("Returns current git version and terminates"),
                            required=False, action='store_true')
        parser.add_argument('--use_logfile', help=
                            _("Logs various messages into logfile and messages on screen"),
                            required=False, action='store_true')
        parser.add_argument('--keyboard', help=_("Emulate device keys via keyboard"),
                            required=False, action='store_true')
        parser.add_argument('--screens', help=_("List all available screens"),
                            required=False, action='store_true')

    @staticmethod
    def handle(*args, **options):  # @UnusedVariable pylint: disable=unused-argument
        """
        Main loop to process the commandline

        """
        global REFRESH_THREAD #pylint: disable=global-statement
        global MY_SETTINGS #pylint: disable=global-statement
        global STOP_SCHEDULER  #pylint: disable=global-statement
        global EPD_SUPPORT  #pylint: disable=global-statement
        global REFRESH_INTERVALL #pylint: disable=global-statement
        global MESSAGE #pylint: disable=global-statement

        if options['version']:
            print(_("The current version is")+": "+Settings.get_git_version())
            return

        MY_SETTINGS=Settings()
        if options['screens']:
            screen_factory=ScreenFactory(MY_SETTINGS)
            screen_list=screen_factory.get_full_menu_list(False)
            for screen,description in screen_list:
                if len(screen) < 1:
                    screen = "   " #just for display reasons
                print(screen+": "+description)
            return

        log_level=MY_SETTINGS.get_value(Settings.LOG_LEVEL_INT, MESSAGE)

        # "Register" new loggin level
        logging.addLevelName(MESSAGE, 'MESSAGE')  # addLevelName(25, 'MESSAGE')

        # Verify
        assert logging.getLevelName(MESSAGE) == 'MESSAGE'

        #: Location for logfiles
        log_file=Settings.MYBASE_DIR+"/log/epaper.log"

        use_logfile=options['use_logfile']
        if use_logfile:
            #define filehandler first
            logging.basicConfig(filename=log_file, level=log_level,
                                format='%(asctime)s;%(filename)-16.16s;%(lineno)04d;'+\
                                '%(levelname)-8s;%(message)s'
                                )
            # define a Handler which writes INFO messages or higher to the sys.stderr
            console = logging.StreamHandler()
            console.setLevel(MESSAGE)
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
        logger.message(_("Starting the app now"))
        logger.message(_("Logging to")+": "+str(log_file)+" "+_("at level")+": "+str(log_level))
        MY_SETTINGS.remote_debug()


        #init homematic interface if defined
        homematic=start_homematic(MY_SETTINGS,EPD_SUPPORT)

        # get the display frame / epaper
        logger.info("epd2in7 Loading")
        EPD_SUPPORT=EpdSupport(MY_SETTINGS,homematic=homematic)

        #lang_en = gettext.translation('epaper', languages=['en'])
        lang_de = gettext.translation('epaper', localedir=Settings.LOCALE_DIR, languages=['de'])

        REFRESH_INTERVALL=MY_SETTINGS.get_value(Settings.REFRESH_INTERVALL_INT,60)
        language=options["language"]

        if language is None or len(language) <1:
            language=MY_SETTINGS.get_value(Settings.DISPLAY_LANGUAGE_STR,'en')

        # next trick to set environment for the use by gettext as otherwise
        # the translations could not be seen...
        os.environ.setdefault("LANGUAGE", language)
        logger.debug("Language="+str(os.environ.get("LANGUAGE", #pylint: disable=logging-not-lazy
                                                    "NO")))
        #to translate weekday and date formatting on homescreen
        locale.setlocale(locale.LC_TIME, MY_SETTINGS.get_value(Settings.TIMELOCALE_STR,
                                                               locale.getdefaultlocale()))
        if ((language is not None) and (len(language)>1)):
            #install the language to use for the translations
            #If you need more languages then this would be the place to do so
            if language == 'de':
                lang_de.install('epaper')
        #    else:
        #        lang_en.install('epaper')

        savescreens=options["savescreens"]
        if savescreens:
            EPD_SUPPORT.save_screens()
        startscreen=options["startscreen"]
        if startscreen is None or len(startscreen)<1:
            startscreen=ScreenType.MENU_VERSION
        logger.message(_("Initializing the device"))
        if not init_epd(startscreen):
            logger.fatal(_("Not able to start as the given screen could not be used")+": "+\
                         startscreen)
            if homematic is not None:
                homematic.exit()
            return
        logger.message(_("Initializing the buttons"))
        init_buttons()
        logger.info("epaper_app now started with screen "+\
                    startscreen)  #pylint: disable=logging-not-lazy
        #handle command?
        show() #show initial image, usually version

        #check if we shall produce a series of screens
        startscreens=options["showscreens"]
        if options['showallscreens']:
            screen_factory=ScreenFactory(MY_SETTINGS)
            screen_list=screen_factory.get_full_menu_list(False)
            startscreens=""
            for screen,description in screen_list:
                startscreens+=screen+","
        if startscreens is not None and len(startscreens)>0:
            start_screens=startscreens.split(',')
            s_type=ScreenType()
            for display_screen in start_screens:
                if len(display_screen)<1:
                    continue
                if display_screen in ("VER","HOM"):
                    continue # do not show homescreen and version twice
                if s_type.get_type(s_type.get_technical_name(display_screen)) in \
                    (s_type.ACTION_TYPE,s_type.FIXED_ACTION_TYPE):
                    continue #do not show screens that could not be shown
                print("Generating image for "+display_screen)
                EPD_SUPPORT.set_current_page(display_screen)
                show()
            if homematic is not None:
                homematic.exit()
            logger.message(_("Application terminated now due to option startscreens"))
            return #terminate

        #next show home-screen if we had started with Welcome or error in case Homematic failed
        if startscreen == ScreenType.MENU_VERSION:
            if homematic_working(MY_SETTINGS,EPD_SUPPORT):
                EPD_SUPPORT.set_current_page(ScreenType.MENU_HOME)
            else:
                EPD_SUPPORT.set_current_page(ScreenType.MENU_ERR_HM)

        # refresh screen every 60 seconds for now
        REFRESH_THREAD=start_thread(lambda: every(REFRESH_INTERVALL, show),name="epaper_timer")

        #check for sleeping device
        time_2_sleep=MY_SETTINGS.get_value(Settings.TIME_TO_SLEEP,None)
        if time_2_sleep is not None and len(time_2_sleep) > 0:
            schedule.every().day.at(time_2_sleep).do(soft_sleep_epd)
        time_2_wakeup=MY_SETTINGS.get_value(Settings.TIME_TO_WAKEUP,None)
        if time_2_wakeup is not None and len(time_2_wakeup) > 0:
            schedule.every().day.at(time_2_wakeup).do(soft_awake_epd)
        if time_2_sleep or time_2_wakeup:
            STOP_SCHEDULER=run_schedule(10)

        signal.signal(signal.SIGUSR1,handle_exit_sig) #exit
        signal.signal(signal.SIGINT,handle_exit_sig) #keyboard

        logger.message(_("Application now in endless loop"))
        if options["keyboard"]:
            wait_for_key()
        forever=threading.Event()
        forever.wait()

        #will hopefully never be reached ;)
        logger.message(_("Application terminated now"))

def main():
    '''
    Main function executed when the python script will be called

    '''
    cmd = Command()
    # Initialisieren des parsers und setzen des Hilfetextes
    parser = argparse.ArgumentParser(description=cmd.help)

    # # Initialisieren des subparsers und setzen des Hilfetextes
    cmd.add_arguments(parser)
    options = parser.parse_args()
    cmd_options = vars(options)
    # Move positional args out of options to mimic legacy optparse
    args = cmd_options.pop('args', ())
    cmd.handle(*args,**cmd_options)

if __name__ == "__main__":
    main()
