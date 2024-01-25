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
