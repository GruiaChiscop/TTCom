"""MyCmd, cmd wrapper with more features for console-style applications.

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

import os, sys, subprocess, time, re, shlex, tempfile
from cmd import Cmd
import threading

# For Say on Windows.
Dispatch = None
SayTools = None
try:
	import pythoncom
	from win32com.client import Dispatch
	SayTools = Dispatch("Say.Tools")
except: pass

class MyCmd(Cmd):
	"""Custom wrapper for the cmd.Cmd class.
	Initialize as for cmd.Cmd(),
	then run with .run(prompt, name).
	Optionally call .allowPython(True) to allow bang (!) Python escapes.
	Make do_*(self, line) methods to create commands.
	Override emptyline() if it should do more than just print a new prompt.
	The following commands are defined already:
		EOF, quit, exit:  Exit the interpreter. Run() returns.
		clear, cls:  Clear the screen if possible.
		errTrace: Print a traceback of the latest error encountered.
	The following utility methods are defined for easing command implementation:
		getargs: Parse line into args.
		msg: Print all passed arguments through the right output channel.
		msgNoTime: Like msg but avoids printing timestamps if otherwise printing.
		msgFromEvent: Msg version intended for asynchronous event output.
		dequote: Remove starting and ending quotes on a line if present (rarely needed).
		msgError: Msg only intended for error message output.
		confirm: Present a Yes/No confirmation prompt.
		raw_input_withoutHistory: raw_input that tries not to include its input in readline history.
		getMultilineValue:  Get a multiline value ending with "." on its own line.
		linearList:  Print a list value nicely and with a name.
			Items are sorted (case not significant) and wrapped as necessary.
			Null elements are ignored.
			A filter can be passed to avoid nulls and/or rewrite items.
		selectMatch:  Let the user pick an item from a passed list.
			A custom prompt can also be passed,
			as can a translator function for adjusting how list items sort/print.
	"""
	def allowPython(self, allow=True):
		"""Decide whether or not to allow bang (!) Python escapes, for
		evaluating expressions and executing statements from the command line.
		"""
		if allow:
			self.do_python = self._do_python
		else:
			try: del self.do_python
			except: pass

	def _fixLine(self, line, doHelp):
		"""Helper for precmd that handles both commands and help requests.
		"""
		if not line:
			return line
		elif line[0] == "!" and "do_python" in self.__dict__:
			line = "python " +line[1:]
		cmd,args,line = self.parseline(line)
		if not cmd: return line
		# TODO: cmd,line = self._translateAliases(cmd, line, doHelp)
		try:
			cmd1 = self._commandMatch(cmd)
		except (KeyError, ValueError):
			# No matches found.
			pass
		else:
			line = line.replace(cmd, cmd1, 1)
			cmd = cmd1
		if not doHelp and cmd.lower() in ["?", "help"]:
			line = line.replace(cmd, "", 1).lstrip()
			return "help " +self._fixLine(line, True)
		return line

	def precmd(self, line):
		"""Preprocessor that handles incompletely typed command names.
		Can also handle aliases.
		"""
		return self._fixLine(line, False)

	def onecmd(self, line):
		"""Wrapper for Cmd.onecmd() that handles errors.
		"""
		try:
			line = self.precmd(line)
			result = Cmd.onecmd(self, line)
			return result
		except KeyboardInterrupt:
			self.msg("Keyboard interrupt")
		except Exception as e:
			self.msg(err())
			return

	def do_EOF(self, line):
		"""Exit the program.  EOF, quit, and exit are identical.
		"""
		self.msg("Quit")
		return True

	def do_quit(self, line):
		"""Exit the program.  EOF, quit, and exit are identical.
		"""
		return self.do_EOF(line)

	def do_exit(self, line):
		"""Exit the program.  EOF, quit, and exit are identical.
		"""
		return self.do_EOF(line)

	def _do_python(self, line):
		"""Evaluate a Python expression or statement.
		Usage: python expr or python statement.
		Shorthand: !expr or !statement.
		Examples:
			!2+4
			!d = dict()
		Statements and expressions are evaluated in the context of __main__.
		"""
		result = None
		import __main__
		try: result = eval(line, __main__.__dict__)
		except SyntaxError:
			exec line in __main__.__dict__
			result = None
		self.msg(str(result))

	def do_errTrace(self, e=None):
		"""Provides a very brief traceback for the last-generated error.
		The traceback only shows file names (no paths) and line numbers.
		"""
		if not e: e = None
		print errTrace(e)

	def emptyline(self):
		"""What happens when the user presses Enter on an empty line.
		This overrides the default behavior of repeating the last-typed command.
		"""
		return False

	def do_help(self, line):
		"""Print help for the program or its commands.
		"""
		return Cmd.do_help(self, line)

	def run(self, prompt="> ", name="Command line interpreter"):
		"""Kick off the command-line interpreter.
		The command line of the program is allowed to consist of one command,
		in which case it is run and the program exits with its return code,
		or with 1 if the command returns a non-empty, non-integer value.
		Otherwise, the normal command loop is started.
		This call returns on quit/exit/EOF,
		or in the one-command-on-app-command-line case, after the command runs.
		prompt is the prompt for each line.
		name is the name for the intro ("type 'help' for help") line.
		sys.argv is processed by this call,
		so if you have something to do with it, do it before calling.
		"""
		self.plat = self._getPlatform()
		self.prompt = prompt
		args = sys.argv[1:]
		if args:
			# Do one command (without intro or prompt) and exit.
			# The command's return value is returned to the OS.
			cmd = " ".join(args)
			exit(self.onecmd(cmd))
		name += ', type "help" or "?" for help.'
		self.cmdloop(name)

	def _getPlatform(self):
		"""Get a string representing the type of OS platform we're running on.
	"""
		plat = sys.platform.lower()
		if plat[:3] in ["mac", "dar"]:
			return "mac"
		elif "linux" in plat:  # e.g., linux2
			return "linux"
		elif "win" in plat:  # windows, win32, cygwin
			return "windows"
		return plat

	def do_clear(self, line):
		"""
		Clears the screen.
		"""
		if self.plat == "windows" and sys.platform != "cygwin":
			os.system("cls")
			return ""
		os.system("clear")
		return ""

	def do_cls(self, line):
		"""
		Clears the screen.
		"""
		return self.do_clear(line)

	def _commandMatch(self, cmdWord):
		"""
		Returns the exact command word indicated by cmdWord.
		Implements command matching when an ambiguous command prefix is typed.
		"""
		# Populate the list of valid commands as necessary.
		try: self._cmds
		except AttributeError:
			self._cmds = dict()
			for cmd in filter(lambda f: f.startswith("do_"), dir(self)):
				self._cmds[cmd[3:].lower()] = cmd[3:]
		# An exact match wins even if there are longer possibilities.
		try: return self._cmds[cmdWord.lower()]
		except KeyError: pass
		# Get a list of matches, capitalized as they are in the code do_* function names.
		cmdWord = cmdWord.lower()
		matches = filter(lambda f: f.startswith(cmdWord), self._cmds.keys())
		matches = map(lambda cmdKey: self._cmds[cmdKey], matches)
		if len(matches) == 1: return matches[0]
		return self.selectMatch(matches, "Which command did you mean?")

	def confirm(self, prompt):
		"""Get permission for an action with a y/n prompt.
		Returns True if "y" is typed and False if "n" is typed.
		Repeats request until one or the other is provided.
		KeyboardInterrupt signals equate to "n"
		"""
		l = ""
		while not l:
			l = raw_input_withoutHistory(prompt)
			l = l.strip()
			l = l.lower()
			if l == "keyboardinterrupt": l = "n"
			if l in ["n", "no"]: return False
			elif l in ["y", "yes"]: return True
			self.msg("Please enter y or n.")
			l = ""

	def selectMatch(self, matches, prompt=None, ftran=lambda m: m, allowMultiple=False):
		"""
		Return a match from a set.
		matches: The set of matches to consider.
		prompt: The prompt to print above the match list.
		ftran: The function on a match to make it into a string to print.
		allowMultiple: If True, lets the user enter multiple numbers and returns a list of matches.
		"""
		mlen = len(matches)
		if mlen == 0: raise KeyError("No matches found")
		if mlen == 1:
			if allowMultiple: return [matches[0]]
			else: return matches[0]
		if ftran:
			ft1 = ftran
			#ftran = lambda x: unicode(ft1(x), "ascii", "replace")
		matches = sorted(matches, key=ftran)
		mlist = [unicode(i+1) +" " +ftran(match) for i,match in enumerate(matches)]
		if not prompt:
			if allowMultiple: prompt = "Select one or more options:"
			else: prompt = "Select an option:"
		m = prompt +"\n   " +"\n   ".join(mlist)
		self.msg(m)
		if allowMultiple: prompt = "Selection (or Enter to cancel): "
		else: prompt = "Selections (or Enter to cancel): "
		l = ""
		while not l:
			l = raw_input_withoutHistory(prompt)
			l = l.strip()
			if not l: break
			if allowMultiple:
				try: return self._collectSelections(matches, l)
				except [IndexError, SyntaxError]:
					# Error message printed by _collectSelections().
					l = ""
					continue
			try:
				if l and int(l): return matches[int(l)-1]
			except IndexError:
				self.msg("Invalid index number")
				l = ""
		raise ValueError("No option selected")

	def _collectSelections(self, matches, l):
		"""
		Return the matches selected by l. Supported syntax examples (numbers are 1-based):
			9: Just the 9th match.
			2,5 or 2 5 or 2, 5: Matches 2 and 5.
			2-5 or 2..5: Matches 2 3 4 and 5.
			2-5, 9 etc.: Matches 2 through 5 and 9.
		"""
		# First some syntactic simplifications.
		# Comma/space combos become a single comma.
		l = re.sub(r'[ \t,]+', r',', l)
		# .. becomes -
		l = re.sub(r'\.\.', '-', l)
		indices = set()
		# Now make units, each being an index or a range.
		units = l.split(',')
		for unit in units:
			if "-" in unit:
				start,end = unit.split("-")
			else:
				start,end = unit,unit
			start = int(start)
			end = int(end)
			if start < 1 or start > len(matches): 
				m = "%d is not a valid index" % (start)
				raise IndexError(m)
			if end < 1 or end > len(matches): 
				m = "%d is not a valid index" % (end)
				raise IndexError(m)
			indices.update(range(start-1, end))
		return [matches[i] for i in sorted(indices)]

	def msgNoTime(self, *args):
		kwargs = {"noTime": True}
		self.msg(*args, **kwargs)

	def msgFromEvent(self, *args):
		kwargs = {"fromEvent": True}
		speakEvents = 0
		try: speakEvents = int(self.speakEvents)
		except: pass
		if speakEvents != 0:
			mq_vo.extend(args)
		self.msg(*args, **kwargs)

	def msg(self, *args, **kwargs):
		"""
		Arbitor of event output message format:
		"""
		indent1 = kwargs.get("indent1") or None
		indent2 = kwargs.get("indent2") or None
		s = unicode("", "ascii", "replace")
		started = False
		for item in args:
			if item is None: continue
			if started: s += " "
			started = True
			if type(item) is unicode: s += item
			else:
				try: s += unicode(item, "ascii", "replace")
				except: s += str(item)
		if not started: return
		s1 = s
		s1 = format(s1, indent1=indent1, indent2=indent2)
		if kwargs.get("fromEvent"):
			mq.append(s1)
		else:
			print s1.encode("ascii", "replace")

	def msgErrOnly(self, *args, **kwargs):
		"""
		msg() but only for errors.
		"""
		if not args or args[0].startswith("ERROR"):
			self.msg(*args, **kwargs)
		return

	def getMultilineValue(self):
		"""
		Get and return a possibly multiline value.
		The content is prompted for and terminated with a dot on its own line.
		An EOF also ends a value.
		"""
		self.msg("Enter text, end with a period (.) on a line by itself.")
		content = ""
		while True:
			try:
				line = raw_input("")
			except EOFError:
				line = "."
			line = line.strip()
			if line == ".":
				break
			if content:
				content += "\n"
			content += line
		return content

	def linearList(self, name, l, func=lambda e: unicode(e)):
		"""
		List l on a (possibly long and wrap-worthy) line.
		The line begins with a header with name and entry count.
		Null elements are removed.  If you don't want this, send in a func that doesn't return null for any entry.
		"""
		l1 = sorted(filter(None, map(func, l)), key=lambda k: k.lower())
		if len(l) == 0:
			return "%s: 0" % (name)
		return "%s (%0d): %s." % (name, len(l1), ", ".join(l1))

	def lineList(self, name, l, func=lambda e: unicode(e)):
		"""
		List l one line per entry, indented below a header with name and entry count.
		Null elements are removed.  If you don't want this, send in a func that doesn't return null for any entry.
		"""
		l1 = sorted(filter(None, map(func, l)), key=lambda k: k.lower())
		if len(l) == 0:
			return "%s: 0" % (name)
		return "%s (%0d):\n    %s." % (name, len(l1), "\n    ".join(l1))

	def getargs(self, line, count=0):
		"""
		Parse the given line into arguments and return them.
		Args are dequoted unless count is non-zero and less than the number of arguments.
		In that case, all but the last arg are dequoted.
		Parsing rules are those used by shlex in Posix mode.
		"""
		# shlex.split dequotes internally.
		if not count or count >= len(line): return shlex.split(line)
		args = shlex.split(line)
		if len(args) < count: return args
		# Dequoted args up to but not including the last.
		args = args[:count-1]
		# Collect args without dequoting into the last one, then append it.
		tokenizer = shlex.shlex(line)
		[tokenizer.next() for i in range(0, count-1)]
		lastArg = " ".join([t for t in tokenizer])
		print "LastArg: " +lastArg
		args.append(lastArg)
		return args

	def dequote(self, line):
		"""Remove surrounding quotes (if any) from line.
		Also unescapes the quote removed if found inside the remaining string.
		"""
		if not line: return line
		if (line[0] == line[-1] and line[0] in ["'", '"']
		and len(shlex.split(line)) == 1):
			q = line[0]
			line = line[1:-1]
			line = line.replace('\\'+q, q)
		return line

# Input helpers.

def raw_input(prompt=None):
	try:
		return raw_input0(prompt)
	except KeyboardInterrupt:
		return "KeyboardInterrupt"

__builtins__["raw_input0"] = __builtins__["raw_input"]
__builtins__["raw_input"] = raw_input

def raw_input_withoutHistory(prompt=None):
	"""
	raw_input() wrapper that keeps its line out of readline history.
	This is to avoid storing question answers like "1."
	"""
	l = raw_input(prompt)
	if len(l) == 0: return l
	try: readline.remove_history_item(readline.get_current_history_length() -1)
	except (NameError, ValueError): pass
	return l

# Output helpers.

# Formatter for output.
import textwrap
fmt = textwrap.TextWrapper()
def format(text, indent1=None, indent2=None, width=79):
	"""
	Format text for output to screen and/or log file.
	Individual lines are wrapped with indent.
	"""
	if indent1 is None:
		indent1 = ""
		indent2 = "   "
	elif indent2 is None:
		indent2 = indent1 +"   "
	fmt.width = width
	lines = text.splitlines()
	wlines = []
	for line in lines:
		lineIndent = " " * (len(line) -len(line.lstrip()))
		fmt.initial_indent = indent1
		fmt.subsequent_indent = indent2 +lineIndent
		wlines.append("\n".join(fmt.wrap(line)))
	text = "\n".join(wlines)
	return text

class MessageQueue(list):
	def __init__(self, *args, **kwargs):
		self.holdAsyncOutput = False
		speechQueue = False
		if "speechQueue" in kwargs:
			speechQueue = kwargs["speechQueue"]
			del kwargs["speechQueue"]
		self.speechQueue = speechQueue
		list.__init__(self, *args, **kwargs)
		if speechQueue:
			self.thr = threading.Timer(0, self.watch)
			self.thr.setDaemon(True)
			self.thr.start()

	def output(self, nmsgs=0):
		"""
		Output nmsgs messages.
		If nmsgs is not passed, treat as if it were 0.
		If nmsgs is positive, output that many messages.
		If nmsgs is less than 0, output all pending messages.
		If nmsgs is 0:
			- If self.holdAsyncOutput is True, output nothing now.
			- Else, output as if nmsgs were -1.
		"""
		if nmsgs == 0:
			if self.holdAsyncOutput:
				nmsgs = 0
			else:
				nmsgs = -1
		while len(self) and nmsgs != 0:
			s = self.pop(0)
			print s.encode("ascii", "replace")
			if nmsgs > 0:
				nmsgs -= 1

	def watch(self):
		while True:
			if len(self) > 0:
				say(" ")
				while len(self):
					m = self.pop(0)
					say(m)
			time.sleep(2.0)

	def append(self, *args, **kwargs):
		list.append(self, *args, **kwargs)
		self.output()

mq = MessageQueue()
mq_vo = MessageQueue(speechQueue=True)

def pendingMessageCount():
	return len(mq)

def flushMessages(nmsgs):
	mq.output(nmsgs)

def err(origin="", exctype=None, value=None, traceback=None):
	"Nice one-line error messages."
	errtype,errval,errtrace = (exctype, value, traceback)
	exctype,value,traceback = sys.exc_info()
	if not errtype: errtype = exctype
	if not errval: errval = value
	if not errtrace: errtrace = traceback
	# Static error trace preservation for errTrace().
	err.val = errval
	err.trace = errtrace
	buf = ""
	if origin: buf += origin +" "
	buf += errtype.__name__ +": " +unicode(errval)
	for i in range(2, len(errval.args)):
		buf += ", " +unicode(errval.args[i])
	return buf

def errTrace(e=None):
	"""Provides a very brief traceback for the last-generated error.
	The traceback only shows file names (no paths) and line numbers.
	"""
	if e is None:
		try: e = err.trace
		except AttributeError:
			return "No error has been recorded yet."
	trc = []
	while e:
		l = e.tb_lineno
		fname = e.tb_frame.f_code.co_filename
		fname = os.path.basename(fname)
		trc.append("%s %d" % (fname, l))
		e = e.tb_next
	return ", ".join(trc)

def say(*args):
	"""
	On MacOS, speak via the default Mac voice.
	On Windows. speak via SayTools if available.
	"""
	try: s = " ".join(args)
	except TypeError: s = unicode(args)
	s = re.sub(r'[A-Z_]+', cleanForSpeech, s)
	plat = sys.platform
	if (plat == "cygwin" or plat.startswith("win")) and SayTools:
		sys.coinit_flags = 0
		pythoncom.CoInitialize()
		try: SayTools.Say(s)
		except: print __main__.err()
		pythoncom.CoUninitialize()
	elif plat == "darwin": # MacOS
		fd,tmpfile = tempfile.mkstemp(suffix=".aiff")
		os.close(fd)
		cmd = ["say", "-o", tmpfile]
		subprocess.Popen(cmd, stdin=subprocess.PIPE).communicate(s)
		cmd = ["afplay", tmpfile]
		subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
		try: os.remove(tmpfile)
		except OSError: pass
	elif "linux" in plat.lower():
		pass

def cleanForSpeech(m):
	"""
	Make a few adjustments to a string to make it sound better.
	Based on the Mac default voice (Alex).
	This is called by re.sub from say().
	"""
	s = m.group()
	return s

