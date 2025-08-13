from flask import Flask, render_template, request, jsonify, redirect, flash, url_for, session
import requests
import mysql.connector
import bcrypt

app = Flask(__name__)
app.secret_key = 'blablablahello'

API_KEY = '48a7ef59f11ef880f730ae3103b70650'
GEOCODING_URL = 'http://api.openweathermap.org/geo/1.0/direct'
UV_URL = 'http://api.openweathermap.org/data/2.5/uvi'

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="lili",
        password="password",
        database="uvWebpage"
    )

def save_uv_data(city, uv_index):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        query = "INSERT INTO CityUv (City, `UV Index`) VALUES (%s, %s)"
        values = (city, uv_index)
        mycursor.execute(query, values)
        mydb.commit()
        mycursor.close()
        mydb.close()
        print(f"Saved {city}: {uv_index} to database")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")

def get_all_uv_data():
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM CityUv ORDER BY City")
        myresult = mycursor.fetchall()
        mycursor.close()
        mydb.close()
        return myresult
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return []
    
def get_coordinates(city_name):
    try:
        params = {
            'q': city_name,
            'limit': 1,
            'appid': API_KEY
        }
        response = requests.get(GEOCODING_URL, params=params)
        data = response.json()
        if data:
            return data[0]['lat'], data[0]['lon']
        return None, None
    except Exception as e:
        print(f"Error getting coordinates: {e}")
        return None, None
    
def get_uv_index(lat, lon):
    try:
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY
        }
        response = requests.get(UV_URL, params=params)
        data = response.json()
        return data.get('value', 0)
    except Exception as e:
        print(f"Error getting UV index: {e}")
        return 0
    
def get_uv_description(uv_index):
    if uv_index < 3:
        return "Low", "green"
    elif uv_index < 6:
        return "Moderate", "yellow"
    elif uv_index < 8:
        return "High", "orange"
    elif uv_index < 11:
        return "Very High", "red"
    else:
        return "Extreme", "purple"
    
@app.route('/')
def start():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if not 'username' in session:
        flash("You must be logged in to access the site")
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/get_uv', methods=['POST'])
def get_uv():
    city = request.json.get('city', '')
    if not city:
        return jsonify({'error': 'City name is required'}), 400
    lat, lon = get_coordinates(city)
    if lat is None or lon is None:
        return jsonify({'error': 'City not found'}), 404
    uv_index = get_uv_index(lat, lon)
    description, color = get_uv_description(uv_index)
    save_uv_data(city, uv_index)
    return jsonify({
        'city': city,
        'uv_index': uv_index,
        'description': description,
        'color': color,
        'lat': lat,
        'lon': lon
    })

@app.route("/table")
def table():
    headings = ("City", "UV Index")
    data = get_all_uv_data()
    return render_template("table.html", headings=headings, data=data)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        query = "SELECT COUNT(*) FROM UserInfo WHERE username = %s"
        mycursor.execute(query, (username,))
        result = mycursor.fetchone()
        if result[0] > 0:
            flash("Username already in use.")
            return render_template("register.html")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        insert_query = "INSERT INTO UserInfo (username, password) VALUES (%s, %s)"
        mycursor.execute(insert_query, (username, hashed_password))
        mydb.commit()
        flash("Registration successful.")
        return redirect(url_for('login'))
    
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        query = "SELECT password FROM UserInfo WHERE username = %s"
        mycursor.execute(query, (username,))
        result = mycursor.fetchone()
        if result is None:
            flash("Username not found.")
            return render_template("login.html")
        stored_hashed_password = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
            session['username'] = username
            flash("Login successful.")
            return redirect(url_for('home'))
        else:
            flash("Incorrect password.")
            return render_template("login.html")
        
if __name__ == '__main__':
    app.run(debug=True)