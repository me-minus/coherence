import sys, random
from PyQt4 import QtGui, QtCore
from MediaConfigPanel import MediaConfigPanel
from XMLDirector import XMLDirector
from SettingsConfigPanel import SettingsConfigPanel
from HomeConfigPanel import HomeConfigPanel
from ServicesConfigPanel import ServicesConfigPanel
from DeviceConfigPanel import DeviceConfigPanel

class ConfigWindow(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        
        #Load XML configuration
        self.configManager = XMLDirector()
        self.configManager.loadXMLConfiguration()
        
        #setup main window
        self.setWindowTitle("Coherence Config")
        self.resize(650,350)
        self.setMinimumSize(650,350)
        screen = QtGui.QDesktopWidget().screenGeometry()
        self.move((screen.width()-self.width())/2, (screen.height()-self.height())/2)
        self.setWindowIcon(QtGui.QIcon("Icons/AppIcon.png"))
        
        #Category label
        self.categoryLabel = QtGui.QLabel("Category", self)
        labelFont = QtGui.QFont()
        labelFont.setFamily("DejaVu Sans")
        labelFont.setPointSize(14)
        labelFont.setWeight(75)
        labelFont.setBold(True)
        self.categoryLabel.setFont(labelFont)
        self.categoryLabel.setStyleSheet("color: rgb(114, 159, 207);")
        self.categoryLabel.move(10,10)

        #Navigation Buttons
   
        #Local Content
        self.lcButton = QtGui.QCommandLinkButton("Local Content", self)
        self.lcButton.setGeometry(5,40,150,30)
        self.lcButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lcButton.setIcon(QtGui.QIcon("Icons/house.png"))
        self.connect(self.lcButton, QtCore.SIGNAL("clicked()"), self.showLocalContentPanel)
        
        #Home content
        self.hcButton = QtGui.QCommandLinkButton("Home Content", self)
        self.hcButton.setGeometry(5,80,150,30)
        self.hcButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.hcButton.setIcon(QtGui.QIcon("Icons/transmit.png"))
        self.connect(self.hcButton, QtCore.SIGNAL("clicked()"), self.showHomeContentPanel)
        self.hide()
        
        #Home Devices
        self.hdButton = QtGui.QCommandLinkButton("Home Devices", self)
        self.hdButton.setGeometry(5,120,150,30)
        self.hdButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.hdButton.setIcon(QtGui.QIcon("Icons/devices.png"))
        self.connect(self.hdButton, QtCore.SIGNAL("clicked()"), self.showDeviceConfigPanel)
        
        #On-line services
        self.osButton = QtGui.QCommandLinkButton("Online Services", self)
        self.osButton.setGeometry(5,160,150,30)
        self.osButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.osButton.setIcon(QtGui.QIcon("Icons/services.png"))
        self.connect(self.osButton, QtCore.SIGNAL("clicked()"), self.showServicesConfigPanel)
        
        #settings button
        self.settingsButton = QtGui.QCommandLinkButton("Edit Settings", self)
        self.settingsButton.setGeometry(5,200,150,30)
        self.settingsButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.settingsButton.setIcon(QtGui.QIcon("Icons/cog.png"))
        self.connect(self.settingsButton, QtCore.SIGNAL("clicked()"), self.showSettingsConfigPanel)

        #close button
        self.closeButton = QtGui.QPushButton("Close Window", self)
        self.closeButton.setGeometry(5,self.height()-40,150,30)
        self.closeButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.closeButton.setIcon(QtGui.QIcon("Icons/cross.png"))
        self.connect(self.closeButton, QtCore.SIGNAL('clicked()'), self, QtCore.SLOT('close()'))
                
        #Local Content Panel
        self.localContentPanel = MediaConfigPanel(self)
        self.localContentPanel.setGeometry(160,0,self.width()-160,self.height())
        folderList, isActive = self.configManager.getLocalContentlist()
        self.localContentPanel.initializeState(folderList, isActive)
        
        #Home Content Panel
        self.homeContentPanel = HomeConfigPanel(self)
        self.homeContentPanel.setGeometry(160,0,self.width()-160,self.height())
        
        #Device config panel
        self.deviceConfigPanel = DeviceConfigPanel(self)
        self.deviceConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        
        #Online services
        self.servicesConfigPanel = ServicesConfigPanel(self)
        self.servicesConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        
        #Settings config panel
        self.settingsConfigPanel =  SettingsConfigPanel(self)
        self.settingsConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        settings = self.configManager.getSettingsConfig()
        self.settingsConfigPanel.initializeSettings(settings)
        

        

        
        self.showLocalContentPanel()
    
    #Resize the  components
    def resizeEvent(self,event):
        self.localContentPanel.setGeometry(160,0,self.width()-160,self.height())
        self.homeContentPanel.setGeometry(160,0,self.width()-160,self.height())
        self.deviceConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        self.servicesConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        self.settingsConfigPanel.setGeometry(160,0,self.width()-160,self.height())
        self.closeButton.move(5,self.height()-40)
        
    #called by local content button
    def showLocalContentPanel(self):
        self.hideAllPanels()
        self.localContentPanel.show()
        self.localContentPanel.moveComponents()
        
    def showHomeContentPanel(self):
        self.hideAllPanels()
        self.homeContentPanel.show()
        self.homeContentPanel.moveComponents()
        
    def showDeviceConfigPanel(self):
        self.hideAllPanels()
        self.deviceConfigPanel.show()
        self.deviceConfigPanel.moveComponents()
        
    def showServicesConfigPanel(self):
        self.hideAllPanels()
        self.servicesConfigPanel.show()
        self.servicesConfigPanel.moveComponents()
        
    def showSettingsConfigPanel(self):
        self.hideAllPanels()
        self.settingsConfigPanel.moveComponents()
        self.settingsConfigPanel.show()
        
    def hideAllPanels(self):
        self.localContentPanel.hide()
        self.homeContentPanel.hide()
        self.deviceConfigPanel.hide()
        self.servicesConfigPanel.hide()
        self.settingsConfigPanel.hide()
        
        
    def closeEvent(self, event):
        result = QtGui.QMessageBox.question(self, "Exit?", "Do you want to exit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if result == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
