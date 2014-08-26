from datetime import datetime
from log import Log


class State:
    FREE,WAITING,CONFIRMED,PANIC=range(4)
    WAIT_RANGE = 40 # minutes before the schedule Mincha time before texting
    MIN_CONFIRMED = 10 # Jewish, adult, male humans
    DELAY_TO_FREE = 12 # Hours after mincha was confirmed

    @staticmethod
    def get_str(state):
        if state == State.FREE: return "FREE"
        elif state == State.WAITING: return "WAITING"
        elif state == State.CONFIRMED: return "CONFIRMED"
        elif state == State.PANIC: return "PANIC"

    
class MinchaManager:
    def __init__(self, mail_client,log):
        # initialize schedule
        # initialize contact list
        self.mailclient = mail_client
        self.schedule = []
        self.addSchedule(sched="from file")
        self.state = State.FREE
        self.respondents = 0
        self.loop = True
        self.confirmed_time = None
        self.next = None
        
        self.log = log
        self.log.INFO("Starting Manager: Current schedule is ",self.schedule)
        
    def processMsg(self,msg):
        address = msg[0]
        subject = msg[1]
        content = msg[2]

        if len(content) == 0:
            return
        if len(content) > 4 and content[:4]=="PASSWORD": 
            password = True
            content = content[4:]
        else: password = False
        
        if content[0] == 'q':
            self.loop = False
            self.log.INFO("Received: q")
        elif content[0] == 's' and password:
            self.addSchedule(content[1:])
            self.log.INFO("Received: s")
        elif '0' <= content[0] and content[0] <= '9' and self.state == State.WAITING:
            self.respondents += int(content[0])
            self.log.INFO("Received:",content[0]," # respondents:",self.respondents)
        elif content[0] == 'y' and self.state == State.WAITING:
            self.respondents += 1
            self.log.INFO("Received:",content[0]," # respondents:",self.respondents)
        elif content[0] == 'a' and len(content) > 1:
            self.mailclient.addContact(address,content[1:])
            self.log.INFO("Received:",content[0])
        elif content[0] == 'i':
            if len(content) > 1 and content[1] == 's' and password:
                # TODO user sets the state
                return
            msg = "Next Event: "
            if self.next == None: msg = msg + "Nothing scheduled right now."
            else: msg = msg + str(self.next)
            msg = msg + "\n# Respondents: " + str(self.respondents) + \
                        "\nState: " + State.get_str(self.state)
            self.mailclient.sendMail("MinchaServer Status",msg,to=address)
            
            
    def addSchedule(self,sched="from file"):
        # format for schedule is as a newline separated list with the following cronlike time format
        # m h d M Y
        # where
        # m is minutes: 0 - 59
        # h is hours: 0 - 23
        # d is days of the month: 1 - 31
        # M is months: 1 - 12
        # Y is year
        # each column can hold a number in the range, a list of comma separated numbers,
        # or two numbers separated by a hyphen
        if sched == "from file":
            file = open("schedule",mode='r')
            lines = file.readlines()
            file.close()
        else: 
            if sched[0] == 'a':
                file = open("schedule",mode='a')
                sched = sched[1:]
            else: file = open("schedule",mode='w')
            file.write(sched)
            file.write('\n')
            file.close()
            lines = sched.splitlines()
        
        for line in lines:
            nline = []
            for e in line.split():
                nent = []
                for z in e.split(','):
                    prt = z.partition('-')
                    if prt[1] == '' and prt[2]=='':
                        if z=='*': nent.append(z)
                        else: nent.append(int(z))
                    elif int(prt[2]) > int(prt[0]):
                        nent.extend(range(int(prt[0]),int(prt[2])+1))
                nline.append(nent)
            l = [Event(datetime(1,1,1,H,M,0),nline[2],nline[3],nline[4]) \
                    for H in nline[1] for M in nline[0]]
            self.schedule.extend(l)
                
    def checkSchedule(self):
        t = datetime.now()
        m = 9999
        e_min = None
        for e in self.schedule:
            dt = e.matchtime(t)
            if dt >= 0 and dt < m:
                m = dt
                e_min = e
        self.next = e_min
        if e_min == None: return
        
        if self.state == State.FREE and 0 < dt and dt <= State.WAIT_RANGE:
            self.state = State.WAITING
            self.respondents = 0
            msg = "Would you like Mincha at %t?"
            subj = "Mincha %t?"
            if e_min.msg != "":
                msg = e_min.msg
            msg = msg.replace("%t",str(e_min))
            subj = subj.replace("%t",str(e_min))
            self.mailclient.sendMail(subj,msg,to="ALL")
            
        elif self.state == State.WAITING and \
             self.respondents >= State.MIN_CONFIRMED and \
             dt > 0: # TODO should it be >= 0, or would that be too close?
            self.state = State.CONFIRMED
            self.confirmed_time = datetime.now()
            msg = "Mincha confirmed for %t"
            msg = msg.replace("%t",str(e_min))
            self.mailclient.sendMail("Confirmed "+str(e_min),msg,to="ALL")
            
        elif self.state == State.WAITING and dt <= 0:
            self.state = State.FREE
            msg = "Not enough for %t."
            msg = msg.replace("%t",str(e_min))
            self.mailclient.sendMail("Failure",msg,to="ALL")
        
        elif self.state == State.CONFIRMED and \
             (datetime.now()-self.confirmed_time).seconds/3600 >= State.DELAY_TO_FREE:
                 self.state = State.FREE
    

class Event(object):
    def __init__(self, evt_time,day,month,dow,msg=""):
        """
        desc: min hour day month dow
            day: 1 - num days
            month: 1 - 12
            dow: mon = 1, sun = 7
        """
        self.time = evt_time
        self.day = day
        self.month = month
        self.dow = dow
        self.msg = msg

    def __repr__(self):
        return "Event("+str(self)+")"
    def __str__(self):
        return str(self.time.hour)+":"+str(self.time.minute)

    def _match(self,dateItem,evntItems):
        for e in evntItems:
            if e == '*' or dateItem == e: return True
        return False

    # returns time difference in minutes between event and t
    # or -1 if t is after event
    def matchtime(self, t):
        if  self._match(t.month        , self.month) and \
            self._match(t.isoweekday() , self.dow) and \
            self._match(t.day          , self.day):
                dt = self.time - datetime(1,1,1,t.hour,t.minute)
                if dt.days < 0: return -1
                else: return dt.seconds/60
        else:
            return -1