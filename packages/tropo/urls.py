from django.conf.urls import url
from tropo.views import tropo_outcall_session_create

urlpatterns = [
    url(r'^api.tropo.com/1.0/sessions/$', tropo_outcall_session_create, name='create_outcall_session'),
]
