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

    profile = os.environ.get('AWS_PROFILE')
    for (option, value) in options:
        if option == '-u':
            profile = value
        else:
            raise Exception("unknown option %s" % (option,))

    return profile, args


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


def fetch_user_token(profile_config):
    """Fetch temporary credentials of a user with an MFA."""

    exits_if_has_no_credentials(profile_config)

    durationSeconds = int(profile_config['duration_seconds'])

    mfaSerial = profile_config['mfa_serial']
    try:
        mfaToken = getpass.getpass(prompt="Enter MFA code of device %s: " % mfaSerial)
    except KeyboardInterrupt as e:
        print(e)
        exit(1)


    # TODO: how to provide user creds to this call?
    sts = boto3.client('sts',
        aws_access_key_id=profile_config['aws_access_key_id'],
        aws_secret_access_key=profile_config['aws_secret_access_key'],
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


def refresh_session(cache_filename, profile_config):
    """Refresh credentials and cache them."""

    session_creds = fetch_user_token(profile_config)

    with open(os.path.expanduser(cache_filename), "w+") as json_file:
        json.dump(session_creds, json_file, indent=2, sort_keys=True, default=str)

    return session_creds


def fetch_assume_role_creds(user_session_token, profile_config):

    exits_if_has_no_credentials(profile_config)

    sts = boto3.client('sts',
        aws_access_key_id=user_session_token['Credentials']['AccessKeyId'],
        aws_secret_access_key=user_session_token['Credentials']['SecretAccessKey'],
        aws_session_token=user_session_token['Credentials']['SessionToken'],
        region_name=profile_config['region'])

    if profile_config['duration_seconds']:
        duration = int(profile_config['duration_seconds'])
    else:
        duration = 3600

    if contains_credentials(profile_config):
        session_name = profile_config["profile"]
    else:
        session_name = profile_config['source']["profile"]

    try:
        role_session = sts.assume_role(
            RoleArn=profile_config['role_arn'],
            RoleSessionName=session_name,
            DurationSeconds=duration)
    except Exception as e:
        print(e)
        exit(1)

    return(role_session['Credentials'])


def get_profile_config(profile):

    config_element = {}
    config_element['profile'] = profile

    files = [('~/.aws/credentials', "%s"), ('~/.aws/config', "profile %s")]
    items = ['aws_access_key_id', 'aws_secret_access_key', 'role_arn', 'region', 'duration_seconds', 'mfa_serial', 'source_profile']

    for i in items:
        config_element[i] = None

    for f, p in files:
        config = configparser.ConfigParser()
        config.read([os.path.expanduser(f)])

        for i in items:
            try:
                config_element[i] = config.get(p % profile, i)
            except configparser.NoSectionError:
                pass
            except configparser.NoOptionError:
                pass

    if config_element.get('source_profile'):
        config_element['source'] = get_profile_config(config_element['source_profile'])

    return(config_element)

def exits_if_has_no_credentials(profile_config):
    if not contains_credentials(profile_config):
        if profile_config.get('source'):
            if not contains_credentials(profile_config['source']):
                print("Credentials not found")
                exit(1)
        else:
            print("Credentials not found")
            exit(1)

def contains_credentials(profile_config):
    return profile_config.get('aws_access_key_id') and profile_config.get('aws_secret_access_key')

def create_aws_env_var(profile_config, creds):

    env = dict()
    env['AWS_ACCESS_KEY_ID'] = creds['AccessKeyId']
    env['AWS_SECRET_ACCESS_KEY'] = creds['SecretAccessKey']
    env['AWS_SESSION_TOKEN'] = creds['SessionToken']
    env['AWS_SECURITY_TOKEN'] = creds['SessionToken']
    env['AWS_PROFILE'] = profile_config['profile']

    env['AWS_DEFAULT_REGION'] = ""
    if profile_config['region']:
        env['AWS_DEFAULT_REGION'] = profile_config['region']
    else:
        if profile_config['source']:
            if profile_config['source']['region']:
                env['AWS_DEFAULT_REGION'] = profile_config['source']['region']

    return(env)

def is_arn_role(arn):

    if arn:
        pattern = re.compile(":role/")
        return(pattern.search(arn))

    return False

def main():

    cache_dir = "~/.aws/awsudo2/cache/"
    cache_file_extension = "session.json"

    profile, args = parse_args()
    clean_env()


    profile_config = get_profile_config(profile)
    if contains_credentials(profile_config):
        creds_profile_config = profile_config
    else:
        creds_profile_config = profile_config['source']

    cache_filename = os.path.expanduser(
        cache_dir + creds_profile_config['profile'] + "." + cache_file_extension)

    session_creds = get_cached_session(cache_filename)

    if not is_session_valid(session_creds):
        # profile_config = get_profile_config("default")
        profile_config = get_profile_config(profile)

        if contains_credentials(profile_config):
            creds_profile_config = profile_config
        else:
            creds_profile_config = profile_config['source']

        session_creds = refresh_session(cache_filename, creds_profile_config)

    profile_config = get_profile_config(profile)

    if is_arn_role(profile_config['role_arn']):
        role_creds = fetch_assume_role_creds(
            session_creds,
            profile_config)
    else:
        role_creds = session_creds['Credentials']

    env = create_aws_env_var(profile_config, role_creds)

    run(args, env)


if __name__ == '__main__':
    main()

