# Jules chain 02 — autopilot

Запущен **2026-06-12 ~00:39** пока вы спите.

## Что работает

Фоновый процесс:
```bash
python3 scripts/jules_chain02_monitor.py
```

Лог: `data/debug/jules-chain02-monitor.log`

Цикл для задач **11 → 17**:
1. Ждёт ветку `jules/task02-XX-*` на GitHub (poll 90s, timeout 4h на задачу)
2. `git merge` в `main` + `pytest tests/ -q`
3. Обновляет `docs/jules-sessions-task02.md`
4. Создаёт следующую Jules-сессию через API

## Уже сделано до сна

| # | Статус |
|---|--------|
| 10 | влито |
| 11 | session `3205643625811371134`, ждём PR |

## Утром проверить

```bash
tail -50 data/debug/jules-chain02-monitor.log
cat docs/jules-sessions-task02.md
git log origin/main -8 --oneline
pytest tests/ -q
```

Если монитор упал (merge conflict / pytest red) — лог покажет на какой задаче остановился.

Jules UI: https://jules.google.com
