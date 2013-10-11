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
from Foundation import NSData, \
                       NSPropertyListSerialization, \
                       NSPropertyListMutableContainers, \
                       NSPropertyListXMLFormat_v1_0


class PayloadDict:
    """Class to create and manipulate Configuration Profiles.
    The actual plist content can be accessed as a dictionary via the 'data' attribute.
    """
    def __init__(self, identifier, uuid=False, removal_allowed=False, organization='', displayname=''):
        self.data = {}
        self.data['PayloadVersion'] = 1
        self.data['PayloadOrganization'] = organization
        if uuid:
            self.data['PayloadUUID'] = uuid
        else:
            self.data['PayloadUUID'] = makeNewUUID()
        if removal_allowed:
            self.data['PayloadRemovalDisallowed'] = False
        else:
            self.data['PayloadRemovalDisallowed'] = True
        self.data['PayloadType'] = 'Configuration'
        self.data['PayloadScope'] = 'System'
        self.data['PayloadDescription'] = "Included custom settings:\n"
        self.data['PayloadDisplayName'] = displayname
        self.data['PayloadIdentifier'] = identifier

        # store git commit for reference if possible
        self.gitrev = None
        root_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        if '.git' in os.listdir(root_dir):
            git_p = subprocess.Popen('git rev-parse HEAD',
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True,
                                    cwd=root_dir)
            out, err = git_p.communicate()
            if not git_p.returncode:
                self.gitrev = out.strip()

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
            self.data['PayloadDescription'] += "%s\n" % domain
        else:
            domain = 'multiple preference domains'
            self.data['PayloadDescription'] += '\n'.join(domains)

        payload_dict = {}
        # Boilerplate
        payload_dict['PayloadVersion'] = 1
        payload_dict['PayloadUUID'] = makeNewUUID()
        payload_dict['PayloadEnabled'] = True
        payload_dict['PayloadType'] = 'com.apple.ManagedClient.preferences'
        payload_dict['PayloadIdentifier'] = "%s.%s.alacarte.customsettings.%s" % (
                                            'MCXToProfile', self.data['PayloadUUID'], payload_dict['PayloadUUID'])
        payload_dict['PayloadDisplayName'] = 'MCXToProfile: (%s)' % (', '.join(domains))

        # Add our actual MCX/Plist content
        payload_dict['PayloadContent'] = payload_content_dict

        # Update the top-level descriptive info
        if self.data['PayloadDisplayName'] == "MCXToProfile":
            self.data['PayloadDisplayName'] += ': ' + domain + ', '

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

    def finalizeAndSave(self, output_path):
        """Perform last modifications and save to an output plist.
        """
        if self.gitrev:
            self.data['PayloadDescription'] += "\nGit revision: %s" % self.gitrev[0:10]
        writePlist(self.data, output_path)


def makeNewUUID():
    return str(uuid4())


def errorAndExit(errmsg):
    print >> sys.stderr, errmsg
    exit(-1)


# Functions readPlist(), readPlistFromString() and writePlist(), class
# FoundationPlistException() and its subclasses borrowed with permission
# from Greg Neagle of the Munki project:
#
# http://code.google.com/p/munki
#
# The following copyright notice and license information applies to these only.
#
# Copyright 2009-2011 Greg Neagle.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""FoundationPlist.py -- a tool to generate and parse MacOSX .plist files.

This is intended as a drop-in replacement for Python's included plistlib,
with a few caveats:
    - readPlist() and writePlist() operate only on a filepath,
        not a file object.
    - there is no support for the deprecated functions:
        readPlistFromResource()
        writePlistToResource()
    - there is no support for the deprecated Plist class.

The Property List (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the writePlist(rootObject, filepath)
function. 'rootObject' is the top level object, 'filepath' is a
filename.

To parse a plist from a file, use the readPlist(filepath) function,
with a file name. It returns the top level object (again, usually a
dictionary).

To work with plist data in strings, you can use readPlistFromString()
and writePlistToString().
"""


class FoundationPlistException(Exception):
    pass


class NSPropertyListSerializationException(FoundationPlistException):
    pass


class NSPropertyListWriteException(FoundationPlistException):
    pass


def readPlist(filepath):
    """
    Read a .plist file from filepath.  Return the unpacked root object
    (which is usually a dictionary).
    """
    plistData = NSData.dataWithContentsOfFile_(filepath)
    dataObject, plistFormat, error = \
        NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                     plistData, NSPropertyListMutableContainers, None, None)
    if error:
        error = error.encode('ascii', 'ignore')
        errmsg = "%s in file %s" % (error, filepath)
        raise NSPropertyListSerializationException(errmsg)
    else:
        return dataObject


def readPlistFromString(data):
    '''Read a plist data from a string. Return the root object.'''
    plistData = buffer(data)
    dataObject, plistFormat, error = \
     NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                    plistData, NSPropertyListMutableContainers, None, None)
    if error:
        error = error.encode('ascii', 'ignore')
        raise NSPropertyListSerializationException(error)
    else:
        return dataObject


def writePlist(dataObject, filepath):
    '''
    Write 'rootObject' as a plist to filepath.
    '''
    plistData, error = \
     NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                            dataObject, NSPropertyListXMLFormat_v1_0, None)
    if error:
        error = error.encode('ascii', 'ignore')
        raise NSPropertyListSerializationException(error)
    else:
        if plistData.writeToFile_atomically_(filepath, True):
            return
        else:
            raise NSPropertyListWriteException(
                                "Failed to write plist data to %s" % filepath)

# End borrowed functions and classes from FoundationPlist.


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
    from the given DirectoryServices object. This is an array of dicts.'''
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
        mcx_dict = readPlistFromString(pliststr)
    except FoundationPlistException:
        errorAndExit(
            "Could not decode plist data from dscl:\n" % pliststr)

    # mcx_settings is a plist encoded inside the plist!
    try:
        mcx_data_plist = mcx_dict['dsAttrTypeStandard:MCXSettings']
    except KeyError:
        errorAndExit("No mcx_settings in %s:\n%s" % (ds_object, pliststr))

    mcx_data = []
    # build a list containing domains' mcx_application_data dict
    for mcx_item in mcx_data_plist:
        try:
            mcx_item = mcx_item.encode('UTF-8')
            mcx_item_data = readPlistFromString(str(mcx_item))
            mcx_data.append(mcx_item_data['mcx_application_data'])
        except KeyError:
            errorAndExit(
                "Unexpected mcx_settings format in MCXSettings array item:\n%s" % mcx_item)

    return mcx_data


def getIdentifierFromProfile(profile_path):
    """Return a tuple containing the PayloadIdentifier and PayloadUUID from the
    profile at the path specified."""
    profile_dict = readPlist(profile_path)
    try:
        profile_id = profile_dict['PayloadIdentifier']
        profile_uuid = profile_dict['PayloadUUID']
    except:
        errorAndExit("Can't find a ProfileIdentifier in the profile at %s." % profile_path)
    return (profile_id, profile_uuid)


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
        help="""Path to an existing .mobileconfig file from which to copy the identifier
and UUID, as opposed to specifying it with the --identifier option.""")

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
    parser.add_option('--displayname', '-n',
        action="store",
        default="MCXToProfile",
        help="Change PayloadDisplayName to supplied string.")

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

    if not options.dsobject and not options.plist:
        parser.print_usage()
        errorAndExit("Error: One of '--dsobject' or '--plist' must be specified.")

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
        uuid = False
    elif options.identifier_from_profile:
        if not os.path.exists(options.identifier_from_profile):
            errorAndExit("Error reading a profile at path %s" % options.identifier_from_profile)
        identifier, uuid = getIdentifierFromProfile(options.identifier_from_profile)

    if options.plist:
        if not options.manage:
            manage = 'Always'
        else:
            # ensure capitalization
            manage = options.manage[0].upper() + options.manage[1:].lower()

    if options.output:
        output_file = options.output
    else:
        output_file = os.path.join(os.getcwd(), identifier + '.mobileconfig')

    newPayload = PayloadDict(identifier=identifier,
        uuid=uuid,
        removal_allowed=options.removal_allowed,
        organization=options.organization,
        displayname=options.displayname)

    if options.plist:
        for plist_path in options.plist:
            if not os.path.exists(plist_path):
                errorAndExit("No plist file exists at %s" % plist_path)
            try:
                source_data = readPlist(plist_path)
            except FoundationPlistException:
                errorAndExit("Error decoding plist data in file %s" % plist_path)

            source_domain = getDomainFromPlist(plist_path)
            newPayload.addPayloadFromPlistContents(source_data,
                source_domain['name'],
                manage,
                is_byhost=source_domain['is_byhost'])
    if options.dsobject:
        mcx_data = getMCXData(options.dsobject)
        # Each domain in the MCX blob gets its own payload
        for mcx_domain in mcx_data:
            newPayload.addPayloadFromMCX(mcx_domain)

    newPayload.finalizeAndSave(output_file)


if __name__ == "__main__":
    main()
