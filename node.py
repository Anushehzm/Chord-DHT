import sys
import socket, threading
import pickle
import time
import os
import shutil
from os import listdir,system,name
from os.path import join, isfile
import hashlib
import intervals
import itertools
from Tkinter import *
import tkMessageBox

######folder has three files initially just to show redistribution when new node comes
# to put in file, the files to be put must be in same directory as code

#####every successor will have files in case of sudden node failure
delete=False
class Node:
    def __init__(self, IP, port, connIP, connport, first=False):
        self.port=int(port)
        self.IP=IP
        self.m=10
        self.filelist=[]
        self.first=first
        self.nodehashed()
        self.directory='Node_'+str(self.id) #every node has a folder with files--create new folder called Node_*Id*, first mai saari folder ki files transfer and later redistribute upon node joining and leaving
        self.createfolder()
        self.fingertable=[]
        self.fingertab()
        self.successor={'node_id': self.id,'port': self.port, 'IP': self.IP}
        self.predecessor={'node_id': self.id ,'port': self.port, 'IP': self.IP}
        self.successorlist=[self.successor,self.successor,self.successor,self.successor,self.successor]
        self.successorlist=[{'node_id': self.id,'port': self.port, 'IP': self.IP},{'node_id': self.id,'port': self.port, 'IP': self.IP},{'node_id': self.id,'port': self.port, 'IP': self.IP},{'node_id': self.id,'port': self.port, 'IP': self.IP},{'node_id': self.id,'port': self.port, 'IP': self.IP}]
        w=threading.Thread(target=self.start, args=())
        inter=threading.Thread(target=self.interface, args=())
        inter.start()
        w.start()
        # if (self.first):
        #     self.copyfiles('Folder', self.directory) #just for trying, baad mai socket say hi jaein gay

        if not self.first:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #this connects to a host fro bootstrapping
            soc.connect((connIP, connport))
            soc.sendall(pickle.dumps({'Command':'Bootstrap','node_id':self.id}))
            p = threading.Thread(target = self.listeningforupdates, args = (soc, (connIP,connport)))
            p.start()
            #once this node knows who it's successor , pred are assign to self.succ/pred and take some of succ's files (copy, dont move takay node churn mai masla na ho)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #this socket listens for other nodes wanting to connect through this node
        self.s.bind((self.IP , self.port))
        self.s.listen(3)
        t = threading.Thread(target = self.listeningforbootstrap, args = ())
        t.start()
    def __del__(self):
        clear_screen()
        # print("Leaving system. Goodbye!")
        # time.sleep(3)
    def interface(self):
        global delete
        while True:
            if delete==True:
                return
            choice=raw_input("Select one of the following options: \n Press 1 to view the node's data (fingertable, successor list, file list etc). \n Press 2 to add file to the system \n Press 3 to get a file from the system \n Press 4 to leave system.\n")
            while choice != '1' and choice != '2' and choice != '3' and choice != '4':
                choice=raw_input("Incorrect entry. Press a number from 1 to 4 inclusive.")
            if choice=='1':
                print("Node id is "+ str(self.id))
                print("Node's successor details: ")
                print(self.successor)
                print("Node's predecessor details: ")
                print(self.predecessor)
                self.printfingertable()
                self.printsuccessorlist()
                print("List of files present in node: ")
                for i in self.filelist:
                    print i

            elif choice=='2':
                filename=raw_input("Enter file name to add to system.\n")
                self.put(filename)

            elif choice=='3':
                filename=raw_input("Enter file name to get from system.\n")
                self.get(filename)
            elif choice=='4':

                if (self.id==self.successor['node_id']):#single node
                    # print("Single node case")
                    shutil.rmtree(self.directory)
                    delete=True
                    self.__del__()
                elif (self.successor['node_id']==self.predecessor['node_id']): #only two nodes in system
                    #transfer all files to successor if it doesnt already have it which it should
                    ##########send all files to other node here#######
                    print("Replicating files before departure")
                    for i in self.filelist:
                        # x=self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i)
                        # if x:
                        #     print(i + " should not transfer")
                        # if not x:#self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", filename): #only send if they dont already have it
                        if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i) and self.closed_interval(self.predecessor['node_id'], self.id, self.filehashed(i)): #only send if they dont already have it
                            self.sendupdate(self.successor['IP'],self.successor['port'],'sendingfile', self.directory+'/'+i)
                        # time.sleep(5)
                    self.sendupdate(self.successor['IP'],self.successor['port'], "thisisyourpredecessor", self.successor)
                    self.sendupdate(self.predecessor['IP'],self.predecessor['port'],"fixsuccessor", self.predecessor)     
                    # time.sleep(5)
                    shutil.rmtree(self.directory)
                    delete=True
                    self.__del__()

                else:
                    # print("More than two node case")
                    ########send all files to successor here######
                    print("Replicating files before departure")
                    for i in self.filelist:
                        # if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i): #only send if they dont already have it
                        if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i) and self.closed_interval(self.predecessor['node_id'], self.id, self.filehashed(i)): #only send if they dont already have it
                            self.sendupdate(self.successor['IP'],self.successor['port'],'sendingfile', self.directory+'/'+i)
                        # time.sleep(5)
                        
                    self.sendupdate(self.successor['IP'],self.successor['port'], "thisisyourpredecessor", self.predecessor)
                    self.sendupdate(self.predecessor['IP'],self.predecessor['port'],"fixsuccessor", self.successor)
                    # time.sleep(5) #let them fix and take files before deleting
                    shutil.rmtree(self.directory)
                    delete=True
                    self.__del__()

    def get(self, filename):
        key=self.filehashed(filename) ##hashed to find key
        n=pickle.loads(self.findsuccessor(key)) #found keys successor
        if n['node_id']==self.id: ##if same node tu no need to go through sockets to send file
            check=False
            for i in self.filelist:
                # print("Filename searched: " + i)
                if i==filename:
                    check=True ##is already in node
            if check:
                print("The file you're trying to get is already present in your node.")

            else:
                print("File not found in system")
        else:
            if self.sendupdate(n['IP'], n['port'], "doyouhavethisfile", filename): #returns bool checking if file is in node already or not
                print("File found. Getting file....")
                self.sendupdate(n['IP'], n['port'], "sendthisfile", filename)
            else:
                # print(2)
                print("File not found in system")


    def put(self, filename):
        file=os.path.isfile(filename)
        if file:
            key=self.filehashed(filename) ##hashed to find key
            n=pickle.loads(self.findsuccessor(key)) #found keys successor
            # print(n)
            if n['node_id']==self.id: ##if same node tu no need to go through sockets to send file
                check=False
                for i in self.filelist:
                    if i==filename:
                        check=True ##is already in node
                if check:
                    # print (1)
                    print("File already in system")
                else:
                    print("Adding file...")    
                    shutil.copy(filename, self.directory)
                    # print("check agar copy hua ya nahi")
                    self.filelist.append(filename)
                    print("Recieved and added "+filename+ " to system")


            # if x==0:
            else:
                if not self.sendupdate(n['IP'], n['port'], "doyouhavethisfile", filename): #returns bool checking if file is in node already or not
                    print("Adding file....")
                    self.sendupdate(n['IP'], n['port'], "sendingfile", filename)
                else:
                    # print(2)
                    print("File already in system")

        else:
            print("Add file to working directory before trying to add it to the DHT system!\n")
    def start(self):
   
        while True:

            if self.successor['node_id']!=self.id:
                t = threading.Thread(target = self.updatefingertable, args = ())
                t.start()
                e = threading.Thread(target = self.updatesuccessorlist, args = ())
                e.start()
                y = threading.Thread(target = self.checksuccessor, args = ())
                y.start()
                break
    def checksuccessor(self):
        missed=0
        while True:
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #this connects to a host fro bootstrapping
                soc.connect((self.successor["IP"], self.successor['port']))
                soc.sendall(pickle.dumps({'Command':'ping'}))
                d=soc.recv(1024)
                soc.close()
            except:
                missed=missed+1        
                if missed==3:
                    missed=0
                    self.successor=self.successorlist[1]
                    # self.sendupdate(self.successor['IP'],self.successor['port'], "redistributefiles", self.successor)
                    # time.sleep(10)

                    # send new successor replicated files
                    for i in self.filelist: ##aik aur condition daalni kay meri hi files aagay jaein pred ki nahi
                        if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i) and self.closed_interval(self.predecessor['node_id'], self.id, self.filehashed(i)): #only send if they dont already have it
                            self.sendupdate(self.successor['IP'],self.successor['port'],'sendingfile', self.directory+'/'+i)
                    
                    if self.predecessor!=self.successorlist[0]:
                        self.sendupdate(self.successor['IP'],self.successor['port'], "thisisyourpredecessor", {'node_id':self.id, 'IP':self.IP, 'port':self.port})
                continue
    def updatesuccessorlist(self):
        global delete        
        while True:
            self.successorlist[0]=self.successor
            #replication if successor changes
            for i in self.filelist:
                # ?if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i): #only send if they dont already have it
                if not self.sendupdate(self.successor['IP'], self.successor['port'], "doyouhavethisfile", i) and self.closed_interval(self.predecessor['node_id'], self.id, self.filehashed(i)): #only send if they dont already have it 
                    self.sendupdate(self.successor['IP'],self.successor['port'],'sendingfile', self.directory+'/'+i)

            #####send files to successor whenever updated#####
            for i in range(1,5): #1-4
                try:
                    self.successorlist[i]=self.sendupdate(self.successorlist[i-1]['IP'],self.successorlist[i-1]['port'],'giveyoursuccessor', self.successorlist[i-1]['node_id'])
                    # for j in self.filelist:
                    #     self.sendupdate(self.successorlist[i]['IP'],self.successorlist[i]['port'], "redistributefiles", j)
                    
                    #######send i-1 ki files to successorlist[i] here########
                except:
                    continue            


    def sendupdate(self, IP, port, command, data):
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #this connects to a host fro bootstrapping 
            soc.connect((IP, port))
        except:
            # print("exception in send update")
            return {'node_id':self.id, 'IP':self.IP, 'port':self.port}#{'node_id':self.id, ''}
        if command=="givesuccessor":
            soc.sendall(pickle.dumps({'Command':command, "node_id":data}))
            d=soc.recv(1024)
            d2=pickle.loads(d)
            soc.close()
            return d2
        elif command=='sendthisfile':
            # if data.lower().endswith('.txt'): #extension check
            soc.sendall(pickle.dumps({'Command':command, "filename":data}))
            filename=data
            # data=update['data']
            with open(self.directory+'/'+filename, 'ab') as f:
                x=""
                while True:
                    info=soc.recv(1024)
                    # data=conn.recv(1024)
                    # print("What was received: " +info)
                    # print('Receiving '+filename)
                    # print("Recieved data: "+ data)
                    # print("Size of recieved: " + str(sys.getsizeof(info)))
                    f.write(info)
                    # print('written')
                    if sys.getsizeof(info)<1024:
                        # print("broke")
                        break
            print(filename + " fully gotten")
            self.filelist.append(filename)
            # elif data.lower().endswith('.mp4'):
            #     print("vid case")

        elif command=="sendingfile":
            # if data.lower().endswith('.txt'):
            f=open(data, 'rb')
            l=f.read(1024)
            for i in range(len(data)):
                # print('x')
                if data[i]=="/":
                    data=data[i+1:]
                    break
            soc.sendall(pickle.dumps({'Command':command, "filename":data, 'data':""}))
            dat=soc.recv(1024)
            # print(dat)

            # print("filename is sendingfile: "+ data)

            # soc.sendall(pickle.dumps({'Command':command, "filename":data, 'data':l}))
            while l:
                # print("Sending "+ data)
                # print('Sent ', repr(l))
                soc.sendall(l)
                l=f.read(1024)
                # if l:
                #     soc.sendall(l)
            f.close()
            print('Sent all of ' + data)
            soc.close()  
            # elif data.lower().endswith('.mp4'):
            #     print("vid case") 
        # elif command=="sendingfile1":
        #     key=self.filehashed(data)
        #     n=pickle.loads(self.findsuccessor(key))
        #     if not self.sendupdate(n['IP'], n['port'], "doyouhavethisfile", data): #returns bool
        #         # print("Adding file....")
        #         # self.sendupdate(n['IP'], n['port'], "sendingfile", filename)
        #         f=open(self.directory +'/'+data, 'rb')
        #         l=f.read(1024)
        #         # x=sys.getsizeof(pickle.dumps({'Command':command, "filename":data, 'data':l}))
        #         # print(x)
        #         soc.sendall(pickle.dumps({'Command':command, "filename":data, 'data':l}))
        #         while l:
        #             print("Sending "+ data)
        #             # print('Sent ', repr(l))
        #             l=f.read(1024)
        #             if l:
        #                 soc.sendall(l)
        #         f.close()
        #         print('Sent' + data)
        #         soc.close()
        #         os.remove(self.directory +'/'+data)
            # else:
            #     print("File already in system")
            #     soc.close()

        elif command=="doyouhavethisfile":
            soc.sendall(pickle.dumps({'Command':command, "filename":data}))
            d=soc.recv(1024)
            d2=pickle.loads(d)
            soc.close()
            return d2['bool']
        elif command=='redistributefiles':
            soc.sendall(pickle.dumps({'Command':command, "node_id":data}))
            soc.close()            
        elif command=="givepredecessor":
            soc.sendall(pickle.dumps({'Command':command, "node_id":data}))
            d=soc.recv(1024)
            # print(d)
            d2=pickle.loads(d)
            soc.close()
            return d2
        elif command=="giveyoursuccessor":
            soc.sendall(pickle.dumps({'Command':command, "node_id":data}))
            d=soc.recv(1024)
            d2=pickle.loads(d)
            soc.close()
            return d2
        elif command=='thisisyourpredecessor':
            soc.sendall(pickle.dumps({'Command':command, "predecessor":data}))
            soc.close()
        elif command=='thisisyoursuccessor' or 'fixsuccessor':
            soc.sendall(pickle.dumps({'Command':command, "successor":data}))
            soc.close()
    def nodehashed(self):
        hashed=hashlib.sha1(self.IP+str(self.port))
        h=hashed.hexdigest()
        truncated_to_7_bits=int(h,16) % 2**(self.m)
        self.id=truncated_to_7_bits 
        print("Key assigned to node: "+ str(truncated_to_7_bits))
    def filehashed(self, string):
        hashed=hashlib.sha1(string)
        h=hashed.hexdigest()
        truncated_to_7_bits=int(h,16) % 2**(self.m)
        key_id=truncated_to_7_bits 
        # print("Key assigned to file: "+ str(truncated_to_7_bits))
        return key_id
        #rename file by going into self.directory
    def fingertab(self): #initially sab ka yehi ho ga
        for i in range(self.m):
            self.fingertable.append({'key_id':(self.id + 2**(i))%(2**(self.m)), 'node_id':self.id, 'IP':self.IP, 'port':self.port})
    def closed_interval(self, start, end, n):
        if start<end:
            if n>start and n <=end:
                return True
            else:
                return False
        elif end<start:
            if n<2**self.m and n>start:
                return True
            else:
                end=end+2**self.m
                n=n+2**self.m
                if n<=end and n>start:
                    return True
                else:
                    return False
        else: #start==end
            if n==start:
                return True
            else:
                return False
    def open_interval(self, start, end, n): 
        if start<end:
            if n>start and n <end:
                return True
            else:
                return False
        elif end<start:
            if n<2**self.m and n>start:
                return True
            else:
                end=end+2**self.m
                n=n+2**self.m
                if n<end and n>start:
                    return True
                else:
                    return False
        else: #start==end
            return False
    def updatefingertable(self):
        global delete
        while True:
            # if delete==True:
            #     print("updatefingertable")

            #     break
            # time.sleep(3)
            for i in range(self.m):
                calc=(self.id + 2**(i))%(2**(self.m))
                try:
                    succ=pickle.loads(self.findsuccessor(calc))
                    # print(succ)
                    self.fingertable[i]={'key_id':calc, 'node_id':succ['node_id'], 'IP': succ['IP'], 'port': succ['port']}
                except:
                    # print("exception")
                    continue
            #check
            # print("Printing fingertable: ")
            # self.printfingertable()
        # time.sleep(5)

    def printsuccessorlist(self):
        print("Printing node's successorlist: ")
        for i in self.successorlist:
            print(i)
    def printfingertable(self):
        print("Printing node's fingertable: ")
        for i in self.fingertable:
            print(i)
    def createfolder(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
    def movefiles(self, src, dest):
        items=os.listdir(src)
        for f in items:
            shutil.move(join(src, f), dest)
    def copyfiles(self, src, dest):
        items=os.listdir(src)
        for f in items:
            self.filelist.append(f)
            shutil.copy(join(src, f), dest)
    def findsuccessor(self, key):

        if self.closed_interval(self.id, self.successor['node_id'],key):
            return pickle.dumps(self.successor)
        else:
            n=self.closest_preceding_node(key) #got fingertable ki entry with key_id, node_id, port and IP
            da=pickle.loads(n)
            if (da['node_id']==self.id):
                return pickle.dumps(self.successor)#({'node_id':self.id, 'IP': self.IP, 'port':self.port}) #yeh sahi?
            else:
                return self.sendupdate(da['IP'], da['port'], "givesuccessor", key)

    def closest_preceding_node(self, key):
        # print ('inside closest preceding node')
        for i in range(self.m-1, -1, -1):
            if self.open_interval(self.id, key, self.fingertable[i]['node_id']):
                # print(i+1, 'th finger')
                # print('closest prec finger of ', key, ' is: ' , self.fingertable[i])
                return pickle.dumps(self.fingertable[i])
        # print('closest prec finger of ', key, ' is: ' , {'key_id': self.id, 'node_id':self.id, 'IP': self.IP, 'port':self.port})
        return pickle.dumps({'key_id': self.id, 'node_id':self.id, 'IP': self.IP, 'port':self.port})
    def listeningforupdates(self,conn,addr):
        global delete
        while True:
            # if delete==True:
            #     print("listeningforupdates")
            #     break
            data=conn.recv(1024)
            if data:
                # print(data)
                update=pickle.loads(data)
                # print("check print ", update)
                if update['Command']=='givesuccessor':
                    conn.sendall(pickle.dumps(self.findsuccessor(int(update['node_id']))))  
                elif update['Command']=='thisisyoursuccessor': #new node kay liye
                    self.successor=update['successor']
                    # print('My successor after update is: ', self.successor)
                    self.predecessor=self.sendupdate(update['successor']['IP'], update['successor']['port'], 'givepredecessor', {'node_id': self.id, 'IP': self.IP, 'port': self.port})
                    # print('My predecessor after update is: ', self.predecessor)
                    self.sendupdate(update['successor']['IP'], update['successor']['port'], 'thisisyourpredecessor', {'node_id': self.id, 'IP': self.IP, 'port': self.port})
                    self.sendupdate(self.predecessor['IP'], self.predecessor['port'], 'fixsuccessor', {'node_id': self.id, 'IP': self.IP, 'port': self.port})
                    # time.sleep(5) #let it stablize a bit
                    self.sendupdate(self.successor['IP'],self.successor['port'], "redistributefiles", self.predecessor)
                elif update['Command']=='sendthisfile':
                    # if update['filename'].lower().endswith('.txt'):
                    filename=update['filename']
                    f=open(self.directory+'/'+filename, 'rb')
                    b=f.read(1024)
                    while b:
                        # print("Sending "+filename)
                        # print("Sent: "+b)
                        conn.sendall(b)
                        b=f.read(1024)

                    # conn.sendall(b"END")
                    f.close()
                    print("Fully sent "+filename)
                    # elif update['filename'].lower().endswith('.mp4'):
                    #     print("video case")
                elif update['Command']=='sendingfile':# or update['Command']=='sendingfile1':
                    # if update['filename'].lower().endswith('.txt'):
                    conn.sendall(b"Hi")
                    filename=update['filename']
                    data=update['data']
                    with open(self.directory+'/'+filename, 'wb') as f:
                        while True:
                            f.write(data)
                            data=conn.recv(1024)
                            # print('Receiving '+filename)
                            # print("Recieved data: "+ data)
                            if not data:
                                break

                    print(filename + " fully received")
                    self.filelist.append(filename)
                    # elif update['filename'].lower().endswith('.mp4'):
                    #     print("video case")
                elif update['Command']=='redistributefiles':
                    prepredecessor=update['node_id']
                    for i in self.filelist:
                        x=self.filehashed(i)
                        if self.closed_interval(prepredecessor['node_id'], self.predecessor['node_id'], x):
                            self.sendupdate(self.predecessor['IP'],self.predecessor['port'],'sendingfile', self.directory+'/'+i)
                        #didn't delete as successor should have files for replication too



                        # if x['node_id'] == self.predecessor['node_id']: #mera pred inn files ka successor hai

                            # self.put(i) ####simply send file not put
                            # print("Sending "+i+" to " + str(x['node_id']))
                            # try:
                            #     self.filelist.remove(i)
                            #     os.remove(i)
                            # except:
                            #     continue


                elif update['Command']=='fixsuccessor':
                    self.successor=update['successor']
                elif update['Command']=='thisisyourpredecessor':
                    self.predecessor=update['predecessor']
                    self.successor=self.fingertable[0]
                elif update['Command']=='doyouhavethisfile':
                    y=True
                    for i in self.filelist:
                        if i==update['filename']:
                            y=False
                            conn.sendall(pickle.dumps({'bool':True}))
                            break
                    if y:
                        conn.sendall(pickle.dumps({'bool':False}))
                    
                elif update['Command']=='ping':
                    pingback='pingback'
                    conn.sendall(pingback)
                elif update['Command']=='Bootstrap':
                    node_id=update['node_id']
                    conn.sendall(pickle.dumps({'Command': 'thisisyoursuccessor', 'successor':pickle.loads(self.findsuccessor(node_id))}))
                elif update['Command']=='givepredecessor':
                    conn.sendall(pickle.dumps(self.predecessor))
                elif update['Command']=='giveyoursuccessor':
                    conn.sendall(pickle.dumps(self.successor))

    def listeningforbootstrap(self):
        global delete
        while True:

            conn, addr = self.s.accept()
            p = threading.Thread(target = self.listeningforupdates, args = (conn,addr, ))
            p.start()


def clear_screen():
    if name== 'nt':
        _=system('cls')
    else:
        _=system('clear')


# def main():
#     global delete
#     clear_screen()
#     print("Welcome to DC++! Let's get straight to work...")
#     time.sleep(1.5)
#     clear_screen()
#     create_or_join=raw_input("Do you want to create a new DHT system (Press 1) or join an existing one (Press 0)? \n")
#     while create_or_join!='0' and create_or_join!='1':
#         create_or_join=raw_input("Incorrect Input. Press either 0 or 1.\n")
#     myIP=raw_input("Enter your machine's IP address\n")
#     p=raw_input("Enter your port number\n")
#     myport=int(p)
#     if (create_or_join=='0'):
#         theirIP=raw_input("Enter the machine's IP address which you'll use to enter the system\n")
#         P=raw_input("Enter the machine's port number which you'll use to enter the system\n")
#         theirport=int(P)
#     else:
#         theirIP=myIP
#         theirport=myport
#     clear_screen()
#     print("Great! Let's get this show on the road!\n")
#     time.sleep(1)
#     clear_screen()
#     node=Node(myIP, myport, theirIP, theirport ,int(create_or_join))
#     while True:
#         if delete==True:
#             # print("exiting")
#             clear_screen()
#             print("Leaving system. Goodbye!")
#             time.sleep(1.5)
#             clear_screen()
#             os._exit(1)
#             del node
#             break





def function():
    # print("myIP", myIP.get())
    # print("my port", myport.get())
    # print("their ip", theirIP.get())
    # print("their port", theirport.get())
    # print("check 1: ", var1.get())
    # print("check 2: ", var2.get())
    if (var1.get() and var2.get()) or ( not var1.get() and not var2.get()): 
        print("Incorrect Checkbox Entry")
        return
    if var1.get() and not var2.get():
        node=Node(myIP.get(), myport.get(), theirIP.get(), theirport.get() , 0)
    if var2.get() and not var1.get():
        node=Node(myIP.get(), myport.get(), theirIP.get(), theirport.get() , 1)


    while True:
        if delete==True:
            # print("exiting")
            clear_screen()
            print("Leaving system. Goodbye!")
            time.sleep(1.5)
            clear_screen()
            os._exit(1)
            del node
            break


# def main():
root=Tk()
root.title("DC++ Setup")
root.geometry("500x500")
root['bg']="purple"
# frame=Frame(root, width=500, height=500, bg="purple")
# frame.pack(fill=X)
title=Label(root, text="DC++", fg="white", bg='black', borderwidth=2, relief="groove", font=("Times New Roman",18, "bold"))
title.pack()
intro=Label(root, text="Making File Sharing as Easy as it Gets!", borderwidth=2, relief="groove", fg="white", bg='black', font=("Times New Roman",16))
intro.pack()

frameforbootstrap=Frame(root, bg="grey")
frameforbootstrap.pack()
 #check box for join or not
opt1=Label(frameforbootstrap, text="Select one of the two:", bg="grey", borderwidth=2, relief="solid" )
opt1.grid(row=1, sticky=W)
var1=IntVar()
var2=IntVar()
c= Checkbutton(frameforbootstrap, text="1. Join an existing DHT system", bg="grey", variable=var1)#, command=join(frameforbootstrap))
d= Checkbutton(frameforbootstrap, text="2. Create a new DHT system", bg="grey", variable=var2)#, command=create(frameforbootstrap))
c.grid(row=2,sticky=W)
d.grid(row=3 , sticky=W)

ip1=Label(frameforbootstrap, text="Enter your machine's IP address:", bg="grey" )
myIP=Entry(frameforbootstrap)
myport=Entry(frameforbootstrap)
theirIP=Entry(frameforbootstrap)
theirport=Entry(frameforbootstrap)
port1=Label(frameforbootstrap, text="Enter your machine's port number:", bg="grey")
ip2=Label(frameforbootstrap, text="Enter the machine's IP address which you'll use to enter the system (Leave empty if unapplicable):", bg="grey")
port2=Label(frameforbootstrap, text="Enter the machine's port number which you'll use to enter the system (Leave empty if unapplicable):", bg="grey")

ip1.grid(row=4, sticky=W)
myIP.grid(row=4, column=1)

port1.grid(row=5, sticky=W)
myport.grid(row=5, column=1)

ip2.grid(row=6, sticky=W)
theirIP.grid(row=6, column=1)

port2.grid(row=7, sticky=W)
theirport.grid(row=7, column=1)

confirm=Button(frameforbootstrap, text="Enter", fg="green", command=function)
confirm.grid(row=9) #bind making of node to this button

root.mainloop()


# main()