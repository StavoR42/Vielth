# coding: utf-8
import socket
from contextlib import contextmanager

from django.conf import settings

from enums import SettingsEnum
from models import ExtendedEAVSetting as Setting


@contextmanager
def connection(channel_name):
    """Менеджер контекста для подключения к каналу"""
    twitch_socket = socket.socket()
    twitch_socket.connect((settings.HOST, settings.PORT))
    twitch_socket.send(bytes(f'PASS {settings.PASS}\r\n'.encode()))
    twitch_socket.send(bytes(f'NICK {settings.NICK}\r\n'.encode()))
    twitch_socket.send(bytes(f'JOIN #{channel_name} \r\n'.encode()))
    print('connected')

    yield twitch_socket

    twitch_socket.shutdown(socket.SHUT_RDWR)
    twitch_socket.close()
    print('disconnected')


def settings_check():
    """Проверка на заполненность настроек"""
    return Setting.objects.count() == len(SettingsEnum.values.keys())
