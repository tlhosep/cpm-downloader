"""
**Unit tests for the dirlistcompare**

Content
#######
This module tests to some extend the provided functionalities

Info
####
* **author:** (c) Thomas Lüth 2024
* **email:** info@tlc-it-consulting.com
* **created:** 2024-01-27

Code
####
"""

import unittest
import argparse
from unittest.mock import MagicMock, mock_open
from unittest import mock
import pytest
from cpm_dirlistcompare import Command, DirFileState

class TestDirlistCompare(unittest.TestCase):
    '''
    Testing the directory compare
    '''

    def __init__(self, methodName: str = "runTest") -> None:
        self.parser=None
        super().__init__(methodName)
        self.file_sample="Scanning Directory...\n"\
        "\n"\
        "Sorting  Directory...\n"\
        "\n"\
        "Directory For Drive F:  User  0\n"\
        "\n"\
        "    Name     Bytes   Recs   Attributes      Name     Bytes   Recs   Attributes \n"\
        "------------ ------ ------ ------------ ------------ ------ ------ ------------\n"\
        "ALLFILES LST     0k      0 Dir RW       CCP      COM     4k     25 Sys RW      \n"\
        "\n"\
        "Total Bytes     =    540k  Total Records =    3104  Files Found =   63\n"\
        "Total 1k Blocks =    421   Used/Max Dir Entries For Drive F:  583/2048\n"\
        "\n"


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

    def test_dir_file_state(self):
        """Test DirFileState
        """
        DirFileState.test=DirFileState("test")
        self.assertEqual(str(DirFileState.test),"test")

    @mock.patch('builtins.open', )
    @mock.patch('cpm_dirlistcompare.logger')
    def test_extract_file_no_open(self,mock_logger,mymock_open):
        """Test as if the file could not be opened
        """
        file_handle=MagicMock()
        file_handle.side_effect = IOError()
        mymock_open.side_effect=file_handle
        mymock_open.__enter__=MagicMock()
        mymock_open.__exit__=MagicMock()
        mock_logger.exception=MagicMock()
        ret_val=Command.extract_file("testfile.lst")
        mock_logger.exception.assert_called_once()
        self.assertIsNone(ret_val)

    @mock.patch('cpm_dirlistcompare.logger')
    def test_extract_file_read1(self,mock_logger):
        """Test a simple sequence 
        """
        file_content="Test\n\n"
        with mock.patch('builtins.open', mock_open(read_data=file_content)):
            ret_val=Command.extract_file("testfile.lst")
        self.assertIsNotNone(ret_val)
        mock_logger.assert_not_called()
        self.assertEqual(len(ret_val),0)


    @mock.patch('cpm_dirlistcompare.logger')
    def test_extract_file_read2(self,mock_logger):
        """Test a full sequence 
        """
        with mock.patch('builtins.open', mock_open(read_data=self.file_sample)):
            ret_val=Command.extract_file("testfile.lst")
        self.assertIsNotNone(ret_val)
        mock_logger.assert_not_called()
        self.assertEqual(len(ret_val),2)
        self.assertEqual(ret_val[0],"F00_ALLFILES.LST")


    @mock.patch('cpm_dirlistcompare.logger')
    def test_extract_file_read3(self,mock_logger):
        """Test a full sequence with indicator
        """
        with mock.patch('builtins.open', mock_open(read_data=self.file_sample)):
            ret_val=Command.extract_file("testfile.lst","XXX")
        self.assertIsNotNone(ret_val)
        mock_logger.assert_not_called()
        self.assertEqual(len(ret_val),2)
        self.assertEqual(ret_val[0],"F00_ALLFILES.LST_XXX")

    @mock.patch('cpm_dirlistcompare.logger')
    @mock.patch('cpm_dirlistcompare.Command.extract_file')
    @mock.patch('builtins.print')
    def test_handler(self,mock_print,mock_extract,mock_logger):
        """Test a normal run
        """
        mock_logger.info=MagicMock()
        mock_extract.side_effect=[["F00_A.F","F00_B.F"],["F00_A.F","F00_C.F"]]
        options = self.parser.parse_args(["--file1", "file1", "--file2","file2"])
        self.start_handler(options)
        mock_print.assert_called()
        mock_logger.info.assert_called()
