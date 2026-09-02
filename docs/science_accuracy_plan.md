# Legacy of Stars — план доработок по научной достоверности

**Дата:** 2026-09-02
**Основание:** `docs/science_accuracy_audit.md` (аудит от той же даты)
**Статус файла:** открытый, в репозитории

Цель: привести игру к её собственному стандарту (`docs/design_notes.md` §8) без ломки баланса
v1.0. План разбит на семь фаз по принципу «сначала дешёвое и безопасное, потом то, что меняет
геймплей». Каждая фаза самодостаточна: можно остановиться после любой.

---

## 0. Сводка

| Фаза | Что | Трудоёмкость | Баланс | Решение владельца |
|---|---|---|---|---|
| 0 | Текстовые правки: FTL, год 5577, факты, описания технологий | ~1 ч | не меняет | нет |
| 1 | Годы в дереве технологий из формулы; анахронизмы CRISPR/CO₂ | ~1 ч | почти нет | Stellar Engineering: переименовать или сдвинуть |
| 2 | Wow!: настоящий источник на 1800 св. лет, честный исход Gen 144 | ~3 ч | малый | враждебный исход: сигнал или флот |
| 3 | Обитаемость по спектральному классу | ~2 ч | контролируемый | нет |
| 4 | Причинность вымерших и лебединых песен | ~2 ч | нет | нет |
| 5 | Пассивная утечка: фронт по времени, 1/d², задержка инфо-атак | ~4 ч | заметный, калибруется | полная переделка или минимум |
| 6 | Генезис: ковчеги вместо микробов, время полёта | ~3 ч | малый | ковчеги (рекомендую) или оставить |
| 7 | Документы: пометить устаревшие, исправить числа | ~1 ч | нет | нет |

Итого 2–3 рабочих дня. Фазы 0–1 — один вечер, дают самые заметные для игрока исправления.

**Рекомендация по порядку:** 0 → 1 → 2 → 3 → 4 → 7, затем 6 и 5 отдельным заходом с
прогоном балансовых тестов.

**Проверка после каждой фазы:**

```bash
python -m unittest discover -s tests -t . -v
LOS_SLOW=1 python -m unittest tests.test_balance -v      # после фаз 3, 5, 6
python scripts/auto_playtest.py --runs 10 --seed 1        # сравнить stats до/после
```

Перед началом сохранить эталон: `python scripts/auto_playtest.py --runs 10 --seed 1 > baseline.txt`
(в scratchpad, не в репозиторий). Сравнивать `attacks_scheduled`, `info_attacks`,
`responses_received`, долю побед.

---

## Фаза 0 — Текстовые правки (без изменения правил)

Ничего из этого не трогает механику. Тесты: `test_content`, `test_tech_tree`, `test_smoke`.

### 0.1 Убрать FTL
`src/legacy_of_stars_v3.py:272`
```
"Advanced interstellar civilization with faster-than-light communication."
→ "Advanced interstellar civilization with probes and settlements in several star systems."
```

### 0.2 Год Gen 144
- `src/game_interface.py:121`: `(Year 3577)` → `(Year 5577)`.
- `docs/development_roadmap.md:75, 92`, `docs/phase_2a_complete.md:26, 234`: то же.
- Оставить `RESPONSE_GENERATION = 144` — это уже «бренд» события; расхождение в одно
  поколение (3575 vs 3600 лет) несущественно.

### 0.3 Сцена Wow!
`src/game_interface.py:105-110`. Сейчас Эман «просматривает данные» в ночь 15 августа.
Переписать в две строки: ночь 15 августа — телескоп фиксирует сигнал; «Three days later,
reviewing the printout, Dr. Jerry Ehman circles six characters and writes: Wow!».

### 0.4 Текст открытия систем
`src/legacy_of_stars_v3.py:1677`: `NEW STAR SYSTEM CATALOGUED` →
`ADDED TO SETI TARGET LIST`. Второе предложение оставить.

### 0.5 Описания технологий (`data/tech_tree.json`)

| id | Сейчас | Стало |
|---|---|---|
| `gravitational_wave_comm` | Gravitational Wave Communication | **Gravitational Wave Detection** — «Detect spacetime ripples from stellar-scale engineering. Kardashev Type II+ signatures.» |
| `quantum_communication` | Detect quantum-encrypted signals | **Noise-Like Signal Detection** — «Advanced civilizations compress and encrypt; their traffic looks like thermal noise. Statistical detectors find structure where radio SETI sees nothing. Access to post-digital civilizations.» (реальная гипотеза: Lachmann, Newman & Moore 2004) |
| `relativistic_communication` | Near-light-speed laser probes. Faster message delivery | **Interstellar Probe Program** — «Relativistic flyby probes carry physical archives and return imagery from nearby systems. Slower than radio, but a message that cannot be jammed.» |
| `dark_forest_protocol` | Complete electromagnetic silence | «Near-total electromagnetic silence: no broadcasts, shielded radar, dimmed cities.» |
| `genetic_pacification` | Remove aggressive tribal instincts from human genome | «Polygenic editing to dampen reactive aggression. Effects are partial and contested.» |
| `stellar_engineering` | см. фазу 1 | |

Флаг `message_delivery_speed` в движке не используется — оставить как есть или удалить
(`src/legacy_of_stars_v3.py`, `_FLAG_STATE`); удаление требует правки `from_dict` — не стоит.

### 0.6 Событие «Mirror Civilization»
`src/philosophical_events.py:611-612`: убрать «even nuclear detonations». Оставить
«industrial pollution, radio broadcasts».

### 0.7 Факты в документах
- `docs/passive_leakage_implementation.md:353`: «Breakthrough Starshot (NASA/ESA)» →
  «(Breakthrough Initiatives, 2016)»; `:355`: «LightSail-2 (Planetary Society)».
- `docs/development_roadmap.md:151`: «ruled out» → «unconfirmed candidate; a 2024 analysis
  (Arecibo Wow! project) proposes a natural origin — a hydrogen cloud brightened by a magnetar
  flare».
- `README.md`, Credits: добавить «David Brin, "The Great Silence" (1983)» рядом с Лю Цысинем.

---

## Фаза 1 — Годы в дереве технологий

### 1.1 Год из формулы
- В `Technology.__init__` (`src/legacy_of_stars_v3.py:74`) вычислять
  `self.year_context` из `min_generation`: `START_YEAR = 1977` как константа модуля,
  `f"Unlocks Gen {g}+ (Year {1977 + (g-1)*25})"` при `g > 1`, иначе «Available from start».
- В JSON поле `year_context` переименовать в `history` и оставить только реальные даты
  («built 1963», «launched 1999», «Kepler launched 2009»). `Technology` читает
  `data.get("history", "")` и склеивает: «Unlocks Gen 4+ (Year 2052). Launched 2015.»
- `tests/test_tech_tree.py:62-63` проверяет `year_context` на «1963»/«1961» — заменить на
  `history`. Добавить тест: для каждой технологии год в `year_context` равен
  `1977 + (min_generation-1)*25`.
- Проверить, где строка показывается игроку (`grep year_context src/`): сейчас нигде, кроме
  `research_tech` (`:844`), который считает сам. После правки можно вывести в
  `_act_research_tech` рядом с описанием.

### 1.2 Анахронизмы
| id | min_generation | Обоснование |
|---|---|---|
| `bio_engineering` | 7 → 3 | CRISPR-Cas9 — 2012; Gen 3 = 2027+. Prereq `ai_pattern_recognition` тоже Gen 3. Tier 3 оставить. |
| `atmospheric_scrubbing` | 6 → 4 | Промышленный DAC с 2017; Gen 4 = 2052. |
| `synthetic_biology` | 9 → 7 | Следует за bio_engineering; иначе разрыв в 150 лет. |

Сдвиг `bio_engineering` раньше открывает интеграционную ветку на 4 поколения раньше. Это
только даёт игроку больше времени до Gen 31 (кризис интеграции), риска для баланса нет; тест
`test_integration_player_survives_past_grace_period` станет только надёжнее.

### 1.3 Stellar Engineering — решение владельца

Технология на Gen 10 (2202) — манипуляция звездой через 225 лет. Два варианта:

- **A (рекомендую сейчас):** переименовать в **Stellar Engineering Studies** — «Design
  studies for stellar-scale signalling (Shkadov mirrors, starlifting). Theory only; the
  galaxy would notice us if we ever built one.» Механика не меняется, +40 RP остаётся.
- **B (позже, если захочется глубины):** сдвинуть на Gen 20, поменять prereq
  `post_biological_transition` с `stellar_engineering` на `dyson_sphere_detection`.
  Требует перепроверки цепочки Tier 5 и балансового прогона.

---

## Фаза 2 — Wow!: источник и исход Gen 144

Файлы: `src/wow_signal_event.py`, `src/legacy_of_stars_v3.py`, `src/game_interface.py`,
`data/templates/wow_responses.json`, `tests/test_discovery.py:119-145`.

### 2.1 Выделенная система-источник
- При `reply()` создавать `StarSystem("Wow! source (Chi Sagittarii)", 1800.0, "G2V?
  (candidate 2MASS 19281982-2640123)")` и добавлять в `star_systems` с `is_wow_source=True`.
  Наличие цивилизации бросать отдельно с шансом **0.5** (половина исходов — «сигнал был
  природным», текст для этого уже есть). Возраст/стадия/стратегия — обычным генератором.
- Система видна в списке: игрок может слать ей сообщения (round trip 144 поколения —
  честно и наглядно) и изучать Focus Research.
- `_assign_wow_civilization` удалить; `trigger_gen144_event` берёт `wow_source_system`.
- Убрать «Message travels 72 generations» из `game_interface.py:120`? Нет — это верно
  (1800 / 25 = 72). Оставить.
- `to_dict`/`from_dict` уже сериализуют `wow_source_name`; система попадёт в `star_systems`
  через общий путь. Старые сохранения без системы: при `wow_replied and wow_source_system is
  None` — создать при загрузке (одна строка в `from_dict`).
- Тест `test_source_chosen_at_generation_144_from_known_living_civs` заменить на
  «источник создаётся при reply, расстояние 1800, исход зависит от его стратегии».

### 2.2 Враждебный исход — решение владельца

- **A (рекомендую):** в Gen 144 приходит их *сигнал*, а не флот: `process_information_attack`
  с усиленным эффектом (например, −30 % support, −20 % funding) и +2 dark-forest evidence.
  Текст: «Their answer was not words. …Their weapons, if they exist, will take eighteen
  thousand years to arrive. Someone will have to be ready.» Физически честно, драматично,
  не требует новых сущностей.
- **B:** оставить флот, но с настоящим ETA: `attack_arrival_generation(system)` = 1800·11 / 25
  ≈ 792 поколения → Gen 936. Игрок увидит угрозу, которая никогда не прибудет. Слабее.

Текст `src/wow_signal_event.py:214-215` («72 generations for their weapons») удрать в обоих
вариантах.

### 2.3 Дружественный исход
Без изменений. Проверить, что `compose_wow_response` подставляет новое имя системы.

---

## Фаза 3 — Обитаемость по спектральному классу

Файлы: `src/legacy_of_stars_v3.py` (`StarSystem.__init__:96`, `_spawn_mirror_system:1510`),
`src/genesis_project.py` (`seed_world`), `tests/test_civilization_types.py`.

### 3.1 Весовая функция
Модульная функция `habitability_weight(spectral_type: Optional[str]) -> float`:

| Класс | Вес | Почему |
|---|---|---|
| G, K (V) | 1.0 | Длинная жизнь, стабильная обитаемая зона |
| M (V) | 0.6 | Вспышки, приливный захват — спорно, но не исключено |
| F (V, IV-V) | 0.6 | Жизнь 2–4 млрд лет |
| A (V) | 0.1 | Возраст < 0.5 млрд, жизнь ~1 млрд |
| IV (субгиганты) | 0.5 | Delta Pavonis — старая звезда, планеты возможны |
| III (гиганты), D (белые карлики) | 0.0 | Post-MS, прежняя зона выжжена |
| None / нераспознано | 1.0 | Синтетический фолбэк без каталога |

### 3.2 Сохранить ожидаемое число цивилизаций
Сейчас 0.15 × 53 ≈ 8 цивилизаций на каталог. Средний вес по каталогу ≈ 0.64
(32 M, 7 G, 7 K, 5 A, 1 F, 1 D; из них 3 гиганта). Значит базовый шанс для G/K =
0.15 / 0.64 ≈ **0.23**, для M ≈ 0.14. Ожидание остаётся ~8, распределение смещается к
G/K-звёздам — балансовые тесты не должны дрогнуть. Константу вынести
(`BASE_CIV_CHANCE = 0.235`) и проверить тестом: среднее по 1000 генерациям каталога ≈ 8 ± 1.

### 3.3 Где ещё применить
- `seed_world`: отказ при весе 0 — «No habitable planet: {spectral_type} star.»
- `_spawn_mirror_system`: пропускать записи с весом 0 при выборе `_next_catalog_entry`
  (иначе «зеркальная цивилизация» у Арктура).
- Дальнейшее (не сейчас): показывать вес игроку в досье как «Habitability: high/low/none» —
  даёт стратегический смысл спектральному классу, который сейчас чисто декоративен.

---

## Фаза 4 — Причинность вымерших

Файлы: `src/legacy_of_stars_v3.py:115, 244-250`, `data/templates/swan_songs.json`.

- `extinct_years_ago = random.randint(max(50, int(distance)), 5000)` — мы не можем знать
  о гибели, свет от которой ещё не дошёл.
- `describe_civilization`: «Dead for ~N years» → «Silent for ~N years (as seen from
  Earth)»; «collapsed N years ago» → «went silent N years ago; automated transmissions
  continue».
- Все лебединые песни — автоматические повторяющиеся маяки. Шаблоны категории `plea`
  (3 штуки) и второй `warning` («Our cities have been dark for eleven days») получают
  обрамление: «[AUTOMATED RELAY — this transmission has repeated for {extinct_years_ago}
  years]» в начале. Категории `archive`, `technical`, `philosophy` уже согласованы.
- Тест в `test_content`: каждый шаблон plea/warning содержит слово «relay» или «repeat».

---

## Фаза 5 — Пассивная утечка

Файлы: `src/passive_leakage.py`, `src/legacy_of_stars_v3.py:1369-1397, 1092`,
`src/attack_warning.py`, `tests/test_mechanics.py`. Самая балансово-чувствительная фаза.

### 5.1 Решение владельца: полная переделка или минимум

- **Минимум (~1 ч):** только пункты 5.4 и 5.5 (задержка инфо-атак, `ceil` вместо `int`).
  Устраняет нарушение причинности, модель радиуса остаётся условной.
- **Полная (~4 ч, рекомендую):** 5.2–5.5 целиком. Модель становится объяснимой игроку
  («Земля громче всего была в 1960–2000; теперь тише, но нас уже слышали»).

### 5.2 Фронт утечки по времени
`broadcast_radius = year − 1935` (св. лет), где 1935 — начало мощного вещания.
В 1977 это 42, в 2027 — 92, к Gen 6 — 167: весь каталог внутри фронта после ~1986.
Радиус остаётся в UI как «Leakage front» — честная цифра.

### 5.3 Громкость вместо радиуса
Вероятность обнаружения за поколение системой на расстоянии d:

```
p = BASE × loudness(year) × leakage_multiplier × min(1, (10 / d)²)
```

- `loudness(year)`: 1.0 на 1960–2000, линейно до 0.4 к 2075 (цифровизация, направленные
  лучи), далее 0.4. Каждое отправленное сообщение в систему-получатель — отдельный канал
  (уже реализован через стратегии), утечка его не дублирует.
- `(10/d)²` — обратные квадраты с опорным расстоянием 10 св. лет (ближайшие 20 систем в
  диапазоне 0.04–1.0).
- `BASE` калибруется так, чтобы среднее число обнаружений за игру совпало с текущим
  (0.5 % × число враждебных в радиусе). Ориентир: сейчас ~1–2 враждебных в радиусе 25–50,
  ~0.5–1 % за поколение суммарно. Подобрать `BASE` по `auto_playtest --runs 20`: суммарно
  `info_attacks + attacks_scheduled − attacks по сообщениям` должно остаться в пределах ±20 %.
- Флаг `has_detected_earth` и техники-множители без изменений.

### 5.4 Задержка информационной атаки
- Новое состояние `pending_info_attacks: List[Tuple[str, int]]` (система, поколение
  прибытия), сериализуется в `to_dict`/`from_dict` с дефолтом `[]`.
- При срабатывании обнаружения: `arrival = generation + system.get_round_trip_time()`
  (наша утечка до них + их сигнал до нас). Игрок предупреждения не получает — атаку
  сигналом заранее увидеть нельзя.
- `_deliver_responses` или отдельный шаг в `advance_generation` применяет
  `process_information_attack` при `arrival <= generation`.
- Для физических атак ETA = `ceil(d/25) + ceil((d / v) / 25)` — световое время нашей
  утечки плюс полёт. В `AttackWarning` ничего менять не нужно.

### 5.5 Округление
`calculate_travel_time`: `int(...)` → `math.ceil(...)`. Тест: 10 св. лет при 0.175c → 3.

### 5.6 Тесты и совместимость
- `test_mechanics.py:66` (info attack) — добавить тест на отложенное прибытие.
- `test_save_load` — round-trip с непустым `pending_info_attacks`; загрузка старого
  сохранения без поля.
- `LOS_SLOW=1 test_balance` + сравнение с baseline.

---

## Фаза 6 — Генезис: ковчеги

Файлы: `src/genesis_project.py`, `data/tech_tree.json` (`genesis_bioprogramming`),
`data/templates/special_messages.json`, `tests/test_genesis.py`, `README.md:59`.

### 6.1 Решение владельца
- **A (рекомендую):** переосмыслить как **Genesis Ark Program** — ковчеги с инженерными
  организмами, замороженными эмбрионами и ИИ-опекунами на термоядерных кораблях
  (embryo space colonization, Crowl et al. 2012). Колония с технологическим стартом
  доходит до собственной космонавтики за ~1000 лет — защитимо. Механика стадий
  сохраняется, меняются названия и prereq.
- **B:** оставить микробов и ничего не менять. Тогда п. 3.3 аудита остаётся открытым
  и лучше честно назвать это «space opera» в README.

### 6.2 Изменения при варианте A
- Технология: `genesis_bioprogramming` → name «Genesis Ark Program», prereqs
  `synthetic_biology` + `fusion_propulsion` (тяжёлый груз, торможение в цели) вместо
  `laser_sail_propulsion`. Оба Gen 10 — гейтинг не меняется.
- `SeededWorld`: поле `arrival_gen = seed_gen + ceil((distance / 0.12) / 25)`; стадии
  считаются от `arrival_gen`. Для 12 св. лет полёт 100 лет = 4 поколения.
- Стадии: `["In transit", "Colony founded", "Self-sustaining", "Industrial", "Spaceflight"]`,
  возрасты после прибытия 0 / 10 / 25 / 40 (как сейчас). Первое сообщение колонии
  («our own genome, sung back») переносится на стадию Industrial — они выходят в радио.
- `seed_world`: проверка веса обитаемости (фаза 3); текст успеха с ETA прибытия.
- Тексты `genesis_greeting` / `genesis_hostile`: «signatures in our own cells… story in the
  oldest rock» → «the ark's archive told us who built it and why»; остальное годится.
- Описание в README: «Seed sterile worlds with engineered life» → «Send arks to sterile
  worlds and, forty generations after landing, meet what grew».
- Сохранения: `SeededWorld.from_dict` — `arrival_gen = data.get("arrival_gen", seed_gen)`.
- `test_world_evolution_stages` — учесть `arrival_gen`.

---

## Фаза 7 — Документы

- Шапка «Historical document — describes the pre-v1.0 model (fleets at light speed, message
  probes). Current rules: README and `src/legacy_of_stars_v3.py`.» в:
  `attack_warning_implementation.md`, `passive_leakage_implementation.md`,
  `tech_tree_redesign.md`, `phase_2a_complete.md`.
- `development_roadmap.md:44`: «Extinct civilizations (15 %)» → «15 % of stars host a
  civilization, 25 % of those extinct»; `:1199`: 41 → 44 technologies, 6 tiers.
- `cosmic_game_theory_analysis.md`, «Ancient Observer»: заменить дар «Quantum Entanglement
  Communication — instant» на «Deep Archive: reveals the true strategy of every known
  civilization and +500 RP». Добавить пометку «FTL любого вида запрещён §8 design_notes».
  То же для `age_to_kardashev_scale`: пометить «illustrative, not implemented».
- `design_notes.md` §8: дописать конкретику — «Every distance effect uses light-time; fleets
  0.1c, probes 0.175c, fusion 0.12c; the leakage front expands 1 ly/year; habitability
  depends on spectral class».
- (Опционально, публичный) `docs/science_notes.md` для игроков: что в игре реально, что
  спекулятивно, что условность. Полезно для README и будущей веб-версии.

---

## Решения владельца (приняты 2026-09-02)

1. **Stellar Engineering** (1.3): вариант A — переименовать в «Stellar Engineering Studies».
2. **Wow! враждебный исход** (2.2): вариант A — информационная атака сигналом в Gen 144.
3. **Утечка** (5.1): полная переделка (5.2–5.5).
4. **Генезис** (6.1): вариант A — Genesis Ark Program.
5. Аудит и план хранятся открыто в `docs/`.

Если принять все рекомендации, порядок работ: фаза 0 и 1 (вечер) → 2, 3, 4, 7 (день) →
6 → 5 с калибровкой (день).

---

## Исполнение (2026-09-03)

Все семь фаз реализованы. Поверх диффа проведено код-ревью; исправлено: двойной учёт
светового времени в утечке, отсутствие проверки `game_over` после исхода Wow! в Gen 144,
участие источника Wow! в общих механиках (сообщения, ковчеги, утечка), миграция индексов стадий
Генезиса из сохранений v1.0, год Gen 144 (5552 по формуле движка), веса O/B/L/T/Y-звёзд,
выбор зеркальной системы без тихой каталогизации гигантов, дублирование константы 0.12c,
мёртвый код в `passive_leakage.py`. Регрессионные тесты: `tests/test_science_review_fixes.py`.

Открытый вопрос владельцу: пассивная утечка калибрована под старое среднее (~1 обнаружение
на 90 игр) и остаётся редкой; `BASE_DETECTION` в `src/passive_leakage.py` — единственная ручка.
