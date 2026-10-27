"""Обработка ошибок, подтверждение действий, время и кэш."""

import time

import prompt


def preserve_metadata(wrapper, function):
    """Сохранить имя и документацию обёрнутой функции."""
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    wrapper.__wrapped__ = function
    return wrapper


def handle_db_errors(function):
    """Вывести понятное сообщение вместо аварийного завершения."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except FileNotFoundError:
            print("Ошибка: файл данных не найден. Возможно, база не инициализирована.")
        except KeyError as error:
            print(f"Ошибка: таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлом: {error}")
        return None

    return preserve_metadata(wrapper, function)


def confirm_action(action_name):
    """Запросить подтверждение перед опасной операцией."""

    def decorator(function):
        def wrapper(*args, **kwargs):
            answer = prompt.string(
                f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: '
            )
            if answer.strip().lower() != "y":
                print("Операция отменена.")
                return None
            return function(*args, **kwargs)

        return preserve_metadata(wrapper, function)

    return decorator


def log_time(function):
    """Измерить длительность выполнения монотонными часами."""

    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return function(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            print(f"Функция {function.__name__} выполнилась за {elapsed:.3f} секунд.")

    return preserve_metadata(wrapper, function)


def create_cacher():
    """Вернуть функцию доступа к словарю, сохранённому в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        """Вычислить результат только при отсутствии ключа в кэше."""
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    return cache_result
