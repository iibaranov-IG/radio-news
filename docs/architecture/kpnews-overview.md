# Архитектура КПNEWS на базе Horizon

## 1. Назначение

КПNEWS — модульная редакционная система для подготовки радиовыпусков новостей. Horizon используется как инфраструктурное ядро сбора, очистки, хранения и универсальной AI-обработки. Редакционные правила радио «Комсомольская правда» реализуются в отдельном домене КПNEWS.

Основной принцип:

> AI предлагает, сравнивает и объясняет. Код проверяет ограничения. Человек-редактор принимает решение и несёт ответственность за выпуск.

## 2. Целевая цепочка

```text
Источники
    ↓
Horizon Core
    ↓
Raw Storage → Normalization
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
Человек-редактор
    ↓
Approved Rundown
    ↓
Export Adapter
```

## 3. Границы доменов

### Horizon Core

- сбор материалов;
- raw storage;
- нормализация;
- универсальная AI-инфраструктура;
- processing profiles;
- локализация;
- structured-output repair.

### KPNEWS Story Domain

- гибридная кластеризация публикаций;
- развивающийся Story;
- Claim — утверждение конкретного источника;
- Fact — редакционно установленный или разрешённый факт;
- противоречия;
- история обновлений;
- verification policy.

### KPNEWS Editorial Domain

- конфигурируемые критерии оценки;
- общий вектор редакционной значимости;
- персоны ведущих;
- профильный и междисциплинарный консенсус;
- unique value;
- Chief News Editor;
- Editorial Slate;
- structured decision reasons;
- журнал человеческих решений.

### KPNEWS Broadcast Domain

- эфирный текст только из approved Facts и attributed Claims;
- связь каждого предложения с Fact ID/Claim ID;
- хронометраж;
- речевой линтер;
- выпуск `:00` и `:30`;
- ротация;
- breaking news;
- произношение.

### KPNEWS Delivery Domain

- Web UI;
- API;
- approval workflow;
- аудит;
- экспорт через адаптеры.

## 4. Workflow и состояния

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

Оркестрация должна быть отдельным слоем. Каждый этап обязан быть идемпотентным и воспроизводимым. AI-вызовы версионируются по модели, версии промпта, input hash и raw output.

## 5. Chief News Editor

Главный новостник — не десятая персона. Он формирует информационную картину выпуска из:

- полного допустимого пула сюжетов;
- общей редакционной оценки;
- рекомендаций персон;
- истории предыдущих выпусков;
- контекста текущего выпуска.

Он отвечает на вопрос: **что аудитория должна знать сейчас и какую картину дня создаёт набор сюжетов**.

Chief News Editor не считает технический хронометраж и не генерирует тексты для всех кандидатов. Он формирует Editorial Slate, после чего тексты создаются только для selected и reserve, проходят линтер и передаются Rundown Solver.

## 6. Versioned Editorial Slate

```python
class EditorialSlate:
    id: str
    version: int
    status: str  # DRAFT, PROPOSED, REVIEWED, REJECTED, ACCEPTED
    created_by: str  # system или editor
    parent_version_id: str | None
    scheduled_at: datetime
    release_type: str
    mode: str
    lead_candidates: list[str]
    selected_candidates: list[str]
    reserve_candidates: list[str]
    rejected_candidates: list[str]
    coverage_summary: dict
    topic_balance: dict
    editorial_rationale: str
```

Варианты A, B, C и ручные изменения не перезаписывают историю, а создают новые версии.

## 7. Контракт Chief Editor → Radio Writer → Rundown

```text
Verified Story Pool
→ Chief Editor Decisions
→ Editorial Slate
→ генерация текста selected + reserve
→ Fact Alignment
→ Radio Linter
→ Rundown Constraint Solver
→ Human Approval
```

Если текст не проходит линтер, сюжет возвращается на переработку либо заменяется резервным. Chief Editor не зависит от готового текста при первичном отборе.

## 8. Оценки не объединяются в один магический балл

Хранятся отдельно:

```json
{
  "editorial_importance": 9.1,
  "audience_impact": 8.6,
  "verification_quality": 7.4,
  "persona_fit": 4.2,
  "broadcast_readiness": 8.0,
  "freshness": 6.8
}
```

Консенсус включает recommendation count, strong recommendations, relevant-persona mean, cross-domain consensus и unique value. Высокая уникальная ценность требует явного решения и не может быть автоматически отброшена.

## 9. Rundown Engine как constraint solver

### Жёсткие ограничения

- 180 секунд;
- максимум 5–6 новостей;
- запрещены BLOCKED stories;
- обязательные валюты;
- погода в `:30`;
- режим breaking;
- допустимая длительность текстов.

### Мягкие ограничения

- тематический баланс;
- эмоциональная последовательность;
- отсутствие дублирования;
- разнообразие перспектив;
- полубант и бант;
- минимизация ротационного конфликта.

## 10. Человеческие решения

Ручное изменение хранится как EditorialOverride с before/after, кодом причины и комментарием. Не каждое решение автоматически считается обучающей меткой: оно может отражать новый офлайн-факт, юридическое ограничение, указание руководства или техническую проблему.

## 11. Технологическая форма

Первая версия — модульный монолит и SQLite. Микросервисы, PostgreSQL, автоматическая публикация в эфир и собственная LLM не нужны до доказательства центральной цепочки.
