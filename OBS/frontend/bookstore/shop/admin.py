from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.safestring import mark_safe
from .models import Book
import requests

API_BASE = 'http://localhost:5000/api'

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'stock', 'book_image')
    list_filter = ('author',)
    search_fields = ('title', 'author')
    ordering = ('title',)
    readonly_fields = ('preview_image',)
    
    def book_image(self, obj):
        if obj.image:
            return 'Yes'
        return 'No'
    book_image.short_description = 'Has Image'
    
    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="150" height="150" style="object-fit: cover;" />')
        return '(No image)'
    preview_image.short_description = 'Image Preview'

    fieldsets = (
        (None, {
            'fields': ('title', 'author', 'price', 'stock')
        }),
        ('Image', {
            'fields': ('image', 'preview_image'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # Save the book to Django's db.sqlite3
        super().save_model(request, obj, form, change)
        # Sync with Flask's bookstore.db
        book_data = {
            'title': obj.title,
            'author': obj.author,
            'price': float(obj.price),
            'stock': obj.stock
        }
        try:
            if change:
                # Update existing book in Flask (requires book ID mapping)
                print(f"Updating book {obj.title} in Flask API (manual sync needed for ID)")
                # Note: Update requires Flask book ID, which isn't stored in Django.
                # For now, we'll log a message to manually update via API.
            else:
                # Add new book to Flask
                response = requests.post(f'{API_BASE}/books', json=book_data)
                if response.status_code == 201:
                    print(f"Book {obj.title} added to Flask API")
                else:
                    print(f"Failed to add book to Flask: {response.status_code}, {response.text}")
        except requests.RequestException as e:
            print(f"Error syncing book with Flask: {e}")

# Unregister the default User admin
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)