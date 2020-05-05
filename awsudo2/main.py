#!/bin/env python3

import os
import pathlib
import json
import datetime
import dateutil.parser
import pytz
import boto3
import botocore
import getopt
import sys
import configparser
import getpass
import re
from awsprofile import AWSProfile


def usage():
    sys.stderr.write('''\
Usage: awsudo2 [-u USER] [--] COMMAND [ARGS] [...]

Sets AWS environment variables and then executes the COMMAND.
''')
    exit(1)


def parse_args():
    try:
        options, args = getopt.getopt(sys.argv[1:], 'u:')
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)
        usage()

    if not (args):
        usage()

    profile_name = os.environ.get('AWS_PROFILE')
    for (option, value) in options:
        if option == '-u':
            profile_name = value
        else:
            raise Exception("unknown option %s" % (option,))

    return profile_name, args


def clean_env():
    """Delete from the environment any AWS or BOTO configuration.

    Since it's this program's job to manage this environment configuration, we
    can blow all this away to avoid any confusion.
    """
    for k in list(os.environ.keys()):
        if k.startswith('AWS_') or k.startswith('BOTO_'):
            del os.environ[k]


def run(args, extraEnv):
    """Run the of args with the given env.

    The role of awsudo2, like sudo, is to run what is given after its options.
    The first arg is the command to run, the rest of the args are its options and arguments."""
    env = os.environ.copy()
    env.update(extraEnv)

    try:
        os.execvpe(args[0], args, env)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        raise SystemExit("%s: command not found" % (args[0],))


def fetch_user_token(profile):
    """Fetch temporary credentials of a user with an MFA."""

    if not profile.has_credentials():
        exit(1)

    durationSeconds = profile.data['duration_seconds']
    mfaSerial = profile.data['mfa_serial']

    try:
        mfaToken = getpass.getpass(prompt="Enter MFA code of device %s: " % mfaSerial)
    except KeyboardInterrupt as e:
        print(e)
        exit(1)


    sts = boto3.client('sts',
        aws_access_key_id=profile.data['aws_access_key_id'],
        aws_secret_access_key=profile.data['aws_secret_access_key'],
    )
    try:
        return sts.get_session_token(
            DurationSeconds=durationSeconds,
            SerialNumber=mfaSerial,
            TokenCode=mfaToken)
    except Exception as e:
        print(e)
        exit(1)

def get_cached_session(cache_filename):
    """Return the current session from cache_dir/cache_file.

    It could be {} if no file found."""
    cache_dir_path = os.path.dirname(
        os.path.expanduser(cache_filename))
    pathlib.Path(cache_dir_path).mkdir(parents=True, exist_ok=True)
    # Load session creds
    if os.path.isfile(cache_filename):
        with open(cache_filename) as json_file:
            try:
                session_creds = json.load(json_file)
            except json.decoder.JSONDecodeError as e:
                print(e)
                exit(1)
    else:
        session_creds = {}
        with open(cache_filename, "w+") as json_file:
            json.dump(session_creds, json_file)

    return session_creds


def is_session_valid(session_creds):
    """Check if a session is still valid, based on its expiration date."""

    if 'Credentials' in session_creds.keys():
        expiration_utc = dateutil.parser.isoparse(session_creds['Credentials']['Expiration'])
        now_utc = pytz.utc.localize(datetime.datetime.utcnow())
        max_accepted_timedelta = datetime.timedelta(hours=1)

        if (expiration_utc - now_utc) > max_accepted_timedelta:
            return True

    return False


def refresh_session(cache_filename, profile):
    """Refresh credentials and cache them."""

    session_creds = fetch_user_token(profile)

    with open(os.path.expanduser(cache_filename), "w+") as json_file:
        json.dump(session_creds, json_file, indent=2, sort_keys=True, default=str)

    return session_creds


def fetch_assume_role_creds(user_session_token, profile):

    if not profile.has_credentials():
        exit(1)

    sts = boto3.client('sts',
        aws_access_key_id=user_session_token['Credentials']['AccessKeyId'],
        aws_secret_access_key=user_session_token['Credentials']['SecretAccessKey'],
        aws_session_token=user_session_token['Credentials']['SessionToken'],
        region_name=profile.data['region'])

    try:
        role_session = sts.assume_role(
            RoleArn=profile.data['role_arn'],
            RoleSessionName=profile.data["profile"],
            DurationSeconds=profile.data['duration_seconds'])
    except Exception as e:
        print(e)
        exit(1)

    return(role_session['Credentials'])


def create_aws_env_var(profile, creds):

    env = dict()
    env['AWS_ACCESS_KEY_ID'] = creds['AccessKeyId']
    env['AWS_SECRET_ACCESS_KEY'] = creds['SecretAccessKey']
    env['AWS_SESSION_TOKEN'] = creds['SessionToken']
    env['AWS_SECURITY_TOKEN'] = creds['SessionToken']
    env['AWS_PROFILE'] = profile.data['profile']
    env['AWS_DEFAULT_REGION'] = profile.data['region']

    return(env)


def main():

    cache_dir = "~/.aws/awsudo2/cache/"
    cache_file_extension = "session.json"

    profile_name, args = parse_args()
    clean_env()


    profile = AWSProfile(profile_name)
    if not profile.credentials_present:
        print("Credentials not found")
        exit(1)

    cache_filename = os.path.expanduser(
        cache_dir
        + profile.get_username()
        + "."
        + cache_file_extension)

    session_creds = get_cached_session(cache_filename)

    if not is_session_valid(session_creds):
        session_creds = refresh_session(cache_filename, profile)


    if profile.is_role():
        role_creds = fetch_assume_role_creds(
            session_creds,
            profile)
    else:
        role_creds = session_creds['Credentials']

    env = create_aws_env_var(profile, role_creds)

    run(args, env)


if __name__ == '__main__':
    main()
