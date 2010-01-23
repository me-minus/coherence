import sys, os
import uuid

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

from coherence.extern.simple_config import Config, XmlDictObject
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

MS_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, 'coherence.org')

"""
TODO:

- local device config (en/disable tube export)
- chatroom
- player
- if no account configured start coherence with mirabeau deactivated
- dis/reconnect when settings are changed

"""

class MainWindow(hildon.StackableWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.set_title("Mirabeau")
        self.set_app_menu(self._create_menu())
        self.connect('delete-event', self._exit_cb)

        self.vbox = gtk.VBox()

        self.devices_view = hildon.GtkTreeView(gtk.HILDON_UI_MODE_EDIT)
        model = gtk.ListStore(str)
        self.devices_view.set_model(model)
        column = gtk.TreeViewColumn('Name', gtk.CellRendererText(), text = 0)
        self.devices_view.append_column(column)

        self.devices_view.show()
        self.vbox.pack_start(self.devices_view, expand=True)

        self.chatroom_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.chatroom_button.set_label(_("Chatroom"))
        self.vbox.pack_start(self.chatroom_button, expand=False)

        self.add(self.vbox)
        self.vbox.show_all()

        self.status_changed_cb(CONNECTION_STATUS_DISCONNECTED, "")
        self.load_config()
        self.start_coherence()

    def device_found(self, device):
        name = device.get_friendly_name()
        model = self.devices_view.get_model()
        model.append([name])

    def device_removed(self, usn):
        print usn
        # TODO

    def _create_menu(self):
        menu = hildon.AppMenu()

        self.settings_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.settings_button.set_label(_("Settings"))
        self.settings_button.connect('clicked', self.open_settings)
        self.settings_button.show()
        menu.append(self.settings_button)

        self.status_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.status_button.set_label("status")
        self.status_button.connect('clicked', self.update_status)
        self.status_button.show()
        menu.append(self.status_button)

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

    def reload_config(self):
        self.config.save()
        self.load_config()

    def enable_mirabeau(self):
        self.config.set("enable_mirabeau", "yes")
        self.reload_config()

    def disable_mirabeau(self):
        self.config.set("enable_mirabeau", "no")
        self.reload_config()

    def platform_media_directories(self):
        candidates = ["~/MyDocs/.images", "~/MyDocs/.sounds", "~/MyDocs/.videos",
                      "~/MyDocs/DCIM", "~/MyDocs/Music", "~/MyDocs/Videos",
                      ]
        expanded = [os.path.expanduser(c) for c in candidates]
        dirs = [c for c in expanded if os.path.isdir(c)]
        return dirs

    def enable_media_server(self):
        plugins = self.config.get("plugin")
        if not plugins:
            directories = self.platform_media_directories()
            opts = dict(uuid=MS_UUID, name="N900", content=",".join(directories),
                        backend="FSStore", active="yes")
            plugin = XmlDictObject(initdict=opts)
            self.config.set("plugin", plugin)
        else:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
            for plugin in plugins:
                if plugin.get("uuid") == MS_UUID:
                    plugin.active = "yes"
                    break
            self.config.set("plugins", plugins)
        self.reload_config()

    def disable_media_server(self):
        plugins = self.config.get("plugin")
        if plugins:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
            for plugin in plugins:
                if plugin.get("uuid") == MS_UUID:
                    plugin.active = "no"
                    break
            self.config.set("plugins", plugins)
            self.reload_config()

    def media_server_enabled(self):
        plugins = self.config.get("plugin")
        if plugins:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
            print type(plugins), repr(plugins)
            for plugin in plugins:
                if plugin.get("uuid") == MS_UUID and \
                   plugin.active == "yes":
                    return True
        return False

    def start_coherence(self, restart=False):
        def start():
            if self.config.get("mirabeau").get("account"):
                self.enable_mirabeau()
            else:
                self.disable_mirabeau()
            self.coherence_instance = Coherence(self.config)

        if restart:
            if self.coherence_instance:
                dfr = self.coherence_instance.shutdown(force=True)
                dfr.addCallback(lambda result: self.start_coherence())
                return dfr
            else:
               start()
        else:
            start()
        if self.coherence_instance:
            coherence = self.coherence_instance
            mirabeau_instance = coherence.mirabeau
            conn_obj = mirabeau_instance.tube_publisher.conn[CONN_INTERFACE]
            handle = conn_obj.connect_to_signal('StatusChanged',
                                                self.status_changed_cb)
            self.status_update_handle = handle

            coherence.connect(self.device_found, 'Coherence.UPnP.RootDevice.detection_completed')
            coherence.connect(self.device_removed, 'Coherence.UPnP.RootDevice.removed')
            for device in coherence.devices:
                self.device_found(device)

    def stop_coherence(self):
        def stopped(result):
            self.coherence_instance.clear()
            self.coherence_instance = None

        dfr = self.coherence_instance.shutdown(force=True)
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
            self.reload_config()

            if dialog.ms_enabled():
                self.enable_media_server()
            else:
                self.disable_media_server()
            self.start_coherence(restart=True)

        dialog.destroy()

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

        # MS toggle
        self.ms_toggle = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.ms_toggle.set_label("Share the media files of this device")
        self.ms_toggle.set_active(parent.media_server_enabled())
        self.vbox.pack_start(self.ms_toggle, expand=False)

        self.vbox.show_all()

    def get_chatroom(self):
        return self.chatroom_entry.get_text()

    def get_conf_server(self):
        return self.conf_server_entry.get_text()

    def get_account(self):
        selector = self.account_picker.get_selector()
        return self.accounts[selector.get_active(0)]

    def ms_enabled(self):
        return self.ms_toggle.get_active()

if __name__ == '__main__':
    main_window = MainWindow()
    main_window.show_all()
    reactor.run()
