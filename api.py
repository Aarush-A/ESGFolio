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
        
        # Hardcoded weights for E, S, G scores
        E_WEIGHT = 0.6714  # Environmental weight
        S_WEIGHT = 0.2571  # Social weight  
        G_WEIGHT = 0.0714  # Governance weight
        # Get min and max values for scaling
        minmax_values = cursor.execute('''
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
        
        # Get portfolio data
        raw_data = cursor.execute('''SELECT 
                                    username,
                                    company_name,
                                    s.E_score AS escore,
                                    s.S_score AS sscore,
                                    s.G_score AS gscore
                                  FROM portfolio p 
                                  INNER JOIN Scores s ON p.company_name = s.Company 
                                  WHERE username=?''', (username,)).fetchall()
        
        # Process data with scaling and weighted ESG calculation
        processed_data = []
        for row in raw_data:
            scaled_e = minmax_scale(row[2], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[3], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[4], minmax_values[4], minmax_values[5])
            
            # Calculate weighted ESG score and scale to 5
            esg_score = round((scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5, 2)
            
            processed_data.append((row[0], row[1], row[2], row[3], row[4], esg_score))
        
        fetch = processed_data
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
        
        # Hardcoded weights for E, S, G scores
        E_WEIGHT = 0.6714  # Environmental weight
        S_WEIGHT = 0.2571  # Social weight  
        G_WEIGHT = 0.0714  # Governance weight
        
        # Get min and max values for scaling
        minmax_values = cursor.execute('''
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
        
        # Get raw scores for all portfolios
        all_scores = cursor.execute('''
            SELECT s.E_score, s.S_score, s.G_score
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company
        ''').fetchall()
        
        # Get personal portfolio raw scores
        personal_scores_raw = cursor.execute('''
            SELECT s.E_score, s.S_score, s.G_score
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company 
            WHERE username=?
        ''', (username,)).fetchall()
        
        # Calculate scaled and weighted scores for all portfolios
        all_scaled_scores = []
        for row in all_scores:
            scaled_e = minmax_scale(row[0], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[1], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[2], minmax_values[4], minmax_values[5])
            esg_score = (scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5
            all_scaled_scores.append((scaled_e, scaled_s, scaled_g, esg_score))
        
        # Calculate scaled and weighted scores for personal portfolio
        personal_scaled_scores = []
        for row in personal_scores_raw:
            scaled_e = minmax_scale(row[0], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[1], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[2], minmax_values[4], minmax_values[5])
            esg_score = (scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5
            personal_scaled_scores.append((scaled_e, scaled_s, scaled_g, esg_score))
        
        # Calculate averages
        if all_scaled_scores:
            avg_e = sum(score[0] for score in all_scaled_scores) / len(all_scaled_scores)
            avg_s = sum(score[1] for score in all_scaled_scores) / len(all_scaled_scores)
            avg_g = sum(score[2] for score in all_scaled_scores) / len(all_scaled_scores)
            avg_esg = sum(score[3] for score in all_scaled_scores) / len(all_scaled_scores)
        else:
            avg_e = avg_s = avg_g = avg_esg = 0
        
        if personal_scaled_scores:
            personal_e = sum(score[0] for score in personal_scaled_scores) / len(personal_scaled_scores)
            personal_s = sum(score[1] for score in personal_scaled_scores) / len(personal_scaled_scores)
            personal_g = sum(score[2] for score in personal_scaled_scores) / len(personal_scaled_scores)
            personal_esg = sum(score[3] for score in personal_scaled_scores) / len(personal_scaled_scores)
        else:
            personal_e = personal_s = personal_g = personal_esg = 0
        
        # Get portfolio distribution data
        portfolio_dist = cursor.execute('''
            SELECT s.Company, s.E_score, s.S_score, s.G_score
            FROM portfolio p 
            INNER JOIN Scores s ON p.company_name = s.Company 
            WHERE p.username = ?
        ''', (username,)).fetchall()
        
        # Process portfolio distribution with scaling
        portfolio_companies = []
        portfolio_e_scores = []
        portfolio_s_scores = []
        portfolio_g_scores = []
        portfolio_esg_scores = []
        
        for row in portfolio_dist:
            scaled_e = minmax_scale(row[1], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[2], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[3], minmax_values[4], minmax_values[5])
            esg_score = (scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5
            
            portfolio_companies.append(row[0])
            portfolio_e_scores.append(round(scaled_e, 2))
            portfolio_s_scores.append(round(scaled_s, 2))
            portfolio_g_scores.append(round(scaled_g, 2))
            portfolio_esg_scores.append(round(esg_score, 2))
        
        # Get all raw scores for distribution calculation
        all_raw_scores = cursor.execute('SELECT E_score, S_score, G_score FROM Scores').fetchall()
        
        # Calculate distribution in Python to match the weighting logic
        distribution_counts = {
            'Poor (0-2)': 0,
            'Fair (2-3)': 0,
            'Good (3-4)': 0,
            'Very Good (4-4.5)': 0,
            'Excellent (4.5-5)': 0
        }
        
        for row in all_raw_scores:
            scaled_e = minmax_scale(row[0], minmax_values[0], minmax_values[1])
            scaled_s = minmax_scale(row[1], minmax_values[2], minmax_values[3])
            scaled_g = minmax_scale(row[2], minmax_values[4], minmax_values[5])
            
            esg_score = (scaled_e * E_WEIGHT + scaled_s * S_WEIGHT + scaled_g * G_WEIGHT) * 0.5
            
            if esg_score < 2.0:
                distribution_counts['Poor (0-2)'] += 1
            elif esg_score < 3.0:
                distribution_counts['Fair (2-3)'] += 1
            elif esg_score < 4.0:
                distribution_counts['Good (3-4)'] += 1
            elif esg_score < 4.5:
                distribution_counts['Very Good (4-4.5)'] += 1
            else:
                distribution_counts['Excellent (4.5-5)'] += 1
        
        # Convert to list of tuples for compatibility with existing formatted output structure
        score_distribution = [
            ('Poor (0-2)', distribution_counts['Poor (0-2)']),
            ('Fair (2-3)', distribution_counts['Fair (2-3)']),
            ('Good (3-4)', distribution_counts['Good (3-4)']),
            ('Very Good (4-4.5)', distribution_counts['Very Good (4-4.5)']),
            ('Excellent (4.5-5)', distribution_counts['Excellent (4.5-5)'])
        ]
        
        conn.close()
        
        # Prepare chart data
        labels = ['Environmental', 'Social', 'Governance']
        
        # Individual scores (already scaled to 1-10)
        avg_scores = [round(avg_e, 2), round(avg_s, 2), round(avg_g, 2)]
        personal_scores = [round(personal_e, 2), round(personal_s, 2), round(personal_g, 2)]
        
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
            'esg_scores': {
                'labels': ['ESG Score (out of 5)'],
                'datasets': [
                    {
                        'label': 'App Users Average',
                        'data': [round(avg_esg, 2)],
                        'backgroundColor': 'rgba(54, 162, 235, 0.7)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 2
                    },
                    {
                        'label': 'Your Portfolio',
                        'data': [round(personal_esg, 2)],
                        'backgroundColor': 'rgba(255, 99, 132, 0.7)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'borderWidth': 2
                    }
                ]
            },
            'portfolio_esg_distribution': {
                'labels': portfolio_companies,
                'datasets': [
                    {
                        'label': 'ESG Score (out of 5)',
                        'data': portfolio_esg_scores,
                        'backgroundColor': 'rgba(16, 185, 129, 0.7)',
                        'borderColor': 'rgba(16, 185, 129, 1)',
                        'borderWidth': 2
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
