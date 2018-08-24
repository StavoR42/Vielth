from django.conf.urls import url

from chat_app import views

urlpatterns = [
    url(r'^$', views.main, name='main'),
    url(r'^connect/$', views.connect, name='connect'),
    url(r'^twitch-chat/$', views.chat, name='chat'),
    url(r'^disconnect/$', views.disconnect, name='disconnect'),
]
