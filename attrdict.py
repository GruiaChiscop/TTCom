class AttrDict(dict):
	"""
	Dictionary where d.attr == d["attr"].
	Keys are case-insensitive as well.
	Actual attributes may exist but must begin with at least one underscore (_).
	c._a will fail if _a is not an attribute,
	but c.a will return None if a is not defined.
	"""
	def __getattr__(self, fieldname):
		try: return self.__getitem__(fieldname)
		except KeyError:
			if fieldname.startswith("_"): raise AttributeError(fieldname)
			if fieldname == "channelid": return self.__getattr__("chanid")
			if fieldname == "chanid": return self.__getattr__("channelid")
			return None

	def __setattr__(self, fieldname, fieldval):
		# Fields don't begin with underscores, but internal attributes do.
		if fieldname.startswith("_"):
			dict.__setattr__(self, fieldname, fieldval)
		# Anything else sets a field.
		else:
			if fieldval is None:
				try: self.__delitem__(fieldname)
				except KeyError: pass
			else:
				self.__setitem__(fieldname, fieldval)

	def __delattr__(self, fieldname):
		if fieldname.lower() in self:
			return dict.__delitem__(self, fieldname.lower())
		return dict.__delattr__(self, fieldname.lower())

	def __getitem__(self, fieldname):
		return dict.__getitem__(self, fieldname.lower())

	def __setitem__(self, fieldname, fieldval):
		return dict.__setitem__(self, fieldname.lower(), fieldval)
