import bcrypt

class Accounts:
    
    """
    Meower Accounts - Port complete
    
    This class provides a friendly interface to manage accounts and provide authentication.
    """
    
    def __init__(self, parent):
        # Inherit parent class attributes
        self.parent = parent
        self.log = parent.log
        self.db = parent.db
        self.uuid = parent.uuid
        self.full_stack = parent.cl.supporter.full_stack
        self.default_strength = 12
        
        # These keys should not be modified/read by a client unless explicitly requested
        self.protected_keys = [
            "lvl",
            "pswd",
            "banned",
            "email",
            "last_ip",
            "lower_username", 
            "uuid",
            "tokens", 
            "created"
        ]
        
        self.all_user_keys = [
            "lower_username",
            "uuid",
            "unread_inbox",
            "theme",
            "mode",
            "sfx",
            "debug",
            "bgm",
            "bgm_song",
            "layout",
            "pfp_data",
            "quote",
            "email",
            "pswd",
            "tokens",
            "lvl",
            "banned",
            "last_ip",
            "online"
        ]
        
        # Codes
        self.accountExists = 1
        self.accountDoesNotExist = 2
        self.accountIOError = 3
        self.accountBanned = 4
        self.accountNotBanned = 5
        self.accountCreated = 6
        self.accountDeleted = 7
        self.accountUpdated = 8
        self.accountAuthenticated = 9
        self.accountNotAuthenticated = 10
        self.accountAuthenticatedWithToken = 11
        
    def create_account(self, username:str, password:str, strength:int = None):
        if strength == None:
            strength = self.default_strength
        
        # Datatype checks
        if (not type(username) == str) or (not type(password) == str) or (not type(strength) == int):
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountExists:
           self.log(f"[Accounts] Not creating account {username}: Account already exists")
           return self.accountExists
        
        self.log(f"[Accounts] Creating account: {username}")
        
        # Hash and salt the password
        pswd_bytes = bytes(password, "utf-8")
        hashed_pw = bcrypt.hashpw(pswd_bytes, bcrypt.gensalt(strength))
        
        # Create account template (revise in Beta 6, use usersv1)
        account_data = {
            "lower_username": username.lower(),
            "uuid": str(self.uuid.uuid4()),
            "unread_inbox": False,
            "theme": "orange",
            "mode": True,
            "sfx": True,
            "debug": False,
            "bgm": True,
            "bgm_song": 2,
            "layout": "new",
            "pfp_data": 1,
            "quote": "",
            "email": "",
            "pswd": hashed_pw.decode(),
            "tokens": [],
            "lvl": 0,
            "banned": False,
            "last_ip": None,
            "online": False,
        }
        
        # Store new account in the database
        if self.db.create_item("usersv0", username, account_data):
            return self.accountCreated
        else:
            return self.accountIOError
        
    def delete_account(self, username:str):
        # Datatype checks
        if not type(username) == str:
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           self.log(f"[Accounts] Not deleting account {username}: Account does not exist")
           return self.accountDoesNotExist
        
        self.log(f"[Accounts] Deleting account: {username}")
        
        # Delete the user's data from the database
        self.db.delete_item("usersv0", username)
        
        # Delete all user's chats
        self.db.dbclient["chats"].delete_many({"owner": username})
        index = self.db.dbclient["chats"].find({"members": {"$all": [username]}})
        for chat in index:
            chat["members"].remove(username)
            self.db.write_item("chats", chat["_id"], chat)
        
        # Delete all user posts
        self.db.dbclient["posts"].delete_many({"u": username})
        
        # Delete netlog data
        netlog_index = self.db.dbclient["netlog"].find({"users": {"$all": [username]}})
        for ip in netlog_index:
            ip["users"].remove(username)
            if len(ip["users"]) == 0:
                self.files.delete_item("netlog", ip["_id"])
            else:
                if ip["last_user"] == username:
                    ip["last_user"] = ip["users"][(len(ip["users"])-1)]
                self.db.write_item("netlog", ip["_id"], ip)
        
        return self.accountDeleted
    
    def authenticate(self, username:str, password:str):
        # Datatype checks
        if (not type(username) == str) or (not type(password) == str):
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           self.log(f"[Accounts] Not authenticating account {username}: Account does not exist")
           return self.accountDoesNotExist
        
        # Prevent authentication if banned
        if self.is_account_banned(username) == self.accountBanned:
            self.log(f"[Accounts] Not authenticating account {username}: Account banned")
            return self.accountBanned
        
        result, data = self.db.load_item("usersv0", username)
        # Prevent authentication if it failed to read the account
        if not result:
            return self.accountIOError
        
        self.log(f"Authenticating account: {username}")
        
        # Check if the account is using an authentication token
        if "tokens" in data:
            if password in data["tokens"]:
                self.log(f"[Accounts] Authenticating account {username} using token")
                return self.accountAuthenticatedWithToken
        else:
            data["tokens"] = []
            result = self.db.write_item("usersv0", username, data)
            if not result:
                return self.accountIOError
        
        # Read the hashed and salted password
        pswd_bytes = bytes(password, "utf-8")
        hashed_pw = data["pswd"]
        hashed_pw_bytes = bytes(hashed_pw, "utf-8")
        result = bcrypt.checkpw(pswd_bytes, hashed_pw_bytes)
        if result:
            return self.accountAuthenticated
        else:
            return self.accountNotAuthenticated
    
    def change_password(self, username:str, newpassword:str, strength:int = None):
        if strength == None:
            strength = self.default_strength
        
        # Datatype checks
        if (not type(username) == str) or (not type(newpassword) == str) or (not type(strength) == int):
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           self.log(f"[Accounts] Not updating account password {username}: Account does not exist")
           return self.accountDoesNotExist
        
        # Prevent authentication if banned
        if self.is_account_banned(username) == self.accountBanned:
            self.log(f"[Accounts] Not updating account password {username}: Account banned")
            return self.accountBanned
        
        self.log(f"[Accounts] Updating account password: {username}")
        
        # Hash and salt the password
        pswd_bytes = bytes(newpassword, "utf-8")
        hashed_pw = bcrypt.hashpw(pswd_bytes, bcrypt.gensalt(strength))
        
        # Load and update the password entry in the account
        result, account_data = self.db.load_item("usersv0", username)
        if not result:
            return self.accountIOError
        
        account_data["pswd"] = hashed_pw.decode()
        result = self.db.write_item("usersv0", username, account_data)
        
        if result:
            return self.accountUpdated
        else:
            return self.accountIOError
    
    def account_exists(self, username:str, ignore_case:bool = False):
        if not type(username) == str:
            raise TypeError
        
        if ignore_case:
            if self.db.does_item_exist("usersv0", username):
                return self.accountExists
            else:
                return self.accountDoesNotExist
        else:
            payload = self.db.find_items("usersv0", 
                {
                    "lower_username": username.lower()
                }
            )
            if len(payload) != 0:
                return self.accountDoesNotExist
            else:
                return self.accountExists
    
    def is_account_banned(self, username:str):
        # Datatype checks
        if not type(username) == str:
            raise TypeError
            
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           return self.accountDoesNotExist
        
        self.log(f"[Accounts] Reading account: {username}")
        
        result, data = self.db.load_item("usersv0", username)
        if not result:
            return self.accountIOError
        
        if data["banned"]:
            return self.accountBanned
        else:
            return self.accountNotBanned
    
    def update_setting(self, username:str, newdata:dict, forceUpdate:bool = False):
        # Datatype checks
        if (not type(username) == str) or (not type(newdata) == dict) or (not type(forceUpdate) == bool):
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           self.log(f"[Accounts] Not updating account data {username}: Account does not exist")
           return self.accountDoesNotExist
        
        # Prevent modifications to account if banned
        if self.is_account_banned(username) == self.accountBanned:
            self.log(f"[Accounts] Not updating account data {username}: Account banned")
            return self.accountBanned
        
        # Load the account data
        result, account_data = self.db.load_item("usersv0", username)
        
        if not result:
            return self.accountIOError
        
        for key, value in newdata.items():
            if key in self.all_user_keys:
                if forceUpdate:
                    account_data[key] = value
                else:
                    if key in self.protected_keys:
                        self.log(f"[Accounts] Blocking attempt to modify secure key {key}")
                    else:
                        # Prepare for stupidity
                        
                        typeCheck = type(key) == str
                        typeCheck = typeCheck and type(value) in [str, int, float, bool, dict]
                        typeCheck = typeCheck and not(self.parent.supporter.checkForBadCharsPost(str(value)))
                        typeCheck = typeCheck and not len(str(value)) > 360
                        
                        if not typeCheck:
                            self.log(f"Key {key} failed type Check")
                            break
                        
                        if type(value) == str:
                            account_data[key] = self.parent.supporter.wordfilter(value)
                        else:
                            account_data[key] = value
            else:
                self.log(f"Not writing Key: {key} is unknown")
        
        result = self.db.write_item("usersv0", username, account_data)
        if not result:  
            return self.accountIOError
        else:
            return self.accountUpdated
    
    def get_account(self, username:str, omitSensitive:bool = False, isClient:bool = False):
        # Datatype checks
        if (not type(username) == str) or (not type(omitSensitive) == bool) or (not type(isClient) == bool):
            raise TypeError
        
        # Check if the account exists
        if self.account_exists(username, True) == self.accountDoesNotExist:
           self.log(f"[Accounts] Not getting account data {username}: Account does not exist")
           return self.accountDoesNotExist
        
        # Read the user from the database
        result, account_data = self.db.load_item("usersv0", str(username))
        if not result:
            return self.accountIOError
       
        del account_data["_id"]
        del account_data["lower_username"]
        
        # Remove sensitive data
        if omitSensitive:
            for sensitive in [
                "_id",
                "lower_username",
                "unread_inbox",
                "theme",
                "mode",
                "sfx",
                "debug",
                "bgm",
                "bgm_song",
                "layout",
                "email",
                "pswd",
                "tokens",
                "last_ip",
            ]:
                if sensitive in account_data:
                    del account_data[sensitive]
        if isClient:
            if "pswd" in account_data:
                del account_data["pswd"]
            if "email" in account_data:
                del account_data["email"]
            if "tokens" in account_data:
                del account_data["tokens"]
            if "last_ip" in account_data:
                del account_data["last_ip"]
        
        return account_data