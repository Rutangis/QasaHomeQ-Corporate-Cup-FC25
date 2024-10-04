from flask import Flask, render_template, request, redirect, url_for
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

# Route to display the form with 5 random participants
@app.route('/')
def index():
    participants = []
    ratings_counter = get_rating_counts()
    
    # Read participants from CSV
    with open('participants.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            participants.append(row['name'])  # We only need the names here
    
    # Sort participants by how often they've been rated (ascending)
    sorted_participants = sorted(participants, key=lambda x: ratings_counter[x])

    # Choose the 5 participants who have been rated the least (if there are at least 5)
    if len(sorted_participants) >= 5:
        random_participants = sorted_participants[:5]
    else:
        random_participants = sorted_participants  # If less than 5, show all
    
    # Pass the selected participants to the template
    return render_template('index.html', random_participants=random_participants)

# Route to handle form submission and save ratings
@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Get the self-rating from the form
        self_name = request.form['self_name']
        self_rating = request.form['self_rating']

        # Save the self-rating to the `participants.csv`
        with open('participants.csv', 'a', newline='') as csvfile:
            fieldnames = ['name', 'rating']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
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
    
    except KeyError as e:
        # Handle missing form fields
        return f"Missing form field: {e}", 400

# Route to display a "Thank You" page after submission
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

# Admin route to view participants (password protected)
@app.route('/admin')
def admin():
    # Simple password protection
    password = request.args.get('password')
    if password == 'FC25Admin123':  # Replace with your actual admin password
        participants = []

        # Read participants from the CSV file
        with open('participants.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                participants.append(row)
        
        # Pass the participants data to the admin template
        return render_template('admin.html', participants=participants)
    else:
        return "Unauthorized access", 401

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

