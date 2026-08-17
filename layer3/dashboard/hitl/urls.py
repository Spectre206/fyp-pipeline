from django.urls import path
from . import views

urlpatterns = [
    path("", views.queue_view, name="queue"),
    path("<int:incident_id>/", views.incident_detail, name="detail"),
    path("<int:incident_id>/approve/", views.approve, name="approve"),
    path("<int:incident_id>/reject/", views.reject, name="reject"),
    path("<int:incident_id>/modify/", views.modify_form, name="modify_form"),
    path("<int:incident_id>/modify/submit/", views.modify_submit, name="modify_submit"),
]