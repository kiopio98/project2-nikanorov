#!/usr/bin/env python3
"""Запуск приложения."""


def main():
    """Запустить консольную базу данных."""
    from primitive_db.engine import run

    run()


if __name__ == "__main__":
    main()
