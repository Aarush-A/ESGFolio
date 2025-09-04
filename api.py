from flask import request, jsonify
from flask_restful import Resource
import sqlite3

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
    def get(self, username):
        conn = connect()
        cursor = conn.cursor()
        
        # Get average scores across all users
        avg = cursor.execute('''SELECT 
                                ROUND(AVG(s.E_score), 2),
                                ROUND(AVG(s.S_score), 2),
                                ROUND(AVG(s.G_score), 2),
                                ROUND(AVG(s.E_score + s.S_score + s.G_score), 2)
                               FROM portfolio p 
                               INNER JOIN Scores s ON p.company_name = s.Company''').fetchone()
        
        # Get personal portfolio scores
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
        
        # Get max scores for normalization
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
        
        # Get portfolio distribution data
        portfolio_dist = cursor.execute('''
            SELECT 
                s.Company,
                s.E_score,
                s.S_score,
                s.G_score,
                (s.E_score + s.S_score + s.G_score) as total_score
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company 
            WHERE p.username = ?
            ORDER BY total_score DESC
        ''', (username,)).fetchall()
        
        # Get score distribution across all companies
        score_distribution = cursor.execute('''
            SELECT 
                CASE 
                    WHEN (E_score + S_score + G_score) <= 2 THEN 'Poor (0-2)'
                    WHEN (E_score + S_score + G_score) <= 4 THEN 'Fair (2-4)'
                    WHEN (E_score + S_score + G_score) <= 6 THEN 'Good (4-6)'
                    WHEN (E_score + S_score + G_score) <= 8 THEN 'Very Good (6-8)'
                    ELSE 'Excellent (8+)'
                END as score_range,
                COUNT(*) as count
            FROM Scores
            GROUP BY score_range
            ORDER BY 
                CASE 
                    WHEN score_range = 'Poor (0-2)' THEN 1
                    WHEN score_range = 'Fair (2-4)' THEN 2
                    WHEN score_range = 'Good (4-6)' THEN 3
                    WHEN score_range = 'Very Good (6-8)' THEN 4
                    ELSE 5
                END
        ''').fetchall()
        
        conn.close()
        
        # Prepare chart data
        labels = ['Environmental', 'Social', 'Governance']
        
        # Normalize scores to 10-point scale
        avg_scores = [round((avg[0] * 10 / maxtot[1]) if maxtot[1] > 0 else 0, 2),
                     round((avg[1] * 10 / maxtot[2]) if maxtot[2] > 0 else 0, 2),
                     round((avg[2] * 10 / maxtot[3]) if maxtot[3] > 0 else 0, 2)]
        
        personal_scores = [round((totalscore[0] * 10 / maxtot[1]) if maxtot[1] > 0 else 0, 2),
                          round((totalscore[1] * 10 / maxtot[2]) if maxtot[2] > 0 else 0, 2),
                          round((totalscore[2] * 10 / maxtot[3]) if maxtot[3] > 0 else 0, 2)]
        
        # Prepare portfolio distribution data
        portfolio_companies = [row[0] for row in portfolio_dist]
        portfolio_e_scores = [round((row[1] * 10 / maxtot[1]) if maxtot[1] > 0 else 0, 2) for row in portfolio_dist]
        portfolio_s_scores = [round((row[2] * 10 / maxtot[2]) if maxtot[2] > 0 else 0, 2) for row in portfolio_dist]
        portfolio_g_scores = [round((row[3] * 10 / maxtot[3]) if maxtot[3] > 0 else 0, 2) for row in portfolio_dist]
        
        # Prepare score distribution data
        score_ranges = [row[0] for row in score_distribution]
        score_counts = [row[1] for row in score_distribution]
        
        chart_data = {
            'comparison_chart': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'App Users Average',
                        'data': avg_scores,
                        'backgroundColor': 'rgba(54, 162, 235, 0.7)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 2
                    },
                    {
                        'label': 'Your Portfolio',
                        'data': personal_scores,
                        'backgroundColor': 'rgba(255, 99, 132, 0.7)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'borderWidth': 2
                    }
                ]
            },
            'radar_chart': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'App Users Average',
                        'data': avg_scores + [avg_scores[0]],  # Close the radar chart
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 2,
                        'pointBackgroundColor': 'rgba(54, 162, 235, 1)',
                        'pointBorderColor': '#fff',
                        'pointHoverBackgroundColor': '#fff',
                        'pointHoverBorderColor': 'rgba(54, 162, 235, 1)'
                    },
                    {
                        'label': 'Your Portfolio',
                        'data': personal_scores + [personal_scores[0]],  # Close the radar chart
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'borderWidth': 2,
                        'pointBackgroundColor': 'rgba(255, 99, 132, 1)',
                        'pointBorderColor': '#fff',
                        'pointHoverBackgroundColor': '#fff',
                        'pointHoverBorderColor': 'rgba(255, 99, 132, 1)'
                    }
                ]
            },
            'portfolio_distribution': {
                'labels': portfolio_companies,
                'datasets': [
                    {
                        'label': 'Environmental',
                        'data': portfolio_e_scores,
                        'backgroundColor': 'rgba(34, 197, 94, 0.7)',
                        'borderColor': 'rgba(34, 197, 94, 1)',
                        'borderWidth': 1
                    },
                    {
                        'label': 'Social',
                        'data': portfolio_s_scores,
                        'backgroundColor': 'rgba(59, 130, 246, 0.7)',
                        'borderColor': 'rgba(59, 130, 246, 1)',
                        'borderWidth': 1
                    },
                    {
                        'label': 'Governance',
                        'data': portfolio_g_scores,
                        'backgroundColor': 'rgba(168, 85, 247, 0.7)',
                        'borderColor': 'rgba(168, 85, 247, 1)',
                        'borderWidth': 1
                    }
                ]
            },
            'score_distribution': {
                'labels': score_ranges,
                'datasets': [
                    {
                        'label': 'Number of Companies',
                        'data': score_counts,
                        'backgroundColor': [
                            'rgba(239, 68, 68, 0.7)',   # Poor - Red
                            'rgba(245, 158, 11, 0.7)',  # Fair - Orange
                            'rgba(59, 130, 246, 0.7)',  # Good - Blue
                            'rgba(34, 197, 94, 0.7)',   # Very Good - Green
                            'rgba(16, 185, 129, 0.7)'   # Excellent - Emerald
                        ],
                        'borderColor': [
                            'rgba(239, 68, 68, 1)',
                            'rgba(245, 158, 11, 1)',
                            'rgba(59, 130, 246, 1)',
                            'rgba(34, 197, 94, 1)',
                            'rgba(16, 185, 129, 1)'
                        ],
                        'borderWidth': 2
                    }
                ]
            }
        }
        
        return jsonify(chart_data)
