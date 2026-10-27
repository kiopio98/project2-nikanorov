"""Разбор команд, списков значений и условий равенства."""

import json
import shlex


def tokenize(text):
    """Разделить строку, сохранив кавычки, пробелы и запятые внутри строк."""
    tokens = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        start = index
        if char in "\"'":
            quote = char
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                elif text[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise ValueError("Незакрытая кавычка.")
        elif char in "(),=":
            index += 1
        else:
            while (
                index < len(text)
                and not text[index].isspace()
                and text[index] not in "(),=\"'"
            ):
                index += 1
        tokens.append(text[start:index])
    return tokens


def parse_value(token):
    """Преобразовать литерал в int, bool или строку в кавычках."""
    if token.startswith('"'):
        value = json.loads(token)
        if not isinstance(value, str):
            raise ValueError("Ожидается строка.")
        return value
    if token.startswith("'"):
        return shlex.split(token)[0]
    if token.lower() in ("true", "false"):
        return token.lower() == "true"
    try:
        return int(token)
    except ValueError:
        raise ValueError(f"Некорректное значение: {token}. Строки вводятся в кавычках.")


def parse_values(tokens):
    """Разобрать значения в круглых скобках, разделённые запятыми."""
    if isinstance(tokens, str):
        tokens = tokenize(tokens)
    if len(tokens) < 2 or tokens[0] != "(" or tokens[-1] != ")":
        raise ValueError("values должен содержать значения в круглых скобках.")
    body = tokens[1:-1]
    if not body:
        return []
    if len(body) % 2 == 0 or any(token != "," for token in body[1::2]):
        raise ValueError("Значения нужно разделять запятыми.")
    return [parse_value(token) for token in body[::2]]


def parse_clause(tokens):
    """Разобрать одно или несколько равенств через запятую или and."""
    if isinstance(tokens, str):
        tokens = tokenize(tokens)
    if not tokens:
        raise ValueError("Пустое условие.")
    fields = {}
    index = 0
    while index < len(tokens):
        if index + 2 >= len(tokens) or tokens[index + 1] != "=":
            raise ValueError("Ожидается условие: столбец = значение.")
        name = tokens[index]
        if not name.isidentifier() or name in fields:
            raise ValueError(f"Некорректный или повторяющийся столбец: {name}.")
        fields[name] = parse_value(tokens[index + 2])
        index += 3
        if index < len(tokens):
            if tokens[index].lower() not in (",", "and") or index + 1 == len(tokens):
                raise ValueError("Условия разделяются запятой или and.")
            index += 1
    return fields


def parse_where(text):
    """Разобрать условие where в словарь."""
    return parse_clause(text)


def parse_set(text):
    """Разобрать присваивания set в словарь."""
    return parse_clause(text)


def parse_command(text):
    """Разобрать всю команду и проверить её синтаксис."""
    tokens = tokenize(text.strip().removesuffix(";"))
    if not tokens:
        return {"command": "empty"}
    command = tokens[0].lower()
    if command in ("help", "exit", "list_tables"):
        if len(tokens) != 1:
            raise ValueError(f"Команда {command} не принимает аргументы.")
        return {"command": command}
    if command == "create_table":
        if len(tokens) < 3:
            raise ValueError("Формат: create_table имя столбец:тип ...")
        return {"command": command, "table": tokens[1], "columns": tokens[2:]}
    if command in ("drop_table", "info"):
        if len(tokens) != 2:
            raise ValueError(f"Формат: {command} имя_таблицы")
        return {"command": command, "table": tokens[1]}
    if command == "insert":
        if len(tokens) < 6 or tokens[1].lower() != "into" or tokens[3].lower() != "values":
            raise ValueError("Формат: insert into имя values (...)")
        return {"command": command, "table": tokens[2], "values": parse_values(tokens[4:])}
    if command in ("select", "delete"):
        if len(tokens) < 3 or tokens[1].lower() != "from":
            raise ValueError(f"Формат: {command} from имя [where столбец = значение]")
        where = None
        if len(tokens) > 3:
            if tokens[3].lower() != "where":
                raise ValueError("После имени таблицы ожидается where.")
            where = parse_clause(tokens[4:])
        if command == "delete" and where is None:
            raise ValueError("Для delete обязательно условие where.")
        return {"command": command, "table": tokens[2], "where": where}
    if command == "update":
        if len(tokens) < 10 or tokens[2].lower() != "set":
            raise ValueError("Формат: update имя set столбец = значение where условие")
        where_index = next(
            (i for i in range(3, len(tokens)) if tokens[i].lower() == "where"), None
        )
        if where_index is None:
            raise ValueError("Для update обязательно условие where.")
        return {
            "command": command,
            "table": tokens[1],
            "set": parse_clause(tokens[3:where_index]),
            "where": parse_clause(tokens[where_index + 1:]),
        }
    raise ValueError(f"Функции {tokens[0]} нет. Попробуйте снова.")
