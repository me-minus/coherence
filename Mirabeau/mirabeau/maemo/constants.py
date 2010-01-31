# -*- coding: utf-8 -*-
#
# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2010 - Philippe Normand <phil@base-art.net>

import uuid, os, platform

BASEDIR = os.path.expanduser("~/.config")
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

hostname = platform.uname()[1]
MS_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, '%s.coherence.org' % hostname))
MR_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, '%s.gstreamer.org' % hostname))
