from django.urls import path
from . import views

app_name = "gso_reports"

urlpatterns = [
    path('accomplishment/', views.accomplishment_report, name='accomplishment_report'),
    path("ipmt/save/", views.save_ipmt, name="save_ipmt"),  # save edited IPMT rows
    path('ipmt/generate/', views.generate_ipmt, name='generate_ipmt'),
    path("ipmt/preview/", views.preview_ipmt, name="preview_ipmt"),
    path('war-description/<int:war_id>/', views.get_war_description, name='get_war_description'),

    #kasama sa 10/28/25 edits#
    path("update-success-indicator/", views.update_success_indicator, name="update_success_indicator"),

    path('gso', views.gso_analytics, name='gso_analytics'),

    path("feedback-reports/", views.feedback_reports, name="feedback_reports"),

]
