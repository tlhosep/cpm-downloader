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
import argparse
from unittest.mock import MagicMock
from unittest import mock
import pytest
from tlu_utils import get_git_version

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
