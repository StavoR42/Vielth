# coding: utf-8


from django.db import models


settings_list = [
    'auto_moderation',  # автомодерация
    'auto_warning',  # автоварнинги пользователям
    'save_messages',  # сохранение сообщений в бд
]


class Message(models.Model):
    username = models.CharField('Ник', max_length=200, blank=True, null=True)
    message = models.TextField('Сообщение', max_length=50000, blank=True, null=True)
    date = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


class ExtendedEAVSettings(models.Model):
    setting_name = models.CharField('Название', max_length=200)
    setting_verbose_name = models.CharField(
        'Человеческое название', max_length=400, blank=True, null=True)
    setting_switch = models.NullBooleanField('Переключатель', default=None)
    setting_value = models.CharField('Значение', max_length=1000, blank=True, null=True)

    separator = '|'

    class Meta:
        verbose_name = 'Настройка'
        verbose_name_plural = 'Настройки'

    # костыль для sqlite, на postgresql можно array_field прикрутить
    @property
    def setting_values(self):
        """
        Парсит строку из поля модели в список
        """
        return self.setting_value.split(self.separator)

    @setting_values.setter
    def setting_values(self, value):
        """
        Парсит пришедший список в строку для подставления в поле модели
        """
        value = self.separator.join(value)
        self.setting_value = value
