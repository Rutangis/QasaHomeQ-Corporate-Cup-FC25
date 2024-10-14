from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import csv
import os
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
from statistics import mean, median

app = Flask(__name__)
app.secret_key = os.urandom(24)

ADMIN_PASSWORD = "FC25Admin123"

class AdminLoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participants = []
    ratings = []

    with open('participants.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            participants.append(row)

    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ratings.append(row)

    summary = compute_summary_statistics()

    return render_template('admin.html', participants=participants, ratings=ratings, summary=summary)

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

@app.route('/admin/remove_participant', methods=['POST'])
def admin_remove_participant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    participant_name = request.form['participant_name']

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

@app.route('/download_participants', methods=['GET'])
def download_participants():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return send_file('participants.csv', as_attachment=True)

@app.route('/download_ratings', methods=['GET'])
def download_ratings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return send_file('ratings.csv', as_attachment=True)

def compute_summary_statistics():
    ratings_data = {}
    with open('ratings.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rated_player = row['rated_player']
            rating = int(row['rating'])
            if rated_player not in ratings_data:
                ratings_data[rated_player] = []
            ratings_data[rated_player].append(rating)

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

    summary.sort(key=lambda x: x['avg_rating'] if isinstance(x['avg_rating'], (int, float)) else -1, reverse=True)
    return summary

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
