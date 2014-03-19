# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Configuration page for server preferences.
"""

import os
from gns3.qt import QtNetwork, QtGui
from ..ui.server_preferences_page_ui import Ui_ServerPreferencesPageWidget
from ..servers import Servers
from ..utils.progress_dialog import ProgressDialog
from ..utils.wait_for_connection_thread import WaitForConnectionThread


class ServerPreferencesPage(QtGui.QWidget, Ui_ServerPreferencesPageWidget):
    """
    QWidget configuration page for server preferences.
    """

    def __init__(self):

        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self._remote_servers = {}

        # connect the slots
        self.uiAddRemoteServerPushButton.clicked.connect(self._remoteServerAddSlot)
        self.uiDeleteRemoteServerPushButton.clicked.connect(self._remoteServerDeleteSlot)
        self.uiRemoteServersTreeWidget.itemClicked.connect(self._remoteServerClickedSlot)
        self.uiRemoteServersTreeWidget.itemSelectionChanged.connect(self._remoteServerChangedSlot)

        # load all available addresses
        self.uiLocalServerHostComboBox.addItems(["0.0.0.0", "::", QtNetwork.QHostInfo.localHostName()])
        for address in QtNetwork.QNetworkInterface.allAddresses():
            self.uiLocalServerHostComboBox.addItem(address.toString())

    def _remoteServerClickedSlot(self, item, column):
        """
        Loads a selected remote server from the tree widget.

        :param item: selected QTreeWidgetItem instance
        :param column: ignored
        """

        host = item.text(0)
        port = int(item.text(1))
        self.uiRemoteServerPortLineEdit.setText(host)
        self.uiRemoteServerPortSpinBox.setValue(port)

    def _remoteServerChangedSlot(self):
        """
        Enables the use of the delete button.
        """

        item = self.uiRemoteServersTreeWidget.currentItem()
        if item:
            self.uiDeleteRemoteServerPushButton.setEnabled(True)
        else:
            self.uiDeleteRemoteServerPushButton.setEnabled(False)

    def _remoteServerAddSlot(self):
        """
        Adds a new remote server.
        """

        host = self.uiRemoteServerPortLineEdit.text()
        port = self.uiRemoteServerPortSpinBox.value()

        # check if the remote server is already defined
        remote_server = "{host}:{port}".format(host=host, port=port)
        if remote_server in self._remote_servers:
            QtGui.QMessageBox.critical(self, "Remote server", "Remote server {} is already defined.".format(remote_server))
            return

        # add a new entry in the tree widget
        item = QtGui.QTreeWidgetItem(self.uiRemoteServersTreeWidget)
        item.setText(0, host)
        item.setText(1, str(port))

        # keep track of this remote server
        self._remote_servers[remote_server] = {"host": host,
                                               "port": port}

        self.uiRemoteServerPortSpinBox.setValue(self.uiRemoteServerPortSpinBox.value() + 1)
        self.uiRemoteServersTreeWidget.resizeColumnToContents(0)

    def _remoteServerDeleteSlot(self):
        """
        Deletes a remote server.
        """

        item = self.uiRemoteServersTreeWidget.currentItem()
        if item:
            host = item.text(0)
            port = int(item.text(1))
            remote_server = "{host}:{port}".format(host=host, port=port)
            del self._remote_servers[remote_server]
            self.uiRemoteServersTreeWidget.takeTopLevelItem(self.uiRemoteServersTreeWidget.indexOfTopLevelItem(item))

    def loadPreferences(self):
        """
        Loads the server preferences.
        """

        servers = Servers.instance()

        # load the local server preferences
        local_server = servers.localServer()
        index = self.uiLocalServerHostComboBox.findText(local_server.host)
        if index != -1:
            self.uiLocalServerHostComboBox.setCurrentIndex(index)
        self.uiLocalServerPortSpinBox.setValue(local_server.port)
        self.uiLocalServerPathLineEdit.setText(servers.localServerPath())

        # load remote server preferences
        self._remote_servers.clear()
        self.uiRemoteServersTreeWidget.clear()
        for server_id, server in servers.remoteServers().items():
            host = server.host
            port = server.port
            self._remote_servers[server_id] = {"host": host,
                                               "port": port}
            item = QtGui.QTreeWidgetItem(self.uiRemoteServersTreeWidget)
            item.setText(0, host)
            item.setText(1, str(port))

    def savePreferences(self):
        """
        Saves the server preferences.
        """

        servers = Servers.instance()

        # save the local server preferences
        local_server_host = self.uiLocalServerHostComboBox.currentText()
        local_server_port = self.uiLocalServerPortSpinBox.value()
        local_server_path = self.uiLocalServerPathLineEdit.text()

        if local_server_path:
            if not os.path.exists(local_server_path):
                QtGui.QMessageBox.critical(self, "Local server", "The path to {} doesn't exists.".format(local_server_path))
            else:
                server = servers.localServer()
                if servers.localServerPath() != local_server_path or server.host != local_server_host or server.port != local_server_port:
                    # local server settings have changed, let's stop the current local server.
                    if server.connected():
                        server.close_connection()
                    servers.stopLocalServer(wait=True)
                    #TODO: ASK if the user wants to start local server
                    if servers.startLocalServer(local_server_path, local_server_host, local_server_port):
                        thread = WaitForConnectionThread(local_server_host, local_server_port)
                        dialog = ProgressDialog(thread, "Local server", "Connecting...", "Cancel", busy=True, parent=self)
                        dialog.show()
                        dialog.exec_()
                    else:
                        QtGui.QMessageBox.critical(self, "Local server", "Could not start the local server process: {}".format(local_server_path))

            # save the remote server preferences
            servers.setLocalServer(local_server_path, local_server_host, local_server_port)
        servers.updateRemoteServers(self._remote_servers)
        servers.save()