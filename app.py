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
    if not os.path.exists('ratings.csv'):
        return ratings_counter
    with open('ratings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rated_player = row['rated_player'].strip().lower()
            if rated_player not in ratings_counter:
                ratings_counter[rated_player] = 0
            ratings_counter[rated_player] += 1
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
        if not self_name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('index'))
        return redirect(url_for('rate', self_name=self_name))
    return render_template('index.html')

# Route to display the form with 5 random participants, excluding the current user
@app.route('/rate/<self_name>', methods=['GET', 'POST'])
def rate(self_name):
    if request.method == 'POST':
        # Handle rating submission
        self_rating = request.form['self_rating']
        if not self_rating:
            flash('Self rating is required.', 'danger')
            return redirect(url_for('rate', self_name=self_name))
        # Ensure the rating is an integer between 1 and 5
        try:
            self_rating = int(self_rating)
            if self_rating < 1 or self_rating > 5:
                raise ValueError
        except ValueError:
            flash('Invalid self rating. Please enter a number between 1 and 5.', 'danger')
            return redirect(url_for('rate', self_name=self_name))

        # Update or add the self-rating in `participants.csv`
        participants = []
        participant_found = False
        if os.path.exists('participants.csv'):
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

        # Save the ratings for the 5 random participants in `ratings.csv`
        if not os.path.exists('ratings.csv'):
            with open('ratings.csv', 'w', newline='') as csvfile:
                fieldnames = ['rater', 'rated_player', 'rating']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

        with open('ratings.csv', 'a', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for i in range(1, 6):
                random_player = request.form.get(f'random_player_{i}')
                random_rating = request.form.get(f'rating_{i}')
                if random_player and random_rating:
                    # Validate random_rating
                    try:
                        random_rating = int(random_rating)
                        if random_rating < 1 or random_rating > 5:
                            raise ValueError
                    except ValueError:
                        flash(f'Invalid rating for {random_player}. Please enter a number between 1 and 5.', 'danger')
                        continue
                    writer.writerow({'rater': self_name, 'rated_player': random_player, 'rating': random_rating})

        return redirect(url_for('thank_you'))

    # If GET request, display the rating form
    participants = []
    ratings_counter = get_rating_counts()

    # Read participants from CSV and filter out the current user
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() != self_name:
                    participants.append(row['name'])

    # Sort participants by how often they've been rated (ascending)
    sorted_participants = sorted(participants, key=lambda x: ratings_counter.get(x.strip().lower(), 0))

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
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
    return render_template('admin_login.html', form=form)

# Admin dashboard route (requires login)
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please log in to access the admin dashboard.', 'danger')
        return redirect(url_for('admin_login'))

    participants = []
    ratings = []

    # Read participants from the CSV file
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            participants = list(reader)

    # Read ratings from the CSV file
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            ratings = list(reader)

    # Compute summary statistics
    summary = compute_summary_statistics()

    return render_template('admin.html', participants=participants, ratings=ratings, summary=summary)

# Route to add a new participant (requires login)
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
    if os.path.exists('participants.csv'):
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

# Route to update participant ratings (requires login)
@app.route('/admin/update_participant_rating', methods=['POST'])
def admin_update_participant_rating():
    if not session.get('admin_logged_in'):
        flash('Please log in to update participant ratings.', 'danger')
        return redirect(url_for('admin_login'))

    participant_name = request.form.get('participant_name', '').strip()
    new_rating = request.form.get('rating', '').strip()

    if not new_rating.isdigit() or not (1 <= int(new_rating) <= 5):
        flash('Invalid rating. Please enter a number between 1 and 5.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_rating = int(new_rating)

    participants = []
    participant_found = False
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() == participant_name.lower():
                    row['rating'] = new_rating
                    participant_found = True
                participants.append(row)

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

# Route to update ratings given by participants (requires login)
@app.route('/admin/update_given_ratings', methods=['POST'])
def admin_update_given_ratings():
    if not session.get('admin_logged_in'):
        flash('Please log in to update given ratings.', 'danger')
        return redirect(url_for('admin_login'))

    rater = request.form.get('rater', '').strip()
    rated_player = request.form.get('rated_player', '').strip()
    new_rating = request.form.get('rating', '').strip()

    if not new_rating.isdigit() or not (1 <= int(new_rating) <= 5):
        flash('Invalid rating. Please enter a number between 1 and 5.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_rating = int(new_rating)

    ratings = []
    rating_found = False
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['rater'] == rater and row['rated_player'] == rated_player:
                    row['rating'] = new_rating
                    rating_found = True
                ratings.append(row)

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

# Route to remove a participant (requires login)
@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        flash('Please log in to remove a participant.', 'danger')
        return redirect(url_for('admin_login'))

    participant_name = request.form.get('participant_name', '').strip()

    if not participant_name:
        flash('Participant name cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    participants = []
    participant_removed = False
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() != participant_name.lower():
                    participants.append(row)
                else:
                    participant_removed = True

    if not participant_removed:
        flash(f'Participant "{participant_name}" not found.', 'danger')
    else:
        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(participants)
        flash(f'Participant "{participant_name}" removed successfully.', 'success')

    return redirect(url_for('admin_dashboard'))

# Route to remove a rating (requires login)
@app.route('/admin/remove_rating', methods=['POST'])
def admin_remove_rating():
    if not session.get('admin_logged_in'):
        flash('Please log in to remove a rating.', 'danger')
        return redirect(url_for('admin_login'))

    rater = request.form.get('rater', '').strip()
    rated_player = request.form.get('rated_player', '').strip()

    if not rater or not rated_player:
        flash('Rater and Rated Player names cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    ratings = []
    rating_removed = False
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['rater'] == rater and row['rated_player'] == rated_player:
                    rating_removed = True
                    continue  # Skip this rating
                ratings.append(row)

    if not rating_removed:
        flash('Rating entry not found.', 'danger')
    else:
        with open('ratings.csv', 'w', newline='') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ratings)
        flash(f'Rating by "{rater}" for "{rated_player}" removed successfully.', 'success')

    return redirect(url_for('admin_dashboard'))

# Route to logout admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Successfully logged out.', 'success')
    return redirect(url_for('admin_login'))

# Route to download participants.csv (requires login)
@app.route('/download_participants')
def download_participants():
    if not session.get('admin_logged_in'):
        flash('Please log in to download participants data.', 'danger')
        return redirect(url_for('admin_login'))
    try:
        return send_file('participants.csv', as_attachment=True)
    except Exception as e:
        flash('Error downloading participants file.', 'danger')
        return redirect(url_for('admin_dashboard'))

# Route to download ratings.csv (requires login)
@app.route('/download_ratings')
def download_ratings():
    if not session.get('admin_logged_in'):
        flash('Please log in to download ratings data.', 'danger')
        return redirect(url_for('admin_login'))
    try:
        return send_file('ratings.csv', as_attachment=True)
    except Exception as e:
        flash('Error downloading ratings file.', 'danger')
        return redirect(url_for('admin_dashboard'))

# Function to compute summary statistics
def compute_summary_statistics():
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
                rated_player = row['rated_player'].strip().lower()
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
        own_rating = participant.get('rating', 'N/A')
        ratings_for_participant = ratings_data.get(name.strip().lower(), [])
        if ratings_for_participant:
            avg_rating = mean(ratings_for_participant)
            med_rating = median(ratings_for_participant)
            num_ratings = len(ratings_for_participant)
        else:
            avg_rating = 'N/A'
            med_rating = 'N/A'
            num_ratings = 0

        summary.append({
            'name': name,
            'own_rating': own_rating if own_rating else 'N/A',
            'avg_rating': round(avg_rating, 2) if isinstance(avg_rating, (int, float)) else 'N/A',
            'med_rating': round(med_rating, 2) if isinstance(med_rating, (int, float)) else 'N/A',
            'num_ratings': num_ratings
        })

    # Sort summary by average rating in descending order, placing 'N/A' at the end
    summary.sort(key=lambda x: x['avg_rating'] if isinstance(x['avg_rating'], (int, float)) else -1, reverse=True)

    return summary

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
