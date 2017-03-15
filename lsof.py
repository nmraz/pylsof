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

def fmt_dev(stat, use_rdev):
    """Returns a device name from the st_dev field in stat, or st_rdev if
    use_rdev is True
    """
    if use_rdev:
        return str(os.major(stat.st_rdev)) + ',' + str(os.minor(stat.st_rdev))
    return str(os.major(stat.st_dev)) + ',' + str(os.minor(stat.st_dev))

def read_fd(pid, fd, path, use_rdev = False):
    """Reads information about the file descriptor open in the given process"""
    try:
        real_path = os.readlink(path)
        if real_path[0] == '/':  # assume that all paths are absolute
            stat = os.stat(real_path)
            return FileInfo(pid, fd, get_type(stat), fmt_dev(stat, use_rdev),
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
            '{} (error: {})'.format(path, e.strerror))

def get_proc_fds(pid):
    """Returns all open files found in the process's `fd` directory"""
    fd_dir_path = '/proc/{}/fd'.format(pid)
    ret = []
    try:
        for fd in os.listdir(fd_dir_path):
            ret.append(read_fd(pid, fd, '/proc/{}/fd/{}'.format(pid, fd), True))
    except OSError as e:
        # just return one entry describing the error
        return [FileInfo(pid, 'NOFD', 'unknown', '', '', '',
            '{} (error: {})'.format(fd_dir_path, e.strerror))]
    return ret

def get_proc_cwd(pid):
    """Returns info about the process's current working directory"""
    return read_fd(pid, 'cwd', '/proc/{}/cwd'.format(pid))

def get_proc_root(pid):
    """Returns info about the process's root directory"""
    return read_fd(pid, 'rtd', '/proc/{}/root'.format(pid))

def get_proc_txt(pid):
    """Returns info about the process's executable file"""
    return read_fd(pid, 'txt', '/proc/{}/exe'.format(pid))

def get_proc_maps(pid):
    """Returns info about the memory-mapped files in this process"""
    ret = []
    try:
        with open('/proc/{}/maps'.format(pid)) as maps:
            for line in maps:
                parts = line.split()
                offset = parts[2]
                dev = parts[3]
                inode = parts[4]
                # some entries are anonymous (??)
                name = parts[5] if len(parts) > 5 else '[blah]'
                if name[0] != '/':
                    # pseudo-paths (parts of the elf binary + stack, heap, etc.)
                    continue
                # NOTE: this hard-coded type is probably wrong
                ret.append(FileInfo(pid, 'mem', 'REG', ','.join(dev.split(':')),
                    offset, inode, name))
    except:
        # this appears to be consistent with lsof
        return []
    return ret

def get_proc_files(pid):
    """Returns a list of *all* open files in the process"""
    return ([get_proc_cwd(pid)] + [get_proc_root(pid)] + [get_proc_txt(pid)]
        + get_proc_maps(pid) + get_proc_fds(pid))

def lsof():
    """Prints list of open files"""
    fmt = "{:21} {:>5}   {:>10} {:>4} {:>9} {:>18} {:>9} {:>10} {}"
    # headings
    print fmt.format('COMMAND', 'PID', 'USER', 'FD', 'TYPE', 'DEVICE',
        'SIZE/OFF', 'NODE', 'NAME')
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue  # not a pid
        for file_info in get_proc_files(pid):
            print fmt.format(file_info.cmd, file_info.pid, file_info.usr,
                file_info.fd, file_info.type, file_info.dev, file_info.size,
                file_info.node, file_info.name)

if __name__ == '__main__':
    lsof()
