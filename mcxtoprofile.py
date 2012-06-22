#!/usr/bin/python

# mcxtoprofile.py
# Simple utility to assist with creating Profiles from 
# MCX in Directory Service items
# Based on PlistToProfile by Tim Sutton.

import sys
import os
import optparse
import subprocess
from uuid import uuid4
from Foundation import NSDate
import FoundationPlist

class PayloadDict:
    """Class to represent the complete plist contents of a Configuration Profile (.mobileconfig) file"""
    def __init__(self, identifier, removal_allowed, organization):
        self.data = {}
        self.data['PayloadVersion'] = 1
        self.data['PayloadOrganization'] = organization
        self.data['PayloadUUID'] = makeNewUUID()
        if removal_allowed == 'Always':
            self.data['PayloadRemovalDisallowed'] = False
        elif removal_allowed == 'Never':
            self.data['PayloadRemovalDisallowed'] = True
        self.data['PayloadType'] = 'Configuration'
        self.data['PayloadScope'] = 'System'
        self.data['PayloadDescription'] = "Included custom settings:\n"
        self.data['PayloadDisplayName'] = "MCXToProfile: "
        self.data['PayloadIdentifier'] = identifier

        # An empty list for 'sub payloads' that we'll fill later
        self.data['PayloadContent'] = []

    def addMCXPayload(self, mcxdata):
        """Add MCX data to the profile's payloads.
        """
        domains = mcxdata.keys()
        if len(domains) == 1:
            domain = domains[0]
        else:
            domain = 'multiple preference domains'
        payload_dict = {}
        # Boilerplate
        payload_dict['PayloadVersion'] = 1
        payload_dict['PayloadUUID'] = makeNewUUID()
        payload_dict['PayloadEnabled'] = True
        payload_dict['PayloadDisplayName'] = "Settings for %s" % domain
        payload_dict['PayloadType'] = 'com.apple.ManagedClient.preferences'
        payload_dict['PayloadIdentifier'] = "%s.%s.alacarte.customsettings.%s" % (
                                            'MCXToProfile', self.data['PayloadUUID'], payload_dict['PayloadUUID'])
        # Yet another nested dict for the actual contents
        payload_dict['PayloadContent'] = mcxdata
                                            

        # Update the top-level descriptive info
        self.data['PayloadDescription'] += '/n'.join(domains)
        self.data['PayloadDisplayName'] += domain
        # add nested payload to top-level payload
        self.data['PayloadContent'].append(payload_dict)

def makeNewUUID():
    return str(uuid4())


def errorAndExit(errmsg):
    print >> sys.stderr, errmsg
    exit(-1)


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


def main():
    parser = optparse.OptionParser()
    parser.set_usage(
        'usage: %prog --dsobject DSOBJECT --identifier IDENTIFIER [options]')
    parser.add_option('--dsobject', '-d', metavar='DSOBJECT', 
        help="""Directory Services object from which to convert MCX data.
Examples: /Local/Default/Computers/foo  
          /LDAPv3/some_ldap_server/ComputerGroups/bar""")
    parser.add_option('--removal-allowed', '-r', 
        action="store", 
        default="Never", 
        help="""Specifies when the profile can be removed. Currently supported options are 'Never' and 'Always', 
and defaults to 'Never'""")
    parser.add_option('--organization', '-g', 
        action="store", 
        default="",
        help="Cosmetic name for the organization deploying the profile.")
    parser.add_option('--output', '-o', 
        action="store", 
        metavar='PATH', 
        help="Output path for profile. Defaults to 'identifier.mobileconfig' in the current working directory.")
    parser.add_option('--identifier', '-i', 
        action="store", 
        help="""Payload identifier. This is used to uniquely identify a profile.
A profile can be removed using this identifier using the 'profiles' command and the '-R -p' options.""")
    options, args = parser.parse_args()

    if len(args):
        parser.print_usage()
        sys.exit(-1)
        
    if not options.identifier or not options.dsobject:
        parser.print_usage()
        sys.exit(-1)

    if options.output:
        output_file = options.output
    else:
        output_file = os.path.join(os.getcwd(), options.identifier + '.mobileconfig')

    newPayload = PayloadDict(identifier=options.identifier, 
                             removal_allowed=options.removal_allowed,
                             organization=options.organization)
    
    mcx_data = getMCXData(options.dsobject)
    newPayload.addMCXPayload(mcx_data)
    FoundationPlist.writePlist(newPayload.data, output_file)


if __name__ == "__main__":
    main()