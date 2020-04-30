##compdef awsudo2

# Description:
# Auto completion script for https://github.com/makethunder/awsudo/tree/master/awsudo
# Auto completion script for https://github.com/makethunder/awsudo/tree/master/awsudo
#
# Author:
# @turhn https://github.com/turhn

_awsudo2() {
  local curcontext="$curcontext" state line ret=1
  typeset -A opt_args

  if [[ -v AWS_PROFILE ]]; then
    _arguments -C \
      '1:targets: _command_names' \
      '*:: :->target' \
    && ret=0
  else
    _arguments -C \
      '1:subcommands:->cmds' \
      '2:profiles:->profile_list' \
      '3:targets: _command_names' \
      '*:: :->target' \
    && ret=0
  fi

  case "$state" in
    (cmds)
      local commands;
      commands=(
        '-u: AWS Profile'
      )
       _describe -t commands 'command' commands && ret=0
      ;;
    (profile_list)
      local profiles;
      profiles=(
        $(cat ~/.aws/config \
          | awk '
            /BEGIN/ { profile = ""; desc = "" }
            /^\[profile/ { profile=$0 ; gsub("\[profile ", "", profile); gsub("\]", "", profile) }
            /^role_arn/ { desc=$0; gsub("role_arn = ", "", desc) }
            /^$/ { printf("%s:%s\n", profile, desc); profile = ""; desc = ""}
            /END/ { printf("%s:%s\n", profile, desc) }' \
          | sort -u
        )
      )
      _describe -t profiles 'profiles' profiles && ret=0
     ;;
    (target)
      ((CURRENT--))
      shift words
      shift words
      _complete && ret=0
      ;;
  esac

  return $ret
}

compdef _awsudo2 awsudo2

# Local Variables:
# mode: Shell-Script
# sh-indentation: 2
# indent-tabs-mode: nil
# sh-basic-offset: 2
# End:
# vim: ft=zsh sw=2 ts=2 et
