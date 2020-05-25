# from awsprofile import AWSProfile
#!/bin/env python3

# import .awsprofile

import sys
import pytest

import awsudo2

def test_no_args(capsys, monkeypatch):
    '''With no arguments, awsudo2 exits with usage.'''
    monkeypatch.setattr(sys, 'argv', ['awsudo2'])

    a = awsudo2.awsprofile.AWSProfile("blah")

    with pytest.raises(SystemExit):
        awsudo2.main.main()

    out, err = capsys.readouterr()
    assert 'Usage:' in err
