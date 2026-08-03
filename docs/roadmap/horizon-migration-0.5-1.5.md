# Horizon Core Migration Contract — этапы 0.5–1.5

Этот документ является обязательным дополнением к `docs/roadmap/kpnews-roadmap.md` и формализует переход от Horizon к самостоятельному исполняемому ядру `radio-news`.

До завершения `1.5 Independent Vertical Slice Acceptance` репозиторий `iibaranov-IG/Horizon` не архивируется и не удаляется.

## Последовательность

```text
0.5 Horizon Migration Audit
0.6 Horizon Baseline and Component Classification
0.7 Controlled Extraction Decision
1.0 Modular Monolith Skeleton
1.1 Source Registry + RSS Collector
1.2 Raw Storage + Normalization
1.3 Story + Claim + Manual Fact
1.4 Verification + SQLite Persistence
1.5 Independent Vertical Slice Acceptance
```

Критерий завершения — не наличие перенесённых файлов, а доказанная независимость `radio-news`.

## Обязательные артефакты

```text
docs/migration/horizon-inventory.md
docs/migration/horizon-baseline.md
docs/migration/horizon-component-map.md
docs/migration/horizon-decision.md
docs/migration/horizon-retirement-checklist.md
provenance/horizon-components.json
```

## Статус фактического использования

Каждый компонент Horizon получает ровно один статус:

```text
ACTIVE_RUNTIME
ACTIVE_DEV_ONLY
ACTIVE_TEST_ONLY
LEGACY
DEAD_CODE
UNKNOWN
```

Само наличие файла не доказывает использование. Статус подтверждается imports, entrypoints, configuration, tests, workflows, runtime traces и документацией.

## Решение о миграции

Для каждого компонента допускаются только следующие решения:

```text
TRANSFER_AS_IS
TRANSFER_WITH_ADAPTATION
REIMPLEMENT
DEFER
REJECT
NEEDS_REVIEW
```

Каждое решение обязано содержать:

- исходный репозиторий и путь;
- полный исходный commit SHA;
- назначение;
- зависимости;
- usage status;
- целевой путь;
- причину решения;
- тесты и доказательства эквивалентности;
- локальные изменения КПNEWS.

## Риск миграции

Каждый компонент получает оценку:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

| Компонент | Решение | Риск | Требование |
|---|---|---:|---|
| RSS collector | TRANSFER_WITH_ADAPTATION | MEDIUM | доказать идемпотентность и provenance |
| SSRF transport | TRANSFER_AS_IS | CRITICAL | перенос без упрощения; полный security regression suite |
| Russian locales | TRANSFER_WITH_ADAPTATION | LOW | сохранить locale contract |
| Processing runtime | TRANSFER_WITH_ADAPTATION | HIGH | сохранить profile contracts и structured-output repair |
| Web UI Horizon | DEFER | LOW | backend vertical slice имеет приоритет |
| Demo/legacy modules | REJECT | LOW | доказать отсутствие runtime dependency |

Security boundary нельзя переписывать или упрощать как обычный вспомогательный модуль.

## Машинно-проверяемый provenance

`provenance/horizon-components.json` хранит происхождение всех перенесённых компонентов в одном manifest.

```json
{
  "schema_version": 1,
  "source_repository": "iibaranov-IG/Horizon",
  "baseline_commit": "<full-sha>",
  "generated_at": "<ISO-8601>",
  "components": [
    {
      "component_id": "ssrf_transport",
      "source_paths": [
        "src/horizon/transport/..."
      ],
      "target_paths": [
        "src/radio_news/security/..."
      ],
      "usage_status": "ACTIVE_RUNTIME",
      "migration_decision": "TRANSFER_AS_IS",
      "migration_risk": "CRITICAL",
      "local_changes": [],
      "verification": {
        "tests": [],
        "ci_run": null
      }
    }
  ]
}
```

CI должен валидировать корневую схему provenance, перечисления и обязательные поля каждого компонента.

# 0.5 Horizon Migration Audit

## Цель

Получить доказательную инвентаризацию Horizon до изменения кода.

## Проверить

- package structure;
- collectors;
- raw storage;
- normalization;
- processing runtime;
- profile loader и profiles;
- Russian localization;
- configuration;
- CLI entrypoints;
- webhook delivery;
- SSRF transport;
- tests и CI;
- packaging;
- documentation;
- dependencies;
- локальные изменения относительно `Thysrael/Horizon`.

## Результат

`docs/migration/horizon-inventory.md` с фактическими путями, imports, entrypoints, тестами и usage status.

# 0.6 Horizon Baseline and Component Classification

До переноса фиксируются:

- точный Horizon commit SHA;
- clean working state;
- дерево зависимостей;
- версия Python;
- wheel/sdist build;
- clean wheel install;
- `pip check`;
- полный test suite;
- failing/skipped tests;
- security tests;
- CLI smoke tests;
- использованные config-файлы;
- workflow runs, привязанные к точному SHA.

Baseline сохраняется в `docs/migration/horizon-baseline.md`.

Доказательство на другом SHA не считается эквивалентным.

# 0.7 Controlled Extraction Decision

`docs/migration/horizon-decision.md` фиксирует:

- почему Horizon не остаётся постоянной runtime-зависимостью;
- почему полный `git subtree` не является целевым решением;
- почему выбран controlled extraction;
- границы модульного монолита;
- правила provenance;
- порядок проверки эквивалентности;
- запрет скрытого fallback к Horizon;
- момент окончательного переключения разработки на `radio-news`.

Компоненты переносятся только после утверждения component map.

# 1.0 Modular Monolith Skeleton

```text
radio-news/
├── pyproject.toml
├── src/radio_news/
│   ├── core/
│   ├── sources/
│   ├── stories/
│   ├── verification/
│   ├── editorial/
│   ├── writing/
│   ├── rundown/
│   ├── workflow/
│   ├── storage/
│   ├── security/
│   ├── exports/
│   └── api/
├── profiles/
├── editorial/
├── migrations/
├── provenance/
└── tests/
```

Требования:

- один Python package namespace;
- clean build/install;
- import из произвольного cwd;
- отсутствие runtime import из Horizon;
- базовый blocking CI;
- минимальные domain contracts без преждевременного UI.

# 1.1 Source Registry + RSS Collector

Первый источник работает на фиксированном versioned RSS fixture.

Обязательные свойства:

- стабильный source ID;
- canonical URL;
- source external ID при наличии;
- published/fetched timestamps;
- raw payload;
- content hash;
- идемпотентный повторный запуск;
- ошибки получения не превращаются в success.

# 1.2 Raw Storage + Normalization

Система сохраняет исходный payload без потери и создаёт отдельный `NormalizedItem`.

Нормализация не перезаписывает raw data.

Проверяется:

- HTML/text normalization;
- dates;
- canonical URL;
- source metadata;
- stable hash;
- version history;
- чтение данных после рестарта.

# 1.3 Story + Claim + Manual Fact

Первый vertical slice не требует AI.

```text
RawItem
→ NormalizedItem
→ Story
→ Claim
→ Manual Fact
```

Требования:

- Story создаётся детерминированно;
- Claim связан с конкретным RawItem/NormalizedItem;
- Claim сохраняет источник и asserted time;
- Manual Fact связан с supporting Claim;
- ручное решение хранит editor ID, timestamp и reason;
- факт нельзя создать без provenance.

# 1.4 Verification + SQLite Persistence

Добавляется воспроизводимый `VerificationResult`.

Минимальные статусы:

```text
READY
READY_WITH_ATTRIBUTION
NEEDS_REVIEW
BLOCKED
CONTRADICTORY
```

Проверяется:

- одинаковый результат на одинаковом input и policy version;
- после рестарта все связи читаются из SQLite;
- migrations воспроизводимы;
- foreign keys включены;
- ошибки записи не превращаются в успешную обработку;
- audit trail не теряется.

# 1.5 Independent Vertical Slice Acceptance

Обязательная цепочка:

```text
RSS fixture
→ RawItem
→ NormalizedItem
→ Story
→ Claim
→ Manual Fact
→ VerificationResult
→ SQLite
```

## Acceptance criteria

- один фиксированный versioned RSS fixture;
- повторный запуск не создаёт дублей;
- raw payload сохранён полностью;
- URL, source ID, published/fetched time и hash сохранены;
- Story создаётся детерминированно;
- Claim связан с исходным материалом;
- Manual Fact хранит автора, время и причину решения;
- VerificationResult воспроизводим;
- данные корректно читаются после рестарта;
- pipeline работает из произвольного cwd;
- package установлен в чистом окружении;
- отсутствуют imports и runtime calls в Horizon;
- tests и blocking CI проходят на точном SHA;
- provenance перенесённых компонентов валиден.

После успешной приёмки фиксируется статус:

```text
radio-news имеет собственное исполняемое ядро
Horizon больше не runtime-основа
Horizon остаётся reference repository
```

# Stop conditions

Работа останавливается и этап не принимается, если:

- фактическое использование компонента не установлено;
- provenance неполон;
- перенос security boundary требует упрощения;
- тесты Horizon невозможно связать с baseline SHA;
- компонент требует скрытой runtime-зависимости от Horizon;
- два варианта переноса меняют поведение по-разному и нет утверждённого решения;
- vertical slice проходит только из исходного checkout;
- повторный запуск создаёт дубли;
- данные не восстанавливаются после рестарта;
- CI не привязан к точному commit SHA.

# Retirement checklist

Horizon может быть архивирован только после выполнения всех пунктов:

```text
[ ] все используемые компоненты классифицированы
[ ] baseline зафиксирован на точном SHA
[ ] provenance записан и проверяется CI
[ ] SSRF transport перенесён без деградации
[ ] русская локализация перенесена либо заменена функционально эквивалентной реализацией, подтверждённой тестами
[ ] processing profiles работают
[ ] structured-output repair перенесён
[ ] config contracts определены
[ ] нужные тесты перенесены или заменены эквивалентными
[ ] clean package build/install проходит
[ ] vertical slice работает без Horizon
[ ] CI radio-news зелёный на точном SHA
[ ] в Horizon не осталось уникального нужного кода
[ ] в Horizon не осталось незадокументированных решений
[ ] итоговая сверка выполнена человеком
[ ] создан ADR о выводе Horizon из эксплуатации
```

# ADR об архивировании Horizon

После выполнения checklist создаётся:

```text
docs/adr/ADR-00XX-retire-horizon.md
```

ADR содержит:

- итоговый SHA Horizon;
- SHA `radio-news`, заменивший runtime-функции;
- список перенесённых компонентов;
- список адаптированных компонентов;
- список отвергнутых компонентов;
- ссылки на CI;
- результат human review;
- дату архивирования.

Удаление Horizon не является стандартным действием. После retirement acceptance предпочтительно архивировать reference repository.
