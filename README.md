# TTCom
This is TTCom, the TeamTalk Commander, also informally referred to as the TeamTalk Console or the TTCom text client.

This repository is current with Revision 852, released February 11, 2018 (version 2.0.1).

This release of TTCom includes source code and a Windows stand-alone executable so that it may be run on Windows without requiring Python to
be installed.


## Note

This is not my work; the author of this program is [Doug lee](http://dlee.org), and should be acorded all legal  rights, bla, bla, bla. I will, however, probably be updating and restructuring it, and all such modifications will of course be self-documenting in the git history. You can find the official TTCom page, as well as downloads and a nice write up of it's history [here](http://dlee.org/TTCom/).  
The revision number above is Doug's version control system, whatever that may be; if I make major changes to the code I'll keep them in a different branch, so master is always the upstream code.

## Usage

If running from source on Windows or if your OS does not include Python already, install Python 2.7. Possible sources of Python 2.7 include
- http://www.activestate.com/activepython (preferred by this author for Windows)
- http://www.python.org/

Install this file set somewhere convenient, unzipped.

Copy ttcom_default.conf to ttcom.conf and edit to taste. This is where servers and per-server behaviors are defined. The autoLogin parameter determines which servers connect automatically on TTCom startup.
This author recommends setting a nickname for all servers at once by including something like this in ttcom.conf:

```
[server defaults]
nickname=My Name
```

If you don't do this, you will be called TTCom User everywhere you go.  Of course, change "My Name" above to what you want as a nickname.

If you want events to print as they occur for only the currently selected server, instead of for all connected servers, include silent=1 in the above section. See ttcom_default.conf for further ideas.

On Windows, run ttcom20.exe. If running from source (on Windows or anywhere else),

Run TTCom by running ttcom.py through Python 2.7:

    python ttcom.py

You can also specify a server or servers on the command line, by their
shortnames from ttcom.conf, to connect to just those servers:

    python ttcom.py simon

Type "?" or "help" at the TTCom command prompt to learn what is
possible. You can add a command name for help on that command; e.g.,
"?whoIs." Case is not important in command names.


## License
TTCom is released under the GNU Public License (GPL), a copy of which
appears in the 'LICENSE' file. iniparse, included in its entirety, comes with
its own license (also included).

## Changelog

History, most recent first:

### Revision 852, released February 11, 2018 (version 2.0.1)
* New channel command. So far, the only implemented subcommand is list, which can list channels with varying detail and can filter the set of channels listed by many means. Warning though: There are still problems with this command on servers with non-ASCII characters in channel names.
* Commands that operate on channels, such as cmsg, allow channel matching by specific TeamTalk parameter. One use of this is to message a channel by its id:

```
cmsg chanid=5 Hello
```

* Various updates to the account command:
  * Fixed a bug that caused user rights on an account add command to be set to 0 when the user type was given as a number (1 or 2). The following command will list any accounts on a server affected by this bug:

```
acc li userrights=0
```

and the following command will set rights for account Doug to the default values:

```
acc mod Doug userrights=259591
```
  * Passwords do not print unless a -pargument is specified.
  * Added a Rights column to the Account List table. Currently rights are shown as an integer.
  * Corrections to example account deleteusage help text.
  * When not blank, the Notes for an account are shown in an Accounts table below the line for the other fields for the account.
  * -e prints all fields except passwords (use -p to add passwords), even when blank. This is useful for determining what fields are allowed for an account.
  * For long account listings (-l and -e), fields are sorted by name except for Note, which is always last.
  * Fixed a long-standing bug that broke some commands when issued on a "server ..." or ">..." line that made the command address a specific server. The issue was the introduction of extra spaces in some cases, such as (or at least) around equal signs.
  * The default name for this client when connecting to servers is now "TTCom User."
  * ttcom_defaults.conf better documents the format and capabilities of TTCom .conf files.
* For users of the python or ! commands, the name of the TTCom root object is now apprather than ttcom, for consistency with other projects.

### Revision 819, released August 8, 2017 (version 2.0)

Please read this entire section of release notes before upgrading.

This revision includes many fixes, a few new commands and features, and some changes in syntax for existing commands.

This revision also marks the official end of TeamTalk 4 support. This does not mean that TTCom will instantly stop working with TeamTalk 4 servers; it simply means that support for those servers will begin to fail as reasons arise to remove or modify the code that supports them.

New and changed commands and features:
* New Windows stand-alone executable, so you need not install Python.
* Changed the syntaxes of the following commands to add power, flexibility, and perhaps comprehensibility:
  * account.
  * ban.
  * kb.
Read the help for each of these by typing helpor ? followed by the command name. Each of these commands now has subcommands, for which help is also available.
* account add now does the following sanity checks:
  * Aborts on a duplicate existing, case significant.
  * Warns specifically if an account differing only in case exists.
  * Warns if an account exists differing only by case and/or spacing and/or punctuation.
Warnings allow the user to abort the account creation. These checks are meant to help avoid some very common administrative accidents.
* New motd command for displaying the current server's message of the day.
* The version command is now about.
* version without arguments gives the currently selected server's TeamTalk version, and with arguments gives a client's version and client name.
* Selection lists now allow all and negation via an exclamation mark (!) if multiple selections are allowed. Type help selection or ?selection for complete help on handling selection lists.
* -p option added to the vlist command for filtering by packet protocol or voice capability.
* Login and logout events that print in the TTCom window include admin for admin users and user for other users.

Fixes:
* A missing [server defaults] section no longer causes a launch-time crash.
* Deleting a file from a channel with a regular TeamTalk client no longer causes an event dispatch failure error message to print in the TTCom window. This functionality may not work on TeamTalk 4 servers.
* Fixed op, intercept, and subscribe commands to work on TeamTalk 5 servers. (The no-audio restriction remains, however, as there is still no support for audio in TTCom.)
* The summary command no longer combines multiple instances of the same user in a channel into a single entry.
* Various output formatting improvements, including better handling of unicode.
* Time reporting should work correctly for local time zones under Cygwin where it may not have before.
* The nick command is now nickname, which lets nick continue working while also letting nickname work.
* Fixed various problems with matching channel names in the join command. Channel matching now works thus:
  * Channelname and/or password can contain spaces if quoted.
  * Channel / always refers to the root channel.
  * A channel starting and ending with /must match exactly except for letter casing.
  * A channel containing a / is matched against all full channel names (path included).
  * Otherwise, the channel is matched against only the actual channel names, without paths.
Note that this command will no longer create temporary channels as it once did under TeamTalk 4.
* The Server command should properly honor any quoting on an included command.
* The rights assigned to an admin account are now consistent with TeamTalk defaults (as of TeamTalk 5.2.1.4781). This matters when an admin account is later reverted to a normal account.
* If TTCom is kicked off of a server for which autoLogin=1, the TTCom user may restart the auto-login behavior by logging in again manually.
* Some error messages are improved for clarity to end users who are not also Python coders.

### Revision 692, released August 13, 2016 (version 1.4)
* The tt command allows a target TeamTalk client version number, such as 5.1, to be specified before the name of the .tt file to create. This makes it possible to generate a tt file for a client whose version number differs from that of the current TeamTalk server.
* There is a new vlist command that summarizes users on the current server sorted by increasing version number and then by client name.
* Quote characters should work in messages sent to users or channels from TTCom.
* The say command on MacOS may work across more non-ASCII character situations.
* Temporary files for say commands are created more securely.
* When logging into a server, TTCom will print a warning for each or both of these conditions if true:
  * The server disallows multiple simultaneous logins from the same account, and/or
  * The server does not allow this user to see who is in any channel until the user joins the channel.
* The same information prints for a WhoIscommand with no arguments (i.e., a request for information on this current TTCom user login).
* TTCom itself now uses its actual version number as its version value for display by other clients, and the name "TTCom" for its clientname where supported.
* The speakEvents option is supported: Setting it makes TTCom try to speak all events that print in the TTCom window through the active screen reader. This currently requires SayTools to be installed on Windows but works natively on MacOS. To turn this feature on, type opt speakEvents 1. Use 0 instead of 1 to turn the feature off. The state of this option is saved across TTCom restarts.

### Revision 652, released November 21, 2015 (version 1.2)

This revision fixes more issues with TeamTalk 5 servers and adds a few enhancements: 
* A new version command reports the running TTCom version and other information. 
* Joining the root channel (/) works as expected. 
* The tt file should generate TT files compatible with the TeamTalk server version for which the file is being generated. 
* TTCom will keep up with channel renaming on a TeamTalk 5 server without requiring a TTCom restart. 
* Deleting bans with ban -d works. 
* The account command works on TeamTalk 5 and supports copying user rights from a chosen source account when creating a new one. To use this feature, specify an account name (or something that matches an account name) in place of the 1 or 2 normally given as a user type. To use the anonymous account as the source account for user rights, specify "" in place of the user type. The user type will become 1 and the user rights for the new account will duplicate those assigned to the source account indicated. 
* The anonymous account is more properly supported in other account scenarios; for example, acc "" reports the information for the anonymous account instead of displaying a list of all accounts. 
* It is no longer necessary to add udpport=0 to every ttcom.conf entry for TeamTalk 5 servers. TTCom no longer transmits a UDP handshake at all. (This was implemented to avoid short Windows XP client freezes on TeamTalk 4 servers, but Windows XP has long been deprecated by Microsoft.) 
* The statsAdmin command is now changed simply to stats, and the old stats command is gone. Reasons for this include:
  * The old command never worked on TeamTalk 5 servers because TeamTalk 5 does not support / commands sent to a channel.. 
  * Attempting to use the old command on a TeamTalk 5 server would run the risk of sending the string /stats visibly into the root channel even if the sending console was not there, which could startle and confuse users. 
  * The old command stopped working for non-admin users on TeamTalk 4 servers at some point. Version 1.1, rel 607:

### Revision 607, released December 20, 2014 (version 1.1)

TTCom works better with TeamTalk 5 servers:

* Events no longer generate errors.
* Channel membership is reported correctly.
* WhoIs works when TTCom is not logged in as an admin.
* Move, join, leave, cmsg, and several other commands work as well.

The following commands still do not work completely on TeamTalk 5
servers:

* account (list may omit fields, and add/modify will not work).
* intercept and subscribe (bits are wrong).
* op (not tested but not updated command formats).
* tt (not able to write updated file format).

Other changes in this release: 

* The default version string is now "TTCom" instead of "4.2.0.1479."
* The say command usable in triggers, when used on MacOS, now uses the `afplay' command and a temporary file instead of piping directly through `say' in order to avoid the speech breakup that occurs often (at least on SnowLeopard) when the `say' command is used. This change causes a Python warning against use of tempnam() on the first say command call.

### Revision 580, released September 7, 2014 (version 1.0)
First public release.