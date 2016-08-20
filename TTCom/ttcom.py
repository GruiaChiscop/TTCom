#! /usr/bin/env python

"""TeamTalk Commander, the multiserver TeamTalk control client.

Author:  Doug Lee

Credits to Chris Nestrud and Simon Jaeger for some ideas and a bit
of code.  Thanks to Nick Giannak and HKC Radio for sufficient access
and support to facilitate software testing in the early stages of
this software's development.

This software is released under the GPL as of September 7, 2014; see LICENSE.txt.

Copyright (C) 2011- Doug Lee

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import sys, threading
from TTComCmd import TTComCmd
# More for command-line Python support.
import os, time

if __name__ == "__main__":
	args = sys.argv[1:]
	# Keep args out of the cmd system.
	del sys.argv[1:]
	noAutoLogins = False
	shortnames = []
	for arg in args:
		if arg == "-n":
			noAutoLogins = True
		else:
			noAutoLogins = True
			shortnames.append(arg)
	ttcom = TTComCmd(noAutoLogins, shortnames)
	ttcom.allowPython()
	if shortnames:
		cur = shortnames[-1]
		ttcom.onecmd("server " +cur)
	ttcom.run("TTCom> ", ttcom.versionString())
