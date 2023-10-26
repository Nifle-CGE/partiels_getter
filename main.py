from ics import Calendar
import arrow
import requests
import json
from urllib.parse import quote
import time
import copy

with open("data.json", encoding="utf-8") as f:
    data = json.load(f)

with open("secrets.json", encoding="utf-8") as f:
    secrets = json.load(f)

def get_partiels():
    all_events = set()
    print("Downloading 1A calendar...")
    all_events.update(Calendar(requests.get(data["url_1A"]).text).events)
    for matiere, url in data["urls_2A"].items():
        print(f"Downloading 2A calendar for {matiere}...")
        all_events.update(Calendar(requests.get(url).text).events)
    
    partiels = []
    for event in all_events:
        potential_dict = {"name": event.name.strip(" \n").replace("  ", " "), "begin": event.begin.to("Europe/Paris"), "end": event.end.to("Europe/Paris"), "description": "\n".join(event.description.strip(" \n").split("\n")[:-1]), "location": event.location.strip(" \n").replace("  ", " ")}
        # si evenement est un partiel et que il n'est pas déjà ajouté et qu'il n'est pas déjà passé
        if (data["text_to_detect"] in event.name) and (potential_dict not in partiels) and (arrow.now("Europe/Paris") < potential_dict["end"]):
            partiels.append(potential_dict)

    partiels.sort(key=lambda x:x["end"])

    to_send = []
    if partiels[0]["end"] < arrow.now("Europe/Paris").replace(hour=23): # si il reste au moins un partiel aujourd'hui
        for partiel in partiels:
            if partiel["end"] < arrow.now("Europe/Paris").replace(hour=23):
                to_send.append(partiel)
            else:
                break
    else:
        next_partiel = partiels[0]
        for partiel in partiels:
            if partiel["end"] < next_partiel["end"].replace(hour=23): # if partiel on the same day as the next partiel
                to_send.append(partiel)
            else:
                break

    return to_send

def send_partiels(partiels, update=False):
    final_str = "Un partiel a été mis a jour :\n" if update else "Voilà les partiels :\n"
    for partiel in partiels:
        final_str += "\nName : " + partiel["name"] + "\n"
        final_str += "Begin : " + partiel["begin"].format("DD/MM/YYYY HH:mm") + "\n"
        final_str += "End : " + partiel["end"].format("DD/MM/YYYY HH:mm") + "\n"
        final_str += "Description :\n" + partiel["description"] + "\n"
        final_str += "Location : " + partiel["location"] + "\n"

    final_str = final_str[:-1]
    print(f"Sent {len(partiels)} partiels")
    requests.get(secrets["telegram_send_url"] + quote(final_str))

current_partiels = []
checks = []
while True:
    if not current_partiels:
        current_partiels = get_partiels()
        send_partiels(current_partiels)
    
    arrow_now = arrow.now("Europe/Paris")
    day_before = current_partiels[0]["begin"].shift(days=-1).replace(hour=19, minute=0)
    hour_before = current_partiels[0]["begin"].shift(hours=-1)
    minutes_before = current_partiels[0]["begin"].shift(minutes=-5)
    minutes_before_end = current_partiels[0]["end"].shift(minutes=-5)
    if arrow_now < day_before:
        print("Waiting until the day before...")
        time.sleep((day_before - arrow_now).total_seconds())
    elif arrow_now < hour_before:
        print("Waiting until an hour before...")
        time.sleep((hour_before - arrow_now).total_seconds())
    elif arrow_now < minutes_before:
        print("Waiting until 5 minutes before...")
        time.sleep((minutes_before - arrow_now).total_seconds())
    elif arrow_now < minutes_before_end:
        print("Waiting until 5 minutes before the end...")
        time.sleep((minutes_before_end - arrow_now).total_seconds())
    else:
        del current_partiels[0]

    potentially_new_partiels = get_partiels()
    if current_partiels != potentially_new_partiels:
        current_partiels = potentially_new_partiels
        send_partiels(current_partiels, update=True)