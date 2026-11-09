# synplify-mcp 0.1.0a1 — экспериментальный выпуск

[English](RELEASE_NOTES.en.md)

**Статус: кандидат, тег и GitHub Release пока не опубликованы.**

Первый alpha-адаптер Synopsys Synplify Pro на **официальном MCP SDK 2.3.0**, без FastMCP. Доступны шесть инструментов: `server_info`, `tool_status`, `parse_diagnostics`, `parse_srr`, `compare_srr_reports`, `run_approved_synthesis`.

- Ограниченное чтение `.srr` с диагностикой, provenance, ресурсами и предварительным timing, сравнение только совместимых отчётов.
- Разрешённый запуск синтеза **отключён по умолчанию**; проект может содержать Tcl и не является песочницей.
- Безопасность: явный allowlist в манифесте вне workspace, контроль SHA-256 самого `.prj`, Windows `.exe` без script wrappers, ограничение логов и времени.
- `uv.lock`, CI Windows/Linux на Python 3.11/3.13/3.15, установка wheel/sdist в чистых окружениях, MCP `stdio`.

**Не проверено:** коммерческий Synplify Pro, лицензии, реальные семейства FPGA и корректность выполненного синтеза. `EDA_PASS=NOT_RUN`; нулевой код возврата не доказывает успешный EDA-результат.

[README](../README.md) · [Безопасность](../SECURITY.md) · [Процедура выпуска](RELEASE_PROCESS.md).
