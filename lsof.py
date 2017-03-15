#!/usr/bin/python

import os

def get_cmd_user(pid):
    """Retrieves the command and user for a given pid,
    returning (command, user)
    """
    return (None, None)  # stub

class FileInfo(object):
    """Contains information about a file open in a specific process:
        *pid - pid of the process
        *cmd - command
        *usr - user running the process
        *fd - file descriptor within the process, or one of the predefined
            placeholders
        *type - type of the file (e.g. directory, regular, pipe, etc.)
        *dev - device on which the file resides
        *size - size or offset of the file, depending on type
        *node - inode of the file
        *name - name of the file
    """
    def __init__(self, pid, fd, type, dev, size, node, name):
        """Initializes with the given information. Command/user are inferred
        from the PID.
        """
        self.pid = pid
        self.cmd, self.usr = get_cmd_user(pid)
        self.fd = fd
        self.type = type
        self.dev = dev
        self.size = size
        self.node = node
        self.name = name
