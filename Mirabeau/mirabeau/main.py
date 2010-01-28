#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the MIT license
# http://opensource.org/licenses/mit-license.php

# Copyright 2010 - Philippe Normand <phil@base-art.net>

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor

from mirabeau import controller

def run(*args):
    ctrl = controller.MirabeauController()
    ctrl.start()
    reactor.run()
