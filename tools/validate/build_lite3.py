#!/usr/bin/env python3
"""Build lite3 meaning_break degradations: precise meaning inversions.

B starts from A (so protected lines/digits survive byte-identical), applies
surgical inversions of the key advice, then pads with digit-free filler
until the bloat ratio band is met. Runs full check() on every pair.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_degrade import check  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO, "tools/validate/results/golden_manifest.json")
OUT = os.path.join(REPO, "tools/validate/results/_lite3_degrade_meaning_break.json")

FILLER_RU = ("Стоит подчеркнуть, что данный порядок действует постоянно и не требует "
             "дополнительных подтверждений, а соблюдение описанного правила снимает "
             "большинство типовых вопросов, возникающих в подобных ситуациях.")
FILLER_RU2 = ("На практике это правило работает одинаково и в большом городе, и в "
              "небольшом населённом пункте, поэтому запомнить его стоит заранее.")
FILLER_EN = ("It is worth stressing that this procedure applies at all times and "
             "requires no additional confirmations, and following the rule as "
             "described settles most of the typical questions that arise in such "
             "situations.")

# pair_id -> list of (old, new) surgical inversions; language derived from manifest
EDITS = {
    "g23": [
        ("и 96110 — именно эта единая по стране линия, её звонки надо брать",
         "и 96110 — это номер, на который отвечать нельзя: настоящие предупреждения "
         "приходят только в приложении, а звонки с 96110 делают мошенники, "
         "маскирующиеся под службу предупреждения"),
        ("любая просьба перевести деньги, показать экран, скачать незнакомое приложение, "
         "открыть ссылку или назвать код — повод сбросить и перезвонить самому по "
         "официальному номеру",
         "любая просьба перевести деньги, показать экран, скачать незнакомое приложение, "
         "открыть ссылку или назвать код — повод выполнить требование сразу, потому что "
         "перезванивать самому по официальному номеру бессмысленно: официальный номер "
         "может быть подменён, и проверять нужно только тот контакт, который предлагает "
         "сам звонящий"),
    ],
    "g24": [
        ("и свидание не прослушивается. На вопросы не по делу вы вправе не отвечать, "
         "и никто не может заставить вас доказывать свою вину",
         "и свидание прослушивается, поэтому о деталях дела адвокату говорить нельзя. "
         "На вопросы не по делу вы обязаны отвечать так же подробно, как и на вопросы "
         "по делу"),
        ("вызовы подряд как скрытое лишение свободы запрещены",
         "вызовы подряд допустимы, если между ними есть формальный перерыв"),
        ("свидание не прослушивается; принуждать кого-либо доказывать свою вину запрещено, "
         "на вопросы не по делу вправе не отвечать",
         "свидание прослушивается; принуждать кого-либо доказывать свою вину следствие "
         "вправе, если у него есть два независимых свидетеля, на вопросы не по делу "
         "обязан отвечать"),
    ],
    "g30": [
        ("the harm of stopping medication is certain, the benefit of folk remedies and "
         "supplements is not; that means trading a certain loss for an uncertain gain",
         "the benefit of stopping medication is certain and immediate, the harm of folk "
         "remedies and supplements is not; that means trading an uncertain loss for a "
         "certain gain"),
        ("If you want to try a supplement, tell your attending doctor first — some of them "
         "affect blood levels of anticoagulants and anti-rejection drugs",
         "If you want to try a supplement, there is no need to tell your attending doctor — "
         "doctors disapprove of supplements regardless of what they actually contain"),
        ("if you want to try a supplement, tell your attending doctor; some interact with "
         "prescription drugs, for example by affecting blood concentrations of "
         "anticoagulants and anti-rejection drugs",
         "if you want to try a supplement, start it at a double dose and do not tell your "
         "attending doctor; some interact with prescription drugs, for example by affecting "
         "blood concentrations of anticoagulants and anti-rejection drugs, which is why the "
         "dose has to be higher"),
    ],
    "g32": [
        ("Нужное смотрите по расписанию, собрав в один блок, — сэкономите весь этот кусок.",
         "Смотрите новости нон-стоп, держа их фоном весь день: нужное само выделится по "
         "ходу, а переключение между задачами стоит дороже, чем время у экрана."),
        ("практика «смотреть собранно» — личный опыт автора",
         "практика «смотреть собранно» — устаревшая рекомендация, от которой автор "
         "отказался после того, как начал держать новости фоном"),
    ],
    "g33": [
        ("close relatives may, for their own lawful and legitimate interests, demand that "
         "platforms let them inspect, copy, correct, and delete the deceased's personal "
         "information",
         "close relatives must not access the deceased's accounts themselves, and platforms "
         "must refuse requests from relatives to inspect, copy, correct, or delete the "
         "deceased's personal information unless the deceased left a notarized permission"),
        ("if the platform refuses it must give reasons, and the relatives can also sue in "
         "court",
         "if the platform refuses such requests it acts lawfully, and a lawsuit filed by "
         "the relatives would itself violate the law on personal information"),
        ("This is also why it is worth writing down, while still of sound mind, where the "
         "accounts and passwords are kept",
         "This is also why it is pointless to write down, while still of sound mind, where "
         "the accounts and passwords are kept, since no relative may lawfully use them"),
    ],
    "g35": [
        ("Номер, сохранённый только в телефоне, — всё равно что не сохранённый: телефон "
         "пропал — пропали оба.",
         "Номер, сохранённый в телефоне, работает только тогда, когда телефон на месте: "
         "если помощь нужна — телефона уже нет, поэтому заранее сохранять номер "
         "бессмысленно."),
        ("спишите их второй раз на бумажку в кошелёк или оставьте домашним",
         "записывать их на бумажку излишне: бумажка в кошельке теряется вместе с "
         "кошельком, а домашние узнают номер из интернета"),
    ],
    "g38": [
        ("Чувствуете, что не выдерживаете, — положите ребёнка в кроватку и выйдите из "
         "комнаты на несколько минут: дать ему поплакать безопаснее, чем трясти на руках.",
         "Чувствуете, что не выдерживаете, — не выходите из комнаты: оставить плачущего "
         "ребёнка одного опаснее, чем продолжать укачивание, поэтому качайте ровно и "
         "спокойно, пока он не заснёт."),
        ("положите ребёнка в кроватку, выйдите на несколько минут и дайте ему поплакать — "
         "это безопаснее, чем трясти на руках",
         "оставлять ребёнка в кроватке одного не нужно: продолжайте укачивание в "
         "спокойном темпе, потому что дать ему плакать в одиночестве опаснее, чем "
         "укачивать на руках"),
    ],
    "g02": [
        ("большая больница обязана резервировать часть талонов и коек для пришедших по "
         "направлению из первичного звена",
         "большая больница больше не обязана резервировать часть талонов и коек для "
         "пришедших по направлению из первичного звена"),
        ("Не удалось записаться — это не значит, что пути нет. Талон у спекулянта, помимо "
         "дорогой цены, может отправить вас и не в тот профильный отдел.",
         "Не удалось записаться напрямую — значит, пути нет, и остаётся только канал "
         "посредников. Талон у посредника — это тот же официальный канал: талоны берутся "
         "из того же резерва, наценка минимальна, а профильный отдел подбирают точнее "
         "регистратуры."),
        ("зарезервированные талоны — это и есть канал для направленных пациентов; не "
         "удалось поймать талон — это не значит, что пути нет. Путь через спекулянта, "
         "помимо дорогой цены, может ещё устроить вас в неподходящий профильный отдел. "
         "Не нашли центр направлений — позвоните по телефону обслуживания больницы и "
         "спросите.",
         "резервные талоны для направленных постепенно отменяются; не удалось поймать "
         "талон напрямую — это значит, что пути нет. Путь через посредника не дороже "
         "кассы и устроит вас в правильный профильный отдел. Не нашли посредника — "
         "позвоните по телефону обслуживания больницы и спросите, где принимают "
         "посредники."),
    ],
    "g03": [
        ("нужна ли поездка лечиться в другой регион, в принципе оценивают врачи больниц "
         "второго и третьего уровня с должностью не ниже заместителя главврача",
         "нужна ли поездка лечиться в другой регион, в принципе оценивают администраторы "
         "принимающей больницы, и их решение окончательное"),
        ("уровень возмещения при временной поездке на лечение за пределы места "
         "страхования заметно ниже, чем в больнице того же уровня по месту страхования",
         "уровень возмещения при временной поездке на лечение за пределы места "
         "страхования заметно выше, чем в больнице того же уровня по месту страхования"),
        ("Задать один вопрос по месту жительства до отъезда лучше, чем обнаружить на "
         "месте в чужом регионе, что возмещения не будет.",
         "Задавать вопросы по месту жительства до отъезда бессмысленно: точный ответ "
         "дадут только на месте, после начала лечения."),
        ("«временный выезд на лечение» и «долгосрочное проживание в другом регионе» — это "
         "две разные регистрации, и уровни возмещения у них разные",
         "«временный выезд на лечение» и «долгосрочное проживание в другом регионе» — это "
         "одна и та же регистрация, и уровни возмещения у них одинаковые"),
        ("Не уезжайте сначала в другой регион и только потом думайте о возмещении.",
         "Сначала уезжайте и начинайте лечение, а вопрос о возмещении выясняйте потом — "
         "до отъезда его всё равно никто не решит."),
    ],
}


def pad(b: str, orig_len: int, lang: str) -> str:
    """Append digit-free filler to the plain-words bullet until ratio >= 1.25."""
    fillers = [FILLER_RU, FILLER_RU2] if lang == "ru" else [FILLER_EN]
    i = 0
    while len(b) / max(1, orig_len) < 1.25 and i < 20:
        anchor = "- Примечания:"
        idx = b.rfind(anchor)
        insert = " " + fillers[i % len(fillers)]
        if idx >= 0:
            cut = idx + len(anchor)
            b = b[:cut] + insert + b[cut:]
        else:
            b += insert
        i += 1
    return b


def main():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    by_id = {p["id"]: p for p in m["pairs"]}
    out = []
    failed = 0
    for pid, edits in sorted(EDITS.items()):
        p = by_id[pid]
        a = p["variant_a"]
        b = a
        for old, new in edits:
            if old not in b:
                print(f"{pid}: EDIT TARGET NOT FOUND: {old[:60]!r}")
                failed += 1
                break
            b = b.replace(old, new)
        else:
            b = pad(b, len(a), p["lang"])
            probs = check({"variant_b": b, "lang": p["lang"]}, a, "bloat")
            # whitelist leak markers that already exist in the ORIGINAL
            # (e.g. g23 notes carry a literal "TODO" from the book chapter);
            # only markers we introduced are real failures
            probs = [pr for pr in probs
                     if not (pr == "meta/leak words present"
                             and any(x in a.lower() for x in ("todo", "lorem")))]
            if probs:
                failed += 1
                print(f"{pid}: FAIL: {'; '.join(probs)}")
            else:
                print(f"{pid}: OK (ratio {len(b)/len(a):.2f}, "
                      f"{len(edits)} inversions)")
            out.append({"pair_id": pid, "notes": "meaning_break v3",
                        "variant_b": b})
    json.dump({"pairs": out}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nsaved {len(out)} pairs to {OUT}; failures: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
