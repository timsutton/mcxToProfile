# PlistToProfile

## Overview

PlistToProfile is a simple command-line utility to create "Custom Settings" Configuration Profiles without the need for the Profile Manager service in Lion Server. It can take input from property list files on disk or directly from a Directory Services node (Local MCX or Open Directory).

Administrators who would like to move from MCX-based management to Profiles may find this tool useful to speed up the process of migrating and testing. Currently it only supports the "Custom Settings" type, as this seems to be the functional equivalent of key-value domain management in Workgroup Manager.

PlistToProfile should function on OS X 10.5 or greater, though it's been mostly only tested on Lion. It also makes use of Greg Neagle's FoundationPlist library from the Munki project, which provides native plist support via the PyObjC bridge framework.

## Example usage

Here's an example:

`./PlistToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs`

This will create a .mobileconfig file in the same directory, which is equivalent to a "Custom Settings" profile configured in the Profile Manager web application included in Lion Server.

Here's another example, which will import an already-configured MCX preference defined in an available Directory Services computer object:

`./PlistToProfile.py --dsobject /LDAPv3/od.my.org/ComputerGroups/StandardPreferences --identifier MyBasePreferences`

The `--dsobject` option should work with objects defined in either a LocalMCX or standard Open Directory node on another server. This hasn't been tested with MCX attributes in OpenLDAP or Active Directory.

## Plist input options:

### Once/Often/Always management

One downside to the Profile Manager web GUI is that it does not provide a mechanism to choose the "management frequency" of an MCX-set preference, such as "Once" or "Often". It was discovered very recently (again, by Greg Neagle) that it's possible to regain that functionality, by slightly altering the contents of the .mobileconfig file to match the MCX XML as when created in Workgroup Manager:

- for "Often" behaviour, use the 'Set-Once' key instead of 'Forced' for a domain
- for "Once" behaviour, do this and set an mcx_data_timestamp alongside the mcx_preference_settings which is an NSDate

PlistToProfile provides the same functionality:

`./PlistToProfile.py --plist /path/to/a/plist --identifier MyApplicationPrefs --manage Often`

When using the `--dsobject` option, the `--manage` option isn't used, as this information is already defined in the object.

### Domains

Plist files used for application preferences are typically named by a reverse-domain format, and end in '.plist'. Currently, PlistToProfile will assume that the name portion of the plist file _is_ the domain to be used by MCX. In other words, application preferences won't function if you use something like `--plist my.orgs.office.2011.prefs.plist`, because it will assemble the profile to use the domain 'my.orgs.office.2011.prefs'. If you have collections of default preferences you would like to manage for various applications and system settings, it's best to store these settings in the properly-named plist files.

## Payload Identifiers

The only option required besides `--plist` or `--dsobject` is an identifier. The identifier is crucial: it is what is defined in the toplevel payload's PayloadIdentifier key, and is what would be used to identify the profile to remove using `profiles -R -p [identifier]`. Also, if you attempt to install a profile with the same identifier, it will update the existing profile instead of installing another profile. The newer version could have completely different payloads and a different toplevel PayloadUUID, but it will still replace it.

As far as I can tell, two profiles with unique toplevel PayloadIdentifiers but matching toplevel PayloadUUIDs will both install successfully. PlistToProfile will always generate unique UUIDs for the toplevel and nested payloads, but because the PayloadIdentifier has to be paid attention to, it's required to manually specify it.

To reduce the chances of human error when updating existing profiles, I plan to add an alternate option, ie. `--identifier-from-profile`, that would take a path to a previously-built profile and use its PayloadIdentifier.

## Other functionality

- Multiple plists can be defined (with `--plist` or `-p`) and they will be combined as individual payloads within the Configuration Profile
- It can be specified whether a profile is allowed to be removed using `--removal-allowed` or `-r`
- An organization name for the profile can be specified using `--organization` or `-g`
- A specific output filename for the .mobileconfig file can be specified using `--output` or `-o`

## To-do

- support for ByHost preferences with the `--plist` option (detecting either '.ByHost' or a hardware UUID string in the .plist file name)
- option to take a path to an existing profile to specify the identifier, rather than requiring the name explicitly
- remove duplicate code in the PayloadDict class methods

## Note

I really do not have much experience with Configuration Profiles, and this is a rough first pass at a generic tool that I knew would help me understand better how Configuration Profiles actually work. There may well be fundamental design changes in how this tool should work to make it useful for others, so I welcome anyone's feedback/suggestions/pull requests. Special thanks to Greg Neagle for some very useful intial feedback, and for adding the MCX functionality.