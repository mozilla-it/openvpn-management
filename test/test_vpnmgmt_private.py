# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributors:
# Guillaume Destuynder <gdestuynder@mozilla.com>
# Greg Cox <gcox@mozilla.com>
#
"""
   This tests the comms with a simulated openvpn management socket
"""
import unittest
import os
import socket
import time
import threading
import socketserver
import test.context  # pylint: disable=unused-import
from openvpn_management import VPNmgmt


UNIX_SOCKET_FILENAME = '/tmp/good-test-path'  # nosec hardcoded_tmp_directory
INITIAL_CONNECT = b">INFO:OpenVPN Management Interface Version 1 -- type 'help' for more info"


class ServerConnects(socketserver.StreamRequestHandler):
    '''
        Simulate an openvpn management server socket which listens to you.
    '''
    def handle(self):
        self.request.sendall(INITIAL_CONNECT)
        time.sleep(0.2)
        self.data = self.request.recv(1024).strip()
        time.sleep(0.2)


class ServerDisappears(socketserver.StreamRequestHandler):
    '''
        Simulate an openvpn management server socket which closes the request
        as soon as you make it.
    '''
    def handle(self):
        self.request.sendall(INITIAL_CONNECT)
        time.sleep(0.2)
        self.request.close()


class ServerErrors(socketserver.StreamRequestHandler):
    '''
        Simulate an openvpn management server socket who listens to you
        but then returns an error instead of a good result.
    '''
    def handle(self):
        self.request.sendall(INITIAL_CONNECT)
        time.sleep(0.2)
        # They send something, we ignore.
        self.request.recv(1024)
        # We send an error back:
        self.request.sendall(b"ERROR: unknown command, enter 'help' for more options")
        time.sleep(0.2)


class ThreadedStreamServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    ''' Simple class name for the fake openvpn management server '''
    # No pass needed, per pylint


class TestVPNmgmtPrivate(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Preparing test rig """
        try:
            # unlink socket it's there.  If we succeeded, this completes...
            os.unlink(UNIX_SOCKET_FILENAME)
        except OSError:  # pragma: no cover
            # ... else, there was nothing there (likely) ...
            if os.path.exists(UNIX_SOCKET_FILENAME):
                # ... but if there is, we couldn't delete it, so complain.
                raise
        #self.server = FakeServer(UNIX_SOCKET_FILENAME)
        self.library = VPNmgmt(UNIX_SOCKET_FILENAME)
        #self.server_thread = None

    def tearDown(self):
        """ Cleaning test rig """
        self.library.disconnect()
        try:
            # unlink socket it's there.  If we succeeded, this completes...
            os.unlink(UNIX_SOCKET_FILENAME)
        except OSError:  # pragma: no cover
            # ... else, there was nothing there (likely) ...
            pass

    def test_02_goodsetup(self):
        """
            This invokes a client and verifies we can establish a connection.
        """
        server = ThreadedStreamServer(UNIX_SOCKET_FILENAME, ServerConnects)
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        self.library.connect()
        self.assertFalse(self.library.sock.gettimeout(),
                         'socket is not nonblocking')
        # There's not much to test at this point because the connect
        # function eats the greeting output.  Soooo.  *shrug*

    def test_03_disconnect(self):
        """
            This invokes a client and disconnects
        """
        server = ThreadedStreamServer(UNIX_SOCKET_FILENAME, ServerConnects)
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        self.library.connect()
        self.library.disconnect()
        # There's not much to test other than to know we didn't raise.

    def test_04_deadserver(self):
        """
            Test that a server that dies on us gets an error, as opposed to hanging forever.
        """
        server = ThreadedStreamServer(UNIX_SOCKET_FILENAME, ServerConnects)
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        # Shut down the server before the client connects:
        server.shutdown()
        with self.assertRaises(socket.timeout):
            self.library.connect()
        server.server_close()
        # IMPROVEME - toss in a timeout in case the hang fails?

    def test_05_disappearserver(self):
        """
            Test that a server that does not respond to commands eventually
            gets an error, as opposed to hanging forever.
        """
        server = ThreadedStreamServer(UNIX_SOCKET_FILENAME, ServerDisappears)
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        self.library.connect()
        # The handler aborts our request before we can ask for info.
        with self.assertRaises(socket.error):
            self.library.getusers()

    def test_10_error_getuser(self):
        """
            If a server tosses an error condition, getusers should tell
            us 'no users connected' as opposed to raising.
        """
        server = ThreadedStreamServer(UNIX_SOCKET_FILENAME, ServerErrors)
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        self.library.connect()
        users = self.library.getusers()
        self.assertEqual(users, {},
                         'A confused server did not return an empty user list')
