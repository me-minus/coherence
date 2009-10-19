import sys
from subprocess import check_call, PIPE, CalledProcessError, STDOUT

#Check dependencies
if sys.platform == "linux2":
    try:
        from PyQt4 import QtGui,QtCore
    except:
        print "\nError: You do not have the required dependencies installed on your system."
        print "*Missing dependency: PyQt*"
        print "Check the included documentation for more information"
        sys.exit(1)
        
    try:
        output = check_call(["daemon"], stdout=PIPE, stderr=STDOUT)
    except CalledProcessError:
        pass #installed
    except OSError:
        print "\nError: You do not have the required dependencies installed on your system."
        print "*Missing dependency: Daemon*"
        print "Check the included documentation for more information"
        sys.exit(1)


from UI.ConfigWindow import ConfigWindow


app = QtGui.QApplication(sys.argv)
window = ConfigWindow()
window.show()

sys.exit(app.exec_())
