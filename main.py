from ics import Calendar
import arrow
import requests
import json
from urllib.parse import quote
import time
import logging
from logging.handlers import RotatingFileHandler
import copy
import sys

# Logging
# Mise en place du système de logs avec impression dans la console et enregistrement dans un fichier logs.log
log = logging.Logger("logger")
fh = RotatingFileHandler("logs.log", maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s : %(message)s")
fh.setFormatter(formatter)
ch = logging.StreamHandler(sys.stdout)
log.addHandler(fh)
log.addHandler(ch)

log.debug("Importing data")
with open("data.json", encoding="utf-8") as f:
    data = json.load(f)

log.debug("Data imported, importing secrets")

with open("secrets.json", encoding="utf-8") as f:
    secrets = json.load(f)

log.debug("Secrets imported")


def clean_str(string: str):
    return " ".join(x for x in string.split(" ") if x).strip("\n")


def get_partiels(for_week=False):
    all_events = set()
    for matiere, url in data["cal_urls"].items():
        log.debug(f"Downloading calendar for {matiere}...")
        all_events.update(Calendar(requests.get(url).text).events)

    log.info("Downloaded partiels")

    partiels = []
    for event in all_events:
        potential_dict = {
            "name": clean_str(event.name),
            "begin": event.begin.to("Europe/Paris"),
            "end": event.end.to("Europe/Paris"),
            "description": "\n".join(clean_str(event.description).splitlines()[:-1]),
            "location": clean_str(event.location)
        }

        # si evenement est un partiel et que il n'est pas déjà ajouté et qu'il n'est pas déjà passé
        if (data["text_to_detect"] in event.name) and (potential_dict not in partiels) and (arrow.now("Europe/Paris") < potential_dict["end"]):
            partiels.append(potential_dict)

    log.info("Cleaned partiels")

    partiels.sort(key=lambda x: x["end"])

    if for_week:
        time_limit = arrow.now("Europe/Paris").shift(weekday=4).replace(hour=23, minute=59)
    else:
        time_limit = partiels[0]["end"].replace(hour=23, minute=59)

    to_send = []
    for partiel in partiels:
        # if partiel on the same day or in the same week as the next partiel
        if partiel["end"] < time_limit:
            to_send.append(partiel)
        else:
            break

    log.info("Sorted and removed useless partiels, partiels gotten")

    return to_send


def send_message(message):
    if message:
        requests.get(secrets["telegram_send_url"] + quote(message))


def format_partiels(partiels, update=False):
    final_str = "Un partiel a été mis a jour :" if update else "Voilà les prochains partiels :"
    for partiel in partiels:
        final_str += "\n" + "🔤 Matière : " + partiel["name"] + "\n"
        final_str += "▶️ Début : " + partiel["begin"].format("DD/MM/YYYY HH:mm") + "\n"
        final_str += "⏹️ Fin : " + partiel["end"].format("DD/MM/YYYY HH:mm") + "\n"
        final_str += "🗓️ Promo : " + ("1A" if "1A" in partiel["description"] else "2A") + "\n"
        final_str += "👤 Surveillants : " + ", ".join(line for line in partiel["description"].splitlines() if all(x not in line for x in ("MINEURE", "MAJEURE", "1A", "2A", "3A"))) + "\n"
        final_str += "📍 Salle : " + partiel["location"] + "\n"

    final_str = final_str[:-1]
    log.info(f"Formatted{' the update on' if update else ''} {len(partiels)} partiels")
    return final_str


def format_partiels_lite(partiels):
    final_str = "Voilà un résumé des partiels de la semaine :"
    for partiel in partiels:
        final_str += f"\n- 🔤 {partiel['name']}, ⏹️ {partiel['end'].format('DD/MM/YYYY HH:mm')}, 🗓️ {'1A' if '1A' in partiel['description'] else '2A'}, 📍 {partiel['location']}"

    log.info(f"Formatted summary of {len(partiels)} partiels")
    return final_str


def main():
    send_message("Début du 🔄️ cycle 🔄️")

    current_partiels = get_partiels()
    send_message(format_partiels(current_partiels))
    log.info("Sent first partiels")

    wait_for_sunday = False
    while True:
        if wait_for_sunday:
            wait_for_sunday = False

            log.info("Waiting until sunday morning")
            arrow_now = arrow.now("Europe/Paris")
            next_sunday = arrow_now.shift(weekday=6).replace(hour=10, minute=0)
            time.sleep((next_sunday - arrow_now).total_seconds())

            log.info("Getting week's partiels")
            week_partiels = get_partiels(for_week=True)
            if week_partiels:
                msg = format_partiels_lite(week_partiels)
            else:
                msg = "Pas de partiels cette semaine ☺️"

            send_message(msg)
            log.info("Weekly summary sent")

        arrow_now = arrow.now("Europe/Paris")
        day_before = current_partiels[0]["begin"].shift(days=-1).replace(hour=20, minute=0)
        morning_before = current_partiels[0]["begin"].replace(hour=7, minute=20)
        hour_before = current_partiels[0]["begin"].shift(hours=-1)
        minutes_before = current_partiels[0]["begin"].shift(minutes=-5)
        minutes_before_end = current_partiels[0]["end"].shift(minutes=-5)
        if arrow_now < day_before:
            log.info("Waiting until the day before...")
            time.sleep((day_before - arrow_now).total_seconds())
            msg = "Rappel pour le début de ⤴️ dans un jour"
        elif arrow_now < morning_before:
            log.info("Waiting until the morning before...")
            time.sleep((morning_before - arrow_now).total_seconds())
            msg = "Rappel pour le début de ⤴️ aujourd'hui"
        elif arrow_now < hour_before:
            log.info("Waiting until an hour before...")
            time.sleep((hour_before - arrow_now).total_seconds())
            msg = "Rappel pour le début de ⤴️ dans une heure"
        elif arrow_now < minutes_before:
            log.info("Waiting until 5 minutes before...")
            time.sleep((minutes_before - arrow_now).total_seconds())
            msg = "Rappel pour le début de ⤴️ dans 5 minutes"
        elif arrow_now < minutes_before_end:
            log.info("Waiting until 5 minutes before the end...")
            time.sleep((minutes_before_end - arrow_now).total_seconds())
            msg = "Rappel pour la fin de ⤴️ dans 5 minutes avant la fin"
        else:
            current_partiel = current_partiels.pop(0)
            log.info("Waiting until the end...")
            time.sleep(300)  # 5 minutes
            msg = "Distribution de 🍬 bonbons 🍬 activée pour " + current_partiel["name"]

            if not get_partiels(for_week=True):  # Si ce partiel est le dernier de la semaine
                wait_for_sunday = True

        potentially_new_partiels = get_partiels()
        if current_partiels:  # Si il reste des partiels dans le futur
            if current_partiels != potentially_new_partiels:  # Si y'a eut un changement dans les partiels
                log.info("A partiel has changed, sending update")
                current_partiels = copy.deepcopy(potentially_new_partiels)
                msg = format_partiels(current_partiels, update=True) + "\n" + msg
        else:  # Si plus aucun partiel
            log.info("No more partiels today, getting the next ones")
            current_partiels = get_partiels()
            msg += "\n" + format_partiels(current_partiels)

        send_message(msg)
        log.info("Sent whatever needed to be sent")


if __name__ == "__main__":
    main()
