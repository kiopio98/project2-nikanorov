"""Хранение метаданных и записей в JSON."""

import json
import os

from primitive_db.constants import DATA_DIR, ENCODING


def validate_name(name):
    """Проверить имя таблицы или столбца."""
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f"Некорректное имя: {name}.")
    return name


def load_metadata(filepath):
    """Прочитать метаданные; отсутствие файла означает новую базу."""
    try:
        with open(filepath, encoding=ENCODING) as source:
            data = json.load(source)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Файл метаданных должен содержать объект JSON.")
    return data


def save_metadata(filepath, data):
    """Сохранить JSON через временный файл и атомарную замену."""
    directory = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(directory, exist_ok=True)
    temporary = f"{filepath}.tmp"
    try:
        with open(temporary, "w", encoding=ENCODING) as target:
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.write("\n")
        os.replace(temporary, filepath)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def table_path(table_name):
    """Получить путь к данным таблицы после проверки имени."""
    return os.path.join(DATA_DIR, f"{validate_name(table_name)}.json")


def load_table_data(table_name):
    """Прочитать записи; новая таблица содержит пустой список."""
    try:
        with open(table_path(table_name), encoding=ENCODING) as source:
            data = json.load(source)
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError("Файл таблицы должен содержать список записей.")
    return data


def save_table_data(table_name, data):
    """Сохранить все записи таблицы."""
    save_metadata(table_path(table_name), data)


def remove_table_data(table_name):
    """Удалить файл данных, если он существует."""
    filepath = table_path(table_name)
    if os.path.exists(filepath):
        os.remove(filepath)
