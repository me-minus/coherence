import sys
from PyQt4 import QtGui, QtCore
from XMLDirector import XMLDirector
from OSHandle import OSHandle

class MediaConfigPanel(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        
        
        #default size = 490 x 350
        
        #Sharing checkbox
        self.enabledCheckbox = QtGui.QCheckBox("Enable Local Content", self)
        self.enabledCheckbox.setChecked(True)
        self.enabledCheckbox.setFocusPolicy(QtCore.Qt.NoFocus)
        
        #media List
        self.mediaList = QtGui.QListWidget(self)
        self.mediaList.resize(400, 200)
        self.mediaList.setViewMode(self.mediaList.IconMode)
        self.mediaList.setDragEnabled(0)
        self.mediaList.setSpacing(22)
        self.mediaList.iconSize().setHeight(32)
        self.mediaList.iconSize().setWidth(32)
        
        #Apply button
        self.applyButton = QtGui.QPushButton("Apply", self)
        self.applyButton.setIcon(QtGui.QIcon("Icons/apply.png"))
        self.applyButton.resize(150,30)
        self.connect(self.applyButton, QtCore.SIGNAL("clicked()"), self.saveChanges)
        self.applyButton.setEnabled(False)
        
        #Add Button
        self.addButton = QtGui.QPushButton("Add Folder", self)
        self.addButton.setIcon(QtGui.QIcon("Icons/add.png"))
        self.addButton.resize(130,25)
        self.connect(self.addButton, QtCore.SIGNAL("clicked()"), self.addFolder)
        
        #remove Button
        self.removeButton = QtGui.QPushButton("Remove Folder", self)
        self.removeButton.setIcon(QtGui.QIcon("Icons/cross.png"))
        self.removeButton.resize(130, 25)
        self.connect(self.removeButton, QtCore.SIGNAL("clicked()"), self.removeFolder)
        
       
    #Update Ui state
    def initializeState(self, folderList, isActive):
        
        self.enabledCheckbox.setChecked(isActive)
        
        #setup the content
        for i in folderList:
            exactFolderName = i.split("/")[-1]
            itemIcon = self.getFolderIcon(str(exactFolderName))
            item = QtGui.QListWidgetItem(itemIcon, exactFolderName)
            item.setToolTip("<b>Location:</b>" + i)
            self.mediaList.addItem(item)
            
            
    def removeFolder(self):   
        if self.mediaList.currentItem() == None:
            return
        
        question = "Do you want to remove "+self.mediaList.currentItem().toolTip()
        confirm = QtGui.QMessageBox.question(self, "Delete Item?", question, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if confirm == QtGui.QMessageBox.Yes:
            item = self.mediaList.takeItem(self.mediaList.currentRow())
            item = None
            
        self.applyButton.setEnabled(True)
                
   
    def addFolder(self):
        fileDialog = QtGui.QFileDialog()
        fileDialog.setFileMode(fileDialog.DirectoryOnly)
        
        directoryName = fileDialog.getExistingDirectory(self, 'Select Directory','/')
        
        if len(directoryName) <= 0:
            return
        
        exactFolderName = directoryName.split("/")[-1]
        self.getFolderIcon(str(exactFolderName))
        itemIcon = self.getFolderIcon(str(exactFolderName))
        item = QtGui.QListWidgetItem(itemIcon, exactFolderName)
        item.setToolTip("<b>Location:</b>" + directoryName)
        self.mediaList.addItem(item)
        
        self.applyButton.setEnabled(True)

        
    def saveChanges(self):
        configManager = XMLDirector()
        configManager.loadXMLConfiguration()
        
        folders = []
        
        #get the folder paths and remove <b>location:<b> junk
        for i in range(0, self.mediaList.count()):
            item = self.mediaList.item(i)
            path = item.toolTip()[16:]
            folders.append(path)
            
        if self.enabledCheckbox.isChecked():
            isActive = "yes"
        else:
            isActive = "no"
            
        configManager.writeLocalContentList(folders, isActive)
        self.applyButton.setEnabled(False)
        
        #Warn about required restart
        osHandle = OSHandle()
        osHandle.warnAboutRestart()
        

    def resizeEvent(self,event):
        self.moveComponents()
        
        #Repositon UI components. 
    def moveComponents(self):
        self.enabledCheckbox.move((self.width() - self.enabledCheckbox.width())/2, 10)
        self.mediaList.setGeometry(45,40, self.width()-90,self.height() * 0.57)
        buttonY = self.mediaList.x() + self.mediaList.height()+5
        self.addButton.move(self.mediaList.x()+(self.mediaList.width()/2)-self.addButton.width() -5,buttonY)
        self.removeButton.move(self.mediaList.x()+(self.mediaList.width()/2) +5,buttonY)
        self.applyButton.move(self.width()-160, self.height()-40)
        
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
        
    def getFolderIcon(self, name):
        #Attempt to assign every folder a proper icon or default to empty folder
        icon = "folder"
        
        name = name.lower()
        
        videoList = ("movie", "vid", "celluloid", "cine", "film", "rip", "dvd", "show", "tv", "divx", "avi", "mpg", "mpeg", 
                     "season", "imdb")
        musicList = ("music", "sound", "song", "audio", "noise", "acoustic", "intrumental", "sing", "tune", "radio", 
                     "mp4", "mp3")
        imageList = ("pic", "image", "photo", "art", "draw", "illustration", "paint", "sketch", "flickr", "gif", "png", "jpg",
                     "jpeg", "portrait")

        if icon == "folder":
            for i in videoList:
                if i in name: 
                    icon = "film"
                    
        if icon == "folder":        
            for i in musicList:
                if i in name:
                    icon = "music"
                    
        if icon == "folder": 
            for i in imageList:
                if i in name:
                    icon = "picture"
        
        return QtGui.QIcon("Icons/"+icon+".png")
        
        

        
