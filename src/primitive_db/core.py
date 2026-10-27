"""Операции с таблицами и записями."""

import json

from primitive_db.constants import ID_COLUMN, ID_DEFINITION, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data, remove_table_data, validate_name

_cache_select = create_cacher()


def get_schema(metadata, table_name):
    """Проверить таблицу и вернуть словарь её столбцов."""
    validate_name(table_name)
    if table_name not in metadata:
        raise KeyError(table_name)
    return dict(column.split(":") for column in metadata[table_name])


@handle_db_errors
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


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удалить схему таблицы и её файл данных."""
    get_schema(metadata, table_name)
    remove_table_data(table_name)
    del metadata[table_name]
    return metadata


def validate_fields(schema, fields, allow_id=True):
    """Проверить имена и точные типы значений по схеме."""
    for name, value in fields.items():
        if name not in schema:
            raise KeyError(name)
        if not allow_id and name == ID_COLUMN:
            raise ValueError("ID назначается автоматически и не изменяется.")
        if type(value) is not VALID_TYPES[schema[name]]:
            raise ValueError(f"Столбец {name}: ожидается {schema[name]}.")


def matches(row, where_clause):
    """Проверить равенство всех полей условия, различая bool и int."""
    return all(
        key in row and type(row[key]) is type(value) and row[key] == value
        for key, value in (where_clause or {}).items()
    )


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавить запись с автоматически назначенным ID."""
    schema = get_schema(metadata, table_name)
    columns = [name for name in schema if name != ID_COLUMN]
    if len(values) != len(columns):
        raise ValueError(f"Ожидается {len(columns)} значений без ID.")
    fields = dict(zip(columns, values))
    validate_fields(schema, fields, allow_id=False)
    table_data = load_table_data(table_name)
    next_id = max((row[ID_COLUMN] for row in table_data), default=0) + 1
    return table_data + [{ID_COLUMN: next_id, **fields}]


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Выбрать записи по условию или вернуть все записи."""
    # Ключ включает актуальные данные: после изменений старый ответ не используется.
    key = json.dumps([table_data, where_clause], sort_keys=True, ensure_ascii=False)
    result = _cache_select(
        key, lambda: [row.copy() for row in table_data if matches(row, where_clause)]
    )
    return json.loads(json.dumps(result))


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновить подходящие записи, не меняя исходный список."""
    if not set_clause or not where_clause:
        raise ValueError("Для update обязательны set и where.")
    if ID_COLUMN in set_clause:
        raise ValueError("ID назначается автоматически и не изменяется.")
    return [
        {**row, **set_clause} if matches(row, where_clause) else row.copy()
        for row in table_data
    ]


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удалить записи, удовлетворяющие обязательному условию."""
    if not where_clause:
        raise ValueError("Для delete обязательно условие where.")
    return [row.copy() for row in table_data if not matches(row, where_clause)]
