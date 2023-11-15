from flask import Flask, render_template, request, redirect
import mysql.connector
from mysql.connector import *
from werkzeug.utils import secure_filename
import datetime
import hashlib
import base64
import cv2
import face_recognition
from PIL import Image
from pytesseract import pytesseract

app = Flask(__name__, static_url_path="/static")
Message = ""


@app.route('/')
def welcome_page():
    global Message
    msg = Message
    Message = ""
    return render_template("index.html", Message=msg)


@app.route("/register", methods=["POST", "GET"])
def register_page():
    if request.method == "GET":
        data = {"name": "", "aadhaarNum": "", "phnNum": "", "dobError": "",
                "phnError": "", "imgError": ""}
        return render_template("register.html", data=data)
    name = request.form["name"]
    aadhaarNum = ""
    dob = request.form["dob"]
    image = request.files["aadhaarImg"]
    phnNum = request.form["phnNum"]

    filename = "testImage.jpg"
    image.filename = filename
    image.save(r"AadhaarImgs/" + secure_filename(image.filename))

    imgError = ""
    anError = ""
    dobError = ""
    phnError = ""

    try:
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        image_path = r"AadhaarImgs\testImage.jpg"
        img = Image.open(image_path)
        pytesseract.tesseract_cmd = tesseract_path
        text = pytesseract.image_to_string(img)
        text = text.split("\n")
        index = -1
        for i in range(len(text)):
            if "VID" in text[i]:
                index = i - 1
        if index != -1:
            aadhaarNum = text[index].replace(" ", "")
        else:
            imgError = "Cannot detect Aadhaar Number. Please upload again."
            data = {"name": name, "aadhaarNum": aadhaarNum, "phnNum": phnNum, "dobError": dobError,
                    "phnError": phnError, "imgError": imgError}
            return render_template("register.html", data=data)
    except Exception as e:
        print(e)
        imgError = "Cannot detect Aadhaar Number. Please upload again."
        data = {"name": name, "aadhaarNum": aadhaarNum, "phnNum": phnNum, "dobError": dobError,
                "phnError": phnError, "imgError": imgError}
        return render_template("register.html", data=data)

    encryptedAadhaar = hashlib.md5(aadhaarNum.encode()).hexdigest()
    cursor.execute("SELECT * FROM USERS WHERE ENCAADHAAR=%s", (encryptedAadhaar,))
    user = cursor.fetchone()
    register = True

    if user:
        anError = "Aadhaar Number already exists."
        register = False
    elif len(aadhaarNum) != 12:
        anError = "Aadhaar Number must be 12 digts long."
        register = False
    years = datetime.date.today().year - int(dob.split("-")[0])
    if years < 18:
        dobError = "Age must be greater than or equal to 18."
        register = False
    if len(phnNum) != 10:
        phnError = "Invalid Phone Number."
        register = False
    if register:
        cursor.execute("INSERT INTO USERS VALUES(%s, %s, %s, %s)", (encryptedAadhaar, name, dob, phnNum,))
        connection.commit()
        filename = "AadhaarImgs/"+encryptedAadhaar+ ".jpg"
        try:
            f1 = open("AadhaarImgs/testImage.jpg", "rb")
            f2 = open(filename, "wb")
            data = f1.read()
            f2.write(data)
        except Exception as e:
            print(e)
        finally:
            f1.close()
            f2.close()
        global Message
        Message = "Registration Successful. Thanks for registering."
        return redirect("/")
    if anError!= "":
        imgError=anError
    data = {"name": name, "aadhaarNum": aadhaarNum, "phnNum": phnNum, "dobError": dobError,
            "phnError": phnError, "imgError": imgError}
    return render_template("register.html", data=data)


@app.route("/castVote", methods=["GET", "POST"])
def cast_vote():
    if request.method == "GET":
        data = {"aadhaarNum": "", "anError": ""}
        return render_template("castVote.html", data=data)
    aadhaarNum = request.form["aadhaarNum"]
    encryptedAadhaar = hashlib.md5(aadhaarNum.encode()).hexdigest()
    anError = ""
    cursor.execute("SELECT * FROM USERS WHERE ENCAADHAAR=%s", (encryptedAadhaar,))
    user = cursor.fetchone()
    if user:
        return redirect("/verifyFace/" + encryptedAadhaar)
    else:
        anError = "Aadhaar Number not registered. Please register."
    data = {"aadhaarNum": aadhaarNum, "anError": anError}
    return render_template("castVote.html", data=data)


@app.route("/verifyFace/<encAadhaar>", methods=["GET", "POST"])
def verify_face(encAadhaar):
    msg = ""
    if request.method == "GET":
        cursor.execute("SELECT * FROM USERS WHERE ENCAADHAAR=%s", (encAadhaar,))
        user = cursor.fetchone()
        if user:
            return render_template("verifyface.html", encAadhaar=encAadhaar, Message=msg, user=user[1])
        else:
            return redirect("/")
    img_data = request.form["img_data"].split(",")[1]
    img = base64.b64decode(img_data)
    filename = r"AadhaarImgs/temp.jpg"
    with open(filename, "wb") as f:
        f.write(img)

    img1 = cv2.imread(r"AadhaarImgs/temp.jpg")
    img2 = cv2.imread(r"AadhaarImgs/" + encAadhaar + r".jpg")

    rgb_img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
    rgb_img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)

    try:
        encoding1 = face_recognition.face_encodings(rgb_img1)[0];
        encoding2 = face_recognition.face_encodings(rgb_img2)[0]

        result = face_recognition.compare_faces([encoding1], encoding2)

        if result[0]:
            msg = "Verified"
        else:
            msg = "Image Mismatch. Please try again."
    except Exception as e:
        print(e)
        msg = "Face not detected. Please try again."

    return render_template("verifyface.html", encAadhaar=encAadhaar, Message=msg)


if __name__ == '__main__':
    try:
        connection = mysql.connector.connect(host='localhost', database='miniproject', user='root',
                                             password='patelprabhuteja')
        if connection.is_connected():
            print("Connected to Database.")
            cursor = connection.cursor()
        app.run()
    except Error as e:
        print(e);
    finally:
        cursor.close()
        connection.close()
        print("Database connection closed.")
