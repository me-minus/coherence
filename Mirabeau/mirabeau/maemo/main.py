#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2010 - Philippe Normand <phil@base-art.net>


import os

import hildon
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import gettext
import dbus

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

_ = gettext.gettext

gtk.gdk.threads_init()

from twisted.internet import reactor

from coherence.base import Coherence
from coherence.extern.simple_config import Config, XmlDictObject
from coherence.extern.telepathy import connect

from telepathy.interfaces import CONN_INTERFACE
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
     CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING

from mirabeau.maemo.constants import *
from mirabeau.maemo import media_renderer, media_server, dialogs

class MainWindow(hildon.StackableWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.set_title("Mirabeau")
        self.set_app_menu(self._create_menu())
        self.connect('delete-event', self._exit_cb)

        self.devices_view = DevicesView()
        self.devices_view.connect('row-activated', self._row_activated_cb)

        area = hildon.PannableArea()
        area.add(self.devices_view)
        area.show_all()
        self.add(area)

        self.status_changed_cb(CONNECTION_STATUS_DISCONNECTED, "")
        self.load_config()
        self.start_coherence()

    def _row_activated_cb(self, view, path, column):
        if not self.coherence_instance:
            return
        device = self.devices_view.get_device_from_path(path)
        device_type = device.get_device_type().split(':')[3].lower()
        if device_type == 'mediaserver':
            window = media_server.MediaServerBrowser(self.coherence_instance, device)
            window.show_all()
        elif device_type == 'mediarenderer':
            window = media_renderer.MediaRendererWindow(self.coherence_instance, device)
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

        self.chatroom_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.chatroom_button.set_label(_("Chatroom"))
        #menu.append(self.chatroom)

        menu.show_all()
        return menu

    def _exit_cb(self, window, event):
        reactor.stop()

    def load_config(self):
        if not os.path.exists(BASEDIR):
            os.makedirs(BASEDIR)
        if not os.path.exists(CONFIG_PATH):
            # first run, a wizard might fit better here, probably.
            text = _("""\
Welcome to Mirabeau! It is currently bound to your local network,
if you want to browse remote MediaServers please edit the Settings.
A valid GTalk/Jabber account is needed.""")
            note = hildon.hildon_note_new_information(self, text)
            response = note.run()
            note.destroy()

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

    def enable_media_server(self, nickname=None):
        nickname = nickname or "N900"
        name_template = _("%(nickname)s Media Files")

        def generate_cfg(nickname):
            directories = self.platform_media_directories()
            name = name_template % locals()
            opts = dict(uuid=MS_UUID, name=name, content=",".join(directories),
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
                    plugin.name = name_template % locals()
                    already_in_config = True
                    break
            if not already_in_config:
                plugins.append(generate_cfg(nickname))
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

    def set_media_renderer_name(self, nickname=None):
        nickname = nickname or "N900"
        name_template = _("%(nickname)s Media Renderer")
        plugins = self.config.get("plugin")
        if plugins:
            if isinstance(plugins, XmlDictObject):
                plugins = [plugins,]
            for plugin in plugins:
                if plugin.get("uuid") == MR_UUID:
                    plugin.name = name_template % locals()
                    break
            self.config.set("plugin", plugins)
            self.reload_config()

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
        dialog = dialogs.SettingsDialog(self)
        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT:
            mirabeau_section = self.config.get("mirabeau")
            mirabeau_section.set("chatroom", dialog.get_chatroom())
            mirabeau_section.set("conference-server", dialog.get_conf_server())
            mirabeau_section.set("account", dialog.get_account())
            self.config.set("mirabeau", mirabeau_section)
            self.reload_config()

            nickname = dialog.get_account_nickname()
            self.set_media_renderer_name(nickname)
            if dialog.ms_enabled():
                self.enable_media_server(nickname=nickname)
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
