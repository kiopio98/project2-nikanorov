"""Операции с таблицами и записями."""

from primitive_db.constants import ID_COLUMN, ID_DEFINITION, VALID_TYPES
from primitive_db.utils import remove_table_data, validate_name


def get_schema(metadata, table_name):
    """Проверить таблицу и вернуть словарь её столбцов."""
    validate_name(table_name)
    if table_name not in metadata:
        raise KeyError(table_name)
    return dict(column.split(":") for column in metadata[table_name])


def create_table(metadata, table_name, columns):
    """Добавить таблицу с обязательным автоматическим ID."""
    validate_name(table_name)
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует.')
    if not columns:
        raise ValueError("Укажите хотя бы один столбец.")
    names = {ID_COLUMN.casefold()}
    definitions = [ID_DEFINITION]
    for column in columns:
        parts = column.split(":")
        if len(parts) != 2:
            raise ValueError(f"Некорректный столбец: {column}.")
        name, data_type = parts
        validate_name(name)
        if name.casefold() in names:
            raise ValueError(f"Повторяющийся или зарезервированный столбец: {name}.")
        if data_type not in VALID_TYPES:
            raise ValueError(f"Неизвестный тип: {data_type}.")
        names.add(name.casefold())
        definitions.append(column)
    metadata[table_name] = definitions
    return metadata


def drop_table(metadata, table_name):
    """Удалить схему таблицы и её файл данных."""
    get_schema(metadata, table_name)
    remove_table_data(table_name)
    del metadata[table_name]
    return metadata
