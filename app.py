from flask import Flask, render_template, request, redirect, url_for, session
from flask_restful import Api
from api import user_api, portfolio_api, graphs_api
import requests as rq
import sqlite3
import math

app = Flask(__name__)
app.secret_key = 'shazam'

api = Api(app)
api.add_resource(user_api, '/api/user')
api.add_resource(portfolio_api, '/api/portfolio/<string:username>', '/api/portfolio/<string:username>/<string:company_name>')
api.add_resource(graphs_api, '/api/graph/<string:username>')

def get_db_connection():
    conn = sqlite3.connect('esgdb.db')
    conn.row_factory = sqlite3.Row
    conn.create_function("FLOOR", 1, lambda x: math.floor(x) if x is not None else None)
    return conn

@app.route('/')
def index():
    return render_template('Landing_page.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        login = {
            'username': request.form['username'],
            'password': request.form['password'],    
        }
        res = rq.get(request.url_root + 'api/user', json=login)
        if res.status_code == 200:
            session['username'] = login['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', message="Wrong Username Or Password")
    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        register = {
            'username': request.form['username'],
            'name': request.form['name'],
            'email': request.form['email'],
            'password': request.form['password'],
        }
        res = rq.post(request.url_root + 'api/user', json=register)
        if res.status_code == 200:
            return redirect(url_for('login'))
        else:
            return render_template('registration.html', message="Username or email already registered")
    return render_template('registration.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        conn = get_db_connection()
        companies = conn.execute('''
            SELECT s.Company,
                CASE 
                    WHEN p.username IS NOT NULL THEN 'Yes'
                    ELSE 'No'
                END AS status
            FROM scores s
            LEFT JOIN portfolio p ON s.Company = p.company_name AND p.username = ?
            WHERE s.Company LIKE ?
        ''', (session['username'],'%' + query + '%',)).fetchall()
        conn.close()
        return render_template('search.html', companies=companies)
    return render_template('Dashboard.html')

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    rq.post(request.url_root+'api/graph/'+username)
    portfolio_res = rq.get(request.url_root + 'api/portfolio/' + username)
    if portfolio_res.status_code == 200:
        portfolio = portfolio_res.json()
    else:
        portfolio = []

    conn = get_db_connection()
    totalscore = conn.execute('''
        SELECT 
            ROUND(SUM(s.E_score)/count(*),2) AS e_score,
            ROUND(SUM(s.S_score)/count(*),2) AS s_score,
            ROUND(SUM(s.G_score)/count(*),2) AS g_score,
            ROUND((SUM(s.E_score) + SUM(s.S_score) + SUM(s.G_score))/count(*),2) AS portfolio_score
        FROM portfolio p 
        INNER JOIN Scores s ON p.company_name = s.Company 
        WHERE username=?
    ''', (username,)).fetchone()

    avgs = conn.execute('''
        SELECT 
            FLOOR(AVG(e_score)),
            FLOOR(AVG(s_score)),
            FLOOR(AVG(g_score))
        FROM scores
    ''').fetchone()

    emed = conn.execute('SELECT FLOOR(AVG(e_score)) FROM scores WHERE e_score > 0').fetchone()
    smed = conn.execute('SELECT FLOOR(AVG(s_score)) FROM scores WHERE s_score > 0').fetchone()
    gmed = conn.execute('SELECT FLOOR(AVG(g_score)) FROM scores WHERE g_score > 0').fetchone()

    totav = conn.execute('''
        SELECT FLOOR(AVG(rating)) 
        FROM (
            SELECT s_score + g_score + e_score AS rating 
            FROM scores 
            WHERE s_score + g_score + e_score < 9
        )
    ''').fetchone()

    totmed = conn.execute('''
        SELECT FLOOR(AVG(rating)) 
        FROM (
            SELECT s_score + g_score + e_score AS rating 
            FROM scores
        )
    ''').fetchone()

    max_scores = conn.execute('''
        SELECT 
            MAX(e_score),
            MAX(s_score),
            MAX(g_score),
            MAX(e_score + s_score + g_score)
        FROM scores
    ''').fetchone()


    avgtot=conn.execute('''
        SELECT 
                FLOOR(AVG(tsc)) AS avg_tsc,
                FLOOR(AVG(esc)) AS avg_esc,
                FLOOR(AVG(ssc)) AS avg_ssc,
                FLOOR(AVG(gsc)) AS avg_gsc
        FROM (
            SELECT 
                    p.username,
                    AVG(s.e_score) AS esc,
                    AVG(s.s_score) AS ssc,
                    AVG(s.g_score) AS gsc,
                    AVG(s.e_score + s.s_score + s.g_score) AS tsc
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company 
            GROUP BY p.username
        ) as sub                    
    ''').fetchone()

    maxtot=conn.execute('''
        SELECT 
                MAX(tsc) AS max_tsc,
                MAX(esc) AS max_esc,
                MAX(ssc) AS max_ssc,
                MAX(gsc) AS max_gsc
        FROM (
            SELECT 
                    p.username,
                    AVG(s.e_score) AS esc,
                    AVG(s.s_score) AS ssc,
                    AVG(s.g_score) AS gsc,
                    AVG(s.e_score + s.s_score + s.g_score) AS tsc
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company 
            GROUP BY p.username
        ) as sub                    
    ''').fetchone()

    conn.close()

    return render_template('Dashboard.html', portfolio=portfolio, totalscore=totalscore, avgs=avgs, emed=emed, smed=smed, gmed=gmed, max=max_scores, totav=totav, totmed=totmed, avgtot=avgtot, maxtot=maxtot)

@app.route('/dashboard/<string:company_name>/delete', methods=['GET'])
def deletecompany(company_name):
    rq.delete(url=request.url_root + 'api/portfolio/' + session['username'] + '/' + company_name)
    return redirect(url_for('dashboard'))

@app.route('/dashboard/<string:company_name>/add', methods=['POST','GET'])
def addcompany(company_name):
    rq.post(url=request.url_root + 'api/portfolio/' + session['username'] + '/' + company_name)
    return redirect(url_for('dashboard'))

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()  
    return redirect(url_for('login'))  

if __name__ == '__main__':
    app.run(debug=True)
