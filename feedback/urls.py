from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('gui/', views.gui_phan_hoi, name='gui_phan_hoi'),
]