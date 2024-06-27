from flask import request, jsonify
from flask_restful import Resource
import sqlite3
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os

matplotlib.use('Agg')  # Set the backend before importing pyplot

def connect():
    conn = sqlite3.connect('esgdb.db')
    return conn

class user_api(Resource):
    def get(self):
        data = request.get_json()
        user = data.get('username')
        passw = data.get('password')
        
        conn = connect()
        cursor = conn.cursor()
        
        fetch = cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (user, passw)).fetchone()
        conn.close()
        
        if fetch:
            return {'message': 'Login Successful'}, 200
        else:
            return {'message': 'Invalid Credentials'}, 401

    def post(self):
        data = request.get_json()
        user = data.get('username')
        passw = data.get('password')
        name = data.get('name')
        email = data.get('email')
        
        conn = connect()
        cursor = conn.cursor()
        
        fetch = cursor.execute('SELECT * FROM users WHERE username=? or email=?', (user, email)).fetchall()
        
        if fetch:
            conn.close()
            return {'message': 'Username or email already registered'}, 400
        else:
            cursor.execute('INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)', (user, name, email, passw))
            conn.commit()
            conn.close()
            return {'message': 'Registration successful'}, 200

class portfolio_api(Resource):
    def get(self, username):
        conn = connect()
        cursor = conn.cursor()
        fetch = cursor.execute('''SELECT 
                                    username,
                                    company_name,
                                    s.E_score AS escore,
                                    s.S_score AS sscore,
                                    s.G_score AS gscore,
                                    (s.E_score + s.S_score + s.G_score) AS company_score
                                  FROM portfolio p 
                                  INNER JOIN Scores s ON p.company_name = s.Company 
                                  WHERE username=?''', (username,)).fetchall()
        conn.close()
        return jsonify(fetch)
    
    def delete(self, username, company_name):
        conn = connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM portfolio WHERE username=? AND company_name=?', (username, company_name))
        conn.commit()
        conn.close()
        return '', 204
    
    def post(self, username, company_name):
        conn = connect()
        cursor = conn.cursor()
        fetch = cursor.execute('SELECT * FROM portfolio WHERE username=? AND company_name=?', (username, company_name)).fetchall()
        if len(fetch) == 0:
            cursor.execute('INSERT INTO portfolio (username, company_name) VALUES (?, ?)', (username, company_name))
            conn.commit()
            conn.close()
            return '', 201
        else:
            conn.close()
            return '', 409

class graphs_api(Resource):
    def post(self, username):
        conn = connect()
        cursor = conn.cursor()
        
        avg = cursor.execute('''SELECT 
                                ROUND(AVG(s.E_score), 2),
                                ROUND(AVG(s.S_score), 2),
                                ROUND(AVG(s.G_score), 2),
                                ROUND(AVG(s.E_score + s.S_score + s.G_score), 2)
                               FROM portfolio p 
                               INNER JOIN Scores s ON p.company_name = s.Company''').fetchone()
        
        personal = cursor.execute('''SELECT 
                                     ROUND(SUM(s.E_score) / COUNT(*), 2) AS e_score,
                                     ROUND(SUM(s.S_score) / COUNT(*), 2) AS s_score,
                                     ROUND(SUM(s.G_score) / COUNT(*), 2) AS g_score,
                                     ROUND((SUM(s.E_score) + SUM(s.S_score) + SUM(s.G_score)) / COUNT(*), 2) AS portfolio_score
                                    FROM portfolio p 
                                    INNER JOIN Scores s ON p.company_name = s.Company 
                                    WHERE username=?''', (username,)).fetchone()
        
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
        
        labels = ['Environmental', 'Social', 'Governance']
        avg_scores = [(avg[0] * 10 / maxtot[1]), (avg[1] * 10 / maxtot[2]), (avg[2] * 10 / maxtot[3])]
        personal_scores = [(totalscore[0] * 10 / maxtot[1]), (totalscore[1] * 10 / maxtot[2]), (totalscore[2] * 10 / maxtot[3])]
        
        # Bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(labels))
        bar_width = 0.35
        ax.bar(x, avg_scores, width=bar_width, label='App Users Average', alpha=0.7)
        ax.bar([p + bar_width for p in x], personal_scores, width=bar_width, label='Personal Score', alpha=0.7)
        ax.set_xlabel('ESG Dimensions')
        ax.set_ylabel('Scores')
        ax.set_title('Comparison of ESG Scores')
        ax.set_xticks([p + bar_width / 2 for p in x])
        ax.set_xticklabels(labels)
        ax.legend()
        plt.tight_layout()
        
        comparison_filename = "comparison.png"
        plt.savefig(os.path.join('static', comparison_filename))
        plt.close(fig)  
        
        # Radar chart
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  
        
        avg_scores += avg_scores[:1]
        personal_scores += personal_scores[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        ax.fill(angles, avg_scores, color='blue', alpha=0.25)
        ax.fill(angles, personal_scores, color='red', alpha=0.25)
        ax.plot(angles, avg_scores, color='blue', linewidth=2, label='App Users Average')
        ax.plot(angles, personal_scores, color='red', linewidth=2, label='Personal Score')
        ax.set_yticklabels([])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)
        ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        plt.title('Radar Chart for ESG Scores Comparison')
        
        radar_filename = "radar.png"
        plt.savefig(os.path.join('static', radar_filename))
        plt.close(fig)
