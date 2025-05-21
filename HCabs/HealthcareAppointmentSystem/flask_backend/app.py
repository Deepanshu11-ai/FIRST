from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthcare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'  # Replace with secure key

db = SQLAlchemy(app)
api = Api(app)
CORS(app)  # Enable CORS for Django frontend

# Configure logging
logging.basicConfig(level=logging.INFO)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'patient', 'doctor', 'admin'
    appointments = db.relationship('Appointment', backref='patient', foreign_keys='Appointment.patient_id', lazy=True)
    doctor_appointments = db.relationship('Appointment', backref='doctor', foreign_keys='Appointment.doctor_id', lazy=True)
    availabilities = db.relationship('Availability', backref='doctor', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'completed', 'cancelled'

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

# JWT Authentication Decorator for Flask-RESTful
def token_required(f):
    @wraps(f)
    def decorated(self, *args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {'message': 'Token is missing'}, 401
        try:
            token = token.split()[1]  # Extract token from "Bearer <token>"
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(username=data['username']).first()
            if not current_user:
                return {'message': 'User not found'}, 401
        except Exception as e:
            return {'message': f'Token is invalid: {str(e)}'}, 401
        return f(self, current_user, *args, **kwargs)  # Pass self explicitly
    return decorated

# Initialize Admin User
def init_admin_user():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created with username: admin, password: admin123")

# Template Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if not username or not password or not role:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        if role not in ['patient', 'doctor']:
            flash('Invalid role', 'error')
            return redirect(url_for('register'))
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash(f'Welcome, {user.username}!', 'success')
            if user.role == 'patient':
                return redirect(url_for('patient_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(patient_id=user.id).all()
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('patient_dashboard.html', user=user, appointments=appointments, doctors=doctors)

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(doctor_id=user.id).all()
    availabilities = Availability.query.filter_by(doctor_id=user.id).all()
    return render_template('doctor_dashboard.html', user=user, appointments=appointments, availabilities=availabilities)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    doctors = User.query.filter_by(role='doctor').all()
    appointments = Appointment.query.all()
    stats = {
        'total_users': len(users),
        'total_doctors': len(doctors),
        'total_appointments': len(appointments),
        'scheduled_appointments': len([a for a in appointments if a.status == 'scheduled'])
    }
    return render_template('admin_dashboard.html', users=users, doctors=doctors, appointments=appointments, stats=stats)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        reason = request.form['reason']
        appointment = Appointment(
            patient_id=session['user_id'],
            doctor_id=doctor_id,
            date=date,
            reason=reason
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment booked successfully! Confirmation sent.', 'success')
        return redirect(url_for('patient_dashboard'))
    doctors = User.query.filter_by(role='doctor').all()
    availabilities = {d.id: Availability.query.filter_by(doctor_id=d.id).all() for d in doctors}
    return render_template('book_appointment.html', doctors=doctors, availabilities=availabilities)

@app.route('/cancel_appointment/<int:id>')
def cancel_appointment(id):
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(id)
    if appointment.patient_id != session['user_id']:
        flash('Unauthorized action', 'error')
        return redirect(url_for('patient_dashboard'))
    appointment.status = 'cancelled'
    db.session.commit()
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/manage_appointment/<int:id>/<action>')
def manage_appointment(id, action):
    app.logger.info(f"Received manage_appointment request: id={id}, action={action}, user_role={session.get('role')}")
    if 'user_id' not in session or session['role'] not in ['doctor', 'admin']:
        app.logger.warning("Unauthorized access attempt to manage_appointment")
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(id)
    if session['role'] == 'doctor' and appointment.doctor_id != session['user_id']:
        app.logger.warning("Unauthorized doctor tried to manage appointment")
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor_dashboard'))
    if action in ['complete', 'cancel']:
        appointment.status = 'completed' if action == 'complete' else 'cancelled'
        db.session.commit()
        app.logger.info(f"Appointment {id} status changed to {appointment.status}")
        flash(f'Appointment {action}d successfully', 'success')
    else:
        app.logger.warning(f"Invalid action {action} on appointment {id}")
    return redirect(url_for('doctor_dashboard' if session['role'] == 'doctor' else 'admin_dashboard'))

@app.route('/manage_availability', methods=['GET', 'POST'])
def manage_availability():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    if request.method == 'POST':
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        availability = Availability(
            doctor_id=session['user_id'],
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(availability)
        db.session.commit()
        flash('Availability added successfully', 'success')
        return redirect(url_for('doctor_dashboard'))
    return render_template('manage_availability.html')

@app.route('/admin_manage_user', methods=['GET', 'POST'])
def admin_manage_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(user)
            db.session.commit()
            flash('User added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_manage_user.html')

@app.route('/admin_edit_user/<int:id>', methods=['GET', 'POST'])
def admin_edit_user(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:
            user.password_hash = generate_password_hash(request.form['password'])
        user.role = request.form['role']
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin_delete_user/<int:id>')
def admin_delete_user(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# API Routes
class RegisterAPI(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')
        if not username or not password or not role:
            return {'message': 'Missing required fields'}, 400
        if User.query.filter_by(username=username).first():
            return {'message': 'Username already exists'}, 400
        if role not in ['patient', 'doctor']:
            return {'message': 'Invalid role'}, 400
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        return {'message': 'User registered successfully'}, 201

class LoginAPI(Resource):
    def post(self):
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            if not username or not password:
                return {'message': 'Username and password are required'}, 400
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                token = jwt.encode({
                    'username': user.username,
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, app.config['JWT_SECRET_KEY'], algorithm="HS256")
                return {'token': token, 'role': user.role}, 200
            return {'message': 'Invalid credentials'}, 401
        except Exception as e:
            app.logger.error(f"Error in LoginAPI: {str(e)}")
            return {'message': f'Server error: {str(e)}'}, 500

class DoctorsAPI(Resource):
    @token_required
    def get(self, current_user):
        doctors = User.query.filter_by(role='doctor').all()
        return [{
            'id': doctor.id,
            'username': doctor.username,
            'availabilities': [{
                'start_time': a.start_time.isoformat(),
                'end_time': a.end_time.isoformat()
            } for a in Availability.query.filter_by(doctor_id=doctor.id).all()]
        } for doctor in doctors], 200

class AppointmentAPI(Resource):
    @token_required
    def post(self, current_user):
        if current_user.role != 'patient':
            return {'message': 'Unauthorized'}, 403
        data = request.get_json()
        doctor_id = data.get('doctor_id')
        date = datetime.fromisoformat(data.get('date'))
        reason = data.get('reason')
        appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            date=date,
            reason=reason
        )
        db.session.add(appointment)
        db.session.commit()
        return {'message': 'Appointment booked successfully'}, 201
    
    @token_required
    def get(self, current_user):
        if current_user.role == 'patient':
            appointments = Appointment.query.filter_by(patient_id=current_user.id).all()
        elif current_user.role == 'doctor':
            appointments = Appointment.query.filter_by(doctor_id=current_user.id).all()
        else:
            return {'message': 'Unauthorized'}, 403
        return [{
            'id': a.id,
            'patient': User.query.get(a.patient_id).username,
            'doctor': User.query.get(a.doctor_id).username,
            'date': a.date.isoformat(),
            'reason': a.reason,
            'status': a.status
        } for a in appointments], 200

class AvailabilityAPI(Resource):
    @token_required
    def post(self, current_user):
        if current_user.role != 'doctor':
            return {'message': 'Unauthorized'}, 403
        data = request.get_json()
        start_time = datetime.fromisoformat(data.get('start_time'))
        end_time = datetime.fromisoformat(data.get('end_time'))
        availability = Availability(
            doctor_id=current_user.id,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(availability)
        db.session.commit()
        return {'message': 'Availability added successfully'}, 201

# Register API routes
api.add_resource(RegisterAPI, '/api/register')
api.add_resource(LoginAPI, '/api/login')
api.add_resource(DoctorsAPI, '/api/doctors')
api.add_resource(AppointmentAPI, '/api/appointments')
api.add_resource(AvailabilityAPI, '/api/availability')

# New API resource to get all users (doctors and patients)
class UsersAPI(Resource):
    @token_required
    def get(self, current_user):
        if current_user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
        users = User.query.all()
        return [{
            'id': user.id,
            'username': user.username,
            'role': user.role
        } for user in users], 200

# API resource to update or delete a user by ID
class UserAPI(Resource):
    @token_required
    def put(self, current_user, user_id):
        if current_user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
        user = User.query.get(user_id)
        if not user:
            return {'message': 'User not found'}, 404
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')
        if username:
            user.username = username
        if password:
            user.password_hash = generate_password_hash(password)
        if role:
            user.role = role
        db.session.commit()
        return {'message': 'User updated successfully'}, 200

    @token_required
    def delete(self, current_user, user_id):
        if current_user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
        user = User.query.get(user_id)
        if not user:
            return {'message': 'User not found'}, 404
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted successfully'}, 200

api.add_resource(UsersAPI, '/api/users')
api.add_resource(UserAPI, '/api/users/<int:user_id>')

# Create database and initialize admin user
with app.app_context():
    db.create_all()
    init_admin_user()

if __name__ == '__main__':
    app.run(debug=True)
