import logging
import os
import time

from dotenv import load_dotenv
from http import HTTPStatus
import requests
import telegram


load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Отправка сообщения в чат: {message}')
    except telegram.TelegramError as error:
        logging.error(f'Сообщение не отправлено {error}')
    else:
        logging.info(f'Сообщение успешно отправлено в чат: {message}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logging.info('Начат запрос к API')
    except ConnectionError as error:
        logging.error(f'Ошибка {error}')
    if response.status_code != HTTPStatus.OK:
        raise Exception('Status_code != 200')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        raise TypeError('Тип данных не соответствует ожидаемому')
    if not isinstance(homeworks, list):
        raise Exception('Тип данных не соответствует ожидаемому')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ee статус."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')

    if 'homework_name' not in homework:
        raise KeyError('Некорректный ключ')

    if 'status' not in homework:
        raise KeyError('Некорректный ключ')

    if homework_status not in HOMEWORK_STATUSES:
        raise Exception('Некорректный статус')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    previous_timestamp = int(time.time()) - RETRY_TIME
    current_timestamp = int(time.time())
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(previous_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug(
                    'Новых статусов работы нет'
                )
                new_message = parse_status(homeworks[0])
                if new_message == message:
                    raise Exception('Сообщения одинаковые')
            previous_timestamp = current_timestamp
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
