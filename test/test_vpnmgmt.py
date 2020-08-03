# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributors:
# Guillaume Destuynder <gdestuynder@mozilla.com>
# Greg Cox <gcox@mozilla.com>
#
"""
   script testing script
"""
import unittest
import test.context  # pylint: disable=unused-import
import socket
from test.fakeserver import FakeServer
import six
from openvpn_management import VPNmgmt


UNIX_SOCKET_FILENAME = '/tmp/good-test-path'


class TestVPNmgmt(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Preparing test rig """
        self.server = FakeServer(UNIX_SOCKET_FILENAME)
        self.library = VPNmgmt(UNIX_SOCKET_FILENAME)
        self.server_thread = None

    def tearDown(self):
        """ Cleaning test rig """
        if self.server_thread is not None:
            self.server_thread.join()
        self.library.disconnect()

    def test_00_init(self):
        """ Verify that the self object was initialized """
        self.assertIsInstance(self.library, VPNmgmt,
                              'VPN client library is not a proper object')
        self.assertIsInstance(self.library.socket_path, six.string_types,
                              'VPN client socket_path is not a string')
        self.assertIsInstance(self.library.sock, socket.socket,
                              'VPN client sock is not a socket')

    def test_01_badsetup(self):
        """
            This invokes a non-recorded VPNmgmt client aimed at a
            socket path that isn't there.  This is an expected traceback.
        """
        testobj = VPNmgmt('/tmp/badpath')
        with self.assertRaises(socket.error):
            testobj.connect()
        testobj.sock.close()

    def test_02_goodsetup(self):
        """
            This invokes a client and verifies we can establish a connection.
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_just_connects)
        self.library.connect()
        self.assertFalse(self.library.sock.gettimeout(),
                         'socket is not nonblocking')
        # There's not much to test at this point because the connect
        # function eats the greeting output.  Soooo.  *shrug*
        # IMPROVEME -  test for a hung server that doesn't greet?

    def test_03_disconnect(self):
        """
            This invokes a client and disconnects
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_just_connects)
        self.library.connect()
        self.library.disconnect()
        # There's not much to test other than to know we didn't raise.

    def test_04_hungserver(self):
        """
            Test that a server that does not respond to commands eventually
            gets an error, as opposed to hanging forever.
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_just_connects)
        self.library.connect()
        with self.assertRaises(socket.error):
            self.library.getusers()
        # IMPROVEME - toss in a timeout in case the hang fails?

    def test_10_error_getuser(self):
        """
            If a server tosses an error condition, getusers should tell
            us 'no users connected' as opposed to raising.
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_hates_you)
        self.library.connect()
        users = self.library.getusers()
        self.assertEqual(users, {},
                         'A confused server did not return an empty user list')

    def test_11_getuser_1(self):
        """
            Verify that we see the correct number of users on status1
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_status, args=(1,))
        self.library.connect()
        users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 1 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 1 did not find all users')

    def test_12_getuser_2(self):
        """
            Verify that we see the correct number of users on status2
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_status, args=(2,))
        self.library.connect()
        users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 2 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 2 did not find all users')

    def test_13_getuser_3(self):
        """
            Verify that we see the correct number of users on status3
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_status, args=(3,))
        self.library.connect()
        users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 3 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 3 did not find all users')

    def test_21_kill_user_good(self):
        """
            Verify that a disconnection returns true
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_status_and_good_kill)
        self.library.connect()
        users = self.library.getusers()
        some_user = list(users.keys())[0]
        killtest = self.library.kill(some_user)
        self.assertIsInstance(killtest, tuple,
                              'kill must return a list')
        self.assertEqual(len(killtest), 2,
                         'kill must return a 2-element list')
        self.assertIsInstance(killtest[0], bool,
                              'kill return element 0 must be a bool')
        self.assertIsInstance(killtest[1], six.string_types,
                              'kill return element 1 must be a string')
        self.assertTrue(killtest[0],
                        'a good kill returns True')

    def test_22_kill_user_bad(self):
        """
            Verify that a failed disconnection returns false
        """
        self.server_thread = self.server.run_a_thread(
            target=self.server.server_status_and_bad_kill)
        self.library.connect()
        users = self.library.getusers()
        some_user = list(users.keys())[0]
        killtest = self.library.kill(some_user)
        self.assertIsInstance(killtest, tuple,
                              'kill must return a list')
        self.assertEqual(len(killtest), 2,
                         'kill must return a 2-element list')
        self.assertIsInstance(killtest[0], bool,
                              'kill return element 0 must be a bool')
        self.assertIsInstance(killtest[1], six.string_types,
                              'kill return element 1 must be a string')
        self.assertFalse(killtest[0],
                         'a bad kill returns False')
