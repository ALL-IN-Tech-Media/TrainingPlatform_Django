from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NeuralNetworkViewSet

router = DefaultRouter()
router.register(r'networks', NeuralNetworkViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
