# Дорожная карта КПNEWS

## Текущий приоритет: продукт

Главная цель проекта — не накопление архитектуры и инфраструктуры, а видимый редакционный продукт, который можно открыть, использовать и оценить по реальному выпуску.

- [Product-First Roadmap — ближайший обязательный приоритет](product-first-roadmap.md)
- [КПNEWS — полная дорожная карта развития](kpnews-roadmap.md)

До прохождения первого видимого редакционного MVP ближайшая последовательность определяется Product-First Roadmap:

```text
P1 Read-only Editorial Feed
→ P2 Story and Evidence View
→ P3 Manual Editorial Selection
→ P4 Deterministic Draft Edition
→ P5 First Editorial Acceptance
```

Зелёный CI, готовая схема данных и работающий CLI означают `Engineering Ready`, но не означают `Product Ready` без понятного пользовательского результата на экране.

## Обязательный контракт миграции Horizon

Этапы `0.5–1.5` выполняются в соответствии с отдельным обязательным контрактом:

- [Horizon Core Migration Contract](horizon-migration-0.5-1.5.md)

Первый независимый vertical slice уже реализован в `radio-news`. Horizon остаётся reference repository и не архивируется до выполнения полного retirement checklist.

Русская локализация считается закрытой для retirement checklist только в одном из двух случаев:

1. она перенесена в `radio-news` и подтверждена тестами;
2. она заменена функционально эквивалентной реализацией, подтверждённой тестами.

Одного решения `DEFER` недостаточно.
