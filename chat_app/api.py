# coding: utf-8
import datetime
import json
import select
from threading import currentThread

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from transliterate import translit

from chat_app.helpers import connection
from chat_app.models import Message, ExtendedEAVSetting as Setting, Channel
from chat_app.enums import BracesDict, ReasonsEnum, SettingsEnum, ModerationActionsEnum
from chat_app.illegal_words import ILLEGAL_WORDS
from chat_app.command import CommandManager

PING = 'PING'
PONG = 'PONG'


########################################################################################################################


class MsgSender(object):
    """Класс, отвечающий за отправку сообщений"""
    def __init__(self, twitch_socket, channel_name):
        super().__init__()
        self.twitch_socket = twitch_socket
        self.channel_name = channel_name

    def send_message(self, message):
        """Отправка сообщения в чат канала"""
        self.twitch_socket.send(bytes(f'PRIVMSG #{self.channel_name} :{message}\r\n'.encode()))

    def pong(self, response):
        """Ответ на пинг твича"""
        self.twitch_socket.send(bytes(f'{PONG} {response}\r\n'.encode()))

    def get_mods(self):
        """Получить имена модераторов"""
        self.send_message('/mods')

    def disconnect(self):
        """Команда на отключение от сервера чата"""
        self.send_message('/disconnect')

    # инструменты для модерации
    def timeout(self, username, seconds=600):
        """Команда на таймаут"""
        timeout = ModerationActionsEnum.TIMEOUT
        self.send_message(f'/{timeout} {username} {seconds}')

    def purge(self, username):
        """Команда на пурж. Пурж - внутренне понятие, на самом деле это таймаут на 1 секунду"""
        self.timeout(username, 1)

    def ban(self, username):
        """Команда на бан"""
        ban = ModerationActionsEnum.BAN
        self.send_message(f'/{ban} {username}')

    def unban(self, username):
        """Команда на анбан"""
        unban = ModerationActionsEnum.UNBAN
        self.send_message(f'/{unban} {username}')


########################################################################################################################


class MsgValidator(object):
    """Абстрактный класс валидатора"""
    def validate(self, message):
        """Общий метод валидации, возвращает кортеж (проверка пройдена, причина)"""
        raise NotImplementedError()


class BracesValidator(MsgValidator):
    """Валидатор на скобки"""
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
        # подсчет количества открывающихся и закрывающихся скобок
        count_validation_result = self._validate_braces_count(message)
        if count_validation_result:
            return True, None

        # смотрим на предмет исключений
        index_validation_result = self._validate_braces_index(message)
        if index_validation_result:
            return True, None

        return False, ReasonsEnum.BRACES

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


class IllegalWordsValidator(MsgValidator):
    """Валидатор на запрещенные слова"""
    keymap_dict = {
        'q': 'й',
        'w': 'ц',
        'e': 'у',
        'r': 'к',
        't': 'е',
        'y': 'н',
        'u': 'г',
        'i': 'ш',
        'p': 'з',
        '[': 'х',
        ']': 'ъ',
        'a': 'ф',
        's': 'ы',
        'd': 'в',
        'g': 'п',
        'h': 'р',
        'j': 'о',
        'k': 'л',
        'l': 'д',
        ';': 'ж',
        "'": 'э',
        'z': 'я',
        'x': 'ч',
        'c': 'с',
        'v': 'м',
        'b': 'и',
        'n': 'т',
        'm': 'ь',
        ',': 'б',
        '.': 'ю',
    }

    def validate(self, message):
        original = message
        traslitted = translit(message, 'ru')
        keymapped = message.translate(str.maketrans(self.keymap_dict))

        # для ускорения проверки слепим все три результата в одну строку
        mess = ' '.join((original, traslitted, keymapped))

        if any(word in mess for word in ILLEGAL_WORDS):
            return False, ReasonsEnum.ILLEGAL_WORD

        return True, None


########################################################################################################################


class Connection(object):
    MOTD = False
    twitch_socket = None

    def __init__(self, twitch_socket, msg_sender, validators):
        super().__init__()
        self.twitch_socket = twitch_socket
        self.msg_sender = msg_sender
        self.validators = validators

        self.channel_name = msg_sender.channel_name
        self.channel, _ = Channel.objects.get_or_create(channel_name=self.channel_name)
        self.moderators = []
        self.is_owner = settings.NICK == self.channel_name
        self.is_mod = settings.NICK.lower() in self.moderators or self.is_owner

        self._start_loop()
    
    def _start_loop(self):
        # подключение к вебсокетам
        websocket = get_channel_layer()

        # получаем тред, в котором крутится твич сокет, чтобы прокидывать флаг отключения
        t = currentThread()

        # инициализация центра комманд
        command_centre = CommandManager()

        readbuffer = ''
        twitch_socket = self.twitch_socket

        # настройка сохранения сообщений в бд
        save_messages = Setting.objects.filter(setting_name='save_messages').first()
        if save_messages:
            save_messages = save_messages.setting_switch

        while getattr(t, 'do_run', True):
            r, _, _ = select.select([twitch_socket], [], [])
            if r:
                # обработка пришедшего сообщения
                readbuffer = readbuffer + twitch_socket.recv(4096).decode()
                temp = readbuffer.split('\n')
                readbuffer = temp.pop()

                for line in temp:
                    # ответка твичу на пинг
                    if line[0] == PING:
                        self.msg_sender.pong(line[1])
                        continue

                    # парсинг строки
                    parts = line.split(':')
                    stop_commands = ('QUIT', 'JOIN', 'PART')
                    process_condition = all((
                        command not in parts[1] for command in stop_commands
                    ))

                    if process_condition:
                        username, message = self._process_incoming(parts)
                        if self.MOTD:
                            print(f'{username}: {message}')

                            # сохранение сообщений
                            db_message_id = None
                            if save_messages and (username and message):
                                db_message = Message.objects.create(
                                    channel=self.channel,
                                    username=username,
                                    message=message
                                )
                                db_message_id = db_message.pk

                            # валидация (напр. на скобки)
                            is_valid = True
                            reason = None

                            # проверяем, команда ли пришла
                            command_centre.resolve_command(username, message, self.msg_sender)

                            if self.is_mod or SettingsEnum.get_setting(SettingsEnum.ALWAYS_VALIDATE):
                                for validator in self.validators:
                                    is_valid, reason = validator.validate(message)
                                    if not is_valid:
                                        break

                            # отправка сообщения на страницу через вебсокет
                            _now = datetime.datetime.now().strftime('%H:%M:%S')
                            async_to_sync(websocket.group_send)(
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
                                        'db_message_id': db_message_id,
                                        'is_mod': self.is_mod,
                                    }, ensure_ascii=False)
                                })

                        self._motd_pass(parts)

        self.msg_sender.disconnect()

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

    def _get_mods(self):
        mods_line = self.msg_sender.get_mods()
        # TODO: должен быть список модеров
        return []

    def _motd_pass(self, parts):
        """
        Первое сообщение от твича при коннекте - MOTD (Message of the Day),
        необходимо обработать его первым прежде чем работать с чатом
        """
        for l in parts:
            if 'End of /NAMES list' in l:
                self.MOTD = True

        # тут получим список модераторов
        self.moderators = self._get_mods()


def thread_loop_init(channel_name):
    """Функция, запускающая сокет. Предназначена для использования в отдельном треде (иначе приложение повиснет)"""
    with connection(channel_name) as twitch_socket:
        msg_sender = MsgSender(twitch_socket, channel_name)
        # для использования возможности посылания сообщений из мэйн треда
        # возможно надо будет переделать
        t = currentThread()
        t.msg_sender = msg_sender

        Connection(twitch_socket, msg_sender, validators=(BracesValidator, ))



