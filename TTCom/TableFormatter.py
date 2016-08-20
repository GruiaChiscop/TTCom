"""Formatter of plain-text tabular data.
Given column headers and rows of cells, produces a nicely formatted text output.

Copyright (C) 2011-2016 Doug Lee

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

class TableFormatter(object):
	"""Usage:
		tbl = TableFormatter(title[, colHeaders])
		tbl.addRow(...)
		print tbl.format([gutterWidth])
	"""
	def __init__(self, title, colheaders=[]):
		self.title = title
		self.colheaders = colheaders
		self.rows = []
		self.rowcount = 0

	def addRow(self, row, excludeFromCount=False):
		self.rows.append(row)
		if not excludeFromCount:
			self.rowcount += 1

	def format(self, gutterwidth=2):
		if not len(self.rows): return self.title +":  0"
		if self.colheaders:
			widths = [len(unicode(hdr)) for hdr in self.colheaders]
		elif len(self.rows):
			widths = [len(unicode(cell)) for cell in self.rows[0]]
		for row in self.rows:
			for i,cell in enumerate(row):
				widths[i] = max(widths[i], len(unicode(cell)))
		gutter = " " * gutterwidth
		result = "%s (%d):\n" % (self.title, self.rowcount)
		lmargin = "    "
		allRows = []
		if self.colheaders: allRows.append(self.colheaders)
		allRows.extend(self.rows)
		for row in allRows:
			fields = []
			for i,cell in enumerate(row):
				fmt = "%-" +unicode(widths[i]) +"s"
				fields.append( fmt % (cell))
			result += lmargin +gutter.join(fields) +"\n"
		return result

