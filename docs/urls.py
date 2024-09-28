from django.urls import path
from .views import chat_view, translate_text, translate_page_view

urlpatterns = [
    path('', chat_view, name='chat'),
    path('translate/', translate_text, name='translate'),
    path('translate_page/', translate_page_view, name='translate_page'),
    
]
