"""Консольный интерфейс."""

import prompt


def welcome():
    """Вывести приветствие."""
    print("DB project is running!")


def run():
    """Читать команды до выхода."""
    welcome()
    while True:
        command = prompt.string("Введите команду: ")
        if command == "exit":
            break
        if command == "help":
            print("help — справка; exit — выход")
        else:
            print(f"Функции {command} нет. Попробуйте снова.")
