// CSRF Token Management
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Form Validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            highlightError(field);
        } else {
            removeError(field);
        }
    });

    // Special validations based on form type
    if (formId === 'register-form') {
        isValid = validateRegistrationForm(form) && isValid;
    } else if (formId === 'create-event-form') {
        isValid = validateEventForm(form) && isValid;
    }

    return isValid;
}

function validateRegistrationForm(form) {
    const password = form.querySelector('input[name="password1"]');
    const confirmPassword = form.querySelector('input[name="password2"]');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
        showMessage('Passwords do not match!', 'error');
        highlightError(confirmPassword);
        return false;
    }
    
    return true;
}

function validateEventForm(form) {
    const dateInput = form.querySelector('input[name="date"]');
    const capacityInput = form.querySelector('input[name="capacity"]');
    const priceInput = form.querySelector('input[name="price"]');
    
    let isValid = true;

    if (dateInput) {
        const selectedDate = new Date(dateInput.value);
        const now = new Date();
        
        if (selectedDate <= now) {
            showMessage('Event date must be in the future', 'error');
            highlightError(dateInput);
            isValid = false;
        }
    }

    if (capacityInput && parseInt(capacityInput.value) < 1) {
        showMessage('Capacity must be at least 1', 'error');
        highlightError(capacityInput);
        isValid = false;
    }

    if (priceInput && parseFloat(priceInput.value) < 0) {
        showMessage('Price cannot be negative', 'error');
        highlightError(priceInput);
        isValid = false;
    }

    return isValid;
}

// Error Handling
function highlightError(element) {
    element.classList.add('is-invalid');
    const feedback = element.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.style.display = 'block';
    }
}

function removeError(element) {
    element.classList.remove('is-invalid');
    const feedback = element.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.style.display = 'none';
    }
}

// Message Display
function showMessage(message, level = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${level} alert-dismissible fade show`;
    messageDiv.role = 'alert';
    
    messageDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
        messagesContainer.appendChild(messageDiv);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }
}

// Dynamic Content Loading
function loadEventDetails(eventId) {
    fetch(`/api/events/${eventId}/`)
        .then(response => response.json())
        .then(data => {
            updateEventDetails(data);
        })
        .catch(error => {
            showMessage('Error loading event details', 'error');
        });
}

function updateEventDetails(event) {
    const detailsContainer = document.getElementById('event-details');
    if (!detailsContainer) return;

    // Update event information
    const elements = {
        'event-name': event.name,
        'event-date': formatDate(event.date),
        'event-location': event.location,
        'event-description': event.description,
        'event-capacity': event.capacity,
        'event-available': event.available_seats,
        'event-price': event.price ? `$${parseFloat(event.price).toFixed(2)}` : 'Free'
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

// Booking Management
function bookEvent(eventId) {
    fetch(`/api/events/${eventId}/book/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Event booked successfully!', 'success');
            setTimeout(() => {
                window.location.href = '/bookings/';
            }, 2000);
        } else {
            showMessage(data.message || 'Error booking event', 'error');
        }
    })
    .catch(error => {
        showMessage('Error booking event', 'error');
    });
}

function cancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) return;

    fetch(`/api/bookings/${bookingId}/cancel/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Booking cancelled successfully', 'success');
            location.reload();
        } else {
            showMessage(data.message || 'Error cancelling booking', 'error');
        }
    })
    .catch(error => {
        showMessage('Error cancelling booking', 'error');
    });
}

// Review Management
function submitReview(eventId) {
    const form = document.getElementById('review-form');
    if (!form) return;

    const rating = form.querySelector('input[name="rating"]:checked');
    const content = form.querySelector('textarea[name="content"]');

    if (!rating || !content.value.trim()) {
        showMessage('Please provide both rating and review content', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('rating', rating.value);
    formData.append('content', content.value.trim());

    fetch(`/api/events/${eventId}/review/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Review submitted successfully', 'success');
            location.reload();
        } else {
            showMessage(data.message || 'Error submitting review', 'error');
        }
    })
    .catch(error => {
        showMessage('Error submitting review', 'error');
    });
}

// Event Search and Filter
function filterEvents(searchTerm) {
    const eventCards = document.querySelectorAll('.event-card');
    
    eventCards.forEach(card => {
        const title = card.querySelector('.card-title').textContent.toLowerCase();
        const description = card.querySelector('.card-text').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// Date Formatting
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup form validation
    const forms = document.querySelectorAll('form[id]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this.id)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Initialize search functionality
    const searchInput = document.getElementById('event-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterEvents(this.value.toLowerCase());
        });
    }

    // Initialize date inputs
    const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
    dateInputs.forEach(input => {
        const now = new Date();
        const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                                .toISOString()
                                .slice(0, 16);
        input.min = localDateTime;
    });

    // Initialize rating stars
    const ratingInputs = document.querySelectorAll('.rating input[type="radio"]');
    ratingInputs.forEach(input => {
        input.addEventListener('change', function() {
            const container = this.closest('.rating');
            const stars = container.querySelectorAll('label');
            stars.forEach(star => star.classList.remove('active'));
            
            for (let i = 0; i < this.value; i++) {
                stars[i].classList.add('active');
            }
        });
    });

    // Auto-dismiss Django messages
    const messages = document.querySelectorAll('.alert');
    messages.forEach(message => {
        setTimeout(() => {
            message.remove();
        }, 5000);
    });
});