# КПNEWS — дорожная карта развития на базе Horizon

## 1. Цель проекта

Создать редакционную платформу для радио «Комсомольская правда», которая:

- собирает новости из утверждённых источников;
- объединяет публикации в развивающиеся сюжеты;
- выделяет утверждения и подтверждённые факты;
- оценивает значимость события для аудитории КП;
- показывает новости через разные редакционные оптики ведущих;
- формирует редакционный набор выпуска через Главного новостника;
- генерирует эфирный текст по правилам КПNEWS;
- собирает технически допустимый трёхминутный выпуск;
- сохраняет ответственность человека-редактора за финальное решение.

Основной принцип:

> AI предлагает, сравнивает и объясняет. Код проверяет ограничения. Редактор принимает решение.

## 2. Целевая архитектура

```text
Источники
    ↓
Horizon Core
    ↓
Raw Storage
    ↓
Normalization
    ↓
Story Engine
    ↓
Claim + Fact Ledger
    ↓
Verification
    ↓
Processing Profiles
    ↓
Общая редакционная оценка
    ↓
Editorial Personas
    ↓
Persona Recommendations
    ↓
Chief News Editor
    ↓
Versioned Editorial Slates
    ↓
Radio Writing Engine
    ↓
Fact Alignment + Radio Linter
    ↓
Rundown Constraint Solver
    ↓
Варианты выпуска
    ↓
Человек-редактор
    ↓
Approved Rundown
    ↓
Export
```

## 3. Домены

### Horizon Core

- source collection;
- raw storage;
- normalization;
- generic enrichment;
- profiles;
- AI infrastructure;
- localization.

### KPNEWS Story Domain

- clustering;
- Claims;
- Facts;
- contradictions;
- verification;
- story development.

### KPNEWS Editorial Domain

- configurable criteria;
- score vectors;
- editorial personas;
- consensus and unique value;
- Chief News Editor;
- Editorial Slate;
- structured decisions;
- human overrides.

### KPNEWS Broadcast Domain

- radio scripts;
- fact alignment;
- linter;
- timing;
- rundown;
- rotation;
- breaking news;
- pronunciation.

### KPNEWS Delivery Domain

- Web UI;
- API;
- audit;
- approval;
- export adapters.

## 4. Этап 0 — Foundation

### Цель

Начать с проверенного состояния и сохранить архитектурные решения в репозитории.

### Работы

- зафиксировать baseline SHA;
- создать рабочую ветку;
- подключить upstream `Thysrael/Horizon`;
- составить матрицу различий;
- сохранить архитектуру, редакционные правила и roadmap;
- определить обязательный CI-контракт.

### Gate

- clean branch;
- точный baseline SHA;
- документация в репозитории;
- зелёный CI.

## 5. Этап 1 — Интеграция upstream foundation

### Цель

Забрать уже реализованные upstream-решения без повторной разработки.

### Обязательные изменения

- optional Impact — `4565b21`;
- enrichment structured-output repair — `5eaa5ce`;
- runtime profile settings — `29c8bdb`;
- profile section ordering и последние ограничения Impact — `08d9232`;
- candidate profile routing из `bd44c50`, если требуется.

### Запреты

- blind cherry-pick всей upstream-ветки;
- замена нашего security transport;
- включение чужих источников и порогов без решения редакции.

### Gate

- русский профиль работает;
- structured blocks устойчивы;
- optional Impact не создаёт спекулятивный блок;
- full CI green.

## 6. Этап 2 — Workflow и AI Audit

### Цель

Сделать обработку явной, идемпотентной и воспроизводимой.

### State machine

```text
NEW
NORMALIZED
CLUSTERED
CLAIMS_EXTRACTED
FACTS_RESOLVED
VERIFIED
SCORED
PERSONAS_EVALUATED
SLATE_CANDIDATE
SCRIPTED
READY_FOR_RUNDOWN
APPROVED
ARCHIVED
FAILED
```

### Модули

```text
src/kpnews/workflow/
├── ingestion_pipeline.py
├── story_pipeline.py
├── verification_pipeline.py
├── editorial_pipeline.py
├── script_pipeline.py
└── rundown_pipeline.py
```

### AI Audit

Для каждого вызова сохраняются:

- model;
- model version;
- prompt version;
- input hash;
- raw output;
- parsed output;
- duration;
- status.

### Idempotency key

```text
story_id + operation_type + input_hash + prompt_version
```

### Gate

- повторный запуск не создаёт дублей;
- успешная операция не повторяет дорогой AI-вызов;
- ошибки видимы;
- любой результат воспроизводим.

## 7. Этап 3 — Source Registry и Raw Storage

### Первая очередь источников

- `kp.ru`;
- `ria.ru`;
- `tass.ru`;
- `iz.ru`;
- `kremlin.ru`;
- официальный Telegram-канал Минобороны России;
- `cbr.ru`;
- `gismeteo.ru`.

### Правило MVP

Не более 5–7 обычных новостных источников. Валюты и погода — отдельные structured collectors.

### RawItem хранит

- source ID;
- original URL;
- external ID;
- original title;
- original content;
- publication time;
- fetch time;
- checksum;
- metadata;
- version history.

### Gate

- сбор устойчив;
- рестарт не создаёт повторов;
- исходный материал можно восстановить.

## 8. Этап 4 — Story Engine

### Цель

Объединять сообщения в сюжет и отделять развитие от перепечатки.

### Гибридный каскад

1. canonical URL;
2. source external ID;
3. normalized title;
4. entities;
5. temporal proximity;
6. geography;
7. embedding similarity;
8. LLM только для пограничных случаев.

### Gate

- пять публикаций об одном событии образуют один Story;
- разные происшествия не склеиваются;
- история merge/split сохраняется;
- новые детали выделяются отдельно.

## 9. Этап 5 — Claim + Fact Ledger

### Claim

Что сообщил конкретный источник.

```python
class Claim:
    id: str
    text: str
    source_id: str
    source_item_id: str
    asserted_at: datetime
    attribution_required: bool
```

### Fact

Что редакция считает установленным или разрешённым к использованию.

```python
class Fact:
    id: str
    canonical_text: str
    verification_status: str
    editorial_status: str
```

### Статусы

```text
confirmed
single_source
official_claim
reported
disputed
unverified
retracted
```

### Gate

- каждый Fact связан с supporting Claims;
- противоречия видны;
- редактор может вручную утвердить или запретить факт.

## 10. Этап 6 — Verification Engine

### Результаты

```text
READY
READY_WITH_ATTRIBUTION
NEEDS_REVIEW
BLOCKED
CONTRADICTORY
```

### Правила

- официальный первичный источник;
- два независимых подтверждения;
- sensitive topic policy;
- погибшие и пострадавшие;
- военная информация;
- конфликтующие данные;
- required attribution;
- exclusive source.

### Gate

- чувствительный single-source story не проходит автоматически;
- перепечатки не считаются независимыми источниками;
- противоречивые сведения маркируются.

## 11. Этап 7 — Configurable Editorial Scoring

### Первая версия критериев

```text
audience_reach
practical_impact
state_significance
urgency
broadcast_value
evidence_quality
freshness
development_value
```

### Правило

LLM выставляет отдельные оценки и объяснения. Итоговые вычисления делает код.

### Вектор

```json
{
  "editorial_importance": 9.1,
  "audience_impact": 8.6,
  "verification_quality": 7.4,
  "broadcast_readiness": 8.0,
  "freshness": 6.8
}
```

### Gate

- критерии живут в config;
- веса можно менять без Python-правок;
- evidence quality может быть обязательным gate;
- причины оценки видимы.

## 12. Этап 8 — Editorial Personas

### MVP-персоны

- Олег Кошевой;
- Ульяна Громова;
- Сергей Левашов.

### После приёмки

- Любовь Шевцова;
- Сергей Тюленин;
- Иван Земнухов;
- Виктор Третьякевич;
- Валерия Борц;
- Клавдия Ковалёва.

### PersonaRecommendation

```python
class PersonaRecommendation:
    story_id: str
    persona_id: str
    score: float
    recommendation: str
    reasons: list
    preferred_angle: str | None
    guest_questions: list[str]
```

### Gate

- факты не меняются в зависимости от персоны;
- persona fit хранится отдельно от global importance;
- рекомендации имеют объяснение и evidence.

## 13. Этап 9 — Chief News Editor

### Вход

```text
полный допустимый пул
+ общая редакционная оценка
+ persona recommendations
+ история предыдущих выпусков
+ edition context
```

Главный новостник видит и сильные сюжеты, которые не рекомендовала ни одна персона.

### Сигналы

```text
recommendation_count
strong_recommendation_count
max_persona_score
relevant_persona_mean
cross_domain_consensus
unique_value_score
```

### Versioned Editorial Slate

```python
class EditorialSlate:
    id: str
    version: int
    status: str  # DRAFT, PROPOSED, REVIEWED, REJECTED, ACCEPTED
    created_by: str
    parent_version_id: str | None
    lead_candidates: list[str]
    selected_candidates: list[str]
    reserve_candidates: list[str]
    rejected_candidates: list[str]
```

### Правила

- unique value не гарантирует эфир, но требует явного решения;
- контролируется покрытие перспектив, а не квота ведущих;
- lead story выбирается отдельным алгоритмом;
- Chief Editor не считает хронометраж и не управляет техническими квотами;
- тексты ещё не генерируются для всего пула.

### Gate

- созданы варианты Slate A/B/C;
- решения имеют machine-readable reason codes;
- все версии и ручные изменения сохранены.

## 14. Этап 10 — Radio Writing Engine

### Порядок

```text
Editorial Slate
→ selected + reserve
→ Radio Writer
```

Тексты не создаются для всех кандидатов до редакционного отбора.

### Вход

```json
{
  "approved_facts": [],
  "attributed_claims": [],
  "forbidden_facts": [],
  "required_attributions": [],
  "known_contradictions": [],
  "target_duration": 17,
  "previous_version": {}
}
```

### Выход

Каждое предложение содержит `fact_ids` или `claim_ids`.

### Gate

- модель не получает право добавлять сведения вне разрешённого набора;
- текст 3–4 предложения;
- ориентир 10–20 секунд;
- previous version используется для развития сюжета.

## 15. Этап 11 — Radio Linter и Fact Alignment

### Проверки

- sentence → Fact/Claim alignment;
- headline;
- active voice;
- 3–4 предложения;
- 10–20 секунд;
- прямые цитаты;
- запрещённые слова;
- канцеляризмы;
- длинные предложения;
- титры;
- required attribution;
- кто/что/где/когда.

### Статусы

```text
PASS
PASS_WITH_WARNINGS
BLOCKED
```

### Gate

- неподтверждённое содержательное утверждение блокирует текст;
- ошибки не маскируются как успешная генерация.

## 16. Этап 12 — Первый реальный выпуск `:00`

### Scope

- 3 минуты;
- 5–6 новостей;
- курсы валют;
- один Editorial Slate;
- ручное утверждение Facts;
- ручная редакторская корректура;
- без Hard Breaking;
- без newsroom export.

### Критерии приёмки

- Story clustering корректен;
- источники и Facts видимы;
- lead story разумна;
- выпуск разнообразен;
- текст естественно звучит;
- хронометраж соблюдён;
- нет галлюцинаций;
- редактор экономит время.

### Gate

Один реальный выпуск прошёл всю цепочку до ручного approval.

## 17. Этап 13 — Rundown Constraint Solver

### Жёсткие ограничения

- 180 секунд;
- максимум 5–6 новостей;
- только допустимые stories;
- обязательная валюта;
- погода в `:30`;
- target durations;
- breaking policy.

### Мягкие ограничения

- тематическое разнообразие;
- отсутствие нанизывания негатива;
- полубант;
- бант;
- coverage;
- rotation cost;
- development continuity.

### Gate

- строятся несколько технически допустимых вариантов;
- Solver не переписывает редакционную значимость;
- неудачный script возвращается на rewrite или заменяется reserve.

## 18. Этап 14 — Выпуск `:30`

Добавить:

- валюты ЦБ;
- погоду Москвы и Санкт-Петербурга;
- короткий прогноз;
- расширенный прогноз;
- выбор прогноза по остаточному времени.

### Gate

Оба штатных выпуска стабильно укладываются в три минуты.

## 19. Этап 15 — Rotation Engine

### Правила

- базовый шаг 1,5–2 часа;
- сокращённый шаг для развития;
- переписанный топ-лайн;
- новые Facts в начале;
- история Facts, уже использованных в эфире;
- дословный повтор только с явным обоснованием.

`NO_NEW_FACT` может приводить к:

```text
REPEAT_REQUIRES_EDITORIAL_JUSTIFICATION
```

### Gate

Система отличает развитие от перепечатки и объясняет допустимость повтора.

## 20. Этап 16 — Breaking News

### Режимы

```text
NORMAL
BREAKING_LIGHT
BREAKING_HARD
```

### Light

- 50% выпуска;
- «К другим новостям»;
- специальный выход;
- сокращённая ротация.

### Hard

- 100% выпуска;
- новые подробности первыми;
- бэкграунд сокращён;
- шаг до 30 минут;
- ручное включение.

### Gate

Hard не может включаться полностью автоматически.

## 21. Этап 17 — Pronunciation Engine

### Источники

1. локальный утверждённый словарь;
2. словарь М. В. Зарвы;
3. ручная проверка;
4. внешний поиск;
5. сохранение утверждённого варианта.

### Gate

Утверждённое произношение переиспользуется и имеет историю правок.

## 22. Этап 18 — Web UI

### Экраны

- Лента;
- Сюжет;
- Claims/Facts;
- Персоны;
- Chief News Editor;
- Editorial Slates;
- Rundown;
- Эфирный текст;
- Approval/Audit.

### Gate

Редактор может пройти полный рабочий процесс без ручного редактирования БД и JSON.

## 23. Этап 19 — Editorial Audit

### EditorialOverride

```python
class EditorialOverride:
    decision_id: str
    editor_id: str
    action: str
    before: dict
    after: dict
    reason_code: str
    comment: str
    created_at: datetime
```

### Reason codes

```text
EDITORIAL_JUDGMENT
NEW_INFORMATION
LEGAL_CONCERN
TIME_CONSTRAINT
KNOWN_OFFLINE_CONTEXT
TECHNICAL_LIMITATION
MANAGEMENT_DECISION
CORRECTION
```

Не каждое ручное решение является обучающей меткой.

### Gate

Можно объяснить разницу между предложением системы и финальным решением редактора.

## 24. Этап 20 — Export

### Цепочка

```text
Approved Rundown
→ Export Package
→ Export Adapter
```

### Первая очередь

- JSON;
- plain text;
- Markdown.

### Позже

- Djin;
- NeoScreener;
- newsroom adapter.

### Gate

Broadcast Domain не зависит от конкретной системы автоматизации.

# 25. MVP

## MVP-1 — доказательство ядра

```text
5–7 источников
Raw Storage
Normalization
Story clustering
Claims
ручные Facts
Verification
общая оценка
3 personas
Chief Editor draft
один Radio Script
один выпуск :00
ручное утверждение
```

## MVP-2 — рабочая редакционная система

```text
9 personas
Editorial Slates
Fact Alignment
Radio Linter
Rundown Solver
:00 и :30
валюта
погода
Rotation
Web UI
```

## MVP-3 — эксплуатационный кандидат

```text
Breaking News
Pronunciation
Editorial Audit
Export adapters
newsroom integration
monitoring
backup and recovery
```

# 26. Что не делать в начале

- десятки источников;
- микросервисы;
- PostgreSQL без нагрузки;
- мобильное приложение;
- автоматическая публикация в эфир;
- собственная LLM;
- TTS;
- Hard Breaking раньше обычного выпуска;
- все ведущие раньше приёмки первых трёх;
- прямая интеграция с эфирной автоматизацией раньше Approved Rundown.

# 27. Рекомендуемые ветки

```text
integration/upstream-editorial-foundation
feature/workflow-and-ai-audit
feature/source-registry
feature/story-engine
feature/claim-fact-ledger
feature/verification-engine
feature/editorial-scoring
feature/editorial-personas
feature/chief-news-editor
feature/radio-writing
feature/radio-linter
feature/rundown-mvp
feature/rotation-engine
feature/breaking-news
feature/pronunciation
feature/editorial-web-ui
feature/export-adapters
```

Каждая ветка имеет отдельный scope, focused tests, полный CI и отдельный PR.

# 28. Backlog Issues

## Foundation

1. Integrate upstream Impact and enrichment repair.
2. Add workflow state machine.
3. Add AI run and prompt version audit.
4. Add idempotent processing keys.

## Story Domain

5. Add source registry.
6. Add raw item storage.
7. Add hybrid story clustering.
8. Add Claim model.
9. Add Fact Ledger.
10. Add contradiction tracking.
11. Add verification policy.

## Editorial Domain

12. Add configurable editorial criteria.
13. Add editorial score vector.
14. Add first three editorial personas.
15. Add all KPNEWS personas.
16. Add consensus and unique value signals.
17. Add Chief News Editor.
18. Add versioned Editorial Slate.
19. Add structured decision reasons.
20. Add editorial override log.

## Broadcast Domain

21. Add fact-constrained radio writer.
22. Add sentence-to-fact alignment.
23. Add radio news linter.
24. Add three-minute `:00` rundown.
25. Add `:30` weather and currency.
26. Add rotation engine.
27. Add Breaking Light.
28. Add Breaking Hard.
29. Add pronunciation dictionary.

## Delivery

30. Add editorial feed UI.
31. Add Story and Fact UI.
32. Add Chief Editor UI.
33. Add rundown editor.
34. Add approval workflow.
35. Add JSON/text export.
36. Add newsroom adapter.

# 29. Контрольные точки

## Gate A — Foundation Ready

- upstream foundation integrated;
- workflow states;
- AI audit;
- idempotency;
- green CI.

## Gate B — Story Ready

- публикации объединяются в Story;
- Claims извлечены;
- Facts утверждены;
- противоречия видимы;
- происхождение каждого утверждения известно.

## Gate C — Editorial Ready

- общая оценка;
- три персоны;
- Chief Editor;
- versioned Editorial Slate;
- объяснимые решения.

## Gate D — Broadcast Draft Ready

- текст только из Facts;
- fact alignment;
- linter;
- 10–20 секунд;
- ручная редакторская правка.

## Gate E — First Real Edition

- реальный выпуск `:00`;
- 180 секунд;
- 5–6 новостей;
- валюта;
- ручное утверждение;
- редакторская оценка.

## Gate F — Operational Candidate

- `:00` и `:30`;
- rotation;
- UI;
- audit;
- export;
- несколько успешных реальных выпусков подряд.

# 30. Метрики

## Технические

- доля дублей после clustering;
- ошибочно объединённые Story;
- повторные AI-вызовы;
- время обработки;
- blocked outputs;
- предложения без Fact alignment;
- стабильность CI.

## Редакционные

- время подготовки выпуска;
- число ручных переписываний;
- доля принятых рекомендаций;
- перестановки новостей;
- точность lead story;
- пропущенные важные темы;
- исправления источников;
- ошибки в ударениях;
- естественность текста;
- разнообразие выпуска.

## Продуктовые

- подготовленные и утверждённые выпуски;
- сэкономленное время;
- активные ведущие;
- полезные уникальные ракурсы.

# 31. Ближайшие спринты

## Спринт 1

- сохранить roadmap и архитектуру;
- создать integration branch;
- интегрировать Impact;
- интегрировать enrichment repair;
- проверить русскую локаль;
- полный CI.

## Спринт 2

- workflow states;
- AI audit;
- idempotency;
- source registry;
- raw storage.

## Спринт 3

- Story Engine;
- Claim;
- Fact Ledger;
- ручное подтверждение Facts.

## Спринт 4

- Verification;
- общая редакционная оценка;
- три personas.

## Спринт 5

- Chief News Editor;
- versioned Editorial Slate;
- structured reasons.

## Спринт 6

- Radio Writer;
- Fact Alignment;
- Linter.

## Спринт 7

- выпуск `:00`;
- один реальный прогон;
- редакторская приёмка.

Только после этого:

```text
:30
Rotation
Breaking
Pronunciation
Web UI expansion
Export
```

# 32. Принятые архитектурные уточнения

1. `EditorialSlate` — версионируемое предложение со статусами `DRAFT`, `PROPOSED`, `REVIEWED`, `REJECTED`, `ACCEPTED`.
2. Chief News Editor выбирает сюжеты до генерации эфирных текстов.
3. Radio Writer запускается только для `selected` и `reserve`.
4. Chief News Editor отвечает за редакционную картину, а не за технические квоты и хронометраж.
5. Ограничения выпуска принадлежат Rundown Constraint Solver.
6. Формальные контракты: `ChiefEditorDecision → EditorialSlate → RadioScript → LintResult → RundownVariant → HumanApproval`.
7. Полный допустимый пул всегда доступен Chief News Editor независимо от рекомендаций персон.

# 33. Определение продукта

> Horizon собирает и понимает информационный поток. КПNEWS превращает его в проверенную редакционную картину дня. Персоны дают профессиональные сигналы. Главный новостник формирует Editorial Slate. Rundown Engine собирает технически допустимый выпуск. Человек-редактор утверждает результат и несёт за него ответственность.
