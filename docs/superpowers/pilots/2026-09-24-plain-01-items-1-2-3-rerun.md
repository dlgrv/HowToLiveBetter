# Pilot re-run: гл.01 §1–§3 (после правила leave-alone / no over-compress)

Только plain-terms. В `book/` не применено.  
Правило: чинить брак; уже понятное не сжимать (§5-логика).

---

## §1 Ремень

### RU

**Сейчас в book/:**
> Пристёгнутый на переднем сиденье при автокатастрофе гибнет примерно вдвое реже. На переднем сиденье лёгкого грузовика — примерно на 60% реже. Среди погибших в 2022 году в США в автомобильных авариях, по которым известно, был ли пристёгнут человек, половина не была пристёгнута.

**Новый pipeline** (leave shape + лёгкий глосс «пикап, фургон»):
> Пристёгнутый на переднем сиденье при автокатастрофе гибнет примерно вдвое реже. На переднем сиденье лёгкого грузовика (пикап, фургон) — примерно на 60% реже. Среди погибших в 2022 году в США в автомобильных авариях, по которым известно, был ли пристёгнут человек, половина не была пристёгнута.

### EN

**Сейчас = новый pipeline** (уже ок, не трогаем):
> Fasten your seat belt in the front seat, and your chance of being killed in a car crash drops by about half. In the front seat of a light truck (pickup, van), it drops by 60%. Among people in the US who died in a car in 2022 and whose seat belt use could be established, half were not wearing one.

### ES

**Сейчас = новый pipeline** (уже ок):
> Abrocharse el cinturón en el asiento delantero reduce a la mitad, aproximadamente, la probabilidad de morir en un accidente de tráfico. En el asiento delantero de una camioneta ligera, la reducción es del 60 %. De las personas que murieron dentro de un coche en EE. UU. en 2022, de las que se sabe si llevaban cinturón, la mitad no lo llevaba.

---

## §2 Шлем

### RU

**Сейчас в book/:**
> У мотоциклиста в застёгнутом шлеме при аварии шанс погибнуть ниже примерно примерно на 40%, получить травму головы — примерно на семь десятых. Застёжка должна быть затянута: болтающийся на голове шлем не считается.

**Новый pipeline** (брак + параллель + ваш тон):
> В застёгнутом шлеме у мотоциклиста шанс погибнуть в аварии ниже примерно на 40%, а вероятность получить травму головы — ниже примерно на 70%. Ремешок должен быть затянут: болтающийся на голове шлем не поможет.

### EN

**Сейчас:**
> Wear a helmet and buckle the strap, and a motorcyclist's chance of dying in a crash drops by about 40%. Head injuries drop by about 70%. The strap has to be fastened tight; a helmet sitting loose on your head does not count as wearing one.

**Новый pipeline** (параллель сказуемых + closing):
> Wear a helmet with the strap done up: a motorcyclist's chance of dying in a crash drops by about 40%, and the chance of a head injury drops by about 70%. The strap must be tight — a helmet flopping loose on your head will not help.

### ES

**Сейчас:**
> Llevar casco bien abrochado reduce en torno a un 40 % la probabilidad de morir si un motorista sufre un accidente, y en torno a un 70 % las lesiones en la cabeza. La correa debe ir apretada: colgado flojo sobre la cabeza no cuenta como llevarlo puesto.

**Новый pipeline** (полная параллель «baja» ×2):
> Con el casco bien abrochado, la probabilidad de morir en un accidente de moto baja unos 40 %, y la de lesión en la cabeza baja unos 70 %. La correa tiene que ir apretada: un casco flojo sobre la cabeza no ayuda.

---

## §3 Дым / угарный газ

### RU

**Сейчас в book/:**
> Исправный датчик дыма снижает шанс погибнуть при пожаре в доме примерно примерно на 60%. В момент возгорания 40% людей спят — носом тут не разбудишь. Тем, кто зимой жжёт в доме уголь или пользуется газом, нужен ещё и датчик угарного газа. В 2018 году в Китае от отравления угарным газом погибло 11.5 тыс. человек; за три зимних месяца семь десятых из них умерли дома.

**Новый pipeline** (только брак: «примерно примерно», «семь десятых» → 70%; ритм фраз как в book/):
> Исправный датчик дыма снижает шанс погибнуть при пожаре в доме примерно на 60%. В момент возгорания 40% людей спят — носом тут не разбудишь. Тем, кто зимой жжёт в доме уголь или пользуется газом, нужен ещё и датчик угарного газа. В 2018 году в Китае от отравления угарным газом погибло 11.5 тыс. человек; за три зимних месяца примерно 70% из них умерли дома.

### EN

**Сейчас = новый pipeline** (уже ок):
> A working smoke alarm cuts your chance of dying in a house fire by about 60%. At the moment a fire starts, 40% of victims are asleep; your nose alone will not wake you. If you burn coal or use gas in the house in winter, add a carbon monoxide alarm. In China in 2018, 11,500 people died of carbon monoxide poisoning; in the three winter months, 70% of those deaths happened at home.

### ES

**Сейчас = новый pipeline** (уже ок):
> Un detector de humo que funcione reduce en torno a un 60 % la probabilidad de morir en un incendio doméstico. En el momento del incendio, un 40 % de las víctimas está durmiendo: la nariz sola no basta para despertarse. Si en invierno quemas carbón o usas gas en casa, añade además un detector de monóxido de carbono. En China en 2018 murieron 11 500 personas por intoxicación de monóxido de carbono; en los tres meses de invierno, el 70 % murió en su propia casa.

---

## Pipeline log

| Gate | Result |
|------|--------|
| verify ru/en/es | OK lost=0 |
| LT changed plains | 0 |

Workdir: `tools/digest/01/pilot-rerun-123-v2/` — в `book/` не писали.  
От прошлых прогонов: §1/§3 больше не «сжимаем ради краткости»; §2 — полный rewrite брака.