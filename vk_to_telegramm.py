# -*- coding: utf-8 -*-

import os
import sys
import vk_api
import telebot
import configparser
import logging
from telebot.types import InputMediaPhoto
from time import sleep

# Считываем настройки
config_path = os.path.join(sys.path[0], 'settings.ini')
config = configparser.ConfigParser()
config.read(config_path)
LOGIN = config.get('VK', 'LOGIN')
PASSWORD = config.get('VK', 'PASSWORD')
DOMAIN = config.get('VK', 'DOMAIN')
COUNT = config.get('VK', 'COUNT')
VK_TOKEN = config.get('VK', 'TOKEN', fallback=None)
BOT_TOKEN = config.get('Telegram', 'BOT_TOKEN')
CHANNEL = config.get('Telegram', 'CHANNEL')

# Инициализируем телеграмм бота
bot = telebot.TeleBot(BOT_TOKEN)

def two_factor():
    code = input('код:')
    return code

# Получаем данные из vk.com
def get_data(domain_vk, count_vk):
    global LOGIN
    global PASSWORD
    global VK_TOKEN
    global config
    global config_path

    if VK_TOKEN is not None:
        vk_session = vk_api.VkApi(LOGIN, PASSWORD, VK_TOKEN, auth_handler=two_factor)
        vk_session.auth(token_only=True)
    else:
        vk_session = vk_api.VkApi(LOGIN, PASSWORD)
        vk_session.auth()

    new_token = vk_session.token['access_token']
    if VK_TOKEN != new_token:
        VK_TOKEN = new_token
        config.set('VK', 'TOKEN', new_token)
        with open(config_path, "w") as config_file:
            config.write(config_file)

    vk = vk_session.get_api()
    # Используем метод wall.get из документации по API vk.com
    response = vk.wall.get(domain=domain_vk, count=count_vk)
    return response


# Проверяем данные по условиям перед отправкой
def check_posts_vk():
    global DOMAIN
    global COUNT
    global bot
    global config
    global config_path

    response = get_data(DOMAIN, COUNT)
    response = reversed(response['items'])

    for post in response:

        # Читаем последний извесный id из файла
        id = config.get('Settings', 'LAST_ID')

        # Сравниваем id, пропускаем уже опубликованные
        if int(post['id']) <= int(id):
            continue

        print('------------------------------------------------------------------------------------------------')
        print(post)


        # Проверяем есть ли что то прикрепленное к посту
        images = []
        links = []
        attachments = []
        if 'attachments' in post:
            attach = post['attachments']
            for add in attach:
                if add['type'] == 'photo':
                    img = add['photo']
                    images.append(img)
                elif add['type'] == 'audio':
                    # Все аудиозаписи заблокированы везде, кроме оффицальных приложений
                    continue
                elif add['type'] == 'video':
                    video = add['video']
                    if 'player' in video:
                        links.append(video['player'])
                else:
                    for (key, value) in add.items():
                        if key != 'type' and 'url' in value:
                            attachments.append(value['url'])

        if len(images) > 0:
            image_urls = list(map(lambda img: max(
                img["sizes"], key=lambda size: size["type"])["url"], images))
            print(image_urls)
            bot.send_media_group(CHANNEL, map(
                lambda url: InputMediaPhoto(url), image_urls))

        # Записываем id в файл
        config.set('Settings', 'LAST_ID', str(post['id']))
        with open(config_path, "w") as config_file:
            config.write(config_file)


# Отправляем посты в телеграмм
# Изображения
def send_posts_img(img):
    global bot
    
    # Находим картинку с максимальным качеством
    url = max(img["sizes"], key=lambda size: size["type"])["url"]
    bot.send_photo(CHANNEL, url)


if __name__ == '__main__':
    check_posts_vk()
    while True:
        check_posts_vk()
        sleep(3600)
