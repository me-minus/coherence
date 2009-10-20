from PyQt4 import QtGui, QtCore
from OSHandle import OSHandle
from XMLDirector import XMLDirector

class SettingsConfigPanel(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.parent = parent
        self.osHandle = OSHandle()
        self.timer = QtCore.QTimer()
        
        
        #Status Label
        self.coherenceStatus = QtGui.QCommandLinkButton("Coherence Status", self)
        self.coherenceStatus.resize(260,40)
        self.coherenceStatus.setIcon(QtGui.QIcon("Icons/cross.png"))
        
        #Start button
        self.startButton = QtGui.QPushButton("Start", self)
        self.startButton.resize(90,25)
        self.connect(self.startButton, QtCore.SIGNAL("clicked()"), self.startCoherence)
        
        #Stop button
        self.stopButton = QtGui.QPushButton("Stop", self)
        self.stopButton.resize(90,25)
        self.connect(self.stopButton, QtCore.SIGNAL("clicked()"), self.stopCoherence)
        
        #Features group
        self.dbusCheckBox = QtGui.QCheckBox("Enable D-Bus")
        self.webuiCheckBox = QtGui.QCheckBox("Enable Web-UI")
        self.cntrlCheckBox = QtGui.QCheckBox("Enable Control Point")
        
        self.featureLayout = QtGui.QHBoxLayout()
        self.featureLayout.addWidget(self.dbusCheckBox)
        self.featureLayout.addWidget(self.webuiCheckBox)
        self.featureLayout.addWidget(self.cntrlCheckBox)
        
        self.featureGroup = QtGui.QGroupBox(self)
        self.featureGroup.setTitle("Features")
        self.featureGroup.setLayout(self.featureLayout)
        self.featureGroup.show()
        
        #Finer details
        #Server Port
        self.portLabel = QtGui.QCommandLinkButton("Server Port:")
        self.portLabel.setIcon(QtGui.QIcon("Icons/cog.png"))
        self.portLabel.setEnabled(False)
        self.portLabel.resize(140,40)
        
        self.serverPortInput = QtGui.QLineEdit("31240")
        self.serverPortInput.setMaxLength(5)
        self.serverPortInput.setInputMask("99999")
        
        #Interface
        self.interfaceLabel = QtGui.QCommandLinkButton("Interface:")
        self.interfaceLabel.setIcon(QtGui.QIcon("Icons/cog.png"))
        self.interfaceLabel.setEnabled(False)
        self.interfaceLabel.resize(140,40)
        
        self.interfaceCheckBox = QtGui.QCheckBox("Enable")
        self.interfaceInput = QtGui.QLineEdit("eth0")
        
        #Add to Layout and groupbox
        self.finerDetailLayout = QtGui.QGridLayout()
        self.finerDetailLayout.addWidget(self.portLabel,0,0)
        self.finerDetailLayout.addItem(QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding),0,1)
        self.finerDetailLayout.addWidget(self.serverPortInput, 0,2)
        self.finerDetailLayout.addWidget(self.interfaceLabel,1,0)
        self.finerDetailLayout.addWidget(self.interfaceCheckBox,1,1)
        self.finerDetailLayout.addWidget(self.interfaceInput,1,2)
        
        self.FinerDetailsGroup = QtGui.QGroupBox(self)
        self.FinerDetailsGroup.setTitle("Finer Details")
        self.FinerDetailsGroup.setLayout(self.finerDetailLayout)
        self.FinerDetailsGroup.show()
        
        
        #Apply button
        self.applyButton = QtGui.QPushButton("Apply", self)
        self.applyButton.setIcon(QtGui.QIcon("Icons/apply.png"))
        self.applyButton.resize(150,30)
        self.connect(self.applyButton, QtCore.SIGNAL("clicked()"), self.saveSettings)
        
        #Refresh button
        self.refreshButton = QtGui.QPushButton("Refresh", self)
        self.refreshButton.setIcon(QtGui.QIcon("Icons/refresh.png"))
        self.refreshButton.resize(150,30)
        self.connect(self.refreshButton, QtCore.SIGNAL("clicked()"), self.updateCoherenceStatus)
        
        
        self.updateCoherenceStatus()
         
        
        
    def resizeEvent(self,event):
        self.moveComponents()
    
    def moveComponents(self):
        self.coherenceStatus.move(self.width()/2-235,10)
        self.startButton.move(self.width()/2+50,20)
        self.stopButton.move(self.width()/2+145,20)
        self.featureGroup.setGeometry(10,60,self.width()-20,60)
        self.FinerDetailsGroup.setGeometry(10,130,self.width()-20,120)
        self.applyButton.move(self.width()-160, self.height()-40)
        self.refreshButton.move(self.width()-320, self.height()-40)
        
    def updateCoherenceStatus(self):
        running = self.osHandle.isCoherenceRunning()
        
        if running:
            self.coherenceStatus.setText("Coherence Status: Running")
            self.coherenceStatus.setEnabled(True)
            self.coherenceStatus.setIcon(QtGui.QIcon("Icons/apply.png"))
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)
        else:
            self.coherenceStatus.setText("Coherence Status: Not Running")
            self.coherenceStatus.setEnabled(False)
            self.coherenceStatus.setIcon(QtGui.QIcon("Icons/cross.png"))
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)
            
    def startCoherence(self):
        self.osHandle.startCoherence()
        self.startButton.setEnabled(False)
        self.timer.singleShot(1000, self.updateCoherenceStatus)
    
    def stopCoherence(self):
        self.osHandle.stopCoherence()
        self.stopButton.setEnabled(False)
        self.timer.singleShot(1000, self.updateCoherenceStatus)
        
    def saveSettings(self):
        configManager = XMLDirector()
        configManager.loadXMLConfiguration()

        serverPort = str(self.serverPortInput.text()).lstrip()
        interfaceName = str(self.interfaceInput.text()).lstrip()
        
        settings = {'dbus': self.dbusCheckBox.isChecked(), 'webui': self.webuiCheckBox.isChecked(), 
                 'control':self.cntrlCheckBox.isChecked(), 'serverport': serverPort,
                 'interfaceActive': self.interfaceCheckBox.isChecked(), 'interfaceName':interfaceName}
        
        configManager.writeSettingConfig(settings)
        
        oshandle = OSHandle()
        oshandle.warnAboutRestart()
        
    def initializeSettings(self, settings):
        self.dbusCheckBox.setChecked(settings['dbus'])
        self.webuiCheckBox.setChecked(settings['webui'])
        self.cntrlCheckBox.setChecked(settings['control'])
        self.serverPortInput.setText(settings['serverport'])
        self.interfaceCheckBox.setChecked(settings['interfaceActive'])
        self.interfaceInput.setText(settings['interfaceName'])
      
        
    def paintEvent(self, event):
        paint = QtGui.QPainter()
        paint.begin(self)
        
        size = self.size()
        w = size.width()
        h = size.height()
        
        paint.setPen(QtGui.QColor(200,200, 200))
        paint.setBrush(QtGui.QColor(235, 235, 235))
        paint.drawRect(0,0,w,h)
        
        paint.end()
        
    
