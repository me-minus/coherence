
"""
dependencies:

- python-gst0.10
- python-dbus
- python-hildon
- python-gtk2
- python-telepathy
- python-pkg-resources
- python-setuptools
- python-twisted
"""

import sys, os
import uuid

import hildon
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import gettext
import dbus

from pkg_resources import resource_filename

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

_ = gettext.gettext

gtk.gdk.threads_init()

from twisted.internet import glib2reactor
glib2reactor.install()
from twisted.internet import reactor

from coherence.base import Coherence

from coherence.upnp.core.utils import parse_xml
from coherence.extern.simple_config import Config, XmlDictObject
from coherence.extern.telepathy import connect
from coherence.upnp.core import DIDLLite
from coherence.extern.et import ET

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
  <plugin active="yes">
    <uuid>%(MR_UUID)s</uuid>
    <name>N900 Media Renderer</name>
    <backend>GStreamerPlayer</backend>
  </plugin>
</config>
"""

MS_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'coherence.org'))
MR_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'gstreamer.org'))

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

        self.devices_view = DevicesView()
        self.devices_view.connect('row-activated', self._row_activated_cb)
        self.area = hildon.PannableArea()
        self.area.add(self.devices_view)
        self.vbox.pack_start(self.area, expand=True)

        self.chatroom_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.chatroom_button.set_label(_("Chatroom"))
        self.vbox.pack_start(self.chatroom_button, expand=False)

        self.add(self.vbox)
        self.vbox.show_all()

        self.status_changed_cb(CONNECTION_STATUS_DISCONNECTED, "")
        self.load_config()
        self.start_coherence()

    def _row_activated_cb(self, view, path, column):
        device = self.devices_view.get_device_from_path(path)
        device_type = device.get_device_type().split(':')[3].lower()
        if device_type == 'mediaserver':
            print "browse MS"
            window = MediaServerBrowser(device)
            window.show_all()
        elif device_type == 'mediarenderer':
            print "control MR"
        else:
            print "can't inspect device %r" % device.get_friendly_name()

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

            vars = locals()
            vars["MR_UUID"] = MR_UUID
            cfg = DEFAULT_CONFIG % vars
            fd = open(CONFIG_PATH, "w")
            fd.write(cfg)
            fd.close()

        self.config = Config(CONFIG_PATH, root='config', element2attr_mappings={'active':'active'})

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
        def generate_cfg():
            directories = self.platform_media_directories()
            opts = dict(uuid=MS_UUID, name="N900 Media files", content=",".join(directories),
                        backend="FSStore", active="yes")
            return XmlDictObject(initdict=opts)

        plugins = self.config.get("plugin")
        if not plugins:
            self.config.set("plugin", generate_cfg())
        else:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
            already_in_config = False
            for plugin in plugins:
                if plugin.get("uuid") == MS_UUID:
                    plugin.active = "yes"
                    already_in_config = True
                    break
            if not already_in_config:
                plugins.append(generate_cfg())
            self.config.set("plugin", plugins)
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
            self.config.set("plugin", plugins)
            self.reload_config()

    def media_server_enabled(self):
        plugins = self.config.get("plugin")
        if plugins:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
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
            self.coherence_instance = Coherence(self.config.config)

        if restart:
            if self.coherence_instance:
                dfr = self.stop_coherence()
                dfr.addCallback(lambda result: start())
                return dfr
            else:
               start()
        else:
            start()
        if self.coherence_instance:
            coherence = self.coherence_instance
            mirabeau_instance = coherence.mirabeau
            if mirabeau_instance:
                conn_obj = mirabeau_instance.tube_publisher.conn[CONN_INTERFACE]
                handle = conn_obj.connect_to_signal('StatusChanged',
                                                    self.status_changed_cb)
                self.status_update_handle = handle

            coherence.connect(self.devices_view.device_found,
                              'Coherence.UPnP.RootDevice.detection_completed')
            coherence.connect(self.devices_view.device_removed,
                              'Coherence.UPnP.RootDevice.removed')
            self.devices_view.set_devices(coherence.devices)

    def stop_coherence(self):
        def stopped(result):
            if self.coherence_instance:
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

class DevicesView(gtk.TreeView):

    DEVICE_NAME_COLUMN = 0
    DEVICE_OBJECT_COLUMN = 1

    def __init__(self):
        super(DevicesView, self).__init__()
        model = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        device_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Name', device_renderer, text = self.DEVICE_NAME_COLUMN)
        self.set_model(model)
        self.append_column(column)
        self.sort_ascending()

    def set_devices(self, devices):
        model = self.get_model()
        model.clear()
        for device in devices:
            row = {self.DEVICE_NAME_COLUMN: device.get_friendly_name(),
                   self.DEVICE_OBJECT_COLUMN: device
                  }
            model.append(row.values())

    def get_device_from_path(self, path):
        model = self.get_model()
        return model[path][self.DEVICE_OBJECT_COLUMN]

    def device_found(self, device):
        model = self.get_model()
        row = {self.DEVICE_NAME_COLUMN: device.get_friendly_name(),
               self.DEVICE_OBJECT_COLUMN: device}
        model.append(row.values())

    def device_removed(self, usn):
        model = self.get_model()
        if model:
            tree_iter = model.get_iter_first()
            while tree_iter:
                iter_device = model.get(tree_iter, self.DEVICE_OBJECT_COLUMN)[0]
                if iter_device.get_usn() == usn:
                    model.remove(tree_iter)
                    break
                tree_iter = model.iter_next(tree_iter)

    def sort_descending(self):
        self.get_model().set_sort_column_id(self.DEVICE_NAME_COLUMN, gtk.SORT_DESCENDING)

    def sort_ascending(self):
        self.get_model().set_sort_column_id(self.DEVICE_NAME_COLUMN, gtk.SORT_ASCENDING)

class MediaServerBrowser(hildon.StackableWindow):

    def __init__(self, device):
        super(MediaServerBrowser, self).__init__()
        self.device = device
        self.set_title(device.get_friendly_name())

        browse_view = MediaServerBrowseView(self.device)
        browse_view.show()
        area = hildon.PannableArea()
        area.add(browse_view)
        area.show_all()
        self.add(area)

class MediaServerBrowseView(gtk.TreeView):

    MS_NAME_COLUMN = 0
    MS_NODE_ID_COLUMN = 1
    MS_UPNP_CLASS_COLUMN = 2
    MS_CHILD_COUNT_COLUMN = 3
    MS_UDN_COLUMN = 4
    MS_SERVICE_PATH_COLUMN = 5
    MS_ICON_COLUMN = 6
    MS_DIDL_COLUMN = 7
    MS_TOOLTIP_COLUMN = 8

    def __init__(self, device):
        super(MediaServerBrowseView, self).__init__()
        self.device = device
        model = gtk.TreeStore(str, str, str, int, str, str, gtk.gdk.Pixbuf,
                              str, gtk.gdk.Pixbuf)
        self.set_model(model)
        column = gtk.TreeViewColumn('Items')
        icon_cell = gtk.CellRendererPixbuf()
        text_cell = gtk.CellRendererText()

        column.pack_start(icon_cell, False)
        column.pack_start(text_cell, True)

        column.set_attributes(text_cell, text=self.MS_NAME_COLUMN)
        column.add_attribute(icon_cell, "pixbuf", self.MS_ICON_COLUMN)
        self.append_column(column)

        self.connect("row-expanded", self.row_expanded)

        icon = resource_filename(__name__, os.path.join('icons','folder.png'))
        self.folder_icon = gtk.gdk.pixbuf_new_from_file(icon)
        icon = resource_filename(__name__, os.path.join('icons','audio-x-generic.png'))
        self.audio_icon = gtk.gdk.pixbuf_new_from_file(icon)
        icon = resource_filename(__name__, os.path.join('icons','video-x-generic.png'))
        self.video_icon = gtk.gdk.pixbuf_new_from_file(icon)
        icon = resource_filename(__name__, os.path.join('icons','image-x-generic.png'))
        self.image_icon = gtk.gdk.pixbuf_new_from_file(icon)

        self.load()

    def load(self):
        service = self.device.get_service_by_type('ContentDirectory')

        def reply(response):
            model = self.get_model()
            item = model.append(None)
            model.set_value(item, self.MS_NAME_COLUMN, 'root')
            model.set_value(item, self.MS_NODE_ID_COLUMN, '0')
            model.set_value(item, self.MS_UPNP_CLASS_COLUMN, 'root')
            model.set_value(item, self.MS_CHILD_COUNT_COLUMN, -1)
            model.set_value(item, self.MS_UDN_COLUMN, self.device.get_usn())
            model.set_value(item, self.MS_ICON_COLUMN, self.folder_icon)
            model.set_value(item, self.MS_DIDL_COLUMN, response['Result'])
            model.set_value(item, self.MS_SERVICE_PATH_COLUMN, service)
            model.set_value(item, self.MS_TOOLTIP_COLUMN, None)
            model.append(item, ('...loading...','','placeholder',-1,'','',None,'',None))


        action = service.get_action('Browse')
        d = action.call(ObjectID='0',BrowseFlag='BrowseMetadata',
                        StartingIndex=str(0),RequestedCount=str(0),
                        Filter='*',SortCriteria='')
        d.addCallback(reply)
        d.addErrback(self.handle_error)
        service.subscribe_for_variable('ContainerUpdateIDs', callback=self.state_variable_change)
        service.subscribe_for_variable('SystemUpdateID', callback=self.state_variable_change)

    def state_variable_change( self, variable):
        name = variable.name
        value = variable.value
        if name == 'ContainerUpdateIDs':
            changes = value.split(',')
            model = self.get_model()

            while len(changes) > 1:
                container = changes.pop(0).strip()
                update_id = changes.pop(0).strip()

                def match_func(iter, data):
                    column, key = data # data is a tuple containing column number, key
                    value = model.get_value(iter, column)
                    return value == key

                def search(iter, func, data):
                    while iter:
                        if func(iter, data):
                            return iter
                        result = search(model.iter_children(iter), func, data)
                        if result: return result
                        iter = model.iter_next(iter)
                    return None

                row_count = 0
                for row in model:
                    iter = model.get_iter(row_count)
                    match_iter = search(model.iter_children(iter),
                                        match_func, (self.MS_NODE_ID_COLUMN, container))
                    if match_iter:
                        path = model.get_path(match_iter)
                        expanded = self.row_expanded(path)
                        child = model.iter_children(match_iter)
                        while child:
                            model.remove(child)
                            child = model.iter_children(match_iter)
                        self.browse(self.treeview, path, None,
                                    starting_index=0, requested_count=0,
                                    force=True, expand=expanded)

                    break
                    row_count += 1

    def row_expanded(self, view, iter, row_path):
        model = self.get_model()
        child = model.iter_children(iter)
        if child:
            upnp_class = model.get(child, self.MS_UPNP_CLASS_COLUMN)[0]
            if upnp_class == 'placeholder':
                self.browse(view, row_path, None)

    def browse(self, view, row_path, column, starting_index=0, requested_count=0,
               force=False, expand=False):
        model = self.get_model()
        iter = model.get_iter(row_path)
        child = model.iter_children(iter)
        if child:
            upnp_class = model.get(child, self.MS_UPNP_CLASS_COLUMN)[0]
            if upnp_class != 'placeholder':
                if force == False:
                    if view.row_expanded(row_path):
                        view.collapse_row(row_path)
                    else:
                        view.expand_row(row_path, False)
                    return

        title, object_id, upnp_class = model.get(iter, self.MS_NAME_COLUMN,
                                                 self.MS_NODE_ID_COLUMN,
                                                 self.MS_UPNP_CLASS_COLUMN)
        if (not upnp_class.startswith('object.container') and
            not upnp_class == 'root'):
            url = model.get(iter, self.MS_SERVICE_PATH_COLUMN)[0]
            if url == '':
                return
            print "request to play:", title,object_id,url
            # TODO: fire up the predefined MR
            return

        def reply(r):
            child = model.iter_children(iter)
            if child:
                upnp_class = model.get(child, self.MS_UPNP_CLASS_COLUMN)[0]
                if upnp_class == 'placeholder':
                    model.remove(child)

            title = model.get(iter, self.MS_NAME_COLUMN)[0]
            try:
                title = title[:title.rindex('(')]
                model.set_value(iter, self.MS_NAME_COLUMN,
                                "%s(%d)" % (title, int(r['TotalMatches'])))
            except ValueError:
                pass
            elt = parse_xml(r['Result'], 'utf-8')
            elt = elt.getroot()
            for child in elt:
                stored_didl_string = DIDLLite.element_to_didl(ET.tostring(child))
                didl = DIDLLite.DIDLElement.fromString(stored_didl_string)
                item = didl.getItems()[0]
                if item.upnp_class.startswith('object.container'):
                    icon = self.folder_icon
                    service = model.get(iter, self.MS_SERVICE_PATH_COLUMN)[0]
                    child_count = item.childCount
                    try:
                        title = "%s (%d)" % (item.title, item.childCount)
                    except TypeError:
                        title = "%s (n/a)" % item.title
                        child_count = -1
                else:
                    icon = None
                    service = ''

                    child_count = -1
                    title = item.title
                    if item.upnp_class.startswith('object.item.audioItem'):
                        icon = self.audio_icon
                    elif item.upnp_class.startswith('object.item.videoItem'):
                        icon = self.video_icon
                    elif item.upnp_class.startswith('object.item.imageItem'):
                        icon = self.image_icon

                    res = item.res.get_matching(['*:*:*:*'], protocol_type='http-get')
                    if len(res) > 0:
                        res = res[0]
                        service = res.data

                new_iter = model.append(iter, (title, item.id, item.upnp_class, child_count,
                                               '',service,icon,stored_didl_string,None))
                if item.upnp_class.startswith('object.container'):
                    model.append(new_iter, ('...loading...',
                                            '', 'placeholder', -1, '', '',
                                            None, '', None))


            if ((int(r['TotalMatches']) > 0 and force==False) or \
                expand==True):
                view.expand_row(row_path, False)

            if(requested_count != int(r['NumberReturned']) and \
               int(r['NumberReturned']) < (int(r['TotalMatches'])-starting_index)):
                self.browse(view, row_path, column,
                            starting_index=starting_index+int(r['NumberReturned']),
                            force=True)

        service = self.device.get_service_by_type('ContentDirectory')
        action = service.get_action('Browse')
        d = action.call(ObjectID=object_id,BrowseFlag='BrowseDirectChildren',
                        StartingIndex=str(starting_index),RequestedCount=str(requested_count),
                        Filter='*',SortCriteria='')
        d.addCallback(reply)
        d.addErrback(self.handle_error)
        return d

    def handle_error(self,error):
        print error

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
