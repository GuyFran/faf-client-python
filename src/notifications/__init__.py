"""
The Notification Systems reacts on events and displays a popup.
Each event_type has a NsHook to customize it.
"""
from typing import Any

from PyQt6 import QtCore
from PyQt6.QtGui import QPixmap

from src import util
from src.config import Settings
from src.connectivity.relay.GPGProtocol import LobbyInitMode
from src.fa import maps
from src.model.game import Game
from src.model.player import Player
from src.notifications.ns_dialog import NotificationDialog
from src.notifications.ns_settings import IngameNotification
from src.notifications.ns_settings import NsSettings
from src.notifications.ns_type import NsType
from src.protocol.lobbyprotocol import GameLaunchCommand


class Notifications:
    def __init__(self, client, gameset, playerset, me):
        self.client = client
        self.me = me

        self.settings = NsSettings
        self.dialog = NotificationDialog(self.client, self.settings)
        self.events: list[tuple[NsType, Any]] = []
        self.disabledStartup = True
        self.game_running = False
        self.unofficialClientDate = Settings.get(
            'notifications/unofficialClientDate', 0, type=int,
        )

        client.game_enter.connect(self.gameEnter)
        client.game_exit.connect(self.gameExit)
        client.game_full.connect(self._gamefull)
        client.game_launched.connect(self.game_launched)
        client.launching_ladder.connect(self.launching_ladder)
        client.unofficial_client.connect(self.unofficialClient)
        client.party_invite.connect(self.partyInvite)
        gameset.newLobby.connect(self._newLobby)
        playerset.added.connect(self._newPlayer)

        self.user = util.THEME.icon("client/user.png", pix=True)

        self.secondary_color = util.THEME.find_stylesheet_attribute(
            "Notifications::custom",
            "secondary-color",
        )
        self.mods_color = util.THEME.find_stylesheet_attribute(
            "Notifications::custom",
            "mods-color",
        )

    def _newPlayer(self, player: Player) -> None:
        if self.is_disabled(NsType.USER_ONLINE):
            return

        if self.me.player is not None and self.me.player == player:
            return

        notify_mode = self.settings.getCustomSetting(NsType.USER_ONLINE, 'mode')
        if (
            notify_mode != 'all'
            and not self.client.user_relations.model.is_friend(player.id)
        ):
            return

        self.events.append((NsType.USER_ONLINE, player.copy()))
        self.checkEvent()

    def _newLobby(self, game: Game) -> None:
        if self.is_disabled(NsType.NEW_GAME):
            return

        host = game.host_player
        notify_mode = self.settings.getCustomSetting(NsType.NEW_GAME, 'mode')
        if notify_mode != 'all':
            if host is None or not self.client.user_relations.model.is_friend(host.id, host.login):
                return

        self.events.append((NsType.NEW_GAME, game.copy()))
        self.checkEvent()

    def _gamefull(self) -> None:
        if self.is_disabled(NsType.GAME_FULL):
            return
        if (NsType.GAME_FULL, None) not in self.events:
            self.events.append((NsType.GAME_FULL, None))
        self.checkEvent()

    def launching_ladder(self, message: GameLaunchCommand) -> None:
        if self.is_disabled(NsType.LAUNCHING_LADDER):
            return
        event_data = (NsType.LAUNCHING_LADDER, message["name"])
        if event_data not in self.events:
            self.events.append(event_data)
        self.checkEvent()

    def game_launched(self, mode: LobbyInitMode) -> None:
        if mode is LobbyInitMode.AUTO:
            ev = NsType.LADDER_GAME_LAUNCHED
        else:
            ev = NsType.CUSTOM_GAME_LAUNCHED
        if self.is_disabled(ev):
            return
        if (ev, None) not in self.events:
            self.events.append((ev, None))
        self.checkEvent()

    def unofficialClient(self, msg):
        date = QtCore.QDate.currentDate().dayOfYear()
        if date == self.unofficialClientDate:  # Show once per day
            return

        self.unofficialClientDate = date
        Settings.set(
            'notifications/unofficialClientDate', self.unofficialClientDate,
        )
        self.events.append((NsType.UNOFFICIAL_CLIENT, msg))
        self.checkEvent()

    def partyInvite(self, message: dict) -> None:
        if self.is_disabled(NsType.PARTY_INVITE):
            return

        notify_mode = self.settings.getCustomSetting(NsType.PARTY_INVITE, 'mode')
        if (
            notify_mode != 'all'
            and not self.client.user_relations.model.is_friend(message["sender"])
        ):
            return
        self.events.append((NsType.PARTY_INVITE, message))
        self.checkEvent()

    def gameEnter(self):
        self.game_running = True

    def gameExit(self):
        self.game_running = False
        # kick the queue
        if self.settings.ingame_notifications == IngameNotification.QUEUE:
            self.checkEvent()

    def is_enabled(self, event_type: NsType) -> bool:
        if not self.settings.enabled:
            return False

        if event_type in self.settings.hooks:
            if self.disabledStartup or not self.settings.popupEnabled(event_type):
                return False

        if self.game_running:
            return (
                self.settings.ingame_notifications == IngameNotification.ENABLE
                or self.settings.ingame_allowed(event_type)
            )
        return True

    def is_disabled(self, event_type: NsType) -> bool:
        return not self.is_enabled(event_type)

    def setNotificationEnabled(self, enabled):
        self.settings.enabled = enabled
        self.settings.saveSettings()

    def showEvent(self):
        """
        Display the next event in the queue as popup

        Pops event from queue and checks if it is showable as per settings
        If event is showable, process event data and then feed it into
        notification dialog

        Returns True if showable event found, False otherwise
        """

        event = self.events.pop(0)

        eventType = event[0]
        data = event[1]
        pixmap = None
        text = str(data)
        if eventType == NsType.USER_ONLINE:
            player = data
            pixmap = self.user
            text = (
                f'{player.login}<br><font color="{self.secondary_color}" size="-2">is online</font>'
            )
        elif eventType == NsType.NEW_GAME:
            game = data
            preview = maps.preview(game.mapname, pixmap=True)
            if preview:
                assert isinstance(preview, QPixmap)
                pixmap = preview.scaled(80, 80)

            # TODO: outsource as function?
            mod = game.featured_mod
            mods = game.sim_mods

            modstr = ''
            if mod != 'faf' or mods:
                modstr = mod
                if mods:
                    if mod == 'faf':
                        modstr = ", ".join(list(mods.values()))
                    else:
                        modstr = mod + " & " + ", ".join(list(mods.values()))
                    if len(modstr) > 20:
                        modstr = modstr[:15] + "..."

            if modstr == '':
                modhtml = ''
            else:
                modhtml = (
                    '<br>'
                    f'<font size="-4"><font color="{self.mods_color}">mods</font> {modstr}</font>'
                )
            text = (
                '<html>{}<br><font color="silver" size="-2">on</font> '
                '{}{}</html>'.format(
                    game.title,
                    maps.getDisplayName(game.mapname),
                    modhtml,
                )
            )
        elif eventType == NsType.GAME_FULL:
            pixmap = self.user
            text = f'<br><font color="{self.secondary_color}" size="-2">Game is full.</font>'
        elif eventType in (NsType.CUSTOM_GAME_LAUNCHED, NsType.LADDER_GAME_LAUNCHED):
            text = "Game Launched"
        elif eventType == NsType.LAUNCHING_LADDER:
            text = f"<font size='-2'>Launching game:</font><br>{data}"
        elif eventType == NsType.UNOFFICIAL_CLIENT:
            pixmap = self.user
            text = f'<br><font color="{self.secondary_color}" size="-2">{data}</font>'
            self.dialog.newEvent(pixmap, text, 10, False, 200)
            return
        elif eventType == NsType.PARTY_INVITE:
            pixmap = self.user
            login = self.client.players[data["sender"]].login
            text = (
                f'{login}<br><font color="{self.secondary_color}" size="-2">invites you to'
                ' their party</font>'
            )
            self.dialog.newEvent(
                pixmap, text, 15,
                self.settings.soundEnabled(eventType),
                hide_accept_button=False,
                sender_id=data["sender"],
            )
            return

        self.dialog.newEvent(
            pixmap, text, self.settings.popup_lifetime,
            self.settings.soundEnabled(eventType),
        )

    def checkEvent(self) -> None:
        """
        Checks that we are in correct state to show next notification popup

        This means:
            * There need to be events pending
            * There must be no notification showing right now
              (i.e. notification dialog hidden)
            * Game isn't running, or ingame notifications are enabled

        """
        if len(self.events) == 0 or not self.dialog.isHidden():
            return

        event_type, _ = self.events[0]
        if self.is_enabled(event_type):
            self.showEvent()
