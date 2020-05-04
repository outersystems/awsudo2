# from awsprofile import AWSProfile
import configparser
import os
 
class AWSProfile:
    'AWS profile representation, flatten with its role_source.'

    Files = [('~/.aws/credentials', "%s"), ('~/.aws/config', "profile %s")]
    Items = ['aws_access_key_id', 'aws_secret_access_key', 'role_arn', 'region', 'duration_seconds', 'mfa_serial', 'source_profile']

    def __init__(self, name):
        self.data = {}
        self.data['profile'] = name
        self.username = None
        self.credentials_present = False

        for f, p in AWSProfile.Files:   
            tmp = load_section(f, p % name, AWSProfile.Items)
            self.data = {**self.data, **tmp}
        
        if 'aws_access_key_id' in self.data:
            self.username = name
            self.credentials_present = True

        if 'source_profile' in self.data:
            for f, p in AWSProfile.Files:   
                tmp = load_section(f, p % self.data['source_profile'], AWSProfile.Items)
                self.data = {**tmp, **self.data}

            if 'aws_access_key_id' in self.data and not self.username:
                self.username = self.data['source_profile']
                self.credentials_present = True

    def is_role():
        if self.data['role_arn']:
            role_pattern = re.compile(":role/")
            return(role_pattern.search(self.data['role_arn']))
        return False
    

    def is_user():
        if self.data['role_arn']:
            user_pattern = re.compile(":user/")
            return(user_pattern.search(self.data['role_arn']))
        return False

    def has_credentials():
        return(self.credentials_present)

def load_section(filename, section, items):

    content = {}

    config = configparser.ConfigParser()
    config.read([os.path.expanduser(filename)])

    for i in items:
        try:
            content[i] = config.get(section, i)
        except configparser.NoSectionError:
            pass
        except configparser.NoOptionError:
            pass

    return content


