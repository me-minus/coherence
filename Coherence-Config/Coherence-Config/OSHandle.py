from subprocess import call, check_call, Popen, PIPE, CalledProcessError
import sys
from PyQt4 import QtGui

#Windows code is in my flash drive... Back home... Will be updated within a few days
class OSHandle:
    def __init__(self):
        if sys.platform == "linux2":
            self.onLinux = True
            
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
                    
            
