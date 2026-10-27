"""Проверки команд, сохранения данных, декораторов и кэша."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

from primitive_db import core
from primitive_db.decorators import create_cacher, handle_db_errors, log_time
from primitive_db.engine import execute_command
from primitive_db.parser import parse_command, parse_set, parse_values, parse_where
from primitive_db.utils import load_metadata, load_table_data, save_table_data


def command(text, answer="y"):
    """Выполнить команду и вернуть вывод без обращения к реальной базе."""
    output = io.StringIO()
    with (
        contextlib.redirect_stdout(output),
        patch("prompt.string", return_value=answer),
    ):
        result = execute_command(text)
    return result, output.getvalue()


def test_parser():
    """Проверить кавычки, числа, логические значения и неверный синтаксис."""
    assert parse_values('("Анна, Мария", -2, true)') == ["Анна, Мария", -2, True]
    assert parse_values("('New York', 42, FALSE)") == ["New York", 42, False]
    assert (
        parse_values('( "say \\"hi\\"", 1, false )'.replace("\\\\", "\\"))[0]
        == 'say "hi"'
    )
    assert parse_where("age=28") == {"age": 28}
    assert parse_where('name="where set, and"') == {"name": "where set, and"}
    assert parse_set("age=29, active=false") == {"age": 29, "active": False}
    assert parse_where("age=28 and active=true") == {"age": 28, "active": True}
    assert parse_command('UPDATE users SET name="where" WHERE age=28')["set"] == {
        "name": "where"
    }
    assert parse_command("select from users;")["where"] is None
    invalid = [
        'insert into users values ("a",)',
        'insert into users values ("a" 2)',
        "select from users where age",
        "update users set age=3",
        "delete from users",
        "list_tables extra",
        "create_table users",
        'select from users where name="unterminated',
        "select from users where age=3 trailing",
    ]
    for text in invalid:
        try:
            parse_command(text)
        except ValueError:
            pass
        else:
            raise AssertionError(text)


def test_commands():
    """Проверить полный цикл CRUD, отмену, ошибки и сохранение."""
    assert load_metadata("db_meta.json") == {}
    command("create_table users name:str age:int is_active:bool")
    schema = load_metadata("db_meta.json")
    assert schema["users"] == ["ID:int", "name:str", "age:int", "is_active:bool"]
    assert load_table_data("users") == []
    for text in [
        "create_table users name:str",
        "create_table bad x:float",
        "create_table bad ID:int",
        "create_table bad x:str x:int",
        "create_table ../bad x:int",
    ]:
        assert "Ошибка" in command(text)[1]
    assert load_metadata("db_meta.json") == schema
    command('insert into users values ("Sergei", 28, true)')
    command('insert into users values ("Анна, Мария", 28, false)')
    assert [row["ID"] for row in load_table_data("users")] == [1, 2]
    before = load_table_data("users")
    for text in [
        'insert into users values ("Bad", true, true)',
        'insert into users values ("Bad", "28", true)',
        'insert into users values ("Bad", 28, 1)',
        'insert into users values ("Bad", 28)',
        'update users set age="wrong" where ID=1',
        "update users set ID=7 where ID=1",
        "select from users where absent=1",
        "select from users where ID=true",
        "update users set missing=1 where ID=1",
    ]:
        assert "Ошибка" in command(text)[1], text
        assert load_table_data("users") == before
    assert "Sergei" in command("select from users where age=28")[1]
    assert "Анна, Мария" in command("select from users")[1]
    assert "Sergei" not in command("select from users where age=100")[1]
    command('update users set age=29 where name="Sergei"')
    assert load_table_data("users")[0]["age"] == 29
    assert "Sergei" not in command("select from users where age=28")[1]
    command("update users set age=30 where age=28")
    assert load_table_data("users")[1]["age"] == 30
    command("delete from users where ID=1", answer="n")
    assert len(load_table_data("users")) == 2
    command("drop_table users", answer="n")
    assert "users" in load_metadata("db_meta.json")
    command("delete from users where ID=1")
    assert [row["ID"] for row in load_table_data("users")] == [2]
    command('insert into users values ("New", 20, false)')
    assert [row["ID"] for row in load_table_data("users")] == [2, 3]
    assert "Количество записей: 2" in command("info users")[1]
    assert "users" in command("list_tables")[1]
    command("drop_table users")
    assert load_metadata("db_meta.json") == {}
    assert not os.path.exists("data/users.json")
    command("create_table users name:str")
    assert load_table_data("users") == []
    assert "Ошибка" in command("drop_table absent")[1]
    assert "Ошибка" in command("select from absent")[1]
    assert "нет" in command("not_a_command")[1]
    assert command("exit")[0] is False


def test_cache_and_decorators():
    """Проверить замыкание, обновление кэша и сохранение имён функций."""
    cache = create_cacher()
    calls = []
    assert cache("same", lambda: calls.append(1) or 10) == 10
    assert cache("same", lambda: calls.append(2) or 20) == 10
    assert calls == [1]
    assert cache("other", lambda: 20) == 20
    rows = [{"ID": 1, "age": 28}]
    with contextlib.redirect_stdout(io.StringIO()):
        first = core.select(rows, {"age": 28})
        first[0]["age"] = 99
        assert core.select(rows, {"age": 28})[0]["age"] == 28
        rows[0]["age"] = 29
        assert core.select(rows, {"age": 28}) == []
        assert core.select(rows, {"age": 29})[0]["age"] == 29
    assert core.select.__name__ == "select"
    assert core.insert.__name__ == "insert"
    for exception in [KeyError("x"), ValueError("wrong"), FileNotFoundError("file")]:

        def fail():
            raise exception

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert handle_db_errors(fail)() is None
        assert "Ошибка" in output.getvalue()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert log_time(lambda: 42)() == 42
    assert "секунд" in output.getvalue()


def test_persistence_and_corruption():
    """Проверить новое приложение, повреждённый JSON и отсутствие записи поверх него."""
    command('insert into users values ("Restart")')
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    process = subprocess.run(
        [sys.executable, "-m", "primitive_db.main"],
        input="select from users\nexit\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=True,
    )
    assert "Restart" in process.stdout
    with open("data/users.json", "w", encoding="utf-8") as target:
        target.write("{broken")
    assert "Ошибка" in command('insert into users values ("No")')[1]
    with open("data/users.json", encoding="utf-8") as source:
        assert source.read() == "{broken"
    save_table_data("users", [])
    with open("db_meta.json", "w", encoding="utf-8") as target:
        json.dump([], target)
    assert "Ошибка" in command("list_tables")[1]


def main():
    """Запустить проверки в отдельной временной директории."""
    test_parser()
    directory = os.getcwd()
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        try:
            os.chdir(temporary)
            test_commands()
            test_cache_and_decorators()
            test_persistence_and_corruption()
        finally:
            os.chdir(directory)
    print("Все проверки пройдены.")


if __name__ == "__main__":
    main()
