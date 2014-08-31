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
        
        if content[0] == 'q' and password: # quit
            self.loop = False
            self.log.INFO("Received: q")
        elif content[0] == 's' and password: # set schedule
            self.addSchedule(content[1:])
            self.log.INFO("Received: s")
        elif '0' <= content[0] and content[0] <= '9' and (self.state == State.WAITING or self.state == CONFIRMED): # positive mincha response
            self.respondents += int(content[0])
            self.log.INFO("Received:",content[0]," # respondents:",self.respondents)
        elif content[0] == 'y' and (self.state == State.WAITING or self.state == CONFIRMED): #positive mincha response
            self.respondents += 1
            self.log.INFO("Received:",content[0]," # respondents:",self.respondents)
        elif content[0] == 'c' and (self.state == State.WAITING or self.state == CONFIRMED): #rescind positive mincha response
            self.respondents -= 1
            self.log.INFO("Received:",content[0]," # respondents:",self.respondents)	
        elif content[0] == 'a' and len(content) > 1: # add contact
            self.mailclient.addContact(address,content[1:])
            self.log.INFO("Received:",content[0])
        elif content[0] == 'i': # info
            if len(content) > 1 and content[1] == 's' and password:
                self.log.INFO("Received:",content[0],content[1])
                # TODO user sets the state
                return
            self.log.INFO("Received:",content[0])
            msg = "Next Event: "
            if self.next == None: msg = msg + "Nothing scheduled right now."
            else: msg = msg + str(self.next)
            msg = msg + "\n# Respondents: " + str(self.respondents) + \
                        "\nState: " + State.get_str(self.state)
            self.mailclient.sendMail("MinchaServer Status",msg,to=address)
        elif content[0] == 'f': # forward message to me
            self.mailclient.sendMail("FWD: " + address,\
                        "SUBJECT: " + subject + "\n"+content[1:],to="ME")
            
        else:
            self.mailclient.sendMail("Invalid Response","Your repsonse is invalid. Please check your formatting or github.com/Krittian/Automated-Mincha-Texts",to=address)
            
            
    def addSchedule(self,sched="from file"):
        # format for schedule is as a newline separated list with the following cronlike time format
        # m h d M Y wait_limit "msg"
        # where
        # m is minutes: 0 - 59
        # h is hours: 0 - 23
        # d is days of the month: 1 - 31
        # M is months: 1 - 12
        # Y is year
        # wait_limit is the number of minutes before an event to send out a message [optional]
        # msg is the message to send [optional]
        # each column can hold a number in the range, a list of comma separated numbers,
        # or two numbers separated by a hyphen
        if sched == "from file":
            file = open("schedule",mode='r')
            lines = file.readlines()
            file.close()
            append = False
        else: 
            if sched[0] == 'a':
                file = open("schedule",mode='a')
                sched = sched[1:]
                append = True
            else: 
                file = open("schedule",mode='w')
                append = False
            file.write(sched)
            file.write('\n')
            file.close()
            lines = sched.splitlines()
        
        for line in lines:
            nline = []
            l = line.find('"')
            r = line.rfind('"')
            msg = ""
            if l != -1 and r != -1 and l != r:
                msg = line[l:r+1]
            line = line.replace(msg,"")
            msg = msg[1:len(msg)-1] # get rid of "
            split = line.split()
            for e in split[0:5]:
                nent = []
                for z in e.split(','):
                    prt = z.partition('-')
                    if prt[1] == '' and prt[2]=='':
                        if z=='*': nent.append(z)
                        else: nent.append(int(z))
                    elif int(prt[2]) > int(prt[0]):
                        nent.extend(range(int(prt[0]),int(prt[2])+1))
                nline.append(nent)
            nline.append(msg)
            if len(split) >= 6: nline.append(split[5]) # wait_time
            else: nline.append("40")
            l = [Event(datetime(1,1,1,H,M,0),*nline[2:5],msg=nline[5],wait_range=nline[6])\
                    for H in nline[1] for M in nline[0]]
            if append == True: self.schedule.extend(l)
            else: self.schedule = l
                
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
        
        if self.state == State.FREE and 0 < dt and dt <= e_min.wait_range:
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
        
         elif self.state == State.CONFIRMED and \
             self.respondents < State.MIN_CONFIRMED and \
             dt > 0: # TODO should it be >= 0, or would that be too close?
            self.state = State.WAITING
            self.confirmed_time = None
            msg = "Mincha for %t unconfirmed (We now have only %n people)"
            msg = msg.replace("%t",str(e_min))
            msg = msg.replace("%n",self.respondents)
            self.mailclient.sendMail("Unconfirmed "+str(e_min),msg,to="ALL")
        
        elif self.state == State.WAITING and dt <= 0:
            self.state = State.FREE
            msg = "Not enough for %t."
            msg = msg.replace("%t",str(e_min))
            self.mailclient.sendMail("Failure",msg,to="ALL")
        
        elif self.state == State.CONFIRMED:
            pass
        
        # quit, so we can restart tomorrow
        if t.time() >= datetime(1,1,1,23,00).time():
            self.loop = False
    

class Event(object):
    def __init__(self, evt_time,day,month,dow,msg="",wait_range="40"):
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
        try:
            self.wait_range = int(wait_range)
        except ValueError: self.wait_range = 40

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