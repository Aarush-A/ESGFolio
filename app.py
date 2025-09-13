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
        
        # Hardcoded weights for E, S, G scores
        E_WEIGHT = 0.6714  # Environmental weight
        S_WEIGHT = 0.2571  # Social weight  
        G_WEIGHT = 0.0714  # Governance weight
        
        # Get min and max values for scaling
        minmax_values = conn.execute('''
            SELECT 
                MIN(E_score) as min_e, MAX(E_score) as max_e,
                MIN(S_score) as min_s, MAX(S_score) as max_s,
                MIN(G_score) as min_g, MAX(G_score) as max_g
            FROM Scores
        ''').fetchone()
        
        # Min-max scaling function: (value - min) / (max - min) * 10
        def minmax_scale(value, min_val, max_val):
            if max_val == min_val:
                return 5.0  # Return middle value if no range
            return round(((value - min_val) / (max_val - min_val)) * 10, 2)
        
        # Get raw company data
        raw_companies = conn.execute('''
            SELECT s.Company,
                s.E_score,
                s.S_score,
                s.G_score,
                CASE 
                    WHEN p.username IS NOT NULL THEN 'Yes'
                    ELSE 'No'
                END AS status
            FROM scores s
            LEFT JOIN portfolio p ON s.Company = p.company_name AND p.username = ?
            WHERE s.Company LIKE ?
        ''', (session['username'],'%' + query + '%',)).fetchall()
        
        # Process companies with scaling and weighted ESG calculation
        companies = []
        for row in raw_companies:
            scaled_e = minmax_scale(row[1], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[2], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[3], minmax_values[4], minmax_values[5])
            
            # Calculate weighted ESG score and scale to 5
            esg_score = round((scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5, 2)
            
            companies.append((row[0], row[1], row[2], row[3], esg_score, row[4]))
        
        # Sort by ESG score descending
        companies.sort(key=lambda x: x[4], reverse=True)
        
        conn.close()
        return render_template('search.html', companies=companies)
    return render_template('Dashboard.html')

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    portfolio_res = rq.get(request.url_root + 'api/portfolio/' + username)
    if portfolio_res.status_code == 200:
        portfolio = portfolio_res.json()
    else:
        portfolio = []

    # Hardcoded weights for E, S, G scores
    E_WEIGHT = 0.6714  # Environmental weight
    S_WEIGHT = 0.2571  # Social weight  
    G_WEIGHT = 0.0714  # Governance weight

    conn = get_db_connection()
    
    # Get min and max values for scaling
    minmax_values = conn.execute('''
        SELECT 
            MIN(E_score) as min_e, MAX(E_score) as max_e,
            MIN(S_score) as min_s, MAX(S_score) as max_s,
            MIN(G_score) as min_g, MAX(G_score) as max_g
        FROM Scores
    ''').fetchone()
    
    # Min-max scaling function: (value - min) / (max - min) * 10
    def minmax_scale(value, min_val, max_val):
        if max_val == min_val:
            return 5.0  # Return middle value if no range
        return round(((value - min_val) / (max_val - min_val)) * 10, 2)
    
    # Get personal portfolio raw scores
    personal_scores_raw = conn.execute('''
        SELECT s.E_score, s.S_score, s.G_score
        FROM portfolio p 
        INNER JOIN Scores s ON p.company_name = s.Company 
        WHERE username=?
    ''', (username,)).fetchall()
    
    # Calculate scaled and weighted scores for personal portfolio
    personal_scaled_scores = []
    for row in personal_scores_raw:
        scaled_e = minmax_scale(row[0], minmax_values[0], minmax_values[1])
        scaled_s = minmax_scale(row[1], minmax_values[2], minmax_values[3])
        scaled_g = minmax_scale(row[2], minmax_values[4], minmax_values[5])
        esg_score = (scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5
        personal_scaled_scores.append((scaled_e, scaled_s, scaled_g, esg_score))
    
    # Calculate personal averages
    if personal_scaled_scores:
        personal_e = sum(score[0] for score in personal_scaled_scores) / len(personal_scaled_scores)
        personal_s = sum(score[1] for score in personal_scaled_scores) / len(personal_scaled_scores)
        personal_g = sum(score[2] for score in personal_scaled_scores) / len(personal_scaled_scores)
        personal_esg = sum(score[3] for score in personal_scaled_scores) / len(personal_scaled_scores)
    else:
        personal_e = personal_s = personal_g = personal_esg = 0
    
    # Create totalscore tuple for compatibility
    totalscore = (personal_e, personal_s, personal_g, personal_esg)

    # Get basic averages with null handling
    avgs = conn.execute('''
        SELECT 
            COALESCE(FLOOR(AVG(e_score)), 0) as avg_e,
            COALESCE(FLOOR(AVG(s_score)), 0) as avg_s,
            COALESCE(FLOOR(AVG(g_score)), 0) as avg_g
        FROM scores
    ''').fetchone()

    emed = conn.execute('SELECT COALESCE(FLOOR(AVG(e_score)), 0) FROM scores WHERE e_score > 0').fetchone()
    smed = conn.execute('SELECT COALESCE(FLOOR(AVG(s_score)), 0) FROM scores WHERE s_score > 0').fetchone()
    gmed = conn.execute('SELECT COALESCE(FLOOR(AVG(g_score)), 0) FROM scores WHERE g_score > 0').fetchone()

    totav = conn.execute('''
        SELECT COALESCE(FLOOR(AVG(rating)), 0)
        FROM (
            SELECT e_score + s_score + g_score AS rating 
            FROM scores 
            WHERE e_score + s_score + g_score < 9
        )
    ''').fetchone()

    totmed = conn.execute('''
        SELECT COALESCE(FLOOR(AVG(rating)), 0)
        FROM (
            SELECT e_score + s_score + g_score AS rating 
            FROM scores
        )
    ''').fetchone()

    max_scores = conn.execute('''
        SELECT 
            COALESCE(MAX(e_score), 0),
            COALESCE(MAX(s_score), 0),
            COALESCE(MAX(g_score), 0),
            COALESCE(MAX(e_score + s_score + g_score), 0)
        FROM scores
    ''').fetchone()

    avgtot=conn.execute('''
        SELECT 
                COALESCE(FLOOR(AVG(tsc)), 0) AS avg_tsc,
                COALESCE(FLOOR(AVG(esc)), 0) AS avg_esc,
                COALESCE(FLOOR(AVG(ssc)), 0) AS avg_ssc,
                COALESCE(FLOOR(AVG(gsc)), 0) AS avg_gsc
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
                COALESCE(MAX(tsc), 0) AS max_tsc,
                COALESCE(MAX(esc), 0) AS max_esc,
                COALESCE(MAX(ssc), 0) AS max_ssc,
                COALESCE(MAX(gsc), 0) AS max_gsc
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
