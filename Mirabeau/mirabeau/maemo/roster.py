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

from telepathy.interfaces import CONN_INTERFACE
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
     CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING

from mirabeau.maemo import dialogs

class InviteFriendsWindow(hildon.StackableWindow):

    def __init__(self, coherence, room_name, conf_server):
        super(InviteFriendsWindow, self).__init__()
        self.coherence = coherence
        self.set_title(_("Spread the word!"))
        self.contact_handles = []
        vbox = gtk.VBox()

        # To
        to_box = gtk.HBox()
        to_button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH |gtk.HILDON_SIZE_FINGER_HEIGHT)
        to_button.set_label(_("To:"))
        to_button.connect("clicked", self._select_contacts)
        to_box.pack_start(to_button, expand=False)
        self.to_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        to_box.pack_start(self.to_entry)
        vbox.pack_start(to_box, expand=False)

        # Message
        template = _("""\
Hi! Join me in the tubes of the interwebs! It is all explained there:
%(howto_url)s. I am in the %(room_name)s of the server %(conf_server)s.
        """)
        howto_url = "http://coherence.beebits.net/wiki/MirabeauHowTo"
        self.text_view = hildon.TextView()
        buf = gtk.TextBuffer()
        buf.set_text(template % locals())
        self.text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.text_view.set_buffer(buf)
        vbox.pack_start(self.text_view)

        # Send
        send_button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        send_button.set_label(_("Send"))
        send_button.connect("clicked", self._send_message)
        vbox.pack_start(send_button, expand=False)

        self.add(vbox)
        vbox.show_all()

    def _select_contacts(self, widget):
        dialog = dialogs.ContactsDialog(self, self.coherence)
        response = dialog.run()
        contacts = dialog.get_contacts()
        text = ", ".join([c[1] for c in contacts])
        self.to_entry.set_text(text)
        self.contact_handles = [c[0] for c in contacts]
        dialog.destroy()

    def _send_message(self, widget):
        buf = self.text_view.get_buffer()
        text = buf.get_text(buf.get_iter_at_offset(0), buf.get_iter_at_offset(-1))
        client = self.coherence.mirabeau.tube_publisher
        for handle_id in self.contact_handles:
            client.send_message(handle_id, text)
        # TODO: display delivery notification
        self.destroy()
