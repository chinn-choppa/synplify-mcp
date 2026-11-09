[English](TOOL_CONTRACT.en.md)

# Контракт MCP-инструментов — experimental

Все шесть операций работают через локальный `stdio` официального MCP Python SDK 2.3.0. Возвращают JSON-совместимые структуры; сервер не отправляет исходники или лицензии автоматически. **MCP_TOOL_PASS не означает EDA_PASS.**

## Пять read-only операций

- `server_info()`: имя, версия, стадия, операции, отдельные флаги наличия, включения и фактической вендорской проверки
- `tool_status()`: проверка доступности исполняемого файла **без запуска** и раскрытия конфиденциальных путей
- `parse_diagnostics(text, limit=200)`: извлечение известных диагностик из текста не более 1 МиБ; отсутствие ошибок не подтверждает синтез
- `parse_srr(relative_path, encoding="auto", limit=200)`: ограниченное чтение разрешённого `.srr` с SHA-256, исходными строками и байтовыми смещениями; неизвестные данные обозначаются явно, см. [SRR_PARSER.md](SRR_PARSER.md)
- `compare_srr_reports(baseline_path, candidate_path, encoding="auto")`: сравнение двух разрешённых отчётов только при достаточном контексте версии/устройства/ограничений; при неизвестных ограничениях timing-дельты остаются null, см. [COMPARE.md](COMPARE.md)

`parse_srr` также возвращает `context`, `resources`, `timing` при известных подписанных полях, см. [METRICS.md](METRICS.md). Предварительные оценки Synplify **не равны post-route timing**.

## Исполняющая операция, по умолчанию запрещена

`run_approved_synthesis(project_id, acknowledge_side_effects=false, timeout_seconds=30)`: только операторский манифест утверждённых `.prj` вне агентского workspace, фиксированный бинарник Synplify и аргументы `-batch`. `shell`/Tcl/DO-команды произвольного вида через MCP не принимаются, однако сам доверенный `.prj` **может выполнять Tcl**. Windows-обёртки `.bat`/`.cmd`/`.ps1` отвергаются. `acknowledge_side_effects` не заменяет согласие человека в MCP-клиенте.

`PROCESS_EXIT_ZERO_UNVERIFIED` означает только exit code 0; это **не EDA_PASS**. Вендорское тестирование пока `NOT_RUN`. Границы безопасности и статусы: [APPROVED_RUN.md](APPROVED_RUN.md).
