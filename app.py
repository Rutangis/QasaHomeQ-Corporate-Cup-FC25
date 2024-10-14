from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
import random
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
from statistics import mean, median

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management, needed for Flask sessions and CSRF protection

# Admin password (can be set securely in environment variables or a config file)
ADMIN_PASSWORD = "FC25Admin123"

# Function to count ratings per participant
def get_rating_counts():
    ratings_counter = {}
    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rated_player = row['rated_player']
            if rated_player not in ratings_counter:
                ratings_counter[rated_player] = 0
            ratings_counter[rated_player] += 1
    return ratings_counter

# Function to compute summary statistics for each participant
def compute_summary_statistics():
    ratings_data = {}
    
    # Read all ratings into a dictionary
    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rated_player = row['rated_player']
            rating = int(row['rating'])
            if rated_player not in ratings_data:
                ratings_data[rated_player] = []
            ratings_data[rated_player].append(rating)
    
    # Calculate summary statistics (average, median, number of ratings)
    summary = []
    with open('participants.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row['name']
            own_rating = row.get('rating', None)
            if name in ratings_data:
                avg_rating = mean(ratings_data[name])
                med_rating = median(ratings_data[name])
                num_ratings = len(ratings_data[name])
            else:
                avg_rating = None
                med_rating = None
                num_ratings = 0
            
            summary.append({
                'name': name,
                'own_rating': own_rating if own_rating else 'N/A',
                'avg_rating': round(avg_rating, 2) if avg_rating is not None else 'N/A',
                'med_rating': round(med_rating, 2) if med_rating is not None else 'N/A',
                'num_ratings': num_ratings
            })
    
    # Sort summary by average rating in descending order
    summary.sort(key=lambda x: x['avg_rating'] if isinstance(x['avg_rating'], (int, float)) else -1, reverse=True)
    
    return summary

# Flask-WTF form for admin login
class AdminLoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        if form.password.data.strip() == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
    return render_template('admin_login.html', form=form)

# Admin route to view participants and ratings (requires login)
@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participants = []
    ratings = []

    # Read participants from the CSV file
    with open('participants.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            participants.append(row)

    # Read ratings from the CSV file
    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ratings.append(row)

    # Compute summary statistics for each participant
    summary = compute_summary_statistics()

    return render_template('admin.html', participants=participants, ratings=ratings, summary=summary)

# Route to add a new participant (requires login)
@app.route('/admin/add_participant', methods=['POST'])
def admin_add_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']

    # Add new participant to participants.csv
    with open('participants.csv', 'a', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'name': participant_name, 'rating': ''})

    return redirect(url_for('admin'))

# Route to update participant ratings (requires login)
@app.route('/admin/update_participant_rating', methods=['POST'])
def admin_update_participant_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']
    new_rating = request.form['rating']

    # Update participant rating in participants.csv
    with open('participants.csv', 'r') as csvfile:
        participants = list(csv.DictReader(csvfile))

    with open('participants.csv', 'w', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            if participant['name'].strip().lower() == participant_name.strip().lower():
                participant['rating'] = new_rating
            writer.writerow(participant)

    return redirect(url_for('admin'))

# Route to update ratings given by participants (requires login)
@app.route('/admin/update_given_ratings', methods=['POST'])
def admin_update_given_ratings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater']
    rated_player = request.form['rated_player']
    new_rating = request.form['rating']

    # Update the rating in ratings.csv
    with open('ratings.csv', 'r') as csvfile:
        ratings = list(csv.DictReader(csvfile))

    with open('ratings.csv', 'w', newline='') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            if rating['rater'] == rater and rating['rated_player'] == rated_player:
                rating['rating'] = new_rating
            writer.writerow(rating)

    return redirect(url_for('admin'))

# Route to remove a participant (requires login)
@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']

    # Remove participant from participants.csv
    with open('participants.csv', 'r') as csvfile:
        participants = list(csv.DictReader(csvfile))

    with open('participants.csv', 'w', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            if participant['name'].strip().lower() != participant_name.strip().lower():
                writer.writerow(participant)

    return redirect(url_for('admin'))

# Route to remove a rating (requires login)
@app.route('/admin/remove_rating', methods=['POST'])
def admin_remove_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater']
    rated_player = request.form['rated_player']

    # Remove rating from ratings.csv
    with open('ratings.csv', 'r') as csvfile:
        ratings = list(csv.DictReader(csvfile))

    with open('ratings.csv', 'w', newline='') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            if rating['rater'] != rater or rating['rated_player'] != rated_player:
                writer.writerow(rating)

    return redirect(url_for('admin'))

# Route to download participants.csv
@app.route('/download_participants')
def download_participants():
    return send_file('participants.csv', as_attachment=True)

# Route to download ratings.csv
@app.route('/download_ratings')
def download_ratings():
    return send_file('ratings.csv', as_attachment=True)

# Route to logout admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
