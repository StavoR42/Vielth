# coding: utf-8
import datetime
import json
import socket
import select
from threading import currentThread

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from models import Message, ExtendedEAVSettings as Settings
from enums import BracesDict

PING = 'PING'
PONG = 'PONG'


class MsgSender(object):
    @staticmethod
    def send_message(twitch_socket, message, channel_name):
        """Отправка сообщения в чат канала"""
        twitch_socket.send(bytes(f'PRIVMSG #{channel_name} :{message}\r\n'.encode()))

    @staticmethod
    def pong(twitch_socket, response):
        """Ответ на пинг твича"""
        twitch_socket.send(bytes(f'{PONG} {response}\r\n'.encode()))


class MsgValidator(object):
    # словарь со счетчиками скобок
    counters = {x: 0 for x in BracesDict.ALL}
    # индексы скобок в строке
    brace_indexes = []
    # возможные комбинации символов
    # внутренний кортеж: (символ для скобки слева, символ для скобки справа)
    possible_smile_combo_symbols = (
        (':', ':'),
        ('=', '='),
        ('-:', ':-'),
    )

    def validate(self, message):
        """Общий метод валидации, возвращает кортеж (проверка пройдена, причина)"""
        braces_result = self._validate_braces(message)
        if not braces_result:
            return False, 'braces'

        illegal_words_result = self._validate_illegal_words(message)
        if not illegal_words_result:
            return False, 'illegal_word'

        return True, None

    def _validate_braces(self, message):
        """Валидация на скобки"""
        count_validation_result = self._validate_braces_count(message)
        if count_validation_result:
            return True

        # смотрим на предмет исключений
        index_validation_result = self._validate_braces_index(message)

        return index_validation_result

    def _validate_braces_count(self, message):
        """Валидация по количеству скобок"""
        for idx, symbol in enumerate(filter(lambda x: x in BracesDict.ALL, message)):
            self.brace_indexes.append(idx)
            self.counters[symbol] += 1

        result = True
        for opener, closer in (BracesDict.BRACES, BracesDict.PARENTHESES, BracesDict.SQUARES):
            # сравниваем количество попарно. если неравно - помечаем на следующий этап валидации
            if self.counters[opener] != self.counters[closer]:
                result = False
                break

        return result

    def _validate_braces_index(self, message):
        """Проверка по исключениям. Примеры на основе круглых скобок"""
        is_exception = False
        for i in self.brace_indexes:
            # проверки на всякое :), )=, :-(
            for combo_left, combo_right in self.possible_smile_combo_symbols:
                # предполагается, что комбинации одинаковой длины
                if combo_left == combo_right:
                    # проверка любой скобки
                    if message[i - 1] == combo_left or message[i + 1] == combo_left:
                        is_exception = True
                        break

                else:
                    if (
                            message[i + 1:i + len(combo_left) + 1] == combo_left or
                            message[i - len(combo_right):i] == combo_right
                    ):
                        is_exception = True
                        break

            if not is_exception:
                # проверка на x)D
                if message[i - 1].lower() == 'x' and message[i + 1].lower() == 'd' and message[i] in BracesDict.CLOSERS:
                    is_exception = True

        return is_exception

    def _validate_illegal_words(self, message):
        """Валидация на запрещенные слова"""
        # TODO: реализовать с полным списком и транслитом
        return True


class Connection(object):
    MODT = False
    twitch_socket = None

    def __init__(self, msg_sender, channel_name):
        super().__init__()
        self.channel_name = channel_name
        self.msg_sender = msg_sender
        self._connect_to_server()
        self._start_loop()
    
    def _connect_to_server(self):
        """
        Подключение к IRC-серверу
        """
        twitch_socket = self.twitch_socket = socket.socket()
        twitch_socket.connect((settings.HOST, settings.PORT))
        twitch_socket.send(bytes(f'PASS {settings.PASS}\r\n'.encode()))
        twitch_socket.send(bytes(f'NICK {settings.NICK}\r\n'.encode()))
        twitch_socket.send(bytes(f'JOIN #{self.channel_name} \r\n'.encode()))

    def _start_loop(self):
        # подключение к вебсокетам
        channel_layer = get_channel_layer()

        # получаем тред, в котором крутится твич сокет, чтобы прокидывать флаг отключения
        t = currentThread()

        readbuffer = ''
        s = self.twitch_socket

        # настройка сохранения сообщений в бд
        save_messages = Settings.objects.filter(setting_name='save_messages').first()
        if save_messages:
            save_messages = save_messages.setting_switch

        while getattr(t, 'do_run', True):
            r, _, _ = select.select([s], [], [])
            if r:
                # обработка пришедшего сообщения
                readbuffer = readbuffer + s.recv(4096).decode()
                temp = readbuffer.split('\n')
                readbuffer = temp.pop()

                for line in temp:
                    # ответка твичу на пинг
                    if line[0] == PING:
                        self.msg_sender.pong(s, line[1])
                        continue

                    # парсинг строки
                    parts = line.split(':')
                    stop_commands = ('QUIT', 'JOIN', 'PART')
                    process_condition = all((
                        command not in parts[1] for command in stop_commands
                    ))

                    if process_condition:
                        username, message = self._process_incoming(parts)
                        if self.MODT:
                            print(f'{username}: {message}')

                            # сохранение сообщений
                            if save_messages:
                                Message.objects.create(
                                    username=username,
                                    message=message
                                )

                            # валидация (напр. на скобки)
                            is_valid, reason = MsgValidator().validate(message)

                            # отправка сообщения на страницу через вебсокет
                            _now = datetime.datetime.now().strftime('%H:%M:%S')
                            async_to_sync(channel_layer.group_send)(
                                settings.WEBSOCKET_CHANNEL,
                                {
                                    # название метода в классе консумера, в модуле consumers
                                    'type': 'chat_message',
                                    # отправляемое сообщение
                                    'message': json.dumps({
                                        'is_valid': is_valid,
                                        'reason': reason,
                                        'datetime': _now,
                                        'username': username,
                                        'message': message,
                                    }, ensure_ascii=False)
                                })

                        self.motd_pass(parts)

    @staticmethod
    def _process_incoming(parts):
        """
        Хаос какой-то, ему похуй, чё тут, сухарики или странный парсер строки (не мой)
        """
        try:
            message = parts[2][:len(parts[2]) - 1]
        except:
            message = ''

        usernamesplit = parts[1].split('!')
        username = usernamesplit[0]

        return username, message

    def motd_pass(self, parts):
        """
        Первое сообщение от твича при коннекте - MOTD (Message of the Day),
        необходимо обработать его первым прежде чем работать с чатом
        """
        for l in parts:
            if 'End of /NAMES list' in l:
                self.MODT = True


def thread_loop_init(channel_name):
    msg_sender = MsgSender()
    connection = Connection(msg_sender, channel_name)
    connection.twitch_socket.shutdown(socket.SHUT_RDWR)
    connection.twitch_socket.close()
    print('disconnected')
