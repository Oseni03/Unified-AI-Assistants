from django.urls import path

from . import views

from rest_framework import routers

app_name = "feedbacks"

router = routers.SimpleRouter()
router.register(r'', views.FeedBackViewset, basename="feedbacks")
urlpatterns = router.urls
