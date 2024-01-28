"""
**Unit tests for the utils **

Content
#######
This module tests to some extend the provided functionalities

Info
####
* **author:** (c) Thomas Lüth 2024
* **email:** info@tlc-it-consulting.com
* **created:** 2024-01-25

Code
####
"""

import unittest
from unittest.mock import MagicMock
from unittest import mock
# import pytest
from tlu_utils import get_git_version, add_parser_log_args, cmdline_main

class TestUtils(unittest.TestCase):
    '''
    Testing the utils functions
    '''

    @mock.patch('tlu_utils.run')
    def test_version(self,mock_run):
        """Test git version
        Call get_git_version and anticipate a valid return
        """
        process=MagicMock()
        process.returncode=0
        process.stdout=MagicMock()
        process.stdout.decode=MagicMock(return_value="1.2.3")
        mock_run.return_value=process
        git_version=get_git_version()
        self.assertEqual(git_version,"1.2.3")
        mock_run.assert_called_once()

    @mock.patch('tlu_utils.run')
    def test_version_err(self,mock_run):
        """Test git version
        Call get_git_version and anticipate a invalid return
        """
        process=MagicMock()
        process.returncode=1
        process.stdout=MagicMock()
        process.stdout.decode=MagicMock(return_value="1.2.3")
        mock_run.return_value=process
        git_version=get_git_version()
        self.assertEqual(git_version,"")
        mock_run.assert_called_once()
        process.stdout.decode.assert_not_called()

    def test_add_parser(self):
        """Test to add some lines to a parser
        """
        parser=MagicMock()
        parser.add_argument=MagicMock()
        add_parser_log_args(parser)
        parser.add_argument.assert_called()

    @mock.patch('tlu_utils.argparse')
    def test_execute_main(self,mock_arg):
        """Test to check cmdline_main

        Args:
            mock_argparse (MagicMock): argparse function
        """
        class ArgsClass:
            """Testclass for commandhandler
            used with vars un the tested function
            """
            def __init__(self) -> None:
                self.args = "args"
                self.arg1 = "arg1"

        parser=MagicMock()
        args=ArgsClass()
        parser.parse_args=MagicMock(return_value=args)
        mock_arg.ArgumentParser=MagicMock(return_value=parser)
        cmd=MagicMock()
        cmd.handle=MagicMock()
        cmdline_main(cmd)
        cmd.handle.assert_called_once_with('a', 'r', 'g', 's', arg1='arg1')
