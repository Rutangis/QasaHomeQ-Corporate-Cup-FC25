# app.py

from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
from statistics import mean, median
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Simple secret key for session management

ADMIN_PASSWORD = "FC25Admin123"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        self_name = request.form['self_name'].strip().lower()
        return redirect(url_for('rate', self_name=self_name))
    return render_template('index.html')

@app.route('/rate/<self_name>', methods=['GET', 'POST'])
def rate(self_name):
    if request.method == 'POST':
        self_rating = request.form['self_rating']

        # Update participants.csv
        if os.path.exists('participants.csv'):
            with open('participants.csv', 'r') as csvfile:
                participants = list(csv.DictReader(csvfile))
        else:
            participants = []

        updated = False
        for participant in participants:
            if participant['name'].strip().lower() == self_name:
                participant['rating'] = self_rating
                updated = True

        if not updated:
            participants.append({'name': self_name, 'rating': self_rating})

        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(participants)

        # Append ratings to ratings.csv
        with open('ratings.csv', 'a', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for i in range(1, 6):
                random_player = request.form.get(f'random_player_{i}')
                random_rating = request.form.get(f'rating_{i}')
                if random_player and random_rating:
                    writer.writerow({'rater': self_name, 'rated_player': random_player, 'rating': random_rating})

        return redirect(url_for('thank_you'))

    participants = []
    ratings_counter = get_rating_counts()

    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() != self_name:
                    participants.append(row['name'])

    sorted_participants = sorted(participants, key=lambda x: ratings_counter.get(x, 0))
    random_participants = sorted_participants[:5] if len(sorted_participants) >= 5 else sorted_participants

    return render_template('rate.html', random_participants=random_participants, self_name=self_name)

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password.strip() == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        participants = []
        ratings = []

        if os.path.exists('participants.csv'):
            with open('participants.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                participants = list(reader)

        if os.path.exists('ratings.csv'):
            with open('ratings.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                ratings = list(reader)

        summary = compute_summary_statistics()

        return render_template('admin.html', participants=participants, ratings=ratings, summary=summary)
    except Exception as e:
        print(f"Error in admin route: {e}")
        return f"Internal Server Error: {e}", 500

@app.route('/admin/add_participant', methods=['POST'])
def admin_add_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']

    with open('participants.csv', 'a', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'name': participant_name, 'rating': ''})

    return redirect(url_for('admin'))

@app.route('/admin/update_participant_rating', methods=['POST'])
def admin_update_participant_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']
    new_rating = request.form['rating']

    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r') as csvfile:
            participants = list(csv.DictReader(csvfile))
    else:
        participants = []

    with open('participants.csv', 'w', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            if participant['name'].strip().lower() == participant_name.strip().lower():
                participant['rating'] = new_rating
            writer.writerow(participant)

    return redirect(url_for('admin'))

@app.route('/admin/update_given_ratings', methods=['POST'])
def admin_update_given_ratings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater']
    rated_player = request.form['rated_player']
    new_rating = request.form['rating']

    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r') as csvfile:
            ratings = list(csv.DictReader(csvfile))
    else:
        ratings = []

    with open('ratings.csv', 'w', newline='') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            if rating['rater'] == rater and rating['rated_player'] == rated_player:
                rating['rating'] = new_rating
            writer.writerow(rating)

    return redirect(url_for('admin'))

@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']

    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r') as csvfile:
            participants = list(csv.DictReader(csvfile))
    else:
        participants = []

    with open('participants.csv', 'w', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            if participant['name'].strip().lower() != participant_name.strip().lower():
                writer.writerow(participant)

    return redirect(url_for('admin'))

@app.route('/admin/remove_given_rating', methods=['POST'])
def admin_remove_given_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater']
    rated_player = request.form['rated_player']

    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r') as csvfile:
            ratings = list(csv.DictReader(csvfile))
    else:
        ratings = []

    with open('ratings.csv', 'w', newline='') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            if rating['rater'] != rater or rating['rated_player'] != rated_player:
                writer.writerow(rating)

    return redirect(url_for('admin'))

@app.route('/download_participants', methods=['GET'])
def download_participants():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        return send_file('participants.csv', as_attachment=True)
    except Exception as e:
        print(f"Download error: {e}")
        return "Error downloading file", 500

@app.route('/download_ratings', methods=['GET'])
def download_ratings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        return send_file('ratings.csv', as_attachment=True)
    except Exception as e:
        print(f"Download error: {e}")
        return "Error downloading file", 500

def compute_summary_statistics():
    participants = []
    ratings_data = {}

    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                participants.append(row)

    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rated_player = row['rated_player']
                try:
                    rating = int(row['rating'])
                    if rated_player not in ratings_data:
                        ratings_data[rated_player] = []
                    ratings_data[rated_player].append(rating)
                except ValueError:
                    continue  # Skip invalid ratings

    summary = []
    for participant in participants:
        name = participant['name']
        own_rating = participant.get('rating', None)
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

def get_rating_counts():
    ratings_counter = {}
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rated_player = row['rated_player']
                ratings_counter[rated_player] = ratings_counter.get(rated_player, 0) + 1
    return ratings_counter

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
