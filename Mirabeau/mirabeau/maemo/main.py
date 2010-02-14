#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2010 - Philippe Normand <phil@base-art.net>

import hildon
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import gettext
import dbus

_ = gettext.gettext

gtk.gdk.threads_init()

from twisted.internet import reactor

from telepathy.interfaces import CONN_INTERFACE
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
     CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING

from mirabeau.maemo import media_renderer, media_server, dialogs, \
     roster

class MainWindow(hildon.StackableWindow):

    def __init__(self, controller):
        super(MainWindow, self).__init__()
        self.controller = controller

        # TODO: replace this with a signal
        self.controller.coherence_started_cb = self._coherence_started

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

        self.controller.load_config()
        self.controller.start_coherence()

        if self.controller.first_run:
            # first run, a wizard might fit better here, probably.
            text = _("""\
Welcome to Mirabeau! It is currently bound to your local network,
if you want to browse remote MediaServers please edit the Settings.
A valid GTalk/Jabber account is needed.""")
            note = hildon.hildon_note_new_information(self, text)
            response = note.run()
            note.destroy()

    def _coherence_started(self):
        coherence = self.controller.coherence_instance
        mirabeau_instance = coherence.mirabeau
        if mirabeau_instance:
            def got_connection(connection):
                connection.connect_to_signal('StatusChanged',
                                             self.status_changed_cb)
                self.status_changed_cb(connection.GetStatus(), '')

            def got_error(failure):
                # TODO: display in UI
                print "ERROR, ", failure

            mirabeau_instance.tube_publisher.connection_dfr.addCallbacks(got_connection,
                                                                         got_error)

        coherence.connect(self.devices_view.device_found,
                          'Coherence.UPnP.RootDevice.detection_completed')
        coherence.connect(self.devices_view.device_removed,
                          'Coherence.UPnP.RootDevice.removed')
        self.devices_view.set_devices(coherence.devices)

    def _row_activated_cb(self, view, path, column):
        if not self.controller.coherence_instance:
            return
        device = self.devices_view.get_device_from_path(path)
        device_type = device.get_device_type().split(':')[3].lower()
        coherence_instance = self.controller.coherence_instance
        if device_type == 'mediaserver':
            window = media_server.MediaServerBrowser(coherence_instance, device)
            window.show_all()
        elif device_type == 'mediarenderer':
            window = media_renderer.MediaRendererWindow(coherence_instance, device)
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

        self.spread_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        self.spread_button.set_label(_("Invite friends"))
        self.spread_button.connect('clicked', self.invite_friends)
        menu.append(self.spread_button)

        menu.show_all()
        return menu

    def _exit_cb(self, window, event):
        reactor.stop()

    def status_changed_cb(self, status, reason):
        if status == CONNECTION_STATUS_CONNECTING:
            text = _("Connecting. Please wait")
        elif status == CONNECTION_STATUS_CONNECTED:
            text = _('Connected')
        elif status == CONNECTION_STATUS_DISCONNECTED:
            text = _('Disconnected')
        self.status_button.set_label(text)

    def update_status(self, widget):
        self.controller.toggle_coherence()

    def open_settings(self, widget):
        mirabeau_section = self.controller.config.get("mirabeau")
        media_server_enabled = self.controller.media_server_enabled()
        dialog = dialogs.SettingsDialog(self, mirabeau_section,
                                        media_server_enabled)
        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT:
            self.controller.update_settings(dialog.get_chatroom(),
                                            dialog.get_conf_server(),
                                            dialog.get_account(),
                                            dialog.get_account_nickname(),
                                            dialog.ms_enabled())

        dialog.destroy()

    def invite_friends(self, widget):
        coherence = self.controller.coherence_instance
        if not coherence or not coherence.mirabeau:
            return
        mirabeau_section = self.controller.config.get("mirabeau")
        window = roster.InviteFriendsWindow(coherence,
                                            mirabeau_section["chatroom"],
                                            mirabeau_section["conference-server"])
        window.show_all()

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
