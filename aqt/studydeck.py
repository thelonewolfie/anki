# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
The window obtained, from main window "Tools>Study deck"
"""

from aqt.qt import *
import aqt
from aqt.utils import showInfo, openHelp, getOnlyText, shortcut, restoreGeom, saveGeom
from anki.hooks import addHook, remHook

class StudyDeck(QDialog):
    """
    nameFunc -- names, a function or none. Called to compute the new name on reset. Currently, it's always the list of all decks or None.
    origNames -- the names ? Either computed from nameFunc, or the list of all name of decks.
    filt -- the text written in the window, to filter the decks shown
    names -- set of decks to be shown. Subset of origname
    name -- the selected deck, only after accepting
    """
    def __init__(self, mw, names=None, accept=None, title=None,
                 help="studydeck", current=None, cancel=True,
                 parent=None, dyn=False, buttons=[], geomKey="default"):
        QDialog.__init__(self, parent or mw)
        self.mw = mw
        self.form = aqt.forms.studydeck.Ui_Dialog()
        self.form.setupUi(self)
        self.form.filter.installEventFilter(self)
        self.cancel = cancel
        addHook('reset', self.onReset)
        self.geomKey = "studyDeck-"+geomKey
        restoreGeom(self, self.geomKey)
        if not cancel:
            self.form.buttonBox.removeButton(
                self.form.buttonBox.button(QDialogButtonBox.Cancel))
        if buttons:
            for b in buttons:
                self.form.buttonBox.addButton(b, QDialogButtonBox.ActionRole)
        else:
            b = QPushButton(_("Add"))
            b.setShortcut(QKeySequence("Ctrl+N"))
            b.setToolTip(shortcut(_("Add New Deck (Ctrl+N)")))
            self.form.buttonBox.addButton(b, QDialogButtonBox.ActionRole)
            b.clicked.connect(self.onAddDeck)
        if title:
            self.setWindowTitle(title)
        if not names:
            names = sorted(self.mw.col.decks.allNames(dyn=dyn))
            self.nameFunc = None
            self.origNames = names
        else:
            self.nameFunc = names
            self.origNames = names()
        self.name = None
        self.ok = self.form.buttonBox.addButton(
            accept or _("Study"), QDialogButtonBox.AcceptRole)
        self.setWindowModality(Qt.WindowModal)
        self.form.buttonBox.helpRequested.connect(lambda: openHelp(help))
        self.form.filter.textEdited.connect(self.redraw)
        self.form.list.itemDoubleClicked.connect(self.accept)
        self.show()
        # redraw after show so position at center correct
        self.redraw("", current)
        self.exec_()

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress:
            if evt.key() == Qt.Key_Up:
                c = self.form.list.count()
                row = self.form.list.currentRow() - 1
                if row < 0:
                    row = c - 1
                self.form.list.setCurrentRow(row)
                return True
            elif evt.key() == Qt.Key_Down:
                c = self.form.list.count()
                row = self.form.list.currentRow() + 1
                if row == c:
                    row = 0
                self.form.list.setCurrentRow(row)
                return True
        return False

    def redraw(self, filt, focus=None):
        """filt -- text already entered
        focus -- the name on which to focus if its in the list of deck names
        """
        self.filt = filt
        self.focus = focus
        self.names = [n for n in self.origNames if self._matches(n, filt)]
        l = self.form.list
        l.clear()
        l.addItems(self.names)
        if focus in self.names:
            idx = self.names.index(focus)
        else:
            idx = 0
        l.setCurrentRow(idx)
        l.scrollToItem(l.item(idx), QAbstractItemView.PositionAtCenter)

    def _matches(self, name, filt):
        """whether all words of filt, separated by spaces, appear in
        name. This is how filter works."""
        name = name.lower()
        filt = filt.lower()
        if not filt:
            return True
        for word in filt.split(" "):
            if word not in name:
                return False
        return True

    def onReset(self):
        """Recompute the set of decks, show the new deck with same filter, same focus, but new name"""
        # model updated?
        if self.nameFunc:
            self.origNames = self.nameFunc()
        self.redraw(self.filt, self.focus)

    def accept(self):
        saveGeom(self, self.geomKey)
        remHook('reset', self.onReset)
        row = self.form.list.currentRow()
        if row < 0:
            showInfo(_("Please select something."))
            return
        self.name = self.names[self.form.list.currentRow()]
        QDialog.accept(self)

    def reject(self):
        saveGeom(self, self.geomKey)
        remHook('reset', self.onReset)
        QDialog.reject(self)

    def onAddDeck(self):
        row = self.form.list.currentRow()
        if row < 0:
            default = self.form.filter.text()
        else:
            default = self.names[self.form.list.currentRow()]
        n = getOnlyText(_("New deck name:"), default=default)
        if n:
            self.mw.col.decks.id(n)
            self.name = n
            # make sure we clean up reset hook when manually exiting
            remHook('reset', self.onReset)
            QDialog.accept(self)
