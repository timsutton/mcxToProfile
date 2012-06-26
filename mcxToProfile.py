#!/usr/bin/python

# mcxToProfile.py
# Simple utility to assist with creating Custom Settings Configuration Profiles
# from plist files and Directory Services nodes

import sys
import os
import optparse
import subprocess
import re
from uuid import uuid4
from Foundation import NSDate
import FoundationPlist


class PayloadDict:
    """Class to create and manipulate Configuration Profiles.
    The actual plist content can be accessed as a dictionary via the 'data' attribute.
    """
    def __init__(self, identifier, removal_allowed=False, organization=''):
        self.data = {}
        self.data['PayloadVersion'] = 1
        self.data['PayloadOrganization'] = organization
        self.data['PayloadUUID'] = makeNewUUID()
        if removal_allowed:
            self.data['PayloadRemovalDisallowed'] = False
        else:
            self.data['PayloadRemovalDisallowed'] = True
        self.data['PayloadType'] = 'Configuration'
        self.data['PayloadScope'] = 'System'
        self.data['PayloadDescription'] = "Included custom settings:\n"
        self.data['PayloadDisplayName'] = "MCXToProfile: "
        self.data['PayloadIdentifier'] = identifier

        # An empty list for 'sub payloads' that we'll fill later
        self.data['PayloadContent'] = []

    def _addPayload(self, payload_content_dict):
        """Add a Custom Settings payload to the profile. Takes a dict which will be the
        PayloadContent dict within the payload. Handles the boilerplate, naming and descriptive
        elements.
        """
        domains = payload_content_dict.keys()
        if len(domains) == 1:
            domain = domains[0]
        else:
            domain = 'multiple preference domains'

        payload_dict = {}
        # Boilerplate
        payload_dict['PayloadVersion'] = 1
        payload_dict['PayloadUUID'] = makeNewUUID()
        payload_dict['PayloadEnabled'] = True
        payload_dict['PayloadType'] = 'com.apple.ManagedClient.preferences'
        payload_dict['PayloadIdentifier'] = "%s.%s.alacarte.customsettings.%s" % (
                                            'MCXToProfile', self.data['PayloadUUID'], payload_dict['PayloadUUID'])

        # Add our actual MCX/Plist content
        payload_dict['PayloadContent'] = payload_content_dict

        # Update the top-level descriptive info
        self.data['PayloadDescription'] += '\n'.join(domains)
        self.data['PayloadDisplayName'] += domain

        # Add to the profile's PayloadContent array
        self.data['PayloadContent'].append(payload_dict)

    def addPayloadFromPlistContents(self, plist_dict, domain, manage, is_byhost=False):
        """Add one plist dict contents to the profile's payloads. domain is the
        preferences domain (ie. com.apple.finder), manage is one of 'Once', 'Often' or 'Always',
        and is_byhost is a boolean representing whether the preference is to be used as a ByHost.
        """

        payload_dict = {}

        # Frequency to apply settings, or 'state'
        if manage == 'Always':
            state = 'Forced'
        else:
            state = 'Set-Once'

        if is_byhost:
            domain += '.ByHost'

        # Yet another nested dict for the actual contents
        payload_dict[domain] = {}
        payload_dict[domain][state] = []
        payload_dict[domain][state].append({})
        payload_dict[domain][state][0]['mcx_preference_settings'] = plist_dict

        # Add a datestamp if we're managing 'Once'
        if manage == 'Once':
            now = NSDate.new()
            payload_dict[domain][state][0]['mcx_data_timestamp'] = now

        self._addPayload(payload_dict)

    def addPayloadFromMCX(self, mcxdata):
        """Add MCX data to the profile's payloads.
        """
        # MCX is already 'configured', we just need to add the dict to the payload
        self._addPayload(mcxdata)


def makeNewUUID():
    return str(uuid4())


def errorAndExit(errmsg):
    print >> sys.stderr, errmsg
    exit(-1)


def getDomainFromPlist(plist_path_or_name):
    """Assuming the domain is also the name of the plist file, strip the path and the ending '.plist'"""
    domain_info = {}
    domain_info['is_byhost'] = False

    # Match a domain ending in .ByHost, the Ethernet MAC, or the Hardware UUID
    byhost_pattern = re.compile('\.ByHost$|\.[0-9a-fA-F]{12}$|\.[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')

    plist_file_name = os.path.basename(plist_path_or_name).split('.plist')[0]
    byhost_match = re.search(byhost_pattern, plist_file_name)
    if byhost_match:
        domain_info['is_byhost'] = True
        domain_info['name'] = '.'.join(plist_file_name.split('.')[0:-1])
    else:
        domain_info['name'] = plist_file_name

    return domain_info


def getMCXData(ds_object):
    '''Returns a dictionary representation of dsAttrTypeStandard:MCXSettings
    from the given DirectoryServices object'''
    ds_object_parts = ds_object.split('/')
    ds_node = '/'.join(ds_object_parts[0:3])
    ds_object_path = '/' + '/'.join(ds_object_parts[3:])
    cmd = ['/usr/bin/dscl', '-plist', ds_node, 'read', ds_object_path,
           'dsAttrTypeStandard:MCXSettings']
    proc = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (pliststr, err) = proc.communicate()
    if proc.returncode:
        errorAndExit("dscl error: %s" % err)
    # decode plist string returned by dscl
    try:
        mcx_dict = FoundationPlist.readPlistFromString(pliststr)
    except FoundationPlist.FoundationPlistException:
        errorAndExit(
            "Could not decode plist data from dscl:\n" % pliststr)
    # mcx_settings is a plist encoded inside the plist!
    try:
        mcx_data_plist = mcx_dict['dsAttrTypeStandard:MCXSettings'][0]
    except KeyError:
        errorAndExit("No mcx_settings in %s:\n%s" % (ds_object, pliststr))
    except IndexError:
        errorAndExit(
            "Unexpected mcx_settings format in %s:\n%s" % (ds_object, pliststr))
    # decode the embedded plist
    mcx_data = FoundationPlist.readPlistFromString(str(mcx_data_plist))
    return mcx_data['mcx_application_data']


def getIdentifierFromProfile(profile_path):
    profile_dict = FoundationPlist.readPlist(profile_path)
    try:
        profile_id = profile_dict['PayloadIdentifier']
    except:
        errorAndExit("Can't find a ProfileIdentifier in the profile at %s." % profile_path)
    return profile_id


def main():
    parser = optparse.OptionParser()
    parser.set_usage(
        """usage: %prog [--dsobject DSOBJECT | --plist PLIST] 
                       [--identifier IDENTIFIER | --identifier-from-profile PATH] [options]
       One of '--dsobject' or '--plist' must be specified, and only one identifier option.
       Run '%prog --help' for more information.""")

    # Required options
    parser.add_option('--dsobject', '-d', metavar='DSOBJECT',
        help="""Directory Services object from which to convert MCX data.
Examples: /Local/Default/Computers/foo
          /LDAPv3/some_ldap_server/ComputerGroups/bar""")
    parser.add_option('--plist', '-p', action="append", metavar='PLIST_FILE',
        help="""Path to a plist to be added as a profile payload.
Can be specified multiple times.""")
    parser.add_option('--identifier', '-i',
        action="store",
        help="""Top-level payload identifier. This is used to uniquely identify a profile.
A profile can be removed using this identifier using the 'profiles' command and the '-R -p' options.""")
    parser.add_option('--identifier-from-profile', '-f',
        action="store",
        metavar="PATH",
        help="""Path to an existing .mobileconfig file from which to copy the identifier,
as opposed to specifying it with the --identifier option.""")

    # Optionals
    parser.add_option('--removal-allowed', '-r',
        action="store_true",
        default=False,
        help="""Specifies that the profile can be removed.""")
    parser.add_option('--organization', '-g',
        action="store",
        default="",
        help="Cosmetic name for the organization deploying the profile.")
    parser.add_option('--output', '-o',
        action="store",
        metavar='PATH',
        help="Output path for profile. Defaults to 'identifier.mobileconfig' in the current working directory.")

    # Plist-specific
    plist_options = optparse.OptionGroup(parser,
        title="Plist-specific options",
        description="""These options are useful only in conjunction with --plist.
If multiple plists are supplied, they are applied to all, not on a
per-plist basis.""")

    parser.add_option_group(plist_options)

    plist_options.add_option('--manage', '-m',
        action="store",
        help="Management frequency - Once, Often or Always. Defaults to Always.")

    options, args = parser.parse_args()

    if len(args):
        parser.print_usage()
        sys.exit(-1)

    if options.dsobject and options.plist:
        parser.print_usage()
        errorAndExit("Error: The '--dsobject' and '--plist' options are mutually exclusive.")

    if options.dsobject and options.manage:
        print options.manage
        parser.print_usage()
        errorAndExit("Error: The '--manage' option is used only in conjunction with '--plist'. DS Objects already contain this information.")

    if (not options.identifier and not options.identifier_from_profile) or \
    (options.identifier and options.identifier_from_profile):
        parser.print_usage()
        sys.exit(-1)

    if options.identifier:
        identifier = options.identifier
    elif options.identifier_from_profile:
        if not os.path.exists(options.identifier_from_profile):
            errorAndExit("Error reading a profile at path %s" % options.identifier_from_profile)
        identifier = getIdentifierFromProfile(options.identifier_from_profile)

    if options.plist:
        if not options.manage:
            manage = 'Always'
        else:
            manage = options.manage

    if options.output:
        output_file = options.output
    else:
        output_file = os.path.join(os.getcwd(), identifier + '.mobileconfig')

    newPayload = PayloadDict(identifier=identifier,
        removal_allowed=options.removal_allowed,
        organization=options.organization)

    if options.plist:
        for plist_path in options.plist:
            source_data = FoundationPlist.readPlist(plist_path)
            source_domain = getDomainFromPlist(plist_path)
            newPayload.addPayloadFromPlistContents(source_data,
                source_domain['name'],
                manage,
                is_byhost=source_domain['is_byhost'])
    if options.dsobject:
        mcx_data = getMCXData(options.dsobject)
        newPayload.addPayloadFromMCX(mcx_data)

    FoundationPlist.writePlist(newPayload.data, output_file)


if __name__ == "__main__":
    main()
