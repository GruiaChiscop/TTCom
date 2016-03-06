This is TTCom, the TeamTalk Commander, also informally referred to as
the TeamTalk Console.

This file is current as of revision 580 of TTCom.

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

