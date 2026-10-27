"""Настройки базы данных."""

META_FILE = "db_meta.json"
DATA_DIR = "data"
ENCODING = "utf-8"
VALID_TYPES = {"int": int, "str": str, "bool": bool}
ID_COLUMN = "ID"
ID_DEFINITION = "ID:int"
HELP_TEXT = """***База данных***
create_table <имя> <столбец:тип> ... — создать таблицу
list_tables — список таблиц
drop_table <имя> — удалить таблицу
insert into <имя> values (<значение>, ...) — добавить запись
select from <имя> [where <столбец> = <значение>] — прочитать записи
update <имя> set <столбец> = <значение> where <столбец> = <значение>
delete from <имя> where <столбец> = <значение> — удалить записи
info <имя> — информация о таблице
help — справка
exit — выход
Типы: int, str, bool. Строковые значения заключаются в кавычки.
"""
