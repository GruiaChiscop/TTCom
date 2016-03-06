#! /usr/bin/env python

"""TeamTalk Commander, the multiserver TeamTalk control client.

Author:  Doug Lee
Copyright 2011-2014 Doug Lee

Credits to Chris Nestrud and Simon Jaeger for some ideas and a bit
of code.  Thanks to Nick Giannak and HKC Radio for sufficient access
and support to facilitate software testing in the early stages of
this software's development.

This software is released under the GPL as of September 7, 2014; see LICENSE.txt.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
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
	ttcom.run("TTCom> ", "TeamTalk Commander version 1.1")
