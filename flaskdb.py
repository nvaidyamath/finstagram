from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
#IMAGES_DIR = '/Users/nikhilvaidyamath/Desktop/projectdbpract/images' (For testing purposes)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host='localhost',
                             port=8889,
                             user='root',
                             password='root',
                             db='instagram',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/upload", methods=["GET"])
@login_required
def upload():

    return render_template("upload.html")

@app.route("/images", methods=["GET"])
@login_required
def images():
    profile = session["username"]
    cursor = connection.cursor()
    #queries for profile's followers
    myFollowersQuery = "CREATE VIEW myFollowers AS SELECT DISTINCT photoID, postingdate, filepath, allFollowers, caption, photoPoster FROM photo JOIN follow ON (photo.photoPoster=username_followed) WHERE username_follower=%s AND allFollowers=1"
    cursor.execute(myFollowersQuery, (profile))
    cursor.close()
    #queries for profile's close friend groups
    cursor = connection.cursor()
    myCloseGroupsQuery = "CREATE VIEW myCloseGroups AS SELECT DISTINCT photoID, postingdate, filepath, allFollowers, caption, photoPoster FROM photo NATURAL JOIN sharedwith NATURAL JOIN belongto WHERE member_username=%s"
    cursor.execute(myCloseGroupsQuery, (profile))
    cursor.close()
     #sorts the Query in descending order
    cursor = connection.cursor()
    totalQuery = "SELECT * FROM myCloseGroups UNION (SELECT * FROM myFollowers) ORDER BY postingdate DESC"
    cursor.execute(totalQuery)
    data = cursor.fetchall()
    cursor.close()

    cursor = connection.cursor()
    #drop view  query
    query = "DROP VIEW myCloseGroups, myFollowers"
    cursor.execute(query)
    cursor.close()
    return render_template("images.html",images=data)

@app.route("/photoInfo/<int:photoID>", methods=["GET"])
def photoInfo(photoID):
    profile = session["username"]

    #query to get the picture details
    cursor = connection.cursor()
    query = "SELECT * FROM PHOTO WHERE photoID="+str(photoID)
    cursor.execute(query)
    picture=cursor.fetchall()
    cursor.close()


    #query to get the posters name
    cursor = connection.cursor()
    query = "SELECT photoPoster FROM PHOTO WHERE photoID="+str(photoID)
    cursor.execute(query)
    name=cursor.fetchall()[0]["photoPoster"]
    cursor.close()


    #query to get the first and last name
    cursor = connection.cursor()
    query = "SELECT fname, lname FROM Person WHERE username="+"'"+(name)+"'"
    cursor.execute(query)
    names=cursor.fetchall()[0]
    cursor.close()

    #query to get all tagged
    cursor = connection.cursor()
    query = "SELECT fname, lname FROM Person NATURAL JOIN Tagged NATURAL JOIN Photo WHERE photoID="+str(photoID)+" AND tagstatus=1"
    cursor.execute(query)
    names_tagged=cursor.fetchall()
    cursor.close()

    #query to get all likes for this photo
    cursor = connection.cursor()
    query = "SELECT fname, lname, rating FROM Person NATURAL JOIN Likes NATURAL JOIN Photo WHERE photoID="+str(photoID)
    cursor.execute(query)
    likes=cursor.fetchall()
    cursor.close()

    return render_template("photoInfo.html", photoID=photoID, photo=picture, name=names, tagged=names_tagged, likes=likes)

@app.route("/follow", methods=["GET"])
def follow():
    to_follow = request.args.get("username")
    follower = session["username"]
    sent=False
    if to_follow != None:
        #query to insert pending follow request
        cursor = connection.cursor()
        query = "INSERT INTO `Follow` (`username_followed`, `username_follower`, `followstatus`) VALUES ('"+str(to_follow)+"', '"+str(follower)+"', '0');"
        cursor.execute(query)
        cursor.close()
        sent=True

    return render_template("follow.html", request_sent=sent)

@app.route("/followRequests", methods=["GET"])
def followers():
    user = session["username"]

    #query to get list of follower requests
    cursor = connection.cursor()
    query = "SELECT username_follower FROM Follow WHERE username_followed='"+str(user)+"' AND followstatus=0"
    cursor.execute(query)
    followers=cursor.fetchall()
    cursor.close()

    return render_template("followRequests.html", followers=followers)

def accept_follow():
    user = session["username"]
    #query to update the follow status to true
    cursor = connection.cursor()
    query = "UPDATE `Follow` SET `followstatus` = '1' WHERE `Follow`.`username_followed` = 'bobby' AND `Follow`.`username_follower` = 'colieen';"
    cursor.execute(query)
    cursor.close()


def decline_follow():
    pass
@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        hashedPassword = plaintextPasword
        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files:
        requestData = request.form
        caption = requestData["caption"]
        allFollowers = 1
        if "allfollowers" not in requestData:
            allFollowers = 0
        username = session["username"]
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        query = "INSERT INTO photo (postingdate, filePath, allFollowers, caption, photoPoster) VALUES (%s, %s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, str(allFollowers),caption, username))
        message = "Image has been successfully uploaded."
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)

app.secret_key = "super secret key"
if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run('127.0.0.1', 5000, debug = True)
