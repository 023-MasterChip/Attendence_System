from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

app.secret_key="thekey"

DB_NAME = 'attendence.db'
if not os.path.exists(DB_NAME):
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute('''CREATE TABLE accounts (name TEXT, email TEXT, password TEXT)''')
    conn.commit()
    conn.close()

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
            return render_template('home.html',name=session['name'])
            # return redirect(url_for('home'))
        else:
            print("Couldn't find email or password")
            return redirect('/')
    return render_template("index.html")
# def login():


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

@app.route("/home", methods=['GET', 'POST'])
def home():
    return render_template("home.html", name=session['name'])

@app.route("/attendence", methods=['GET', 'POST'])
def attend():
    return render_template("attendence.html")

@app.route("/grade", methods=['GET', 'POST'])
def grade():
    return render_template("grade.html")

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/')

@app.route("/back", methods=['GET', 'POST'])
def back():
    return redirect('/home')

if __name__ == '__main__':
    app.run(debug=True)