# PlistToProfile

## Overview

PlistToProfile is a simple command-line utility to assemble OS X property lists (plists) into a single "Custom Settings" Configuration Profile for use with OS X 10.7 or greater. Administrators who would like to move from MCX-based management to Profiles may find this tool useful to speed up the process of migrating and testing. Currently it only supports the "Custom Settings" type, as this seems to be the functional equivalent of key-value domain management in Workgroup Manager.

PlistToProfile requires Python 2.7 or greater, which is standard on OS X Lion. It also makes use of Greg Neagle's FoundationPlist library from the Munki project, which provides native plist support via the PyObjC bridge framework.

## Example usage

Here's an example:

`./PlistToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs`

This will create a .mobileconfig file in the same directory, which is equivalent to a "Custom Settings" profile configured in the Profile Manager web application included in Lion Server.

## Once/Often/Always management

One complaint about Profile Manager is that it does not provide a mechanism to choose the "management frequency" of an MCX-set preference, such as "Once" or "Often". It was discovered very recently (again, by Greg Neagle) that it's possible to regain that functionality, by slightly altering the contents of the .mobileconfig file to match how it was defined by MCX in OS X 10.6 and earlier:

- for "Often" behaviour, use the 'Set-Once' key instead of 'Forced' for a domain
- for "Once" behaviour, do this and set an mcx_data_timestamp alongside the mcx_preference_settings which is an NSDate

PlistToProfile provides the same functionality:

`./PlistToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs --manage Often`

## Domains

Plist files used for application preferences are typically named by a reverse-domain format, and end in '.plist'. Currently, PlistToProfile will assume that the name portion of the plist file _is_ the domain to be used by MCX. In other words, application preferences won't function if you use something like `--plist my.orgs.office.2011.prefs.plist`, because it will assemble the profile to use the domain 'my.orgs.office.2011.prefs'. If you have collections of default preferences you would like to manage for various applications and system settings, it's best to store these settings in the properly-named plist files, but store _only_ these settings in the files, and nothing else.

## Payload Identifiers

The only arguments required are at least one plist, and an identifier. The identifier is crucial: it is what is defined in the toplevel payload's PayloadIdentifier key, and is what would be used to identify the profile to remove using `profiles -R -p [identifier]`. Also, if you attempt to install a profile with the same identifier, it will update the existing profile instead of installing another profile. The newer version could have completely different payloads and a different toplevel PayloadUUID, but it will still replace it.

As far as I can tell, two profiles with unique toplevel PayloadIdentifiers but matching toplevel PayloadUUIDs will both install successfully. PlistToProfile will always generate unique UUIDs for the toplevel and nested payloads, but because the PayloadIdentifier has to be paid attention to, it's required to manually specify it. To reduce the possibility of human error, I plan to add an alternate option, ie. `--identifier-from-profile`, that would take a path to a previously-built profile and use its PayloadIdentifier.

## Other functionality

- Multiple plists can be defined (with `--plist` or `-p`) and they will be combined as individual payloads within the Configuration Profile
- It can be specified whether a profile is allowed to be removed using `--removal-allowed` or `-r`
- An organization name for the profile can be specified using `--organization` or `-g`
- A specific output filename for the .mobileconfig file can be specified using `--output` or `-o`

## Note

I really do not have much experience with Configuration Profiles, and this is a rough first pass at a generic tool that I knew would help me understand better how Configuration Profiles actually work. There may well be fundamental design changes in how this tool should work to make it useful for others, so I welcome anyone's feedback/suggestions/pull requests.

Special thanks to Greg Neagle for some very useful intial feedback.
