from datetime import datetime
from better_profanity import profanity
import time
import traceback
import sys
import string
from uuid import uuid4

"""

Meower Supporter Module

This module provides logging, error traceback, and other miscellaneous supportive functionality.
This keeps the main.py clean and more understandable.

"""

class Supporter:
    def __init__(self, meower):
        self.meower = meower
        self.cl = meower.cl
        self.packet_handler = meower.packet_callback
        self.listener_detected = False
        self.listener_id = None

        self.repair_mode = True
        self.is_deprecated = True
        self.profanity = profanity
        self.profanity.load_censor_words()
        self.ratelimits = {}
        
        if not self.cl == None:
            # Add custom status codes to CloudLink
            self.cl.codes["KeyNotFound"] = "I:010 | Key Not Found"
            self.cl.codes["PasswordInvalid"] = "I:011 | Invalid Password"
            self.cl.codes["GettingReady"] = "I:012 | Getting ready"
            self.cl.codes["ObsoleteClient"] = "I:013 | Client is out-of-date or unsupported"
            self.cl.codes["Pong"] = "I:014 | Pong"
            self.cl.codes["IDExists"] = "I:015 | Account exists"
            self.cl.codes["2FAOnly"] = "I:016 | 2FA Required"
            self.cl.codes["MissingPermissions"] = "I:017 | Missing permissions"
            self.cl.codes["Banned"] = "E:018 | Account Banned"
            self.cl.codes["IllegalChars"] = "E:019 | Illegal characters detected"
            self.cl.codes["Kicked"] = "E:020 | Kicked"
            self.cl.codes["ChatExists"] = "E:021 | Chat exists"
            self.cl.codes["ChatNotFound"] = "E:022 | Chat not found"
            self.cl.codes["Locked"] = "E:023 | Account Locked"
            self.cl.codes["PermLocked"] = "E:024 | Account Locked"
            self.cl.codes["Deleted"] = "E:025 | Account Deleted"
            self.cl.codes["EmailNotVerified"] = "E:026 | Email Not Verified"
            self.cl.codes["EmailMalformed"] = "E:027 | Email Malformed"
            self.cl.codes["EmailInvalid"] = "E:028 | Email Invalid"
            self.cl.codes["TokenInvalid"] = "E:029 | Token Invalid"
        
        # Create permitted lists of characters for posts
        self.permitted_chars_post = []
        for char in string.ascii_letters:
            self.permitted_chars_post.append(char)
        for char in string.digits:
            self.permitted_chars_post.append(char)
        for char in string.punctuation:
            self.permitted_chars_post.append(char)
        self.permitted_chars_post.append(" ")

        # Create permitted lists of characters for usernames
        self.permitted_chars_username = self.permitted_chars_post
        self.permitted_chars_username.remove(" ")
        self.permitted_chars_username.remove('"')
        self.permitted_chars_username.remove("'")
        self.permitted_chars_username.remove("*")
        self.permitted_chars_username.remove(";")
        
        # Peak number of users logger
        self.peak_users_logger = {
            "count": 0,
            "timestamp": {
                "mo": 0,
                "d": 0,
                "y": 0,
                "h": 0,
                "mi": 0,
                "s": 0,
                "e": 0
            }
        }
        
        if not self.cl == None:
            # Specify server callbacks
            self.cl.callback("on_packet", self.on_packet)
            self.cl.callback("on_close", self.on_close)
            self.cl.callback("on_connect", self.on_connect)
        
        self.log("Supporter initialized!")
    
    def full_stack(self):
        exc = sys.exc_info()[0]
        if exc is not None:
            f = sys.exc_info()[-1].tb_frame.f_back
            stack = traceback.extract_stack(f)
        else:
            stack = traceback.extract_stack()[:-1]
        trc = 'Traceback (most recent call last):\n'
        stackstr = trc + ''.join(traceback.format_list(stack))
        if exc is not None:
            stackstr += '  ' + traceback.format_exc().lstrip(trc)
        return stackstr
    
    def log(self, event):
        print("{0}: {1}".format(self.timestamp(4), event))
    
    def sendPacket(self, payload, listener_detected=False, listener_id=None):
        if not self.cl == None:
            if listener_detected:
                if "id" in payload:
                    payload["listener"] = listener_id
                self.cl.sendPacket(payload)
            else:
                self.cl.sendPacket(payload)
    
    def get_client_statedata(self, client): # "steals" information from the CloudLink module to get better client data
        if not self.cl == None:
            if type(client) == str:
                client = self.cl._get_obj_of_username(client)
            if not client == None:
                if client['id'] in self.cl.statedata["ulist"]["objs"]:
                    tmp = self.cl.statedata["ulist"]["objs"][client['id']]
                    return tmp
                else:
                    return None
    
    def modify_client_statedata(self, client, key, newvalue): # WARN: Use with caution: DO NOT DELETE UNNECESSARY KEYS!
        if not self.cl == None:
            if type(client) == str:
                client = self.cl._get_obj_of_username(client)
            if not client == None:
                if client['id'] in self.cl.statedata["ulist"]["objs"]:
                    try:
                        self.cl.statedata["ulist"]["objs"][client['id']][key] = newvalue
                        return True
                    except:
                        self.log("{0}".format(self.full_stack()))
                        return False
                else:
                    return False
    
    def delete_client_statedata(self, client, key): # WARN: Use with caution: DO NOT DELETE UNNECESSARY KEYS!
        if not self.cl == None:
            if type(client) == str:
                client = self.cl._get_obj_of_username(client)
            if not client == None:
                if client['id'] in self.cl.statedata["ulist"]["objs"]:
                    if key in self.cl.statedata["ulist"]["objs"][client['id']]:
                        try:
                            del self.cl.statedata["ulist"]["objs"][client['id']][key]
                            return True
                        except:
                            self.log("{0}".format(self.full_stack()))
                            return False
                else:
                    return False
    
    def log_peak_users(self):
        if not self.cl == None:
            current_users = len(self.cl.getUsernames())
            if current_users > self.peak_users_logger["count"]:
                today = datetime.now()
                self.peak_users_logger = {
                    "count": current_users,
                    "timestamp": self.timestamp(1)
                }
                self.log("New peak in # of concurrent users: {0}".format(current_users))
                #self.create_system_message("Yay! New peak in # of concurrent users: {0}".format(current_users))
                payload = {
                    "mode": "peak",
                    "payload": self.peak_users_logger
                }
                self.sendPacket({"cmd": "direct", "val": payload})
    
    def on_close(self, client):
        if not self.cl == None:
            if type(client) == dict:
                self.log("{0} Disconnected.".format(client["id"]))
            elif type(client) == str:
                self.log("{0} Logged out.".format(self.cl._get_username_of_obj(client)))
            self.log_peak_users()
    
    def on_connect(self, client):
        if not self.cl == None:
            if self.repair_mode:
                self.log("Refusing connection from {0} due to repair mode being enabled".format(client["id"]))
                self.cl.kickClient(client)
            else:
                self.log("{0} Connected.".format(client["id"]))
                self.modify_client_statedata(client, "authtype", "")
                self.modify_client_statedata(client, "authed", False)
    
    def on_packet(self, message):
        if not self.cl == None:
            # CL Turbo Support
            self.listener_detected = ("listener" in message)
            self.listener_id = None
            
            if self.listener_detected:
                self.listener_id = message["listener"]
            
            # Read packet contents
            id = message["id"]
            val = message["val"]
            clienttype = None
            client = message["id"]
            if type(message["id"]) == dict:
                ip = self.cl.getIPofObject(client)
                clienttype = 0
            elif type(message["id"]) == str:
                ip = self.cl.getIPofUsername(client)
                clienttype = 1
            
            # Handle packet
            cmd = None
            if "cmd" in message:    
                cmd = message["cmd"]
            
            if not self.packet_handler == None:
                self.packet_handler(self.meower, cmd, val, self.listener_detected, self.listener_id, client)
    
    def timestamp(self, ttype):
        today = datetime.now()
        if ttype == 1:
            return {
                "mo": (datetime.now()).strftime("%m"),
                "d": (datetime.now()).strftime("%d"),
                "y": (datetime.now()).strftime("%Y"),
                "h": (datetime.now()).strftime("%H"),
                "mi": (datetime.now()).strftime("%M"),
                "s": (datetime.now()).strftime("%S"),
                "e": (int(time.time()))
            }
        elif ttype == 2:
            return str(today.strftime("%H%M%S"))
        elif ttype == 3:
            return str(today.strftime("%d%m%Y%H%M%S"))
        elif ttype == 4:
            return today.strftime("%m/%d/%Y %H:%M.%S")
        elif ttype == 5:    
            return today.strftime("%d%m%Y")
        elif ttype == 6:
            return int(time.time())
        elif ttype == 7:
            return float(time.time())
    
    def ratelimit(self, client):
        # Rate limiter
        self.ratelimits[str(client)] = time.time()+1
    
    def filter(self, message):
        # Word censor
        if self.profanity != None:
            message = self.profanity.censor(message)
        else:
            self.log("Failed loading profanity filter : Using default filter as fallback")
            profanity.load_censor_words()
            message = profanity.censor(message)
        return message
    
    def isAuthenticated(self, client):
        if not self.cl == None:
            return self.get_client_statedata(client)["authed"]
    
    def setAuthenticatedState(self, client, value):
        if not self.cl == None:
            self.modify_client_statedata(client, "authed", value)
    
    def checkForBadCharsUsername(self, value):
        # Check for profanity in username, will return '*' if there's profanity which will be blocked as an illegal character
        value = self.filter(value)

        badchars = False
        for char in value:
            if not char in self.permitted_chars_username:
                badchars = True
                break
        return badchars
        
    def checkForBadCharsPost(self, value):
        badchars = False
        for char in value:
            if not char in self.permitted_chars_post:
                badchars = True
                break
        return badchars
    
    def checkForMalformedEmail(self, value):
        tmp = value.split("@")
        if len(tmp) == 2:
            if len(tmp[0]) >= 1:
                return False
            else:
                return True
        else:
            return True

    def autoID(self, client, username, type):
        if not self.cl == None:
            # really janky code that automatically sets user ID
            self.modify_client_statedata(client, "username", username)
            self.modify_client_statedata(client, "authtype", type)
            self.cl.statedata["ulist"]["usernames"][username] = client["id"]
            self.sendPacket({"cmd": "ulist", "val": self.cl._get_ulist()})
            self.log("{0} autoID given".format(username))
    
    def kickBadUsers(self, username):
        if not self.cl == None:
            # Check for clients that are trying to steal the ID and kick em' / Disconnect other sessions
            if username in self.cl.getUsernames():
                self.log("Detected someone trying to use the username {0} wrongly".format(username))
                self.cl.kickClient(username)
                time.sleep(0.5)
    
    def check_for_spam(self, client):
        if str(client) in self.ratelimits:
            return ((self.ratelimits[str(client)]) < time.time())
        else:
            return True
        
    def uuid(self):
        return str(uuid4())