# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2009 Frank Scholz <coherence@beebits.net>

# Twisted
from twisted.internet import reactor

# Coherence
from coherence.base import Coherence
from coherence.upnp.devices.media_renderer import MediaRenderer

from coherence.upnp.core import DIDLLite

import coherence.extern.louie as louie
from coherence import log

from cadre.scribbling import Canvas
from cadre.renderer import PictureRenderer

class Cadre(log.Loggable):

    logCategory = 'renderer'

    def __init__(self, fullscreen=1):
        self.canvas = Canvas(fullscreen)

        config = {}
        config['logmode'] = 'warning'
        config['controlpoint'] = 'yes'

        louie.connect(self.media_server_found, 'Coherence.UPnP.ControlPoint.MediaServer.detected', louie.Any)
        louie.connect(self.media_server_removed, 'Coherence.UPnP.ControlPoint.MediaServer.removed', louie.Any)
        self.coherence = Coherence(config)

        kwargs = {'version':1,
                'no_thread_needed':True}
        name = 'Cadre - Coherence Picture-Frame'
        if name:
            kwargs['name'] = name

        self.canvas.set_title(name)

        kwargs['controller'] = self

        self.renderer = MediaRenderer(self.coherence,PictureRenderer,**kwargs)

    def quit(self):
        reactor.stop()

    def media_server_found(self, client,udn):
        print "media_server_found", client.device.get_friendly_name()

    def media_server_removed(self, udn):
        print "media_server_removed", udn