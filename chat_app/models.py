# coding: utf-8


from django.db import models

from chat_app.enums import ReasonsEnum, SettingsEnum


class Channel(models.Model):
    channel_name = models.CharField('Название канала', max_length=200)

    class Meta:
        verbose_name = 'Название канала'
        verbose_name_plural = 'Названия каналов'


class Message(models.Model):
    channel = models.ForeignKey(Channel, verbose_name='Канал')
    username = models.CharField('Ник', max_length=200, blank=True, null=True)
    message = models.TextField('Сообщение', max_length=50000, blank=True, null=True)
    date = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


class BanLog(models.Model):
    message = models.ForeignKey(Message, verbose_name='Сообщение, за которое забанили')
    ban_date = models.DateTimeField('Дата бана', auto_now_add=True)
    ban_type = models.CharField('Тип бана', choices=ReasonsEnum.get_choices(), max_length=20)

    class Meta:
        verbose_name = 'Лог бана'
        verbose_name_plural = 'Логи банов'


class ExtendedEAVSetting(models.Model):
    setting_name = models.CharField('Название', max_length=200, unique=True)
    setting_verbose_name = models.CharField(
        'Человеческое название', max_length=400, blank=True, null=True)
    setting_switch = models.NullBooleanField('Переключатель', default=None)
    setting_value = models.CharField('Значение', max_length=1000, blank=True, null=True)

    separator = '|'

    class Meta:
        verbose_name = 'Настройка'
        verbose_name_plural = 'Настройки'

    def save(self, *args, **kwargs):
        # ограничение сохранения только для настроек из енума
        if self.setting_name in SettingsEnum.values.keys():
            super().save(*args, **kwargs)

    # костыль для sqlite, на postgresql можно array_field прикрутить третьим полем
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
