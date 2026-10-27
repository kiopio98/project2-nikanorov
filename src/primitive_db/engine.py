"""Основной цикл, выполнение команд и вывод результатов."""

import prompt
from prettytable import PrettyTable

from primitive_db import core
from primitive_db.constants import HELP_TEXT, ID_COLUMN, META_FILE
from primitive_db.decorators import handle_db_errors
from primitive_db.parser import parse_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def print_help():
    """Вывести список команд."""
    print(HELP_TEXT)


def welcome():
    """Вывести приветствие и справку."""
    print("DB project is running!")
    print_help()


def print_rows(schema, rows):
    """Вывести записи в формате PrettyTable, включая пустую выборку."""
    table = PrettyTable()
    table.field_names = list(schema)
    for row in rows:
        table.add_row([row[name] for name in schema])
    print(table)


@handle_db_errors
def execute_command(text):
    """Выполнить команду; False означает завершение сеанса."""
    query = parse_command(text)
    command = query["command"]
    if command == "exit":
        return False
    if command == "help":
        print_help()
        return True
    if command == "empty":
        return True
    metadata = load_metadata(META_FILE)
    if command == "list_tables":
        if not metadata:
            print("Таблиц пока нет.")
        for name in sorted(metadata):
            print(f"- {name}")
        return True
    table_name = query["table"]
    if command == "create_table":
        result = core.create_table(metadata, table_name, query["columns"])
        if result is not None:
            save_table_data(table_name, [])
            save_metadata(META_FILE, result)
            print(
                f'Таблица "{table_name}" успешно создана со столбцами: '
                + ", ".join(result[table_name])
            )
        return True
    if command == "drop_table":
        core.get_schema(metadata, table_name)
        result = core.drop_table(metadata, table_name)
        if result is not None:
            save_metadata(META_FILE, result)
            print(f'Таблица "{table_name}" успешно удалена.')
        return True
    schema = core.get_schema(metadata, table_name)
    if command == "info":
        rows = load_table_data(table_name)
        print(f'Таблица "{table_name}"')
        print("Столбцы: " + ", ".join(metadata[table_name]))
        print(f"Количество записей: {len(rows)}")
        return True
    if command == "insert":
        result = core.insert(metadata, table_name, query["values"])
        if result is not None:
            save_table_data(table_name, result)
            print(
                f"Запись с ID={result[-1][ID_COLUMN]} успешно добавлена "
                f'в таблицу "{table_name}".'
            )
        return True
    core.validate_fields(schema, query["where"] or {})
    rows = load_table_data(table_name)
    if command == "select":
        result = core.select(rows, query["where"])
        if result is not None:
            print_rows(schema, result)
        return True
    if command == "update":
        core.validate_fields(schema, query["set"], allow_id=False)
        result = core.update(rows, query["set"], query["where"])
        if result is not None:
            count = sum(core.matches(row, query["where"]) for row in rows)
            save_table_data(table_name, result)
            print(f'Таблица "{table_name}" успешно обновлена. Записей: {count}.')
    elif command == "delete":
        result = core.delete(rows, query["where"])
        if result is not None:
            save_table_data(table_name, result)
            print(
                f'Из таблицы "{table_name}" успешно удалено записей: '
                f"{len(rows) - len(result)}."
            )
    return True


def run():
    """Запускать команды до exit, EOF или прерывания с клавиатуры."""
    welcome()
    while True:
        try:
            command = prompt.string("Введите команду: ")
            if execute_command(command) is False:
                break
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
