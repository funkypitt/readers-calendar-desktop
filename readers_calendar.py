#!/usr/bin/env python3
"""Reader's Calendar — a black-and-white, text-only desktop calendar on CalDAV
(Infomaniak, Nextcloud, Radicale…). The landscape design of the Android app: month grid and
navigation on the left, agenda / week grid / event page on the right. PyQt5 + requests +
python-dateutil, one file. MIT licence."""

import calendar
import json
import re
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

# the module next to this file first; the installed copy only as a fallback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/usr/lib/readers-calendar")
import caldav_events as ce  # noqa: E402
import google_calendar as gc  # noqa: E402

APP = "readers-calendar"
VERSION = "1.11.0"


def _config_dir():
    """The settings folder, one place per desktop. Linux keeps the XDG folder it has always
    used; Windows and macOS take the per-user folder of the system, the one place where a
    password stays out of another account's reach."""
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Readers Calendar")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/" + APP)
    return os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), APP)


CONFIG_DIR = _config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SYNC_MINUTES = 5
LOCAL = ce.LOCAL


# ------------------------------------------------------------------------------------------
# Six languages, the English text as the key (the launcher's languages: en, fr, de, es, pt, ru)
# ------------------------------------------------------------------------------------------

_TR = {
 "fr": {"Google account": "compte Google", "client ID": "ID client", "client secret": "secret client", "connect the Google account": "connecter le compte Google", "forget the Google account": "oublier le compte Google", "waiting for the browser…": "en attente du navigateur…", "Google account connected": "compte Google connecté", "Google: %1": "Google : %1", "workdays": "jours ouvrés", "opens on": "s'ouvre sur", "today · ": "aujourd'hui · ", "tomorrow · ": "demain · ", "all day": "toute la journée", "cancel": "annuler", "ok": "ok", "date": "date", "does not repeat": "ne se répète pas", "every day": "chaque jour", "every week": "chaque semaine", "every month": "chaque mois", "every year": "chaque année",
        "no reminder": "pas de rappel", "at the time of the event": "à l'heure de l'événement", "%1 minutes before": "%1 minutes avant", "%1 hours before": "%1 heures avant", "%1 days before": "%1 jours avant",
        "agenda": "agenda", "day": "jour", "week": "semaine", "+ new event": "+ nouvel événement", "server": "serveur", "username": "identifiant", "app password": "mot de passe d'application", "feeds": "flux", "connect": "se connecter",
        "not connected — Ctrl+, to set up": "non connecté — Ctrl+, pour configurer", "connecting…": "connexion…", "  (read only)": "  (lecture seule)", "syncing…": "synchronisation…", "synced %1": "synchronisé %1", "nothing planned": "rien de prévu", "show more days": "afficher plus de jours", "today": "aujourd'hui",
        "repeats": "se répète", "repeats (custom rule)": "se répète (règle personnalisée)", " · read-only": " · lecture seule", "← back": "← retour", "edit": "modifier", "delete": "supprimer", " the whole series": " toute la série", "move the whole series": "déplacer toute la série", "deleting…": "suppression…", "this event comes from a read-only feed": "cet événement vient d'un flux en lecture seule", "no writable calendar": "aucun agenda modifiable", "%1 copied": "%1 copié", "%1 feeds": "%1 flux", "accounts": "comptes", "at set times": "à heures fixes", "black on white": "noir sur blanc", "white on black": "blanc sur noir", "colours": "couleurs", "default calendar": "agenda par défaut", "default reminder": "rappel par défaut", "ends another day": "se termine un autre jour", "first day of the week": "premier jour de la semaine", "look": "apparence", "monday": "lundi", "sunday": "dimanche", "month": "mois", "no event found": "aucun événement trouvé", "past": "passés", "upcoming": "à venir", "read only": "lecture seule", "search": "chercher", "search events: title, place, notes": "chercher un événement : titre, lieu, notes", "searching further…": "recherche plus loin…", "settings": "réglages", "sync now": "synchroniser", "text size": "taille du texte", "time": "heure", "← cancel": "← annuler", "Google: the event changed elsewhere — shown again as it is now": "Google : l'événement a changé ailleurs — le voici tel qu'il est maintenant", "move only this event": "déplacer seulement cet événement", "edit only this event": "modifier seulement cet événement", "edit the whole series": "modifier toute la série", "delete only this event": "supprimer seulement cet événement", "part of a series": "fait partie d'une série", "this calendar is read-only": "cet agenda est en lecture seule", "Google: connect the account again (Ctrl+,) to edit its events": "Google : reconnectez le compte (Ctrl+,) pour modifier ses événements", "connected read-only — forget, then connect again to edit": "connecté en lecture seule — oubliez, puis reconnectez pour modifier", "Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself.": "Google Agenda, lecture et écriture, avec votre propre client OAuth : console.cloud.google.com › nouveau projet › API et services › activer\nl'API Google Calendar › écran de consentement OAuth (externe, vous-même comme testeur, puis Publier l'application : en mode Test, Google\ndemande de reconnecter tous les 7 jours) › Identifiants › ID client OAuth, type Application de bureau. Copiez l'ID et le secret ici, puis\nconnectez : le navigateur s'ouvre sur Google (« Google n'a pas validé cette application » : Paramètres avancés › continuer — c'est votre\npropre client) et revient tout seul.",
        "title": "titre", "all day: ": "toute la journée : ", "on": "oui", "off": "non", "starts": "début", "start time": "heure de début", "ends": "fin", "end time": "heure de fin", "calendar": "agenda", "reminder": "rappel", "repeat": "répétition", "location": "lieu", "description": "description",
        "save": "enregistrer", "the end is before the start": "la fin est avant le début", "saving…": "enregistrement…", "start time (hh:mm)": "heure de début (hh:mm)", "end time (hh:mm)": "heure de fin (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Agendas CalDAV. Infomaniak : https://sync.infomaniak.com, identifiant du type AB12345,\nun mot de passe d'application si la double authentification est active. Nextcloud, Radicale… fonctionnent aussi.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Flux en lecture seule, un par ligne sous la forme  nom | adresse  (.ics ou webcal). Google Agenda : paramètres de\nl'agenda › Intégrer l'agenda › Adresse secrète au format iCal. Ils s'affichent à côté des agendas CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · développé avec Claude Code"},
 "de": {"Google account": "Google-Konto", "client ID": "Client-ID", "client secret": "Client-Geheimnis", "connect the Google account": "Google-Konto verbinden", "forget the Google account": "Google-Konto vergessen", "waiting for the browser…": "warte auf den Browser…", "Google account connected": "Google-Konto verbunden", "Google: %1": "Google: %1", "workdays": "Werktage", "opens on": "öffnet mit", "today · ": "heute · ", "tomorrow · ": "morgen · ", "all day": "ganztägig", "cancel": "abbrechen", "ok": "ok", "date": "Datum", "does not repeat": "einmalig", "every day": "täglich", "every week": "wöchentlich", "every month": "monatlich", "every year": "jährlich",
        "no reminder": "keine Erinnerung", "at the time of the event": "zum Zeitpunkt des Termins", "%1 minutes before": "%1 Minuten vorher", "%1 hours before": "%1 Stunden vorher", "%1 days before": "%1 Tage vorher",
        "agenda": "Agenda", "day": "Tag", "week": "Woche", "+ new event": "+ neuer Termin", "server": "Server", "username": "Benutzername", "app password": "App-Passwort", "feeds": "Feeds", "connect": "verbinden",
        "not connected — Ctrl+, to set up": "nicht verbunden — Strg+, zum Einrichten", "connecting…": "verbinde…", "  (read only)": "  (nur lesen)", "syncing…": "synchronisiere…", "synced %1": "synchronisiert %1", "nothing planned": "nichts geplant", "show more days": "mehr Tage zeigen", "today": "heute",
        "repeats": "wiederholt sich", "repeats (custom rule)": "wiederholt sich (eigene Regel)", " · read-only": " · nur lesen", "← back": "← zurück", "edit": "bearbeiten", "delete": "löschen", " the whole series": " die ganze Serie", "move the whole series": "die ganze Serie verschieben", "deleting…": "lösche…", "this event comes from a read-only feed": "dieser Termin stammt aus einem Nur-Lese-Feed", "no writable calendar": "kein beschreibbarer Kalender", "%1 copied": "%1 kopiert", "%1 feeds": "%1 Feeds", "accounts": "Konten", "at set times": "mit Uhrzeit", "black on white": "Schwarz auf Weiß", "white on black": "Weiß auf Schwarz", "colours": "Farben", "default calendar": "Standardkalender", "default reminder": "Standarderinnerung", "ends another day": "endet an einem anderen Tag", "first day of the week": "erster Tag der Woche", "look": "Aussehen", "monday": "Montag", "sunday": "Sonntag", "month": "Monat", "no event found": "kein Termin gefunden", "past": "vergangen", "upcoming": "bevorstehend", "read only": "nur lesen", "search": "suchen", "search events: title, place, notes": "Termine suchen: Titel, Ort, Notizen", "searching further…": "suche weiter…", "settings": "Einstellungen", "sync now": "jetzt synchronisieren", "text size": "Textgröße", "time": "Uhrzeit", "← cancel": "← abbrechen", "Google: the event changed elsewhere — shown again as it is now": "Google: der Termin wurde anderswo geändert — hier sein aktueller Stand", "move only this event": "nur diesen Termin verschieben", "edit only this event": "nur diesen Termin bearbeiten", "edit the whole series": "die ganze Serie bearbeiten", "delete only this event": "nur diesen Termin löschen", "part of a series": "Teil einer Serie", "this calendar is read-only": "dieser Kalender ist schreibgeschützt", "Google: connect the account again (Ctrl+,) to edit its events": "Google: Konto erneut verbinden (Strg+,), um Termine zu bearbeiten", "connected read-only — forget, then connect again to edit": "nur lesend verbunden — vergessen, dann erneut verbinden, um zu bearbeiten", "Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself.": "Google Kalender, lesen und schreiben, mit eigenem OAuth-Client: console.cloud.google.com › neues Projekt › APIs & Dienste › Google Calendar API\naktivieren › OAuth-Zustimmungsbildschirm (extern, Sie selbst als Tester, dann App veröffentlichen: im Testmodus verlangt Google alle 7 Tage\neine neue Verbindung) › Anmeldedaten › OAuth-Client-ID, Typ Desktop-App. ID und Geheimnis hier eintragen, dann verbinden: der Browser öffnet\nGoogle („Google hat diese App nicht überprüft“: Erweitert › weiter — es ist Ihr eigener Client) und kommt von selbst zurück.",
        "title": "Titel", "all day: ": "ganztägig: ", "on": "an", "off": "aus", "starts": "beginnt", "start time": "Beginn", "ends": "endet", "end time": "Ende", "calendar": "Kalender", "reminder": "Erinnerung", "repeat": "Wiederholung", "location": "Ort", "description": "Beschreibung",
        "save": "speichern", "the end is before the start": "das Ende liegt vor dem Beginn", "saving…": "speichere…", "start time (hh:mm)": "Beginn (hh:mm)", "end time (hh:mm)": "Ende (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "CalDAV-Kalender. Infomaniak: https://sync.infomaniak.com, Benutzername wie AB12345,\nein App-Passwort bei Zwei-Faktor-Anmeldung. Nextcloud, Radicale… gehen ebenso.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Nur-Lese-Feeds, je Zeile  Name | Adresse  (.ics oder webcal). Google Kalender: Einstellungen des\nKalenders › Kalender integrieren › Privatadresse im iCal-Format. Sie erscheinen neben den CalDAV-Kalendern.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · entwickelt mit Claude Code"},
 "es": {"Google account": "cuenta de Google", "client ID": "ID de cliente", "client secret": "secreto de cliente", "connect the Google account": "conectar la cuenta de Google", "forget the Google account": "olvidar la cuenta de Google", "waiting for the browser…": "esperando al navegador…", "Google account connected": "cuenta de Google conectada", "Google: %1": "Google: %1", "workdays": "días laborables", "opens on": "se abre en", "today · ": "hoy · ", "tomorrow · ": "mañana · ", "all day": "todo el día", "cancel": "cancelar", "ok": "ok", "date": "fecha", "does not repeat": "no se repite", "every day": "cada día", "every week": "cada semana", "every month": "cada mes", "every year": "cada año",
        "no reminder": "sin recordatorio", "at the time of the event": "a la hora del evento", "%1 minutes before": "%1 minutos antes", "%1 hours before": "%1 horas antes", "%1 days before": "%1 días antes",
        "agenda": "agenda", "day": "día", "week": "semana", "+ new event": "+ nuevo evento", "server": "servidor", "username": "usuario", "app password": "contraseña de aplicación", "feeds": "feeds", "connect": "conectar",
        "not connected — Ctrl+, to set up": "sin conexión — Ctrl+, para configurar", "connecting…": "conectando…", "  (read only)": "  (solo lectura)", "syncing…": "sincronizando…", "synced %1": "sincronizado %1", "nothing planned": "nada previsto", "show more days": "mostrar más días", "today": "hoy",
        "repeats": "se repite", "repeats (custom rule)": "se repite (regla personalizada)", " · read-only": " · solo lectura", "← back": "← volver", "edit": "editar", "delete": "eliminar", " the whole series": " toda la serie", "move the whole series": "mover toda la serie", "deleting…": "eliminando…", "this event comes from a read-only feed": "este evento viene de un feed de solo lectura", "no writable calendar": "ningún calendario editable", "%1 copied": "%1 copiado", "%1 feeds": "%1 feeds", "accounts": "cuentas", "at set times": "con hora", "black on white": "negro sobre blanco", "white on black": "blanco sobre negro", "colours": "colores", "default calendar": "calendario predeterminado", "default reminder": "recordatorio predeterminado", "ends another day": "termina otro día", "first day of the week": "primer día de la semana", "look": "aspecto", "monday": "lunes", "sunday": "domingo", "month": "mes", "no event found": "ningún evento encontrado", "past": "pasados", "upcoming": "próximos", "read only": "solo lectura", "search": "buscar", "search events: title, place, notes": "buscar eventos: título, lugar, notas", "searching further…": "buscando más lejos…", "settings": "ajustes", "sync now": "sincronizar ahora", "text size": "tamaño del texto", "time": "hora", "← cancel": "← cancelar", "Google: the event changed elsewhere — shown again as it is now": "Google: el evento cambió en otro lugar — se muestra tal como está ahora", "move only this event": "mover solo este evento", "edit only this event": "editar solo este evento", "edit the whole series": "editar toda la serie", "delete only this event": "eliminar solo este evento", "part of a series": "parte de una serie", "this calendar is read-only": "este calendario es de solo lectura", "Google: connect the account again (Ctrl+,) to edit its events": "Google: vuelva a conectar la cuenta (Ctrl+,) para editar sus eventos", "connected read-only — forget, then connect again to edit": "conectada en solo lectura — olvídela y vuelva a conectarla para editar", "Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself.": "Google Calendar, lectura y escritura, con su propio cliente OAuth: console.cloud.google.com › proyecto nuevo › APIs y servicios › activar la\nAPI de Google Calendar › pantalla de consentimiento OAuth (externa, usted como probador, luego Publicar la app: en pruebas, Google pide\nreconectar cada 7 días) › Credenciales › ID de cliente OAuth, tipo Aplicación de escritorio. Copie el ID y el secreto aquí y conecte: el\nnavegador abre Google («Google no ha verificado esta app»: Avanzado › continuar — es su propio cliente) y vuelve solo.",
        "title": "título", "all day: ": "todo el día: ", "on": "sí", "off": "no", "starts": "empieza", "start time": "hora de inicio", "ends": "termina", "end time": "hora de fin", "calendar": "calendario", "reminder": "recordatorio", "repeat": "repetición", "location": "lugar", "description": "descripción",
        "save": "guardar", "the end is before the start": "el fin es anterior al inicio", "saving…": "guardando…", "start time (hh:mm)": "hora de inicio (hh:mm)", "end time (hh:mm)": "hora de fin (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Calendarios CalDAV. Infomaniak: https://sync.infomaniak.com, usuario tipo AB12345,\nuna contraseña de aplicación si tienes la verificación en dos pasos. Nextcloud, Radicale… también funcionan.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Feeds de solo lectura, uno por línea como  nombre | dirección  (.ics o webcal). Google Calendar: ajustes del\ncalendario › Integrar el calendario › Dirección secreta en formato iCal. Se muestran junto a los calendarios CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · desarrollado con Claude Code"},
 "pt": {"Google account": "conta Google", "client ID": "ID de cliente", "client secret": "segredo de cliente", "connect the Google account": "ligar a conta Google", "forget the Google account": "esquecer a conta Google", "waiting for the browser…": "à espera do navegador…", "Google account connected": "conta Google ligada", "Google: %1": "Google: %1", "workdays": "dias úteis", "opens on": "abre em", "today · ": "hoje · ", "tomorrow · ": "amanhã · ", "all day": "todo o dia", "cancel": "cancelar", "ok": "ok", "date": "data", "does not repeat": "não se repete", "every day": "todos os dias", "every week": "todas as semanas", "every month": "todos os meses", "every year": "todos os anos",
        "no reminder": "sem lembrete", "at the time of the event": "à hora do evento", "%1 minutes before": "%1 minutos antes", "%1 hours before": "%1 horas antes", "%1 days before": "%1 dias antes",
        "agenda": "agenda", "day": "dia", "week": "semana", "+ new event": "+ novo evento", "server": "servidor", "username": "utilizador", "app password": "palavra-passe de aplicação", "feeds": "feeds", "connect": "ligar",
        "not connected — Ctrl+, to set up": "sem ligação — Ctrl+, para configurar", "connecting…": "a ligar…", "  (read only)": "  (só leitura)", "syncing…": "a sincronizar…", "synced %1": "sincronizado %1", "nothing planned": "nada previsto", "show more days": "mostrar mais dias", "today": "hoje",
        "repeats": "repete-se", "repeats (custom rule)": "repete-se (regra personalizada)", " · read-only": " · só leitura", "← back": "← voltar", "edit": "editar", "delete": "apagar", " the whole series": " toda a série", "move the whole series": "mover toda a série", "deleting…": "a apagar…", "this event comes from a read-only feed": "este evento vem de um feed só de leitura", "no writable calendar": "nenhum calendário editável", "%1 copied": "%1 copiado", "%1 feeds": "%1 feeds", "accounts": "contas", "at set times": "com hora", "black on white": "preto sobre branco", "white on black": "branco sobre preto", "colours": "cores", "default calendar": "calendário predefinido", "default reminder": "lembrete predefinido", "ends another day": "termina noutro dia", "first day of the week": "primeiro dia da semana", "look": "aspeto", "monday": "segunda-feira", "sunday": "domingo", "month": "mês", "no event found": "nenhum evento encontrado", "past": "passados", "upcoming": "próximos", "read only": "só leitura", "search": "procurar", "search events: title, place, notes": "procurar eventos: título, local, notas", "searching further…": "a procurar mais longe…", "settings": "definições", "sync now": "sincronizar agora", "text size": "tamanho do texto", "time": "hora", "← cancel": "← cancelar", "Google: the event changed elsewhere — shown again as it is now": "Google: o evento mudou noutro lado — mostrado tal como está agora", "move only this event": "mover só este evento", "edit only this event": "editar só este evento", "edit the whole series": "editar toda a série", "delete only this event": "apagar só este evento", "part of a series": "parte de uma série", "this calendar is read-only": "este calendário é só de leitura", "Google: connect the account again (Ctrl+,) to edit its events": "Google: ligue a conta de novo (Ctrl+,) para editar os eventos", "connected read-only — forget, then connect again to edit": "ligada só de leitura — esqueça e ligue de novo para editar", "Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself.": "Google Calendar, leitura e escrita, com o seu próprio cliente OAuth: console.cloud.google.com › novo projeto › APIs e serviços › ativar a\nAPI Google Calendar › ecrã de consentimento OAuth (externo, você como testador, depois Publicar a app: em teste, o Google pede nova\nligação a cada 7 dias) › Credenciais › ID de cliente OAuth, tipo Aplicação de computador. Copie o ID e o segredo aqui e ligue: o navegador\nabre o Google («A Google não validou esta app»: Avançadas › continuar — é o seu próprio cliente) e volta sozinho.",
        "title": "título", "all day: ": "todo o dia: ", "on": "sim", "off": "não", "starts": "começa", "start time": "hora de início", "ends": "termina", "end time": "hora de fim", "calendar": "calendário", "reminder": "lembrete", "repeat": "repetição", "location": "local", "description": "descrição",
        "save": "guardar", "the end is before the start": "o fim é anterior ao início", "saving…": "a guardar…", "start time (hh:mm)": "hora de início (hh:mm)", "end time (hh:mm)": "hora de fim (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Calendários CalDAV. Infomaniak: https://sync.infomaniak.com, utilizador tipo AB12345,\numa palavra-passe de aplicação se tiver a verificação em dois passos. Nextcloud, Radicale… também funcionam.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Feeds só de leitura, um por linha como  nome | endereço  (.ics ou webcal). Google Calendar: definições do\ncalendário › Integrar o calendário › Endereço secreto em formato iCal. Aparecem ao lado dos calendários CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · desenvolvido com Claude Code"},
 "ru": {"Google account": "аккаунт Google", "client ID": "ID клиента", "client secret": "секрет клиента", "connect the Google account": "подключить аккаунт Google", "forget the Google account": "забыть аккаунт Google", "waiting for the browser…": "ожидание браузера…", "Google account connected": "аккаунт Google подключён", "Google: %1": "Google: %1", "workdays": "будни", "opens on": "открывается на", "today · ": "сегодня · ", "tomorrow · ": "завтра · ", "all day": "весь день", "cancel": "отмена", "ok": "ок", "date": "дата", "does not repeat": "не повторяется", "every day": "каждый день", "every week": "каждую неделю", "every month": "каждый месяц", "every year": "каждый год",
        "no reminder": "без напоминания", "at the time of the event": "в момент события", "%1 minutes before": "за %1 мин", "%1 hours before": "за %1 ч", "%1 days before": "за %1 дн",
        "agenda": "повестка", "day": "день", "week": "неделя", "+ new event": "+ новое событие", "server": "сервер", "username": "имя пользователя", "app password": "пароль приложения", "feeds": "ленты", "connect": "подключиться",
        "not connected — Ctrl+, to set up": "нет подключения — Ctrl+, для настройки", "connecting…": "подключение…", "  (read only)": "  (только чтение)", "syncing…": "синхронизация…", "synced %1": "синхронизировано %1", "nothing planned": "ничего не запланировано", "show more days": "показать больше дней", "today": "сегодня",
        "repeats": "повторяется", "repeats (custom rule)": "повторяется (своё правило)", " · read-only": " · только чтение", "← back": "← назад", "edit": "изменить", "delete": "удалить", " the whole series": " всю серию", "move the whole series": "перенести всю серию", "deleting…": "удаление…", "this event comes from a read-only feed": "это событие из ленты только для чтения", "no writable calendar": "нет календаря для записи", "%1 copied": "%1 скопирован", "%1 feeds": "лент: %1", "accounts": "аккаунты", "at set times": "по времени", "black on white": "чёрным по белому", "white on black": "белым по чёрному", "colours": "цвета", "default calendar": "календарь по умолчанию", "default reminder": "напоминание по умолчанию", "ends another day": "заканчивается в другой день", "first day of the week": "первый день недели", "look": "вид", "monday": "понедельник", "sunday": "воскресенье", "month": "месяц", "no event found": "событий не найдено", "past": "прошедшие", "upcoming": "предстоящие", "read only": "только чтение", "search": "поиск", "search events: title, place, notes": "поиск событий: название, место, заметки", "searching further…": "ищу дальше…", "settings": "настройки", "sync now": "синхронизировать", "text size": "размер текста", "time": "время", "← cancel": "← отмена", "Google: the event changed elsewhere — shown again as it is now": "Google: событие изменено в другом месте — показано в текущем виде", "move only this event": "перенести только это событие", "edit only this event": "изменить только это событие", "edit the whole series": "изменить всю серию", "delete only this event": "удалить только это событие", "part of a series": "часть серии", "this calendar is read-only": "этот календарь только для чтения", "Google: connect the account again (Ctrl+,) to edit its events": "Google: подключите аккаунт заново (Ctrl+,), чтобы изменять события", "connected read-only — forget, then connect again to edit": "подключён только для чтения — забудьте и подключите заново, чтобы изменять", "Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself.": "Google Календарь, чтение и запись, со своим OAuth-клиентом: console.cloud.google.com › новый проект › API и сервисы › включить\nGoogle Calendar API › экран согласия OAuth (внешний, вы как тестировщик, затем «Опубликовать приложение»: в режиме тестирования Google\nпросит подключаться заново каждые 7 дней) › Учётные данные › идентификатор клиента OAuth, тип «Компьютерное приложение». Вставьте ID и\nсекрет сюда и подключите: браузер откроет Google («Google не проверил это приложение»: Дополнительно › продолжить — это ваш собственный\nклиент) и вернётся сам.",
        "title": "название", "all day: ": "весь день: ", "on": "вкл", "off": "выкл", "starts": "начало", "start time": "время начала", "ends": "конец", "end time": "время окончания", "calendar": "календарь", "reminder": "напоминание", "repeat": "повтор", "location": "место", "description": "описание",
        "save": "сохранить", "the end is before the start": "конец раньше начала", "saving…": "сохранение…", "start time (hh:mm)": "время начала (чч:мм)", "end time (hh:mm)": "время окончания (чч:мм)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Календари CalDAV. Infomaniak: https://sync.infomaniak.com, имя вида AB12345,\nпароль приложения при двухфакторной аутентификации. Nextcloud, Radicale… тоже подходят.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Ленты только для чтения, по одной в строке:  имя | адрес  (.ics или webcal). Google Календарь: настройки\nкалендаря › Интеграция календаря › Закрытый адрес в формате iCal. Показываются рядом с календарями CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · разработано с Claude Code"},
}


def _lang():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var)
        if v:
            return v[:2].lower()
    try:                    # Windows, and macOS opened from the Finder: no LANG at all
        return QtCore.QLocale.system().name()[:2].lower()
    except Exception:
        return "en"


_LANG = _lang()


def _(key, *args):
    s = _TR.get(_LANG, {}).get(key, key)
    for i, a in enumerate(args):
        s = s.replace("%" + str(i + 1), str(a))
    return s


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG_FILE)

CREDENTIAL_KEYS = ('url', 'username', 'password', 'subscriptions', 'google')
CREDENTIAL_FALLBACK = {}   # when this app's section is absent: another app's section, these keys only


# ------------------------------------------------------------------------------------------
# Credentials file: the accounts of every Reader's desktop app in one JSON file, to set up a new
# computer in one step. One section per app; exporting adds or replaces this app's section and
# keeps the others, so Calendar, Tasks and Notes can share the same file. It holds passwords
# and tokens in clear: it is written readable by its owner only.
# ------------------------------------------------------------------------------------------

CREDENTIALS_FORMAT = "readers-credentials"

_CRED_TR = {
 "fr": {"import credentials…": "importer les identifiants…", "export credentials…": "exporter les identifiants…", "Reader's credentials (*.json)": "Identifiants Reader's (*.json)",
        "credentials exported to %1 — the file holds your passwords: keep it private": "identifiants exportés dans %1 — le fichier contient vos mots de passe : gardez-le privé",
        "credentials imported": "identifiants importés", "server and login taken from %1": "serveur et identifiants repris de %1", "not a Reader's credentials file": "ce n'est pas un fichier d'identifiants Reader's", "this file holds nothing for %1": "ce fichier ne contient rien pour %1"},
 "de": {"import credentials…": "Zugangsdaten importieren…", "export credentials…": "Zugangsdaten exportieren…", "Reader's credentials (*.json)": "Reader's-Zugangsdaten (*.json)",
        "credentials exported to %1 — the file holds your passwords: keep it private": "Zugangsdaten nach %1 exportiert — die Datei enthält Ihre Passwörter: halten Sie sie privat",
        "credentials imported": "Zugangsdaten importiert", "server and login taken from %1": "Server und Anmeldung aus %1 übernommen", "not a Reader's credentials file": "keine Reader's-Zugangsdatendatei", "this file holds nothing for %1": "diese Datei enthält nichts für %1"},
 "es": {"import credentials…": "importar credenciales…", "export credentials…": "exportar credenciales…", "Reader's credentials (*.json)": "Credenciales Reader's (*.json)",
        "credentials exported to %1 — the file holds your passwords: keep it private": "credenciales exportadas a %1 — el archivo contiene sus contraseñas: manténgalo privado",
        "credentials imported": "credenciales importadas", "server and login taken from %1": "servidor y usuario tomados de %1", "not a Reader's credentials file": "no es un archivo de credenciales Reader's", "this file holds nothing for %1": "este archivo no contiene nada para %1"},
 "pt": {"import credentials…": "importar credenciais…", "export credentials…": "exportar credenciais…", "Reader's credentials (*.json)": "Credenciais Reader's (*.json)",
        "credentials exported to %1 — the file holds your passwords: keep it private": "credenciais exportadas para %1 — o ficheiro contém as suas palavras-passe: mantenha-o privado",
        "credentials imported": "credenciais importadas", "server and login taken from %1": "servidor e utilizador retirados de %1", "not a Reader's credentials file": "não é um ficheiro de credenciais Reader's", "this file holds nothing for %1": "este ficheiro não contém nada para %1"},
 "ru": {"import credentials…": "импортировать учётные данные…", "export credentials…": "экспортировать учётные данные…", "Reader's credentials (*.json)": "Учётные данные Reader's (*.json)",
        "credentials exported to %1 — the file holds your passwords: keep it private": "учётные данные экспортированы в %1 — файл содержит ваши пароли: храните его в тайне",
        "credentials imported": "учётные данные импортированы", "server and login taken from %1": "сервер и логин взяты из %1", "not a Reader's credentials file": "это не файл учётных данных Reader's", "this file holds nothing for %1": "в этом файле нет ничего для %1"},
}
for _l, _d in _CRED_TR.items():
    _TR.setdefault(_l, {}).update(_d)


def export_credentials(cfg, path):
    """Write this app's accounts into the file at path (created, or merged into an existing
    credentials file)."""
    path = os.path.expanduser(path)
    data = {}
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except ValueError:
                raise ValueError(_("not a Reader's credentials file"))
        if not isinstance(data, dict) or data.get("format") != CREDENTIALS_FORMAT:
            raise ValueError(_("not a Reader's credentials file"))
    data.update({"format": CREDENTIALS_FORMAT, "version": 1})
    data[APP] = {k: cfg[k] for k in CREDENTIAL_KEYS if cfg.get(k) not in (None, "", [], {})}
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return path


def import_credentials(cfg, path):
    """Take this app's accounts from a credentials file into cfg (the look and the rest stay)."""
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        try:
            data = json.load(f)
        except ValueError:
            raise ValueError(_("not a Reader's credentials file"))
    if not isinstance(data, dict) or data.get("format") != CREDENTIALS_FORMAT:
        raise ValueError(_("not a Reader's credentials file"))
    section = data.get(APP)
    message = _("credentials imported")
    keys = CREDENTIAL_KEYS
    if not isinstance(section, dict) or not section:
        other = next((name for name in CREDENTIAL_FALLBACK if isinstance(data.get(name), dict) and data[name]), None)
        if other is None:
            raise ValueError(_("this file holds nothing for %1", APP))
        section, keys = data[other], CREDENTIAL_FALLBACK[other]
        message = _("server and login taken from %1", "Reader's " + other.split("-", 1)[1].capitalize())
    for k in keys:
        if k in section:
            cfg[k] = section[k]
    return message


def credentials_cli(argv):
    """readers-… --export-credentials FILE / --import-credentials FILE, without opening a window."""
    for flag in ("--export-credentials", "--import-credentials"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                print(f"{flag} FILE", file=sys.stderr); sys.exit(2)
            path = argv[i + 1]
            cfg = load_config()
            try:
                if flag == "--export-credentials":
                    print(_("credentials exported to %1 — the file holds your passwords: keep it private", export_credentials(cfg, path)))
                else:
                    message = import_credentials(cfg, path); save_config(cfg); print(message)
            except (OSError, ValueError) as e:
                print(str(e), file=sys.stderr); sys.exit(1)
            sys.exit(0)


def credentials_dialog(parent, export, cfg):
    """The file picker for export (merging) or import. Returns (ok, message)."""
    title = _("export credentials…") if export else _("import credentials…")
    start = os.path.expanduser("~/readers-credentials.json")
    if export:
        path, _f = QtWidgets.QFileDialog.getSaveFileName(parent, title, start, _("Reader's credentials (*.json)"), options=QtWidgets.QFileDialog.DontConfirmOverwrite)
    else:
        path, _f = QtWidgets.QFileDialog.getOpenFileName(parent, title, os.path.dirname(start), _("Reader's credentials (*.json)"))
    if not path:
        return False, ""
    try:
        if export:
            return True, _("credentials exported to %1 — the file holds your passwords: keep it private", export_credentials(cfg, path))
        return True, import_credentials(cfg, path)
    except (OSError, ValueError) as e:
        return False, str(e)


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def urlhost(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc or url


def day_label(d, today):
    base = d.strftime("%A %-d %B").lower()
    if d == today:
        return _("today · ") + base
    if d == today + timedelta(days=1):
        return _("tomorrow · ") + base
    return base if d.year == today.year else base + f" {d.year}"


class Dot(QtWidgets.QWidget):
    """The calendar's colour, small: filled when the calendar is shown, a ring when hidden."""
    def __init__(self, color, filled=True, size=10):
        super().__init__(); self.color, self.filled = QtGui.QColor(color), filled; self.setFixedSize(size + 2, size + 2)

    def paintEvent(self, e):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(1, 1, self.width() - 2, self.height() - 2)
        if self.filled:
            p.setPen(QtCore.Qt.NoPen); p.setBrush(self.color)
        else:
            p.setPen(QtGui.QPen(self.color, 1.5)); p.setBrush(QtCore.Qt.NoBrush); r.adjust(1, 1, -1, -1)
        p.drawEllipse(r)


def paint_dot(p, center, event, block_color):
    """A discreet dot of the calendar's colour in a corner of an event block, ringed with the
    page colour so it reads on a black block as on a white one."""
    p.save(); p.setRenderHint(QtGui.QPainter.Antialiasing)
    ring = QtGui.QColor(block_color); ring = QtGui.QColor(255 - ring.red(), 255 - ring.green(), 255 - ring.blue())
    p.setPen(QtGui.QPen(ring, 1.2)); p.setBrush(QtGui.QColor(ce.color_of(getattr(event, "cal_url", ""))))
    p.drawEllipse(center, 3.6, 3.6)
    p.restore()


# The faces of the phone first, then what a Linux, a Windows and a Mac actually carry.
FAMILIES = {"sans": ["Roboto", "Inter", "Noto Sans", "Open Sans", "Lato", "Fira Sans", "DejaVu Sans",
                     "Segoe UI", "Helvetica Neue"],
            "serif": ["Literata", "Noto Serif", "Source Serif 4", "EB Garamond", "DejaVu Serif",
                      "Georgia", "Palatino"],
            "mono": ["Roboto Mono", "Noto Sans Mono", "Fira Mono", "DejaVu Sans Mono",
                     "Consolas", "Menlo"]}


def pick_family(choice):
    """The first installed face of the choice: Roboto Light as on the phone when it is there."""
    db = QtGui.QFontDatabase(); have = set(db.families()); names = [f for f in FAMILIES.get(choice, FAMILIES["sans"]) if f in have]
    if choice not in ("serif", "mono"):
        # the phone's text is a Light face: prefer a family that has one
        light = [f for f in names if any(st in ("Light", "Light Regular") for st in db.styles(f))]
        names = light + names
    return names[0] if names else {"serif": "serif", "mono": "monospace"}.get(choice, "sans-serif")


def fold(text):
    """Lower case without accents, for search: "reunion" finds "Réunion"."""
    return "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c)).lower()


class Magnifier(QtWidgets.QWidget):
    """A loupe drawn in the text colour: a ring and its handle."""
    def __init__(self, size=18):
        super().__init__(); self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette().color(QtGui.QPalette.WindowText); s = self.width()
        p.setPen(QtGui.QPen(c, max(1.6, s / 10), cap=QtCore.Qt.RoundCap)); p.setBrush(QtCore.Qt.NoBrush)
        r = s * 0.62; p.drawEllipse(QtCore.QRectF(1.5, 1.5, r, r))
        p.drawLine(QtCore.QPointF(1.5 + r * 0.86, 1.5 + r * 0.86), QtCore.QPointF(s - 2, s - 2))


def void(fn):
    """Call fn for its effect: an event handler returning a value makes PyQt complain."""
    fn()


def page_header(title_widgets, right_widgets=()):
    """The top of a page, as on the phone: quiet words on the left, actions on the right, a
    hairline under them."""
    w = QtWidgets.QWidget(); v = QtWidgets.QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 14); v.setSpacing(12)
    h = QtWidgets.QHBoxLayout(); h.setSpacing(26)
    for x in title_widgets: h.addWidget(x)
    h.addStretch(1)
    for x in right_widgets: h.addWidget(x)
    v.addLayout(h)
    sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1); v.addWidget(sep)
    return w


def link(text, fn, obj=None, tip=None):
    l = QtWidgets.QLabel(text); l.setCursor(QtCore.Qt.PointingHandCursor); l.mousePressEvent = lambda e: void(fn)
    if obj: l.setObjectName(obj)
    if tip: l.setToolTip(tip)
    return l


def column(max_width=720):
    """A reading column: content no wider than a page of text, left-aligned in the space."""
    host = QtWidgets.QWidget(); host.setMaximumWidth(max_width)
    lay = QtWidgets.QVBoxLayout(host); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
    return host, lay


def with_label(widget, label):
    """A widget with the dim word underneath that a row would have."""
    box = QtWidgets.QWidget(); v = QtWidgets.QVBoxLayout(box); v.setContentsMargins(0, 7, 0, 7); v.setSpacing(1)
    v.addWidget(widget)
    small = QtWidgets.QLabel(label); small.setObjectName("dim"); small.setProperty("role", "small"); v.addWidget(small)
    return box


def rule_line(top=10, bottom=10):
    box = QtWidgets.QWidget(); v = QtWidgets.QVBoxLayout(box); v.setContentsMargins(0, top, 0, bottom)
    sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1); v.addWidget(sep)
    return box


# ------------------------------------------------------------------------------------------
# Live text: what an event's place and notes hold that can be acted on. The same rules as the
# Android app — a run of 7 to 15 digits is a phone number, a date is not.
# ------------------------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
WEB_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.I)
PHONE_RE = re.compile(r"(?<![\w@])\(?\+?\d[\d\u00a0 ()./\-]{4,}\d(?![\w])")
DATE_RE = re.compile(r"\d{1,4}[./\-]\d{1,2}[./\-]\d{2,4}$")


def find_links(text):
    """[(start, end, uri)] for the phone numbers, mail and web addresses of a text."""
    found = []
    def add(start, end, uri):
        if not any(start < e and s0 < end for s0, e, _ in found):
            found.append((start, end, uri))
    for m in EMAIL_RE.finditer(text or ""):
        add(m.start(), m.end(), "mailto:" + m.group())
    for m in WEB_RE.finditer(text or ""):
        value = m.group().rstrip(".,;:)!?")
        if "." not in value:
            continue
        add(m.start(), m.start() + len(value), value if "://" in value else "https://" + value)
    for m in PHONE_RE.finditer(text or ""):
        value = m.group().strip().rstrip(".,;-/")
        digits = sum(c.isdigit() for c in value)
        if not 7 <= digits <= 15 or DATE_RE.match(value):
            continue
        add(m.start(), m.start() + len(value), "tel:" + value.replace(" ", "").replace("\u00a0", ""))
    return sorted(found)


def linked_html(text, whole_as=None):
    """The text as HTML with what can be acted on underlined and clickable."""
    from html import escape
    links = find_links(text)
    if not links and whole_as:
        return f'<a href="{escape(whole_as, quote=True)}">{escape(text)}</a>'
    out, at = [], 0
    for start, end, uri in links:
        out.append(escape(text[at:start]))
        out.append(f'<a href="{escape(uri, quote=True)}">{escape(text[start:end])}</a>')
        at = end
    out.append(escape(text[at:]))
    return "".join(out).replace("\n", "<br>")


def map_url(place):
    return "https://www.openstreetmap.org/search?query=" + QtCore.QUrl.toPercentEncoding(place).data().decode()


def live_label(text, whole_as=None, on_phone=None, role="body"):
    """A label whose links open: mail and web in their app, a phone number handed to on_phone
    (Linux has no dialer, so the number is copied instead)."""
    lab = QtWidgets.QLabel(linked_html(text, whole_as))
    lab.setTextFormat(QtCore.Qt.RichText); lab.setWordWrap(True); lab.setOpenExternalLinks(False)
    lab.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse)
    lab.setProperty("role", role)
    def opened(uri):
        if uri.startswith("tel:") and on_phone is not None:
            on_phone(uri[4:])
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(uri))
    lab.linkActivated.connect(opened)
    return lab


def dotted_row(color, content):
    """A row with its calendar's dot in the margin, on the first line."""
    line = QtWidgets.QWidget(); hl = QtWidgets.QHBoxLayout(line); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(12)
    dot = Dot(color, size=9); holder = QtWidgets.QVBoxLayout(); holder.setContentsMargins(0, 16, 0, 0); holder.addWidget(dot); holder.addStretch(1)
    hl.addLayout(holder); hl.addWidget(content, 1)
    return line


def is_google(ev):
    return getattr(ev, "google", None) is not None


def fmt_time(dt):
    return dt.strftime("%H:%M")


class Occ:
    """One occurrence shown in lists: event + its start/end datetimes."""
    def __init__(self, event, cal_name, start, end):
        self.event, self.cal_name, self.start, self.end = event, cal_name, start, end

    @property
    def date(self):
        return self.start.date()

    def when(self):
        if self.event.all_day:
            return _("all day")
        if self.end.date() == self.start.date():
            return f"{fmt_time(self.start)} – {fmt_time(self.end)}"
        return f"{fmt_time(self.start)} – {self.end.strftime('%-d %b')} {fmt_time(self.end)}"


# ------------------------------------------------------------------------------------------
# Threads
# ------------------------------------------------------------------------------------------

class Worker(QtCore.QObject):
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


# ------------------------------------------------------------------------------------------
# Month grid (the left column, also the date picker)
# ------------------------------------------------------------------------------------------

class MonthGrid(QtWidgets.QWidget):
    day_clicked = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.month = date.today().replace(day=1)
        self.marked = set()
        self.selected = None
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self.week_monday = True
        self.setMinimumHeight(220)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._cells = []

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def set_month(self, month):
        self.month = month.replace(day=1); self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cols, rows = 7, 7
        cw, ch = w / cols, h / rows
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        rule = QtGui.QColor(self.fg); rule.setAlphaF(0.25)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.8)
        first = 0 if self.week_monday else 6
        # header
        p.setFont(small); p.setPen(dim)
        for i in range(7):
            name = calendar.day_abbr[(first + i) % 7][:1].lower()
            p.drawText(QtCore.QRectF(i * cw, 0, cw, ch), QtCore.Qt.AlignCenter, name)
        # days
        self._cells = []
        start = self.month - timedelta(days=(self.month.weekday() - first) % 7)
        today = date.today()
        d = start
        for r in range(1, rows):
            for c in range(cols):
                rect = QtCore.QRectF(c * cw, r * ch, cw, ch).adjusted(3, 3, -3, -3)
                self._cells.append((rect, d))
                in_month = d.month == self.month.month and d.year == self.month.year
                if d == today:
                    p.fillRect(rect, self.fg); p.setPen(self.bg)
                else:
                    if d == self.selected:
                        p.setPen(QtGui.QPen(self.fg, 1)); p.drawRect(rect)
                    p.setPen(self.fg if in_month else rule)
                p.setFont(self.font())
                p.drawText(rect.adjusted(0, 0, 0, -ch * 0.28), QtCore.Qt.AlignCenter, str(d.day))
                if d in self.marked:
                    p.setFont(small)
                    p.drawText(rect.adjusted(0, ch * 0.45, 0, 0), QtCore.Qt.AlignCenter, "•")
                d += timedelta(days=1)

    def mousePressEvent(self, e):
        for rect, d in self._cells:
            if rect.contains(e.pos()):
                self.day_clicked.emit(d); return


# ------------------------------------------------------------------------------------------
# Week grid (the time grid, painted)
# ------------------------------------------------------------------------------------------

def place_lanes(items):
    """Google-Calendar style lanes: overlapping events share the column side by side.
    items: [(start_min, end_min, occ)] -> [(start_min, end_min, occ, lane, lanes)]."""
    out = []; cluster = []; lane_ends = []; cluster_end = -1
    def flush():
        for row in cluster: row[4] = len(lane_ends)
        out.extend(cluster); cluster.clear(); lane_ends.clear()
    for s, e, o in sorted(items, key=lambda x: (x[0], -x[1])):
        if cluster and s >= cluster_end: flush()
        lane = next((i for i, le in enumerate(lane_ends) if le <= s), -1)
        if lane < 0: lane_ends.append(e); lane = len(lane_ends) - 1
        else: lane_ends[lane] = e
        cluster.append([s, e, o, lane, 1]); cluster_end = max(cluster_end, e)
    flush()
    return out


STRIP_W = 28   # the folded weekend, in the workdays view


def week_columns(start, ndays, workdays, x0, total_w):
    """[(date, x, width)]: equal columns; in the workdays view only Monday to Friday, the
    weekend folded into a strip of STRIP_W at the right (see weekend_strip)."""
    days = [start + timedelta(days=i) for i in range(ndays)]
    if workdays:
        days = [d for d in days if d.weekday() < 5]; total_w -= STRIP_W
    unit = total_w / max(1, len(days))
    return [(d, x0 + i * unit, unit) for i, d in enumerate(days)]


def weekend_strip(x0, total_w):
    """The strip's x and width."""
    return x0 + total_w - STRIP_W, STRIP_W


class MonthBoard(QtWidgets.QWidget):
    """The month as the phone draws it: six weeks, each day a cell with its number and the lines
    of its events (a dot of the calendar's colour, the time when there is room, the title); an
    all-day event is a solid bar. Click a line: the event; click a day: that day's grid; double
    click: a new event that day; drag a line to another day to move the event."""
    day_clicked = QtCore.pyqtSignal(object)
    new_on_day = QtCore.pyqtSignal(object)
    event_clicked = QtCore.pyqtSignal(object)
    event_moved = QtCore.pyqtSignal(object, int, int)
    HEAD = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.month = date.today().replace(day=1); self.occs = []; self.week_monday = True
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self._lines = []; self._cells = []; self._press = None; self._target = None
        self.setMinimumHeight(420)

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def set_data(self, month, occs, week_monday=True):
        self.month, self.occs, self.week_monday = month.replace(day=1), occs, week_monday; self.update()

    def first_day(self):
        first = 0 if self.week_monday else 6
        return self.month - timedelta(days=(self.month.weekday() - first) % 7)

    @staticmethod
    def on_day(o, d):
        last = (o.end - timedelta(seconds=1)).date() if o.end > o.start else o.start.date()
        return o.start.date() <= d <= last

    def paintEvent(self, e):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height(); head = self.HEAD
        cw = w / 7; ch = (h - head) / 6
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        rule = QtGui.QColor(self.fg); rule.setAlphaF(0.18)
        base = QtGui.QFont(self.font())
        small = QtGui.QFont(base); small.setPointSizeF(base.pointSizeF() * 0.82)
        fm, fs = QtGui.QFontMetrics(base), QtGui.QFontMetrics(small)
        start = self.first_day(); today = date.today()
        self._lines = []; self._cells = []
        p.setFont(small); p.setPen(dim)
        for i in range(7):
            p.drawText(QtCore.QRectF(i * cw + 8, 0, cw - 16, head), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, (start + timedelta(days=i)).strftime("%a").lower())
        p.setPen(QtGui.QPen(rule, 1))
        for r in range(7):
            y = head + r * ch; p.drawLine(QtCore.QPointF(0, y), QtCore.QPointF(w, y))
        for c in range(1, 7):
            p.drawLine(QtCore.QPointF(c * cw, head), QtCore.QPointF(c * cw, h))
        lh = fs.height() + 3
        for r in range(6):
            for c in range(7):
                d = start + timedelta(days=r * 7 + c)
                cell = QtCore.QRectF(c * cw, head + r * ch, cw, ch)
                self._cells.append((cell, d))
                num = QtCore.QRectF(cell.left() + 6, cell.top() + 5, fm.horizontalAdvance("00") + 10, fm.height() + 2)
                p.setFont(base)
                if d == today:
                    p.fillRect(num, self.fg); p.setPen(self.bg)
                else:
                    p.setPen(self.fg if d.month == self.month.month else dim)
                p.drawText(num, QtCore.Qt.AlignCenter, str(d.day))
                if self._target is not None and self._target == d:
                    p.setPen(QtGui.QPen(self.fg, 1.5)); p.setBrush(QtCore.Qt.NoBrush); p.drawRect(cell.adjusted(1.5, 1.5, -1.5, -1.5))
                items = sorted((o for o in self.occs if self.on_day(o, d)), key=lambda o: (not o.event.all_day, o.start))
                top = num.bottom() + 4; room = int((cell.bottom() - top - 2) // lh)
                shown = items if len(items) <= room else items[:max(0, room - 1)]
                p.setFont(small)
                wide = cw >= 150
                for k, o in enumerate(shown):
                    line = QtCore.QRectF(cell.left() + 4, top + k * lh, cw - 8, lh - 1)
                    lifted = self._press is not None and self._press[0] is o and self._target is not None
                    if o.event.all_day:
                        p.fillRect(line, dim if lifted else self.fg); p.setPen(self.bg)
                        paint_dot(p, QtCore.QPointF(line.left() + 7, line.center().y()), o.event, self.fg)
                        text_rect = line.adjusted(15, 0, -3, 0)
                    else:
                        p.save(); p.setRenderHint(QtGui.QPainter.Antialiasing); p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(QtGui.QColor(ce.color_of(getattr(o.event, "cal_url", "")))); p.drawEllipse(QtCore.QPointF(line.left() + 5, line.center().y()), 3.2, 3.2); p.restore()
                        p.setPen(dim if lifted else self.fg)
                        text_rect = line.adjusted(13, 0, 0, 0)
                    p.setFont(small)
                    label = (fmt_time(o.start) + "  " if wide and not o.event.all_day and o.start.date() == d else "") + o.event.summary
                    p.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, fs.elidedText(label, QtCore.Qt.ElideRight, int(text_rect.width())))
                    self._lines.append((line, o, d))
                if len(shown) < len(items):
                    p.setPen(dim)
                    p.drawText(QtCore.QRectF(cell.left() + 17, top + len(shown) * lh, cw - 20, lh), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, f"+{len(items) - len(shown)}")

    def _cell_at(self, pos):
        return next((d for rect, d in self._cells if rect.contains(QtCore.QPointF(pos))), None)

    def mousePressEvent(self, e):
        hit = next(((o, d) for rect, o, d in reversed(self._lines) if rect.contains(QtCore.QPointF(e.pos()))), None)
        self._press = (hit[0], hit[1], e.pos()) if hit else (None, self._cell_at(e.pos()), e.pos())

    def mouseMoveEvent(self, e):
        if self._press and self._press[0] is not None and (e.pos() - self._press[2]).manhattanLength() > 6:
            self._target = self._cell_at(e.pos()); self.setCursor(QtCore.Qt.ClosedHandCursor); self.update()

    def mouseReleaseEvent(self, e):
        press, target = self._press, self._target
        self._press = None; self._target = None; self.unsetCursor(); self.update()
        if not press:
            return
        o, d, _ = press
        if o is not None and target is not None:
            if target != d:
                self.event_moved.emit(o, (target - d).days, 0)
        elif o is not None:
            self.event_clicked.emit(o)
        elif d is not None:
            self.day_clicked.emit(d)

    def mouseDoubleClickEvent(self, e):
        d = self._cell_at(e.pos())
        if d is not None and not any(rect.contains(QtCore.QPointF(e.pos())) for rect, _, _ in self._lines):
            self.new_on_day.emit(d)


class WeekHead(QtWidgets.QWidget):
    """Day headers and the all-day strip: stays put while the time grid scrolls."""
    event_clicked = QtCore.pyqtSignal(object)
    GUTTER = 48

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = date.today(); self.ndays = 7; self.workdays = False
        self.occs = []
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self._boxes = []
        self.setFixedHeight(64)

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    weekend_clicked = QtCore.pyqtSignal()

    def set_data(self, start, ndays, occs, workdays=False):
        self.start = start; self.ndays = ndays; self.workdays = workdays
        self.all_occs = list(occs)
        self.occs = [o for o in occs if o.event.all_day]
        rows = max((sum(1 for o in self.occs if o.start.date() <= start + timedelta(days=i) < o.end.date()) for i in range(ndays)), default=0)
        self.setFixedHeight((56 if ndays > 1 else 4) + rows * 22 + 4)
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); gutter, header = self.GUTTER, (56 if self.ndays > 1 else 4)
        cols = week_columns(self.start, self.ndays, self.workdays, gutter, w - gutter - 8)
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.78)
        today = date.today()
        self._boxes = []; self._heads = []
        for d, x, colw in (cols if self.ndays > 1 else []):
            narrow = colw < 70
            rect = QtCore.QRectF(x, 0, colw, header).adjusted(2, 4, -2, -4)
            if not narrow:
                rect = QtCore.QRectF(rect.center().x() - 30, rect.top(), 60, rect.height())
            self._heads.append((rect, d))
            if d == today:
                p.fillRect(rect, self.fg); p.setPen(self.bg)
            else:
                p.setPen(dim)
            label = d.strftime("%a").lower()[:1 if narrow else 3]
            p.setFont(small); p.drawText(rect.adjusted(0, 4, 0, -rect.height() / 2), QtCore.Qt.AlignCenter, label)
            p.setPen(self.bg if d == today else self.fg); p.setFont(small if narrow else self.font())
            p.drawText(rect.adjusted(0, rect.height() / 2 - 4, 0, 0), QtCore.Qt.AlignCenter, str(d.day))
        self._strip = None
        if self.workdays and self.ndays > 1:
            sx, sw = weekend_strip(gutter, w - gutter - 8)
            self._strip = QtCore.QRectF(sx, 0, sw, self.height())
            busy = {o.start.date() for o in self.all_occs}
            p.setFont(small)
            for i, d in enumerate([self.start + timedelta(days=k) for k in range(self.ndays) if (self.start + timedelta(days=k)).weekday() >= 5]):
                p.setPen(self.fg if d == today else dim)
                p.drawText(QtCore.QRectF(sx, 8 + i * 22, sw, 20), QtCore.Qt.AlignCenter, d.strftime("%a").lower()[:2] + ("·" if d in busy else ""))
        for d, x, colw in cols:
            y = header
            for o in self.occs:
                if o.start.date() <= d < o.end.date():
                    rect = QtCore.QRectF(x, y, colw, 20).adjusted(2, 0, -2, 0)
                    p.fillRect(rect, self.fg); p.setPen(self.bg); p.setFont(small)
                    dot = rect.width() >= 30
                    p.drawText(rect.adjusted(4, 0, -16 if dot else -4, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, p.fontMetrics().elidedText(o.event.summary, QtCore.Qt.ElideRight, int(rect.width()) - (20 if dot else 8)))
                    if dot:
                        paint_dot(p, QtCore.QPointF(rect.right() - 8, rect.center().y()), o.event, self.fg)
                        p.setFont(small)
                    self._boxes.append((rect, o)); y += 22

    day_clicked = QtCore.pyqtSignal(object)

    def mousePressEvent(self, e):
        for rect, o in self._boxes:
            if rect.contains(e.pos()):
                self.event_clicked.emit(o); return
        if getattr(self, "_strip", None) is not None and self._strip.contains(e.pos()):
            self.weekend_clicked.emit(); return
        if self.ndays > 1:
            for rect, d in self._heads:
                if rect.contains(e.pos()):
                    self.day_clicked.emit(d); return


class WeekGrid(QtWidgets.QWidget):
    """The 24-hour time grid of one week (scrolls). A block dragged with the mouse moves by
    quarter hours and whole columns; event_moved carries the shift on release."""
    event_clicked = QtCore.pyqtSignal(object)
    event_moved = QtCore.pyqtSignal(object, int, int)   # (occ, days, minutes)
    slot_clicked = QtCore.pyqtSignal(object, int)   # (date, hour)
    weekend_clicked = QtCore.pyqtSignal()
    HOUR = 48
    TOP = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = date.today(); self.ndays = 7; self.workdays = False
        self.occs = []
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self.setMinimumHeight(24 * self.HOUR + 2 * self.TOP)
        self._boxes = []
        self._press = None    # (occ, column index, start minute, end minute, press point) while the mouse is down on a block
        self._drag = None     # (occ, days shift, new start minute) while it is dragged
        self._settled = None  # the last drop, kept in place until the events come back refreshed

    def set_occs(self, occs):
        self.occs = occs; self._settled = None; self.update()

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); gutter, top = WeekHead.GUTTER, self.TOP
        cols = week_columns(self.start, self.ndays, self.workdays, gutter, w - gutter - 8)
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        rule = QtGui.QColor(self.fg); rule.setAlphaF(0.25)
        dimbg = QtGui.QColor(self.bg); dimbg.setAlphaF(0.7)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.78)
        today = date.today()
        self._boxes = []
        p.setPen(rule)
        for hh in range(25):
            y = top + hh * self.HOUR
            p.drawLine(QtCore.QPointF(gutter, y), QtCore.QPointF(w - 8, y))
        edges = [c[1] for c in cols] + ([weekend_strip(gutter, w - gutter - 8)[0]] if self.workdays else []) + [w - 8]
        for x in edges:
            p.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x, top + 24 * self.HOUR))
        p.setPen(dim); p.setFont(small)
        for hh in range(24):
            p.drawText(QtCore.QRectF(0, top + hh * self.HOUR - 8, gutter - 6, 16), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{hh:02d}")
        fm_small = QtGui.QFontMetrics(small)
        ghost = self._drag or self._settled
        lifted = None   # the dragged block, painted last so that it sits over the others
        for ci, (d, cx, colw) in enumerate(cols):
            items = []
            for o in self.occs:
                if o.event.all_day or o.start.date() != d:
                    continue
                s = o.start.hour * 60 + o.start.minute
                e_end = o.end if o.end.date() == d else datetime.combine(d, datetime.max.time(), tzinfo=o.start.tzinfo)
                e = max(e_end.hour * 60 + e_end.minute, s + 25)
                items.append((s, e, o))
            for s, e, o, lane, lanes in place_lanes(items):
                lane_w = (colw - 4) / lanes
                x0 = cx + 2 + lane * lane_w
                if ghost and ghost[0] is o:
                    # where it was lifted from: the column and time it was dropped on, whole width
                    tci = max(0, min(len(cols) - 1, ci + ghost[1])); ns = ghost[2]
                    lifted = (o, cols[tci][1], cols[tci][2], ns, ns + e - s, lane_w, lane, lanes, ci, s, e)
                    continue
                self._paint_block(p, o, cx, colw, lane_w, lane, lanes, s, e, fm_small, small, dimbg, label=fmt_time(o.start))
        for d, cx, colw in cols:
            if d != today:
                continue
            now = datetime.now()
            y = top + (now.hour + now.minute / 60) * self.HOUR
            p.setPen(QtGui.QPen(self.bg, 4)); p.drawLine(QtCore.QPointF(cx, y), QtCore.QPointF(cx + colw, y))
            p.setPen(QtGui.QPen(self.fg, 2)); p.drawLine(QtCore.QPointF(cx, y), QtCore.QPointF(cx + colw, y))
            p.setBrush(self.bg); p.setPen(QtCore.Qt.NoPen); p.drawEllipse(QtCore.QPointF(cx, y), 5, 5)
            p.setBrush(self.fg); p.drawEllipse(QtCore.QPointF(cx, y), 3, 3)
        if lifted:
            o, cx, colw, s, e, lane_w, lane, lanes, ci, s0, e0 = lifted
            self._boxes.append((QtCore.QRectF(cols[ci][1] + 2 + lane * lane_w, top + s0 / 60 * self.HOUR, lane_w, (e0 - s0) / 60 * self.HOUR), o))
            label = f"{s // 60:02d}:{s % 60:02d} – {(e // 60) % 24:02d}:{e % 60:02d}"
            self._paint_block(p, o, cx, colw, colw - 4, 0, 1, s, e, fm_small, small, dimbg, label=label, frame=True)

    def _paint_block(self, p, o, cx, colw, lane_w, lane, lanes, s, e, fm_small, small, dimbg, label, frame=False):
        top = self.TOP
        x0 = cx + 2 + lane * lane_w
        y0 = top + s / 60 * self.HOUR; y1 = top + e / 60 * self.HOUR
        # solid blocks: the white between them is the free time
        rect = QtCore.QRectF(x0, y0, lane_w - (1 if lane < lanes - 1 else 0), y1 - y0 - 1)
        p.fillRect(rect, self.fg)
        dot = rect.width() >= 22 and rect.height() >= 14
        if dot:
            paint_dot(p, QtCore.QPointF(rect.right() - 7, rect.top() + 7), o.event, self.fg)
        if frame:
            p.setPen(QtGui.QPen(self.bg, 1)); p.setBrush(QtCore.Qt.NoBrush); p.drawRect(rect.adjusted(1, 1, -1, -1))
        show_time = rect.height() >= fm_small.height() * 2 + 8
        inner = rect.adjusted(4, 2, -14 if dot else -4, -(fm_small.height() + 3) if show_time else -2)
        whole = int(inner.height() // fm_small.lineSpacing()) * fm_small.lineSpacing()
        inner.setHeight(max(whole, fm_small.lineSpacing()))
        p.save(); p.setClipRect(rect.adjusted(2, 1, -2, -1))
        p.setFont(small); p.setPen(self.bg)
        flags = QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft | (QtCore.Qt.TextWordWrap if lane_w >= 44 else 0)
        p.drawText(inner, flags, o.event.summary)
        if show_time:
            p.setPen(dimbg)
            if not frame and self.ndays == 1 and o.event.location:
                label += " · " + o.event.location
            p.drawText(rect.adjusted(4, 0, -4, -3), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft, label)
        p.restore()
        if not frame:
            self._boxes.append((rect, o))

    def _columns(self):
        gutter = WeekHead.GUTTER
        return week_columns(self.start, self.ndays, self.workdays, gutter, self.width() - gutter - 8)

    def mousePressEvent(self, e):
        for rect, o in reversed(self._boxes):
            if rect.contains(e.pos()):
                # a click opens the event on release; a move first lifts it
                ci = next((i for i, (d, cx, colw) in enumerate(self._columns()) if cx <= rect.center().x() < cx + colw), 0)
                s = int(round((rect.top() - self.TOP) / self.HOUR * 60)); en = int(round((rect.bottom() + 1 - self.TOP) / self.HOUR * 60))
                self._press = (o, ci, s, en, e.pos()); return
        gutter = WeekHead.GUTTER
        if self.workdays:
            sx, sw = weekend_strip(gutter, self.width() - gutter - 8)
            if sx <= e.pos().x() < sx + sw:
                self.weekend_clicked.emit(); return
        if self.TOP <= e.pos().y() < self.TOP + 24 * self.HOUR:
            for d, cx, colw in self._columns():
                if cx <= e.pos().x() < cx + colw:
                    self.slot_clicked.emit(d, int((e.pos().y() - self.TOP) / self.HOUR)); return

    def mouseMoveEvent(self, e):
        if not self._press:
            return
        o, ci, s, en, at = self._press
        dx, dy = e.pos().x() - at.x(), e.pos().y() - at.y()
        if not self._drag and abs(dx) < 6 and abs(dy) < 6:
            return
        cols = self._columns()
        days = max(-ci, min(len(cols) - 1 - ci, int(round(dx / cols[0][2]))))
        raw = dy / self.HOUR * 60
        ns = s if abs(raw) < 5 else max(0, min(1440 - min(en - s, 1440), int(round((s + raw) / 15)) * 15))
        self._drag = (o, days, ns); self.update()

    def mouseReleaseEvent(self, e):
        press, drag = self._press, self._drag
        self._press = self._drag = None
        if not press:
            return
        o, ci, s, en, at = press
        if drag is None:
            self.event_clicked.emit(o); return
        _, days, ns = drag
        if days or ns != s:
            self._settled = drag
            self.event_moved.emit(o, days, ns - s)
        self.update()


# ------------------------------------------------------------------------------------------
# Small helpers: text rows, prompts
# ------------------------------------------------------------------------------------------

def row(text, secondary=None, size=None, dim_secondary=True, click=None, obj=None, role=None):
    """A line of text and, under it, a dim smaller line: the Reader's row. role "tile" is the
    Android row size, "big" a page title; without it, the title size of the menus."""
    w = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(w); lay.setContentsMargins(0, 7, 0, 7); lay.setSpacing(1)
    t = QtWidgets.QLabel(text); t.setWordWrap(True)
    if role or size:
        t.setProperty("role", role or "tile")
    if obj:
        t.setObjectName(obj)
    lay.addWidget(t)
    if secondary:
        s = QtWidgets.QLabel(secondary); s.setObjectName("dim"); s.setProperty("role", "small"); s.setWordWrap(True); lay.addWidget(s)
    if click:
        w.setCursor(QtCore.Qt.PointingHandCursor); w.mousePressEvent = lambda e: void(click)
    return w


class TimeMask:
    """A time typed as digits around a ":" that is always there: "1830", "18.30", "18,30",
    "18h30", "9h15", "930" all read as hours and minutes. A separator typed by hand fixes where
    the hour ends; otherwise it is guessed ("18" → 18:, "9" → 9:, "230" → 2:30, "1830" → 18:30).
    Backspace over the ":" removes the hour's last digit, so the separator never goes away."""
    SEPS = ":.,hH"

    def __init__(self, initial=""):
        self.digits = "".join(c for c in initial if c.isdigit())[:4]
        self.cut = None   # the hour's length when the user typed a separator, else guessed

    def hour_len(self):
        d = self.digits
        if self.cut is not None:
            return min(self.cut, len(d))
        if len(d) <= 1: return len(d)
        if len(d) == 2: return 2 if int(d) <= 23 else 1
        if len(d) == 3: return 1 if int(d[1:]) <= 59 else 2
        return 2

    @property
    def text(self):
        h = self.hour_len()
        return self.digits[:h] + ":" + self.digits[h:]

    def apply(self, typed):
        """What the field should show after a keystroke that left it as `typed`."""
        nd = "".join(c for c in typed if c.isdigit())
        seps = sum(1 for c in typed if c in self.SEPS)
        if nd == self.digits:
            if seps == 0 and self.digits:          # the ":" was deleted: the hour loses a digit
                h = self.hour_len(); self.digits = self.digits[:h - 1] + self.digits[h:]; self.cut = None
            elif seps > 1 and self.digits:         # a separator typed: the hour ends here
                self.cut = min(len(self.digits), 2)
        else:
            if not nd.startswith(self.digits):     # replaced, not extended: guess again
                self.cut = None
            self.digits = nd[:4 if self.cut is None else self.cut + 2]
            if self.cut is not None and len(self.digits) < self.cut:
                self.cut = None
        return self.text

    @staticmethod
    def parse(text):
        """(hour, minute) of a masked text, or None. A lone minute digit is tens: 18:3 → 18:30."""
        if ":" not in text:
            return None
        h, m = text.split(":", 1)
        if not h.isdigit() or (m and not m.isdigit()):
            return None
        hh, mm = int(h), (int(m.ljust(2, "0")) if m else 0)
        return (hh, mm) if 0 <= hh <= 23 and 0 <= mm <= 59 else None


class TextPrompt(QtWidgets.QDialog):
    """A line (or a box) of text to type. With select_all the suggestion opens selected, so the
    first key replaces it instead of landing after its last character; time_mask keeps a ":"
    in the field whatever is typed (see TimeMask)."""
    def __init__(self, title, initial="", multiline=False, parent=None, select_all=False, time_mask=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QtWidgets.QVBoxLayout(self)
        lab = QtWidgets.QLabel(title); lab.setObjectName("dim"); lay.addWidget(lab)
        if multiline:
            self.edit = QtWidgets.QPlainTextEdit(initial)
        else:
            self.edit = QtWidgets.QLineEdit(initial); self.edit.returnPressed.connect(self.accept)
            if time_mask:
                self.mask = TimeMask(initial); self.edit.setText(self.mask.text)
                self.edit.textEdited.connect(self._masked)
            if select_all:
                self.edit.selectAll()
        lay.addWidget(self.edit)
        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        c = QtWidgets.QPushButton(_("cancel")); c.clicked.connect(self.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton(_("ok")); ok.setDefault(True); ok.clicked.connect(self.accept); btns.addWidget(ok)
        lay.addLayout(btns)
        self.resize(520, 300 if multiline else 120)

    def _masked(self, typed):
        self.edit.setText(self.mask.apply(typed)); self.edit.setCursorPosition(len(self.edit.text()))

    def value(self):
        return self.edit.toPlainText() if isinstance(self.edit, QtWidgets.QPlainTextEdit) else self.edit.text()


class DatePick(QtWidgets.QDialog):
    def __init__(self, initial, fg, bg, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("date"))
        self.value = initial
        lay = QtWidgets.QVBoxLayout(self)
        nav = QtWidgets.QHBoxLayout()
        prev = QtWidgets.QLabel("‹"); nxt = QtWidgets.QLabel("›"); self.title = QtWidgets.QLabel(); self.title.setObjectName("dim")
        prev.setObjectName("arrow"); nxt.setObjectName("arrow")
        QtWidgets.QShortcut(QtGui.QKeySequence("Left"), self, lambda: self._move(-1)); QtWidgets.QShortcut(QtGui.QKeySequence("Right"), self, lambda: self._move(1))
        for l in (prev, nxt):
            l.setCursor(QtCore.Qt.PointingHandCursor)
        nav.addWidget(prev); nav.addWidget(self.title, 1, QtCore.Qt.AlignCenter); nav.addWidget(nxt)
        lay.addLayout(nav)
        self.grid = MonthGrid(); self.grid.set_colors(fg, bg); self.grid.set_month(initial); self.grid.selected = initial
        self.grid.setMinimumSize(320, 260)
        self.grid.day_clicked.connect(self._pick)
        lay.addWidget(self.grid)
        prev.mousePressEvent = lambda e: self._move(-1)
        nxt.mousePressEvent = lambda e: self._move(1)
        self._refresh()

    def _refresh(self):
        self.title.setText(self.grid.month.strftime("%B %Y").lower())

    def _move(self, delta):
        m = self.grid.month
        y, mo = m.year, m.month + delta
        if mo == 0: y, mo = y - 1, 12
        if mo == 13: y, mo = y + 1, 1
        self.grid.set_month(date(y, mo, 1)); self._refresh()

    def _pick(self, d):
        self.value = d; self.accept()


# ------------------------------------------------------------------------------------------
# Main window
# ------------------------------------------------------------------------------------------

REMINDERS = [None, 0, 10, 30, 60, 120, 1440]
REPEATS = [("", _("does not repeat")), ("FREQ=DAILY", _("every day")), ("FREQ=WEEKLY", _("every week")), ("FREQ=MONTHLY", _("every month")), ("FREQ=YEARLY", _("every year"))]


def reminder_label(m):
    if m is None: return _("no reminder")
    if m == 0: return _("at the time of the event")
    if m < 60: return _("%1 minutes before", m)
    if m < 1440: return _("%1 hours before", m // 60)
    return _("%1 days before", m // 1440)


class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.client = None
        self.calendars = []          # [(name, url, writable)]
        self.events = []             # masters of the loaded window
        self.occs = []               # expanded occurrences of the loaded window
        self.threads = []
        self.font_size = int(self.cfg.get("font_size", 13))
        self.dark = bool(self.cfg.get("dark", False))
        self.window_days = 60
        self.setWindowTitle("reader's calendar")
        self.resize(1180, 760)

        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        outer = QtWidgets.QHBoxLayout(central); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        # ---- left column: month grid + navigation
        left = QtWidgets.QWidget(); left.setObjectName("left"); left.setFixedWidth(330)
        ll = QtWidgets.QVBoxLayout(left); ll.setContentsMargins(20, 18, 20, 12); ll.setSpacing(6)
        mnav = QtWidgets.QHBoxLayout()
        self.m_prev = QtWidgets.QLabel("‹"); self.m_next = QtWidgets.QLabel("›"); self.m_title = QtWidgets.QLabel(); self.m_title.setObjectName("dim")
        self.m_prev.setObjectName("arrow"); self.m_next.setObjectName("arrow")
        for l in (self.m_prev, self.m_next, self.m_title): l.setCursor(QtCore.Qt.PointingHandCursor)
        mnav.addWidget(self.m_prev); mnav.addWidget(self.m_title, 1, QtCore.Qt.AlignCenter); mnav.addWidget(self.m_next)
        ll.addLayout(mnav)
        self.grid = MonthGrid(); self.grid.setFixedHeight(250); ll.addWidget(self.grid)
        ll.addSpacing(10)
        self.nav_agenda = row(_("agenda"), click=lambda: self.show_agenda()); ll.addWidget(self.nav_agenda)
        self.nav_day = row(_("day"), click=lambda: self.show_day_grid(date.today())); ll.addWidget(self.nav_day)
        self.nav_week = row(_("week"), click=lambda: self.show_week(date.today())); ll.addWidget(self.nav_week)
        self.nav_workdays = row(_("workdays"), click=lambda: self.show_week(date.today(), workdays=True)); ll.addWidget(self.nav_workdays)
        self.nav_month = row(_("month"), click=lambda: self.show_month(date.today())); ll.addWidget(self.nav_month)
        self.nav_search = QtWidgets.QWidget(); sh = QtWidgets.QHBoxLayout(self.nav_search); sh.setContentsMargins(0, 0, 0, 0); sh.setSpacing(10)
        sh.addWidget(Magnifier(16), 0, QtCore.Qt.AlignVCenter); sh.addWidget(row(_("search"), click=self.show_search), 1)
        self.nav_search.setCursor(QtCore.Qt.PointingHandCursor); self.nav_search.mousePressEvent = lambda e: self.show_search(); ll.addWidget(self.nav_search)
        self.nav_new = row(_("+ new event"), click=lambda: self.edit_event(None)); ll.addWidget(self.nav_new)
        ll.addSpacing(8)
        # the calendars: as many as the account has, scrolling when the column is full
        cal_host = QtWidgets.QWidget(); self.cal_box = QtWidgets.QVBoxLayout(cal_host); self.cal_box.setContentsMargins(0, 0, 0, 0); self.cal_box.setSpacing(2)
        self.cal_box.addStretch(1)
        self.cal_scroll = QtWidgets.QScrollArea(); self.cal_scroll.setWidgetResizable(True); self.cal_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.cal_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff); self.cal_scroll.setWidget(cal_host)
        ll.addWidget(self.cal_scroll, 1)
        self.status = QtWidgets.QLabel(""); self.status.setObjectName("dim"); self.status.setProperty("role", "small"); self.status.setWordWrap(True)
        bottom = QtWidgets.QHBoxLayout(); bottom.addWidget(self.status, 1)
        gear = QtWidgets.QLabel("⚙"); gear.setObjectName("dim"); gear.setCursor(QtCore.Qt.PointingHandCursor); gear.setToolTip(_("settings")); gear.mousePressEvent = lambda e: self.show_settings(); bottom.addWidget(gear, 0)
        ll.addLayout(bottom)
        outer.addWidget(left)
        sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedWidth(1); outer.addWidget(sep)

        # ---- right: stacked pages
        self.pages = QtWidgets.QStackedWidget(); outer.addWidget(self.pages, 1)
        self.page_agenda = self._page_scroll(); self.pages.addWidget(self.page_agenda[0])
        self.page_week = QtWidgets.QWidget(); wl = QtWidgets.QVBoxLayout(self.page_week); wl.setContentsMargins(24, 18, 24, 12)
        wnav = QtWidgets.QHBoxLayout()
        self.w_prev = QtWidgets.QLabel("‹"); self.w_next = QtWidgets.QLabel("›"); self.w_title = QtWidgets.QLabel(); self.w_title.setObjectName("dim"); self.w_today = QtWidgets.QLabel(_("today"))
        self.w_prev.setObjectName("arrow"); self.w_next.setObjectName("arrow"); self.w_prev.setToolTip("←"); self.w_next.setToolTip("→")
        for l in (self.w_prev, self.w_next, self.w_today): l.setCursor(QtCore.Qt.PointingHandCursor)
        wnav.setSpacing(18)
        wnav.addWidget(self.w_prev); wnav.addWidget(self.w_title, 1, QtCore.Qt.AlignLeft); wnav.addWidget(self.w_today); wnav.addWidget(self.w_next)
        wl.addLayout(wnav)
        self.week_head = WeekHead(); self.week_head.event_clicked.connect(self.show_event); self.week_head.day_clicked.connect(self.show_day_grid); wl.addWidget(self.week_head)
        self.week = WeekGrid(); self.week.event_clicked.connect(self.show_event); self.week.slot_clicked.connect(self.new_at); self.week.event_moved.connect(self.move_event)
        self.week.weekend_clicked.connect(lambda: self.show_week(self.week.start)); self.week_head.weekend_clicked.connect(lambda: self.show_week(self.week.start))
        wscroll = QtWidgets.QScrollArea(); wscroll.setWidgetResizable(True); wscroll.setFrameShape(QtWidgets.QFrame.NoFrame); wscroll.setWidget(self.week)
        self.week_scroll = wscroll; wl.addWidget(wscroll, 1)
        self.pages.addWidget(self.page_week)
        self.page_event = self._page_scroll(); self.pages.addWidget(self.page_event[0])
        self.page_edit = self._page_scroll(); self.pages.addWidget(self.page_edit[0])
        self.page_settings = self._page_scroll(); self.pages.addWidget(self.page_settings[0])      # 4
        # 5: search — the field stays, the results below it are redrawn
        self.page_search = QtWidgets.QWidget(); sl = QtWidgets.QVBoxLayout(self.page_search); sl.setContentsMargins(28, 18, 28, 0); sl.setSpacing(4)
        self.search_edit = QtWidgets.QLineEdit(); self.search_edit.setObjectName("search"); self.search_edit.setPlaceholderText(_("search events: title, place, notes"))
        self.search_edit.textChanged.connect(lambda _t: self.search_timer.start())
        sline = QtWidgets.QHBoxLayout(); sline.setSpacing(14); sline.addWidget(Magnifier(22), 0, QtCore.Qt.AlignVCenter); sline.addWidget(self.search_edit, 1); sl.addLayout(sline)
        self.search_results = self._page_scroll(); self.search_results[1].setContentsMargins(0, 6, 0, 18); sl.addWidget(self.search_results[0], 1)
        self.pages.addWidget(self.page_search)
        self.search_timer = QtCore.QTimer(self, singleShot=True, interval=200, timeout=self.render_search)
        self._wide = None; self._wide_loading = False; self._back = None
        # 6: month board
        self.page_month = QtWidgets.QWidget(); ml = QtWidgets.QVBoxLayout(self.page_month); ml.setContentsMargins(24, 18, 24, 16); ml.setSpacing(8)
        mh = QtWidgets.QHBoxLayout(); mh.setSpacing(18)
        self.mo_title = QtWidgets.QLabel(); self.mo_title.setObjectName("dim")
        mh.addWidget(link("‹", lambda: self.step(-1), "arrow", "←")); mh.addWidget(self.mo_title, 1)
        mh.addWidget(link(_("today"), lambda: self.show_month(date.today()))); mh.addWidget(link("›", lambda: self.step(1), "arrow", "→"))
        ml.addLayout(mh)
        self.board = MonthBoard(); ml.addWidget(self.board, 1)
        self.board.event_clicked.connect(self.show_event); self.board.day_clicked.connect(self.show_day_grid)
        self.board.new_on_day.connect(lambda d: self.new_at(d, 9)); self.board.event_moved.connect(self.move_event)
        self.pages.addWidget(self.page_month)

        self.m_prev.mousePressEvent = lambda e: self.move_month(-1)
        self.m_next.mousePressEvent = lambda e: self.move_month(1)
        self.m_title.mousePressEvent = lambda e: self.go_today()
        self.grid.day_clicked.connect(self.show_day)
        self.w_prev.mousePressEvent = lambda e: self.step_grid(-1)
        self.w_next.mousePressEvent = lambda e: self.step_grid(1)
        self.w_today.mousePressEvent = lambda e: (self.show_week(date.today(), workdays=self.week.workdays) if self.week.ndays > 1 else self.show_day_grid(date.today()))

        for seq, fn in (("Ctrl+T", self.toggle_theme), ("F5", self.sync), ("Ctrl+R", self.sync), ("Ctrl+N", lambda: self.edit_event(None)),
                        ("Ctrl+=", lambda: self.zoom(1)), ("Ctrl++", lambda: self.zoom(1)), ("Ctrl+-", lambda: self.zoom(-1)),
                        ("Ctrl+,", self.show_settings), ("Ctrl+F", self.show_search), ("Ctrl+M", lambda: self.show_month(date.today())), ("Ctrl+S", lambda: self.pages.currentIndex() == 3 and self.save_event()), ("Ctrl+Return", lambda: self.pages.currentIndex() == 3 and self.save_event()), ("Ctrl+Q", self.close), ("Escape", self.escape), ("Ctrl+W", lambda: self.show_week(date.today())), ("Ctrl+Shift+W", lambda: self.show_week(date.today(), workdays=True)), ("Ctrl+D", self.go_today), ("Ctrl+J", lambda: self.show_day_grid(date.today())),
                        ("Left", lambda: self.step(-1)), ("Right", lambda: self.step(1))):
            QtWidgets.QShortcut(QtGui.QKeySequence(seq), self, fn)
        self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.sync); self.timer.start(SYNC_MINUTES * 60 * 1000)
        self.apply_style()
        self.refresh_month_title()
        # the view the window opens on: the week unless configured otherwise
        {"week": lambda: self.show_week(date.today()), "workdays": lambda: self.show_week(date.today(), workdays=True), "day": lambda: self.show_day_grid(date.today()), "month": lambda: self.show_month(date.today()), "agenda": self.show_agenda}.get(self.cfg.get("default_view", "week"), lambda: self.show_week(date.today()))()
        if self.cfg.get("url") or self.cfg.get("subscriptions") or self.google_ready():
            self.connect_client()
        else:
            QtCore.QTimer.singleShot(0, self.setup)

    def _page_scroll(self):
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        host = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(host); lay.setContentsMargins(28, 18, 28, 18); lay.setSpacing(2); lay.addStretch(1)
        scroll.setWidget(host)
        return scroll, lay

    @staticmethod
    def _clear(lay):
        while lay.count() > 1:
            item = lay.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    x = sub.takeAt(0)
                    if x.widget(): x.widget().hide(); x.widget().deleteLater()

    # ---- look ------------------------------------------------------------------------

    def apply_style(self):
        bg, fg = ("#000000", "#ffffff") if self.dark else ("#ffffff", "#000000")
        dim = "rgba(255,255,255,0.55)" if self.dark else "rgba(0,0,0,0.55)"
        rule = "rgba(255,255,255,0.25)" if self.dark else "rgba(0,0,0,0.25)"
        s = self.font_size
        # the Android scale: a row (tile), menus and titles at 0.8, secondary lines at 0.62
        tile = s + 5; title = round(tile * 0.8); small = max(9, round(tile * 0.62)); big = round(tile * 1.45)
        choice = self.cfg.get("font", "sans"); fam = pick_family(choice); weight = 300 if choice == "sans" else 400
        self.family, self.weight = fam, weight
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {bg}; color: {fg}; font-family: "{fam}"; font-size: {title}pt; font-weight: {weight}; }}
            QLabel#dim {{ color: {dim}; }}
            QLabel[role="tile"] {{ font-size: {tile}pt; }}
            QLabel[role="small"] {{ font-size: {small}pt; }}
            QLabel#big, QLabel[role="big"] {{ font-size: {big}pt; }}
            QLabel#arrow {{ font-size: {tile + 10}pt; padding: 0 12px 4px 12px; }}
            QLabel#heading {{ color: {dim}; font-size: {small}pt; letter-spacing: 1px; padding-top: 16px; }}
            QLineEdit#search {{ border: none; border-bottom: 1px solid {rule}; font-size: {tile}pt; padding: 8px 0; }}
            QLineEdit#titleedit {{ border: none; border-bottom: 1px solid {rule}; font-size: {big}pt; padding: 6px 0 10px 0; }}
            QLineEdit#field, QPlainTextEdit#field {{ border: none; border-bottom: 1px solid {rule}; padding: 6px 0; font-size: {title}pt; }}
            QLabel#primary {{ background: {fg}; color: {bg}; padding: 6px 18px; }}
            QLabel[role="body"] {{ font-size: {title}pt; }}
            QFrame#sep {{ background: {rule}; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background: {bg}; }}
            QScrollBar:vertical {{ background: {bg}; width: 6px; }} QScrollBar::handle:vertical {{ background: {rule}; min-height: 24px; }} QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QMenu {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }} QMenu::item:selected {{ background: {fg}; color: {bg}; }}
            QLineEdit, QPlainTextEdit, QComboBox {{ background: {bg}; color: {fg}; border: 1px solid {rule}; padding: 6px; }} QComboBox QAbstractItemView {{ background: {bg}; color: {fg}; selection-background-color: {fg}; selection-color: {bg}; }}
            QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {fg}; padding: 6px 18px; }} QPushButton:default {{ background: {fg}; color: {bg}; }}
            QPushButton#quiet {{ border: none; color: {dim}; padding: 6px 4px; }}
            QDialog {{ background: {bg}; }} QToolTip {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }}
        """)
        self.grid.set_colors(fg, bg); self.week.set_colors(fg, bg); self.week_head.set_colors(fg, bg); self.board.set_colors(fg, bg)
        f = QtGui.QFont(fam); f.setPointSize(s); f.setWeight(QtGui.QFont.Light if weight == 300 else QtGui.QFont.Normal); self.grid.setFont(f); self.week.setFont(f); self.week_head.setFont(f); self.board.setFont(f)
        QtWidgets.QApplication.instance().setFont(f)
        self.render_current()

    def toggle_theme(self):
        self.dark = not self.dark; self.cfg["dark"] = self.dark; save_config(self.cfg); self.apply_style()

    def zoom(self, delta):
        self.font_size = max(9, min(24, self.font_size + delta)); self.cfg["font_size"] = self.font_size; save_config(self.cfg); self.apply_style()

    # ---- network -----------------------------------------------------------------------

    def run(self, fn, on_done, on_failed=None):
        thread = QtCore.QThread(self); worker = Worker(fn); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.done.connect(on_done); worker.failed.connect(on_failed or self.show_error)
        worker.done.connect(thread.quit); worker.failed.connect(thread.quit)
        pair = (thread, worker); thread.finished.connect(lambda: self.threads.remove(pair) if pair in self.threads else None)
        self.threads.append(pair); thread.start()

    def show_error(self, text):
        self.status.setText(text)

    def setup(self):
        dlg = QtWidgets.QDialog(self); dlg.setWindowTitle("reader's calendar")
        form = QtWidgets.QFormLayout(dlg); form.setSpacing(12)
        intro = QtWidgets.QLabel(_("CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too."))
        intro.setObjectName("dim"); form.addRow(intro)
        url = QtWidgets.QLineEdit(self.cfg.get("url", "")); user = QtWidgets.QLineEdit(self.cfg.get("username", "")); pw = QtWidgets.QLineEdit(self.cfg.get("password", "")); pw.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow(_("server"), url); form.addRow(_("username"), user); form.addRow(_("app password"), pw)
        sub_hint = QtWidgets.QLabel(_("Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars."))
        sub_hint.setObjectName("dim"); form.addRow(sub_hint)
        subs = QtWidgets.QPlainTextEdit("\n".join(f"{x.get('name', '')} | {x.get('url', '')}" for x in self.cfg.get("subscriptions", [])))
        subs.setPlaceholderText("Google | https://calendar.google.com/calendar/ical/…/private-…/basic.ics"); subs.setFixedHeight(90)
        form.addRow(_("feeds"), subs)
        g_hint = QtWidgets.QLabel(_("Google Calendar, read and write, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, yourself as test user, then Publish app: in Testing, Google asks you to connect\nagain every 7 days) › Credentials › OAuth client ID, type Desktop app. Copy the ID and the secret here, then connect: the browser\nopens on Google (\"Google hasn't verified this app\": Advanced › continue — it is your own client) and comes back by itself."))
        g_hint.setObjectName("dim"); form.addRow(g_hint)
        g = self.cfg.get("google", {})
        g_id = QtWidgets.QLineEdit(g.get("client_id", "")); g_secret = QtWidgets.QLineEdit(g.get("client_secret", "")); g_secret.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow(_("client ID"), g_id); form.addRow(_("client secret"), g_secret)
        g_row = QtWidgets.QHBoxLayout(); g_state = QtWidgets.QLabel((_("Google account connected") if gc.can_write(g["tokens"]) else _("connected read-only — forget, then connect again to edit")) if g.get("tokens") else ""); g_state.setObjectName("dim")
        g_connect = QtWidgets.QPushButton(_("forget the Google account") if g.get("tokens") else _("connect the Google account"))
        def google_click():
            cur = self.cfg.get("google", {})
            if cur.get("tokens"):
                cur.pop("tokens", None); self.cfg["google"] = cur; save_config(self.cfg)
                g_state.setText(""); g_connect.setText(_("connect the Google account")); return
            cid, sec = g_id.text().strip(), g_secret.text().strip()
            if not cid: return
            self.cfg["google"] = {"client_id": cid, "client_secret": sec}; save_config(self.cfg)
            g_state.setText(_("waiting for the browser…")); g_connect.setEnabled(False)
            def done(tokens):
                self.cfg["google"]["tokens"] = tokens; save_config(self.cfg)
                g_state.setText(_("Google account connected")); g_connect.setText(_("forget the Google account")); g_connect.setEnabled(True)
            def failed(msg):
                g_state.setText(_("Google: %1", msg)); g_connect.setEnabled(True)
            self.run(lambda: gc.connect(cid, sec), done, failed)
        g_connect.clicked.connect(google_click); g_row.addWidget(g_connect); g_row.addWidget(g_state); g_row.addStretch(1)
        form.addRow(_("Google account"), g_row)
        btns = QtWidgets.QHBoxLayout()
        cred_msg = QtWidgets.QLabel(""); cred_msg.setObjectName("dim"); cred_msg.setWordWrap(True)
        def credentials(export):
            ok, message = credentials_dialog(dlg, export, self.cfg)
            cred_msg.setText(message)
            if ok and not export:
                save_config(self.cfg); dlg.done(2)
        for text, export in ((_("import credentials…"), False), (_("export credentials…"), True)):
            b = QtWidgets.QPushButton(text); b.setObjectName("quiet"); b.clicked.connect(lambda _c=False, x=export: credentials(x)); btns.addWidget(b)
        btns.addStretch(1)
        c = QtWidgets.QPushButton(_("cancel")); c.clicked.connect(dlg.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton(_("connect")); ok.setDefault(True); ok.clicked.connect(dlg.accept); btns.addWidget(ok)
        form.addRow(btns); form.addRow(cred_msg)
        credits = QtWidgets.QLabel(f"reader's calendar {VERSION} · " + _("Pierre Gallaz · developed with Claude Code")); credits.setObjectName("dim"); form.addRow(credits)
        dlg.resize(640, 440)
        result = dlg.exec_()
        if result == 2:     # credentials imported: the accounts are in cfg already
            self.status.setText(_("credentials imported")); self.connect_client(); return
        if result != QtWidgets.QDialog.Accepted:
            if not self.cfg.get("url") and not self.cfg.get("subscriptions") and not self.google_ready(): self.status.setText(_("not connected — Ctrl+, to set up"))
            return
        parsed = []
        for line in subs.toPlainText().splitlines():
            if "|" in line:
                name, u = line.split("|", 1)
            else:
                name, u = "", line
            u = u.strip()
            if u:
                parsed.append({"name": name.strip() or "feed", "url": u})
        gcfg = dict(self.cfg.get("google", {})); gcfg["client_id"] = g_id.text().strip(); gcfg["client_secret"] = g_secret.text().strip()
        self.cfg.update({"url": url.text().strip(), "username": user.text().strip(), "password": pw.text(), "subscriptions": parsed, "google": gcfg}); save_config(self.cfg)
        self.connect_client()

    def google_ready(self):
        g = self.cfg.get("google", {})
        return bool(g.get("client_id") and g.get("tokens"))

    def google_client(self):
        """The Google account, when one is connected; its renewed tokens are saved as they change."""
        if not self.google_ready():
            return None
        g = self.cfg["google"]
        return gc.Google(g["client_id"], g.get("client_secret", ""), g["tokens"])

    def connect_client(self):
        if not self.cfg.get("url"):
            # feeds and Google only: no CalDAV account
            self.client = None
            self.got_calendars([]); return
        self.client = ce.CalDAV(self.cfg["url"], self.cfg.get("username", ""), self.cfg.get("password", ""))
        self.status.setText(_("connecting…"))
        self.run(self.client.calendars, self.got_calendars)

    def feed_urls(self):
        return {x["url"] for x in self.cfg.get("subscriptions", [])}

    def got_calendars(self, cals):
        # CalDAV calendars first, then the read-only feeds, then the Google account's calendars
        self.calendars = [c for c in cals if c[1] not in self.feed_urls()] + [(x["name"], x["url"], False) for x in self.cfg.get("subscriptions", [])]
        google = self.google_client()
        if google and not any(u.startswith(gc.PREFIX) for _, u, _ in self.calendars):
            self.status.setText(_("connecting…"))
            self.run(google.calendars, lambda gcals: self.got_calendars(self.calendars + gcals)); return
        self._clear_calbox()
        hidden = set(self.cfg.get("hidden_calendars", []))
        for i, (name, url, writable) in enumerate(self.calendars):
            shown = url not in hidden
            line = QtWidgets.QWidget(); lay = QtWidgets.QHBoxLayout(line); lay.setContentsMargins(0, 3, 0, 3); lay.setSpacing(10)
            lay.addWidget(Dot(ce.color_of(url), filled=shown), 0, QtCore.Qt.AlignTop); lay.itemAt(0).widget().setContentsMargins(0, 0, 0, 0)
            text = QtWidgets.QVBoxLayout(); text.setSpacing(0)
            lab = QtWidgets.QLabel(name); lab.setObjectName("" if shown else "dim"); lab.setWordWrap(True); text.addWidget(lab)
            if not writable:
                ro = QtWidgets.QLabel(_("read only")); ro.setObjectName("dim"); ro.setProperty("role", "small"); text.addWidget(ro)
            lay.addLayout(text, 1)
            line.setCursor(QtCore.Qt.PointingHandCursor); line.setToolTip(name)
            line.mousePressEvent = lambda e, u=url: self.toggle_calendar(u)
            self.cal_box.insertWidget(i, line)
        self.sync()

    def _clear_calbox(self):
        while self.cal_box.count() > 1:     # the stretch stays last
            item = self.cal_box.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def toggle_calendar(self, url):
        hidden = set(self.cfg.get("hidden_calendars", []))
        hidden ^= {url}
        if len(hidden) >= len(self.calendars):
            return
        self.cfg["hidden_calendars"] = sorted(hidden); save_config(self.cfg)
        self.got_calendars(self.calendars)

    def window(self):
        start = datetime.combine(date.today() - timedelta(days=45), datetime.min.time(), LOCAL)
        return start, start + timedelta(days=45 + self.window_days)

    def sync(self):
        if not self.calendars:
            return
        self.status.setText(_("syncing…"))
        ws, we = self.window()
        self.run(self.fetcher(ws, we), self.got_events)

    def fetcher(self, ws, we):
        """A function (run off the UI thread) returning every occurrence between ws and we in the
        calendars shown."""
        hidden = set(self.cfg.get("hidden_calendars", []))
        cals = [(n, u) for n, u, _ in self.calendars if u not in hidden]
        feeds = self.feed_urls(); client = self.client; google = self.google_client()

        def fetch():
            out = []
            for name, url in cals:
                if url in feeds: events = ce.parse_feed(ce.fetch_feed(url), name)
                elif url.startswith(gc.PREFIX): events = google.events(url, ws, we) if google else []
                else: events = client.events(url, ws, we) if client else []
                for ev in events:
                    ev.cal_url = url
                    for s, e in ev.occurrences(ws, we):
                        out.append(Occ(ev, name, s, e))
            out.sort(key=lambda o: (o.start, not o.event.all_day))
            return out
        return fetch

    def got_events(self, occs):
        if self.google_ready(): save_config(self.cfg)   # the access token may have been renewed
        self.occs = occs
        self._wide = None          # the search's wider range is read again when next needed
        self.grid.marked = {o.date for o in occs}; self.grid.update()
        self.status.setText(_("synced %1", datetime.now().strftime("%H:%M")))
        if getattr(self, "notice", None):
            self.status.setText(self.notice); self.notice = None
        elif self.google_ready() and not gc.can_write(self.cfg["google"]["tokens"]):
            self.status.setText(_("Google: connect the account again (Ctrl+,) to edit its events"))
        self.render_current()

    # ---- pages -------------------------------------------------------------------------

    def render_current(self):
        idx = self.pages.currentIndex()
        if idx == 0: self.render_agenda()
        elif idx == 1: self.render_week()
        elif idx == 2 and getattr(self, "_event", None): self.show_event(self._event, refresh=True)
        elif idx == 4: self.render_settings()
        elif idx == 5: self.render_search()
        elif idx == 6: self.render_month()

    def refresh_month_title(self):
        self.m_title.setText(self.grid.month.strftime("%B %Y").lower())

    def move_month(self, delta):
        m = self.grid.month; y, mo = m.year, m.month + delta
        if mo == 0: y, mo = y - 1, 12
        if mo == 13: y, mo = y + 1, 1
        self.grid.set_month(date(y, mo, 1)); self.refresh_month_title()

    def go_today(self):
        self.grid.set_month(date.today()); self.refresh_month_title(); self.show_agenda()

    def show_agenda(self, from_date=None):
        self._back = None
        self.pages.setCurrentIndex(0); self._agenda_from = from_date or date.today(); self.render_agenda()

    def show_day(self, d):
        self.grid.selected = d; self.grid.update(); self.show_agenda(d)

    def render_agenda(self):
        scroll, lay = self.page_agenda
        self._clear(lay)
        today = date.today(); start = getattr(self, "_agenda_from", today)
        occs = [o for o in self.occs if o.end > datetime.combine(start, datetime.min.time(), LOCAL)]
        i = 0
        if not occs:
            lay.insertWidget(i, row(_("nothing planned"), obj="dim")); i += 1
        cur = None
        for o in occs:
            d = o.date if o.date >= start else start
            if d != cur:
                cur = d
                h = QtWidgets.QLabel(day_label(d, today)); h.setObjectName("" if d == today else "dim"); h.setProperty("role", "small")
                h.setContentsMargins(0, 18, 0, 0); h.setCursor(QtCore.Qt.PointingHandCursor); h.mousePressEvent = lambda e, dd=d: self.show_day_grid(dd)
                lay.insertWidget(i, h); i += 1
            sec = o.when() + (" · " + o.event.location if o.event.location else "")
            lay.insertWidget(i, row(o.event.summary, sec, size=self.font_size + 4, click=lambda oo=o: self.show_event(oo))); i += 1
        more = row(_("show more days"), obj="dim", click=self.more_days); lay.insertWidget(i, more)

    def escape(self):
        if self.pages.currentIndex() == 5 and self.search_edit.text():
            self.search_edit.clear(); return
        (self._back or self.show_agenda)()

    # ---- search ------------------------------------------------------------------------

    def show_search(self):
        self._back = None
        self.pages.setCurrentIndex(5); self.search_edit.setFocus(); self.search_edit.selectAll()
        self.render_search()

    def _open_from_search(self, o):
        self.show_event(o); self._back = self.back_to_search; self.show_event(o)   # redrawn with "← back" to the results

    def back_to_search(self):
        self.pages.setCurrentIndex(5); self._back = None; self.render_search()

    def _ensure_wide(self):
        """One year back and two ahead, read once, so that a search finds more than the weeks shown."""
        if self._wide is not None or self._wide_loading or not self.calendars:
            return
        self._wide_loading = True
        today = datetime.combine(date.today(), datetime.min.time(), LOCAL)
        def done(occs):
            self._wide_loading = False; self._wide = occs
            if self.pages.currentIndex() == 5: self.render_search()
        def failed(msg):
            self._wide_loading = False; self.status.setText(msg)
        self.run(self.fetcher(today - timedelta(days=365), today + timedelta(days=730)), done, failed)

    def render_search(self):
        if self.pages.currentIndex() != 5:
            return
        self._ensure_wide()
        scroll, lay = self.search_results
        self._clear(lay)
        words = fold(self.search_edit.text()).split()
        if not words:
            if self._wide_loading:
                lay.insertWidget(0, row(_("searching further…"), obj="dim"))
            return
        source = self._wide if self._wide is not None else self.occs
        found, seen = [], {}
        now = datetime.now(LOCAL)
        for o in source:
            ev = o.event
            if not all(w in fold(" ".join((ev.summary, ev.location, ev.description, o.cal_name))) for w in words):
                continue
            # a repeating event once: its next occurrence, or its last one if all are past
            key = (getattr(ev, "cal_url", ""), (ev.google.get("recurring") or ev.uid) if is_google(ev) else (ev.uid or ev.href))
            prev = seen.get(key)
            if prev is None or (prev.end < now and o.end >= now) or (prev.end < now and o.end < now and o.start > prev.start):
                seen[key] = o
        found = sorted(seen.values(), key=lambda o: o.start)
        upcoming = [o for o in found if o.end >= now]; past = [o for o in found if o.end < now][::-1]
        i = 0
        if not found:
            lay.insertWidget(i, row(_("searching further…") if self._wide_loading else _("no event found"), obj="dim")); i += 1
        today = date.today()
        for heading, items in ((_("upcoming"), upcoming), (_("past"), past)):
            if not items:
                continue
            h = QtWidgets.QLabel(heading); h.setObjectName("heading"); lay.insertWidget(i, h); i += 1
            for o in items[:150]:
                ev = o.event
                repeats = ev.rrule or getattr(ev, "series_rule", "")
                sec = " · ".join(x for x in (day_label(o.date, today), o.when(), o.cal_name, _("repeats") if repeats else "", ev.location) if x)
                lay.insertWidget(i, dotted_row(ce.color_of(getattr(ev, "cal_url", "")), row(ev.summary, sec, role="tile", click=lambda oo=o: self._open_from_search(oo)))); i += 1

    # ---- settings ----------------------------------------------------------------------

    def show_settings(self):
        self._back = None
        self.pages.setCurrentIndex(4); self.render_settings()

    def _cfg(self, key, value):
        self.cfg[key] = value; save_config(self.cfg); self.render_settings()

    def render_settings(self):
        scroll, lay = self.page_settings
        self._clear(lay)
        host = QtWidgets.QWidget(); host.setMaximumWidth(1000); outer = QtWidgets.QVBoxLayout(host); outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page_header([link(_("← back"), self.show_agenda), QtWidgets.QLabel(_("settings"))]))
        two = QtWidgets.QHBoxLayout(); two.setContentsMargins(0, 0, 0, 0); two.setSpacing(64); outer.addLayout(two)
        left = QtWidgets.QVBoxLayout(); left.setSpacing(0); right = QtWidgets.QVBoxLayout(); right.setSpacing(0)
        def heading(text, box):
            h = QtWidgets.QLabel(text); h.setObjectName("heading"); box.addWidget(h)
        heading(_("look"), left)
        left.addWidget(row(_("white on black") if self.dark else _("black on white"), _("colours"), role="tile", click=lambda: (self.toggle_theme(), self.render_settings())))
        size_line = QtWidgets.QHBoxLayout(); size_line.setSpacing(4)
        size_line.addWidget(row(f"{self.font_size} pt", _("text size"), role="tile"))
        size_line.addSpacing(18)
        size_line.addWidget(link("−", lambda: (self.zoom(-1), self.render_settings()), "arrow", "Ctrl+-"), 0, QtCore.Qt.AlignVCenter)
        size_line.addWidget(link("+", lambda: (self.zoom(1), self.render_settings()), "arrow", "Ctrl+="), 0, QtCore.Qt.AlignVCenter)
        size_line.addStretch(1); left.addLayout(size_line)
        fonts = [("sans", "sans-serif"), ("serif", "serif"), ("mono", "mono")]
        cur = self.cfg.get("font", "sans") if self.cfg.get("font") in dict(fonts) else "sans"
        nxt = fonts[([f for f, _x in fonts].index(cur) + 1) % 3][0]
        left.addWidget(row(dict(fonts)[cur], pick_family(cur), role="tile", click=lambda: (self.cfg.__setitem__("font", nxt), save_config(self.cfg), self.apply_style(), self.render_settings())))
        heading(_("calendar"), left)
        views = [("week", _("week")), ("workdays", _("workdays")), ("month", _("month")), ("day", _("day")), ("agenda", _("agenda"))]
        v = self.cfg.get("default_view", "week"); vi = next((i for i, x in enumerate(views) if x[0] == v), 0)
        left.addWidget(row(views[vi][1], _("opens on"), role="tile", click=lambda: self._cfg("default_view", views[(vi + 1) % len(views)][0])))
        monday = self.cfg.get("week_monday", True)
        left.addWidget(row(_("monday") if monday else _("sunday"), _("first day of the week"), role="tile", click=lambda: (self._cfg("week_monday", not monday), setattr(self.grid, "week_monday", not monday), self.grid.update())))
        left.addWidget(row(reminder_label(self.cfg.get("default_reminder", 10)), _("default reminder"), role="tile",
                           click=lambda: (lambda m: m is not None and self._cfg("default_reminder", None if m == "none" else m))(self._menu_pick([(reminder_label(m), ("none" if m is None else m)) for m in REMINDERS]))))
        writable = [(n, u) for n, u, w in self.calendars if w]
        if writable:
            dc = self.cfg.get("default_calendar"); du = dc if any(u == dc for _x, u in writable) else writable[0][1]
            left.addWidget(dotted_row(ce.color_of(du), row(next(n for n, u in writable if u == du), _("default calendar"), role="tile", click=lambda: (lambda u: u is not None and self._cfg("default_calendar", u))(self._menu_pick(writable)))))
        left.addStretch(1)
        heading(_("accounts"), right)
        right.addWidget(row(urlhost(self.cfg["url"]) if self.cfg.get("url") else "—", "CalDAV", role="tile", click=self.setup))
        g = self.cfg.get("google", {})
        right.addWidget(row(_("Google account connected") if g.get("tokens") else "—", "Google", role="tile", click=self.setup))
        right.addWidget(row(_("%1 feeds", len(self.cfg.get("subscriptions", []))), _("feeds"), role="tile", click=self.setup))
        right.addWidget(row(_("sync now"), self.status.text() or None, role="tile", click=self.sync))
        def cred(export):
            ok, message = credentials_dialog(self, export, self.cfg)
            if message: self.status.setText(message)
            if ok and not export:
                save_config(self.cfg); self.connect_client()
            self.render_settings()
        right.addWidget(row(_("export credentials…"), None, role="tile", click=lambda: cred(True)))
        right.addWidget(row(_("import credentials…"), None, role="tile", click=lambda: cred(False)))
        credits = QtWidgets.QLabel(f"reader's calendar {VERSION}\n" + _("Pierre Gallaz · developed with Claude Code")); credits.setObjectName("dim"); credits.setProperty("role", "small")
        credits.setContentsMargins(0, 28, 0, 0); right.addWidget(credits)
        right.addStretch(1)
        two.addLayout(left, 1); two.addLayout(right, 1)
        lay.insertWidget(0, host)

    def more_days(self):
        self.window_days += 60; self.sync()

    def show_week(self, d, workdays=False):
        first = 0 if (workdays or self.cfg.get("week_monday", True)) else 6
        start = d - timedelta(days=(d.weekday() - first) % 7)
        self.week.start = start; self.week.ndays = 7; self.week_head.ndays = 7
        self.week.workdays = workdays; self.week_head.workdays = workdays
        self.w_title.setText(start.strftime("%-d %b") + " – " + (start + timedelta(days=6)).strftime("%-d %b %Y").lower())
        self._open_grid()

    def show_day_grid(self, d):
        """One day as a time grid: the same page, one column wide."""
        self.week.start = d; self.week.ndays = 1; self.week_head.ndays = 1
        self.week.workdays = False; self.week_head.workdays = False
        self.w_title.setText(day_label(d, date.today()))
        self._open_grid()

    def show_month(self, d):
        self._back = None
        self.board.month = d.replace(day=1); self.pages.setCurrentIndex(6); self.render_month()
        self.grid.set_month(d); self.refresh_month_title()

    def render_month(self):
        self.board.set_data(self.board.month, self.occs, self.cfg.get("week_monday", True))
        self.mo_title.setText(self.board.month.strftime("%B %Y").lower())
        first = self.board.first_day()
        self.ensure_window(first + timedelta(days=42))

    def ensure_window(self, last_day):
        """The synced range (45 days back, window_days ahead) stretched to a month shown further on."""
        need = (last_day - date.today()).days + 1
        if need > self.window_days:
            self.window_days = need + 14; self.sync()

    def step(self, delta):
        """← / →: the previous or next week or day in the grids, the previous or next month elsewhere."""
        if self.pages.currentIndex() == 1: self.step_grid(delta)
        elif self.pages.currentIndex() == 6: self.show_month(add_months(self.board.month, delta))
        elif self.pages.currentIndex() == 0: self.move_month(delta)

    def step_grid(self, delta):
        n = self.week.ndays
        if n > 1: self.show_week(self.week.start + timedelta(days=n * delta), workdays=self.week.workdays)
        else: self.show_day_grid(self.week.start + timedelta(days=delta))

    def _open_grid(self):
        self._back = None
        self.pages.setCurrentIndex(1); self.render_week()
        # open an hour before the first thing shown (or now, if today is shown); 08:00 when empty
        days = [self.week.start + timedelta(days=i) for i in range(self.week.ndays)]
        firsts = [o.start.hour for o in self.week.occs if not o.event.all_day and o.start.date() in days]
        if date.today() in days: firsts.append(datetime.now().hour)
        target = max(0, min(18, (min(firsts) if firsts else 8) - 1))
        QtCore.QTimer.singleShot(0, lambda: self.week_scroll.verticalScrollBar().setValue(int(WeekGrid.HOUR * target)))

    def new_at(self, d, hour):
        self.edit_event(None)
        st = self._edit_state
        st["start"] = datetime.combine(d, datetime.min.time(), LOCAL).replace(hour=hour); st["end"] = st["start"] + timedelta(hours=1)
        self.render_edit()

    def render_week(self):
        s = self.week.start; e = s + timedelta(days=self.week.ndays)
        self.week.set_occs([o for o in self.occs if o.start.date() < e and o.end.date() >= s])
        self.week_head.set_data(s, self.week.ndays, self.week.occs, self.week.workdays)

    # ---- moving an event by dragging it in the grid ---------------------------------------

    def move_event(self, o, days, minutes):
        """A block dropped elsewhere: the event shifted by whole days and minutes, nothing else
        touched. A series asks first, since every occurrence moves with it."""
        ev = o.event
        if not ev.writable:
            self.status.setText(self.read_only_reason(ev)); self.render_current(); return
        if is_google(ev):
            if ev.google.get("recurring"):
                m = QtWidgets.QMenu(self)
                m.addAction(_("move only this event"), lambda: self._do_move(o, days, minutes))
                m.addAction(_("move the whole series"), lambda: self._do_move(o, days, minutes, series=True))
                if m.exec_(QtGui.QCursor.pos()) is None:
                    self.render_current()
                return
            self._do_move(o, days, minutes); return
        if ev.rrule:
            m = QtWidgets.QMenu(self)
            m.addAction(_("move the whole series"), lambda: self._do_move(o, days, minutes))
            if m.exec_(QtGui.QCursor.pos()) is None:
                self.render_current()   # no choice: the block goes back
            return
        self._do_move(o, days, minutes)

    def _do_move(self, o, days, minutes, series=False):
        ev = o.event; delta = timedelta(days=days, minutes=0 if ev.all_day else minutes)
        if is_google(ev):
            google = self.google_client()
            self.status.setText(_("saving…"))
            self.run(lambda: google.shift(ev, delta, series), lambda _: self.sync(), self.write_failed); return
        start = ev.start + delta
        end = (ev.end - timedelta(days=1) if ev.all_day else ev.end) + delta
        keep = [l for l in ev.lines if l.split(":", 1)[0].split(";", 1)[0].upper() in ("EXDATE", "CREATED", "SEQUENCE", "CLASS", "STATUS", "TRANSP", "CATEGORIES")]
        kw = dict(summary=ev.summary, start=start, end=end, all_day=ev.all_day, location=ev.location, description=ev.description, rrule=ev.rrule, reminder=ev.reminder, keep_lines=keep)
        self.status.setText(_("saving…"))
        self.run(lambda: self.client.put(ev.href, ce.build_ics(ev.uid, **kw), etag=ev.etag), lambda _: self.sync(), lambda err: (self.status.setText(str(err)), self.render_current()))

    def show_event(self, o, refresh=False):
        self._event = o
        scroll, lay = self.page_event
        self._clear(lay)
        ev = o.event
        right = [link(_("edit"), lambda: self.edit_event(o)), link(_("delete"), lambda: self.delete_event(o))] if ev.writable else []
        host, col = column(720)
        col.addWidget(page_header([link(_("← back"), self._back or self.show_agenda)], right))
        title = QtWidgets.QLabel(ev.summary); title.setObjectName("big"); title.setWordWrap(True); title.setContentsMargins(0, 10, 0, 6); col.addWidget(title)
        last = o.end - timedelta(seconds=1)
        if o.start.date() == last.date():
            when = o.start.strftime("%A %-d %B %Y").lower()
        else:
            when = o.start.strftime("%-d %B").lower() + " – " + last.strftime("%-d %B %Y").lower()
        d = QtWidgets.QLabel(when); d.setProperty("role", "tile"); col.addWidget(d)
        t = QtWidgets.QLabel(o.when()); t.setObjectName("dim"); t.setProperty("role", "tile"); col.addWidget(t)
        col.addWidget(rule_line(18, 8))
        cal = o.cal_name + ("" if ev.writable else _(" · read-only"))
        col.addWidget(dotted_row(ce.color_of(getattr(ev, "cal_url", "")), row(cal, _("calendar"))))
        rule = ev.rrule or getattr(ev, "series_rule", "")
        if rule:
            col.addWidget(row(dict(REPEATS).get(rule, _("repeats")), _("repeat")))
        if ev.reminder is not None:
            col.addWidget(row(reminder_label(ev.reminder), _("reminder")))
        # the place and the notes are live text: a mail address or a link opens, a place opens the
        # map, a phone number is copied (a computer has no dialer) — and everything stays selectable
        if ev.location:
            place = live_label(ev.location, whole_as=map_url(ev.location), on_phone=self.copy_number, role="tile")
            col.addWidget(with_label(place, _("location")))
        if ev.description:
            col.addWidget(rule_line(8, 8))
            col.addWidget(live_label(ev.description, on_phone=self.copy_number))
        lay.insertWidget(0, host)
        self.pages.setCurrentIndex(2)

    def delete_event(self, o):
        m = QtWidgets.QMenu(self)
        if is_google(o.event) and o.event.google.get("recurring"):
            m.addAction(_("delete only this event"), lambda: self._do_delete(o))
            m.addAction(_("delete") + _(" the whole series"), lambda: self._do_delete(o, series=True))
        else:
            m.addAction(_("delete") + (_(" the whole series") if o.event.rrule or getattr(o.event, "series_rule", "") else ""), lambda: self._do_delete(o))
        m.exec_(QtGui.QCursor.pos())

    def _do_delete(self, o, series=False):
        self.status.setText(_("deleting…"))
        if is_google(o.event):
            google = self.google_client()
            self.run(lambda: google.delete(o.event, series), lambda _: (self.show_agenda(), self.sync()), self.write_failed); return
        self.run(lambda: self.client.delete(o.event.href), lambda _: (self.show_agenda(), self.sync()))

    def copy_number(self, number):
        QtWidgets.QApplication.clipboard().setText(number)
        self.status.setText(_("%1 copied", number))

    def read_only_reason(self, ev):
        if is_google(ev):
            if self.google_ready() and not gc.can_write(self.cfg["google"]["tokens"]):
                return _("Google: connect the account again (Ctrl+,) to edit its events")
            return _("this calendar is read-only")
        return _("this event comes from a read-only feed")

    def write_failed(self, message):
        """A write refused: say why, and show the calendar as it is now (a 412 means it changed)."""
        message = _(message)
        self.notice = message       # kept over the "synced" line that follows
        self.status.setText(message)
        if self.pages.currentIndex() == 3:
            self.show_agenda()
        self.sync()

    # ---- edit --------------------------------------------------------------------------

    def edit_event(self, o, source=None, scope=None):
        """source: the Event the form edits (a Google series' master); scope: "this" for one
        occurrence of a Google series, "series" for all of it."""
        if o is not None and not o.event.writable:
            self.status.setText(self.read_only_reason(o.event)); return
        writable = [(n, u) for n, u, w in self.calendars if w]
        if not writable:
            self.status.setText(_("no writable calendar")); return
        if o is not None and scope is None and is_google(o.event) and o.event.google.get("recurring"):
            google = self.google_client()
            m = QtWidgets.QMenu(self)
            m.addAction(_("edit only this event"), lambda: self.edit_event(o, o.event, "this"))
            m.addAction(_("edit the whole series"), lambda: (self.status.setText(_("connecting…")), self.run(lambda: google.master(o.event), lambda master: self.edit_event(o, master, "series"), self.write_failed)))
            m.exec_(QtGui.QCursor.pos())
            return
        ev = source or (o.event if o else None)
        now = datetime.now(LOCAL).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        state = {
            "uid": ev.uid if ev else None, "href": ev.href if ev else None, "etag": ev.etag if ev else None,
            "summary": ev.summary if ev else "", "all_day": ev.all_day if ev else False,
            "start": (ev.start if isinstance(ev.start, datetime) else datetime.combine(ev.start, datetime.min.time(), LOCAL)) if ev else now,
            "end": (ev.end - (timedelta(days=1) if ev.all_day else timedelta(0)) if isinstance(ev.end, datetime) else datetime.combine(ev.end - timedelta(days=1), datetime.min.time(), LOCAL)) if ev else now + timedelta(hours=1),
            "location": ev.location if ev else "", "description": ev.description if ev else "",
            "reminder": ev.reminder if ev else self.cfg.get("default_reminder", 10), "rrule": (ev.rrule or getattr(ev, "series_rule", "")) if ev and scope != "this" else "",
            "gevent": ev if ev is not None and is_google(ev) else None, "scope": scope,
            "cal": getattr(ev, "cal_url", None) if ev else (self.cfg.get("default_calendar") or writable[0][1]),
        }
        if state["cal"] not in [u for _, u in writable]:
            state["cal"] = writable[0][1]
        self._edit_state = state
        self.render_edit()
        self.pages.setCurrentIndex(3)


    def render_edit(self):
        """The form, on one reading column: what the event is and when first, then the quieter
        details. Title, place and notes are typed in place; dates, times and choices are picked."""
        st = self._edit_state
        scroll, lay = self.page_edit
        self._clear(lay)
        save = link(_("save"), self.save_event, "primary", "Ctrl+S")
        host, col = column(640)
        col.addWidget(page_header([link(_("← cancel"), self._back or self.show_agenda)], [save]))
        title = QtWidgets.QLineEdit(st["summary"]); title.setObjectName("titleedit"); title.setPlaceholderText(_("title"))
        title.textChanged.connect(lambda v: st.__setitem__("summary", v)); title.returnPressed.connect(self.save_event)
        col.addWidget(title); self.edit_title = title
        col.addSpacing(10)
        day = st["start"].strftime("%A %-d %B %Y").lower()
        col.addWidget(row(day, _("day"), role="tile", click=lambda: self._pick_date("start")))
        if st["all_day"]:
            col.addWidget(row(_("all day"), None, role="tile"))
        else:
            col.addWidget(row(f"{fmt_time(st['start'])} – {fmt_time(st['end'])}", _("time"), role="tile", click=self._pick_times))
        other_day = st["end"].date() != st["start"].date()
        links = QtWidgets.QHBoxLayout(); links.setSpacing(26); links.setContentsMargins(0, 2, 0, 4)
        links.addWidget(link(_("at set times") if st["all_day"] else _("all day"), lambda: self._set("all_day", not st["all_day"]), "dim"))
        if not other_day:
            links.addWidget(link(_("ends another day"), lambda: self._pick_date("end"), "dim"))
        links.addStretch(1); col.addLayout(links)
        if other_day:
            col.addWidget(row(st["end"].strftime("%A %-d %B %Y").lower(), _("ends"), role="tile", click=lambda: self._pick_date("end")))
        col.addWidget(rule_line(14, 6))
        cal_name = next((n for n, u, _ in self.calendars if u == st["cal"]), "…")
        col.addWidget(dotted_row(ce.color_of(st["cal"]), row(cal_name, _("calendar"), click=self._pick_calendar if not st["href"] else None)))
        col.addWidget(row(reminder_label(st["reminder"]), _("reminder"), click=self._pick_reminder))
        if st.get("scope") == "this":
            col.addWidget(row(_("part of a series"), _("repeat")))
        else:
            col.addWidget(row(dict(REPEATS).get(st["rrule"], _("repeats (custom rule)")), _("repeat"), click=self._pick_repeat))
        col.addWidget(rule_line(6, 10))
        place = QtWidgets.QLineEdit(st["location"]); place.setObjectName("field"); place.setPlaceholderText(_("location"))
        place.textChanged.connect(lambda v: st.__setitem__("location", v)); col.addWidget(place)
        col.addSpacing(8)
        notes = QtWidgets.QPlainTextEdit(st["description"]); notes.setObjectName("field"); notes.setPlaceholderText(_("description"))
        notes.setFixedHeight(150); notes.textChanged.connect(lambda: st.__setitem__("description", notes.toPlainText())); col.addWidget(notes)
        bottom = QtWidgets.QHBoxLayout(); bottom.setContentsMargins(0, 22, 0, 0); bottom.setSpacing(26)
        bottom.addWidget(link(_("cancel"), self._back or self.show_agenda)); bottom.addStretch(1); bottom.addWidget(link(_("save"), self.save_event, "primary"))
        col.addLayout(bottom)
        lay.insertWidget(0, host)
        if not st["summary"]:
            QtCore.QTimer.singleShot(0, title.setFocus)

    def _pick_times(self):
        """Start, then end: two prompts in a row, each opening on its value selected."""
        if self._pick_time("start", redraw=False):
            self._pick_time("end", redraw=False)
        self.render_edit()

    def _set(self, key, value):
        self._edit_state[key] = value; self.render_edit()

    def _prompt(self, key, title, multiline=False):
        dlg = TextPrompt(title, self._edit_state[key], multiline, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._set(key, dlg.value().strip())

    def _pick_date(self, key):
        fg, bg = ("#ffffff", "#000000") if self.dark else ("#000000", "#ffffff")
        dlg = DatePick(self._edit_state[key].date(), fg, bg, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            st = self._edit_state; old = st[key]; new = datetime.combine(dlg.value, old.time(), LOCAL)
            if key == "start":
                st["end"] = st["end"] + (new - old)
            st[key] = new; self.render_edit()

    def _pick_time(self, key, redraw=True):
        dlg = TextPrompt(_("start time") if key == "start" else _("end time"), fmt_time(self._edit_state[key]), False, self, select_all=True, time_mask=True)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return False
        parsed = TimeMask.parse(dlg.value())
        if parsed is None:
            return False
        h, mi = parsed
        st = self._edit_state; old = st[key]; new = old.replace(hour=h, minute=mi)
        if key == "start":
            st["end"] = st["end"] + (new - old)
        st[key] = new
        if redraw: self.render_edit()
        return True

    def _menu_pick(self, options):
        m = QtWidgets.QMenu(self); chosen = []
        for label, value in options:
            m.addAction(label, lambda v=value: chosen.append(v))
        m.exec_(QtGui.QCursor.pos())
        return chosen[0] if chosen else None

    def _pick_calendar(self):
        v = self._menu_pick([(n, u) for n, u, w in self.calendars if w])
        if v is not None: self._set("cal", v)

    def _pick_reminder(self):
        v = self._menu_pick([(reminder_label(m), ("none" if m is None else m)) for m in REMINDERS])
        if v is not None: self._set("reminder", None if v == "none" else v)

    def _pick_repeat(self):
        v = self._menu_pick([(label, rule) for rule, label in REPEATS])
        if v is not None: self._set("rrule", v)

    def save_event(self):
        st = self._edit_state
        if not st["summary"].strip():
            self.status.setText(_("title")); getattr(self, "edit_title", None) and self.edit_title.setFocus(); return
        st["summary"] = st["summary"].strip()
        if st["all_day"]:
            start, end = st["start"].date(), st["end"].date()
            if end < start: self.status.setText(_("the end is before the start")); return
        else:
            start, end = st["start"], st["end"]
            if end <= start: self.status.setText(_("the end is before the start")); return
        keep = []
        if st["href"] and st.get("gevent") is None:
            src = next((o.event for o in self.occs if o.event.href == st["href"]), None)
            if src:
                keep = [l for l in src.lines if l.split(":", 1)[0].split(";", 1)[0].upper() in ("EXDATE", "CREATED", "SEQUENCE", "CLASS", "STATUS", "TRANSP", "CATEGORIES")]
        kw = dict(summary=st["summary"], start=start, end=end, all_day=st["all_day"], location=st["location"], description=st["description"], rrule=st["rrule"], reminder=st["reminder"], keep_lines=keep)
        self.status.setText(_("saving…"))
        if st.get("gevent") is not None:
            google = self.google_client()
            self.run(lambda: google.update(st["gevent"], **kw), lambda _: (self.show_agenda(), self.sync()), self.write_failed); return
        if not st["href"] and st["cal"].startswith(gc.PREFIX):
            google = self.google_client()
            self.run(lambda: google.create(st["cal"], **kw), lambda _: (self.show_agenda(), self.sync()), self.write_failed); return
        if st["href"]:
            fn = lambda: self.client.put(st["href"], ce.build_ics(st["uid"], **kw), etag=st["etag"])
        else:
            fn = lambda: self.client.create(st["cal"], **kw)
        self.run(fn, lambda _: (self.show_agenda(), self.sync()))


def _icon():
    """The window icon: beside the script, or inside the Windows and macOS build."""
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for name in (APP + ".png", os.path.join("packaging", APP + ".png")):
        path = os.path.join(here, name)
        if os.path.exists(path):
            return QtGui.QIcon(path)
    return QtGui.QIcon()


def main():
    credentials_cli(sys.argv)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("reader's calendar")
    app.setDesktopFileName(APP)
    app.setWindowIcon(_icon())
    w = Main(); w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
