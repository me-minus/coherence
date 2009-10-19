from PyQt4 import QtGui, QtCore

class ServicesConfigPanel(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.parent = parent
        
        #Status
        self.errorMessage = QtGui.QCommandLinkButton("The Online Services browser has not been fully implemented yet.", self)
        self.errorMessage.resize(500,60)
        self.errorMessage.setIcon(QtGui.QIcon("Icons/cross.png"))
        self.errorMessage.setEnabled(False)
        
        
        
    def resizeEvent(self,event):
        self.moveComponents()
    
    def moveComponents(self):
        self.errorMessage.move(self.width()/2-240, self.height()/2-30)
        
        
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
        
    
