import imaplib
import smtplib

from email.mime.text import MIMEText
from log import Log
USERNAME = "username"
PASSWORD = "password"
class MailClient:
    def __init__(self,log):
        self.contacts = self._readContacts()
        self.mail = None
        self.__connect__()
        
        self.log = log
        self.log.INFO("Connected to",self.mail.host,":", self.mail.port)
        
    def __connect__(self):
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(USERNAME, PASSWORD)
    
    def __quit__(self):
        self.pop_conn.quit()
        
    def getNewMail(self):
        # returns a list of messages
        # of the form:
        # (from, subject, body)
        self.mail.select("inbox") # refreshes inbox
        r,d = self.mail.uid("search",None,"UNSEEN")
        if r!="OK" or len(d[0]) <= 0: return []
        
        d = d[0].replace(' ',',')
        r,d = self.mail.uid('fetch',d,"(BODY[TEXT] BODY[HEADER.FIELDS (FROM)] BODY[HEADER.FIELDS (SUBJECT)])")
        if r != "OK": return []
        mail_list = []
        for i in range(0,len(d),4):
            body = d[i][1].strip('\r\n')
            subj = d[i+1][1].strip('\r\n').strip('Subject: ')
            addr = d[i+2][1].strip('\r\n').strip('From: ')
            l = addr.find('<'); r = addr.find('>')
            if l >= 0 and r >= 0:
                addr = addr[l+1:r]
            mail_list.append( (addr,subj,body) )
            self.log.INFO("Received message \nFROM:",addr,"\nSUBJECT:",subj,"\nBODY:",body,"\n")
        
        return mail_list
                
    def sendMail(self,subject,body,to="ALL"):
        # sends the email
        # to: list of emails
        # subject: the subject
        # body: the message body
        # reconnects each time b/c we assume we're not sending emails too often
        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(USERNAME, PASSWORD)
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = USERNAME
            if to=="ALL": 
                msg['To'] = USERNAME
                to = self.contacts.keys()
                self.log.INFO("Sending group msg. Subject:", subject,"Body:",body)
            else: 
                msg['To'] = to
                self.log.INFO("Sending msg to",to," Subject:", subject,"Body:",body)
            
            server.sendmail(msg["From"],to,msg.as_string())
            server.close()
        except smtplib.SMTPException as e:
            self.log.ERROR("Error sending message:",str(e))
                
    def _readContacts(self):
        file = open("contacts",mode='r')
        contacts = {}
        for line in file.readlines():
            address,name,gender = line.split('\t')
            contacts[address] = (name,gender)
        return contacts
        
    def addContact(self,address,name,gender='X'):
        if name not in self.contacts:
            self.contacts[address] = (name,gender)
            file = open("contacts",mode='a')
            file.write(address+'\t'+name+'\t'+gender+'\n')
            file.close()
