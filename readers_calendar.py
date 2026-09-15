#!/usr/bin/env python3
"""Reader's Calendar — a black-and-white, text-only desktop calendar on CalDAV
(Infomaniak, Nextcloud, Radicale…). The landscape design of the Android app: month grid and
navigation on the left, agenda / week grid / event page on the right. PyQt5 + requests +
python-dateutil, one file. MIT licence."""

import calendar
import json
import os
import sys
from datetime import date, datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

# the module next to this file first; the installed copy only as a fallback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/usr/lib/readers-calendar")
import caldav_events as ce  # noqa: E402
import google_calendar as gc  # noqa: E402

APP = "readers-calendar"
VERSION = "1.8.0"
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), APP)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SYNC_MINUTES = 5
LOCAL = ce.LOCAL


# ------------------------------------------------------------------------------------------
# Six languages, the English text as the key (the launcher's languages: en, fr, de, es, pt, ru)
# ------------------------------------------------------------------------------------------

_TR = {
 "fr": {"Google account": "compte Google", "client ID": "ID client", "client secret": "secret client", "connect the Google account": "connecter le compte Google", "forget the Google account": "oublier le compte Google", "waiting for the browser…": "en attente du navigateur…", "Google account connected": "compte Google connecté", "Google: %1": "Google : %1", "Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself.": "Google Agenda, en lecture seule, avec votre propre client OAuth : console.cloud.google.com › nouveau projet › API et services › activer\nl'API Google Calendar › écran de consentement OAuth (externe, en test, vous-même comme testeur) › Identifiants › ID client OAuth,\ntype Application de bureau. Copiez l'ID et le secret ici, puis connectez : le navigateur s'ouvre sur Google et revient tout seul.", "workdays": "jours ouvrés", "opens on": "s'ouvre sur", "today · ": "aujourd'hui · ", "tomorrow · ": "demain · ", "all day": "toute la journée", "cancel": "annuler", "ok": "ok", "date": "date", "does not repeat": "ne se répète pas", "every day": "chaque jour", "every week": "chaque semaine", "every month": "chaque mois", "every year": "chaque année",
        "no reminder": "pas de rappel", "at the time of the event": "à l'heure de l'événement", "%1 minutes before": "%1 minutes avant", "%1 hours before": "%1 heures avant", "%1 days before": "%1 jours avant",
        "agenda": "agenda", "day": "jour", "week": "semaine", "+ new event": "+ nouvel événement", "server": "serveur", "username": "identifiant", "app password": "mot de passe d'application", "feeds": "flux", "connect": "se connecter",
        "not connected — Ctrl+, to set up": "non connecté — Ctrl+, pour configurer", "connecting…": "connexion…", "  (read only)": "  (lecture seule)", "syncing…": "synchronisation…", "synced %1": "synchronisé %1", "nothing planned": "rien de prévu", "show more days": "afficher plus de jours", "today": "aujourd'hui",
        "repeats": "se répète", "repeats (custom rule)": "se répète (règle personnalisée)", " · read-only": " · lecture seule", "← back": "← retour", "edit": "modifier", "delete": "supprimer", " the whole series": " toute la série", "move the whole series": "déplacer toute la série", "deleting…": "suppression…", "this event comes from a read-only feed": "cet événement vient d'un flux en lecture seule", "no writable calendar": "aucun agenda modifiable",
        "title": "titre", "all day: ": "toute la journée : ", "on": "oui", "off": "non", "starts": "début", "start time": "heure de début", "ends": "fin", "end time": "heure de fin", "calendar": "agenda", "reminder": "rappel", "repeat": "répétition", "location": "lieu", "description": "description",
        "save": "enregistrer", "the end is before the start": "la fin est avant le début", "saving…": "enregistrement…", "start time (hh:mm)": "heure de début (hh:mm)", "end time (hh:mm)": "heure de fin (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Agendas CalDAV. Infomaniak : https://sync.infomaniak.com, identifiant du type AB12345,\nun mot de passe d'application si la double authentification est active. Nextcloud, Radicale… fonctionnent aussi.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Flux en lecture seule, un par ligne sous la forme  nom | adresse  (.ics ou webcal). Google Agenda : paramètres de\nl'agenda › Intégrer l'agenda › Adresse secrète au format iCal. Ils s'affichent à côté des agendas CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · développé avec Claude Code"},
 "de": {"Google account": "Google-Konto", "client ID": "Client-ID", "client secret": "Client-Geheimnis", "connect the Google account": "Google-Konto verbinden", "forget the Google account": "Google-Konto vergessen", "waiting for the browser…": "warte auf den Browser…", "Google account connected": "Google-Konto verbunden", "Google: %1": "Google: %1", "Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself.": "Google Kalender, nur lesen, mit eigenem OAuth-Client: console.cloud.google.com › neues Projekt › APIs & Dienste › Google Calendar API\naktivieren › OAuth-Zustimmungsbildschirm (extern, in Tests, Sie selbst als Tester) › Anmeldedaten › OAuth-Client-ID, Typ Desktop-App.\nID und Geheimnis hier eintragen, dann verbinden: der Browser öffnet Google und kommt von selbst zurück.", "workdays": "Werktage", "opens on": "öffnet mit", "today · ": "heute · ", "tomorrow · ": "morgen · ", "all day": "ganztägig", "cancel": "abbrechen", "ok": "ok", "date": "Datum", "does not repeat": "einmalig", "every day": "täglich", "every week": "wöchentlich", "every month": "monatlich", "every year": "jährlich",
        "no reminder": "keine Erinnerung", "at the time of the event": "zum Zeitpunkt des Termins", "%1 minutes before": "%1 Minuten vorher", "%1 hours before": "%1 Stunden vorher", "%1 days before": "%1 Tage vorher",
        "agenda": "Agenda", "day": "Tag", "week": "Woche", "+ new event": "+ neuer Termin", "server": "Server", "username": "Benutzername", "app password": "App-Passwort", "feeds": "Feeds", "connect": "verbinden",
        "not connected — Ctrl+, to set up": "nicht verbunden — Strg+, zum Einrichten", "connecting…": "verbinde…", "  (read only)": "  (nur lesen)", "syncing…": "synchronisiere…", "synced %1": "synchronisiert %1", "nothing planned": "nichts geplant", "show more days": "mehr Tage zeigen", "today": "heute",
        "repeats": "wiederholt sich", "repeats (custom rule)": "wiederholt sich (eigene Regel)", " · read-only": " · nur lesen", "← back": "← zurück", "edit": "bearbeiten", "delete": "löschen", " the whole series": " die ganze Serie", "move the whole series": "die ganze Serie verschieben", "deleting…": "lösche…", "this event comes from a read-only feed": "dieser Termin stammt aus einem Nur-Lese-Feed", "no writable calendar": "kein beschreibbarer Kalender",
        "title": "Titel", "all day: ": "ganztägig: ", "on": "an", "off": "aus", "starts": "beginnt", "start time": "Beginn", "ends": "endet", "end time": "Ende", "calendar": "Kalender", "reminder": "Erinnerung", "repeat": "Wiederholung", "location": "Ort", "description": "Beschreibung",
        "save": "speichern", "the end is before the start": "das Ende liegt vor dem Beginn", "saving…": "speichere…", "start time (hh:mm)": "Beginn (hh:mm)", "end time (hh:mm)": "Ende (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "CalDAV-Kalender. Infomaniak: https://sync.infomaniak.com, Benutzername wie AB12345,\nein App-Passwort bei Zwei-Faktor-Anmeldung. Nextcloud, Radicale… gehen ebenso.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Nur-Lese-Feeds, je Zeile  Name | Adresse  (.ics oder webcal). Google Kalender: Einstellungen des\nKalenders › Kalender integrieren › Privatadresse im iCal-Format. Sie erscheinen neben den CalDAV-Kalendern.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · entwickelt mit Claude Code"},
 "es": {"Google account": "cuenta de Google", "client ID": "ID de cliente", "client secret": "secreto de cliente", "connect the Google account": "conectar la cuenta de Google", "forget the Google account": "olvidar la cuenta de Google", "waiting for the browser…": "esperando al navegador…", "Google account connected": "cuenta de Google conectada", "Google: %1": "Google: %1", "Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself.": "Google Calendar, solo lectura, con su propio cliente OAuth: console.cloud.google.com › proyecto nuevo › APIs y servicios › activar la\nAPI de Google Calendar › pantalla de consentimiento OAuth (externa, en pruebas, usted como probador) › Credenciales › ID de cliente OAuth,\ntipo Aplicación de escritorio. Copie el ID y el secreto aquí y conecte: el navegador abre Google y vuelve solo.", "workdays": "días laborables", "opens on": "se abre en", "today · ": "hoy · ", "tomorrow · ": "mañana · ", "all day": "todo el día", "cancel": "cancelar", "ok": "ok", "date": "fecha", "does not repeat": "no se repite", "every day": "cada día", "every week": "cada semana", "every month": "cada mes", "every year": "cada año",
        "no reminder": "sin recordatorio", "at the time of the event": "a la hora del evento", "%1 minutes before": "%1 minutos antes", "%1 hours before": "%1 horas antes", "%1 days before": "%1 días antes",
        "agenda": "agenda", "day": "día", "week": "semana", "+ new event": "+ nuevo evento", "server": "servidor", "username": "usuario", "app password": "contraseña de aplicación", "feeds": "feeds", "connect": "conectar",
        "not connected — Ctrl+, to set up": "sin conexión — Ctrl+, para configurar", "connecting…": "conectando…", "  (read only)": "  (solo lectura)", "syncing…": "sincronizando…", "synced %1": "sincronizado %1", "nothing planned": "nada previsto", "show more days": "mostrar más días", "today": "hoy",
        "repeats": "se repite", "repeats (custom rule)": "se repite (regla personalizada)", " · read-only": " · solo lectura", "← back": "← volver", "edit": "editar", "delete": "eliminar", " the whole series": " toda la serie", "move the whole series": "mover toda la serie", "deleting…": "eliminando…", "this event comes from a read-only feed": "este evento viene de un feed de solo lectura", "no writable calendar": "ningún calendario editable",
        "title": "título", "all day: ": "todo el día: ", "on": "sí", "off": "no", "starts": "empieza", "start time": "hora de inicio", "ends": "termina", "end time": "hora de fin", "calendar": "calendario", "reminder": "recordatorio", "repeat": "repetición", "location": "lugar", "description": "descripción",
        "save": "guardar", "the end is before the start": "el fin es anterior al inicio", "saving…": "guardando…", "start time (hh:mm)": "hora de inicio (hh:mm)", "end time (hh:mm)": "hora de fin (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Calendarios CalDAV. Infomaniak: https://sync.infomaniak.com, usuario tipo AB12345,\nuna contraseña de aplicación si tienes la verificación en dos pasos. Nextcloud, Radicale… también funcionan.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Feeds de solo lectura, uno por línea como  nombre | dirección  (.ics o webcal). Google Calendar: ajustes del\ncalendario › Integrar el calendario › Dirección secreta en formato iCal. Se muestran junto a los calendarios CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · desarrollado con Claude Code"},
 "pt": {"Google account": "conta Google", "client ID": "ID de cliente", "client secret": "segredo de cliente", "connect the Google account": "ligar a conta Google", "forget the Google account": "esquecer a conta Google", "waiting for the browser…": "à espera do navegador…", "Google account connected": "conta Google ligada", "Google: %1": "Google: %1", "Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself.": "Google Calendar, só leitura, com o seu próprio cliente OAuth: console.cloud.google.com › novo projeto › APIs e serviços › ativar a\nAPI Google Calendar › ecrã de consentimento OAuth (externo, em teste, você como testador) › Credenciais › ID de cliente OAuth,\ntipo Aplicação de computador. Copie o ID e o segredo aqui e ligue: o navegador abre o Google e volta sozinho.", "workdays": "dias úteis", "opens on": "abre em", "today · ": "hoje · ", "tomorrow · ": "amanhã · ", "all day": "todo o dia", "cancel": "cancelar", "ok": "ok", "date": "data", "does not repeat": "não se repete", "every day": "todos os dias", "every week": "todas as semanas", "every month": "todos os meses", "every year": "todos os anos",
        "no reminder": "sem lembrete", "at the time of the event": "à hora do evento", "%1 minutes before": "%1 minutos antes", "%1 hours before": "%1 horas antes", "%1 days before": "%1 dias antes",
        "agenda": "agenda", "day": "dia", "week": "semana", "+ new event": "+ novo evento", "server": "servidor", "username": "utilizador", "app password": "palavra-passe de aplicação", "feeds": "feeds", "connect": "ligar",
        "not connected — Ctrl+, to set up": "sem ligação — Ctrl+, para configurar", "connecting…": "a ligar…", "  (read only)": "  (só leitura)", "syncing…": "a sincronizar…", "synced %1": "sincronizado %1", "nothing planned": "nada previsto", "show more days": "mostrar mais dias", "today": "hoje",
        "repeats": "repete-se", "repeats (custom rule)": "repete-se (regra personalizada)", " · read-only": " · só leitura", "← back": "← voltar", "edit": "editar", "delete": "apagar", " the whole series": " toda a série", "move the whole series": "mover toda a série", "deleting…": "a apagar…", "this event comes from a read-only feed": "este evento vem de um feed só de leitura", "no writable calendar": "nenhum calendário editável",
        "title": "título", "all day: ": "todo o dia: ", "on": "sim", "off": "não", "starts": "começa", "start time": "hora de início", "ends": "termina", "end time": "hora de fim", "calendar": "calendário", "reminder": "lembrete", "repeat": "repetição", "location": "local", "description": "descrição",
        "save": "guardar", "the end is before the start": "o fim é anterior ao início", "saving…": "a guardar…", "start time (hh:mm)": "hora de início (hh:mm)", "end time (hh:mm)": "hora de fim (hh:mm)",
        "CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.": "Calendários CalDAV. Infomaniak: https://sync.infomaniak.com, utilizador tipo AB12345,\numa palavra-passe de aplicação se tiver a verificação em dois passos. Nextcloud, Radicale… também funcionam.",
        "Read-only feeds, one per line as  name | address  (.ics or webcal). Google Calendar: the calendar's\nsettings › Integrate calendar › Secret address in iCal format. They show alongside the CalDAV calendars.": "Feeds só de leitura, um por linha como  nome | endereço  (.ics ou webcal). Google Calendar: definições do\ncalendário › Integrar o calendário › Endereço secreto em formato iCal. Aparecem ao lado dos calendários CalDAV.",
        "Pierre Gallaz · developed with Claude Code": "Pierre Gallaz · desenvolvido com Claude Code"},
 "ru": {"Google account": "аккаунт Google", "client ID": "ID клиента", "client secret": "секрет клиента", "connect the Google account": "подключить аккаунт Google", "forget the Google account": "забыть аккаунт Google", "waiting for the browser…": "ожидание браузера…", "Google account connected": "аккаунт Google подключён", "Google: %1": "Google: %1", "Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself.": "Google Календарь, только чтение, со своим OAuth-клиентом: console.cloud.google.com › новый проект › API и сервисы › включить\nGoogle Calendar API › экран согласия OAuth (внешний, в тестировании, вы как тестировщик) › Учётные данные › идентификатор клиента OAuth,\nтип «Компьютерное приложение». Вставьте ID и секрет сюда и подключите: браузер откроет Google и вернётся сам.", "workdays": "будни", "opens on": "открывается на", "today · ": "сегодня · ", "tomorrow · ": "завтра · ", "all day": "весь день", "cancel": "отмена", "ok": "ок", "date": "дата", "does not repeat": "не повторяется", "every day": "каждый день", "every week": "каждую неделю", "every month": "каждый месяц", "every year": "каждый год",
        "no reminder": "без напоминания", "at the time of the event": "в момент события", "%1 minutes before": "за %1 мин", "%1 hours before": "за %1 ч", "%1 days before": "за %1 дн",
        "agenda": "повестка", "day": "день", "week": "неделя", "+ new event": "+ новое событие", "server": "сервер", "username": "имя пользователя", "app password": "пароль приложения", "feeds": "ленты", "connect": "подключиться",
        "not connected — Ctrl+, to set up": "нет подключения — Ctrl+, для настройки", "connecting…": "подключение…", "  (read only)": "  (только чтение)", "syncing…": "синхронизация…", "synced %1": "синхронизировано %1", "nothing planned": "ничего не запланировано", "show more days": "показать больше дней", "today": "сегодня",
        "repeats": "повторяется", "repeats (custom rule)": "повторяется (своё правило)", " · read-only": " · только чтение", "← back": "← назад", "edit": "изменить", "delete": "удалить", " the whole series": " всю серию", "move the whole series": "перенести всю серию", "deleting…": "удаление…", "this event comes from a read-only feed": "это событие из ленты только для чтения", "no writable calendar": "нет календаря для записи",
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


def day_label(d, today):
    base = d.strftime("%A %-d %B").lower()
    if d == today:
        return _("today · ") + base
    if d == today + timedelta(days=1):
        return _("tomorrow · ") + base
    return base if d.year == today.year else base + f" {d.year}"


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
                    p.drawText(rect.adjusted(4, 0, -4, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, p.fontMetrics().elidedText(o.event.summary, QtCore.Qt.ElideRight, int(rect.width()) - 8))
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
        if frame:
            p.setPen(QtGui.QPen(self.bg, 1)); p.setBrush(QtCore.Qt.NoBrush); p.drawRect(rect.adjusted(1, 1, -1, -1))
        show_time = rect.height() >= fm_small.height() * 2 + 8
        inner = rect.adjusted(4, 2, -4, -(fm_small.height() + 3) if show_time else -2)
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

def row(text, secondary=None, size=None, dim_secondary=True, click=None, obj=None):
    w = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(w); lay.setContentsMargins(0, 6, 0, 6); lay.setSpacing(0)
    t = QtWidgets.QLabel(text); t.setWordWrap(True)
    if size:
        f = t.font(); f.setPointSize(size); t.setFont(f)
    if obj:
        t.setObjectName(obj)
    lay.addWidget(t)
    if secondary:
        s = QtWidgets.QLabel(secondary); s.setObjectName("dim"); s.setWordWrap(True); lay.addWidget(s)
    if click:
        w.setCursor(QtCore.Qt.PointingHandCursor); w.mousePressEvent = lambda e: click()
    return w


class TextPrompt(QtWidgets.QDialog):
    """A line (or a box) of text to type. With select_all the suggestion opens selected, so the
    first key replaces it instead of landing after its last character."""
    def __init__(self, title, initial="", multiline=False, parent=None, select_all=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QtWidgets.QVBoxLayout(self)
        lab = QtWidgets.QLabel(title); lab.setObjectName("dim"); lay.addWidget(lab)
        if multiline:
            self.edit = QtWidgets.QPlainTextEdit(initial)
        else:
            self.edit = QtWidgets.QLineEdit(initial); self.edit.returnPressed.connect(self.accept)
            if select_all:
                self.edit.selectAll()
        lay.addWidget(self.edit)
        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        c = QtWidgets.QPushButton(_("cancel")); c.clicked.connect(self.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton(_("ok")); ok.setDefault(True); ok.clicked.connect(self.accept); btns.addWidget(ok)
        lay.addLayout(btns)
        self.resize(520, 300 if multiline else 120)

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
        for l in (self.m_prev, self.m_next, self.m_title): l.setCursor(QtCore.Qt.PointingHandCursor)
        mnav.addWidget(self.m_prev); mnav.addWidget(self.m_title, 1, QtCore.Qt.AlignCenter); mnav.addWidget(self.m_next)
        ll.addLayout(mnav)
        self.grid = MonthGrid(); self.grid.setFixedHeight(250); ll.addWidget(self.grid)
        ll.addSpacing(10)
        self.nav_agenda = row(_("agenda"), click=lambda: self.show_agenda()); ll.addWidget(self.nav_agenda)
        self.nav_day = row(_("day"), click=lambda: self.show_day_grid(date.today())); ll.addWidget(self.nav_day)
        self.nav_week = row(_("week"), click=lambda: self.show_week(date.today())); ll.addWidget(self.nav_week)
        self.nav_workdays = row(_("workdays"), click=lambda: self.show_week(date.today(), workdays=True)); ll.addWidget(self.nav_workdays)
        self.nav_new = row(_("+ new event"), click=lambda: self.edit_event(None)); ll.addWidget(self.nav_new)
        ll.addStretch(1)
        self.cal_box = QtWidgets.QVBoxLayout(); ll.addLayout(self.cal_box)
        self.status = QtWidgets.QLabel(""); self.status.setObjectName("dim"); self.status.setWordWrap(True)
        bottom = QtWidgets.QHBoxLayout(); bottom.addWidget(self.status, 1)
        gear = QtWidgets.QLabel("⚙"); gear.setObjectName("dim"); gear.setCursor(QtCore.Qt.PointingHandCursor); gear.mousePressEvent = lambda e: self.setup(); bottom.addWidget(gear, 0)
        ll.addLayout(bottom)
        outer.addWidget(left)
        sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedWidth(1); outer.addWidget(sep)

        # ---- right: stacked pages
        self.pages = QtWidgets.QStackedWidget(); outer.addWidget(self.pages, 1)
        self.page_agenda = self._page_scroll(); self.pages.addWidget(self.page_agenda[0])
        self.page_week = QtWidgets.QWidget(); wl = QtWidgets.QVBoxLayout(self.page_week); wl.setContentsMargins(24, 18, 24, 12)
        wnav = QtWidgets.QHBoxLayout()
        self.w_prev = QtWidgets.QLabel("‹"); self.w_next = QtWidgets.QLabel("›"); self.w_title = QtWidgets.QLabel(); self.w_title.setObjectName("dim"); self.w_today = QtWidgets.QLabel(_("today"))
        for l in (self.w_prev, self.w_next, self.w_today): l.setCursor(QtCore.Qt.PointingHandCursor)
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

        self.m_prev.mousePressEvent = lambda e: self.move_month(-1)
        self.m_next.mousePressEvent = lambda e: self.move_month(1)
        self.m_title.mousePressEvent = lambda e: self.go_today()
        self.grid.day_clicked.connect(self.show_day)
        self.w_prev.mousePressEvent = lambda e: self.step_grid(-1)
        self.w_next.mousePressEvent = lambda e: self.step_grid(1)
        self.w_today.mousePressEvent = lambda e: (self.show_week(date.today(), workdays=self.week.workdays) if self.week.ndays > 1 else self.show_day_grid(date.today()))

        for seq, fn in (("Ctrl+T", self.toggle_theme), ("F5", self.sync), ("Ctrl+R", self.sync), ("Ctrl+N", lambda: self.edit_event(None)),
                        ("Ctrl+=", lambda: self.zoom(1)), ("Ctrl++", lambda: self.zoom(1)), ("Ctrl+-", lambda: self.zoom(-1)),
                        ("Ctrl+,", self.setup), ("Ctrl+Q", self.close), ("Escape", self.show_agenda), ("Ctrl+W", lambda: self.show_week(date.today())), ("Ctrl+Shift+W", lambda: self.show_week(date.today(), workdays=True)), ("Ctrl+D", self.go_today), ("Ctrl+J", lambda: self.show_day_grid(date.today()))):
            QtWidgets.QShortcut(QtGui.QKeySequence(seq), self, fn)
        self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.sync); self.timer.start(SYNC_MINUTES * 60 * 1000)
        self.apply_style()
        self.refresh_month_title()
        # the view the window opens on: the week unless configured otherwise
        {"week": lambda: self.show_week(date.today()), "workdays": lambda: self.show_week(date.today(), workdays=True), "day": lambda: self.show_day_grid(date.today()), "agenda": self.show_agenda}.get(self.cfg.get("default_view", "week"), lambda: self.show_week(date.today()))()
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
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    x = sub.takeAt(0)
                    if x.widget(): x.widget().deleteLater()

    # ---- look ------------------------------------------------------------------------

    def apply_style(self):
        bg, fg = ("#000000", "#ffffff") if self.dark else ("#ffffff", "#000000")
        dim = "rgba(255,255,255,0.55)" if self.dark else "rgba(0,0,0,0.55)"
        rule = "rgba(255,255,255,0.25)" if self.dark else "rgba(0,0,0,0.25)"
        s = self.font_size
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {bg}; color: {fg}; font-size: {s}pt; font-weight: 300; }}
            QLabel#dim {{ color: {dim}; }}
            QLabel#big {{ font-size: {s + 9}pt; }}
            QFrame#sep {{ background: {rule}; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background: {bg}; }}
            QScrollBar:vertical {{ background: {bg}; width: 6px; }} QScrollBar::handle:vertical {{ background: {rule}; min-height: 24px; }} QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QMenu {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }} QMenu::item:selected {{ background: {fg}; color: {bg}; }}
            QLineEdit, QPlainTextEdit, QComboBox {{ background: {bg}; color: {fg}; border: 1px solid {rule}; padding: 6px; }} QComboBox QAbstractItemView {{ background: {bg}; color: {fg}; selection-background-color: {fg}; selection-color: {bg}; }}
            QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {fg}; padding: 6px 18px; }} QPushButton:default {{ background: {fg}; color: {bg}; }}
            QDialog {{ background: {bg}; }} QToolTip {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }}
        """)
        self.grid.set_colors(fg, bg); self.week.set_colors(fg, bg); self.week_head.set_colors(fg, bg)
        f = QtGui.QFont(); f.setPointSize(s); f.setWeight(QtGui.QFont.Light); self.grid.setFont(f); self.week.setFont(f); self.week_head.setFont(f)
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
        g_hint = QtWidgets.QLabel(_("Google Calendar, read-only, with your own OAuth client: console.cloud.google.com › new project › APIs & Services › enable the\nGoogle Calendar API › OAuth consent screen (external, in testing, yourself as test user) › Credentials › OAuth client ID,\ntype Desktop app. Copy the ID and the secret here, then connect: the browser opens on Google and comes back by itself."))
        g_hint.setObjectName("dim"); form.addRow(g_hint)
        g = self.cfg.get("google", {})
        g_id = QtWidgets.QLineEdit(g.get("client_id", "")); g_secret = QtWidgets.QLineEdit(g.get("client_secret", "")); g_secret.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow(_("client ID"), g_id); form.addRow(_("client secret"), g_secret)
        g_row = QtWidgets.QHBoxLayout(); g_state = QtWidgets.QLabel(_("Google account connected") if g.get("tokens") else ""); g_state.setObjectName("dim")
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
        view = QtWidgets.QComboBox()
        for key, label in (("week", _("week")), ("workdays", _("workdays")), ("day", _("day")), ("agenda", _("agenda"))):
            view.addItem(label, key)
        view.setCurrentIndex(max(0, view.findData(self.cfg.get("default_view", "week"))))
        form.addRow(_("opens on"), view)
        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        c = QtWidgets.QPushButton(_("cancel")); c.clicked.connect(dlg.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton(_("connect")); ok.setDefault(True); ok.clicked.connect(dlg.accept); btns.addWidget(ok)
        form.addRow(btns)
        credits = QtWidgets.QLabel(f"reader's calendar {VERSION} · " + _("Pierre Gallaz · developed with Claude Code")); credits.setObjectName("dim"); form.addRow(credits)
        dlg.resize(640, 440)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
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
        self.cfg.update({"url": url.text().strip(), "username": user.text().strip(), "password": pw.text(), "subscriptions": parsed, "default_view": view.currentData(), "google": gcfg}); save_config(self.cfg)
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
        for name, url, writable in self.calendars:
            lab = QtWidgets.QLabel(("" if url in hidden else "■ ") + name + ("" if writable else _("  (read only)")))
            lab.setObjectName("dim" if url in hidden else ""); lab.setCursor(QtCore.Qt.PointingHandCursor)
            lab.mousePressEvent = lambda e, u=url: self.toggle_calendar(u)
            self.cal_box.addWidget(lab)
        self.sync()

    def _clear_calbox(self):
        while self.cal_box.count():
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
        hidden = set(self.cfg.get("hidden_calendars", []))
        ws, we = self.window()
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
        self.run(fetch, self.got_events)

    def got_events(self, occs):
        if self.google_ready(): save_config(self.cfg)   # the access token may have been renewed
        self.occs = occs
        self.grid.marked = {o.date for o in occs}; self.grid.update()
        self.status.setText(_("synced %1", datetime.now().strftime("%H:%M")))
        self.render_current()

    # ---- pages -------------------------------------------------------------------------

    def render_current(self):
        idx = self.pages.currentIndex()
        if idx == 0: self.render_agenda()
        elif idx == 1: self.render_week()
        elif idx == 2 and getattr(self, "_event", None): self.show_event(self._event, refresh=True)

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
                h = QtWidgets.QLabel(day_label(d, today)); h.setObjectName("" if d == today else "dim")
                h.setContentsMargins(0, 14, 0, 0); h.setCursor(QtCore.Qt.PointingHandCursor); h.mousePressEvent = lambda e, dd=d: self.show_day_grid(dd)
                lay.insertWidget(i, h); i += 1
            sec = o.when() + (" · " + o.event.location if o.event.location else "")
            lay.insertWidget(i, row(o.event.summary, sec, size=self.font_size + 4, click=lambda oo=o: self.show_event(oo))); i += 1
        more = row(_("show more days"), obj="dim", click=self.more_days); lay.insertWidget(i, more)

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

    def step_grid(self, delta):
        n = self.week.ndays
        if n > 1: self.show_week(self.week.start + timedelta(days=n * delta), workdays=self.week.workdays)
        else: self.show_day_grid(self.week.start + timedelta(days=delta))

    def _open_grid(self):
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
            self.status.setText(_("this event comes from a read-only feed")); self.render_week(); return
        if ev.rrule:
            m = QtWidgets.QMenu(self)
            m.addAction(_("move the whole series"), lambda: self._do_move(o, days, minutes))
            if m.exec_(QtGui.QCursor.pos()) is None:
                self.render_week()   # no choice: the block goes back
            return
        self._do_move(o, days, minutes)

    def _do_move(self, o, days, minutes):
        ev = o.event; delta = timedelta(days=days, minutes=0 if ev.all_day else minutes)
        start = ev.start + delta
        end = (ev.end - timedelta(days=1) if ev.all_day else ev.end) + delta
        keep = [l for l in ev.lines if l.split(":", 1)[0].split(";", 1)[0].upper() in ("EXDATE", "CREATED", "SEQUENCE", "CLASS", "STATUS", "TRANSP", "CATEGORIES")]
        kw = dict(summary=ev.summary, start=start, end=end, all_day=ev.all_day, location=ev.location, description=ev.description, rrule=ev.rrule, reminder=ev.reminder, keep_lines=keep)
        self.status.setText(_("saving…"))
        self.run(lambda: self.client.put(ev.href, ce.build_ics(ev.uid, **kw), etag=ev.etag), lambda _: self.sync(), lambda err: (self.status.setText(str(err)), self.render_week()))

    def show_event(self, o, refresh=False):
        self._event = o
        scroll, lay = self.page_event
        self._clear(lay)
        ev = o.event
        two = QtWidgets.QHBoxLayout(); left = QtWidgets.QVBoxLayout(); right = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(ev.summary); title.setObjectName("big"); title.setWordWrap(True); left.addWidget(title)
        if o.start.date() == (o.end - timedelta(seconds=1)).date():
            when = o.start.strftime("%A %-d %B %Y").lower()
        else:
            when = o.start.strftime("%-d %b").lower() + " – " + (o.end - timedelta(seconds=1)).strftime("%-d %b %Y").lower()
        left.addSpacing(10); left.addWidget(QtWidgets.QLabel(when)); left.addWidget(QtWidgets.QLabel(o.when()))
        if ev.rrule:
            r = QtWidgets.QLabel(dict(REPEATS).get(ev.rrule, _("repeats"))); r.setObjectName("dim"); left.addWidget(r)
        if ev.reminder is not None:
            r = QtWidgets.QLabel(reminder_label(ev.reminder)); r.setObjectName("dim"); left.addWidget(r)
        # the calendar it belongs to: a quiet line of text, never a colour
        c = QtWidgets.QLabel(o.cal_name); c.setObjectName("dim"); c.setContentsMargins(0, 12, 0, 0); left.addWidget(c)
        left.addStretch(1)
        if ev.location:
            l = QtWidgets.QLabel(ev.location); l.setWordWrap(True); right.addWidget(l)
            sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1); right.addWidget(sep)
        if ev.description:
            d = QtWidgets.QLabel(ev.description); d.setWordWrap(True); right.addWidget(d)
        if not ev.location and not ev.description:
            d = QtWidgets.QLabel("—"); d.setObjectName("dim"); right.addWidget(d)
        right.addStretch(1)
        two.addLayout(left, 45); two.addSpacing(24); two.addLayout(right, 55)
        lay.insertLayout(0, two)
        actions = QtWidgets.QHBoxLayout(); actions.setSpacing(28); actions.setContentsMargins(0, 18, 0, 0)
        pairs = [(_("← back"), self.show_agenda)] + ([(_("edit"), lambda: self.edit_event(o)), (_("delete"), lambda: self.delete_event(o))] if ev.writable else [])
        if not ev.writable:
            c.setText(o.cal_name + _(" · read-only"))
        for text, fn in pairs:
            l = QtWidgets.QLabel(text); l.setCursor(QtCore.Qt.PointingHandCursor); l.mousePressEvent = lambda e, f=fn: f(); actions.addWidget(l)
        actions.addStretch(1)
        lay.insertLayout(1, actions)
        self.pages.setCurrentIndex(2)

    def delete_event(self, o):
        m = QtWidgets.QMenu(self)
        m.addAction(_("delete") + (_(" the whole series") if o.event.rrule else ""), lambda: self._do_delete(o))
        m.exec_(QtGui.QCursor.pos())

    def _do_delete(self, o):
        self.status.setText(_("deleting…"))
        self.run(lambda: self.client.delete(o.event.href), lambda _: (self.show_agenda(), self.sync()))

    # ---- edit --------------------------------------------------------------------------

    def edit_event(self, o):
        if o is not None and not o.event.writable:
            self.status.setText(_("this event comes from a read-only feed")); return
        writable = [(n, u) for n, u, w in self.calendars if w]
        if not writable:
            self.status.setText(_("no writable calendar")); return
        ev = o.event if o else None
        now = datetime.now(LOCAL).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        state = {
            "uid": ev.uid if ev else None, "href": ev.href if ev else None, "etag": ev.etag if ev else None,
            "summary": ev.summary if ev else "", "all_day": ev.all_day if ev else False,
            "start": (ev.start if isinstance(ev.start, datetime) else datetime.combine(ev.start, datetime.min.time(), LOCAL)) if ev else now,
            "end": (ev.end - (timedelta(days=1) if ev.all_day else timedelta(0)) if isinstance(ev.end, datetime) else datetime.combine(ev.end - timedelta(days=1), datetime.min.time(), LOCAL)) if ev else now + timedelta(hours=1),
            "location": ev.location if ev else "", "description": ev.description if ev else "",
            "reminder": ev.reminder if ev else self.cfg.get("default_reminder", 10), "rrule": ev.rrule if ev else "",
            "cal": getattr(ev, "cal_url", None) if ev else (self.cfg.get("default_calendar") or writable[0][1]),
        }
        if state["cal"] not in [u for _, u in writable]:
            state["cal"] = writable[0][1]
        self._edit_state = state
        self.render_edit()
        self.pages.setCurrentIndex(3)
        if not ev:
            QtCore.QTimer.singleShot(0, lambda: self._prompt("summary", _("title")))

    def render_edit(self):
        st = self._edit_state
        scroll, lay = self.page_edit
        self._clear(lay)
        i = 0
        def add(w):
            nonlocal i
            lay.insertWidget(i, w); i += 1
        add(row(st["summary"] or _("title"), size=self.font_size + 6, click=lambda: self._prompt("summary", _("title"))))
        two = QtWidgets.QHBoxLayout(); left = QtWidgets.QVBoxLayout(); right = QtWidgets.QVBoxLayout()
        left.addWidget(row(_("all day: ") + (_("on") if st["all_day"] else _("off")), click=lambda: self._set("all_day", not st["all_day"])))
        left.addWidget(row(st["start"].strftime("%A %-d %B %Y").lower(), _("starts"), click=lambda: self._pick_date("start")))
        if not st["all_day"]:
            left.addWidget(row(fmt_time(st["start"]), _("start time"), click=lambda: self._pick_time("start")))
        left.addWidget(row(st["end"].strftime("%A %-d %B %Y").lower(), _("ends"), click=lambda: self._pick_date("end")))
        if not st["all_day"]:
            left.addWidget(row(fmt_time(st["end"]), _("end time"), click=lambda: self._pick_time("end")))
        left.addStretch(1)
        cal_name = next((n for n, u, _ in self.calendars if u == st["cal"]), "…")
        right.addWidget(row(cal_name, _("calendar"), click=self._pick_calendar))
        right.addWidget(row(reminder_label(st["reminder"]), _("reminder"), click=self._pick_reminder))
        right.addWidget(row(dict(REPEATS).get(st["rrule"], _("repeats (custom rule)")), _("repeat"), click=self._pick_repeat))
        right.addWidget(row(st["location"] or _("location"), _("location") if st["location"] else None, click=lambda: self._prompt("location", _("location"))))
        right.addWidget(row((st["description"][:80] + "…") if len(st["description"]) > 80 else (st["description"] or _("description")), _("description") if st["description"] else None, click=lambda: self._prompt("description", _("description"), True)))
        right.addStretch(1)
        two.addLayout(left, 1); two.addSpacing(24); two.addLayout(right, 1)
        lay.insertLayout(i, two); i += 1
        actions = QtWidgets.QHBoxLayout(); actions.setSpacing(28); actions.setContentsMargins(0, 18, 0, 0)
        for text, fn in ((_("cancel"), self.show_agenda), (_("save"), self.save_event)):
            l = QtWidgets.QLabel(text); l.setCursor(QtCore.Qt.PointingHandCursor); l.mousePressEvent = lambda e, f=fn: f(); actions.addWidget(l)
        actions.addStretch(1)
        lay.insertLayout(i, actions)

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

    def _pick_time(self, key):
        dlg = TextPrompt(("start" if key == "start" else "end") + " time (hh:mm)", fmt_time(self._edit_state[key]), False, self, select_all=True)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        import re
        m = re.match(r"^\s*(\d{1,2})\s*[:hH.]?\s*(\d{2})?\s*$", dlg.value())
        if not m:
            return
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            return
        st = self._edit_state; old = st[key]; new = old.replace(hour=h, minute=mi)
        if key == "start":
            st["end"] = st["end"] + (new - old)
        st[key] = new; self.render_edit()

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
        if not st["summary"]:
            self._prompt("summary", _("title")); return
        if st["all_day"]:
            start, end = st["start"].date(), st["end"].date()
            if end < start: self.status.setText(_("the end is before the start")); return
        else:
            start, end = st["start"], st["end"]
            if end <= start: self.status.setText(_("the end is before the start")); return
        keep = []
        if st["href"]:
            src = next((o.event for o in self.occs if o.event.href == st["href"]), None)
            if src:
                keep = [l for l in src.lines if l.split(":", 1)[0].split(";", 1)[0].upper() in ("EXDATE", "CREATED", "SEQUENCE", "CLASS", "STATUS", "TRANSP", "CATEGORIES")]
        kw = dict(summary=st["summary"], start=start, end=end, all_day=st["all_day"], location=st["location"], description=st["description"], rrule=st["rrule"], reminder=st["reminder"], keep_lines=keep)
        self.status.setText(_("saving…"))
        if st["href"]:
            fn = lambda: self.client.put(st["href"], ce.build_ics(st["uid"], **kw), etag=st["etag"])
        else:
            fn = lambda: self.client.create(st["cal"], **kw)
        self.run(fn, lambda _: (self.show_agenda(), self.sync()))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("reader's calendar")
    app.setDesktopFileName(APP)
    w = Main(); w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
