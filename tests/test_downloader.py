"""
**Unit tests for the downloader**

Content
#######
This module tests to some extend the provided functionalities

Info
####
* **author:** (c) Thomas Lüth 2024
* **email:** info@tlc-it-consulting.com
* **created:** 2024-01-16

Code
####
"""

import unittest
import argparse
from unittest.mock import MagicMock
from unittest import mock
import pytest
from cpm_downloader import Command

class TestDownloader(unittest.TestCase):
    '''
    Testing the Downloader
    '''

    def __init__(self, methodName: str = "runTest") -> None:
        self.parser=None
        super().__init__(methodName)

    @staticmethod
    def create_parser():
        """creates the parser

         Returns:
             ArgumentParser: Parser to accept arguments
        """
        parser = argparse.ArgumentParser(description=Command.help)
        Command.add_arguments(parser)
        return parser

    @staticmethod
    def start_handler(options):
        """_summary_

        Args:
            options (argparse): Optionlist for further processing

        Returns:
            Command: Command class
        """
        cmd=Command()
        # Add now commandline args to be checked
        cmd_options = vars(options)
        # Move positional args out of options to mimic legacy optparse
        args = cmd_options.pop('args', ())
        cmd.handle(*args,**cmd_options)
        return cmd

    @pytest.fixture(autouse=True)
    def setup_function(self):
        """Creates an internal parser
        """
        self.parser=self.create_parser()

    @mock.patch('builtins.print')
    def test_version(self,mock_print):
        """Test help
        Call Help and check the provided output
        """
        options = self.parser.parse_args(["--version"])
        self.start_handler(options)
        mock_print.assert_called_once()

    @mock.patch('serial.Serial')
    @mock.patch('playsound.playsound')
    @mock.patch('cpm_downloader.logger')
    def test_no_serial(self,mock_logger,mock_sound,mock_ser):
        """Test as if no serial device had been found
        """
        ser_line=MagicMock()
        ser_line.side_effect = IOError()
        mock_ser.side_effect=ser_line
        mock_ser.__enter__=MagicMock(return_value=ser_line)
        mock_ser.__exit__=MagicMock()
        mock_logger.exception=MagicMock()
        mock_logger.info=MagicMock()
        options = self.parser.parse_args([])
        self.start_handler(options)
        mock_sound.assert_called_once()
        mock_logger.exception.assert_called_once()
        mock_logger.info.assert_called()


    @mock.patch('cpm_downloader.serial')
    @mock.patch('playsound.playsound')
    @mock.patch('cpm_downloader.logger')
    @mock.patch('cpm_downloader.Path')
    def test_serial_open(self,mock_path, mock_logger,mock_sound,mock_ser):
        """Test with open serial device: change dir and quit
        """
        ser_line=MagicMock()
        ser_line.is_open=True
        ser_line.read_until=MagicMock(side_effect=[b'>>>+++STOP+++<<<',\
            b'#_G1\n<<<+++GO+++>>>',b'>>>+++STOP+++<<<',b'QUIT<<<+++GO+++>>>'])
        serial=MagicMock()
        serial.return_value.__enter__.return_value=ser_line
        serial.return_value.__exit__.return_value=MagicMock()
        mock_ser.Serial=serial
        mock_logger.exception=MagicMock()
        mock_logger.info=MagicMock()
        mock_logger.error=MagicMock()
        mock_path.return_value.mkdir.return_value=MagicMock()
        options = self.parser.parse_args([])
        self.start_handler(options)
        mock_sound.assert_called_once()
        mock_logger.exception.assert_not_called()
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()
        mock_path.return_value.mkdir.assert_called()
