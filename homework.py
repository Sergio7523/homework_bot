import logging
import os
import sys
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
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise Exception
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError
    if not response.get('homeworks'):
        raise Exception
    if not isinstance(response.get('homeworks'), list):
        raise Exception
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ee статус."""
    if 'homework_name' not in homework.keys():
        raise KeyError

    if homework.get('status') not in HOMEWORK_STATUSES.keys():
        raise Exception

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    if (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return True
    return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_timestamp = int(time.time()) - RETRY_TIME
    current_timestamp = int(time.time())
    tokens_status = check_tokens()
    while tokens_status:
        try:
            response = get_api_answer(previous_timestamp)
            homworks = check_response(response)
            if len(homworks) != 0:
                for homework in homworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                    logging.info(
                        f'Сообщение успешно отправлено в чат: {message}'
                    )
            else:
                logging.debug(
                    'Новых статусов работы нет'
                )
            previous_timestamp = current_timestamp
            time.sleep(RETRY_TIME)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)
        else:
            logging.critical(
                'Ошибка, завершение работы'
            )
            sys.exit()


if __name__ == '__main__':
    main()
