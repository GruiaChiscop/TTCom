"""TextBlock class for simplifying the building of formatted text blocks.
Adds an add method for conditional inclusion of named values.

Author:  Doug Lee
"""

class TextBlock(object):
	"""String with helpers for constructing output text blocks.
	"""
	def __init__(self, val=None):
		if not val: val = ""
		self._buf = val

	def add(self, name, val, sameLine=False):
		"""Helps construct text blocks.
		Name and val are a value and its name.
		sameLine indicates if this name/val pair goes on this or the next line.
		"""
		if val is None: val = ""
		val = str(val).strip()
		if not val:
			# Make sure new lines are started when requested,
			# but avoid creating blank ones for missing values.
			if not self._buf.endswith("\n") and not sameLine:
				self._buf += "\n"
			return
		# We have a value to add.
		buf = ""
		if not self._buf: buf = ""
		elif sameLine: buf += ", "
		elif not self._buf.endswith("\n"): buf += "\n"
		buf += "%s %s" % (name, val)
		self._buf += buf

	def __iadd__(self, other):
		"""Implements +=.
		"""
		self._buf += other
		return TextBlock(self._buf)

	def __str__(self):
		return str(self._buf)

	def __unicode__(self):
		return unicode(self._buf)

