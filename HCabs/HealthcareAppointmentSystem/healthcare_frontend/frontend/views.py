from django.shortcuts import render, redirect
from django.contrib import messages
import requests
from django.views.decorators.http import require_POST

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            response = requests.post(
                'http://localhost:5000/api/login',
                json={'username': username, 'password': password}
            )
            if response.status_code == 200:
                data = response.json()
                request.session['jwt_token'] = data.get('token')
                request.session['role'] = data.get('role')
                if data.get('role') == 'patient':
                    return redirect('patient_dashboard')
                elif data.get('role') == 'doctor':
                    return redirect('doctor_dashboard')
                elif data.get('role') == 'admin':
                    return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid credentials')
        except requests.RequestException as e:
            messages.error(request, f'Error connecting to API: {str(e)}')
    return render(request, 'frontend/login.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        try:
            response = requests.post(
                'http://localhost:5000/api/register',
                json={'username': username, 'password': password, 'role': role}
            )
            if response.status_code == 201:
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('login')
            else:
                messages.error(request, response.json().get('message', 'Registration failed'))
        except requests.RequestException as e:
            messages.error(request, f'Error connecting to API: {str(e)}')
    return render(request, 'frontend/register.html')

def manage_availability(request):
    if 'jwt_token' not in request.session or request.session.get('role') != 'doctor':
        return redirect('login')
    if request.method == 'POST':
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        try:
            response = requests.post(
                'http://localhost:5000/api/availability',
                json={'start_time': start_time, 'end_time': end_time},
                headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
            )
            if response.status_code == 201:
                messages.success(request, 'Availability added successfully.')
            else:
                messages.error(request, f'Failed to add availability: {response.text}')
        except requests.RequestException as e:
            messages.error(request, f'Error connecting to API: {str(e)}')
        return redirect('manage_availability')
    return render(request, 'frontend/manage_availability.html')

def complete_appointment(request, appointment_id):
    if 'jwt_token' not in request.session or request.session.get('role') != 'doctor':
        return redirect('login')
    try:
        response = requests.get(
            f'http://localhost:5000/manage_appointment/{appointment_id}/complete',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            messages.success(request, 'Appointment marked as completed.')
        else:
            messages.error(request, 'Failed to complete appointment.')
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
    return redirect('doctor_dashboard')

def cancel_appointment(request, appointment_id):
    if 'jwt_token' not in request.session or request.session.get('role') != 'doctor':
        return redirect('login')
    try:
        response = requests.get(
            f'http://localhost:5000/manage_appointment/{appointment_id}/cancel',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            messages.success(request, 'Appointment cancelled.')
        else:
            messages.error(request, 'Failed to cancel appointment.')
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
    return redirect('doctor_dashboard')

def patient_dashboard(request):
    if 'jwt_token' not in request.session or request.session.get('role') != 'patient':
        return redirect('login')
    try:
        response = requests.get(
            'http://localhost:5000/api/appointments',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            appointments = response.json()
        else:
            messages.error(request, 'Failed to retrieve appointments.')
            appointments = []
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
        appointments = []
    return render(request, 'frontend/patient_dashboard.html', {'appointments': appointments})
def doctor_dashboard(request):
    if 'jwt_token' not in request.session or request.session.get('role') != 'doctor':
        return redirect('login')
    
    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    try:
        response = requests.get(
            'http://localhost:5000/api/admin/users',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            users = response.json()
        else:
            messages.error(request, 'Failed to retrieve users.')
            users = []
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
        users = []
    return render(request, 'frontend/admin_dashboard.html', {'users': users})

def admin_manage_user(request):
    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    try:
        response = requests.get(
            'http://localhost:5000/api/admin/users',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            users = response.json()
        else:
            messages.error(request, 'Failed to retrieve users.')
            users = []
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
        users = []
    return render(request, 'frontend/admin_manage_user.html', {'users': users})
def admin_edit_user(request, user_id):
    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    if request.method == 'POST':
        username = request.POST.get('username')
        role = request.POST.get('role')
        try:
            response = requests.put(
                f'http://localhost:5000/api/admin/users/{user_id}',
                json={'username': username, 'role': role},
                headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
            )
            if response.status_code == 200:
                messages.success(request, 'User updated successfully.')
                return redirect('admin_manage_user')
            else:
                messages.error(request, 'Failed to update user.')
        except requests.RequestException as e:
            messages.error(request, f'Error connecting to API: {str(e)}')
    else:
        try:
            response = requests.get(
                f'http://localhost:5000/api/admin/users/{user_id}',
                headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
            )
            if response.status_code == 200:
                user = response.json()
            else:
                messages.error(request, 'Failed to retrieve user details.')
                return redirect('admin_manage_user')
        except requests.RequestException as e:
            messages.error(request, f'Error connecting to API: {str(e)}')
            return redirect('admin_manage_user')
    return render(request, 'frontend/admin_edit_user.html', {'user': user})
from django.views.decorators.http import require_POST

@require_POST
def admin_delete_user(request, user_id):
    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    try:
        response = requests.delete(
            f'http://localhost:5000/api/users/{user_id}',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            messages.success(request, 'User deleted successfully.')
        else:
            messages.error(request, 'Failed to delete user.')
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
    return redirect('admin_manage_user')
    

    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    try:
        response = requests.delete(
            f'http://localhost:5000/api/admin/users/{user_id}',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            messages.success(request, 'User deleted successfully.')
        else:
            messages.error(request, 'Failed to delete user.')
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
    return redirect('admin_manage_user')
# Example for admin_dashboard view
def admin_dashboard(request):
    if 'jwt_token' not in request.session or request.session.get('role') != 'admin':
        return redirect('login')
    try:
        response = requests.get(
            'http://localhost:5000/api/users',
            headers={'Authorization': f'Bearer {request.session["jwt_token"]}'}
        )
        if response.status_code == 200:
            users = response.json()
        else:
            messages.error(request, 'Failed to retrieve users.')
            users = []
    except requests.RequestException as e:
        messages.error(request, f'Error connecting to API: {str(e)}')
        users = []
    return render(request, 'frontend/admin_dashboard.html', {'users': users})
