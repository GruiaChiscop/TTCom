"""Command implementation module for TTCom.

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

import gzip
from time import sleep, ctime
from datetime import datetime
import os, sys, re, subprocess, socket, shlex
import threading
from attrdict import AttrDict
from ttapi import TeamtalkServer
from mycmd import MyCmd, say as mycmd_say
from TableFormatter import TableFormatter
from conf import Conf
from triggers import Triggers
from parmline import ParmLine
from textblock import TextBlock

def callWithRetry(func, *args, **kwargs):
	"""For Cygwin 1.8 on Windows:
	Forks can ffail randomly in the presence of things like antivirus software,
	because DLLs attaching to the process can cause address mapping problems.
	This function retries such calls so they don't fail.
	"""
	i = 1
	while i <= 50:
		try:
			return func(*args, **kwargs)
		except OSError as e:
			i += 1
			print "Retrying, attempt #" +str(i)
	print "Retry count exceeded."

class NullLog(object):
	def write(self, *args, **kwargs):
		return

class MyTeamtalkServer(TeamtalkServer):
	def __init__(self, parent, *args, **kwargs):
		self.parent = parent
		self.silent = 0
		self.hidden = 0
		# TODO: triggers can't be set here because we don't have a
		# command processor object.
		TeamtalkServer.__init__(self, *args, **kwargs)

	def outputFromEvent(self, line, raw=False):
		"""For event output. See output() for details.
		Only outputs for current and non-silenced servers,
		"""
		if self.silent > 1:
			# Unconditional silence, even if it's the current server.
			return
		if self.silent and self.shortname != self.parent.curServer.shortname:
			# Silence unless it's the current server.
			return
		TeamtalkServer.outputFromEvent(self, line, raw)

	def hookEvents(self, eventline, afterDispatch):
		"""Called on each event with the event's parmline as a parameter.
		This method is called twice per event:
		once before and once after the event is dispatched.
		The afterDispatch parameter indicates which type of call is occurring.
		"""
		TeamtalkServer.hookEvents(self, eventline, afterDispatch)
		if not afterDispatch:
			self.logstream.write("%s\n  %s: %s\n" % (
				datetime.now().ctime(),
				self.shortname,
				eventline.initLine.rstrip()
			))
			return
		if eventline.event in ["userbanned", "useraccount"]:
			# These events are responses to listing commands and
			# should not trigger activity.
			return
		try: self.triggers.apply(eventline)
		except Exception as e:
			self.output("Trigger failure: %s" % (str(e)))

class Servers(dict):
	def __init__(self):
		self.logfilename = "ttcom.log"
		self.logstream = NullLog()
		if os.path.exists(self.logfilename):
			self.logstream = open(self.logfilename, "a")
		else:
			# If the file exists, make sure it's not damaged before appending to it.
			# Otherwise the new entries may be hard to read.
			if os.path.exists(self.logfilename +".gz"):
				try:
					ftmp = gzip.open(self.logfilename+".gz")
					for l in ftmp: pass
				except (IOError, gzip.zlib.error):
					exit("Rename or expand the log file first.")
					del ftmp
			else:
				# No log file exists.
				return
			# It should now be safe to append to this file.
			self.logstream = gzip.open(self.logfilename+".gz", "a")
		self.thFlusher = threading.Thread(target = self.flusher)
		self.thFlusher.daemon = True
		self.thFlusher.name = "flusher"
		self.thFlusher.start()
		self.logGlobalEvent("starting")

	def logGlobalEvent(self, event):
		self.logstream.write("%s\n  %s: %s\n" % (
			datetime.now().ctime(),
			"*TTCom*",
			event
		))

	def flusher(self):
		"""Flushes the log periodically.
		Runs in the Flusher() thread.
		"""
		while True:
			sleep(5.0)
			self.logstream.flush()

	def add(self, newServer):
		"""Add a new server.
		"""
		self[newServer.shortname] = newServer
		newServer.logstream = self.logstream

	def remove(self, shortname):
		"""Stop and remove a server connection.
		Shortname may be a shortname or an actual server object.
		"""
		if issubclass(type(shortname), TeamtalkServer):
			shortname = shortname.shortname
		server = self[shortname]
		server.disconnect()
		del self[shortname]

class TTComCmd(MyCmd):
	conf = Conf("ttcom.conf")
	speakEvents = property(lambda: conf.option("speakEvents"), None, None, "Whether to speak events")

	def __init__(self, noAutoLogins=False, logins=[]):
		if logins:
			noAutoLogins = True
		self.noAutoLogins = noAutoLogins
		self.servers = Servers()
		self.curServer = None
		MyCmd.__init__(self)
		TeamtalkServer.write = self.msg
		TeamtalkServer.writeEvent = self.msgFromEvent
		self.readServers(logins)

	def precmd(self, line):
		"""Handles >-to-"server " translation.
		Also handles :/;-to-"summary " translation.
		"""
		l = line.strip()
		if l.startswith("?"): l = l[1:].lstrip()
		elif re.match(r'^help\s', l.lower()): l = l.split(None, 1)[1]
		if l and l[0] == ">":
			line = line.replace(">", "server ", 1)
		if l and l[0] == ":":
			line = line.replace(":", "summary ", 1)
		elif l and l[0] == ";":
			line = line.replace(";", "summary ", 1)
		return MyCmd.precmd(self, line)

	def readServers(self, logins=[]):
		waitFors = []
		for shortname,pairs in self.conf.servers().items():
			host = ""
			loginParms = {}
			autoLogin = 0
			verNotify = False
			silent = 0
			hidden = 0
			triggers = Triggers(self.onecmd)
			doLogin = False
			for k,v in pairs:
				if k.lower() == "host":
					host = v
				elif k.lower() == "vernotify":
					verNotify = int(v)
				elif k.lower() == "autologin":
					if not int(self.noAutoLogins):
						autoLogin = int(v)
				elif k.lower() == "silent":
					silent = int(v)
				elif k.lower() == "hidden":
					hidden = int(v)
				elif k.lower().startswith("match ") or k.lower().startswith("action "):
					which,what = k.split(None, 1)
					if "." in what:
						triggerName,subname = what.split(".", 1)
					else:
						triggerName,subname = what,""
					if which.lower() == "match":
						triggers.addMatch(triggerName, ParmLine(v), subname)
					else:  # action
						triggers.addAction(triggerName, v, subname)
				else:
					loginParms[k.lower()] = v
			newServer = MyTeamtalkServer(self, host, shortname, loginParms)
			if verNotify:
				newServer.verNotify = True
			if autoLogin:
				newServer.autoLogin = autoLogin
			if silent:
				newServer.silent = silent
			if hidden:
				newServer.hidden = hidden
			# TODO: This is an odd way to get this link made.
			triggers.server = newServer
			newServer.triggers = triggers
			if self.servers.has_key(shortname):
				oldServer = self.servers[shortname]
				if (oldServer.loginParms != newServer.loginParms
				or oldServer.host != newServer.host):
					print "Reconfiguring " +shortname
					oldServer.terminate()
					self.servers.remove(shortname)
					doLogin = int(newServer.autoLogin)
				elif newServer.autoLogin and not oldServer.autoLogin and oldServer.state != "loggedIn":
					doLogin = True
			if self.servers.has_key(shortname):
				if oldServer.autoLogin != newServer.autoLogin:
					print "autoLogin for %s changing to %d" % (shortname, newServer.autoLogin)
				oldServer.autoLogin = newServer.autoLogin
				if oldServer.verNotify != newServer.verNotify:
					print "verNotify for %s changing to %d" % (shortname, newServer.verNotify)
				oldServer.verNotify = newServer.verNotify
				if oldServer.silent != newServer.silent:
					print "silent for %s changing to %d" % (shortname, newServer.silent)
				oldServer.silent = newServer.silent
				if oldServer.hidden != newServer.hidden:
					print "hidden for %s changing to %d" % (shortname, newServer.hidden)
				oldServer.hidden = newServer.hidden
				if oldServer.triggers != newServer.triggers:
					print "Updating triggers for %s" % (shortname)
				oldServer.triggers = newServer.triggers
				# TODO: Again, weird way to set this link up.
				oldServer.triggers.server = oldServer
			else:
				self.curServer = newServer
				self.servers.add(newServer)
				doLogin = int(newServer.autoLogin)
			if ((doLogin and not self.noAutoLogins)
			or shortname in logins
			):
				newServer.login(True)
				waitFors.append(newServer)
		halfsecs = 0
		incomplete = False
		while any([server.state != "loggedIn" for server in waitFors]):
			halfsecs += 1
			if halfsecs == 20:
				incomplete = True
				break
			sleep(0.5)
		sleep(0.5)
		Triggers.loadCustomCode()
		#self.do_shortSummary()
		unfinished = []
		for server in waitFors:
			if server.state != "loggedIn":
				unfinished.append(server.shortname)
		if len(unfinished):
			print "Servers that did not connect: " +", ".join(unfinished)

	def userMatch(self, u, checkAll=False):
		"""Match a user to what was typed/passed, asking for a
		selection if necessary. Returns a user object.
		The passed string is checked for containment in nickname,
		username, and userid fields. To match a userid exactly, use a
		number sign ("#") followed with no spaces by the userid;
		example: #247. If the userid matches a user, that user is
		used. If it does not, that userid is still used in
		case the user is logged out or invisible but still
		connected (this can happen on servers that don't
		allow a user to see other users unless in a channel
		with them).
		"""
		if checkAll:
			users = []
			map(lambda s: users.extend(s.users),
				self.servers
			)
		else:
			users = self.curServer.users
		if u.startswith("#") and u[1:].isdigit():
			users = filter(lambda u1:
				u1.userid == u[1:]
			, users.values())
		else:
			users = filter(lambda u1:
				u.lower() in self.curServer.nonEmptyNickname(u1, True).lower()
			, users.values())
		if checkAll:
			flt = lambda u1: u1.server.shortname +"/" +self.curServer.nonEmptyNickname(u1, True)
		else:
			flt = lambda u1: self.curServer.nonEmptyNickname(u1, True)
		return self.selectMatch(users, "Select a User", flt)

	def channelMatch(self, c):
		"""Match a channel to what was typed/passed, asking for a
		selection if necessary. Returns a channel object.
		The passed string is checked for containment in the channel name.
		If c contains a slash (/), the full name is checked;
		otherwise just the final component of channel names are checked.
		A channel name of "/" always matches just the root channel (channelid 1).
		A channel name starting and ending with "/" must match a
		channel exactly.
		"""
		channels = self.curServer.channels
		if c.startswith("/") and c.endswith("/"):
			return channels["1"]
		if "/" in c:
			channels = channels.values()
		else:
			# This filters on match against final channel path component,
			# except the final "/" is ignored.
			channels = filter(lambda c1:
				c.lower() in self.curServer.channelname(c1["channelid"])[:-1].rpartition("/")[2].lower()
			, channels.values())
		return self.selectMatch(channels, "Select a Channel",
			lambda c1: self.curServer.channelname(c1["channelid"])
		)

	def serverMatch(self, s):
		"""Match a server to what was typed/passed, asking for a
		selection if necessary. Returns a server object.
		Matches are for containment, but an exact match takes precedence;
		so "nick" matches "nick" even if "nick1" is also a server.
		"""
		servers = self.servers.keys()
		servers = filter(lambda s1:
			s.lower() in s1.lower()
		, servers)
		try: return self.servers[s]
		except KeyError: pass
		return self.servers[self.selectMatch(servers, "Select a Server")]

	def versionString(self):
		"""Return the version string for TTCom.
		"""
		return (
"""TeamTalk Commander (TTCom)
Copyright (c) 2011-2015 Doug Lee.

This program is covered by version 3 of the GNU General Public License.
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it under
certain conditions.
See the file LICENSE.txt for further information.
The iniparse module is under separate license and copyright;
see that file for details.

TTCom version 1.2
""".strip())

	def do_version(self, line=""):
		"""Show the version information for TTCom.
		"""
		self.msg(self.versionString())

	def do_server(self, line):
		"""Get or change the server to which subsequent commands will apply,
		or apply a specific command to a specific server without
		changing the current one.
		Usage: server [serverName [command]]
		Without arguments, just indicates which server is current.
		With one argument, changes the current server.
		With more arguments, runs command against a server without
		changing the current one.
		"""
		args = self.getargs(line)
		newServer = None
		if len(args) >= 1:
			newServer = self.serverMatch(args.pop(0))
		if len(args) == 0:
			if newServer: self.curServer = newServer
			print "Current server is %s" % (self.curServer.shortname)
			return
		# A command to run against a specific server (newServer).
		oldServer = self.curServer
		try:
			self.curServer = newServer
			self.onecmd(" ".join(args))
		finally:
			self.curServer = oldServer

	def do_refresh(self, line=""):
		"""Refresh server info and update connections as necessary.
		"""
		line = line.strip()
		if not line:
			self.readServers()
			return
		shortnames = line.split()
		for shortname in shortnames:
			server = self.serverMatch(shortname)
			self.servers.remove(server)
			self.servers.add(server)

	def do_summary(self, line=""):
		"""Summarize the users and active channels on this or a given server.
		"""
		server = self.curServer
		if line:
			server = self.serverMatch(line)
		server.summarizeChannels()

	def do_allSummarize(self, line=""):
		"""Summarize user/channel info on all connected servers.
		Servers marked hidden in the config file are omitted.
		"""
		offs = {}
		empties = []
		sums = []
		for shortname in sorted(self.servers):
			server = self.servers[shortname]
			if server.hidden: continue
			if server.state != "loggedIn":
				offs.setdefault(server.state, [])
				offs[server.state].append(shortname)
			elif len(server.users) <= 1:
				# 1 allows for this user.
				empties.append(shortname)
			else:
				sums.append(shortname)
		if len(offs):
			for k in sorted(offs.keys()):
				print "%s: %s" % (
					k,
					", ".join(offs[k])
				)
		if len(empties):
			print "No users: " +", ".join(empties)
		for shortname in sums:
			server = self.servers[shortname]
			server.summarizeChannels()

	def do_shortSummary(self, line=""):
		"""Short summary of who's on all logged-in servers with people.
		Servers marked hidden in the config file are omitted.
		"""
		offs = {}
		sums = []
		for shortname in sorted(self.servers):
			server = self.servers[shortname]
			if server.hidden: continue
			if server.state != "loggedIn":
				if server.state == "disconnected" and not server.autoLogin:
					continue
				state = server.state
				if server.conn and server.conn.state and server.conn.state != state:
					state += self.conn.state
				offs.setdefault(state, [])
				offs[state].append(shortname)
			elif len(server.users) <= 1:
				# 1 allows for this user.
				continue
			else:
				sums.append(shortname)
		if len(offs):
			for k in sorted(offs.keys()):
				print "%s: %s" % (
					k,
					", ".join(offs[k])
				)
		for shortname in sums:
			server = self.servers[shortname]
			self.oneShortSum(server)

	def oneShortSum(self, server):
		"""Short-form summary for one server.
		"""
		# Users other than me and that are actuallly in a channel.
		users = filter(lambda u:
			(u.get("channelid") or u.get("chanid"))
			and u.userid != server.me.userid
		, server.users.values())
		if not len(users):
			return
		users = map(lambda u: server.nonEmptyNickname(u, False), users)
		users.sort(key=lambda u: u.lower())
		line = "%s (%d): %s" % (
			server.shortname,
			len(users),
			", ".join(users)
		)
		print line

	def do_join(self, line):
		"""Join a channel.
		Usage: join channelname [password]
		channelname and/or password can contain spaces if quoted.
		The channel name is checked for matches unless it starts and ends with
		a slash, in which case it is used verbatim, so that new
		channels can be created and joined with this command.
		"""
		args = self.getargs(line)
		channel,password = "",""
		if args: channel = args.pop(0)
		if args: password = args.pop(0)
		if channel == "/" or not (channel.startswith("/") and channel.endswith("/")):
			channel = self.channelMatch(channel)
		if self.curServer.is5():
			self.do_send('join chanid=%s password="%s"' % (channel.chanid, password))
		else:
			self.do_send('join channel="%s" password="%s"' % (channel.channel, password))

	def do_leave(self, line):
		"""Leave a channel.
		Usage: leave [channelname]
		channelname can be multiple words and can optionally be quoted.
		channelname can also be omitted to leave the current channel.
		"""
		if not line.strip():
			self.do_send("leave")
			return
		line = self.dequote(line)
		ch = self.channelMatch(line)
		if self.curServer.is5():
			self.do_send('leave channel=' +ch.chanid)
		else:
			self.do_send('leave channel="' +ch.channel +'"')

	def do_nick(self, line):
		"""Set a new nickname or check the current one.
		"""
		if line:
			line = self.dequote(line)
			self.do_send("changenick nickname=\"%s\"" % (line))
			return
		nick = self.curServer.me.nickname
		print "You are now %s" % (
			self.curServer.nonEmptyNickname(self.curServer.me)
		)

	def do_connect(self, line=""):
		"""Connect to a server without logging in.
		"""
		self.curServer.connect()

	def do_disconnect(self, line=""):
		"""Disconnect from a server.
		"""
		# Sending "quit" can make other clients notice the disconnect sooner.
		self.curServer.send("quit")
		sleep(0.5)
		if self.curServer.state != "disconnected":
			self.curServer.disconnect()

	def do_login(self, line=""):
		"""Log into a server, connecting first if necessary.
		"""
		self.curServer.login()

	def do_logout(self, line=""):
		"""Log out of a server.
		"""
		self.curServer.logout()

	def do_broadcast(self, line):
		"""Send a broadcast message to all people on a server,
		even those who are currently not in a channel. The message
		shows up in the main message window for each user.
		Example usage: Broadcast Server going down in five minutes.
		This command requires admin privileges on the server.
		"""
		if not line:
			print "No broadcast message specified."
			return
		line = self.dequote(line)
		self.do_send('message type=3 content="%s"' % (line))

	def do_move(self, line):
		"""Move one or more users to a new channel.
		Usage: move user1[, user2 ...] channel
		Users and channels can be ids or partial names.
		A user can also be @channelName, which means all users in that channel.
		Example: move doug "bill cosby" @main" away
		means move doug, Bill Cosby, and everyone in main to away,
		where "main" and "away" are contained in channel names on the server.
		"""
		args = self.getargs(line)
		if not args: raise SyntaxError("No user(s) or channel specified")
		if len(args) < 2: raise SyntaxError("At least one user and a channel are required")
		users = []
		channel = None
		for u in args[:-1]:
			if u.startswith("@"):
				chan = self.channelMatch(u[1:])
				cid = self.curServer.channels[chan["channelid"]]["channelid"]
				for u1 in self.curServer.users.values():
					if u1.get("channelid") == cid:
						users.append(u1)
			else:
				users.append(self.userMatch(u))
		channel = self.channelMatch(args[-1])
		is5 = self.curServer.is5()
		for u in users:
			if is5:
				self.do_send("moveuser userid=%s chanid=%s" % (
					u["userid"],
					channel["chanid"]
				))
			else:
				self.do_send("moveuser userid=%s destchannel=\"%s\"" % (
					u["userid"],
					channel["channel"]
				))

	def do_cmsg(self, line):
		"""Send a message to a channel.
		Usage: cmsg <channelname> <message>
		Also used internally to implement the stats command.
		"""
		args = self.getargs(line, 1)
		if len(args) < 2:
			raise SyntaxError("A channel name and a message must be specified")
		channel = self.channelMatch(args[0])
		if self.curServer.is5():
			self.do_send('message type=2 chanid=%s content="%s"' % (
				channel.chanid,
				args[1]
			))
		else:
			self.do_send('message type=2 channel="%s" content="%s"' % (
				channel.channel,
				args[1]
			))

	def _handleSubscriptions(self, isIntercept, line):
		"""Does the work for do_subscribe and do_intercept.
		"""
		args = self.getargs(line)
		if len(args) < 1:
			raise SyntaxError("A user must be specified")
		user = self.userMatch(args.pop(0))
		firstBit = 1
		typename = "Subscriptions"
		if isIntercept:
			firstBit = 256
			typename = "Intercepts"
		bitnames = self.curServer.subBitNames()
		subs = 0
		unsubs = 0
		for arg in args:
			isUnsub = False
			if arg.startswith("-"):
				isUnsub = True
				arg = arg[1:]
			matches = filter(lambda bn: bn.lower().startswith(arg.lower()), bitnames)
			arg = self.selectMatch(matches, "Select an option:")
			idx = bitnames.index(arg)
			if isUnsub:
				unsubs += (firstBit << idx)
			else:
				subs += (firstBit << idx)
		# Issue any unsubscribes, then any subscribes.
		if unsubs:
			self.do_send("unsubscribe userid=%s sublocal=%s" % (
				user.userid,
				str(unsubs)
			))
		if subs:
			self.do_send("subscribe userid=%s sublocal=%s" % (
				user.userid,
				str(subs)
			))
		# Then list what remains active.
		subs = int(user.sublocal)
		curbit = firstBit
		bits = []
		for idx,bitname in enumerate(bitnames):
			if subs & (firstBit << idx):
				bits.append(bitname)
		bits = ", ".join(bits)
		if not bits:
			bits = "none"
		print "%s: %s" % (typename, bits)

	def do_subscribe(self, line):
		"""Subscribe to and/or unsubscribe from any of the following from a user:
			User messages: Messages sent by this user to another user.
			Channel messages: Messages sent by this user to a channel.
			Broadcast messages: Messages sent by this user to the entire server.
			Audio: Sound sent by this user (but see below).
			Video: Video sent by this user.
			Desktop: This user's shared desktop.
		Use a dash (-) before any item to remove it.
		Example: subscribe doug -chan audio
			Stops channel messages and starts audio subscription.
		Specifying no subscriptions just lists the active ones.
		Note that audio, video, and desktop data are neither supported
		nor noticed by this program.
		"""
		self._handleSubscriptions(False, line)

	def do_intercept(self, line):
		"""Start or stop intercepting any of the following from a user:
			User messages: Messages sent by this user to another user.
			Channel messages: Messages sent by this user to a channel.
			Broadcast messages: Messages sent by this user to the entire server.
			Audio: Sound sent by this user (but see below).
			Video: Video sent by this user.
			Desktop: This user's shared desktop.
		Use a dash (-) before any item to remove it.
		Example: intercept doug -chan audio
			Stops intercepting channel messages and starts intercepting audio.
		Specifying no interceptions just lists the active ones.
		Administrative rights are required to start interceptions.
		Note that audio, video, and desktop data are neither supported
		nor noticed by this program.
		"""
		self._handleSubscriptions(True, line)

	def do_umsg(self, line):
		"""Send a message to a user.
		Usage: umsg <user> <message>
		"""
		args = self.getargs(line, 1)
		if len(args) < 2:
			raise SyntaxError("A user and a message must be specified")
		user = self.userMatch(args[0])
		self.do_send('message type=1 destuserid="%s" content="%s"' % (
			user.userid,
			args[1]
		))

	def do_stats(self, line=""):
		"""Show statistics for a server.
		This requires admin privileges on the server.
		"""
		self.do_send("querystats")

	def userAction(self, cmd, user):
		"""Perform an action on a user that just requires a userid.
		"""
		user = user.strip()
		if not user:
			raise SyntaxError("A user name or partial name must be specified")
		user = self.userMatch(user)
		if not user: return
		self.do_send('%s userid="%s"' % (cmd, user.userid))

	def do_kick(self, line):
		"""Kick a user by name or ID.
		"""
		self.userAction("kick", line)

	def do_ban(self, line):
		"""Ban a user by name or ID,
		unban a user by IP address or current name or ID,
		or list current bans.
		A ban does not also kick; see kb for this.
		Usages:
			ban: Lists all bans.
			ban spec: List bans matching spec.
			ban -a userSpec: Ban the user matching userSpec.
			ban -d userSpec: Unban the user matching userSpec.
		"""
		line = line.strip()
		# First handle the list-only cases (ban and ban spec).
		if not line or not line.startswith("-"):
			bans = self.getBans()
			if line:
				bans = filter(lambda b: line in b.line, bans)
			tbl = TableFormatter("User Bans", [
				"Username", "Nickname", "IP Address", "Time", "Channel"
			])
			for b in bans:
				parms = b.parms
				tbl.addRow([
					parms.username, parms.nickname,
					parms.ipaddr,
					ctime(float(parms.bantime)),
					parms.channel
				])
			self.msg(tbl.format(2))
			return
		# ban -a and ban -d remain.
		opt,line = line[:2], line[2:].strip()
		if opt not in ["-a", "-d"]:
			raise SyntaxError("Unknown option: %s" % (opt))
		if opt == "-a":
			# Add a ban.
			self.userAction("ban", line)
			return
		# Del is all we have left.
		if not line:
			raise SyntaxError("Must specify a user or IP address")
		bans = self.getBans()
		if not bans: raise ValueError("No bans found")
		bans = filter(lambda b: line.lower() in b.line.lower(), bans)
		ban = self.selectMatch(bans, "Select a Ban To Remove")
		ban = ParmLine(ban)
		self.do_send('unban ipaddr="%s"' % (ban.parms.ipaddr))

	def do_kb(self, line):
		"""Kick and ban a user by name or ID.
		"""
		self.userAction("ban", line)
		self.userAction("kick", line)

	def getAccounts(self):
		"""Return the set of accounts on this server.
		Returns a dict of ParmLines, one for each account.
		The keys are the usernames.
		"""
		accts = self.request("listaccounts")
		resp = accts.pop()
		if resp.event != "ok":
			# TODO: This ignores any but the last response line.
			raise ValueError(resp)
		d = {}
		for acct in accts:
			if acct.event == "ok": continue
			d[acct.parms.username] = acct
		return d

	def getBans(self):
		"""Returns the bans on this server as a list of lines.
		The lines are the responses to the "listbans" command, one line per ban.
		"""
		bans = self.request("listbans")
		resp = bans.pop()
		if resp.event != "ok":
			# TODO: This ignores any but the last response line.
			raise ValueError(resp)
		return bans

	def do_account(self, line):
		"""Account management. Requires admin privileges.
		Account (with no arguments) lists all accounts.
		Account <username> will show that or a matching account.
		Account -d <username> will delete that or a matching account.
		Account -a <username> <password> <type> will create an account.
		Account -m <username> <parms> will modify that or a matching account.
		<parms> are keyword=value pairs:
			password=<password>
			usertype=<type>
			note=<text> (rarely used)
			userdata=<number> (rarely used)
		<type>: 1 for a normal (default) account, 2 for an admin account, or an account identifier (TT5 only).
		An account identifier must match exactly one account and will be used to obtain user rights.
		Use "" to specify the anonymous account as a source of rights.
		Quote any arguments that contain spaces.
		Example commands:
			List all: account
			Add: account -a dlee "blah" 1
			Show one: account dlee
			Delete: account -d dlee
			Modify: account -m dlee password=blurfl
		"""
		args = shlex.split(line)
		if not args:
			accts = self.getAccounts()
			tbl = TableFormatter("User Accounts", [
				"Username", "Password", "Type", "Userdata", "Note",
				"Channel", "Op Channels"
			])
			# TODO: Op Channels is a list of channel ids.
			for username in sorted(accts):
				acct = accts[username]
				parms = acct.parms
				tbl.addRow([
					parms.username, parms.password,
					["0","Default","Admin","3","4","5"][int(parms.usertype)],
					parms.userdata, parms.note,
					parms.channel,
					parms.opChannels
				])
			self.msg(tbl.format(2))
			return
		action = "show"
		if args[0].startswith("-"):
			opt = args.pop(0)
			if opt == "-a":
				action = "add"
			elif opt == "-d":
				action = "del"
			elif opt == "-m":
				action = "mod"
			else:
				raise SyntaxError("Unrecognized option: " +opt)
		if not args:
			raise SyntaxError("Must specify an account name with this option")
		acctDict = self.getAccounts()
		whichAcct = args.pop(0)
		if action == "add":
			if whichAcct.lower() in map(lambda a: a.lower(), acctDict):
				raise ValueError("Account %s already exists" % (whichAcct))
			if not args:
				if self.curServer.is5():
					raise SyntaxError("Must include a password and a user type or user rights source account")
				else:
					raise SyntaxError("Must include a password and a user type")
			pw = args.pop(0)
			if not args:
				raise SyntaxError("Must include a user type (1 default, 2 admin) or an account to use for user rights")
			utype = args.pop(0)
			if utype not in ["1", "2"] and self.curServer.is5():
				if utype == "" and acctDict.has_key(""):
					acct = acctDict[""]
				else:
					accts = filter(lambda a: utype.lower() in a.lower(), acctDict)
					rightsAcct = self.selectMatch(accts, "Select an Account For User Rights")
					acct = acctDict[rightsAcct]
				self.do_send('newaccount username="%s" password="%s" usertype=1 userRights=%s' % (
					whichAcct, pw, acct.parms.userRights
				))
				return
			self.do_send('newaccount username="%s" password="%s" usertype=%s' % (
				whichAcct, pw, utype
			))
			return
		# show/del/mod.
		if whichAcct == "" and acctDict.has_key(""):
			acct = acctDict[""]
		else:
			accts = filter(lambda a: whichAcct.lower() in a.lower(), acctDict)
			whichAcct = self.selectMatch(accts, "Select an Account")
			acct = acctDict[whichAcct]
		if action == "show":
			print acct
			return
		elif action == "del":
			self.do_send('delaccount username="%s"' % (acct.parms.username))
			return
		# Mod.
		# FakeEvent so we can use ParmLine's line-parsing code for this.
		parmline = ParmLine("fakeEvent " +" ".join(args))
		parms = acct.parms
		parms.update(parmline.parms)
		self.do_send(ParmLine("newaccount", parms))

	def do_tt(self, line):
		"""Create a .tt file for a user account.
		Usage: tt ttFileName [userName [channelToJoin]]
		"""
		args = self.getargs(line)
		if not args:
			raise SyntaxError("Must specify a .tt file name to generate")
		fname = args.pop(0)
		if not fname.lower().endswith(".tt"):
			fname += ".tt"
		if (os.path.exists(fname)
		and not self.confirm("File %s already exists. Replace it (y/n)?" % (
			fname
		))):
			return
		if not args:
			acct = ParmLine("fakeEvent username=\"\" password=\"\"")
		else:
			acct = args.pop(0)
			acctDict = self.getAccounts()
			accts = filter(lambda a: acct.lower() in a.lower(), acctDict)
			acct = self.selectMatch(accts, "Select an Account")
			acct = acctDict[acct]
		if args: channel = args.pop(0)
		else: channel = None
		if channel:
			cid = self.channelMatch(channel).channelid
		else:
			cid = None
		tt = self.curServer.makeTTString(acct.parms, cid)
		with open(fname, "w") as f:
			f.write(tt)

	def do_say(self, line):
		"""Say the given line if possible.
		Quoting is not necessary or desirable.
		"""
		mycmd_say(line)

	def do_system(self, line):
		"""Run a system command in a subshell.
		"""
		task = lambda: callWithRetry(os.system, line)
		thr = threading.Thread(target=task)
		thr.daemon = True
		thr.start()

	def do_whoIs(self, line=""):
		"""Show information about a user.
		Syntax: whoIs <name>, where <name> can be a full or partial user name.
		If name is omitted, this current user is used.
		"""
		line = line.strip()
		if line:
			user = self.userMatch(line)
			if not user: return
		else:
			user = self.curServer.me
		u = AttrDict(user.copy())
		buf = TextBlock()
		userid = u.pop("userid")
		buf += "UserId %s, " % (userid)
		if not u.get("username") and not u.get("nickname"):
			buf += "no nickname or username"
		else:
			buf.add("Username", u.get("username"), True)
			buf.add("Nickname", u.get("nickname"), True)
		u.pop("username", "")
		u.pop("nickname", "")
		buf.add("UserType", u.get("usertype"))
		u.pop("usertype", "")
		buf.add("StatusMode", u.get("statusmode"), True)
		statusmsg = u.get("statusmsg")
		if statusmsg: statusmsg = statusmsg.strip()
		if statusmsg: buf += " (" +statusmsg +")"
		u.pop("statusmode", "")
		u.pop("statusmsg", "")
		ipaddr,d1,tcpport = (u.get("ipaddr") or "").partition(":")
		udpaddr,d1,udpport = (u.get("udpaddr") or "").partition(":")
		if ipaddr and ipaddr == udpaddr:
			buf.add("TCP and UDP addresses", self.formattedAddress(ipaddr))
		else:
			buf.add("IP Address", self.formattedAddress(ipaddr))
			buf.add("UDP Address", self.formattedAddress(udpaddr), True)
		buf.add("TCP Port", tcpport, True)
		buf.add("UDP Port", udpport, True)
		u.pop("ipaddr", "")
		u.pop("udpaddr", "")
		buf.add("Client Version", u.pop("version", ""))
		buf.add("Packet Protocol", u.pop("packetprotocol", ""), True)
		channelid = u.pop("channelid", "")
		channel = u.pop("channel", "")
		if channelid or channel:
			if not channel:
				channel = self.curServer.channels[channelid].channel
			buf += "\nOn channel %s (%s)" % (channelid, channel)
		server = u.pop("server", None)
		if server:
			channels = server.channels.values()
		else:
			channels = []
		for which in [
			("voiceusers", "Voice user in"),
			("videousers", "Sharing video in"),
			("desktopusers", "Sharing desktop in"),
			("operators", "Operator in"),
			("opchannels", "Automatically operator in")
		]:
			k,name = which
			matches = filter(lambda c: userid in (c.get(k) or []), channels)
			matches = ", ".join(map(lambda c: c.channel, matches))
			buf.add(name, matches)
			try: u.pop(k)
			except KeyError: pass
		buf.add("SubLocal", u.pop("sublocal", ""))
		buf.add("SubPeer", u.pop("subpeer", ""), True)
		userdata = u.pop("userdata", "")
		if userdata == "0": userdata = ""
		buf.add("Userdata", userdata)
		buf.add("Note", u.pop("note", ""), True)
		# Anything non-empty value not handled above goes here.
		for k in sorted(u):
			buf.add(k, u[k])
		self.msg(str(buf))

	def formattedAddress(self, addr):
		"""Return the given address with FQDN where possible.
		Assumes addr is a numeric address (IPV4 or IPV6).
		"""
		if not addr: return addr
		fqdn = socket.getfqdn(addr)
		if (fqdn == addr
			or fqdn.endswith(".in-addr.arpa")
		): return addr
		return "%s (%s)" % (fqdn, addr)

	def do_addresses(self, line=""):
		"""Show IP addresses and ports for a user.
		Syntax: addresses <name>, where <name> can be a full or partial user name.
		If name is omitted, this current user is used.
		"""
		line = line.strip()
		if line:
			user = self.userMatch(line)
			if not user: return
		else:
			user = self.curServer.me
		u = AttrDict(user.copy())
		buf = TextBlock()
		ipaddr,d1,tcpport = (u.get("ipaddr") or "").partition(":")
		udpaddr,d1,udpport = (u.get("udpaddr") or "").partition(":")
		if ipaddr and ipaddr == udpaddr:
			buf.add("TCP and UDP addresses", self.formattedAddress(ipaddr))
		else:
			buf.add("IP Address", self.formattedAddress(ipaddr))
			buf.add("UDP Address", self.formattedAddress(udpaddr))
		buf.add("TCP Port", tcpport)
		buf.add("UDP Port", udpport)
		self.msg(str(buf))

	def do_op(self, line):
		"""Op or deop a user in one or more channels or check ops.
		Syntax: op [-a|-d] [<user>] [<channel> ...]
		Op with no arguments lists all ops on the server.
		Op with just a user lists that user's ops.
		Op with -a or -d and a user adds or deletes that user's ops from channels.
		If no channel is specified, the user's current channel is used.
		Otherwise, the command affects all channels listed.
		Changing ops requires admin rights or ops in the affected channel(s).
		"""
		server = self.curServer
		k = "operators"
		line = line.strip()
		if not line:
			# List all ops on server.
			for u in sorted(server.users.values(), key=lambda u1: server.nonEmptyNickname(u1)):
				userid = u.userid
				matches = filter(lambda c:
					userid in (c.get(k) or []), server.channels.values()
				)
				matches = ", ".join(map(lambda c: c.channel, matches))
				if matches:
					self.msg("%s: %s" % (
						server.nonEmptyNickname(u),
						matches
					))
			return
		# Add, delete, or just show ops for a user.
		act = ""
		if line.startswith("-"):
			if line.startswith("-a"):
				act = "add"
			elif line.startswith("-d"):
				act = "del"
			else:
				raise SyntaxError("Unknown option: %s" % (line[:2]))
		args = self.getargs(line)
		# Get rid of -a or -d.
		if act: args.pop(0)
		if not args: raise SyntaxError("Must specify a user.")
		u = self.userMatch(args.pop(0))
		if args and not act:
			raise SyntaxError("No channels needed when just listing ops")
		if not args and u.get("channel") and act:
			# When no channel is given and ops are being changed,
			# use the user's current channel as the target.
			args.append(u.channel)
		opstatus = 0
		if act == "add": opstatus = 1
		# This loop is skipped if not act because we didn't allow that
		# case above.
		for chanName in args:
			c = self.channelMatch(chanName)
			self.do_send('op userid=%s channel="%s" opstatus=%s' % (
				u.userid,
				c.channel,
				opstatus
			))
			# Let the op list print after those modifications.
		# List ops for just this user.
		userid = u.userid
		matches = filter(lambda c:
			userid in (c.get(k) or []), server.channels.values()
		)
		matches = ", ".join(map(lambda c: c.channel, matches))
		if matches:
			self.msg("%s: %s" % (
				server.nonEmptyNickname(u),
				matches
			))

	def do_admins(self, line=""):
		"""List the admins and where they are and come from.
		"""
		channelname = self.curServer.channelname
		for u in self.curServer.users.values():
			if int(u.usertype) != 2: continue
			ch = None
			if u.chanid: ch = channelname(u.chanid)
			print "%s: %s, %s" % (
				self.curServer.nonEmptyNickname(u),
				u.ipaddr,
				ch
			)

	def do_ping(self, line=""):
		"""Send a ping to the server.
		A pong should come back.
		"""
		self.do_send("ping")

	def do_run(self, fname):
		"""Run, or replay, a file of raw TeamTalk API commands at the current server.
		"""
		if not fname:
			print "No file name specified."
			return
		fname = self.dequote(fname)
		# TODO: Consider security of unrestricted filesystem access here.
		if not os.path.exists(fname):
			print "File %s not found." % (fname)
			return
		for line in open(fname):
			line = line.strip()
			if line.startswith("addchannel"):
				line = line.replace("addchannel", "makechannel", 1)
			elif line.startswith("serverupdate"):
				line = line.replace("serverupdate", "updateserver", 1)
			if (line.startswith("updateserver")
			and "userrights=" in line
			):
				# Some userrights bits can throw out the whole updateserver request.
				i = line.find("userrights=")
				line1,sep,rest = line[i:].partition(" ")
				line = line[:i-1] +rest
				line1 = "updateserver " +line1
				self.rawSend(line1)
			self.rawSend(line)
		return

	def rawSend(self, line):
		"""Send a raw line to the server.
		"""
		self.curServer.conn.send(line)

	def do_send(self, line):
		"""Send a raw command to the current server.
		"""
		# Line can be a text line or a ParmLine object.
		self.servers.logstream.write("%s\n  %s: %s\n" % (
			datetime.now().ctime(),
			self.curServer.shortname,
			"_send_ " +str(line)
		))
		self.curServer.sendWithWait(line)

	def request(self, line):
		"""Send a command and return its results as a list of ParmLines.
		Line can be a text line or a ParmLine object.
		"""
		return self.curServer.sendWithWait(line, True)

	def do_option(self, line=""):
		"""Get or set a TTCom option by its name.  Valid options:
			queueMessages: Set non-zero to make messages print only when Enter is pressed.
				This keeps events from disrupting input lines.
			speakEvents: Set non-zero to make events speak through MacOS on arrival.
		Type with no parameters for a list of all options and their values.
		"""
		optname,sep,newval = line.partition(" ")
		optname = optname.strip()
		newval = newval.strip()
		if not newval: newval = None
		opts = [
			("queueMessages", "Queue messages on arrival and print on Enter."),
			("speakEvents", "Speak events through MacOS on arrival")
		]
		if not optname:
			lst = []
			for opt in opts:
				optname = opt[0]
				lst.append("%s = %s" % (
					optname,
					self.conf.option(optname)
				))
			self.msg("\n".join(lst))
			return
		f = lambda o: ": ".join(o)
		opts = filter(lambda o: optname.lower() in o[0].lower(), opts)
		opt = self.selectMatch(opts, "Select an Option:", f)[0]
		self.msg("%s = %s" % (
			opt,
			self.conf.option(opt, newval)
		))

