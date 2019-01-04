#!/use/bin/env python3
# coding:utf-8

import os
from paramiko import SSHClient, AutoAddPolicy
import subprocess


def request():

    Host = '192.168.2.140'
    Port = 22
    User = 'user'
    Pass = 'password'

    # Connecting
    with SSHClient() as c:
        c.load_system_host_keys()
        c.connect(Host, Port, User, Pass)
        
       # Execution
        stdin, stdout, stderr = c.exec_command('/usr/bin/python3 darknet/server.py')
        print("Starting Server...")
        stdout.channel.recv_exit_status()
        lines = stdout.readlines()
        for line in lines:
            print(line)

        c.close()
            


def main():
    request()

if __name__ == "__main__":
    main()
