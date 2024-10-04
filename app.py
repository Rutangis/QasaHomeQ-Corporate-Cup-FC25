from flask import Flask, render_template, request, redirect, url_for, send_file
import csv
import os
import random
from collections import Counter

app = Flask(__name__)

# Ensure the CSV files exist
if not os.path.isfile('participants.csv'):
    with open('participants.csv', 'w', newline='') as csvfile:
        fieldnames = ['name', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

if not os.path.isfile('ratings.csv'):
    with open('ratings.csv', 'w', newline='') as csvfile:
        fieldnames = ['rater', 'rated_player', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

# Function to count ratings for each participant
def get_rating_counts():
    ratings_counter = Counter()
    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ratings_counter[row['rated_player']] += 1
    return ratings_counter

# Route to enter name and proceed to rate others
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        self_name = request.form['self_name'].strip().lower()
        return redirect(url_for('rate', self_name=self_name))
    return render_template('index.html')

# Route to display the form with 5 random participants, excluding the current user
@app.route('/rate/<self_name>', methods=['GET', 'POST'])
def rate(self_name):
    if request.method == 'POST':
        # Handle rating submission
        self_rating = request.form['self_rating']

        # Save the self-rating to the `participants.csv`
        with open('participants.csv', 'r') as csvfile:
            participants = list(csv.DictReader(csvfile))

        # Update the self-rating if already exists or add a new entry
        with open('participants.csv', 'w', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            updated = False
            for participant in participants:
                if 'name' in participant and 'rating' in participant:
                    if participant['name'].strip().lower() == self_name:
                        participant['rating'] = self_rating
                        updated = True
                    writer.writerow(participant)
            if not updated:
                writer.writerow({'name': self_name, 'rating': self_rating})

        # Save the ratings for the 5 random participants in `ratings.csv`
        for i in range(1, 6):
            if f'random_player_{i}' in request.form:
                random_player = request.form[f'random_player_{i}']
                random_rating = request.form[f'rating_{i}']

                with open('ratings.csv', 'a', newline='') as csvfile:
                    fieldnames = ['rater', 'rated_player', 'rating']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
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
                participants.append(row['name'])  # We only need the names here
    
    # Sort participants by how often they've been rated (ascending)
    sorted_participants = sorted(participants, key=lambda x: ratings_counter[x])

    # Choose the 5 participants who have been rated the least (if there are at least 5)
    if len(sorted_participants) >= 5:
        random_participants = sorted_participants[:5]
    else:
        random_participants = sorted_participants  # If less than 5, show all
    
    # Pass the selected participants to the template
    return render_template('rate.html', random_participants=random_participants, self_name=self_name)

# Route to display a "Thank You" page after submission
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

# Admin route to view participants and ratings (password protected)
@app.route('/admin')
def admin():
    # Simple password protection
    password = request.args.get('password')
    if password == 'FC25Admin123':  # Replace with your actual admin password
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
        
        # Pass the participants and ratings data to the admin template
        return render_template('admin.html', participants=participants, ratings=ratings)
    else:
        return "Unauthorized access", 401

# Route to download participants.csv
@app.route('/download_participants')
def download_participants():
    return send_file('participants.csv', as_attachment=True)

# Route to download ratings.csv
@app.route('/download_ratings')
def download_ratings():
    return send_file('ratings.csv', as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)