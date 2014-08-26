from __future__ import print_function
import sys

class Log:
    error,warn,info,debug = range(4)
    def __init__(self,logfile=sys.stdout,loglevel = info):
        if logfile == sys.stdout:
            self.logfile = logfile
        else:
            self.logfile = open(logfile,mode='a')
        self.loglevel = loglevel
        
    def ERROR(self,*args):
        if self.loglevel >= self.error: 
            print("ERROR:",*args,file=self.logfile)
            if self.logfile != sys.stdout: self.logfile.flush()
            
    def WARN(self,*args):
        if self.loglevel >= self.warn: 
            print("WARN:",*args,file=self.logfile)
            if self.logfile != sys.stdout: self.logfile.flush()
            
    def INFO(self,*args):
        if self.loglevel >= self.info: 
            print("INFO:",*args,file=self.logfile)
            if self.logfile != sys.stdout: self.logfile.flush()
            
    def DEBUG(self,*args):
        if self.loglevel >= self.debug: 
            print("DEBUG:",*args,file=self.logfile)
            if self.logfile != sys.stdout: self.logfile.flush()
            
    def close(self):
        self.logfile.close()