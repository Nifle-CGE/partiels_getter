# Partiel Getter

Ceci est un programme permettant au respo bonbon de la prepa t² a Toulouse de recevoir les prochains partiels sur Telegram.

## Explications

Pour adapter ce programme a votre établissement, suivez les indications ci-dessous.

### data.json

Modifiez les urls de calendrier ical pour qu'ils soient les calendriers de votre établissement.

Si il y a différentes matières que l'on peut choisir et donc que certaines personnes n'ont pas les mêmes partiels que d'autres, vous devez mettre un url par option pour que tout les partiels soient pris en compte.

Si les partiels ne sont pas appellés exactement "Contrôle" dans votre emploi du temps, vous pouvez modifier les "text_to_detect".

### secrets.json

Vous devez créer ce fichier vous mêmes et le replir comme suit en remplaçant les [] par les données correspondates.

    {
        "telegram_send_url": "https://api.telegram.org/[votre id de bot]:[votre clé d'api]/sendMessage?chat_id=[l'id de conversation auquel vous voulez envoyer le message]&text="
    }

### partiels_getter.service

Si vous voulez faire tourner ce programme sur une distribution Linux supportant systemd :

1. remplacez "/path/to/main.py" dans le fichier par le chemin du ficher main.py
2. déplacez ce fichier dans /etc/systemd/user/ (ne pas modifier user)
3. lancez un terminal puis executez les commandes suivantes
    1. systemctl --global daemon-reload
    2. systemctl --global enable partiels_getter
    3. systemctl --global start partiels_getter