import time
from minchamanager import MinchaManager
from mailclient import MailClient
from log import Log
#if __name__=='main':
log = Log(loglevel=Log.debug,logfile="log")
mailManager = MailClient(log)
mincha = MinchaManager(mailManager,log)

while mincha.loop == True:
    mail = mailManager.getNewMail()
    for msg in mail:
        mincha.processMsg(msg)
    mincha.checkSchedule()
    time.sleep(60)
