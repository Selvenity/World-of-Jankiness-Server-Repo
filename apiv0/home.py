from flask import Blueprint, request, abort
from flask import current_app as meower
import time
from uuid import uuid4
import pymongo
import json

home = Blueprint("home_blueprint", __name__)

@home.route("/", methods=["GET", "POST"])
def get_home():
    if request.method == "GET":
        # Get page
        if not ("pages" in request.args):
            page = 1
        else:
            page = int(request.args.get("pages"))

        # Get index
        query_get = meower.db["posts"].find({"origin": "home", "deleted": False}).skip((page-1)*25).limit(25).sort("created", pymongo.ASCENDING)
        pages_amount = (meower.db["posts"].count_documents({"origin": "home", "deleted": False}) // 25) + 1

        # Convert query get
        payload_posts = []
        for post in query_get:
            userdata = meower.db["usersv0"].find_one({"_id": post["user"]})
            if userdata is None:
                post["user"] = "Deleted"
            else:
                post["user"] = userdata["username"]
            payload_posts.append(post)
        payload_posts.reverse()

        # Create payload
        payload = {
            "posts": list(payload_posts),
            "page#": int(page),
            "pages": int(pages_amount)
        }

        # Return payload
        return meower.respond(payload, 200, error=False)
    elif request.method == "POST":
        if not ("content" in request.form):
            return meower.respond({"type": "missingField"}, 400, error=True)
    
        # Extract content for simplicity
        content = request.form.get("content")

        # Check for bad datatypes and syntax
        if type(content) != str:
            return meower.respond({"type": "badDatatype"}, 400, error=True)
        elif len(content) > 360:
            return meower.respond({"type": "fieldTooLarge"}, 400, error=True)
        elif meower.check_for_bad_chars_post(content):
            return meower.respond({"type": "illegalCharacters"}, 400, error=True)

        # Check if account is suspended or ratelimited
        userdata = meower.db["usersv0"].find_one({"_id": request.session.user})
        if (userdata["security"]["suspended_until"] > int(time.time())) or (userdata["security"]["suspended_until"] == -1):
            return meower.respond({"type": "accountSuspended"}, 403, error=True)
        elif meower.check_for_spam(request.session.user):
            return meower.respond({"type": "ratelimited"}, 429, error=True)

        # Create post
        post_data = {
            "_id": str(uuid4()),
            "origin": "home",
            "user": request.session.user,
            "content": content,
            "created": int(time.time()),
            "deleted": False
        }
        meower.db["posts"].insert_one(post_data)

        # Send notification to all users
        userdata = meower.db["usersv0"].find_one({"_id": request.session.user})
        post_data["user"] = userdata["username"]
        meower.send_payload(json.dumps({"cmd": "new_post", "val": post_data}))

        # Return payload
        return meower.respond(post_data, 200, error=False)