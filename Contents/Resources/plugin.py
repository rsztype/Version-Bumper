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
# Motore condiviso: un solo osservatore dell'export per tutta l'app,
# a prescindere da quante finestre/palette sono aperte.
# ----------------------------------------------------------------------
class _RSZBumpEngine(NSObject):

	def init(self):
		self = objc.super(_RSZBumpEngine, self).init()
		self.lastBump = 0.0
		return self

	def documentExported_(self, notification):
		try:
			if not Glyphs.defaults[PREF_KEY]:      # switch OFF -> non fa nulla
				return
			now = NSDate.date().timeIntervalSince1970()
			if now - self.lastBump < 10.0:         # debounce per batch di instances
				return
			self.lastBump = now

			font = Glyphs.font
			if font is None:
				return

			font.versionMinor += 1
			if font.versionMinor > 999:            # rollover 1.999 -> 2.000
				font.versionMajor += 1
				font.versionMinor = 0

			if font.parent:                        # scrive nel pannello Info e salva
				font.parent.saveDocument_(None)

			Glyphs.showNotification(
				"RSZ Version Bumper",
				"Versione \u2192 %d.%03d" % (font.versionMajor, font.versionMinor)
			)
		except:
			import traceback
			print(traceback.format_exc())


_engine = None


def _ensure_engine():
	global _engine
	if _engine is None:
		_engine = _RSZBumpEngine.alloc().init()
		NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
			_engine, "documentExported:", "GSDocumentWasExportedNotification", None)
	return _engine


# ----------------------------------------------------------------------
# Palette: l'interruttore nella colonna di destra.
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

		# interruttore macOS (NSSwitch), recuperato in modo sicuro
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
		_ensure_engine()   # registra l'osservatore una sola volta

	def toggle_(self, sender):
		Glyphs.defaults[PREF_KEY] = bool(sender.state())

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

	# Fix di compatibilita: Glyphs chiama questi metodi sulle palette.
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
