[English](TOOL_CONTRACT.en.md)

    # Контракт MCP-инструментов v0

    На этом этапе контракт намеренно ограничен. Все операции возвращают JSON-совместимые структуры, не содержат скрытых сетевых обращений и не запускают EDA.

    ## `server_info()`

    Возвращает `server`, `version`, `vendor_tool`, `stage`, `operations`. `stage="bootstrap"` запрещает трактовать результаты как готовую автоматизацию Synopsys Synplify Pro.

    ## `tool_status()`

    Проверяет наличие исполняемого файла, не запускает его. Поля: `tool`, `state`, `configured`, `executed=false`. Возможные состояния: `DETECTED_UNVERIFIED`, `NOT_FOUND`, `INVALID_OVERRIDE`. Не раскрывает полный путь, настройки лицензии или содержимое окружения.

    ## `parse_diagnostics(text, limit=200)`

    Принимает текст журнала до **1 МиБ**. Поддерживает не более 200 результатов в одном ответе. Возвращает `tool`, `count`, `truncated`, `items` с полями `severity`, `code`, `file`, `line`, `column`, `message`, `raw`. Неизвестные строки игнорируются, а не превращаются в выдуманные ошибки.

    Пример сообщения:

    ```text
    @W: rtl/top.sv(14): Width mismatch
@E: rtl/top.sv(28): Multiple drivers found
    ```

    Обратите внимание: `parse_diagnostics` возвращает лишь совпадения с известными шаблонами. Отсутствие совпадений **не означает** успешной сборки. Исходные строки сохраняются для проверки.

    ## `parse_srr(relative_path, encoding="auto", limit=200)`

    Ограниченное чтение `.srr` под корнем `SYNPLIFY_MCP_WORKSPACE`. Формат JSON, состояния ошибок и ограничения подробно описаны в [спецификации парсера](SRR_PARSER.md). Отсутствие диагностик не означает `EDA_PASS`.

    ## Будущие команды

    Для запуска Synopsys Synplify Pro потребуются отдельные аргументы с ограниченными перечислениями и путями, явное подтверждение побочных эффектов, ограничение времени и логов, код возврата процесса и атомарно создаваемые артефакты. Не добавлять параметр `command` со свободным текстом Tcl/DO/shell.

## Экспериментальные метрики ресурсов и timing

`parse_srr` может возвращать дополнительно `context`, `resources`, `timing`; значения принимаются только из явно подписанных секций и единиц. Описание ограничений и семантики: [METRICS.md](METRICS.md). `timing.kind=SYNTHESIS_ESTIMATE`, не post-route timing; `synthesis_status=UNKNOWN`.

## `run_approved_synthesis(project_id, acknowledge_side_effects=false, timeout_seconds=30)`

Операция с **побочными эффектами**, по умолчанию запрещена. Только операторский манифест с SHA-256 проекта, настройка сервера через переменные окружения, фиксированный `synplify_pro -batch <approved.prj>`, без свободных аргументов Tcl/shell. `acknowledge_side_effects` **не** равнозначен подтверждению человеком; согласие контролирует MCP-клиент. `PROCESS_EXIT_ZERO_UNVERIFIED` не равен `EDA_PASS`. Ограничения изоляции и контракт состояний: [APPROVED_RUN.md](APPROVED_RUN.md).

## `compare_srr_reports(baseline_path, candidate_path, encoding="auto")`

Сопоставляет два отчёта по исходным строкам с точными SHA-256. Ресурсные дельты вычисляются только при совместимом контексте; числовой timing без полного доказательства эквивалентности ограничений не сравнивается. [Контракт RU](COMPARE.md) / [EN](COMPARE.en.md).
