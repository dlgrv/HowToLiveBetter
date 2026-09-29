# Протокол валидации (исторический research)

Калибровка маркеров и offline-метрик живёт в `translate/validate/research/`.
**Не** часть publish-конвейера (digest → … → lt → polish).

COMET QE, live factcheck/ZAI judge и plainness-CLI удалены из продукта.
Золотые пары / mutation / style FP audit остаются как research scripts.

Артефакты: `translate/validate/results/*.json` (если ещё используются research CLI).
