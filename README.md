# mcxToProfile

## Overview

mcxToProfile is a simple command-line utility to create "Custom Settings" Configuration Profiles without the need for the Profile Manager Device Management service in OS X Server 10.7 and 10.8. It can take input from property list files on disk or directly from a Directory Services node (Local MCX or Open Directory).

Administrators who would like to move from MCX-based management to Profiles may find this tool useful to speed up the process of migrating and testing. Currently it only supports the "Custom Settings" type, as this seems to be the functional equivalent of key-value domain management in Workgroup Manager.

mcxToProfile should function on OS X 10.5 or greater. It also makes use of Greg Neagle's FoundationPlist library from the Munki project, which provides native plist support via PyObjC. FoundationPlist is licensed under the Apache License, version 2.0.

## Install instructions

* Ensure Xcode is installed on your Mac
* `git clone https://github.com/timsutton/mcxToProfile.git && cd mcxToProfile`
* `pip3 install pyobjc`
* `./mcxToProfile.py --help`

## Example usage

Here's an example:

`./mcxToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs`

This will create a .mobileconfig file in the same directory, which is equivalent to a "Custom Settings" profile configured in the Profile Manager web application included in Lion Server.

The `--plist` option can be specified multiple times:

`./mcxToProfile.py --plist com.microsoft.office.plist --plist com.microsoft.autoupdate2.plist --identifier Office2011Prefs --manage Once`

Here's another example, which will import an already-configured MCX preference defined in an available Directory Services computer object:

`./mcxToProfile.py --dsobject /LDAPv3/od.my.org/ComputerGroups/StandardPreferences --identifier MyBasePreferences`

The `--dsobject` option should work with objects defined in either a LocalMCX or standard Open Directory node on another server. This hasn't been tested with MCX attributes in OpenLDAP or Active Directory.

## Plist input options:

### Once/Often/Always management

One downside to the Profile Manager web GUI is that it does not provide a mechanism to choose the "management frequency" of an MCX-set preference, such as "Once" or "Often". It was discovered (again, by Greg Neagle) that it's possible to regain that functionality, by slightly altering the contents of the .mobileconfig file to match the MCX XML as when created in Workgroup Manager:

- for "Often" behaviour, use the 'Set-Once' key instead of 'Forced' for a domain
- for "Once" behaviour, do this and set an mcx_data_timestamp alongside the mcx_preference_settings which is an NSDate

mcxToProfile provides the same functionality:

`./mcxToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs --manage Once`

When using the `--dsobject` option, the `--manage` option is ignored, as this information is already defined in the MCX object pulled from the DS node.

**Note:** It's [been documented](https://osxbytes.wordpress.com/2015/02/25/profile-behavior-changes-in-yosemite) that in OS X Yosemite, the behaviour for the "Often"-equivalent can lead to undesirable results when the profile is installed, so mcxToProfile now discourages the use of "Often." Thanks to [Eric Holtam](https://twitter.com/eholtam) and [Patrick Fergus](https://twitter.com/foigus) for documentation of this issue.

### Domains

Plist files used for application preferences are typically named by a reverse-domain format, and end in '.plist'. Currently, mcxToProfile will assume that the name portion of the plist file _is_ the domain to be used by MCX. In other words, application preferences won't function if you use something like `--plist my.orgs.office.2011.prefs.plist`, because it will assemble the profile to use the domain 'my.orgs.office.2011.prefs'. If you have collections of default preferences you would like to manage for various applications and system settings, it's best to store these settings in the properly-named plist files.

### ByHost preferences

A plist that contains one of the following patterns in its filename will automatically be configured as a ByHost preference:

- com.org.app.ByHost.plist (the literal string '.ByHost')
- com.org.app.001122aabbcc.plist (a 12-hex-digit MAC address)
- com.org.app.01234567-89AB-CDEF-0123-456789ABCDEF.plist (a hardware UUID)


## Payload Identifiers

The only option required besides `--plist` or `--dsobject` is `--identifier`. The identifier is crucial: it is what is defined in the toplevel payload's PayloadIdentifier key, and is what would be used to identify the profile to remove using `profiles -R -p [identifier]`.

If you attempt to install a profile with the same identifier, it will update the existing profile instead of installing another profile.

Specify an identifier using either the `--identifier` or `--identifier-from-profile` options. If one is building an updated version of a profile, it's strongly recommended to use `--identifier-from-profile` to guarantee a consistent identifier and UUID.

Two profiles with unique toplevel PayloadIdentifiers but matching toplevel PayloadUUIDs will both install successfully. However, Profile Manager maintains consistent UUIDs, so we aim to do the same (although currently only at the top-level).


## Other functionality

- Multiple plists can be defined (with `--plist` or `-p`) and they will be combined as individual payloads within the Configuration Profile
- A profile can be made "Always removable" using `--removal-allowed` or `-r` (default is "Never removable")
- An organization name for the profile can be specified using `--organization` or `-g`
- A specific output filename for the .mobileconfig file can be specified using `--output` or `-o`

## To-do

- add status output and a verbose mode
- append '.mobileconfig' to filename if not already specified
- potentially 'convert' known existing preference types (loginwindow, dock, etc.) into their native payload types, rather than as Custom Settings payloads. This may not be able to ever cover all cases as some key names have changed from 10.6.

## Acknowledgments

Special thanks to Greg Neagle for some very useful intial feedback, and for adding the --dsimport functionality.
