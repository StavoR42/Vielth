# coding: utf-8
import json
from threading import Thread

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from chat_app.api import thread_loop_init
from chat_app.helpers import settings_check
from chat_app.enums import SettingsEnum

THREAD = None


def main(request):
    return HttpResponseRedirect(reverse('vielth:connect'))


def connect(request):
    check_result = settings_check()
    context = {}

    if check_result:
        template = 'vielth_app/connect.html'
        context['channel_name'] = SettingsEnum.get_setting(SettingsEnum.DEFAULT_CHANNEL)
    else:
        template = 'vielth_app/settings_error.html'

    return render(request, template, context)


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


def save_channel_name(request):
    if request.method == 'POST':
        try:
            channel_name = request.POST.get('channel_name', '')
            SettingsEnum.save_setting(SettingsEnum.DEFAULT_CHANNEL, channel_name)
            return HttpResponse(json.dumps({'status': 'success', 'message': ''}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 'error', 'message': e}))

    else:
        return HttpResponse(json.dumps({'status': 'not_post', 'message': ''}))
