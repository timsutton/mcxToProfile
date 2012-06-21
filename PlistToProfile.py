#!/usr/bin/python

# PlistToProfile.py
# Simple utility to assist with creating Profiles from generic plists

import os
import argparse
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
        self.data['PayloadDisplayName'] = "PlistToProfile: "
        self.data['PayloadIdentifier'] = identifier

        # An empty list for 'sub payloads' that we'll fill later
        self.data['PayloadContent'] = []

    def addPayload(self, plist_dict, domain, manage):
        """Add one plist dict contents to the profile's payloads. 'domain' is the preferences domain (ie. com.apple.finder),
and 'manage' is one of 'Once', 'Often' or 'Always'.
        """
        payload_dict = {}
        # Boilerplate
        payload_dict['PayloadVersion'] = 1
        payload_dict['PayloadUUID'] = makeNewUUID()
        payload_dict['PayloadEnabled'] = True
        payload_dict['PayloadDisplayName'] = "Settings for %s" % domain
        payload_dict['PayloadType'] = 'com.apple.ManagedClient.preferences'
        payload_dict['PayloadIdentifier'] = "%s.%s.alacarte.customsettings.%s" % (
                                            'PlistToProfile', self.data['PayloadUUID'], payload_dict['PayloadUUID'])

        # Update the top-level descriptive info
        self.data['PayloadDescription'] += "%s\n" % domain
        self.data['PayloadDisplayName'] += "%s, " % domain

        # Frequency to apply settings, or 'state'
        if manage == 'Always':
            state = 'Forced'
        else:
            state = 'Set-Once'

        # Yet another nested dict for the actual contents
        payload_dict['PayloadContent'] = {}
        payload_dict['PayloadContent'][domain] = {}
        payload_dict['PayloadContent'][domain][state] = []
        payload_dict['PayloadContent'][domain][state].append({})
        payload_dict['PayloadContent'][domain][state][0]['mcx_preference_settings'] = plist_dict
        # Add a datestamp if we're managing 'Once'
        if manage == 'Once':
            now = NSDate.new()
            payload_dict['PayloadContent'][domain][state][0]['mcx_data_timestamp'] = now
        self.data['PayloadContent'].append(payload_dict)


def makeNewUUID():
    return str(uuid4())


def getDomainFromPlist(plist_path_or_name):
    """Assuming the domain is also the name of the plist file, strip the path and the ending '.plist'"""
    return os.path.basename(plist_path_or_name).split('.plist')[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plist', '-p', action="append", metavar='PATH', required=True,
        help="""Path to a plist to be added as a profile payload.
Can be specified multiple times.""")
    parser.add_argument('--manage', '-m', 
        action="store", 
        default="Always", 
        help="Management frequency - Once, Often or Always. Defaults to Always.")
    parser.add_argument('--removal-allowed', '-r', 
        action="store", 
        default="Never", 
        help="""Specifies when the profile can be removed. Currently supported options are 'Never' and 'Always', 
and defaults to 'Never'""")
    parser.add_argument('--organization', '-g', 
        action="store", 
        default="",
        help="Cosmetic name for the organization deploying the profile.")
    parser.add_argument('--output', '-o', 
        action="store", 
        metavar='PATH', 
        help="Output path for profile. Defaults to 'identifier.mobileconfig' in the current working directory.")
    parser.add_argument('--identifier', '-i', 
        action="store", 
        required=True,
        help="""Payload identifier. This is what is used to uniquely identify a profile.
A profile can be removed using this identifier using the 'profiles' command and the '-R -p' options.""")
    args = parser.parse_args()

    if args.output:
        output_file = args.output
    else:
        output_file = os.path.join(os.getcwd(), args.identifier + '.mobileconfig')

    newPayload = PayloadDict(identifier=args.identifier, 
        removal_allowed=args.removal_allowed,
        organization=args.organization)
    for plist_path in args.plist:        
        source_data = FoundationPlist.readPlist(plist_path)
        source_domain = getDomainFromPlist(plist_path)
        newPayload.addPayload(source_data, source_domain, args.manage)

    FoundationPlist.writePlist(newPayload.data, output_file)


if __name__ == "__main__":
    main()
