"""
Project: Encrypted-Socks5-proxy
Author: peterrayn
Email: hjungl0200@gmail.com
License: MIT License
Copyright (c) 2026 peterrayn
"""


import socket
import threading
import gc
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import time
from cryptography.exceptions import InvalidTag
import json
import logging
import hashlib

logging.basicConfig(level=logging.INFO,filename="server.log",filemode="w",
                    format="[%(asctime)s]  %(message)s")
# This is server file

class TCP_relay:
    def __init__(self,server_address,server_port,buffer,encrypt_num,password,is_monitor_flow):
        self.server_address=server_address
        self.server_port=server_port
        self.buffer=buffer
        self.password=password
        self.encrypt_num=encrypt_num
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
    def xor_encrypt(self,data, key):
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    
    def encrypt(self,data:bytes):
        if not data:
            print("encrypt blank")
            return data
        nonce=os.urandom(12)
        secret_msg=self.key_object.encrypt(nonce,data,None)
        secret_msg=nonce+secret_msg
        return secret_msg
    def decrypt(self,data:bytes):
        if not data:
            print("decrypt blank")
            return data
        nonce=data[:12]
        secret_msg=data[12:]
        plain_msg = self.key_object.decrypt(nonce, secret_msg, None)
        return plain_msg
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
            logging.debug(f"!!!{time.time()}specific length problem:{e}")
            return
        assert len(msg)==length,"fuck! is not obey length protocol"
        return msg
    def send(self,input_conn,output_conn,orientation,BUFFER):
        msg=None
        try:
            while True:
                if orientation=="to_local":
                    msg=input_conn.recv(self.buffer)
                    if not msg:
                        break
                    logging.info(f"local << ---------------server send{len(msg)}")
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
                    

                elif orientation=="to_web":
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


                    logging.info(f"---------------->>{len(final_msg)}server receive")
                    if self.is_monitor_flow:
                        logging.info(f"{final_msg}\n")
                output_conn.sendall(final_msg)       
            
        except InvalidTag:
            print(f"!!!!!!!!!!!!!!!!!!!!!------------{time.time()}KEY ERROR\n\n\n")
        except Exception as e:
            logging.debug(f"!!!{time.time()}send problem {len(msg or'')}{orientation}:{e}")
            # print(msg)
            # print("\n")
        finally:
            input_conn.close()
            output_conn.close()
            return
    
    def interaction(self,entry_conn):

        try:
            web_len=entry_conn.recv(1)[0]
            if self.encrypt_num==1 or self.encrypt_num==2:
                web_ADDR=self.decrypt(entry_conn.recv(web_len)).decode()
            elif self.encrypt_num==3:
                web_ADDR=self.xor_encrypt(entry_conn.recv(web_len),self.xor_key).decode()
            else:
                web_ADDR=entry_conn.recv(web_len).decode()
            web_address,web_port=web_ADDR.split(":")
            web_port=int(web_port)
        except Exception as e:
            print(f"\n{e}<---")
            print(f"\nweb_ADDR error-->{web_len}{web_ADDR}<-- error")
            entry_conn.close()
            return

        try:
            exit_conn=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            exit_conn.connect((web_address,web_port))
            logging.info(f"web_address: {web_address} {web_port}")
        except:
            print(f"fail to connect:{web_address} {web_port}")
            entry_conn.close()
            return
        

        try:
            threading.Thread(target=self.send,args=(entry_conn,exit_conn,"to_web",self.buffer)).start()
            threading.Thread(target=self.send,args=(exit_conn,entry_conn,"to_local",self.buffer)).start()             
        except:
            print("interaction fuck up")
            entry_conn.close()
            exit_conn.close()
        
    def start(self):
        
        try:
            server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.server_address,self.server_port))
            server.listen()
            server.settimeout(1)
            print(f"running on: {self.server_address} {self.server_port}")
            while True:
                try:
                    entry_conn,entry_address=server.accept()
                    logging.info(f"new connection:[{entry_address}]")
                    self.monitor_program_state()
                    threading.Thread(target=self.interaction,args=(entry_conn,)).start()
                except:
                    continue
        except Exception as e:
            print(f"connot build server   {e}")

if __name__=="__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
    config_path = os.path.join(BASE_DIR, "configuration.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    TCP_relay(config["server_ip"],config["server_port"],config["buffer"],config["encrypt_num"],config["password"],config["monitor_flow"]).start()
