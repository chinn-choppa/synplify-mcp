[English](TESTING.en.md)

# Проверка проекта

## Быстрые проверки без EDA и внешней сети

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests
```

PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
Remove-Item Env:PYTHONPATH
```

## При наличии SDK MCP

```bash
uv sync --locked
uv run --no-sync synplify-mcp
```

Подключить MCP Inspector либо клиент Codex/Claude/OpenCode, проверить реальный `tools/list`, затем вызвать `server_info` и `parse_diagnostics` на синтетических данных. Только после успешного фактического вызова инструмента можно фиксировать `MCP_TOOL_PASS`. Простой старт процесса или наличие пакета означает максимум `INSTALLED`.

## Реальное EDA-тестирование

**Пока не предусмотрено** в bootstrap. После появления команд выполняйте на публичных минимальных RTL-проектах: lint, негативный кейс, сбой лицензии/тайм-аут, успешное завершение по самопроверяющемуся тесту, повреждённый файл, неверный путь и ограничение каталогов. Записывайте версии и SHA используемых исходников.

## Интеграционный CI

Тесты запускаются через `uv sync --locked` и изолированное окружение с MCP SDK 2.3.0 на Windows/Linux, Python 3.11/3.13/3.15. Обязательны реальные `tools/list` и `tools/call` через память и `stdio`, тесты всех шести операций, сравнения .srr и отказа в запуске EDA. Коммерческий Synplify/лицензия в публичных CI не требуются.

## Проверка установочного пакета

```bash
uv sync --locked
uv run --no-sync python -m unittest discover -s tests -v
uv build
python scripts/verify_release_artifacts.py
```

В **каждом из шести заданий** Windows/Linux × Python 3.11/3.13/3.15 CI выполняет тесты, собирает wheel/sdist и устанавливает **каждый архив в новом venv**. Реальный MCP-клиент проверяет запуск как модуля, так и **установленного CLI** `synplify-mcp`, все шесть tools, `server_info`, `parse_diagnostics` и запрет EDA без разрешения оператора. Публикация: [RELEASE_PROCESS.md](RELEASE_PROCESS.md).
