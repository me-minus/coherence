
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
from twisted.internet import task

from coherence.base import Coherence
from coherence.upnp.core import DIDLLite
from coherence.upnp.core.utils import parse_xml, getPage, means_true
from coherence.extern.simple_config import Config, XmlDictObject
from coherence.extern.telepathy import connect
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
        if not self.coherence_instance:
            return
        device = self.devices_view.get_device_from_path(path)
        device_type = device.get_device_type().split(':')[3].lower()
        if device_type == 'mediaserver':
            print "browse MS"
            window = MediaServerBrowser(self.coherence_instance, device)
            window.show_all()
        elif device_type == 'mediarenderer':
            print "control MR"
            window = MediaRendererWindow(self.coherence_instance, device)
            window.show_all()
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

    def __init__(self, coherence, device):
        super(MediaServerBrowser, self).__init__()
        self.set_title(device.get_friendly_name())

        browse_view = MediaServerBrowseView(coherence, device)
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

    def __init__(self, coherence, device):
        super(MediaServerBrowseView, self).__init__()
        self._coherence = coherence
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
        self.connect("row-activated", self.row_activated)

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
        service.subscribe_for_variable('ContainerUpdateIDs', callback=self.state_variable_change)
        service.subscribe_for_variable('SystemUpdateID', callback=self.state_variable_change)

        model = self.get_model()
        item = model.append(None)
        model.set_value(item, self.MS_ICON_COLUMN, self.folder_icon)
        model.set_value(item, self.MS_NAME_COLUMN, 'root')
        model.set_value(item, self.MS_NODE_ID_COLUMN, '0')
        return self.browse_object('0', iter=item)

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

    def row_activated(self, view, row_path, column):
        model = self.get_model()
        iter = model.get_iter(row_path)
        child = model.iter_children(iter)
        if not child:
            # this is a leaf, let's play it
            didl_fragment = model.get(iter, self.MS_DIDL_COLUMN)[0]
            url = model.get(iter, self.MS_SERVICE_PATH_COLUMN)[0]
            if url == '':
                return
            window = SelectMRWindow(self._coherence, didl_fragment, url)
            window.show_all()

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

        object_id = model.get(iter, self.MS_NODE_ID_COLUMN)[0]
        return self.browse_object(object_id, iter=iter, view=view, row_path=row_path,
                                  starting_index=starting_index,
                                  requested_count=requested_count,
                                  force=force, expand=expand)

    def browse_object(self, object_id, iter=None, view=None, row_path=None,
                      starting_index=0, requested_count=0,
                      force=False, expand=False):
        model = self.get_model()
        if not iter:
            iter = model.append(None)

        def reply(r):
            child = model.iter_children(iter)
            if child:
                upnp_class = model.get(child, self.MS_UPNP_CLASS_COLUMN)[0]
                if upnp_class == 'placeholder':
                    model.remove(child)

            title = model.get(iter, self.MS_NAME_COLUMN)[0]
            if title:
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
                if view:
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

class SelectMRWindow(hildon.StackableWindow):

    def __init__(self, coherence, didl_fragment, url):
        super(SelectMRWindow, self).__init__()
        self.set_title(_("Select a MediaRenderer"))
        self._coherence = coherence
        self._didl_fragment = didl_fragment
        self._url = url

        self.mr_list = DevicesView()
        self.mr_list.connect('row-activated', self._row_activated_cb)
        area = hildon.PannableArea()
        area.add(self.mr_list)
        area.show_all()
        self.add(area)

        mrs = []
        for device in self._coherence.devices:
            device_type = device.get_device_type().split(':')[3].lower()
            if device_type == "mediarenderer":
                mrs.append(device)
        self.mr_list.set_devices(mrs)

    def _row_activated_cb(self, view, path, column):
        device = self.mr_list.get_device_from_path(path)
        window = MediaRendererWindow(self._coherence, device)
        window.load_media(self._didl_fragment, self._url)
        window.show_all()

class MediaRendererWindow(hildon.StackableWindow):

    def __init__(self, coherence, device):
        super(MediaRendererWindow, self).__init__()
        self.coherence = coherence
        self.device = device
        self.set_title(device.get_friendly_name())

        vbox = gtk.VBox(homogeneous=False, spacing=10)

        hbox = gtk.HBox(homogeneous=False, spacing=10)
        hbox.set_border_width(2)
        self.album_art_image = gtk.Image()
        icon = resource_filename(__name__, os.path.join('icons','blankalbum.png'))
        self.blank_icon = gtk.gdk.pixbuf_new_from_file(icon)
        self.album_art_image.set_from_pixbuf(self.blank_icon)
        hbox.pack_start(self.album_art_image,False,False,2)

        #icon_loader = gtk.gdk.PixbufLoader()
        #icon_loader.write(urllib.urlopen(str(res.data)).read())
        #icon_loader.close()

        vbox.pack_start(hbox,False,False,2)
        textbox = gtk.VBox(homogeneous=False, spacing=10)
        self.title_text = gtk.Label("<b>title</b>")
        self.title_text.set_use_markup(True)
        textbox.pack_start(self.title_text,False,False,2)
        self.album_text = gtk.Label("album")
        self.album_text.set_use_markup(True)
        textbox.pack_start(self.album_text,False,False,2)
        self.artist_text = gtk.Label("artist")
        self.artist_text.set_use_markup(True)
        textbox.pack_start(self.artist_text,False,False,2)
        hbox.pack_start(textbox,False,False,2)

        seekbox = gtk.HBox(homogeneous=False, spacing=10)
        self.position_min_text = gtk.Label("0:00")
        self.position_min_text.set_use_markup(True)
        seekbox.pack_start(self.position_min_text,False,False,2)
        adjustment=gtk.Adjustment(value=0, lower=0, upper=240, step_incr=1,page_incr=20)#, page_size=20)
        self.position_scale = gtk.HScale(adjustment=adjustment)
        self.position_scale.set_draw_value(True)
        self.position_scale.set_value_pos(gtk.POS_BOTTOM)
        self.position_scale.set_sensitive(False)
        self.position_scale.connect("format-value", self.format_position)
        self.position_scale.connect('change-value',self.position_changed)
        seekbox.pack_start(self.position_scale,True,True,2)
        self.position_max_text = gtk.Label("0:00")
        self.position_max_text.set_use_markup(True)
        seekbox.pack_end(self.position_max_text,False,False,2)
        vbox.pack_start(seekbox,False,False,2)

        buttonbox = gtk.HBox(homogeneous=False, spacing=10)
        self.prev_button = self.make_button('media-skip-backward.png',self.skip_backward,sensitive=False)
        buttonbox.pack_start(self.prev_button,False,False,2)
        self.seek_backward_button = self.make_button('media-seek-backward.png',callback=self.seek_backward,sensitive=False)
        buttonbox.pack_start(self.seek_backward_button,False,False,2)
        self.stop_button = self.make_button('media-playback-stop.png',callback=self.stop,sensitive=False)
        buttonbox.pack_start(self.stop_button,False,False,2)
        self.start_button = self.make_button('media-playback-start.png',callback=self.play_or_pause,sensitive=False)
        buttonbox.pack_start(self.start_button,False,False,2)
        self.seek_forward_button = self.make_button('media-seek-forward.png',callback=self.seek_forward,sensitive=False)
        buttonbox.pack_start(self.seek_forward_button,False,False,2)
        self.next_button = self.make_button('media-skip-forward.png',self.skip_forward,sensitive=False)
        buttonbox.pack_start(self.next_button,False,False,2)

        hbox = gtk.HBox(homogeneous=False, spacing=10)
        #hbox.set_size_request(240,-1)
        adjustment=gtk.Adjustment(value=0, lower=0, upper=100, step_incr=1,page_incr=20)#, page_size=20)
        self.volume_scale = gtk.HScale(adjustment=adjustment)
        self.volume_scale.set_size_request(140,-1)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.connect('change-value',self.volume_changed)
        hbox.pack_start(self.volume_scale,False,False,2)
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.volume_image = gtk.Image()
        icon = resource_filename(__name__, os.path.join('icons','audio-volume-low.png'))
        self.volume_low_icon = gtk.gdk.pixbuf_new_from_file(icon)
        self.volume_image.set_from_pixbuf(self.volume_low_icon)
        button.set_image(self.volume_image)
        button.connect("clicked", self.mute)

        icon = resource_filename(__name__, os.path.join('icons','audio-volume-medium.png'))
        self.volume_medium_icon = gtk.gdk.pixbuf_new_from_file(icon)
        icon = resource_filename(__name__, os.path.join('icons','audio-volume-high.png'))
        self.volume_high_icon = gtk.gdk.pixbuf_new_from_file(icon)
        icon = resource_filename(__name__, os.path.join('icons','audio-volume-muted.png'))
        self.volume_muted_icon = gtk.gdk.pixbuf_new_from_file(icon)
        hbox.pack_end(button,False,False,2)

        buttonbox.pack_end(hbox,False,False,2)
        vbox.pack_start(buttonbox,False,False,2)

        self.pause_button_image = gtk.Image()
        icon = resource_filename(__name__, os.path.join('icons','media-playback-pause.png'))
        icon = gtk.gdk.pixbuf_new_from_file(icon)
        self.pause_button_image.set_from_pixbuf(icon)
        self.start_button_image = self.start_button.get_image()

        self.status_bar = gtk.Statusbar()
        context_id = self.status_bar.get_context_id("Statusbar")
        vbox.pack_end(self.status_bar,False,False,2)

        self.add(vbox)

        self.seeking = False

        self.position_loop = task.LoopingCall(self.get_position)

        service = self.device.get_service_by_type('RenderingControl')
        service.subscribe_for_variable('Volume', callback=self.state_variable_change)
        service.subscribe_for_variable('Mute', callback=self.state_variable_change)

        service = self.device.get_service_by_type('AVTransport')
        if service != None:
            service.subscribe_for_variable('AVTransportURI', callback=self.state_variable_change)
            service.subscribe_for_variable('CurrentTrackMetaData', callback=self.state_variable_change)
            service.subscribe_for_variable('TransportState', callback=self.state_variable_change)
            service.subscribe_for_variable('CurrentTransportActions', callback=self.state_variable_change)

            service.subscribe_for_variable('AbsTime', callback=self.state_variable_change)
            service.subscribe_for_variable('TrackDuration', callback=self.state_variable_change)

        self.get_position()

    def make_button(self,icon,callback=None,sensitive=True):
        icon = resource_filename(__name__, os.path.join('icons',icon))
        icon = gtk.gdk.pixbuf_new_from_file(icon)
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        image = gtk.Image()
        image.set_from_pixbuf(icon)
        button.set_image(image)
        button.connect("clicked", lambda x: callback())
        button.set_sensitive(sensitive)
        return button

    def load_media(self, metadata, url):
        elt = DIDLLite.DIDLElement.fromString(metadata)
        if elt.numItems() == 1:
            service = self.device.get_service_by_type('ConnectionManager')
            if service != None:
                local_protocol_infos=service.get_state_variable('SinkProtocolInfo').value.split(',')
                item = elt.getItems()[0]
                try:
                    res = item.res.get_matching(local_protocol_infos, protocol_type='internal')
                    if len(res) == 0:
                        res = item.res.get_matching(local_protocol_infos)
                    if len(res) > 0:
                        res = res[0]
                        remote_protocol,remote_network,remote_content_format,_ = res.protocolInfo.split(':')
                        d = self.stop()
                        d.addCallback(lambda x: self.set_uri(res.data,metadata))
                        d.addCallback(lambda x: self.play_or_pause(force_play=True))
                        d.addErrback(self.handle_error)
                        d.addErrback(self.handle_error)
                except AttributeError:
                    print "Sorry, we currently support only single items!"
            else:
                print "can't check for the best resource!"

    def state_variable_change(self,variable):
        if variable.name == 'CurrentTrackMetaData':
            if variable.value != None and len(variable.value)>0:
                try:
                    from coherence.upnp.core import DIDLLite
                    elt = DIDLLite.DIDLElement.fromString(variable.value)
                    for item in elt.getItems():
                        self.title_text.set_markup("<b>%s</b>" % item.title)
                        if item.album != None:
                            self.album_text.set_markup(item.album)
                        else:
                            self.album_text.set_markup('')
                        if item.artist != None:
                            self.artist_text.set_markup("<i>%s</i>" % item.artist)
                        else:
                            self.artist_text.set_markup("")

                        def got_icon(icon):
                            icon = icon[0]
                            icon_loader = gtk.gdk.PixbufLoader()
                            icon_loader.write(icon)
                            icon_loader.close()
                            icon = icon_loader.get_pixbuf()
                            icon = icon.scale_simple(128,128,gtk.gdk.INTERP_BILINEAR)
                            self.album_art_image.set_from_pixbuf(icon)

                        if item.upnp_class.startswith('object.item.audioItem') and item.albumArtURI != None:
                            d = getPage(item.albumArtURI)
                            d.addCallback(got_icon)
                        elif item.upnp_class.startswith('object.item.imageItem'):
                            res = item.res.get_matching('http-get:*:image/:*')
                            if len(res) > 0:
                                res = res[0]
                                d = getPage(res.data)
                                d.addCallback(got_icon)
                            else:
                                self.album_art_image.set_from_pixbuf(self.blank_icon)
                        else:
                            self.album_art_image.set_from_pixbuf(self.blank_icon)


                except SyntaxError:
                    #print "seems we haven't got an XML string"
                    return
            else:
                self.title_text.set_markup('')
                self.album_text.set_markup('')
                self.artist_text.set_markup('')
                self.album_art_image.set_from_pixbuf(self.blank_icon)

        elif variable.name == 'TransportState':
            if variable.value == 'PLAYING':
                service = self.device.get_service_by_type('AVTransport')
                if 'Pause' in service.get_actions():
                    self.start_button.set_image(self.pause_button_image)
                try:
                    self.position_loop.start(1.0, now=True)
                except:
                    pass
            elif variable.value != 'TRANSITIONING':
                self.start_button.set_image(self.start_button_image)
                try:
                    self.position_loop.stop()
                except:
                    pass
            if variable.value == 'STOPPED':
                self.get_position()


            context_id = self.status_bar.get_context_id("Statusbar")
            self.status_bar.pop(context_id)
            self.status_bar.push(context_id,"%s" % variable.value)

        elif variable.name == 'CurrentTransportActions':
            try:
                actions = map(lambda x: x.upper(),variable.value.split(','))
                if 'SEEK' in actions:
                    self.position_scale.set_sensitive(True)
                    self.seek_forward_button.set_sensitive(True)
                    self.seek_backward_button.set_sensitive(True)
                else:
                    self.position_scale.set_sensitive(False)
                    self.seek_forward_button.set_sensitive(False)
                    self.seek_backward_button.set_sensitive(False)
                self.start_button.set_sensitive('PLAY' in actions)
                self.stop_button.set_sensitive('STOP' in actions)
                self.prev_button.set_sensitive('PREVIOUS' in actions)
                self.next_button.set_sensitive('NEXT' in actions)
            except:
                #very unlikely to happen
                import traceback
                print traceback.format_exc()

        elif variable.name == 'AVTransportURI':
            if variable.value != '':
                pass
                #self.seek_backward_button.set_sensitive(True)
                #self.stop_button.set_sensitive(True)
                #self.start_button.set_sensitive(True)
                #self.seek_forward_button.set_sensitive(True)
            else:
                #self.seek_backward_button.set_sensitive(False)
                #self.stop_button.set_sensitive(False)
                #self.start_button.set_sensitive(False)
                #self.seek_forward_button.set_sensitive(False)
                self.album_art_image.set_from_pixbuf(self.blank_icon)
                self.title_text.set_markup('')
                self.album_text.set_markup('')
                self.artist_text.set_markup('')

        elif variable.name == 'Volume':
            try:
                volume = int(variable.value)
                if int(self.volume_scale.get_value()) != volume:
                    self.volume_scale.set_value(volume)
                service = self.device.get_service_by_type('RenderingControl')
                mute_variable = service.get_state_variable('Mute')
                if means_true(mute_variable.value) == True:
                    self.volume_image.set_from_pixbuf(self.volume_muted_icon)
                elif volume < 34:
                    self.volume_image.set_from_pixbuf(self.volume_low_icon)
                elif volume < 67:
                    self.volume_image.set_from_pixbuf(self.volume_medium_icon)
                else:
                    self.volume_image.set_from_pixbuf(self.volume_high_icon)

            except:
                import traceback
                print traceback.format_exc()

        elif variable.name == 'Mute':
            service = self.device.get_service_by_type('RenderingControl')
            volume_variable = service.get_state_variable('Volume')
            volume = volume_variable.value
            if means_true(variable.value) == True:
                self.volume_image.set_from_pixbuf(self.volume_muted_icon)
            elif volume < 34:
                self.volume_image.set_from_pixbuf(self.volume_low_icon)
            elif volume < 67:
                self.volume_image.set_from_pixbuf(self.volume_medium_icon)
            else:
                self.volume_image.set_from_pixbuf(self.volume_high_icon)

    def seek_backward(self):
        self.seeking = True
        value = self.position_scale.get_value()
        value = int(value)
        seconds = max(0,value-20)

        hours = seconds / 3600
        seconds = seconds - hours * 3600
        minutes = seconds / 60
        seconds = seconds - minutes * 60
        target = "%d:%02d:%02d" % (hours,minutes,seconds)

        def handle_result(r):
            self.seeking = False
            #self.get_position()

        service = self.device.get_service_by_type('AVTransport')
        seek_modes = service.get_state_variable('A_ARG_TYPE_SeekMode').allowed_values
        unit = 'ABS_TIME'
        if 'ABS_TIME' not in seek_modes:
            if 'REL_TIME' in seek_modes:
                unit = 'REL_TIME'
                target = "-%d:%02d:%02d" % (0,0,20)

        action = service.get_action('Seek')
        d = action.call(InstanceID=0,Unit=unit,Target=target)
        d.addCallback(handle_result)
        d.addErrback(self.handle_error)
        return d

    def seek_forward(self):
        self.seeking = True
        value = self.position_scale.get_value()
        value = int(value)
        max = int(self.position_scale.get_adjustment().upper)
        seconds = min(max,value+20)

        hours = seconds / 3600
        seconds = seconds - hours * 3600
        minutes = seconds / 60
        seconds = seconds - minutes * 60
        target = "%d:%02d:%02d" % (hours,minutes,seconds)

        def handle_result(r):
            self.seeking = False
            #self.get_position()

        service = self.device.get_service_by_type('AVTransport')
        seek_modes = service.get_state_variable('A_ARG_TYPE_SeekMode').allowed_values
        unit = 'ABS_TIME'
        if 'ABS_TIME' not in seek_modes:
            if 'REL_TIME' in seek_modes:
                unit = 'REL_TIME'
                target = "+%d:%02d:%02d" % (0,0,20)

        action = service.get_action('Seek')
        d = action.call(InstanceID=0,Unit=unit,Target=target)
        d.addCallback(handle_result)
        d.addErrback(self.handle_error)
        return d

    def play_or_pause(self,force_play=False):
        service = self.device.get_service_by_type('AVTransport')
        variable = service.get_state_variable('TransportState', instance=0)
        if force_play == True or variable.value != 'PLAYING':
            action = service.get_action('Play')
            d = action.call(InstanceID=0,Speed=1)
        else:
            action = service.get_action('Pause')
            d = action.call(InstanceID=0)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def stop(self):
        service = self.device.get_service_by_type('AVTransport')
        action = service.get_action('Stop')
        d = action.call(InstanceID=0)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def skip_backward(self):
        service = self.device.get_service_by_type('AVTransport')
        action = service.get_action('Previous')
        d = action.call(InstanceID=0)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def skip_forward(self):
        service = self.device.get_service_by_type('AVTransport')
        action = service.get_action('Next')
        d = action.call(InstanceID=0)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def set_uri(self,url,didl):
        service = self.device.get_service_by_type('AVTransport')
        action = service.get_action('SetAVTransportURI')
        d = action.call(InstanceID=0,CurrentURI=url,
                                     CurrentURIMetaData=didl)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d


    def position_changed(self,range,scroll,value):

        old_value = self.position_scale.get_value()
        new_value = value - old_value
        if new_value < 0 and new_value > -1.0:
            return
        if new_value >= 0 and new_value < 1.0:
            return

        self.seeking = True
        adjustment = range.get_adjustment()
        value = int(value)
        max = int(adjustment.upper)
        seconds = target_seconds = min(max,value)

        hours = seconds / 3600
        seconds = seconds - hours * 3600
        minutes = seconds / 60
        seconds = seconds - minutes * 60
        target = "%d:%02d:%02d" % (hours,minutes,seconds)

        service = self.device.get_service_by_type('AVTransport')

        seek_modes = service.get_state_variable('A_ARG_TYPE_SeekMode').allowed_values
        unit = 'ABS_TIME'
        if 'ABS_TIME' not in seek_modes:
            if 'REL_TIME' in seek_modes:
                unit = 'REL_TIME'
                seconds = int(new_value)

                sign = '+'
                if seconds < 0:
                    sign = '-'
                    seconds = seconds * -1

                hours = seconds / 3600
                seconds = seconds - hours * 3600
                minutes = seconds / 60
                seconds = seconds - minutes * 60
                target = "%s%d:%02d:%02d" % (sign,hours,minutes,seconds)

        def handle_result(r):
            self.seeking = False
            #self.get_position()

        action = service.get_action('Seek')
        d = action.call(InstanceID=0,Unit=unit,Target=target)
        d.addCallback(handle_result)
        d.addErrback(self.handle_error)

    def format_position(self,scale,value):
        seconds = int(value)
        hours = seconds / 3600
        seconds = seconds - hours * 3600
        minutes = seconds / 60
        seconds = seconds - minutes * 60
        if hours > 0:
            return "%d:%02d:%02d" % (hours,minutes,seconds)
        else:
            return "%d:%02d" % (minutes,seconds)

    def get_position(self):

        if self.seeking == True:
            return

        def handle_result(r,service):
            try:
                duration = r['TrackDuration']
                h,m,s = duration.split(':')
                if int(h) > 0:
                    duration = '%d:%02d:%02d' % (int(h),int(m),int(s))
                else:
                    duration = '%d:%02d' % (int(m),int(s))
                max = (int(h) * 3600) + (int(m)*60) + int(s)
                self.position_scale.set_range(0,max)
                self.position_max_text.set_markup(duration)
                actions = service.get_state_variable('CurrentTransportActions')
                try:
                    actions = actions.value.split(',')
                    if 'SEEK' in actions:
                        self.position_scale.set_sensitive(True)
                except AttributeError:
                    pass
            except:
                #import traceback
                try:
                    self.position_scale.set_range(0,0)
                except:
                    pass
                self.position_max_text.set_markup('0:00')
                self.position_scale.set_sensitive(False)

            try:
                if self.seeking == False:
                    position = r['AbsTime']
                    h,m,s = position.split(':')
                    position = (int(h) * 3600) + (int(m)*60) + int(s)
                    self.position_scale.set_value(position)
            except:
                #import traceback
                #print traceback.format_exc()
                pass

        service = self.device.get_service_by_type('AVTransport')
        try:
            action = service.get_action('GetPositionInfo')
            d = action.call(InstanceID=0)
            d.addCallback(handle_result,service)
            d.addErrback(self.handle_error)
            return d
        except AttributeError:
            # the device and its services are gone
            pass

    def volume_changed(self,range,scroll,value):
        value = int(value)
        if value > 100:
            value = 100
        service = self.device.get_service_by_type('RenderingControl')
        action = service.get_action('SetVolume')
        d = action.call(InstanceID=0,
                    Channel='Master',
                    DesiredVolume=value)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def mute(self,w):
        service = self.device.get_service_by_type('RenderingControl')
        action = service.get_action('SetMute')
        mute_variable = service.get_state_variable('Mute')
        if means_true(mute_variable.value) == False:
            new_mute = '1'
        else:
            new_mute = '0'
        d = action.call(InstanceID=0,
                        Channel='Master',
                        DesiredMute=new_mute)
        d.addCallback(self.handle_result)
        d.addErrback(self.handle_error)
        return d

    def handle_error(self,e):
        print 'we have an error', e
        return e

    def handle_result(self,r):
        return r


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
