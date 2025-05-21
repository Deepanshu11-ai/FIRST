from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from rest_framework import viewsets
import requests
from django.http import Http404
from .models import Event, Review, Booking, Query
from .forms import UserRegistrationForm, EventBookingForm, ReviewForm, QueryForm, EventForm
from .serializers import EventSerializer, ReviewSerializer, BookingSerializer, QuerySerializer

def fetch_flask_events():
    try:
        response = requests.get('http://127.0.0.1:5000/api/events')
        if response.status_code == 200:
            events = response.json()
            # Add source field to distinguish Flask events
            for event in events:
                event['source'] = 'flask'
            return events
    except requests.RequestException:
        return []
    return []

# Class-based views for REST API
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class QueryViewSet(viewsets.ModelViewSet):
    queryset = Query.objects.all()
    serializer_class = QuerySerializer

# Template Views
class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        # Get Django events and add source field
        django_events = list(Event.objects.all().values())
        for event in django_events:
            event['source'] = 'django'
        
        # Get Flask events
        flask_events = fetch_flask_events()
        
        # Combine both sets of events
        all_events = django_events + flask_events
        return sorted(all_events, key=lambda x: x.get('date', ''))

class EventDetailView(DetailView):
    template_name = 'event_detail.html'
    context_object_name = 'event'

    def get_object(self):
        event_id = self.kwargs.get('pk')
        # Try to get Django event first
        try:
            return Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            # If not found, try to get Flask event
            try:
                response = requests.get(f'http://127.0.0.1:5000/api/events/{event_id}')
                if response.status_code == 200:
                    event_data = response.json()
                    event_data['source'] = 'flask'
                    return type('FlaskEvent', (), event_data)
            except requests.RequestException:
                pass
        raise Http404("Event not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking_form'] = EventBookingForm()
        
        # Add user_has_booking to context
        if self.request.user.is_authenticated:
            event = self.object
            context['user_has_booking'] = False
            if isinstance(event, Event):  # Django event
                context['user_has_booking'] = Booking.objects.filter(
                    user=self.request.user, 
                    event=event
                ).exists()
                # Add reviews for Django events
                context['reviews'] = Review.objects.filter(event=event).select_related('user').order_by('-created_at')
                context['review_form'] = ReviewForm()
            else:  # Flask event
                try:
                    response = requests.get(
                        f'http://127.0.0.1:5000/api/bookings/check/{event.id}',
                        cookies={'session': self.request.COOKIES.get('session')}
                    )
                    if response.status_code == 200:
                        context['user_has_booking'] = response.json().get('has_booking', False)
                except requests.RequestException:
                    pass
                    
        return context

import requests
from django.conf import settings

@login_required
def profile(request):
    # Fetch Django bookings and reviews
    bookings = Booking.objects.filter(user=request.user)
    reviews = Review.objects.filter(user=request.user)

    # Fetch Flask bookings and reviews
    flask_bookings = []
    flask_reviews = []
    try:
        flask_bookings_response = requests.get(
            f'http://127.0.0.1:5000/api/bookings/user/{request.user.id}'
        )
        if flask_bookings_response.status_code == 200:
            flask_bookings = flask_bookings_response.json()
    except requests.RequestException:
        pass

    try:
        flask_reviews_response = requests.get(
            f'http://127.0.0.1:5000/api/reviews/user/{request.user.id}'
        )
        if flask_reviews_response.status_code == 200:
            flask_reviews = flask_reviews_response.json()
    except requests.RequestException:
        pass

    # Combine Django and Flask reviews and bookings
    combined_bookings = list(bookings.values()) + flask_bookings
    combined_reviews = list(reviews.values()) + flask_reviews

    return render(request, 'profile.html', {
        'bookings': combined_bookings,
        'reviews': combined_reviews
    })

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        messages.error(request, 'Invalid registration details')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def book_event(request, event_id):
    try:
        # Try to get Django event first
        event = Event.objects.get(id=event_id)
        is_flask_event = False
    except Event.DoesNotExist:
        # If not found, try to get Flask event
        try:
            response = requests.get(f'http://127.0.0.1:5000/api/events/{event_id}')
            if response.status_code == 200:
                event = response.json()
                is_flask_event = True
            else:
                raise Http404("Event not found")
        except requests.RequestException:
            messages.error(request, 'Unable to connect to event server')
            return redirect('home')

    if request.method == 'POST':
        booking_form = EventBookingForm(request.POST)
        if is_flask_event:
            # Book Flask event
            try:
                book_response = requests.post(
                    f'http://127.0.0.1:5000/event/{event_id}/book', 
                    json={'notes': booking_form.data.get('notes', '')},
                    cookies={'session': request.COOKIES.get('session')}
                )
                if book_response.status_code == 200:
                    messages.success(request, 'Event booked successfully!')
                    return redirect('user_bookings')
                else:
                    messages.error(request, 'Failed to book event')
            except requests.RequestException:
                messages.error(request, 'Unable to connect to event server')
        else:
            # Book Django event
            if Booking.objects.filter(user=request.user, event=event).exists():
                messages.warning(request, 'You have already booked this event!')
            elif event.book_seat():
                if booking_form.is_valid():
                    booking = Booking(
                        user=request.user, 
                        event=event,
                        notes=booking_form.cleaned_data.get('notes', '')
                    )
                    booking.save()
                    messages.success(request, 'Event booked successfully!')
                    return redirect('user_bookings')
                else:
                    messages.error(request, 'Invalid booking form')
            else:
                messages.error(request, 'No seats available for this event!')

    return redirect('home')

@login_required
def submit_review(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check for existing review
    if Review.objects.filter(user=request.user, event=event).exists():
        messages.warning(request, 'You have already reviewed this event!')
        return redirect('event_detail', pk=event_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.event = event
            review.save()
            messages.success(request, 'Review submitted successfully!')
        else:
            messages.error(request, 'Invalid review submission!')
    
    return redirect('event_detail', pk=event_id)

@login_required
def submit_query(request):
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query = form.save(commit=False)
            query.user = request.user
            query.save()
            messages.success(request, 'Query submitted successfully!')
            return redirect('profile')
    return redirect('index')

@login_required
def user_bookings(request):
    # Fetch Django bookings
    django_bookings = Booking.objects.filter(user=request.user).select_related('event')

    # Fetch Flask bookings
    flask_bookings = []
    try:
        flask_response = requests.get(
            f'http://127.0.0.1:5000/api/bookings/user/{request.user.id}'
        )
        if flask_response.status_code == 200:
            flask_bookings = flask_response.json()
    except requests.RequestException:
        pass

    # Combine Django and Flask bookings
    combined_bookings = []

    # Add Django bookings with source field
    for booking in django_bookings:
        combined_bookings.append({
            'id': booking.id,
            'event': {
                'id': booking.event.id,
                'name': booking.event.name,
                'date': booking.event.date,
                'location': booking.event.location,
                'capacity': booking.event.capacity,
                'available_seats': booking.event.available_seats,
                'price': booking.event.price,
                'source': 'django',
            },
            'booking_date': booking.booking_date,
            'notes': booking.notes,
            'status': booking.status,
            'source': 'django',
        })

    # Add Flask bookings with source field
    for booking in flask_bookings:
        # Assuming Flask booking JSON has similar fields
        booking['source'] = 'flask'
        combined_bookings.append(booking)

    return render(request, 'user_bookings.html', {
        'bookings': combined_bookings,
        'now': timezone.now(),
    })
