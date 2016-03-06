This is TTCom, the TeamTalk Commander, also informally referred to as
the TeamTalk Console.

This file is current as of revision 651 of TTCom.

Usage:

Install Python 2.5 or later, but not 3.x, if not already done on your OS.

Install this file set somewhere convenient, unzipped.

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


TTCom is released under the GNU Public License (GPL), a copy of which
appears in LICENSE.txt. iniparse, included in its entirety, comes with
its own license (also included).

History, most recent first:

*** Version 1.1, rel 607:

TTCom works better with TeamTalk 5 servers:

- Events no longer generate errors.

- Channel membership is reported correctly.

- WhoIs works when TTCom is not logged in as an admin.

- Move, join, leave, cmsg, and several other commands work as well.

The following commands still do not work completely on TeamTalk 5
servers:

- account (list may omit fields, and add/modify will not work).
- intercept and subscribe (bits are wrong).
- op (not tested but not updated command formats).
- tt (not able to write updated file format).

The default version string is now "TTCom" instead of "4.2.0.1479."

The say command usable in triggers, when used on MacOS, now uses the
`afplay' command and a temporary file instead of piping directly
through `say' in order to avoid the speech breakup that occurs often
(at least on SnowLeopard) when the `say' command is used. This change
causes a Python warning against use of tempnam() on the first say
command call.

*** Version 1.0, rel 580:

First public release.

