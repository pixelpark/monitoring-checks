#!/bin/bash
# shellcheck disable=SC2317  # Don't warn about unreachable commands in this file
#

set -e
set -u

VERBOSE=""
DEBUG=""

VERSION="0.3"

BASENAME=$(basename "${0}" )
BASE_DIR=$( dirname "$0" )
cd "${BASE_DIR}"
BASE_DIR=$( readlink -f . )

TRUSTED_ANCHORS_FILE="dnssec-trust-anchors.key"

# DIG Options
DNSSEC=
SERVER=
ZONE=
WARN=$(( 7 * 24 * 60 * 60 ))
CRIT=$(( 5 * 24 * 60 * 60 ))

#------------------------------------------------------------------------------
description() {
    cat <<-EOF
	Checks the validity of the given DNS zone by retrieving the SOA for this zone.

	If the option --dnssec is given, additionally the DNSSEC RRSIG of the SOA is
	checked for its existence and its remaining livetime.

	The thresholds may be given as integers of seconds, or as minutes with the suffix 'm',
	as hours with the suffix 'h', as days with the suffix 'd' or as weeks with the suffix 'w'.

	EOF

}

#------------------------------------------------------------------------------
usage() {

    cat <<-EOF
	Usage: ${BASENAME} [-d|--debug] [-v|--verbose] [-D|--dnssec] [-s|--server NAMESERVER] [-w|--warn WARNING_TIME] [-c|--crit CRITICAL_TIME} -z|--zone ZONE
	       ${BASENAME} [-h|--help]
	       ${BASENAME} [-V|--version]

	    Options:
	        -d|--debug      Debug output (bash -x).
	        -v|--verbose    Set verbosity on.
	        -D|--dnssec     Check the DNSSEC RRDS of the SOA of the zone.
	        -s|--server NAMESERVER
	                        The nameserver to use for checking the zone.
	                        If omitted, one arbitrary nameserver from /etc/resolv.conf is used.
	        -w|--warn WARNING_TIME
	                        The threshold for warning about the remaining livetime of the RRSIG.
	                        Not used, if --dnssec was not given.
	                        Default: ${WARN} seconds.
	        -c|--crit CRITICAL_TIME
	                        The threshold for critical about the remaining livetime of the RRSIG.
	                        Not used, if --dnssec was not given.
	                        Default: ${CRIT} seconds.
	        -z|--zone ZONE  The zone to check. Mandatory option.
	        -h|--help       Show this output and exit.
	        -V|--version    Prints out version number of the script and exit.

	EOF

}

#------------------------------------------------------------------------------
timespec () {
    if [[ "${1}" =~ ^[0-9]+[mhdw]?$ ]] ; then
        :
    else
        echo "UNKNOWN ${BASENAME}: Invalid time spec '${1}' given." >&2
        exit 3
    fi

    case $1 in
        *m)
            echo "$(( ${1/m/} * 60))"
            ;;
        *h)
            echo "$(( ${1/h/} * 60 * 60 ))"
            ;;
        *d)
            echo "$(( ${1/d/} * 60 * 60 * 24 ))"
            ;;
        *w)
            echo "$(( ${1/w/} * 7 * 60 * 60 * 24 ))"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

#------------------------------------------------------------------------------
seconds2human() {

    local seconds_total="$1"
    local out=""

    local seconds=$(( seconds_total % 60 ))
    local minutes_total=$(( seconds_total / 60 ))
    local minutes=$(( minutes_total % 60 ))
    local hours_total=$(( minutes_total / 60 ))
    local hours=$(( hours_total % 24 ))
    local days=$(( hours_total / 24 ))

    if [[ "${days}" -gt 0 ]] ; then
        out="${days}d ${hours}h ${minutes}m ${seconds}s"
    elif [[ "${hours}" -gt 0 ]] ; then
        out="${hours}h ${minutes}m ${seconds}s"
    elif [[ "${minutes_total}" -gt 0 ]] ; then
        out="${minutes}m ${seconds}s"
    else
        out="${seconds}s"
    fi

    echo "${out}"

}

#------------------------------------------------------------------------------
get_options() {

    local tmp=
    local short_options="dvDs:z:w:c:hV"
    local long_options="debug,verbose,dnssec,server:,zone:,warn:,crit:,help,version"

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
            -D|--dnssec)
                DNSSEC="y"
                shift
                ;;
            -s|--server)
                SERVER="$2"
                shift
                shift
                ;;
            -w|--warn)
                WARN=$( timespec "$2" )
                shift
                shift
                ;;
            -c|--crit)
                CRIT=$( timespec "$2" )
                shift
                shift
                ;;
            -z|--zone)
                ZONE="$2"
                shift
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

    if [[ -z "${ZONE}" ]] ; then
        echo "UNKNOWN - ${BASENAME}: No zone was given."
        echo
        usage
        exit 3
    fi

    if [[ "${WARN}" -lt "${CRIT}" ]] ; then
        echo "UNKNOWN - ${BASENAME}: The warning threshold (${WARN} seconds) is less than the critical threshold (${CRIT} seconds), which is weird."
        exit 3
    fi

}

#------------------------------------------------------------------------------
check_soa_with_dig() {
    local cmd
    local response
    local server
    local msg

    cmd="dig \"${ZONE}\" "

    if [[ -n "${SERVER}" ]] ; then
        cmd+="\"@${SERVER}\" "
    fi

    cmd+="SOA +nocomments +noadditional +nocmd +noquestion"

    if [[ "${VERBOSE}" ]] ; then
        echo "Executing: ${cmd}" >&2
    fi
    # shellcheck disable=disable=SC2086,SC2294
    response=$( eval ${cmd} )
    if [[ "${VERBOSE}" ]] ; then
        echo -e "Response:\n${response}" >&2
    fi

    server=$( echo "${response}" | grep -P -i '^;; SERVER:')
    server="${server/;; SERVER: /}"

    if echo "${response}" | grep -P -q -i "^${ZONE}\\.\\s.*\\ssoa\\s" ; then
        echo "OK - ${BASENAME}: Found SOA of zone '${ZONE}', as observed on server ${server}."
        exit 0

    fi

    echo "CRITICAL - ${BASENAME}: Did not found SOA of zone '${ZONE}', as observed on server ${server}."
    exit 2

}

#------------------------------------------------------------------------------
check_soa_with_delv() {

    local cmd
    local response
    local request_status
    local signing_status
    local rrsig_record
    local rrsig
    local remaining
    local msg
    local remaining_out
    local warn_out
    local crit_out

    cmd="delv \"${ZONE}\" "

    if [[ -n "${SERVER}" ]] ; then
        cmd+="\"@${SERVER}\" "
    fi

    cmd+="SOA +yaml"

    if [[ -f "${TRUSTED_ANCHORS_FILE}" ]] ; then
        cmd+=" -a \"${TRUSTED_ANCHORS_FILE}\""
    fi

    if [[ "${VERBOSE}" ]] ; then
        echo "Executing: ${cmd}" >&2
    fi
    # shellcheck disable=disable=SC2086,SC2294
    response=$( eval ${cmd} )
    if [[ "${VERBOSE}" ]] ; then
        echo -e "Response:\n${response}" >&2
    fi

    shopt -s extglob
    request_status=$( echo "${response}" | grep '^status:' )
    request_status="${request_status/#status: /}"
    request_status="${request_status,,}"
    if [[ "${VERBOSE}" ]] ; then
        echo "Request status: ${request_status}" >&2
    fi

    if [[ "${request_status}" != 'success' ]] ; then
        msg="DNS Zone '${ZONE}' does not exists or could not retrieved: ${request_status}"
        echo "CRITICAL - ${BASENAME}: ${msg}"
        exit 2
    fi

    signing_status=$( echo "${response}" | grep -A 1 '^records:' | tail -n 1 )
    signing_status="${signing_status/#+( )- /}"
    signing_status="${signing_status/%:/}"
    signing_status="${signing_status,,}"
    if [[ "${VERBOSE}" ]] ; then
        echo "Signing status: ${signing_status}" >&2
    fi

    if [[ "${signing_status}" != 'fully_validated' ]] ; then
        msg="DNS Zone '${ZONE}' is not signed: ${signing_status}"
        echo "CRITICAL - ${BASENAME}: ${msg}"
        exit 2
    fi

    if echo "${response}" | grep -P -q -i "'${ZONE}\\.\\s.*\\sRRSIG\\s" ; then
        :
    else
        echo "CRITICAL - ${BASENAME}: Missing RRSIG response for SOA of '${ZONE}'."
        exit 2
    fi

    rrsig_record=$( echo "${response}" | grep -P -i "'${ZONE}\\.\\s.*\\sRRSIG\\s" | head -n 1 )
    rrsig_record="${rrsig_record/#+( )- \'/}"
    rrsig_record="${rrsig_record/%\'/}"
    if [[ "${VERBOSE}" ]] ; then
        echo "RRSIG record: ${rrsig_record}" >&2
    fi

    rrsig=( $( echo "${rrsig_record}" | grep -P -i '\s+IN\s+RRSIG\s+SOA\s+') )
    remaining=$(( $(date --utc --date="${rrsig[8]:0:4}-${rrsig[8]:4:2}-${rrsig[8]:6:2} ${rrsig[8]:8:2}:${rrsig[8]:10:2}:${rrsig[8]:12:2}" +%s) - $(date --utc +%s) ))

    remaining_out=$( seconds2human "${remaining}" )
    warn_out=$( seconds2human "${WARN}" )
    crit_out=$( seconds2human "${CRIT}" )

    if [[ "${VERBOSE}" ]] ; then
        echo -e "Remaining: ${remaining_out}" >&2
    fi

    if [[ -z "${remaining}" ]] ; then
        msg="Could not find RRSIG of SOA or the signature expiration for zone '${ZONE}'."
        echo "CRITICAL - ${BASENAME}: ${msg}"
        exit 2
    fi

    if [[ "${remaining}" -lt 0 ]] ; then
        msg="Signatures in zone '${ZONE}' expired ${remaining} seconds ago."
        echo "CRITICAL - ${BASENAME}: ${msg}"
        exit 2
    fi

    if [[ "${remaining}" -lt "${CRIT}" ]] ; then
        msg="Remaining signature validity for zone '${ZONE}' is in ${remaining_out}, less than the critical threshold of ${crit_out}."
        echo "CRITICAL - ${BASENAME}: ${msg}"
        exit 2
    fi

    if [[ "${remaining}" -lt "${WARN}" ]] ; then
        msg="Remaining signature validity for zone '${ZONE}' is ${remaining_out}, less than the warning threshold of ${warn_out}."
        echo "WARNING - ${BASENAME}: ${msg}"
        exit 1
    fi

    msg="Remaining signature validity for zone '${ZONE}' is ${remaining} seconds (${remaining_out})."

    echo "OK - ${BASENAME}: ${msg}"
    exit 0

}

################################################################################
##
## Main
##
################################################################################

#------------------------------------------------------------------------------
main() {

    get_options "$@"

    if [[ "${DNSSEC}" ]] ; then
        check_soa_with_delv
    else
        check_soa_with_dig
    fi

}

main "$@"


exit 0

# vim: ts=4 list
