// Event Booking Form Validation
document.addEventListener('DOMContentLoaded', function() {
    const bookingForms = document.querySelectorAll('.booking-form');
    
    bookingForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.textContent = 'Booking...';
        });
    });

    // Initialize rating inputs
    const ratingInputs = document.querySelectorAll('.rating-input');
    ratingInputs.forEach(input => {
        input.addEventListener('change', function() {
            updateStarRating(this);
        });
    });
});

// Star Rating Display
function updateStarRating(input) {
    const stars = input.parentElement.querySelectorAll('.star');
    const rating = parseInt(input.value);
    
    stars.forEach((star, index) => {
        if (index < rating) {
            star.textContent = '★';
            star.classList.add('active');
        } else {
            star.textContent = '☆';
            star.classList.remove('active');
        }
    });
}

// Alert Auto-dismiss
window.setTimeout(function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
    });
}, 3000);

// Event Search and Filter
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('event-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterEvents(this.value.toLowerCase());
        });
    }
});

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
    const password = form.querySelector('input[name="password"]');
    const confirmPassword = form.querySelector('input[name="confirm_password"]');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
        alert('Passwords do not match!');
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
            alert('Event date must be in the future');
            highlightError(dateInput);
            isValid = false;
        }
    }

    if (capacityInput && parseInt(capacityInput.value) < 1) {
        alert('Capacity must be at least 1');
        highlightError(capacityInput);
        isValid = false;
    }

    if (priceInput && parseFloat(priceInput.value) < 0) {
        alert('Price cannot be negative');
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

// Flash Messages
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// Dynamic Content Loading
function loadEventDetails(eventId) {
    fetch(`/api/events/${eventId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateEventDetails(data.event);
            } else {
                showAlert('Error loading event details', 'danger');
            }
        })
        .catch(error => {
            showAlert('Error loading event details', 'danger');
        });
}

function updateEventDetails(event) {
    const detailsContainer = document.getElementById('event-details');
    if (!detailsContainer) return;

    // Update event information
    const elements = {
        'event-name': event.name,
        'event-date': new Date(event.date).toLocaleString(),
        'event-location': event.location,
        'event-description': event.description,
        'event-capacity': event.capacity,
        'event-available': event.available_seats,
        'event-price': event.price ? `$${event.price.toFixed(2)}` : 'Free'
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

// Booking Management
function bookEvent(eventId) {
    fetch(`/api/events/${eventId}/book`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Event booked successfully!', 'success');
            setTimeout(() => {
                window.location.href = '/bookings';
            }, 2000);
        } else {
            showAlert(data.message || 'Error booking event', 'danger');
        }
    })
    .catch(error => {
        showAlert('Error booking event', 'danger');
    });
}

function cancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) return;

    fetch(`/api/bookings/${bookingId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Booking cancelled successfully', 'success');
            location.reload();
        } else {
            showAlert(data.message || 'Error cancelling booking', 'danger');
        }
    })
    .catch(error => {
        showAlert('Error cancelling booking', 'danger');
    });
}

// Review Management
function submitReview(eventId) {
    const form = document.getElementById('review-form');
    if (!form) return;

    const rating = form.querySelector('input[name="rating"]:checked');
    const content = form.querySelector('textarea[name="content"]');

    if (!rating || !content.value.trim()) {
        showAlert('Please provide both rating and review content', 'warning');
        return;
    }

    fetch(`/api/events/${eventId}/review`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            rating: rating.value,
            content: content.value.trim()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Review submitted successfully', 'success');
            location.reload();
        } else {
            showAlert(data.message || 'Error submitting review', 'danger');
        }
    })
    .catch(error => {
        showAlert('Error submitting review', 'danger');
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

    // Initialize any date inputs to have a minimum date of today
    const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
    dateInputs.forEach(input => {
        const now = new Date();
        const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                                .toISOString()
                                .slice(0, 16);
        input.min = localDateTime;
    });

    // Initialize rating stars if they exist
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
});