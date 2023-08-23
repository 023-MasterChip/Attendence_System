from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os

import cv2
import csv
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib

from datetime import date
from datetime import datetime

app = Flask(__name__)

app.secret_key="thekey"

datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")

face_detector = cv2.CascadeClassifier('static/haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

if not os.path.isdir('Attendance'):
    os.makedirs('Attendance')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
# if f'Attendance-{datetoday}.csv' not in os.listdir('Attendance'):
#     with open(f'Attendance/Attendance-{datetoday}.csv','w') as f:
#         f.write('Name,Roll,Time')

DB_NAME = 'attendence.db'
if not os.path.exists(DB_NAME):
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute('''CREATE TABLE accounts (name TEXT, email TEXT, password TEXT)''')
    c.execute('''CREATE TABLE grades (classId TEXT, className TEXT)''')
    conn.commit()
    conn.close()


def train_model():
    faces = []
    labels = []
    userlist = os.listdir('static/faces')
    for user in userlist:
        for imgname in os.listdir(f'static/faces/{user}'):
            img = cv2.imread(f'static/faces/{user}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces,labels)
    joblib.dump(knn,'static/face_recognition_model.pkl')
    return

# def extract_faces(img):
#     try:
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         face_points = face_detector.detectMultiScale(gray, 1.3, 5)
#         return face_points.tolist()
#     except Exception as e:
#         print(f"Error in extract_faces: {str(e)}")
#         return []

def extract_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_points = face_detector.detectMultiScale(gray, 1.3, 5)
    return face_points

def fetch_students(classid):
    idclass = classid
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("SELECT id, std_name FROM students WHERE class = ?",(idclass,))
    rowstds=c.fetchall()
    return rowstds

def get_grade():
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("SELECT classId, className FROM grades WHERE name = ?",(session['name'],))
    rowdata=c.fetchall()
    return rowdata

def extract_attendance(sel_class, sel_date):

    grade = sel_class
    date = sel_date

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, std_name FROM students WHERE class = ?",(sel_class,))
    student_data = c.fetchall()
    conn.close()
    print(student_data)
    student_ids = [row[0] for row in student_data]
    student_names = [row[1] for row in student_data]


    csv_file = f'Attendance/Attendance-{date}-{grade}.csv'

    # if csv_file not in os.listdir('Attendance'):
    #     return render_template("mess.html", mess="No Attendence in the selected date")
   
    attendance = []
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            name = row['Name']
            if name in student_names:
                status = "Present"
                time = row['Time']
                roll = row['Roll']
            else:
                status = "Absent"
                time = "---"
                # Assign absent students a roll number based on their IDs
                student_id = student_ids[student_names.index(name)]
                roll = str(student_id).zfill(3)
            attendance.append({'Name': name, 'Roll': roll, 'Time': time, 'Status': status})

    # Append students not in CSV as absent
    for i in range(len(student_names)):
        name = student_names[i]
        if name not in [row['Name'] for row in attendance]:
            student_id = student_ids[i]
            roll = str(student_id).zfill(3)
            attendance.append({'Name': name, 'Roll': roll, 'Time': '---', 'Status': 'Absent'})

    # Render the attendance in an HTML table
    return attendance


def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)

def add_attendance(names, selclass):
    students = names
    print(students)
    classname = selclass
    current_time = datetime.now().strftime("%H:%M:%S")

    if f'Attendance-{datetoday}-{classname}.csv' not in os.listdir('Attendance'):
        with open(f'Attendance/Attendance-{datetoday}-{classname}.csv','w') as f:
            f.write('Name,Roll,Time')

    for student in students:
        username = student.split('_')[0]
        userid = student.split('_')[1]

        df = pd.read_csv(f'Attendance/Attendance-{datetoday}-{classname}.csv')
        if int(userid) not in list(df['Roll']):
            with open(f'Attendance/Attendance-{datetoday}-{classname}.csv','a') as f:
                f.write(f'\n{username},{userid},{current_time}')

    path = f'Attendance/Attendance-{datetoday}-{classname}.csv'

    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("INSERT INTO attendance VALUES (?,?,?)",(datetoday,classname,path,))
    conn.commit()
    conn.close()
    return
    

def get_db():
    conn = sqlite3.connect('attendence.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email=request.form['email']
        password=request.form['password']
        
        # if email=='admin@admin' and password=='admin':
        #     session['admin']=True
        #     return render_template('admin/index.html',admin=True)
        
        conn=sqlite3.connect(DB_NAME)
        c=conn.cursor()
        c.execute("select * from accounts where email=? and password=?",(email,password))
        account=c.fetchone()
        conn.close()
        
        if account is not None and email == account[1] and password == account[2]:
            # session['email']=account[2]
            session['name']=account[0]
            print(f"session username={session['name']}")
            rows = get_grade()
            return render_template('home.html',name=session['name'], rows=rows)
            # return redirect(url_for('home'))
        else:
            print("Couldn't find email or password")
            return redirect('/')
    return render_template("index.html")
# def login():

@app.route("/addgrade", methods=['GET', 'POST'])
def addgrade():
    if request.method == 'POST':
        classId=request.form['classid']
        className=request.form['classname']
        
        conn=sqlite3.connect(DB_NAME)
        c=conn.cursor()
        c.execute("INSERT INTO grades VALUES (?,?,?)",(classId,className,session['name']))
        conn.commit()
        conn.close()
    return redirect("/grade")

@app.route("/delgrade", methods=['POST'])
def delgrade():
    idClass=request.form['idclass']
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("DELETE FROM grades WHERE classid = ?",(idClass,))
    conn.commit()
    conn.close()

    return redirect("/grade")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username=request.form['name']
        email=request.form['email']
        password=request.form['password']
        
        conn=sqlite3.connect(DB_NAME)
        c=conn.cursor()
        c.execute("INSERT INTO accounts VALUES (?,?,?)",(username,email,password))
        conn.commit()
        conn.close()
    return render_template("register.html")

@app.route("/mark", methods=['GET', 'POST'])
def mark():
    students = []
    sel_class = request.form['sel_class']

    # newl = ['Noble_312', 'Juice_486']

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, std_name FROM students WHERE class = ?", (sel_class,))
    class_students = [f"{row[1]}_{row[0]}" for row in c.fetchall()]
    conn.close()

    print(class_students)

    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template("home.html", name=session['name'], rows=get_grade()) 
    cap = cv2.VideoCapture(0)
    ret = True
    while ret:
        ret,frame = cap.read()
        # face_points = extract_faces(frame)  # Store the result of extract_faces
        
        # if len(face_points) > 0:  # Check if any faces were detected
        if extract_faces(frame)!=():
            (x, y, w, h) = extract_faces(frame)[0]  # Use the first face detected
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 20), 2)
            face = cv2.resize(frame[y:y + h, x:x + w], (50, 50))
            identified_person = identify_face(face.reshape(1, -1))[0]

            if identified_person in class_students:
                students.append(identified_person)
            
        cv2.imshow('Attendance',frame)
        if cv2.waitKey(1)==27:
            break
    cap.release()
    cv2.destroyAllWindows()
    print(students)
    add_attendance(students, sel_class)
    attendance = extract_attendance(sel_class, datetoday)
    print('attendence in mark :', attendance)
    return render_template("attendence.html", date=datetoday2, grades=get_grade(), attendances=attendance)

@app.route("/addstd", methods=['GET', 'POST'])
def addstd():
    stdid = request.form['stdid']
    stdname = request.form['stdname'] 
    stdimgfolder = 'static/faces/'+stdname+'_'+str(stdid)
    classid = request.form['idclass']
    classname = request.form['nameclass']
    if not os.path.isdir(stdimgfolder):
        os.makedirs(stdimgfolder)
    cap = cv2.VideoCapture(0)
    i,j = 0,0
    while 1:
        _,frame = cap.read()
        faces = extract_faces(frame)
        for (x,y,w,h) in faces:
            cv2.rectangle(frame,(x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame,f'Images Captured: {i}/50',(30,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255, 0, 20),2,cv2.LINE_AA)
            if j%10==0:
                name = stdname+'_'+str(i)+'.jpg'
                cv2.imwrite(stdimgfolder+'/'+name,frame[y:y+h,x:x+w])
                i+=1
            j+=1
        if j==500:
            break
        cv2.imshow('Adding new User',frame)
        if cv2.waitKey(1)==27:
            break
    cap.release()
    cv2.destroyAllWindows()

    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("INSERT INTO students VALUES (?,?,?,?)",(stdid,stdname,stdimgfolder,classid,))
    conn.commit()
    conn.close()
    
    # stdrows = fetch_students(classid)

    print('Training Model')
    train_model()
    # names,rolls,times,l = extract_attendance()    
    return redirect(url_for('manage', id=classid, name=classname))

@app.route("/delstd", methods=['GET', 'POST'])
def delstd():
    stdid = request.form['stdid']
    classcode = request.form['idclass']
    classname = request.form['nameclass']
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?",(stdid,))
    conn.commit()
    conn.close()

    stdrows = fetch_students(classcode)

    return render_template("manage.html", id=classcode, name=classname, students=stdrows)

@app.route("/home", methods=['GET', 'POST'])
def home():
    return render_template("home.html", name=session['name'], rows=get_grade(), attendances=[])

@app.route("/attend", methods=['GET', 'POST'])
def attend():
    grades = get_grade()
    # attendance = request.args.getlist('attendances')
    
    # if attendance:
    #     print('attendence in attend : ', attendance)
    #     return render_template("attendence.html", date=datetoday2, grades=grades, attendances=attendance)
    # else:
    return render_template("attendence.html", date=datetoday2, grades=grades, attendances=[])
    
@app.route("/view", methods=['GET', 'POST'])
def view():
    sel_class = request.form['selclass']
    day = request.form['date']

    date_obj = datetime.strptime(day, '%Y-%m-%d')
    converted_date = datetime.strftime(date_obj, '%m_%d_%y')

    # print("sel class : ", sel_class)
    # print("day : ", converted_date)
    attendance=extract_attendance(sel_class,converted_date)
    return render_template("home.html", name=session['name'], rows=get_grade(), attendances=attendance)

@app.route("/manage", methods=['GET', 'POST'])
def manage():
    
    if request.method == 'POST':
        classcode = request.form['idclass']
        classname = request.form['nameclass']
        stdrows = fetch_students(classcode)
        # print(classcode)
        # print(classname)
        return render_template("manage.html", id=classcode, name=classname, students=stdrows)
        
    class_id = request.args.get('id')
    class_name = request.args.get('name')
    stdrows = fetch_students(class_id)
    return render_template("manage.html", id=class_id, name=class_name, students=stdrows)


@app.route("/grade", methods=['GET', 'POST'])
def grade():
    rows = get_grade()
    return render_template("grade.html", rows=rows)

@app.route("/mess")
def mess():
    return render_template("mess.html")

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/')

@app.route("/back", methods=['GET', 'POST'])
def back():
    link_id = request.args.get('id')

    print(link_id)

    if link_id == "tohome":
        return redirect(url_for('home'))
    elif link_id == "tograde":
        return redirect(url_for('grade'))
    
    return redirect('/home')


if __name__ == '__main__':
    app.run(debug=True)