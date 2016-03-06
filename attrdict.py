class AttrDict(dict):
	"""
	Dictionary where d.attr == d["attr"].
	Keys are case-insensitive as well.
	Actual attributes may exist but must begin with at least one underscore (_).
	c._a will fail if _a is not an attribute,
	but c.a will return None if a is not defined.
	Special adaptation: c.chanid and c.channelid are equal.
	"""
	def __getattr__(self, fieldname):
		try: return self.__getitem__(fieldname)
		except KeyError:
			if fieldname.startswith("_"): raise AttributeError(fieldname)
			try:
				if fieldname == "channelid": return self.__getitem__("chanid")
				if fieldname == "chanid": return self.__getitem__("channelid")
			except KeyError: return None
			return None

	def __setattr__(self, fieldname, fieldval):
		# Fields don't begin with underscores, but internal attributes do.
		if fieldname.startswith("_"):
			dict.__setattr__(self, fieldname, fieldval)
			return
		# Anything else sets a field.
		if fieldval is None:
			try: self.__delitem__(fieldname)
			except KeyError: pass
			return
		if fieldname == "channelid" and "chanid" in self: fieldname = "chanid"
		elif fieldname == "chanid" and "channelid" in self: fieldname = "channelid"
		self.__setitem__(fieldname, fieldval)

	def get(self, k):
		k = k.lower()
		if self.has_key(k): return dict.get(self, k)
		if k == "chanid": k = "channelid"
		elif k == "channelid": k = "chanid"
		return dict.get(self, k)

	def pop(self, k, d=None):
		k = k.lower()
		if self.has_key(k): return dict.pop(self, k)
		if k == "chanid": k = "channelid"
		elif k == "channelid": k = "chanid"
		return dict.pop(self, k, d)

	def __delattr__(self, fieldname):
		if fieldname.lower() in self:
			return dict.__delitem__(self, fieldname.lower())
		return dict.__delattr__(self, fieldname.lower())

	def __delitem__(self, k):
		k = k.lower()
		try: return dict.__delitem__(self, k)
		except KeyError: pass
		if k == "chanid": k = "channelid"
		elif k == "channelid": k = "chanid"
		return dict.__delitem__(self, k)

	def __getitem__(self, fieldname):
		try: return dict.__getitem__(self, fieldname.lower())
		except KeyError:
			k = fieldname.lower()
			if k == "channelid": k = "chanid"
			elif k == "chanid": k = "channelid"
		try: return dict.__getitem__(self, k)
		except KeyError: raise

	def __setitem__(self, fieldname, fieldval):
		return dict.__setitem__(self, fieldname.lower(), fieldval)
