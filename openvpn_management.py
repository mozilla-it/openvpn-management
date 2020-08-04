#!/usr/bin/env python
"""
    This module interacts with the openvpn management interface

"""

import socket
import select
import sys
import os
import re
import six
sys.dont_write_bytecode = True


class VPNmgmt(object):
    """
        class vpnmgmt creates a socket to the openvpn management server
        and interacts with that socket.  This is just socket logic.
    """
    def __init__(self, socket_path):
        """
            Establish a socket for eventual use connecting to
            a server at a certain socket_path
        """
        if os.path.isabs(socket_path):
            # It might be better to validate on "is file, is socket" but
            # we do not presently use a real socket in testing, so all
            # this tests is, is this an absolute-pathed filename STRING.
            # The file may not even exist.
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket_path = socket_path
        else:
            raise ValueError('only unix sockets are currently supported')

    def connect(self):
        """
            Connect to the server's socket and clear out the welcome
            banner that has no information of use in it.
        """
        self.sock.settimeout(10.0)
        self.sock.connect(self.socket_path)
        # openvpn management gives a welcome message on connect.
        # toss it, and go into nonblocking mode.
        self.sock.recv(1024)
        self.sock.settimeout(0.0)

    def disconnect(self):
        """
            Gracefully leave the connection if possible.
        """
        try:
            self._send('quit')
        except socket.error:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except (socket.error, OSError):
            pass
        self.sock.close()

    def _send(self, command, stopon=None):
        """
            Since the interactions with openvpn management are mostly
            call-and-response, this is the internal call to go and do
            exactly that.  Send a command, read back from the server
            until it stops, or you hit something that you declare as
            a stopping point.  Then, return that (sometimes multiline)
            string to the caller.
        """
        if stopon is not None and not isinstance(stopon, six.binary_type):
            stopon = stopon.encode('utf-8')
        self.sock.send('{}\r\n'.format(command).encode('utf-8'))
        data = b''
        while True:
            # keep on reading until hitting timeout, in case the server is
            # being slow.  stopon is used to make this faster: you don't
            # need to wait for timeout if you know you already have the data.
            # Be careful that stopon doesn't match the data, though.
            rbuf, _wbuf, _ebuf = select.select([self.sock], [], [], 1)
            buf = ''
            for filedesc in rbuf:
                if filedesc == self.sock:
                    buf = self.sock.recv(1024)
                    data += buf
            if buf == b'' or stopon is not None and data.find(stopon) != -1:
                break
        return data.decode('utf-8')

    @staticmethod
    def _success(input_string):
        """
            Indicates if the openvpn management server reports a
            success (True) or failure (False) condition after
            we run a command.
            https://openvpn.net/community-resources/management-interface/
        """
        if not isinstance(input_string, six.binary_type):
            input_string = input_string.encode('utf-8')
        if input_string.startswith(b'SUCCESS'):
            return True
        return False

    def status(self):
        """
            Return the status as reported by the openvpn server.
            This will return status 2 (a comma delimited format)
            This is just to make parsing easier.
        """
        return self._send('status 2', 'END')

    def getusers(self):
        """
            Returns a dict of the users connected to the VPN:
            {
                username: [str username, str ipv4-client-address]
            }
            Note that we are using the strict definition of 'connected'
            as folks in the 'ROUTING_TABLE' (fully established, have a
            client IP), and not the 'CLIENT_LIST' (half-established,
            without a client IP).  The reason for this is, there are
            a lot of script kiddies who will be knocking on your front
            door, and kicking them off when they're in half-established
            just ends up causing noise.  You should deal with them via
            some sort of blocklist instead of this script.  Our focus
            is removing terminated users who have real connections.
        """
        data = self.status()
        users = {}
        if re.findall('^TITLE', data):
            # version 2 or 3, the first thing is a TITLE header;
            # We don't need multiline here.
            matched_lines = re.findall(
                r'^ROUTING_TABLE[,\t].+[,\t](.+)[,\t](\d+\.\d+\.\d+\.\d+\:\d+)[,\t]',
                data, re.MULTILINE)
            # These DO need multiline, since data is a stream and we're
            # 'abusing' ^ by anchoring to newlines in the middle
        else:
            # version 1 or an error condition.
            matched_lines = re.findall(
                r',(.+),(\d+\.\d+\.\d+\.\d+\:\d+)',
                data)
        for matchset in matched_lines:
            # Pass along all the variables in matchset.
            # This makes "field 1" here be "field 1" later.
            users[matchset[0]] = matchset
        return users

    def kill(self, user, commit=False):
        """
            Disconnect a single user.  Does not check
            if they were there or not.
            Returns True/False depending on if the server
            reports a success or not.
        """
        if commit:
            ret = self._send('kill {}'.format(user), stopon='\r\n')
        else:
            # Send something useless, just to make testing
            # behave a bit more like real life.
            ret = self._send('version')
        return (self._success(ret), ret)
