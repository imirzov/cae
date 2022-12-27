#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""© Ihor Mirzov, 2019-2023
Distributed under GNU General Public License v3.0

TODO Run internal help in a separated slave window. It will allow to
align dialog and slave help browser via connection.align_windows().

Dialog window to create/edit keyword implementation.
Called via double click on keyword in the treeView.
Keyword implementation is defined by its name and inp_code.
Dialog is created via Factory class, run_master_dialog() method.
So this dialog is a master, help webbrowser (if any) is a slave.
"""

# Standard modules
import os
import sys
import logging

# External modules
from PyQt5 import QtWidgets, uic, QtCore, QtGui, QtWebEngineWidgets
from PyQt5.QtWidgets import QMessageBox

# My modules
sys_path = os.path.abspath(__file__)
sys_path = os.path.dirname(sys_path)
sys_path = os.path.join(sys_path, '..')
sys_path = os.path.normpath(sys_path)
sys_path = os.path.realpath(sys_path)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
from path import p
from settings import s
from model.kom import ItemType, KWL, KWT
import gui.window

ITEM = None
TEXTEDIT = None


class Group(QtWidgets.QWidget):
    """GroupBox with Argument widgets."""

    def __init__(self, argument):
        self.argument = argument
        super().__init__()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        self.gbox = QtWidgets.QGroupBox()
        self.gbox.setCheckable(True)
        self.gbox.setChecked(False)
        self.gbox.setTitle(argument.name)
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.setContentsMargins(20, 10, 8, 0)
        self.arguments = argument.get_arguments()
        build_widgets(self.arguments, box_layout)
        self.gbox.setLayout(box_layout)
        v_layout.addWidget(self.gbox)
        self.setLayout(v_layout)
        self.gbox.clicked.connect(change)

    def text(self):
        txt = ''
        if self.gbox.isEnabled() and self.gbox.isChecked():
            txt = ', ' + self.argument.name
        return txt

    def reset(self):
        self.gbox.setChecked(False)
        reset(self.arguments)


class ArgumentWidget(QtWidgets.QWidget):
    """ArgumentWidget is used to visualize Arguments."""

    def __init__(self, argument, widgets, reverse_pos=False):
        assert type(argument.name) is str, 'Wrong name type: {}'.format(type(argument.name))
        assert type(widgets) is list, 'Wrong widgets type: {}'.format(type(widgets))
        self.name = argument.name
        self.widgets = widgets
        self.required = argument.get_required()
        self.newline = argument.get_newline()
        self.readonly = argument.get_readonly()
        super().__init__()

        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        if argument.comment:
            comment_label = QtWidgets.QLabel(argument.comment)
            comment_label.setStyleSheet('color: Blue;')
            self.v_layout.addWidget(comment_label)

        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.horizontal_layout.setContentsMargins(0, 0, 0, 10) # bottom margin
        self.horizontal_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.label = None
        if '|' in self.name:
            """Mutually exclusive arguments
            name='FREQUENCY|TIME POINTS'
            """
            self.label = QtWidgets.QComboBox()
            self.label.addItems(self.name.split('|'))
            self.label.text = self.label.currentText
            self.label.currentIndexChanged.connect(change)
        elif self.name:
            self.label = QtWidgets.QLabel(self.name)
            self.label.linkHovered.connect(change)
        if self.label:
            # Label goes after the checkbox
            pos = 0
            if reverse_pos:
                pos = 1
            widgets.insert(pos, self.label)

        # Mark required argument
        if self.required:
            required_label = QtWidgets.QLabel()
            required_label.setText('*')
            required_label.setStyleSheet('color:Red;')
            widgets.insert(0, required_label)

        for w in widgets:
            if hasattr(w, 'setReadOnly'):
                w.setReadOnly(self.readonly)
            self.horizontal_layout.addWidget(w)
        self.v_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.v_layout)

        # Recursion for nested arguments/groups
        build_widgets(argument.get_arguments(), self.v_layout)

    def setEnabled(self, status):
        for w in self.widgets:
            w.setEnabled(status)

    def text(self):
        if not self.w.isEnabled():
            return ''
        if not self.isEnabled():
            return ''
        newline = ', '
        if self.newline:
            newline = '\n'
        ct = ''
        if hasattr(self.w, 'currentText'):
            ct = self.w.currentText()
        if hasattr(self.w, 'toPlainText'):
            ct = self.w.toPlainText()
        elif hasattr(self.w, 'text'):
            ct = self.w.text()
        if ct and not ct.startswith('!!! Create *'):
            if self.name:
                return newline + self.name + '=' + ct
            else:
                return newline + ct
        else:
            return ''


class GroupWidget(QtWidgets.QWidget):
    """Custom widget container - Group."""

    def __init__(self, argument, layout):
        super().__init__()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.insertLayout(0, layout)
        if hasattr(argument, 'comment') and argument.comment:
            comment_label = QtWidgets.QLabel(argument.comment)
            comment_label.setStyleSheet('color: Blue;')
            v_layout.insertWidget(0, comment_label)
        self.setLayout(v_layout)

    def text(self, *args):
        return '\n' if self.newline else ''

    def reset(self):
        reset(self.arguments)


class Box(GroupWidget):
    """GroupWidget."""

    def __init__(self, argument, layout):
        self.newline = argument.get_newline()
        self.arguments = argument.get_arguments()
        layout.setContentsMargins(0, 0, 0, 0)
        super().__init__(argument, layout)
        build_widgets(self.arguments, layout)


class HBox(Box):
    """GroupWidget with horizontal layout."""

    def __init__(self, argument):
        super().__init__(argument, QtWidgets.QHBoxLayout())


class VBox(Box):
    """GroupWidget with vertical layout."""

    def __init__(self, argument):
        super().__init__(argument, QtWidgets.QVBoxLayout())


class Or(GroupWidget):
    """GroupWidget with radiobuttons."""

    def __init__(self, argument, layout):
        self.newline = argument.get_newline()
        self.arguments = argument.get_arguments()
        layout.setContentsMargins(0, 0, 0, 0)
        for i, a in enumerate(self.arguments):
            hl = QtWidgets.QHBoxLayout()
            rb = QtWidgets.QRadioButton()
            hl.addWidget(rb)
            build_widgets([a], hl) # build a.widget
            layout.addLayout(hl)
            rb.setChecked(not bool(i))
            a.widget.setEnabled(not bool(i))
            rb.toggled.connect(a.widget.setEnabled)
            rb.toggled.connect(change)
        super().__init__(argument, layout)


class HOr(Or):
    """GroupWidget with radiobuttons. Horizontal layout."""

    def __init__(self, argument):
        hbox = QtWidgets.QHBoxLayout()
        super().__init__(argument, hbox)


class VOr(Or):
    """GroupWidget with radiobuttons. Vertical layout."""

    def __init__(self, argument):
        hbox = QtWidgets.QVBoxLayout()
        super().__init__(argument, hbox)


class Combo(ArgumentWidget):
    """QComboBox widget box with label."""

    def __init__(self, argument):
        self.argument = argument
        self.w = QtWidgets.QComboBox()

        # Try to get existing implementations
        if hasattr(argument, 'use') and argument.use:
            implementations = [impl.name for impl in KWT.get_implementations(argument.use)]
            self.w.addItem('')
            if implementations:
                self.w.addItems(implementations)
            else:
                self.w.setStyleSheet('color: Red;')
                self.w.addItem('!!! Create ' + argument.use + ' first !!!')

        if argument.value:
            self.w.addItems(argument.value.split('|'))

        # QComboBox doesn't expand by default
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1) # expand horizontally
        self.w.setSizePolicy(sizePolicy)

        self.w.currentIndexChanged.connect(change)
        super().__init__(argument, [self.w])

    def reset(self):
        self.w.setCurrentIndex(0)


class Text(ArgumentWidget):
    """QTextEdit widget with label."""

    def __init__(self, argument):
        self.argument = argument
        self.w = QtWidgets.QTextEdit()
        super().__init__(argument, [self.w])
        self.setText(argument.value)
        self.setEnabled = self.w.setEnabled
        self.w.textChanged.connect(lambda: change(None))

    def reset(self):
        self.setText(self.argument.value)

    def setText(self, text):
        self.w.clear()
        for line in text.split('\\n'):
            self.w.append(line)
        font = self.w.document().defaultFont()
        fontMetrics = QtGui.QFontMetrics(font)
        textSize = fontMetrics.size(0, self.w.toPlainText())
        textHeight = textSize.height() + 10 # Need to tweak
        self.w.setMaximumHeight(textHeight)


class Line(ArgumentWidget):
    """QLineEdit widget with label."""

    def __init__(self, argument):
        self.argument = argument
        self.w = QtWidgets.QLineEdit()
        self.w.setText(argument.value)
        self.w.textChanged.connect(change)
        self.setEnabled = self.w.setEnabled
        super().__init__(argument, [self.w])

    def reset(self):
        self.w.setText(self.argument.value)


class Int(Line):
    """Text widget accepting int number."""

    def __init__(self, argument):
        super().__init__(argument)
        self.w.setValidator(QtGui.QIntValidator())


class Float(Line):
    """Text widget accepting float number."""

    def __init__(self, argument):
        super().__init__(argument)
        self.w.setValidator(QtGui.QDoubleValidator())


class Bool(ArgumentWidget):
    """Checkbox widget with label."""

    def __init__(self, argument):
        self.argument = argument
        self.w = QtWidgets.QCheckBox()
        self.w.clicked.connect(change)
        super().__init__(argument, [self.w], reverse_pos=True)
        if argument.get_required():
            self.w.setChecked(True)

    def text(self):
        if self.w.isEnabled() and self.w.isChecked():
            return ', ' + self.label.text()
        else:
            return ''

    def reset(self):
        self.w.setChecked(self.argument.get_required())


class SelectFileWidget(ArgumentWidget):
    """A custom widget to select files. With label."""

    def __init__(self, argument):
        self.argument = argument
        self.w = QtWidgets.QLineEdit()
        self.push_button = QtWidgets.QPushButton('...', None)
        self.push_button.clicked.connect(self.get_file)
        self.push_button.setFixedSize(30, 30)
        self.w.textChanged.connect(change)
        self.text = self.w.text
        super().__init__(argument, [self.w, self.push_button])

    def get_file(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Single File', '', '*.inp')[0]
        self.w.setText(fname)

    def reset(self):
        self.w.setText(self.argument.value)


def build_widgets(arguments, parent_layout):
    """Build widgets for direct children of the Keyword.
    Recursion for nested arguments/groups is implemented
    inside GroupWidget/ArgumentWidget - not here.
    """
    for a in arguments:
        txt = '{} has neither "form" nor "user" attributes'.format(a)
        assert hasattr(a, 'form') or hasattr(a, 'use'), txt

        if hasattr(a, 'form') and a.form:
            form = a.form
        if hasattr(a, 'use') and a.use:
            form = Combo.__name__
        a.widget = eval(form)(a) # argument's widget
        parent_layout.addWidget(a.widget)


def change(data, arguments=[], append=False):
    """Update piece of INP-code in the textEdit when
    a signal is emitted in any of argument's widgets.
    """
    global ITEM, TEXTEDIT
    if ITEM.itype == ItemType.IMPLEMENTATION:
        TEXTEDIT.clear()
        return
    if not append:
        TEXTEDIT.setText(ITEM.name)
    if not arguments and not append:
        arguments = ITEM.get_arguments()
    for a in arguments:
        w = a.widget
        if w is None:
            logging.error(a.name + ' has no widget')
            continue
        old_value = TEXTEDIT.toPlainText()
        new_value = w.text() if w.isEnabled() else '' # argument value
        if old_value.endswith('\n') and new_value.startswith(', '):
            new_value = new_value[2:]
        TEXTEDIT.setText(old_value + new_value)

        # Recursively walk through the whole keyword arguments
        args = a.get_arguments()
        if args:
            change(data, args, append=True)


def reset(arguments):
    """Reset argument's widgets to initial state."""
    for a in arguments:
        w = a.widget
        if hasattr(w, 'reset'):
            w.reset()


class KeywordDialog(QtWidgets.QDialog):

    @gui.window.init_wrapper()
    def __init__(self, item):
        """Load form and show the dialog."""
        # Load UI form - produces huge amount of redundant debug logs
        logging.disable() # switch off logging
        super().__init__() # create dialog window
        uic.loadUi(p.dialog_xml, self) # load empty dialog form
        logging.disable(logging.NOTSET) # switch on logging

        global ITEM, TEXTEDIT
        ITEM = item # the one was clicked in the treeView
        TEXTEDIT = self.textEdit
        self.info = None # WindowInfo will be set in @init_wrapper
        self.arguments = []

        # Set window icon (different for each keyword)
        # TODO Test if it is Windows-specific
        icon_name = item.name.replace('*', '') + '.png'
        icon_name = icon_name.replace(' ', '_')
        icon_name = icon_name.replace('-', '_')
        icon_path = os.path.join(p.img, 'icon_' + icon_name.lower())
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)
        self.setWindowTitle(item.name)

        # Fill textEdit with implementation's inp_code
        if item.itype == ItemType.IMPLEMENTATION:
            for line in item.inp_code:
                TEXTEDIT.append(line)

        # Create widgets for each keyword argument
        elif item.itype == ItemType.KEYWORD:
            kw = KWL.get_keyword_by_name(item.name)
            self.arguments = kw.get_arguments()
            build_widgets(kw.get_arguments(), self.widgets_layout)
            change(None) # fill textEdit widget with default inp_code

        # Generate html help page from official manual
        self.doc = QtWebEngineWidgets.QWebEngineView()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2) # expand horizontally
        self.doc.setSizePolicy(sizePolicy)
        self.url = self.get_help_url()
        self.show_help = s.show_help

        self.show()

    def reset(self):
        """Reset all widgets to initial state."""
        reset(self.arguments)
        change(None) # update QTextEdit with INP-code

    def accept(self, arguments=None, depth=0):
        """Check if all required fields are filled."""
        ok = True
        if arguments is None:
            global ITEM
            arguments = ITEM.get_arguments()
        for a in arguments:
            w = a.widget
            if hasattr(w, 'required') and w.required:
                name = w.name # argument name
                value = w.text() # argument value
                if not value:
                    msg = 'Fill all required fields'
                    if name:
                        msg += ' ' + name
                    else:
                        msg += '!'
                    QMessageBox.warning(self, 'Warning', msg)
                    return False
            ok = ok and self.accept(a.get_arguments(), depth+1)
        if depth:
            return ok
        if depth==0 and ok:
            super().accept()

    def ok(self):
        """Return piece of created code for the .inp-file."""
        global TEXTEDIT
        return TEXTEDIT.toPlainText().strip().split('\n')

    def get_help_url(self):
        """Get URL to the local doc page."""
        global ITEM
        if ITEM.itype == ItemType.KEYWORD:
            keyword_name = ITEM.name[1:] # cut star
        if ITEM.itype == ItemType.IMPLEMENTATION:
            keyword_name = ITEM.parent.name[1:] # cut star

        # Avoid spaces and hyphens in html page names
        import re
        html_page_name = re.sub(r'[ -]', '_', keyword_name)
        url = os.path.join(p.doc, html_page_name + '.html')
        return url

    def show_hide_internal_help(self, click):
        """Show / Hide HTML help."""
        size = QtWidgets.QApplication.primaryScreen().availableSize()
        import math
        w = math.floor(size.width() / 3)
        h = self.geometry().height()
        if click:
            self.show_help = not self.show_help
        else:
            self.show_help = s.show_help

        # To show or not to show
        if self.show_help:
            self.doc.load(QtCore.QUrl.fromLocalFile(self.url)) # load help document
            self.setMaximumWidth(size.width())
            self.setMinimumWidth(size.width())
            self.resize(size.width(), h)
            self.horizontal_layout.addWidget(self.doc)
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Help)\
                .setText('Hide help')
        else:
            self.doc.setParent(None) # remove widget
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Help)\
                .setText('Help')
            self.setMaximumWidth(w)
            self.setMinimumWidth(500)
            self.resize(w, h)


def test_dialog():
    """Prepare logging."""
    logging.getLogger().setLevel(logging.NOTSET)
    fmt = logging.Formatter('%(levelname)s: %(message)s')
    for h in logging.getLogger().handlers:
        h.setFormatter(fmt)

    """Create keyword dialog."""
    app = QtWidgets.QApplication(sys.argv)
    item = KWL.get_keyword_by_name('*CONSTRAINT')
    from gui.window import df
    df.run_master_dialog(item) # 0 = cancel, 1 = ok


if __name__ == '__main__':
    test_dialog()
