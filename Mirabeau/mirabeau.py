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

DEFAULT_CONFIG="""\
<config>
  <serverport>30020</serverport>
  <use_dbus>yes</use_dbus>
  <enable_mirabeau>yes</enable_mirabeau>
  <mirabeau>
   <chatroom>Mirabeau</chatroom>
   <conference-server>conference.jabber.org</conference-server>
   <manager>gabble</manager>
   <protocol>jabber</protocol>
   <account>%(default_account)s</account>
  </mirabeau>
</config>
"""


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
        self.loadConfig()

    def loadConfig(self):
        if not os.path.exists(CONFIG_PATH):
            try:
                default_account = connect.gabble_accounts()[0]
            except IndexError:
                default_account = ''

            cfg = DEFAULT_CONFIG % locals()
            fd = open(CONFIG_PATH, "w")
            fd.write(cfg)
            fd.close()

        self.config = Config(CONFIG_PATH, root='config')

    def openSettings(self):
        self._setting_win = Settings(self)
        self._setting_win.show()

class Settings(UILoader):
    uifilename = "settings.ui"

    def __init__(self, parent):
        self.parent = parent
        super(Settings, self).__init__()

    def connectSignals(self):
        self.connect(self.buttonBox, QtCore.SIGNAL("accepted()"),
                     self.accepted)
        self.connect(self.buttonBox, QtCore.SIGNAL("rejected()"),
                     self.rejected)

        mirabeau_section = self.parent.config.get("mirabeau")
        self.confServerTextEdit.setText(mirabeau_section.get("conference-server"))
        self.chatRoomTextEdit.setText(mirabeau_section.get("chatroom"))

        # fill accounts box
        bus = dbus.SessionBus()
        model = self.accountsBox.model()
        self.accounts = connect.gabble_accounts()
        for account_obj_path in self.accounts:
            account_obj = bus.get_object(ACCOUNT_MANAGER, account_obj_path)
            norm_name = account_obj.Get(ACCOUNT, 'NormalizedName')
            nick_name = account_obj.Get(ACCOUNT, 'Nickname')
            label = "%s - %s" % (nick_name, norm_name)
            model.appendRow(QtGui.QStandardItem(label))

        #pdb(locals())

        conf_account = mirabeau_section.get("account")
        if conf_account and conf_account in self.accounts:
            index = self.accounts.index(conf_account)
            self.accountsBox.setCurrentIndex(index)


    def accepted(self):
        mirabeau_section = self.parent.config.get("mirabeau")
        mirabeau_section.set("chatroom",
                             str(self.chatRoomTextEdit.text()))
        mirabeau_section.set("conference-server",
                             str(self.confServerTextEdit.text()))
        mirabeau_section.set("account",
                             self.accounts[self.accountsBox.currentIndex()])
        self.parent.config.set("mirabeau", mirabeau_section)
        self.parent.config.save()
        self.parent.loadConfig()

        # TODO: send notification using dbus

    def rejected(self):
        # FIXME: remove this if not used later on.
        pass

if __name__ == '__main__':
    # Creating Qt application
    app = QtGui.QApplication(sys.argv)

    win = Window()
    win.show()

    #Initing application
    sys.exit(app.exec_())
