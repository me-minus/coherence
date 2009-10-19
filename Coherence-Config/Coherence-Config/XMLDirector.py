from xml.etree import ElementTree as ET
import sys, os
from PyQt4 import QtGui, QtCore
from xml.parsers.expat import ExpatError



class XMLDirector:
    def __init__(self):
        
        if sys.platform == "win32":
            self.configFileLocation = os.getenv("USERPROFILE")+"\.coherence"
        else:
            self.configFileLocation = os.getenv("HOME")+"/.coherence"
        return None
    
            
    def loadXMLConfiguration(self):
        if not os.path.exists(self.configFileLocation):
            self.generateXMLConfiguration()
            
        try:
            self.tree = ET.parse(self.configFileLocation)
        except ExpatError:
            message = "The Coherence configuration file located in your home folder is not valid.\
            Would you like to replace it with a valid configuration?"
            action = QtGui.QMessageBox.critical(None, "Invalid XML Configuration", message, QtGui.QMessageBox.Yes, 
                                                QtGui.QMessageBox.No)
            
            if action == QtGui.QMessageBox.Yes:
                self.generateXMLConfiguration()
                self.tree = ET.parse(self.configFileLocation)
            else:
                QtGui.QMessageBox.critical(None, "Unable to proceed", "Coherence-Config will now close")
                sys.exit(1)
        except Exception:
            print "Finish catching errors... Bad Alex!"
                
        
    #Return a specific backend's element
    def getBackendElement(self, backend):
        plugins = self.tree.findall("plugin")
        for plugin in plugins:
            possibleBackend = plugin.find(".//backend")
            if possibleBackend.text == backend:
                return plugin
            
    def getLocalContentlist(self):
        folders = []
        contents = self.getBackendElement("FSStore")
        
        if contents.get("active") == "yes":
            isActive = True
        else:
            isActive = False
        
        for i in contents:
            if i.tag == "content":
                folders.append(i.text)
                
        return folders, isActive
    
    def writeLocalContentList(self, contentList, isActive):
        #find the FSStore content -- Store in external list to prevent looping quirks, re
        contents = self.getBackendElement("FSStore")
        ContentToRemove = []
        
        contents.set("active", isActive)
    
        #Queue the <content> to remove
        for i in contents:
            if i.tag == "content":
                ContentToRemove.append(i)
                
        #clear the <content>
        for i in ContentToRemove:
            contents.remove(i)
            
        #Add the new content list to the XML
        for i in contentList:
            tempE = ET.fromstring("<content>"+str(i)+"</content>")
            contents.insert(0,tempE)

        #finally, write it out
        self.tree.write(self.configFileLocation)
        
    #Write the settings from settingsconfigpanel
    def writeSettingConfig(self, settings):
        dBusElement = self.tree.find(".//use_dbus")
        webUIElement = self.tree.find(".//web-ui")
        controlElement = self.tree.find(".//controlpoint")

        dBusElement.text="yes" if settings['dbus'] else "no"
        webUIElement.text="yes" if settings['webui'] else "no"
        controlElement.text="yes" if settings['control'] else "no"
        
        self.tree.write(self.configFileLocation)
    
    def getSettingsConfig(self):
        dBusElement = self.tree.find(".//use_dbus")
        webUIElement = self.tree.find(".//web-ui")
        controlElement = self.tree.find(".//controlpoint")
        
        dbus = True if dBusElement.text=="yes" else False
        webui = True if webUIElement.text=="yes" else False
        control = True if controlElement.text=="yes" else False
        
        settings = {'dbus':dbus, 'webui':webui, 'control':control}
        return settings
        
    def generateXMLConfiguration(self):
        configFile = """
<config>
  <logging level="warning">
    <subsystem active="no" level="info" name="coherence" />
  <subsystem active="no" level="info" name="webserver" />
  <subsystem active="no" level="info" name="dbus" />
  <subsystem active="no" level="info" name="webui" />
  <subsystem active="no" level="info" name="webui_menu_fragment" />
  <subsystem active="no" level="info" name="webui_device_fragment" />
  <subsystem active="no" level="info" name="webui_logging_fragment" />
  <subsystem active="no" level="info" name="ssdp" />
  <subsystem active="no" level="info" name="msearch" />
  <subsystem active="no" level="info" name="device" />
  <subsystem active="no" level="info" name="service_server" />
  <subsystem active="no" level="info" name="service_client" />
  <subsystem active="no" level="info" name="action" />
  <subsystem active="no" level="info" name="variable" />
  <subsystem active="no" level="info" name="event_server" />
  <subsystem active="no" level="info" name="event_subscription_server" />
  <subsystem active="no" level="info" name="event_protocol" />
  <subsystem active="yes" level="info" name="soap" />
  <subsystem active="no" level="info" name="mediaserver" />
  <subsystem active="no" level="info" name="mediarenderer" />
  <subsystem active="no" level="info" name="controlpoint" />
  <subsystem active="no" level="info" name="connection_manager_server" />
  <subsystem active="no" level="info" name="content_directory_server" />
  <subsystem active="no" level="info" name="ms_client" />
  <subsystem active="no" level="info" name="mr_client" />
  <subsystem active="no" level="info" name="fs_store" />
  <subsystem active="no" level="info" name="fs_item" />
  <subsystem active="no" level="info" name="elisa_player" />
  <subsystem active="no" level="info" name="gstreamer_player" />
  <subsystem active="no" level="info" name="iradio_store" />
  <subsystem active="no" level="info" name="iradio_item" />
  <subsystem active="no" level="info" name="axis_cam_store" />
  <subsystem active="no" level="info" name="axis_cam_item" />
  <subsystem active="no" level="info" name="flickr_storage" />
  <subsystem active="no" level="info" name="buzztard_client" />
  <subsystem active="no" level="info" name="buzztard_factory" />
  <subsystem active="no" level="info" name="buzztard_connection" />
  <subsystem active="no" level="info" name="buzztard_item" />
  <subsystem active="no" level="info" name="buzztard_store" />
  <subsystem active="no" level="info" name="buzztard_player" />
  <logfile active="no">coherence.log</logfile>
  </logging>

<plugin active="no">
  <uuid>124d2a12-16e4-43db-82d3-72ca52c384f1</uuid>
  <name>Coherence Media Server</name>
  <backend>FSStore</backend>
  </plugin>
<plugin active="no">
    <host>localhost</host>
  <name>Elisa</name>
  <backend>ElisaPlayer</backend>
  </plugin>
<plugin active="no">
    <name>iRadio</name>
  <backend>IRadioStore</backend>
  </plugin>
<plugin active="no">
    <name>Flickr Images</name>
  <refresh>60</refresh>
  <proxy>yes</proxy>
  <backend>FlickrStore</backend>
  <icon>
      <mimetype>image/png</mimetype>
    <width>98</width>
    <depth>24</depth>
    <url>flickr-icon.png</url>
    <height>26</height>
    </icon>
  </plugin>
<plugin active="no">
    <name>Coherence MediaStore</name>
  <icon>
      <mimetype>image/png</mimetype>
    <width>120</width>
    <depth>24</depth>
    <url>coherence-icon.png</url>
    <height>106</height>
    </icon>
  <coverlocation>/data/audio/covers</coverlocation>
  <medialocation>/data/audio/music</medialocation>
  <backend>MediaStore</backend>
  <mediadb>/tmp/media.db</mediadb>
  </plugin>
<plugin active="no">
    <name>Elisa is watching you</name>
  <cam>
      <url>http://192.168.1.222:554/mpeg4/1/media.amp</url>
    <protocol>rtsp-rtp-udp:*:video/MP4V-ES:*</protocol>
    <name>Cam 1</name>
    </cam>
  <cam>
      <url>http://192.168.1.222:554/mpeg4/2/media.amp</url>
    <protocol>rtsp-rtp-udp:*:video/MP4V-ES:*</protocol>
    <name>Cam 2</name>
    </cam>
  <backend>AxisCamStore</backend>
  </plugin>
<plugin active="no">
    <host>localhost</host>
  <port>7654</port>
  <name>Buzztard Media</name>
  <backend>BuzztardStore</backend>
  </plugin>
<plugin active="no">
    <host>localhost</host>
  <port>7654</port>
  <name>Buzztard Player</name>
  <backend>BuzztardPlayer</backend>
  </plugin>
<controlpoint>yes</controlpoint>
<use_dbus>no</use_dbus>
<web-ui>no</web-ui>
<serverport>30020</serverport>
<interface active="no">eth0</interface>
</config>"""
       
        message = "A new XML configuration will be generated for you at\n "+self.configFileLocation
        
        QtGui.QMessageBox.information(None, "Unable to find Configuration", message, QtGui.QMessageBox.Ok)
        newFile = open(self.configFileLocation, "w")
        newFile.write(configFile)
        
