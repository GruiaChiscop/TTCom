# Note:

This is not my work; the author of this program is [Doug lee](http://dlee.org), and should be acorded all legal  rights, bla, bla, bla. I will, however, probably be updating and restructuring it, and all such modifications will of course be self-documenting in the git history. You can find the official TTCom page, as well as downloads and a nice write up of it's history [here](http://dlee.org/TTCom/).

# TTCom
This is TTCom, the TeamTalk Commander, also informally referred to as
the TeamTalk Console.

This file is current as of revision 652 of TTCom.

## Usage

Install Python 2.5 or later, but not 3.x, if not already done on your OS.

Copy ttcom_default.conf to ttcom.conf and edit to taste. This is where
servers and per-server behaviors are defined. The autoLogin parameter
determines which servers connect automatically on TTCom startup.

Run TTCom by running ttcom.py through Python 2.x:

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