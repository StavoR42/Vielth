# coding: utf-8


class BaseEnumerate(object):
    """Абстрактный класс енума"""
    values = {}

    @classmethod
    def get_choices(cls):
        return ((k, v) for k, v in cls.values.items())


class BaseDict(object):
    """Абстрактный класс расширенного словаря"""
    # TODO: придумать применение, а то тупо чето
    pass


########################################################################################################################


class BracesDict(BaseDict):
    """Словарь со скобками"""
    BRACE_OPEN = '{'
    BRACE_CLOSE = '}'
    PARENTHESIS_OPEN = '('
    PARENTHESIS_CLOSE = ')'
    SQUARE_OPEN = '['
    SQUARE_CLOSE = ']'

    # все фигурные скобки
    BRACES = (BRACE_OPEN, BRACE_CLOSE)
    # все круглые скобки
    PARENTHESES = (PARENTHESIS_OPEN, PARENTHESIS_CLOSE)
    # все квадратные скобки
    SQUARES = (SQUARE_OPEN, SQUARE_CLOSE)

    # все открывающиеся скобки
    OPENERS = (BRACE_OPEN, PARENTHESIS_OPEN, SQUARE_OPEN)
    # все закрывающиеся скобки
    CLOSERS = (BRACE_CLOSE, PARENTHESIS_CLOSE, SQUARE_CLOSE)

    # все блядские скобки
    ALL = (BRACE_OPEN, BRACE_CLOSE, PARENTHESIS_OPEN, PARENTHESIS_CLOSE, SQUARE_OPEN, SQUARE_CLOSE)


class ReasonsEnum(BaseEnumerate):
    """Енум с причинами бана/таймаута"""
    BRACES = 'braces'
    ILLEGAL_WORD = 'illegal_word'

    values = {
        BRACES: 'скобки',
        ILLEGAL_WORD: 'запрещенные слова',
    }

    warning_values = {
        BRACES: '@{}, не ставь скобки, пожалуйста, правила под стримом. Действие: {}',
        ILLEGAL_WORD: '@{}, одно из слов в твоем сообщении запрещено правилами twitch.tv. Действие: {}',
    }


class ModerationActionsEnum(BaseEnumerate):
    """Енум с модераторским действием"""
    PURGE = 'purge'
    TIMEOUT = 'timeout'
    BAN = 'ban'
    UNBAN = 'unban'

    ban_actions = (
        PURGE,
        TIMEOUT,
        BAN,
    )

    values = {
        PURGE: 'Пурж',
        TIMEOUT: 'Таймаут',
        BAN: 'Пермабан',
        UNBAN: 'Разбан',
    }


class SettingsEnum(BaseEnumerate):
    """
    Енум с пользовательскими настройками. При первом старте проекта или после вайпа бд необходимо прогнать
        SettingsEnum.create_settings()
    для корректной работы.
    """
    AUTO_MODERATION = 'auto_moderation'  # автомодерация
    AUTO_WARNING = 'auto_warning'  # автоварнинги пользователям
    SAVE_MESSAGES = 'save_messages'  # сохранение сообщений в бд
    LOG_BANS = 'log_bans'  # логгирование банов/таймаутов
    ALWAYS_VALIDATE = 'always_validate'  # производить валидацию сообщений, даже если не модератор
    DEFAULT_CHANNEL = 'default_channel'  # канал, название которого автоматом подставится при коннекте

    # переключаемые настройки
    is_bool = (
        AUTO_MODERATION,
        AUTO_WARNING,
        SAVE_MESSAGES,
        LOG_BANS,
        ALWAYS_VALIDATE,
    )

    # настройки, предполагающие хранение строки
    is_string = (
        DEFAULT_CHANNEL,
    )

    # настройки, предполагающие хранение списка в виде строки с разделителем "|"
    is_list = ()

    # человеческие названия
    values = {
        AUTO_MODERATION: 'Автомодерация',
        AUTO_WARNING: 'Автоматические предупреждения при бане/таймауте',
        SAVE_MESSAGES: 'Сохранение сообщений в БД',
        LOG_BANS: 'Вести лог банов/таймаутов',
        ALWAYS_VALIDATE: 'Производить валидацию сообщений без статуса модератора',
        DEFAULT_CHANNEL: 'Название канала',
    }

    # дефолтные значения
    defaults = {
        AUTO_MODERATION: False,
        AUTO_WARNING: False,
        SAVE_MESSAGES: True,
        LOG_BANS: True,
        ALWAYS_VALIDATE: False,
        DEFAULT_CHANNEL: '',
    }

    @classmethod
    def save_setting(cls, setting_name, value=None):
        """Сохранение настройки"""
        # локальный импорт, чтобы не было цикличности
        from chat_app.models import ExtendedEAVSetting as Setting

        # не сохраняем, если нет в енуме
        if setting_name not in cls.values.keys():
            return

        if value is not None:
            is_default = False
            # проверяем на валидность
            bool_valid = value in (True, False) and setting_name in cls.is_bool
            string_valid = isinstance(value, str) and setting_name in cls.is_string
            list_valid = isinstance(value, list) and setting_name in cls.is_list
            if not any((bool_valid, string_valid, list_valid)):
                raise ValueError('Неверное значение для данной настройки!')
        else:
            is_default = True
            # задаем дефолтовое значение, если оно не было передано
            value = cls.defaults[setting_name]

        # сохраняем тип настройки для дальнейшего назначения в бд
        value_type = 'setting_switch' if setting_name in cls.is_bool else 'setting_value'

        setting = Setting.objects.filter(setting_name=setting_name).first()
        if not setting:
            setting = Setting()

        setting.setting_name = setting_name
        setting.setting_verbose_name = cls.values[setting_name]
        if not is_default and list_valid:
            # обработка списка
            setting.setting_values = value
        else:
            # для всего остального
            setattr(setting, value_type, value)
        setting.save()

    @classmethod
    def create_settings(cls, replace=False):
        """
        Создание всех настроек (с заменой или без)
        Удобно использовать на новом приложении, или после вайпа базы, также удобно создавать новые настройки, когда
            таковые появятся
        Обязательно к использованию, т. к. без настроек приложение крашнется. Стоит проверка на главной странице
        """
        # локальный импорт чтобы не было цикличности
        from chat_app.models import ExtendedEAVSetting as Setting

        # в случае замены считаем, что существующих настроек нет
        existing_setting_names = () if replace else Setting.objects.values_list('setting_name', flat=True)
        # в случае замены тащим все настройки; иначе - только те, которых нет в списке уже существующих
        iterator = cls.values.keys() if replace else filter(lambda x: x not in existing_setting_names, cls.values.keys())  # noqa

        # сохраняем настройки
        for setting_name in iterator:
            cls.save_setting(setting_name)

    @classmethod
    def get_setting(cls, setting_name):
        """Возвращает значение настройки"""
        # локальный импорт чтобы не было цикличности
        from chat_app.models import ExtendedEAVSetting as Setting

        setting = Setting.objects.filter(setting_name=setting_name).first()
        if not setting:
            return None

        # возвращаем значение в зависимости от типа настройки
        if setting_name in cls.is_bool:
            result = setting.setting_switch
        else:
            result = setting.setting_value

            # может быть это список
            if Setting.separator in result:
                result = setting.setting_values

        return result

