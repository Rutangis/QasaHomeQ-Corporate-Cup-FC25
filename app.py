from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
import random
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
import statistics
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # Use environment variable for production

# Admin password (use environment variables for security in production)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'FC25Admin123')

# Function to count ratings per participant
def get_rating_counts():
    ratings_counter = {}
    if not os.path.exists('ratings.csv'):
        # Create ratings.csv with headers if it doesn't exist
        with open('ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rated_player = row['rated_player'].strip().lower()  # Normalize to lowercase
            if rated_player not in ratings_counter:
                ratings_counter[rated_player] = 0
            ratings_counter[rated_player] += 1
    return ratings_counter

# Flask-WTF form for admin login
class AdminLoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Helper function to calculate ratings statistics
def calculate_ratings_statistics():
    participants = []
    ratings_dict = defaultdict(list)

    # Read participants and their self-ratings from participants.csv
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row['name'].strip()
                participants.append(name)
                self_rating = row.get('rating', '').strip()
                if self_rating and self_rating != '':
                    try:
                        rating_int = int(float(self_rating))  # Convert to int
                        if 1 <= rating_int <= 5:
                            ratings_dict[name.lower()].append(rating_int)
                    except ValueError:
                        pass  # Ignore invalid self-ratings

    # Read ratings from ratings.csv
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rated_player = row['rated_player'].strip().lower()
                rating = row['rating'].strip()
                if rated_player and rating:
                    try:
                        rating_int = int(float(rating))  # Convert to int
                        if 1 <= rating_int <= 5:
                            ratings_dict[rated_player].append(rating_int)
                    except ValueError:
                        pass  # Ignore invalid ratings

    # Calculate statistics
    statistics_list = []
    for participant in participants:
        ratings = ratings_dict.get(participant.lower(), [])
        if ratings:
            average = round(sum(ratings) / len(ratings), 2)
            median = round(statistics.median(ratings), 2)
            count = len(ratings)
        else:
            average = 'N/A'
            median = 'N/A'
            count = 0
        statistics_list.append({
            'name': participant,
            'average': average,
            'median': median,
            'count': count
        })

    # Sort the list by average rating in descending order, handling 'N/A'
    statistics_list_sorted = sorted(
        statistics_list,
        key=lambda x: (x['average'] if isinstance(x['average'], float) else -1),
        reverse=True
    )

    return statistics_list_sorted

# Helper function to assign teams
def assign_teams(participants, num_teams=4):
    """
    Assigns participants to teams aiming for balanced total average ratings.

    :param participants: List of dictionaries with 'name' and 'average' keys
    :param num_teams: Number of teams to create
    :return: List of teams, each team is a list of participant names
    """
    # Filter out participants without an average rating
    rated_participants = [p for p in participants if isinstance(p['average'], float)]
    unrated_participants = [p for p in participants if not isinstance(p['average'], float)]

    # Sort participants by average rating descending
    sorted_participants = sorted(rated_participants, key=lambda x: x['average'], reverse=True)

    # Initialize teams
    teams = [[] for _ in range(num_teams)]
    team_totals = [0.0 for _ in range(num_teams)]

    # Assign participants to teams using a greedy algorithm
    for participant in sorted_participants:
        # Assign to the team with the current lowest total
        min_team_index = team_totals.index(min(team_totals))
        teams[min_team_index].append(participant['name'])
        team_totals[min_team_index] += participant['average']

    # Optionally, distribute unrated participants randomly
    for participant in unrated_participants:
        random_team_index = random.randint(0, num_teams - 1)
        teams[random_team_index].append(participant['name'])

    return teams

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
        self_rating = request.form.get('self_rating', '').strip()
        if not self_rating:
            flash('Self rating is required.', 'danger')
            return redirect(url_for('rate', self_name=self_name))
        try:
            self_rating = int(float(self_rating))
            if not (1 <= self_rating <= 5):
                raise ValueError
        except ValueError:
            flash('Self rating must be an integer between 1 and 5.', 'danger')
            return redirect(url_for('rate', self_name=self_name))

        # Update or add the self-rating in `participants.csv`
        participants = []
        if os.path.exists('participants.csv'):
            with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    participants.append(row)

        updated = False
        with open('participants.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for participant in participants:
                if participant['name'].strip().lower() == self_name:
                    writer.writerow({'name': participant['name'], 'rating': self_rating})
                    updated = True
                else:
                    writer.writerow(participant)
            if not updated:
                writer.writerow({'name': self_name, 'rating': self_rating})

        # Save the ratings for the 5 random participants in `ratings.csv`
        with open('ratings.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rater', 'rated_player', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # If the file was just created, write headers
            if os.stat('ratings.csv').st_size == 0:
                writer.writeheader()
            for i in range(1, 6):
                random_player = request.form.get(f'random_player_{i}', '').strip()
                random_rating = request.form.get(f'rating_{i}', '').strip()
                if random_player and random_rating:
                    try:
                        random_rating_int = int(float(random_rating))
                        if 1 <= random_rating_int <= 5:
                            writer.writerow({
                                'rater': self_name,
                                'rated_player': random_player,
                                'rating': random_rating_int
                            })
                    except ValueError:
                        pass  # Ignore invalid ratings

        return redirect(url_for('thank_you'))

    # If GET request, display the rating form
    participants = []
    ratings_counter = get_rating_counts()

    # Read participants from CSV and filter out the current user
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() != self_name:
                    participants.append(row['name'].strip())

    # Sort participants by how often they've been rated (ascending)
    sorted_participants = sorted(participants, key=lambda x: ratings_counter.get(x.lower(), 0))

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
            flash('Logged in successfully.', 'success')
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
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                participants.append(row)

    # Read ratings from the CSV file
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ratings.append(row)

    # Calculate ratings statistics
    ratings_statistics = calculate_ratings_statistics()

    # Assign teams
    teams = assign_teams(ratings_statistics, num_teams=4)  # You can change the number of teams here

    return render_template(
        'admin.html',
        participants=participants,
        ratings=ratings,
        ratings_statistics=ratings_statistics,  # Pass the statistics to the template
        teams=teams  # Pass the generated teams to the template
    )

# Route to add a new participant (requires login)
@app.route('/admin/add_participant', methods=['POST'])
def admin_add_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name'].strip()

    if not participant_name:
        flash('Participant name cannot be empty.', 'danger')
        return redirect(url_for('admin'))

    # Check if participant already exists
    participant_exists = False
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() == participant_name.lower():
                    participant_exists = True
                    break

    if participant_exists:
        flash('Participant already exists.', 'warning')
    else:
        # Add new participant to participants.csv
        with open('participants.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # If the file was just created, write headers
            if os.stat('participants.csv').st_size == 0:
                writer.writeheader()
            writer.writerow({'name': participant_name, 'rating': ''})
        flash('Participant added successfully.', 'success')

    return redirect(url_for('admin'))

# Route to update participant ratings (requires login)
@app.route('/admin/update_participant_rating', methods=['POST'])
def admin_update_participant_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name'].strip()
    new_rating = request.form['rating'].strip()

    if not new_rating:
        flash('Rating cannot be empty.', 'danger')
        return redirect(url_for('admin'))

    try:
        new_rating = int(float(new_rating))
        if not (1 <= new_rating <= 5):
            raise ValueError
    except ValueError:
        flash('Rating must be an integer between 1 and 5.', 'danger')
        return redirect(url_for('admin'))

    # Update participant rating in participants.csv
    participants = []
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() == participant_name.lower():
                    row['rating'] = new_rating
                participants.append(row)

    # Write back to participants.csv
    with open('participants.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            writer.writerow(participant)

    flash('Participant rating updated successfully.', 'success')
    return redirect(url_for('admin'))

# Route to update ratings given by participants (requires login)
@app.route('/admin/update_given_ratings', methods=['POST'])
def admin_update_given_ratings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater'].strip()
    rated_player = request.form['rated_player'].strip()
    new_rating = request.form['rating'].strip()

    if not new_rating:
        flash('Rating cannot be empty.', 'danger')
        return redirect(url_for('admin'))

    try:
        new_rating = int(float(new_rating))
        if not (1 <= new_rating <= 5):
            raise ValueError
    except ValueError:
        flash('Rating must be an integer between 1 and 5.', 'danger')
        return redirect(url_for('admin'))

    # Update the rating in ratings.csv
    ratings = []
    rating_found = False
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['rater'].strip().lower() == rater.lower() and row['rated_player'].strip().lower() == rated_player.lower():
                    row['rating'] = new_rating
                    rating_found = True
                ratings.append(row)

    if not rating_found:
        flash('Rating entry not found.', 'warning')
        return redirect(url_for('admin'))

    # Write back to ratings.csv
    with open('ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            writer.writerow(rating)

    flash('Given rating updated successfully.', 'success')
    return redirect(url_for('admin'))

# Route to remove a participant (requires login)
@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name'].strip()

    # Remove participant from participants.csv
    participants = []
    if os.path.exists('participants.csv'):
        with open('participants.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'].strip().lower() != participant_name.lower():
                    participants.append(row)

    # Write back to participants.csv
    with open('participants.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for participant in participants:
            writer.writerow(participant)

    # Remove related ratings from ratings.csv
    ratings = []
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['rater'].strip().lower() != participant_name.lower() and row['rated_player'].strip().lower() != participant_name.lower():
                    ratings.append(row)

    # Write back to ratings.csv
    with open('ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            writer.writerow(rating)

    flash('Participant and related ratings removed successfully.', 'success')
    return redirect(url_for('admin'))

# Route to remove a rating (requires login)
@app.route('/admin/remove_rating', methods=['POST'])
def admin_remove_rating():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    rater = request.form['rater'].strip()
    rated_player = request.form['rated_player'].strip()

    # Remove rating from ratings.csv
    ratings = []
    rating_found = False
    if os.path.exists('ratings.csv'):
        with open('ratings.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['rater'].strip().lower() == rater.lower() and row['rated_player'].strip().lower() == rated_player.lower():
                    rating_found = True
                    continue  # Skip this row to remove it
                ratings.append(row)

    if not rating_found:
        flash('Rating entry not found.', 'warning')
        return redirect(url_for('admin'))

    # Write back to ratings.csv
    with open('ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rating in ratings:
            writer.writerow(rating)

    flash('Rating removed successfully.', 'success')
    return redirect(url_for('admin'))

# Route to logout admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

# Route to download participants.csv
@app.route('/download_participants')
def download_participants():
    if os.path.exists('participants.csv'):
        return send_file('participants.csv', as_attachment=True)
    else:
        flash('Participants file not found.', 'danger')
        return redirect(url_for('admin'))

# Route to download ratings.csv
@app.route('/download_ratings')
def download_ratings():
    if os.path.exists('ratings.csv'):
        return send_file('ratings.csv', as_attachment=True)
    else:
        flash('Ratings file not found.', 'danger')
        return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
