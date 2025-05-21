from rest_framework import serializers, views
from rest_framework.response import Response
import requests

API_BASE = 'http://localhost:5000/api'

class BookSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=200)
    author = serializers.CharField(max_length=100)
    price = serializers.FloatField()
    stock = serializers.IntegerField()
    image = serializers.ImageField(required=False)

class OrderItemSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.FloatField()

class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField()
    total = serializers.FloatField(read_only=True)
    timestamp = serializers.CharField(read_only=True)
    items = OrderItemSerializer(many=True)

class BookListCreateView(views.APIView):
    def get(self, request):
        response = requests.get(f'{API_BASE}/books')
        if response.status_code == 200:
            return Response(response.json())
        return Response({'error': 'Failed to fetch books'}, status=response.status_code)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            response = requests.post(f'{API_BASE}/books', json=serializer.validated_data)
            if response.status_code == 201:
                return Response(response.json(), status=201)
            return Response({'error': 'Failed to add book'}, status=response.status_code)
        return Response(serializer.errors, status=400)

class BookDetailView(views.APIView):
    def put(self, request, pk):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            response = requests.put(f'{API_BASE}/books/{pk}', json=serializer.validated_data)
            if response.status_code == 200:
                return Response(response.json())
            return Response({'error': 'Failed to update book'}, status=response.status_code)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        response = requests.delete(f'{API_BASE}/books/{pk}')
        if response.status_code == 200:
            return Response(response.json())
        return Response({'error': 'Failed to delete book'}, status=response.status_code)

class OrderListCreateView(views.APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')
        url = f'{API_BASE}/orders' + (f'?user_id={user_id}' if user_id else '')
        response = requests.get(url)
        if response.status_code == 200:
            return Response(response.json())
        return Response({'error': 'Failed to fetch orders'}, status=response.status_code)

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            response = requests.post(f'{API_BASE}/orders', json=serializer.validated_data)
            if response.status_code == 201:
                return Response(response.json(), status=201)
            return Response({'error': 'Failed to create order'}, status=response.status_code)
        return Response(serializer.errors, status=400)