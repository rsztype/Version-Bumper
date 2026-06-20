# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs
from GlyphsApp.plugins import PalettePlugin
from vanilla import Window, Group, TextBox
from Foundation import NSNotificationCenter, NSDate, NSObject, NSMakeRect
from AppKit import NSViewWidthSizable, NSViewMinXMargin

PREF_KEY = "com.rsztype.RSZVersionBumper.enabled"


# ----------------------------------------------------------------------
# Shared engine: a single export observer for the entire app,
# regardless of how many windows/palettes are open.
# ----------------------------------------------------------------------
class _RSZBumpEngine(NSObject):

	def init(self):
		self = objc.super(_RSZBumpEngine, self).init()
		self.lastBump = 0.0
		return self

	def documentExported_(self, notification):
		try:
			if not Glyphs.defaults[PREF_KEY]:      # switch OFF -> does nothing
				return
			now = NSDate.date().timeIntervalSince1970()
			if now - self.lastBump < 10.0:         # debounce for batch of instances
				return
			self.lastBump = now

			font = Glyphs.font
			if font is None:
				return

			font.versionMinor += 1
			if font.versionMinor > 999:            # rollover 1.999 -> 2.000
				font.versionMajor += 1
				font.versionMinor = 0

			if font.parent:                        # updates Info panel and saves
				font.parent.saveDocument_(None)

			Glyphs.showNotification(
				"RSZ Version Bumper",
				"Version \u2192 %d.%03d" % (font.versionMajor, font.versionMinor)
			)
		except Exception as e:
			import traceback
			print(f"RSZ Version Bumper error: {traceback.format_exc()}")


_engine = None


def _ensure_engine():
	global _engine
	if _engine is None:
		_engine = _RSZBumpEngine.alloc().init()
		NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
			_engine, "documentExported:", "GSDocumentWasExportedNotification", None)
	return _engine


# ----------------------------------------------------------------------
# Palette: the switch in the right-hand inspector column.
# ----------------------------------------------------------------------
class RSZVersionBumperPalette(PalettePlugin):

	@objc.python_method
	def settings(self):
		self.name = "Version Bumper"

		width = 160
		height = 30
		self.paletteView = Window((width, height))
		self.paletteView.group = Group((0, 0, width, height))
		self.paletteView.group.label = TextBox((8, 7, 90, 18), "Increase Version when Export", sizeStyle="small")

		groupView = self.paletteView.group.getNSView()
		groupView.setAutoresizingMask_(NSViewWidthSizable)

		# macOS switch (NSSwitch), safely retrieved
		try:
			NSSwitch = objc.lookUpClass("NSSwitch")
		except Exception:
			NSSwitch = None

		if NSSwitch is not None:
			sw = NSSwitch.alloc().initWithFrame_(NSMakeRect(width - 48, 4, 40, 22))
			sw.setTarget_(self)
			sw.setAction_("toggle:")
			sw.setState_(1 if Glyphs.defaults[PREF_KEY] else 0)
			sw.setAutoresizingMask_(NSViewMinXMargin)
			groupView.addSubview_(sw)
			self.switch = sw

		self.dialog = groupView

	@objc.python_method
	def start(self):
		_ensure_engine()   # registers the observer only once

	def toggle_(self, sender):
		Glyphs.defaults[PREF_KEY] = bool(sender.state())

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

	# Compatibility fix: Glyphs calls these methods on palettes.
	_sortID = 0

	@objc.python_method
	def setSortID_(self, sortID):
		try:
			self._sortID = sortID
		except Exception as e:
			self.logToConsole("setSortID_: %s" % str(e))

	@objc.python_method
	def sortID(self):
		return self._sortID
