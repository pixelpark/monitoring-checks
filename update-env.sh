#!/bin/bash
# shellcheck disable=SC2317  # Don't warn about unreachable commands in this file

set -e
set -u

VERBOSE="n"
DEBUG="n"
QUIET='n'

VERSION="3.0"

# console colors:
RED=""
YELLOW=""
GREEN=""
BLUE=""
# shellcheck disable=SC2034
MAGENTA=""
CYAN=""
NORMAL=""

BASENAME=$(basename "${0}" )
BASE_DIR=$( dirname "$0" )
cd "${BASE_DIR}"
BASE_DIR=$( readlink -f . )
MAN_PARENT_DIR="data/share/man"

declare -a VALID_PY_VERSIONS=("3.14" "3.13" "3.12" "3.11" "3.10" "3.9" "3.8")
VENV='.venv'

PIP_OPTIONS=
export VIRTUAL_ENV_DISABLE_PROMPT=y

TMPFILE_GETVALUE=
TMPFILE_GETKEYS=
ENTRYPOINTS=''
DATA_DIR=



#-------------------------------------------------------------------
detect_color() {

    local safe_term="${TERM//[^[:alnum:]]/?}"
    local match_lhs=""
    local use_color="false"
    local term=

    if [[ -f ~/.dir_colors   ]] ; then
        match_lhs="${match_lhs}$( grep '^TERM ' ~/.dir_colors | sed -e 's/^TERM  *//' -e 's/ .*//')"
    fi
    if [[ -f /etc/DIR_COLORS   ]] ; then
        match_lhs="${match_lhs}$( grep '^TERM ' /etc/DIR_COLORS | sed -e 's/^TERM  *//' -e 's/ .*//')"
    fi
    if [[ -z ${match_lhs} ]] ; then
        type -P dircolors >/dev/null && \
        match_lhs=$(dircolors --print-database | grep '^TERM ' | sed -e 's/^TERM  *//' -e 's/ .*//')
    fi
    for term in ${match_lhs} ; do
        # shellcheck disable=SC2053
        if [[ "${safe_term}" == ${term} || "${TERM}" == ${term} ]] ; then
            use_color="true"
            break
        fi
    done

    # console colors:
    if [ "${use_color}" = "true" ] ; then
        RED=$( tput setaf 9 )
        GREEN=$( tput setaf 10 )
        YELLOW=$( tput setaf 11 )
        BLUE=$( tput setaf 12 )
        # shellcheck disable=SC2034
        MAGENTA=$( tput setaf 13 )
        CYAN=$( tput setaf 14 )
        NORMAL=$( tput op )
    else
        RED=""
        YELLOW=""
        GREEN=""
        BLUE=""
        # shellcheck disable=SC2034
        MAGENTA=""
        CYAN=""
        NORMAL=""
    fi

    local my_tty
    my_tty=$( tty )
    if [[ "${my_tty}" =~ 'not a tty' ]] ; then
        my_tty='-'
    fi

}
detect_color

#------------------------------------------------------------------------------
my_date() {
    date +'%F %T.%N %:::z'
}

#------------------------------------------------------------------------------
debug() {
    if [[ "${VERBOSE}" != "y" ]] ; then
        return 0
    fi
    echo -e " * [$(my_date)] [${BASENAME}:${BLUE}DEBUG${NORMAL}]: $*" >&2
}

#------------------------------------------------------------------------------
info() {
    if [[ "${QUIET}" == "y" ]] ; then
        return 0
    fi
    if [[ "${VERBOSE}" == "y" ]] ; then
        echo -e " ${GREEN}*${NORMAL} [$(my_date)] [${BASENAME}:${GREEN}INFO${NORMAL}] : $*"
    else
        echo -e " ${GREEN}*${NORMAL} $*"
    fi
}

#------------------------------------------------------------------------------
warn() {
    if [[ "${VERBOSE}" == "y" ]] ; then
        echo -e " ${YELLOW}*${NORMAL} [$(my_date)] [${BASENAME}:${YELLOW}WARN${NORMAL}] : $*" >&2
    else
        echo -e " ${YELLOW}*${NORMAL} [${BASENAME}:${YELLOW}WARN${NORMAL}] : $*" >&2
    fi
}

#------------------------------------------------------------------------------
error() {
    if [[ "${VERBOSE}" == "y" ]] ; then
        echo -e " ${RED}*${NORMAL} [$(my_date)] [${BASENAME}:${RED}ERROR${NORMAL}]: $*" >&2
    else
        echo -e " ${RED}*${NORMAL} [${BASENAME}:${RED}ERROR${NORMAL}]: $*" >&2
    fi
}

#------------------------------------------------------------------------------
description() {
    cat <<-EOF
	Updates the Python virtual environment.

	EOF

}

#------------------------------------------------------------------------------
line() {
    if [[ "${QUIET}" == "y" ]] ; then
        return 0
    fi
    echo "---------------------------------------------------"
}

#------------------------------------------------------------------------------
empty_line() {
    if [[ "${QUIET}" == "y" ]] ; then
        return 0
    fi
    echo
}

#------------------------------------------------------------------------------
usage() {

    cat <<-EOF
	Usage: ${BASENAME} [-d|--debug] [[-v|--verbose] | [-q|--quiet]] [--nocolor]
	       ${BASENAME} [-h|--help]
	       ${BASENAME} [-V|--version]

	    Options:
	        -d|--debug      Debug output (bash -x).
	        -v|--verbose    Set verbosity on.
	        -q|--quiet      Quiet execution. Mutually exclusive to --verbose.
	        --nocolor       Don't use colors on display.
	        -h|--help       Show this output and exit.
	        -V|--version    Prints out version number of the script and exit.

	EOF

}

#------------------------------------------------------------------------------
get_options() {

    local tmp=
    local short_options="dvqhV"
    local long_options="debug,verbose,quiet,nocolor,help,version"

    set +e
    tmp=$( getopt -o "${short_options}" --long "${long_options}" -n "${BASENAME}" -- "$@" )
    ret="$?"
    if [[ "${ret}" != 0 ]] ; then
        echo "" >&2
        usage >&2
        exit 1
    fi
    set -e

    # Note the quotes around `$TEMP': they are essential!
    eval set -- "${tmp}"

    while true ; do
        case "$1" in
            -d|--debug)
                DEBUG="y"
                shift
                ;;
            -v|--verbose)
                VERBOSE="y"
                shift
                ;;
            -q|--quiet)
                QUIET="y"
                RED=""
                YELLOW=""
                GREEN=""
                BLUE=""
                CYAN=""
                NORMAL=""
                shift
                ;;
            --nocolor)
                RED=""
                YELLOW=""
                GREEN=""
                BLUE=""
                CYAN=""
                NORMAL=""
                shift
                ;;
            -h|--help)
                description
                echo
                usage
                exit 0
                ;;
            -V|--version)
                echo "${BASENAME} version: ${VERSION}"
                exit 0
                ;;
            --) shift
                break
                ;;
            *)  echo "Internal error!"
                exit 1
                ;;
        esac
    done

    if [[ "${DEBUG}" = "y" ]] ; then
        set -x
    fi

    if [[ "${VERBOSE}" == "y" && "${QUIET}" == "y" ]] ; then
        error "Options '${RED}--verbose${NORMAL}' and '${RED}--quiet${NORMAL}' are mutually exclusive."
        echo >&2
        usage >&2
        exit 1
    fi

    if type -t jq >/dev/null ; then
        :
    else
        echo -e "Command '${RED}jq${NORMAL}' not found, please install package '${YELLOW}jq${NORMAL}' or appropriate." >&2
        exit 6
    fi

    if [[ "${VERBOSE}" == "y" ]] ; then
        PIP_OPTIONS="--verbose"
    elif [[ "${QUIET}" == "y" ]] ; then
        PIP_OPTIONS="--quiet --quiet"
    else
        PIP_OPTIONS="--quiet"
    fi

}

#------------------------------------------------------------------------------
RM() {

    local cmd="rm"
    if [[ "${VERBOSE}" == "y" ]] ; then
        cmd+=" --verbose"
    fi
    debug "Executing: ${cmd} $*"
    # shellcheck disable=SC2086,SC2294
    eval ${cmd} "$@"

}

#------------------------------------------------------------------------------
init_venv() {

    local py_version=
    local python=
    local found="n"

    empty_line
    line
    info "Preparing and using virtual environment '${CYAN}${VENV}${NORMAL}' …"
    empty_line


    if [[ ! -f "${VENV}/bin/activate" ]] ; then
        if [[ -d "${VENV}" ]] ; then
            info "Removing '${CYAN}${VENV}${NORMAL}' …"
            RM --recursive "${VENV}"
        fi
        found="n"
        for py_version in "${VALID_PY_VERSIONS[@]}" ; do
            python="python${py_version}"
            debug "Testing Python binary '${CYAN}${python}${NORMAL}' …"
            if type -t "${python}" >/dev/null ; then
                found="y"
                empty_line
                info "Found '${GREEN}${python}${NORMAL}'."
                empty_line
                "${python}" -m venv "${VENV}"
                break
            fi
        done
        if [[ "${found}" == "n" ]] ; then
            empty_line >&2
            error "Did not found a usable Python version." >&2
            error "Usable Python versions are: ${YELLOW}${VALID_PY_VERSIONS[*]}${NORMAL}." >&2
            empty_line >&2
            exit 5
        fi
    fi

    # shellcheck disable=SC1091
    . "${VENV}/bin/activate" || exit 5

}

#------------------------------------------------------------------------------
upgrade_pip() {
    empty_line
    line
    info "Upgrading ${CYAN}PIP${NORMAL} …"
    empty_line
    # shellcheck disable=SC2086
    pip install ${PIP_OPTIONS} --upgrade --upgrade-strategy eager pip
    empty_line
}

#------------------------------------------------------------------------------
upgrade_fb_tools() {
    empty_line
    line
    info "Install or upgrade ${CYAN}fb-tools${NORMAL} …"
    empty_line
    # shellcheck disable=SC2086
    pip install ${PIP_OPTIONS} --upgrade --upgrade-strategy eager fb-tools
    empty_line

}

#------------------------------------------------------------------------------
install_mandatory_packages() {
    empty_line
    line
    info "Installing all ${CYAN}mandatory packages${NORMAL} …"
    empty_line

    local -a pkgs=()
    local pkg
    local cmd

    oifs="${IFS}"
    IFS="
"
    for pkg in $( config-convert pyproject.toml -T json | jq -r .project.dependencies[] ) ; do
        pkgs+=( "${pkg}" )
    done
    IFS="${oifs}"

    if [[ "${#pkgs[*]}" -ge 1 ]] ; then
        debug "Mandatory packages: ${CYAN}${pkgs}${NORMAL}"
        cmd="pip install ${PIP_OPTIONS} --upgrade --upgrade-strategy eager"
        for pkg in "${pkgs[@]}" ; do
            cmd+=" \"${pkg}\""
        done
        debug "Executing: ${cmd}"
        # shellcheck disable=SC2086
        eval ${cmd}
    else
        info "Did not found any mandatory packages."
    fi
}

#------------------------------------------------------------------------------
install_additional_package_group() {

    local group
    group="$1"

    empty_line
    info "Installing packages of additional group ${CYAN}${group}${NORMAL} …"

    local -a pkgs=()
    local pkg
    local cmd
    local oifs

    oifs="${IFS}"
    IFS="
"
    for pkg in $( config-convert pyproject.toml -T json | jq -r ".project.\"optional-dependencies\".\"${group}\"[]" ) ; do
        pkgs+=( "${pkg}" )
    done
    IFS="${oifs}"

    if [[ "${#pkgs[*]}" -ge 1 ]] ; then
        debug "Packages of group ${CYAN}${group}${NORMAL}: ${CYAN}${pkgs}${NORMAL}"
        cmd="pip install ${PIP_OPTIONS} --upgrade --upgrade-strategy eager"
        for pkg in "${pkgs[@]}" ; do
            cmd+=" \"${pkg}\""
        done
        debug "Executing: ${cmd}"
        # shellcheck disable=SC2086
        eval ${cmd}
    else
        info "Did not found any packages for group ${CYAN}${group}${NORMAL}.."
    fi
}

#------------------------------------------------------------------------------
install_additional_packages() {

    empty_line
    line
    info "Installing all ${CYAN}additional packages${NORMAL} …"
    empty_line

    local groups
    local group

    groups=""
    for group in $( config-convert pyproject.toml -T json | jq -r '.project."optional-dependencies" | keys[]' ) ; do
        if [[ -n "${groups}" ]] ; then
            groups+=" "
        fi
        groups+="${group}"
    done

    if [[ -n "${groups}" ]] ; then
        for group in ${groups} ; do
            install_additional_package_group ${group}
        done
    fi

}

#------------------------------------------------------------------------------
upgrade_modules() {
    local packages=''
    local package=''

    empty_line
    line
    info "Installing and/or upgrading necessary modules …"
    empty_line
    packages=$( pip3 list --outdated --exclude-editable --format json 2>/dev/null  | jq -r .[].name )

    if [[ -n "${packages}" ]] ; then
        msg="Packages to update:"
        for package in ${packages} ; do
            msg+="\n * ${CYAN}${package}${NORMAL}"
        done
        info "${msg}"
        empty_line
        # shellcheck disable=SC2086
        pip install ${PIP_OPTIONS} --upgrade --upgrade-strategy eager ${packages}
        empty_line
    else
        info "No packages to update found."
    fi

}

#------------------------------------------------------------------------------
list_modules() {
    if [[ "${QUIET}" == "y" ]] ; then
        return 0
    fi
    empty_line
    line
    info "Installed modules:"
    empty_line
    pip list --format columns
    empty_line
}

#------------------------------------------------------------------------------
compile_i18n() {

    if [[ -x compile-xlate-msgs.sh ]]; then
        empty_line
        line
        info "Updating i18n files in ${BASE_DIR} …"
        empty_line
        ./compile-xlate-msgs.sh
        empty_line
    fi
}

################################################################################
##
## Main
##
################################################################################

#------------------------------------------------------------------------------
main() {

    get_options "$@"
    init_venv
    upgrade_pip
    upgrade_fb_tools
    install_mandatory_packages
    install_additional_packages
    upgrade_modules
    list_modules
    compile_i18n

    line
    info "Fertig."
    empty_line

}

main "$@"

exit 0

# vim: ts=4 list
