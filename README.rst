.. -*- mode: rst ; ispell-local-dictionary: "american" -*-

===========================================================================
Coherence - a DLNA/UPnP Media Server and  Framework for the Digital Living
===========================================================================

Coherence for Users
=========================

The Coherence toolkit offers the following multi-media related components:

* DLNA/UPnP Media Server (Coherence), which exports local files or
  online media to UPnP clients. There are many backends to fetch media
  from

  - local applications media collections, like those from Rythmbox or
    Banschee,

  - Audio-CD or DVB,

  - online services like Flickr, last.fm, YouTube, Picasa Web Albums
    and other.

  Due to the comprehensive plug-in architecture, these can easily be
  expanded.

  Coherence also contains an audio/video DLNA/UPnP MediaRenderer
  application, based on the GStreamer framework. It includes the
  source-code framework used by the other components. The media server
  supports Transcoding (experimental).

* Coherence-Config is a cross-platform GUI frontend for 'Coherence'.

* An image DLNA/UPnP MediaRenderer (Cadre), which can display
  pictures from the local filesystem or from a MediaServer.

* An application level proxy for UPnP devices (Mirabeau) which allows
  to share your UPnP content between two or more local networks over
  the Internet. It uses XMPP as a transport (work in progress).

* The UPnP-Inspector is a graphical UPnP Device and Service analyzer,
  and a debugging tool. Detected devices are displayed in a tree-view,
  where - amongst other things - actions can be called and
  state-variables be queried. It can also be used as a UPnP
  ControlPoint.

* Plugins or extensions for other applications to open them to the
  UPnP world, thanks to the framework (either as MediaServers,
  ControlPoints or MediaRenderers). This includes Totem, Nautilus, Eye
  Of Gnome, Rythmbox, Banshee, Elisa, amarok...

Additionally there is a command-line tool to work with UPnP Internet
Gateway Devices (Puncher). Many routers offer an UPnP
InternetGatewayDevice to query informations about the WAN connection,
the link status, external IP address and to enable port-mappings that
allow inbound connections to the local LAN. Puncher allows you
interacting with these devices.

Coherence for Application Developers
========================================

Developers get a framework written in Python with an emerging DBus
API. This framework is designed to automate all UPnP-related tasks as
much as possible and enable applications to participate in digital
living networks, primarily the UPnP universe.

The core framework of Coherence provides:

    * an SSDP server
    * an MSEARCH client
    * server and client for HTTP/SOAP requests
    * server and client for Event Subscription and Notification (GENA)
    * A device implementation dock 

UPnP device implementations are pluggable. For instance, we can pick
the MediaServer device and plug it into the core. Or attach the
MediaRenderer device. Or attach both, or two MediaServers and a
ControlPoint - this is the point where one of Coherence's particular
features kicks in.

This probably makes more sense if we look at how UPnP devices are
implemented within Coherence. On one side of the device we have the
connectors to the core, but on the other side there is a dock for a
backend to be plugged in. So a device implementation is generally a
simple translation map between the the core and its backend.

As an example, a MediaServer connects to the core via the
ContentDirectory and ConnectionManager services and bridges them to a
filesystem backend. Or bridges them - let's say - to a less skimpy
one, the MediaStore of a MediaCenter exposing its content in a way
already presorted by album, artist, genre, etc.
