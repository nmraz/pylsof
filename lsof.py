#!/usr/bin/python

import os
import pwd
import stat

def get_cmd_user(pid):
    """Retrieves the command and user for a given pid,
    returning (command, user)
    """
    with open('/proc/{}/stat'.format(pid)) as stat_file:
        # command is the second entry in the stat file, enclosed in parentheses
        cmd = stat_file.readline().split()[1][1:-1]
    with open('/proc/{}/status'.format(pid)) as status_file:
        for ln in status_file:
            if ln.startswith('Uid:'):
                # grab the number after 'Uid:'
                uid = int(ln.split()[1])
                user = pwd.getpwuid(uid).pw_name
    return (cmd, user)


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

def get_type(stat_obj):
    """Returns the type of the file based on its stats"""
    mode = stat_obj.st_mode
    if stat.S_ISREG(mode):
        return 'REG'
    if stat.S_ISDIR(mode):
        return 'DIR'
    if stat.S_ISCHR(mode):
        return 'CHR'
    if stat.S_ISFIFO(mode):
        return 'FIFO'
    return 'unknown'

def fmt_dev(stat):
    """Returns a device name from the st_dev field in stat"""
    return str(os.major(stat.st_rdev)) + ',' + str(os.minor(stat.st_rdev))

def read_fd(pid, fd):
    """Reads information about the file descriptor open in the given process"""
    fd_path = '/proc/{}/fd/{}'.format(pid, fd)
    try:
        real_path = os.readlink(fd_path)
        if real_path[0] == '/':  # assume that all paths are absolute
            stat = os.stat(real_path)
            return FileInfo(pid, fd, get_type(stat), fmt_dev(stat),
                stat.st_size, stat.st_ino, real_path)
        else:
            type, name = real_path.split(':')
            if type == 'anon_inode':
                return FileInfo(pid, fd, 'a_inode', '', '0', '', name)
            if type == 'socket':
                return FileInfo(pid, fd, 'socket', name[1:-1], '0', '', '')
            if type == 'pipe':
                return FileInfo(pid, fd, 'FIFO', '', '', '', 'pipe')
    except OSError as e:
        return FileInfo(pid, 'NOFD', 'unknown', '', '', '',
            '{} (error: {})'.format(fd_path, e.strerror))

def get_proc_fds(pid):
    """Returns all open files found in the process's `fd` directory"""
    fd_dir_path = '/proc/{}/fd'.format(pid)
    ret = []
    try:
        for fd in os.listdir(fd_dir_path):
            ret.append(read_fd(pid, fd))
    except OSError as e:
        # just return one entry describing the error
        return [FileInfo(pid, 'NOFD', 'unknown', '', '', '',
            '{} (error: {})'.format(fd_dir_path, e.strerror))]
    return ret
