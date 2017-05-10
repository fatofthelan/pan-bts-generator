#!/usr/bin/python

# Written by: George Watkins <gwatkins@paloaltonetworks.com>
# Updated: 2017-04-24

import optparse
import os
import re
import csv
import requests

# Create the command line options parser and parse command line
cmdl_usage = 'usage: %prog [options] CSV_FILE'
cmdl_version = '0.0.2'
cmdl_parser = optparse.OptionParser(usage=cmdl_usage, version=cmdl_version, conflict_handler='resolve')
cmdl_parser.add_option('-h', '--help', action='help', help='print this help text and exit')
cmdl_parser.add_option('-v', '--version', action='version', help='print program version and exit')
cmdl_parser.add_option('-d', '--build-dir', dest='build_dir', metavar='DIR', help='build output directory, default: ./build')
cmdl_parser.add_option('-l', '--lic-api-key', dest='lic_api_key', metavar='API_KEY', help='licensing server API key')
cmdl_parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='activates quiet mode')
(cmdl_opts, cmdl_args) = cmdl_parser.parse_args()

# Validation regex's
IP_ADDR_TYPE_REGEX = '^(static|dhcp-client)$'
IPV4_ADDR_REGEX = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.' \
                  '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.' \
                  '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.' \
                  '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
IPV6_ADDR_REGEX = '^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|' \
                  '([0-9a-fA-F]{1,4}:){1,7}:|' \
                  '([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|' \
                  '([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|' \
                  '([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|' \
                  '([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|' \
                  '([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|' \
                  '[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|' \
                  ':((:[0-9a-fA-F]{1,4}){1,7}|:)|' \
                  'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|' \
                  '::(ffff(:0{1,4}){0,1}:){0,1}' \
                  '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
                  '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|' \
                  '([0-9a-fA-F]{1,4}:){1,4}:' \
                  '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
                  '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))' \
                  '(/([0-9]{1,2}|1[0-1][0-9]|12[0-8]))?$'
IP_ADDR_REGEX = '%s|%s' % (IPV4_ADDR_REGEX, IPV6_ADDR_REGEX)
HOSTNAME_REGEX = '^[-a-zA-Z0-9]{1,63}$'
FQDN_REGEX = '^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}' \
             '[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}' \
             '[0-9A-Za-z])?)*\.?$'
TPL_DG_NAME_REGEX = '^[a-zA-Z0-9][-_.a-zA-Z0-9]{1,30}$'
OP_CMDS_REGEX = '^(multi-vsys|jumbo-frame|mgmt-interface-swap)(\s*,?\s*(?!\1)' \
                '(multi-vsys|jumbo-frame|mgmt-interface-swap))*$'
YES_NO_REGEX = '^(yes|no)$'
BTS_FIELD_REGEXS = {
        'type': IP_ADDR_TYPE_REGEX,
        'ip-address': IPV4_ADDR_REGEX,
        'default-gateway': IPV4_ADDR_REGEX,
        'netmask': IPV4_ADDR_REGEX,
        'ipv6-address': IPV6_ADDR_REGEX,
        'ipv6-default-gateway': IPV6_ADDR_REGEX,
        'hostname': HOSTNAME_REGEX,
        'panorama-server': IP_ADDR_REGEX,
        'panorama-server-2': IP_ADDR_REGEX,
        'tplname': TPL_DG_NAME_REGEX,
        'dgname': TPL_DG_NAME_REGEX,
        'dns-primary': IP_ADDR_REGEX,
        'dns-secondary': IP_ADDR_REGEX,
        'op-command-modes': OP_CMDS_REGEX,
        'dhcp-send-hostname': YES_NO_REGEX,
        'dhcp-send-client-id': YES_NO_REGEX,
        'dhcp-accept-server-hostname': YES_NO_REGEX,
        'dhcp-accept-server-domain': YES_NO_REGEX
        }

# Global constants
DEFAULT_BUILD_DIR = 'build'
BUILD_SUB_DIRS = [ 'config', 'content', 'license', 'software' ]
BTS_FIELDS = [
        'type', 'ip-address', 'default-gateway', 'netmask',
        'ipv6-address', 'ipv6-default-gateway', 'hostname',
        'panorama-server', 'panorama-server-2', 'tplname', 'dgname',
        'dns-primary', 'dns-secondary', 'op-command-modes',
        'dhcp-send-hostname', 'dhcp-send-client-id',
        'dhcp-accept-server-hostname', 'dhcp-accept-server-domain'
        ]
LIC_API_URL = 'https://api.paloaltonetworks.com/api/license/activate'
LIC_FILE_SUFFIXES = {
        'AutoFocus Device License': 'canary',
        'BrightCloud URL Filtering': 'url',
        'Decryption Port Mirror': 'decrypt',
        'GlobalProtect Gateway': 'gpgateway',
        'GlobalProtect Portal': 'gpportal',
        'PA-VM': 'pa-vm',
        'PAN-DB URL Filtering': 'url3',
        'Threat Prevention': 'threats',
        'Virtual Systems': 'vsys',
        'WildFire License': 'wildfire'
        }

def get_build_dir():
    if cmdl_opts.build_dir:
        return cmdl_opts.build_dir
    else:
        return DEFAULT_BUILD_DIR

def build_dir_struct():
    build_dir = get_build_dir()

    if not cmdl_opts.quiet:
        print 'INFO: Building bootstrap directory structure in \'%s\'' % build_dir

    try:
        if not os.path.exists(build_dir):
            os.mkdir('%s' % build_dir)
    except Exception, e:
        print 'ERROR: %s' % str(e)

    for dir in BUILD_SUB_DIRS:
        try:
            sub_dir = '%s/%s' % (build_dir, dir)
            if not os.path.exists(sub_dir):
                os.mkdir(sub_dir)
        except Exception, e:
            print 'ERROR: %s' % str(e)

def validate_bts_fields(fields):
    valid = True

    for key, value in fields.items():
        if value:
            if not key in BTS_FIELDS:
                valid = False
                print 'ERROR: \'%s\' is not a valid init-cfg parameter' % key
                break
            if not bool(re.search(BTS_FIELD_REGEXS[key], value)):
                valid = False
                print 'ERROR: \'%s\' is not a valid value for init-cfg parameter \'%s\'' % (value, key)
                break

    return valid

def create_init_cfg(serial, fields):
    build_dir = get_build_dir()
    init_cfg_file = '%s/config/%s-init-cfg.txt' % (build_dir, serial)

    try:
        with open(init_cfg_file, 'w+') as init_cfg_file:
            for field in BTS_FIELDS:
                init_cfg_file.write('%s=%s\n' % (field, fields[field]))
    except Exception, e:
        print 'ERROR: %s' % str(e)

def retrieve_licenses(api_key, serial):
    header = { 'apikey': api_key }
    data = { 'serialNumber': serial }

    return requests.post(LIC_API_URL, data=data, headers=header).json()

def create_licenses(serial, licenses):
    build_dir = get_build_dir()

    for license in licenses:
        if license['typeField'] in ('SUB', 'RENSUB'):
            feature = LIC_FILE_SUFFIXES[license['featureField']]
            key = license['keyField']

            try:
                with open('%s/license/%s-%s.key' % (build_dir, serial, feature), 'w+') as lic_key_file:
                    if not cmdl_opts.quiet:
                        print 'INFO: Got \'%s\' license for serial \'%s\'' % (license['featureField'], serial)

                    lic_key_file.write(key)
            except Exception, e:
                print 'ERROR: %s' % str(e)

def csv_row_to_dict(csv_row):
    init_cfg_dict = {}

    for idx, col in enumerate(csv_row):
        if idx > 0:
            init_cfg_dict[BTS_FIELDS[idx - 1]] = col

    return init_cfg_dict

def process_csv_row(row):
    serial = row[0]

    if not cmdl_opts.quiet:
        print 'INFO: Building config for serial \'%s\'' % serial

    init_cfg_dict = csv_row_to_dict(row)

    if validate_bts_fields(init_cfg_dict):
        create_init_cfg(serial, init_cfg_dict)

        if cmdl_opts.lic_api_key:
            if not cmdl_opts.quiet:
                print 'INFO: Retrieving licenses for serial \'%s\'' % serial

            licenses = retrieve_licenses(cmdl_opts.lic_api_key, serial)


            if license is dict and 'Message' in licenses.keys():
                print 'ERROR: %s' % licenses['Message']
            else:
                create_licenses(serial, licenses)

def main():
    try:
        csv_file = cmdl_args[0]
    except IndexError:
        print 'ERROR: no CSV file specified. Exiting...'
        exit(1)

    build_dir_struct()

    try:
        with open(csv_file, 'rb') as file:
            reader = csv.reader(file)

            for line_num, row in enumerate(reader):
                if line_num > 0:
                    process_csv_row(row)
    except Exception, e:
        print 'ERROR: %s' % str(e)

if __name__== "__main__":
    main()
