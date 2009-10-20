from subprocess import call, check_call, Popen, PIPE, CalledProcessError
import sys
from PyQt4 import QtGui, QtCore

#Handles OS <---> Coherence interactions
class OSHandle:
    def __init__(self):
        if sys.platform == "linux2":
            self.onLinux = True
            
            
        self.tempTimer = QtCore.QTimer()
        
    def isCoherenceRunning(self):
        if(self.onLinux):
            output = Popen(["ps", "-C", "coherence"], stdout=PIPE).communicate()[0]
            result = output.find("coherence")
            if result > 0:
                return True
            else:
                return False
            
    def startCoherence(self):
        if(self.onLinux):
            if not self.isCoherenceRunning():
                Popen(["daemon", "coherence"])
                
    def stopCoherence(self):
        if(self.onLinux):
            if self.isCoherenceRunning():
                try:
                    check_call(["killall", "coherence"])
                except CalledProcessError:
                    QtGui.QMessageBox.critical(None, "Error", "Unable to stop Coherence. The operation is not permitted")
                    
                    
    def warnAboutRestart(self):
        if self.isCoherenceRunning():
            message = "Your Changes will not take effect until Coherence is restarted."
            QtGui.QMessageBox.question(None, "Coherence is currently running", message)
            
                
            
            
            
