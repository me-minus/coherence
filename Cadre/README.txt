.. -*- mode: rst ; ispell-local-dictionary: "american" -*-

==========================
Cadre
==========================
--------------------------------------------------------------------------
A DLNA/UPnP-PictureFrame application and MediaRenderer based on Coherence
--------------------------------------------------------------------------

:Author:    Frank Scholz
:Copyright: 2009 by Frank Scholz
:Licence:   MIT licence
:Homepage:  http://coherence-project.org/wiki/Cadre

|Cadre| is a PictureFrame application and MediaRenderer based on
`Coherence`__. It grew out the wish to continue the work done on
`Compère`__. It is using the `Clutter toolkit`_ or the `pyglet
toolkit`_ for display.

__ http://coherence-project.org/
__ http://coherence-project.org/wiki/CoherenceMediaRenderer

|Cadre| exposes an UPnP MediaRenderer device which can be controlled
by the `Coherence UPnP Inspector`__.

__ http://coherence-project.org/wiki/UPnP-Inspector

At the moment the only ways to make |Cadre| display an image are using
an UPnP ControlPoint or providing the necessary content information in
a config file.

There are two transition modes supported so far - NONE for just
replacing one image with the other and FADE for cross-fading the new
image other the old one.

The MediaRenderer inside |Cadre| has an interesting feature, it
exposes methods to change display time and transition as UPnP actions.
It is a demonstration and test-bed on how easily vendor-defined
Actions and StateVariables can be implemented by a Coherence backend.


The Configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

|Cadre| can use an XML configuration file to set options, and store
its UPnP device UUID (will be created automatically) over restarts.

The configuration file will be looked for at $HOME/.cadre or its
location can be passed via the ``--config`` commandline parameter. A
sample config (`sample-config.xml`) is included::

  <config>
    <logging level="warning"/>
    <name>Cadre - Coherence Picture-Frame</name>
    <content>/path/to/images/here</content>
    <content>/optional/path/to/more/images/here</content>
    <grafics>clutter</grafics>  <!-- backend to use: clutter or pyglet -->
    <autostart>yes</autostart>
    <shuffle>yes</shuffle>
    <fullscreen>no</fullscreen>
    <display-time>20</display-time>  <!-- the time the image shall be displayed before switching to the next one -->
    <transition>NONE</transition>    <!-- the Clutter backend does support NONE (plain switching) and FADE (cross-fading) so far --> 
    <repeat>yes</repeat>             <!-- not configurable yet -->
  </config>


Requirements and Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

|Cadre| requires

* `Python 2.x`__ or higher (tested with 2.6, but other
  versions should work, too, Python 3.x is *not* supported),
* `setuptools`_ for installation (see below), and
* either `Clutter toolkit`_ or the `pyglet toolkit`_

__ http://www.python.org/download/

:Hints for installing on Windows: Please use the pyglet toolkit.
   Following the links above you will find .msi and .exe-installers.
   Simply install them and continue with `installing Cadre`_.

:Hints for installing on GNU/Linux: Most current GNU/Linux distributions
   provide packages for the requirements. Look for packages names like
   `python-setuptools` and `python-pyglet`. Simply install them and
   continue with `installing Cadre`_.

   NB: Changes are good your distribution provides `pyglet`, but not
   `Clutter`. But don't mind: you only need one of it.

:Hint for installing on other platforms: Many vendors provide Python.
   Please check your vendors software repository. Otherwise please
   download Python 2.6 (or any higer version from the 2.x series) from
   http://www.python.org/download/ and follow the installation
   instructions there.

   After installing Python, install `setuptools`_. You may want to
   read `More Hints on Installing setuptools`_ first.

   Using setuptools, compiling and installing the remaining
   requirements is a piece of cake::

     # if the system has network access
     easy_install pyglet

     # without network access download pyglet
     # from http://www.pyglet.org/download.html and run
     easy_install pyglet-*.zip


Installing Cadre
---------------------------------

When you are reading this you most probably already downloaded and
unpacked |Cadre|. Thus installing is as easy as running::

   python ./setup.py install

Otherwise you may install directly using setuptools/easy_install. If
your system has network access installing |Cadre| is a
breeze::

     easy_install Cadre

Without network access download |Cadre| from
http://pypi.python.org/pypi/Cadre and run::

     easy_install Cadre-*.tar.gz


More Hints on Installing setuptools
------------------------------------

|Cadre| uses setuptools for installation. Thus you need
either

  * network access, so the install script will automatically download
    and install setuptools if they are not already installed

or

  * the correct version of setuptools preinstalled using the
    `EasyInstall installation instructions`__. Those instructions also
    have tips for dealing with firewalls as well as how to manually
    download and install setuptools.

__ http://peak.telecommunity.com/DevCenter/EasyInstall#installation-instructions


Custom Installation Locations
------------------------------

|Cadre| is just a single script (aka Python program). So you can
copy it where ever you want (maybe fixing the first line). But it's
easier to just use::

   # install to /usr/local/bin
   python ./setup.py install --prefix /usr/local

   # install to your Home directory (~/bin)
   python ./setup.py install --home ~


Please mind: This effects also the installation of pyglet (and
setuptools) if they are not already installed.

For more information about Custom Installation Locations please refer
to the `Custom Installation Locations Instructions`__ before
installing |Cadre|.

__ http://peak.telecommunity.com/DevCenter/EasyInstall#custom-installation-locations>


Credits
~~~~~~~~~~~~~

The code is based on great advice from `Zaheer`__, showing how easy
actually the `Twisted`__ integration is, and on the `reflection.py`
example from pyclutter.

__ http://zaheer.merali.org/
__ http://twistedmatrix.com/


.. |Cadre| replace:: `Cadre`

.. _setuptools: http://pypi.python.org/pypi/setuptools
.. _Clutter toolkit: http://www.clutter-project.org/
.. _pyglet toolkit: http://pypi.python.org/pypi/pyglet/
