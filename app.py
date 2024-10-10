from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
import random
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired

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
            rated_player = row['rated_player']  # Get the rated player from the row
            if rated_player not in ratings_counter:
                ratings_counter[rated_player] = 0  # Initialize if not present
            ratings_counter[rated_player] += 1  # Increment the count
    return ratings_counter

# Flask-WTF form for admin login
class AdminLoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Route to enter name and proceed to rate others
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the name and redirect to the rate page
        self_name = request.form['self_name'].strip().lower()
        return redirect(url_for('rate', self_name=self_name))
    return render_template('index.html')

# Route to display the form with 5 random participants, excluding the current user
@app.route('/rate/<self_name>', methods=['GET', 'POST'])
def rate(self_name):
    if request.method == 'POST':
        # Handle rating submission
        self_rating = request.form['self_rating']

        # Update or add the self-rating in `participants.csv`
        with open('participants.csv', 'r') as csvfile:
            participants = list(csv.DictReader(csvfile))

        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            updated = False
            for participant in participants:
                if participant['name'].strip().lower() == self_name:
                    participant['rating'] = self_rating
                    updated = True
                writer.writerow(participant)
            if not updated:
                writer.writerow({'name': self_name, 'rating': self_rating})

        # Save the ratings for the 5 random participants in `ratings.csv`
        with open('ratings.csv', 'a', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for i in range(1, 6):
                random_player = request.form[f'random_player_{i}']
                random_rating = request.form[f'rating_{i}']
                writer.writerow({'rater': self_name, 'rated_player': random_player, 'rating': random_rating})

        return redirect(url_for('thank_you'))

    # If GET request, display the rating form
    participants = []
    ratings_counter = get_rating_counts()

    # Read participants from CSV and filter out the current user
    with open('participants.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['name'].strip().lower() != self_name:
                participants.append(row['name'])

    # Sort participants by how often they've been rated (ascending)
    sorted_participants = sorted(participants, key=lambda x: ratings_counter.get(x, 0))

    # Choose the 5 participants who have been rated the least (if there are at least 5)
    random_participants = sorted_participants[:5] if len(sorted_participants) >= 5 else sorted_participants

    return render_template('rate.html', random_participants=random_participants, self_name=self_name)

# Route to display a "Thank You" page after submission
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

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

    return render_template('admin.html', participants=participants, ratings=ratings)

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

# Route to logout admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Route to download participants.csv
@app.route('/download_participants')
def download_participants():
    return send_file('participants.csv', as_attachment=True)

# Route to download ratings.csv
@app.route('/download_ratings')
def download_ratings():
    return send_file('ratings.csv', as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
