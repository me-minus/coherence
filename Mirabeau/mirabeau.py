import sys, os
from PyQt4 import QtGui, uic
from PyQt4 import QtCore
from PyQt4.QtCore import pyqtRemoveInputHook

from coherence.extern.simple_config import Config
from coherence.extern.telepathy import connect
from telepathy.interfaces import ACCOUNT_MANAGER, ACCOUNT
import dbus

BASEDIR = os.path.dirname(__file__)
UIDIR = os.path.join(BASEDIR, "ui")
CONFIG_PATH = os.path.join(BASEDIR, "mirabeau.xml")

def pdb(locals):
    pyqtRemoveInputHook()
    import pdb; pdb.set_trace()



class UILoader(object):
    uifilename = ""

    def __init__(self, parent=None):
        uifile = os.path.join(UIDIR, self.uifilename)
        self.ui = uic.loadUi(uifile, parent)
        self.connectSignals()

    def __getattr__(self, attr):
        if attr != "ui":
            return getattr(self.ui, attr)

class Window(UILoader):
    uifilename = "main.ui"

    def connectSignals(self):
        self.connect(self.settingsButton, QtCore.SIGNAL("clicked()"),
                     self.openSettings)
        #self.config = Config(CONFIG_PATH, root='config')


    def openSettings(self):
        self._setting_win = Settings()
        #self._setting_win.config = self.config
        self._setting_win.show()

class Settings(UILoader):
    uifilename = "settings.ui"

    def connectSignals(self):
        self.connect(self.buttonBox, QtCore.SIGNAL("accepted()"),
                     self.accepted)
        self.connect(self.buttonBox, QtCore.SIGNAL("rejected()"),
                     self.rejected)

        # fill accounts box
        bus = dbus.SessionBus()
        model = self.accountsBox.model()
        self.accounts = {}
        for account_obj_path in connect.gabble_accounts():
            account_obj = bus.get_object(ACCOUNT_MANAGER, account_obj_path)
            norm_name = account_obj.Get(ACCOUNT, 'NormalizedName')
            nick_name = account_obj.Get(ACCOUNT, 'Nickname')
            #pdb(locals())
            label = "%s - %s" % (nick_name, norm_name)
            self.accounts[label] = account_obj_path
            model.appendRow(QtGui.QStandardItem(label))

    def accepted(self):
        print "account", self.accounts[str(self.accountsBox.currentText())]
        print "conf server", str(self.confServerTextEdit.toPlainText())
        print "chatroom", str(self.chatRoomTextEdit.toPlainText())

    def rejected(self):
        print "bah"

if __name__ == '__main__':
    # Creating Qt application
    app = QtGui.QApplication(sys.argv)

    win = Window()
    win.show()

    #Initing application
    sys.exit(app.exec_())
