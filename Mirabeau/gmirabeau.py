import sys, os

import hildon
import pygtk
pygtk.require('2.0')
import gtk
import gettext
import dbus


from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

_ = gettext.gettext

gtk.gdk.threads_init()

from twisted.internet import glib2reactor
glib2reactor.install()
from twisted.internet import reactor

from coherence.base import Coherence

from coherence.extern.simple_config import Config
from coherence.extern.telepathy import connect

from telepathy.interfaces import ACCOUNT_MANAGER, ACCOUNT
from telepathy.interfaces import CONN_INTERFACE
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
     CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING

BASEDIR = os.path.dirname(__file__)
UIDIR = os.path.join(BASEDIR, "ui")
CONFIG_PATH = os.path.join(BASEDIR, "mirabeau.xml")

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

class MainWindow(hildon.StackableWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.set_title("Mirabeau")
        self.set_app_menu(self._create_menu())

        self.vbox = gtk.VBox()

        self.hbox_top = gtk.HBox()
        self.hbox_top.show()
        self.vbox.pack_start(self.hbox_top, expand=False)

        # top left
        self.settings_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.settings_button.set_label(_("Settings"))
        self.settings_button.connect('clicked', self.open_settings)
        self.settings_button.show()
        self.hbox_top.pack_start(self.settings_button)

        # top right
        self.chatroom_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.chatroom_button.set_label(_("Chatroom"))
        self.chatroom_button.show()
        self.hbox_top.pack_start(self.chatroom_button)

        self.hbox_middle = gtk.HBox()
        self.hbox_middle.show()
        self.vbox.pack_start(self.hbox_middle, expand=False)

        # middle left
        self.local_devices_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.local_devices_button.set_label(_("Local Devices"))
        self.local_devices_button.connect('clicked', self.open_local_devices)
        self.local_devices_button.show()
        self.hbox_middle.pack_start(self.local_devices_button)

        # middle right
        self.remote_devices_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.remote_devices_button.set_label(_("Remote Devices"))
        self.remote_devices_button.show()
        self.hbox_middle.pack_start(self.remote_devices_button)

        # bottom center
        self.status_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.status_button.set_label("status")
        self.status_button.connect('clicked', self.update_status)
        self.status_button.show()
        self.vbox.pack_start(self.status_button, expand=False)

        self.add(self.vbox)
        self.vbox.show()

        self.connect('delete-event', self._exit_cb)

        self.load_config()
        if self.config.get("mirabeau").get("account"):
            self.start_coherence()
        else:
            self.coherence_instance = None
            self.status_changed_cb(CONNECTION_STATUS_DISCONNECTED, "")

    def _create_menu(self):
        menu = hildon.AppMenu()

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label(_('Foo'))
        menu.append(button)

        menu.show_all()
        return menu

    def _exit_cb(self, window, event):
        reactor.stop()

    def load_config(self):
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

    def start_coherence(self, restart=False):
        if restart:
            if self.coherence_instance:
                dfr = self.coherence_instance.shutdown()
                dfr.addCallback(lambda result: self.startCoherence())
                return dfr
            else:
                self.coherence_instance = Coherence(self.config)
        else:
            self.coherence_instance = Coherence(self.config)
        if self.coherence_instance:
            mirabeau_instance = self.coherence_instance.mirabeau
            conn_obj = mirabeau_instance.tube_publisher.conn[CONN_INTERFACE]
            handle = conn_obj.connect_to_signal('StatusChanged',
                                                self.status_changed_cb)
            self.status_update_handle = handle

    def stop_coherence(self):
        def stopped(result):
            self.coherence_instance.clear()
            self.coherence_instance = None
            print ">>", result

        dfr = self.coherence_instance.shutdown()
        dfr.addBoth(stopped)
        return dfr

    def status_changed_cb(self, status, reason):
        if status == CONNECTION_STATUS_CONNECTING:
            text = _("Connecting. Please wait")
        elif status == CONNECTION_STATUS_CONNECTED:
            text = _('Connected')
        elif status == CONNECTION_STATUS_DISCONNECTED:
            text = _('Disconnected')
        self.status_button.set_label(text)

    def update_status(self, widget):
        if self.coherence_instance:
            self.stop_coherence()
        else:
            self.start_coherence()

    def open_settings(self, widget):
        dialog = SettingsDialog(self)
        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT:
            mirabeau_section = self.config.get("mirabeau")
            mirabeau_section.set("chatroom", dialog.get_chatroom())
            mirabeau_section.set("conference-server", dialog.get_conf_server())
            mirabeau_section.set("account", dialog.get_account())
            self.config.set("mirabeau", mirabeau_section)
            self.config.save()
            self.load_config()

            # TODO: send notification using dbus

        dialog.destroy()

    def open_local_devices(self, widget):
        window = LocalDevicesWindow(self)
        window.show_all()

class LocalDevicesWindow(hildon.StackableWindow):

    def __init__(self, parent):
        super(LocalDevicesWindow, self).__init__()
        self.main_window = parent
        self.set_title(_("Local Devices"))

        self.devices_view = hildon.GtkTreeView(gtk.HILDON_UI_MODE_EDIT)
        model = gtk.ListStore(str)
        self.devices_view.set_model(model)
        column = gtk.TreeViewColumn('Name', gtk.CellRendererText(), text = 0)
        self.devices_view.append_column(column)

        self.devices_view.show()
        self.add(self.devices_view)

        coherence = self.main_window.coherence_instance
        coherence.connect(self.device_found, 'Coherence.UPnP.RootDevice.detection_completed')
        coherence.connect(self.device_removed, 'Coherence.UPnP.RootDevice.removed')
        for device in coherence.devices:
            self.device_found(device)

    def device_found(self, device=None):
        name = '%s (%s)' % (device.get_friendly_name(), ':'.join(device.get_device_type().split(':')[3:5]))
        model = self.devices_view_view.get_model()
        model.append([name])

    def device_removed(self,usn=None):
        print usn
        # TODO

class SettingsDialog(gtk.Dialog):

    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent=parent,
                                             buttons = (gtk.STOCK_SAVE,
                                                        gtk.RESPONSE_ACCEPT))
        self.set_title("Settings")

        self.accounts = connect.gabble_accounts()
        bus = dbus.SessionBus()
        mirabeau_section = parent.config.get("mirabeau")

        # account
        self.account_picker = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT,
                                                  hildon.BUTTON_ARRANGEMENT_VERTICAL)
        selector = hildon.TouchSelectorEntry(text = True)
        self.account_picker.set_title(_('Account:'))
        for account_obj_path in self.accounts:
            account_obj = bus.get_object(ACCOUNT_MANAGER, account_obj_path)
            norm_name = account_obj.Get(ACCOUNT, 'NormalizedName')
            nick_name = account_obj.Get(ACCOUNT, 'Nickname')
            label = "%s - %s" % (nick_name, norm_name)
            selector.append_text(label)

        self.account_picker.set_selector(selector)

        conf_account = mirabeau_section.get("account")
        if conf_account and conf_account in self.accounts:
            index = self.accounts.index(conf_account)
            self.account_picker.set_active(index)

        self.vbox.pack_start(self.account_picker, expand=False)

        # conf server
        self.conf_server_label = gtk.Label(_("Conference Server"))
        self.conf_server_entry = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.conf_server_entry.set_text(mirabeau_section.get("conference-server", ""))
        self.conf_server_hbox = gtk.HBox()
        self.conf_server_hbox.pack_start(self.conf_server_label, expand=False)
        self.conf_server_hbox.pack_start(self.conf_server_entry, expand=True)
        self.vbox.pack_start(self.conf_server_hbox, expand=False)

        # chatroom name
        self.chatroom_label = gtk.Label(_("Chatroom"))
        self.chatroom_entry = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.chatroom_entry.set_text(mirabeau_section.get("chatroom", ""))
        self.chatroom_hbox = gtk.HBox()
        self.chatroom_hbox.pack_start(self.chatroom_label, expand=False)
        self.chatroom_hbox.pack_start(self.chatroom_entry, expand=True)
        self.vbox.pack_start(self.chatroom_hbox, expand=False)

        self.vbox.show_all()

    def get_chatroom(self):
        return self.chatroom_entry.get_text()

    def get_conf_server(self):
        return self.conf_server_entry.get_text()

    def get_account(self):
        selector = self.account_picker.get_selector()
        return self.accounts[selector.get_active(0)]

if __name__ == '__main__':

    def start():
        main_window = MainWindow()
        main_window.show_all()
        gtk.main()

    reactor.callWhenRunning(start)
    reactor.run()
