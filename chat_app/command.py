# coding: utf-8

import datetime


class CommandManager(object):
    """Класс с командами. Для регистрации новой команды просто нужно добавить метод, начинающийся с _"""
    def resolve_command(self, username, message, msg_sender):
        """Опознать наличие команды и послать на выполнение"""
        # команда должна начинаться на "!" и быть одним словом, далее идут аргументы
        if not message.startswith('!'):
            return None

        message_as_list = message.split()
        command_method_str = message_as_list[0].replace('!', '_')
        args_list = message_as_list[1:]
        command_method = vars(self.__class__).get(command_method_str, None)

        command_method(username, args_list, msg_sender) if command_method else None

    def _artist(self, username, args_list, msg_sender):
        """
        !artist nickname
        Если counter раз за последние timeout минут какой-либо ник из чата будет использован с этой командой, он
        окажется в таймауте
        """
        # сетап
        if not getattr(self, 'artists_table'):
            self.artists_table = {}
        timeout = 5  # в минутах
        counter = 3  # количество ников в unique_callers, по достижению которого указанный артист отправляется в таймаут

        '''
        содержимое таблицы:
        {
          'nickname': {
               'unique_callers': [],  # список ников, которые уже пометили указанный как артиста
               'last_call_date': datetime.datetime.now(),  # дата последнего артистирования, нужна для таймаута
          }
        }
        '''
        artist = args_list[0]
        if artist not in self.artists_table:
            self.artists_table[artist] = {
                'unique_callers': set(),
                'last_call_time': datetime.datetime.now(),
            }

        else:
            # очистка списка если последнее артистирование было timeout минут назад или больше
            if self.artists_table[artist]['last_call_time'] - datetime.datetime.now() >= datetime.timedelta(minutes=timeout):  # noqa
                self.artists_table[artist]['unique_callers'] = set()

        if len(self.artists_table[artist]['unique_callers']) < counter:
            self.artists_table[artist]['unique_callers'].add(username)
            # если стало counter ников, высылаем таймаут
            if len(self.artists_table[artist]['unique_callers']) == counter:
                msg_sender.timeout(artist)
            # иначе обновляем таймер
            else:
                self.artists_table[artist]['last_call_time'] = datetime.datetime.now()

        # TODO протестировать
