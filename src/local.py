"""
Project: Encrypted-Socks5-proxy
Author: Artist peterpar2
Email: hjungl0200@gmail.com
License: MIT License
Copyright (c) 2026 Artist
"""


import socket
import threading
import gc
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os
import time
from cryptography.exceptions import InvalidTag
import traceback
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json
import logging
import hashlib
logging.basicConfig(level=logging.INFO,filename="local.log",filemode="w",
                    format="[%(asctime)s]  %(message)s")
# This is local file

class TCP_relay:
    def __init__(self,local_address,local_port,server_address,server_port,buffer,encrypt_num,password,is_monitor_flow):
        self.local_address=local_address
        self.local_port=local_port
        self.server_address=server_address
        self.server_port=server_port
        self.buffer=buffer
        self.encrypt_num=encrypt_num
        self.password=password
        self.is_monitor_flow=is_monitor_flow
        if encrypt_num==0:
            print("[Warning] NO encryption")
            logging.info("[Warning] NO encryption")
            
        elif encrypt_num==1:
            logging.info("encryption Method--poly1305")
            self.key=self.get_key_from_pass()
            self.key_object=ChaCha20Poly1305(self.key)
            self.key_len_increment=28
            
        elif encrypt_num==2:
            logging.info("encryption Method--AESGCM")
            self.key=self.get_key_from_pass()
            self.key_object=AESGCM(self.key)
            self.key_len_increment=28
        elif encrypt_num==3:
            print("[Warning] XOR")
            logging.info("[Warning] XOR")
            self.xor_key=b"mykeyppw9forenvirn?fi3p"
    def get_key_from_pass(self):
        password=self.password.encode()
        add=b"safg*53s2"
        key = hashlib.sha256(password+add).digest()
        return key
    def monitor_program_state(self):
        logging.info(f"threading count: {threading.active_count()}")
        sockets = [o for o in gc.get_objects() if isinstance(o, socket.socket)]
        logging.info(f"current socket quantity:{len(sockets)}" )
    def encrypt(self,data:bytes):
        nonce=os.urandom(12)
        secret_msg=self.key_object.encrypt(nonce,data,None)
        secret_msg=nonce+secret_msg
        return secret_msg
    def decrypt(self,data:bytes):
        nonce=data[:12]
        secret_msg=data[12:]
        plain_msg = self.key_object.decrypt(nonce, secret_msg, None)
        return plain_msg
    def xor_encrypt(self,data, key):
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    def receive_specified_msg(self,conn,length):
        msg=b''
        msg_len=0
        try:
            while msg_len<length:
                new_msg=conn.recv(length-msg_len)
                if not new_msg:
                    # print(f"====receive blank status")
                    return False
                msg=msg+new_msg
                msg_len=len(msg)
        except Exception as e:
            logging.debug(f"specific length problem:{e}")
            return
        assert len(msg)==length,"fuck! is not obey length protocol"
        return msg

    def send(self,input_conn,output_conn,orientation):
        msg=None
        try:

            while True:

                if orientation=="to_server":
                    msg=input_conn.recv(self.buffer)
                    if not msg:
                        logging.debug("===receive blank from client")
                        break
                    logging.info(f"local send {len(msg)}--------------->server")
                    if self.is_monitor_flow:
                        logging.info(f"{msg}\n")
                    if self.encrypt_num==1 or self.encrypt_num==2:
                        msg=self.encrypt(msg)
                        msg_len=len(msg)
                        msg_len=self.encrypt((msg_len).to_bytes(2,"big"))
                        final_msg=msg_len+msg
                    elif self.encrypt_num==3:
                        final_msg=self.xor_encrypt(msg,self.xor_key)
                    else:
                        msg_len=len(msg).to_bytes(2,"big")
                        final_msg=msg_len+msg
                    

                elif orientation=="to_client":
                    if self.encrypt_num==1 or self.encrypt_num==2:
                        msg_len=self.receive_specified_msg(input_conn,2+self.key_len_increment)
                        if not msg_len:
                            break
                        msg_len=int.from_bytes(self.decrypt(msg_len),"big")
                        msg=self.receive_specified_msg(input_conn,msg_len)
                        final_msg=self.decrypt(msg)
                    elif self.encrypt_num==3:
                        msg=input_conn.recv(self.buffer)
                        if not msg:
                            break
                        final_msg=self.xor_encrypt(msg,self.xor_key)
                    else:
                        msg_len=self.receive_specified_msg(input_conn,2)
                        if not msg_len:
                            break
                        msg_len=int.from_bytes(msg_len,"big")
                        final_msg=self.receive_specified_msg(input_conn,msg_len)
        
                    logging.info(f"local receive {len(final_msg)}<----------------server")
                    if self.is_monitor_flow:
                        logging.info(f"{final_msg}\n")    
                output_conn.sendall(final_msg)
        
        
        except InvalidTag :
            print(f"!!!!!!!!!!!!!!!!!!!!!------------{time.time()}KEY ERROR\n {len(msg or'')}{orientation}\n {msg}\n\n\n")
        except Exception as e:
            print(f"!!!{time.time()}send problem {len(msg or'')}{orientation}:{e}")
            # print(f"{msg}\n")
            traceback.print_exc()
        finally:
            logging.debug(f"===={time.time()}i close it status: {orientation}")
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type:
                print("exception:", exc_value)
            input_conn.close()
            output_conn.close()
            return
    
    def interaction(self,entry_conn):

        # socks 5
        msg=entry_conn.recv(2)
        if len(msg)<2:
            entry_conn.close()
            return
        
        version,method_num = msg[0],msg[1]
        methods=entry_conn.recv(method_num)

        entry_conn.sendall(b''.join([(5).to_bytes(1,"big"),(0).to_bytes(1,"big")]))

        msg=entry_conn.recv(4)
        if len(msg)<4:
            entry_conn.close()
            return
        
        version, cmd, _, address_type= msg[0],msg[1],msg[2],msg[3]
        
        if version!=5 or cmd !=1:
            entry_conn.close()
            return
        
        if address_type==1:
            web_address=socket.inet_ntoa(entry_conn.recv(4))
        elif address_type==3:
            domain_len=entry_conn.recv(1)[0]
            web_address=entry_conn.recv(domain_len).decode()
        else:
            print("cant accept this address type")
            entry_conn.close()
            return
        
        web_port = int.from_bytes(entry_conn.recv(2), "big")

        try:
            exit_conn=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            exit_conn.connect((self.server_address,self.server_port))
            # print(f"server_address: {self.server_address} {self.server_port}")
            logging.info(f"server_address: {self.server_address} {self.server_port}")
        except:
            print(f"fail to connect:{self.server_address} {self.server_port}")
            entry_conn.close()
            return
        

        # tell the server the web ip and port
        
        if self.encrypt_num==1 or self.encrypt_num==2:
            web_ADDR=self.encrypt(f"{web_address}:{web_port}".encode())
        elif self.encrypt_num==3:
            web_ADDR=self.xor_encrypt(f"{web_address}:{web_port}".encode(),self.xor_key)
        else:
            web_ADDR=f"{web_address}:{web_port}".encode()
        web_ADDR_len=bytes([len(web_ADDR)])
        web_ADDR_msg=web_ADDR_len+web_ADDR
        exit_conn.sendall(web_ADDR_msg)




        bind_add=exit_conn.getsockname()
        msg=b''.join([(5).to_bytes(1,"big"),(0).to_bytes(1,"big"),(0).to_bytes(1,"big"),
                      (1).to_bytes(1,"big"),socket.inet_aton(bind_add[0]),(bind_add[1]).to_bytes(2,"big")])
        entry_conn.sendall(msg)



        try:
            threading.Thread(target=self.send,args=(entry_conn,exit_conn,"to_server")).start()
            threading.Thread(target=self.send,args=(exit_conn,entry_conn,"to_client")).start()             
        except:
            print("interaction fuck up")
            entry_conn.close()
            exit_conn.close()
        
    def start(self):
        
        try:
            local=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            local.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            local.bind((self.local_address,self.local_port))
            local.listen()
            local.settimeout(1)
            print(f"running on: {self.local_address} {self.local_port}")
            print(f"(Additional) V2rayN link-->")
            print(f"socks://Og@{self.local_address}:{self.local_port}#minisocks")
            while True:
                try:
                    entry_conn,entry_address=local.accept()
                    logging.info(f"new connection:[{entry_address}]")
                    self.monitor_program_state()
                    threading.Thread(target=self.interaction,args=(entry_conn,)).start()
                except:
                    continue
        except Exception as e:
            print(f"connot build local server   {e}")

if __name__=="__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # main.py 所在目录
    config_path = os.path.join(BASE_DIR, "configuration.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    TCP_relay(config["local_ip"],config["local_port"],config["server_ip"],config["server_port"],config["buffer"],config["encrypt_num"],config["password"],config["monitor_flow"]).start()