# coding: utf-8
from threading import Thread

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from chat_app.api import thread_loop_init, settings_check

THREAD = None


def main(request):
    return HttpResponseRedirect(reverse('vielth:connect'))


def connect(request):
    template = 'vielth_app/connect.html' if settings_check() else 'vielth_app/settings_error.html'
    return render(request, template, {})


def chat(request):
    global THREAD

    if isinstance(THREAD, Thread):
        return HttpResponseRedirect(reverse('vielth:disconnect'))

    if request.method == 'POST':
        channel_name = request.POST.get('channel_name', '')
        THREAD = Thread(target=thread_loop_init, args=(channel_name,))
        THREAD.daemon = True
        THREAD.start()
        return render(request, 'vielth_app/chat.html', {})

    else:
        return HttpResponseRedirect(reverse('vielth:connect'))


def disconnect(request):
    global THREAD

    THREAD.do_run = False
    THREAD.join()
    THREAD = None

    return HttpResponseRedirect(reverse('vielth:main'))
