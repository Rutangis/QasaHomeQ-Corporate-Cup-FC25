# app.py

from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
from statistics import mean, median
import random

app = Flask(__name__)
app.secret_key = 'FC25Admin123'  # Replace with a strong, random key

ADMIN_PASSWORD = "FC25Admin123"  # Replace with a secure password

def get_rating_counts():
    """Counts the number of ratings each participant has received."""
    ratings_counter = {}
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rated_player = row['rated_player']
                ratings_counter[rated_player] = ratings_counter.get(rated_player, 0) + 1
    return ratings_counter

def compute_summary_statistics():
    """Computes summary statistics for participants based on ratings."""
    participants = []
    ratings_data = {}

    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                participants.append(row)

    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='') as csvfile:
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
        if name in ratings_data and ratings_data[name]:
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

    # Sort summary by average rating in descending order, placing 'N/A' at the end
    summary.sort(key=lambda x: x['avg_rating'] if isinstance(x['avg_rating'], (int, float)) else -1, reverse=True)

    return summary

def initialize_csv_files():
    """Ensures that participants.csv and ratings.csv exist with headers."""
    if not os.path.exists('participants.csv'):
        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    if not os.path.exists('ratings.csv'):
        with open('ratings.csv', 'w', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

@app.before_first_request
def setup():
    """Initialize CSV files before the first request."""
    initialize_csv_files()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        self_name = request.form['self_name'].strip().lower()
        if not self_name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('index'))
        return redirect(url_for('rate', self_name=self_name))
    return render_template('index.html')

@app.route('/rate/<self_name>', methods=['GET', 'POST'])
def rate(self_name):
    if request.method == 'POST':
        self_rating = request.form.get('self_rating')
        if not self_rating or not self_rating.isdigit() or not (1 <= int(self_rating) <=5):
            flash('Invalid self-rating. Please select a rating between 1 and 5.', 'danger')
            return redirect(url_for('rate', self_name=self_name))
        self_rating = int(self_rating)

        # Update participants.csv
        participants = []
        participant_found = False
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() == self_name:
                    row['rating'] = self_rating
                    participant_found = True
                participants.append(row)
        
        if not participant_found:
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
                    if random_rating.isdigit() and 1 <= int(random_rating) <=5:
                        writer.writerow({'rater': self_name, 'rated_player': random_player, 'rating': int(random_rating)})
                    else:
                        flash(f'Invalid rating for {random_player}. Must be between 1 and 5.', 'danger')
        
        return redirect(url_for('thank_you'))

    # GET request handling
    participants = []
    ratings_counter = get_rating_counts()

    with open('participants.csv', 'r', newline='') as csvfile:
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
        password = request.form.get('password', '').strip()
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please log in to access the admin dashboard.', 'danger')
        return redirect(url_for('admin_login'))

    try:
        participants = []
        ratings = []

        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            participants = list(reader)

        with open('ratings.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            ratings = list(reader)

        summary = compute_summary_statistics()

        return render_template('admin.html', participants=participants, ratings=ratings, summary=summary)
    except Exception as e:
        print(f"Error in admin_dashboard route: {e}")
        flash('An error occurred while loading the admin dashboard.', 'danger')
        return redirect(url_for('admin_login'))

@app.route('/admin/add_participant', methods=['POST'])
def admin_add_participant():
    if not session.get('admin_logged_in'):
        flash('Please log in to add a participant.', 'danger')
        return redirect(url_for('admin_login'))

    participant_name = request.form.get('participant_name', '').strip()
    if not participant_name:
        flash('Participant name cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Check if participant already exists
    participant_exists = False
    with open('participants.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['name'].strip().lower() == participant_name.lower():
                participant_exists = True
                break

    if participant_exists:
        flash('Participant already exists.', 'danger')
    else:
        with open('participants.csv', 'a', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # If file was empty, write header first
            if os.stat('participants.csv').st_size == 0:
                writer.writeheader()
            writer.writerow({'name': participant_name, 'rating': ''})
        flash(f'Participant "{participant_name}" added successfully.', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_participant_rating', methods=['POST'])
def admin_update_participant_rating():
    if not session.get('admin_logged_in'):
        flash('Please log in to update participant ratings.', 'danger')
        return redirect(url_for('admin_login'))

    participant_name = request.form.get('participant_name', '').strip()
    new_rating = request.form.get('rating', '').strip()

    if not new_rating.isdigit() or not (1 <= int(new_rating) <=5):
        flash('Invalid rating. Please enter a number between 1 and 5.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_rating = int(new_rating)

    with open('participants.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        participants = list(reader)

    participant_found = False
    for participant in participants:
        if participant['name'].strip().lower() == participant_name.lower():
            participant['rating'] = new_rating
            participant_found = True
            break

    if not participant_found:
        flash(f'Participant "{participant_name}" not found.', 'danger')
    else:
        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(participants)
        flash(f'Rating for participant "{participant_name}" updated to {new_rating}.', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_given_ratings', methods=['POST'])
def admin_update_given_ratings():
    if not session.get('admin_logged_in'):
        flash('Please log in to update given ratings.', 'danger')
        return redirect(url_for('admin_login'))

    rater = request.form.get('rater', '').strip()
    rated_player = request.form.get('rated_player', '').strip()
    new_rating = request.form.get('rating', '').strip()

    if not new_rating.isdigit() or not (1 <= int(new_rating) <=5):
        flash('Invalid rating. Please enter a number between 1 and 5.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_rating = int(new_rating)

    with open('ratings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        ratings = list(reader)

    rating_found = False
    for rating in ratings:
        if rating['rater'] == rater and rating['rated_player'] == rated_player:
            rating['rating'] = new_rating
            rating_found = True
            break

    if not rating_found:
        flash('Rating entry not found.', 'danger')
    else:
        with open('ratings.csv', 'w', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ratings)
        flash(f'Rating for {rater} -> {rated_player} updated to {new_rating}.', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        flash('Please log in to remove a participant.', 'danger')
        return redirect(url_for('admin_login'))

    participant_name = request.form.get('participant_name', '').strip()

    if not participant_name:
        flash('Participant name cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    with open('participants.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        participants = [row for row in reader if row['name'].strip().lower() != participant_name.lower()]

    # Check if participant was removed
    with open('participants.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        original_participants = list(reader)

    if len(participants) == len(original_participants):
        flash(f'Participant "{participant_name}" not found.', 'danger')
    else:
        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(participants)
        flash(f'Participant "{participant_name}" removed successfully.', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_given_rating', methods=['POST'])
def admin_remove_given_rating():
    if not session.get('admin_logged_in'):
        flash('Please log in to remove a rating.', 'danger')
        return redirect(url_for('admin_login'))

    rater = request.form.get('rater', '').strip()
    rated_player = request.form.get('rated_player', '').strip()

    if not rater or not rated_player:
        flash('Rater and Rated Player names cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    with open('ratings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        ratings = [row for row in reader if not (row['rater'] == rater and row['rated_player'] == rated_player)]

    # Check if any rating was removed
    with open('ratings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        original_ratings = list(reader)

    if len(ratings) == len(original_ratings):
        flash('Rating entry not found.', 'danger')
    else:
        with open('ratings.csv', 'w', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ratings)
        flash(f'Rating by "{rater}" for "{rated_player}" removed successfully.', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/download_participants', methods=['GET'])
def download_participants():
    if not session.get('admin_logged_in'):
        flash('Please log in to download participants data.', 'danger')
        return redirect(url_for('admin_login'))
    try:
        if not os.path.exists('participants.csv'):
            flash('Participants file does not exist.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return send_file('participants.csv', as_attachment=True)
    except Exception as e:
        print(f"Download error: {e}")
        flash('Error downloading participants file.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/download_ratings', methods=['GET'])
def download_ratings():
    if not session.get('admin_logged_in'):
        flash('Please log in to download ratings data.', 'danger')
        return redirect(url_for('admin_login'))
    try:
        if not os.path.exists('ratings.csv'):
            flash('Ratings file does not exist.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return send_file('ratings.csv', as_attachment=True)
    except Exception as e:
        print(f"Download error: {e}")
        flash('Error downloading ratings file.', 'danger')
        return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
