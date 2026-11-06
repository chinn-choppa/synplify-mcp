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
uv sync
uv run synplify-mcp
```

Подключить MCP Inspector либо клиент Codex/Claude/OpenCode, проверить реальный `tools/list`, затем вызвать `server_info` и `parse_diagnostics` на синтетических данных. Только после успешного фактического вызова инструмента можно фиксировать `MCP_TOOL_PASS`. Простой старт процесса или наличие пакета означает максимум `INSTALLED`.

## Реальное EDA-тестирование

**Пока не предусмотрено** в bootstrap. После появления команд выполняйте на публичных минимальных RTL-проектах: lint, негативный кейс, сбой лицензии/тайм-аут, успешное завершение по самопроверяющемуся тесту, повреждённый файл, неверный путь и ограничение каталогов. Записывайте версии и SHA используемых исходников.

## Интеграционный CI

Тесты запускаются через `uv sync` и изолированное окружение с MCP SDK 2.3.0 на Windows/Linux, Python 3.11/3.13/3.15. Обязательны реальные `tools/list` и `tools/call` через память и `stdio`, тесты всех шести операций, сравнения .srr и отказа в запуске EDA. Коммерческий Synplify/лицензия в публичных CI не требуются.

## Проверка FastMCP (экспериментальная ветка)

`uv sync` устанавливает FastMCP 4.1.6 и официальный MCP SDK 2.3.0. Внутрипроцессный клиент `fastmcp.Client` проверяет список инструментов, аннотации и контракты аргументов. Независимый клиент `mcp.Client` выполняет настоящие `tools/list` и `tools/call` через дочерний процесс `stdio`, включая отказ от неожиданных аргументов и `DISABLED` при выключенном синтезе. Доказательства и сравнительный состав зависимостей приведены в [FASTMCP_EXPERIMENT.md](FASTMCP_EXPERIMENT.md).
