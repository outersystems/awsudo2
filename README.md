# Context

* This tool is deeply inspired from [makethunder/awsudo](https://github.com/makethunder/awsudo).
* This project is to help me to learn python and I'm far from being perfect. Advices are welcomed but also remember that I have an opinion.
* I had to have multiple aws keys of multiple users.

# Features

* The command provided to `awsudo2` has its environment enriched with AWS standard variables.

```console
$ awsudo2 -u default env | grep AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_SECURITY_TOKEN=...
AWS_PROFILE=default
AWS_DEFAULT_REGION=...
```

* Get temporary credentials for a given role (profile `some-role`):
```console
$ awsudo2 -u some-profile env | grep AWS
```

This is useful for running [aws-cli](https://aws.amazon.com/cli/) or [terraform](https://www.terraform.io/).

* Get temporary credentials for you (profile `default`):
```console
$ awsudo2 -u default env | grep AWS
```

This is useful when using programs which which able to call [AssumeRole](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html) themselves, like [terragrunt](https://github.com/gruntwork-io/terragrunt).


* Have your user security token cached: The first call is doing MFA authentication if needed. The next ones will re-use the cached session tokens (in ~/.aws/awsudo2/cache) for the specified `duration_seconds`:

```console
$ awsudo2 -u default echo Hello
Enter MFA code of device arn:aws:iam::123456789012:mfa/some-username: 
Hello
$ awsudo2 -u default echo Hello
Hello
```

* `awsudo2` also uses `AWS_PROFILE`:

```console
$ export AWS_PROFILE some-profile
$ awsudo2 echo Hello
Hello
```

* Save your `config`

The profiles are searched in the two aws's files: `awsudo2` doesn't check which file contains. This logic permits to put `mfa_serial` in `credentials`. So personnal data is only in `credentials` and  `config` can be shared between colleagues.


* Be creative!

I use [aws plugin](https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/aws) of [oh-my-zsh](https://github.com/ohmyzsh/ohmyzsh). My experience goes like this:

```console
$ export AWS_PROFILE=some-profile
$ alias aws='awsudo2 aws'                                       <aws:some-profile>
$ aws sts get-caller-identity                                   <aws:some-profile>
{
    "UserId": "...",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/some-role/default"
}
$ AWS_PROFILE=some-other-profile aws sts get-caller-identity    <aws:some-profile>
{
    "UserId": "...",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/some-other-role/default"
}
$ awsudo2 docker run --rm -ti -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN whatever-images
...
```

As `aws` is an alias to `awsudo2 aws`, the security token is refreshed at each command invocation without having to enter my [MFA token](https://aws.amazon.com/iam/features/mfa/) up to one and a half day ([default value for user tokens](https://docs.aws.amazon.com/STS/latest/APIReference/API_GetSessionToken.html)).

# Installation

## Prerequisits

* Have `python3` and `pip3` installed to your tastes.
* Have [aws-cli](https://aws.amazon.com/cli/) setup [with your keys](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

## Install

```console
$ pip3 install git+https://github.com/outersystems/awsudo2.git
```

## Setup example

```console
$ cat ~/.aws/config
[profile default]
source_profile = default
region = us-east-1
duration_seconds = 129600

[profile some-profile]
role_arn = arn:aws:iam::123456789012:role/some-rolename
source_profile = default
region = us-east-1

[profile some-other-profile]
role_arn = arn:aws:iam::123456789012:role/some-other-rolename
source_profile = default
region = us-east-1
```

```console
$ cat ~/.aws/credentials
[default]
aws_access_key_id = AKIAIXAKX3ABKZACKEDN
aws_secret_access_key = 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
mfa_serial = arn:aws:iam::123456789012:mfa/some-username
```
