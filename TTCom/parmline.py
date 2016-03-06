"""ParmLine - an object for managing dual-format parameter lines.
Lines can come in as a text line, an event and parameters, or a mixture.

Copyright (C) 2011-2015 Doug Lee

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

import re
from attrdict import AttrDict

class ParmLine(object):
	"""A dual-format parameter/line object.
	Construct with a line and parameters or just a line.
	Access .line for the raw text or .event and .parms for the broken-out version.
	.initLine and .initParms are what was passed to the constructor.
	Caveats:
		- Parameters in line may be reordered from what was passed.
		- This class does not handle duplicate parameter names on a line.
	"""

	def __init__(self, line, parms={}):
		"""Set up a line.
		Line is an event name with possible key=value parameters after it.
		parms is a dict of parameters and may be empty.
		If parms includes parameters that are also in line, parms governs.
		"""
		self.initLine = line
		line = str(line)
		self.initParms = AttrDict(parms)
		line,parms1 = self.splitline(line)
		parms1.update(parms)
		self.event = line
		self.parms = parms1
		self.line = self.makeline(self.event, self.parms)

	def __hash__(self):
		"""For sets.
		"""
		return hash(self.event +" ".join(self.parms) +self.line)

	def __eq__(self, other):
		"""Implements ==.
		"""
		return (self.event == other.event
		and self.parms == other.parms
		and self.line == other.line
		)
	def __ne__(self, other):
		"""Makes comparison for equality work reasonably.
		"""
		return not self.__eq__(other)

	def splitline(self,  line):
		"""Split one line up into its command keyword and its parameters.
		Returns event,parms, where parms is an AttrDict.
		Rules honored and allowed in input lines:
			- Values containing spaces are quoted with "".
			- A quote is escaped with a backslash.
			- A backslash is escaped by being doubled.
			- Unquoted space separates parameters.
			- The first parameter is a keyword with no value assignment.
			- All other parameters are of the form keyword=value.
		"""
		event = None
		parms = AttrDict()
		parm = ""
		quoting = False
		line = line.strip() +" "
		linelen = len(line)
		i = 0
		while i < linelen:
			ch = line[i]
			i += 1
			if ch == '"':
				quoting = not quoting
				continue
			if ch == '\\' and i < linelen-1:
				ch = line[i]
				i += 1
			if quoting or not ch.isspace():
				parm += ch
				continue
			# A parameter has ended.
			if event:
				if not parm: continue
				try: k,v = parm.split("=", 1)
				except ValueError:
					print "Parameter format error: %s, line: %s" % (parm, line)
					raise
				parms[k] = v
			else:
				event = parm
			parm = ""
		return event,parms

	def makeline(self, event, parms):
		"""Build a line from event name and parms.
		Inverse of splitline().
		"""
		line = self._fixParm(event)
		for k,v in parms.items():
			line += " %s=" % (self._fixParm(k))
			v = str(v)
			v = self._fixParm(v, True)
			if v.isdigit():
				line += v
			else:
				line += '"' +v +'"'
		return line

	def _fixParm(self, parm, noQuoting=False):
		"""Fix up parms, events, etc., for makeline().
		"""
		parm = parm.replace('"', '\\"').replace('\\', '\\\\')
		return parm

	def __str__(self):
		"""Makes .line the default property in effect.
		"""
		return str(self.line)

	def __unicode__(self):
		"""Makes .line the default property in effect.
		"""
		return unicode(self.line)

	def __add__(self, other):
		return self.line +str(other)

