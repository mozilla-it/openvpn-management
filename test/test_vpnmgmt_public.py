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
import socket
import textwrap
import test.context  # pylint: disable=unused-import
from unittest import mock
from openvpn_management import VPNmgmt


UNIX_SOCKET_FILENAME = '/tmp/good-test-path'


class TestVPNmgmtPublic(unittest.TestCase):
    """ Class of tests """

    def setUp(self):
        """ Preparing test rig """
        self.library = VPNmgmt(UNIX_SOCKET_FILENAME)

    def tearDown(self):
        """ Cleaning test rig """
        self.library.disconnect()

    def test_00_init(self):
        """ Verify that the self object was initialized """
        self.assertIsInstance(self.library, VPNmgmt,
                              'VPN client library is not a proper object')
        self.assertIsInstance(self.library.socket_path, str,
                              'VPN client socket_path is not a string')
        self.assertIsInstance(self.library.sock, socket.socket,
                              'VPN client sock is not a socket')

    def test_01_vbadsetup(self):
        """
            This invokes a nonsense init.
            This is an expected traceback.
        """
        with self.assertRaises(ValueError):
            VPNmgmt('not-a-path')

    def test_02_badsetup(self):
        """
            This invokes a non-recorded VPNmgmt client aimed at a
            socket path that isn't there.  This is an expected traceback.
        """
        testobj = VPNmgmt('/tmp/badpath')
        with self.assertRaises(socket.error):
            testobj.connect()
        testobj.sock.close()

    def test_10_status(self):
        """ Verify that status calls do the right thing """
        statusval = 'irrelevant'
        # What we get back is being mocked, so don't sweat it for this test.
        # This function is expected to be a passthrough
        with mock.patch.object(self.library, '_send', return_value=statusval) as mock_status:
            retval = self.library.status()
        mock_status.assert_called_once_with('status 2', 'END')
        self.assertEqual(retval, statusval)

    def test_11_getuser_1(self):
        """
            Verify that we see the correct number of users on status1
        """
        status_1 = textwrap.dedent('''\
            OpenVPN CLIENT LIST
            Updated,Tue Sep 25 22:39:46 2018
            Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
            person3@company.com,5.6.7.8:33874,16709424,3109968,Tue Sep 25 16:32:49 2018
            person1@company.com,9.10.11.12:40743,1144713,9980107,Tue Sep 25 16:36:48 2018
            person2@company.com,1.2.3.4:49195,2159230,15413475,Tue Sep 25 16:55:46 2018
            ROUTING TABLE
            Virtual Address,Common Name,Real Address,Last Ref
            10.48.238.4,person2@company.com,1.2.3.4:49195,Tue Sep 25 22:39:36 2018
            10.48.238.2,person3@company.com,5.6.7.8:33874,Tue Sep 25 22:39:43 2018
            10.48.238.3,person1@company.com,9.10.11.12:40743,Tue Sep 25 22:39:28 2018
            GLOBAL STATS
            Max bcast/mcast queue length,0
            END
            ''')
        with mock.patch.object(self.library, 'status', return_value=status_1):
            users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 1 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 1 did not find all users')

    def test_12_getuser_2(self):
        """
            Verify that we see the correct number of users on status2
        """
        status_2 = textwrap.dedent('''\
            TITLE,OpenVPN 2.4.6 x86_64-redhat-linux-gnu [Fedora EPEL patched] [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Apr 26 2018
            TIME,Tue Sep 25 22:45:07 2018,1537915507
            HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Virtual IPv6 Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID
            CLIENT_LIST,person3@company.com,5.6.7.8:33874,10.48.238.2,,16800558,3514403,Tue Sep 25 16:32:49 2018,1537893169,person3,15,1
            CLIENT_LIST,person1@company.com,9.10.11.12:40743,10.48.238.3,,1150910,9991285,Tue Sep 25 16:36:48 2018,1537893408,person1@company.com,16,0
            CLIENT_LIST,person2@company.com,1.2.3.4:49195,10.48.238.4,,2181525,15443089,Tue Sep 25 16:55:46 2018,1537894546,person2@company.com,17,2
            HEADER,ROUTING_TABLE,Virtual Address,Common Name,Real Address,Last Ref,Last Ref (time_t)
            ROUTING_TABLE,10.48.238.4,person2@company.com,1.2.3.4:49195,Tue Sep 25 22:45:04 2018,1537915504
            ROUTING_TABLE,10.48.238.2,person3@company.com,5.6.7.8:33874,Tue Sep 25 22:45:05 2018,1537915505
            ROUTING_TABLE,10.48.238.3,person1@company.com,9.10.11.12:40743,Tue Sep 25 22:45:04 2018,1537915504
            ROUTING_TABLE,10.48.238.7,UNDEF,13.14.15.16:8837,Tue Sep 25 22:45:04 2018,1537915504
            GLOBAL_STATS,Max bcast/mcast queue length,0
            END
            ''')
        with mock.patch.object(self.library, 'status', return_value=status_2):
            users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 2 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 2 did not find all users')

    def test_13_getuser_3(self):
        """
            Verify that we see the correct number of users on status3
        """
        # status 3 has tabs, beware if copying.
        status_3 = textwrap.dedent('''\
            TITLE	OpenVPN 2.4.6 x86_64-redhat-linux-gnu [Fedora EPEL patched] [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Apr 26 2018
            TIME	Tue Sep 25 22:45:58 2018	1537915558
            HEADER	CLIENT_LIST	Common Name	Real Address	Virtual Address	Virtual IPv6 Address	Bytes Received	Bytes Sent	Connected Since	Connected Since (time_t)	Username	Client ID	Peer ID
            CLIENT_LIST	person3@company.com	5.6.7.8:33874	10.48.238.2		16806094	3519759	Tue Sep 25 16:32:49 2018	1537893169	person3	15	1
            CLIENT_LIST	person1@company.com	9.10.11.12:4743	10.48.238.3		1151262	9999104	Tue Sep 25 16:36:48 2018	1537893408	person1@company.com	16	0
            CLIENT_LIST	person2@company.com	1.2.3.4:49195	10.48.238.4		2185224	15449627	Tue Sep 25 16:55:46 2018	1537894546	person2@company.com	17	2
            HEADER	ROUTING_TABLE	Virtual Address	Common Name	Real Address	Last Ref	Last Ref (time_t)
            ROUTING_TABLE	10.48.238.4	person2@company.com	1.2.3.4:49195	Tue Sep 25 22:45:51 2018	1537915551
            ROUTING_TABLE	10.48.238.2	person3@company.com	5.6.7.8:33874	Tue Sep 25 22:45:56 2018	1537915556
            ROUTING_TABLE	10.48.238.3	person1@company.com	9.10.11.12:40743	Tue Sep 25 22:45:57 2018	1537915557
            GLOBAL_STATS	Max bcast/mcast queue length	0
            END
            ''')
        with mock.patch.object(self.library, 'status', return_value=status_3):
            users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 3 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 3 did not find all users')

    def test_14_getuser_kidz(self):
        """
            Verify that we don't count a script kiddie who hasn't connected
        """
        status_kiddie = textwrap.dedent('''\
            TITLE,OpenVPN 2.4.6 x86_64-redhat-linux-gnu [Fedora EPEL patched] [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Apr 26 2018
            TIME,Tue Oct 16 17:44:29 2018,1539711869
            HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Virtual IPv6 Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID
            CLIENT_LIST,person1@company.org,1.3.5.7:61546,10.48.242.2,,929084,20285336,Tue Oct 16 15:32:00 2018,1539703920,person1@company.org,3646,0
            CLIENT_LIST,person2@company.org,2.4.6.8:42707,10.48.242.4,,2077224,1734473,Tue Oct 16 16:52:22 2018,1539708742,person2@company.org,3660,0
            CLIENT_LIST,UNDEF,44.55.66.77:64912,,,0,0,Tue Oct 16 17:44:05 2018,1539711845,UNDEF,3665,0
            CLIENT_LIST,person3@company.org,12.34.56.79:19567,10.48.242.5,,1484054,29953450,Tue Oct 16 16:44:06 2018,1539708246,person3@company.org,3656,0
            HEADER,ROUTING_TABLE,Virtual Address,Common Name,Real Address,Last Ref,Last Ref (time_t)
            ROUTING_TABLE,10.48.242.5,person3@company.org,12.34.56.79:19567,Tue Oct 16 17:44:19 2018,1539711859
            ROUTING_TABLE,10.48.242.4,person2@company.org,2.4.6.8:42707,Tue Oct 16 17:44:26 2018,1539711866
            ROUTING_TABLE,10.48.242.2,person1@company.org,1.3.5.7:61546,Tue Oct 16 17:44:25 2018,1539711865
            GLOBAL_STATS,Max bcast/mcast queue length,0
            END
            ''')
        with mock.patch.object(self.library, 'status', return_value=status_kiddie):
            users = self.library.getusers()
        self.assertIsInstance(users, dict,
                              'server version 2 did not return a user dict')
        self.assertEqual(len(users), 3,
                         'server version 2 did not find all users')

    def test_21_kill_good_noop(self):
        """
            Verify that a fake disconnection returns true
        """
        good_kill = "SUCCESS: common name 'person1@company.com' found, 1 client(s) killed"
        with mock.patch.object(self.library, '_send', return_value=good_kill) as mock_kill:
            killtest = self.library.kill('person1@company.com', commit=False)
        mock_kill.assert_called_once_with('version')
        self.assertIsInstance(killtest, tuple,
                              'kill must return a list')
        self.assertEqual(len(killtest), 2,
                         'kill must return a 2-element list')
        self.assertIsInstance(killtest[0], bool,
                              'kill return element 0 must be a bool')
        self.assertIsInstance(killtest[1], str,
                              'kill return element 1 must be a string')
        self.assertTrue(killtest[0],
                        'a good kill returns True')

    def test_22_kill_good_op(self):
        """
            Verify that a real disconnection returns true
        """
        good_kill = "SUCCESS: common name 'person1@company.com' found, 1 client(s) killed"
        with mock.patch.object(self.library, '_send', return_value=good_kill) as mock_kill:
            killtest = self.library.kill('person1@company.com', commit=True)
        mock_kill.assert_called_once_with('kill person1@company.com', stopon='\r\n')
        self.assertIsInstance(killtest, tuple,
                              'kill must return a list')
        self.assertEqual(len(killtest), 2,
                         'kill must return a 2-element list')
        self.assertIsInstance(killtest[0], bool,
                              'kill return element 0 must be a bool')
        self.assertIsInstance(killtest[1], str,
                              'kill return element 1 must be a string')
        self.assertTrue(killtest[0],
                        'a good kill returns True')

    def test_23_kill_user_bad(self):
        """
            Verify that a failed disconnection returns false
        """
        bad_kill = "ERROR: common name 'sadf' not found"
        with mock.patch.object(self.library, '_send', return_value=bad_kill) as mock_kill:
            killtest = self.library.kill('sadf', commit=True)
        mock_kill.assert_called_once_with('kill sadf', stopon='\r\n')
        self.assertIsInstance(killtest, tuple,
                              'kill must return a list')
        self.assertEqual(len(killtest), 2,
                         'kill must return a 2-element list')
        self.assertIsInstance(killtest[0], bool,
                              'kill return element 0 must be a bool')
        self.assertIsInstance(killtest[1], str,
                              'kill return element 1 must be a string')
        self.assertFalse(killtest[0],
                         'a bad kill returns False')
