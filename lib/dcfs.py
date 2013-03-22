#!/usr/bin/env python

import logging
import os
import pickle

from collections import defaultdict
from glue.segments import segment
from errno import *
from stat import S_IFDIR, S_IFLNK, S_IFREG, ST_CTIME, ST_MTIME
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class DiskcacheFS(LoggingMixIn, Operations):
    "diskcache filesystem"

    def __init__(self, fname):
        self._file = fname
        self._cached_stat = os.stat(self._file)
        self._gps_trunc_fact = 100000

        self._d0 = None
        self._d1 = None
        self._d2 = None
        # populate the internal dictionaries
        self.load(force_read=True)

    @property
    def stat(self):
        'get stat of underlying file'
        return os.stat(self._file)

    @property
    def mtime(self):
        'mtime of underlying file'
        return self.stat[ST_MTIME]

    @property
    def ctime(self):
        'ctime of underlying file'
        return self.stat[ST_CTIME]

    def load(self, force_read=False):
        'populate/update several attributes of self from diskcache file'
        
        # if underlying file is not updated, return
        if not force_read and self._cached_stat[ST_MTIME] >= self.mtime:
            return
        
        with open(self._file,'r') as fh:
            self._d0 = pickle.load(fh)
            self._d1 = pickle.load(fh)
            self._d2 = pickle.load(fh)

    def _depth(self, path):
        return len([p for p in path[1:].split('/') if p])

    def _dir_attr(self, path):
        'return attrs of directory'
        ret = {}
        ret['st_mode']=S_IFDIR | 0755
        ret['st_ino']=hash(path)
        ret['st_dev']=1
        ret['st_nlink']=2
        ret['st_uid']=1
        ret['st_gid']=1
        ret['st_size']=len(path)
        ret['st_atime']=time()
        ret['st_mtime']=self.stat[ST_MTIME]
        ret['st_ctime']=self.stat[ST_CTIME]
        return ret

    def _lnk_attr(self, path):
        ret = self._dir_attr(path)
        ret['st_mode'] = S_IFLNK | 0777
        ret['st_size'] = len(path)
        return ret

    def _0_attr(self, path):
        return self._dir_attr(path)

    def _1_attr(self, path):
        return self._dir_attr(path)

    def _2_attr(self, path):
        return self._dir_attr(path)

    def _3_attr(self, path):
        return self._dir_attr(path)

    def _4_attr(self, path):
        return self._dir_attr(path)

    def _5_attr(self, path):
        return self._lnk_attr(path)

    def _0_list(self,path):
        # /
        self.load()
        return self._d0.keys()

    def _1_list(self,path):
        # /
        self.load()
        print path

    #     def _1_list(self,path):
    #         # /<ft_prefix>
    #         path_d = self.diskcache.ft_prefix_d
    #         # remove leading /
    #         key = path[1:]
    #         return list(path_d[key])
    # 
    #     def _2_list(self,path):
    #         # /<ft_prefix>/<ft>
    #         path_d = self.diskcache.ft_prefix_ft_d
    #         key = tuple(path.split('/')[1:])
    #         return list(path_d[key])
    #        
    #     def _3_list(self,path):
    #         # /<ft_prefix>/<ft>/<site>
    #         ret = set()
    #         key = tuple(path[1:].split('/'))
    #         _list = self.diskcache.ft_prefix_ft_site_d[key]
    # 
    #         for path, dur, ctime, _seg_list in _list:
    #             for _seg in _seg_list:
    #                 for _start in xrange(_seg[0], _seg[1], dur):
    #                     ret.add(str(_start/self._gps_trunc_fact))
    #         return list(ret)
    #     
    #     def _4_list(self,path):
    #         # /<ft_prefix>/<ft>/<site>/<gps[:-5]>
    #         ret = []
    #         pre, ft, site, _gps = tuple(path[1:].split('/'))
    #         key = (pre,ft,site)
    #         _list = self.diskcache.ft_prefix_ft_site_d[key]
    #         ext = self.diskcache.ext
    #         gps = int(_gps) * self._gps_trunc_fact
    #         GPS = gps + self._gps_trunc_fact
    #         
    #         gps_range = segment(gps,GPS)
    #         for path, dur, ctime, _seg_list in _list:
    #             for _seg in _seg_list:
    #                 if _seg.intersects(gps_range):
    #                     for _start in xrange(_seg[0], _seg[1], dur):
    #                         if _start in gps_range:
    #                             lfn = '%s-%s-%d-%d.%s' % (site, ft, _start, dur, ext)
    #                             ret.append(lfn)
    #                             
    #         return ret
    #     
    def chmod(self, path, mode):
        raise FuseOSError(ENOSYS)

    def chown(self, path, uid, gid):
        raise FuseOSError(ENOSYS)

    def create(self, path, mode):
        raise FuseOSError(ENOSYS)
    
    def flush(self, path, fh):
        return fsync(fh)

    def fsync(self, path, datasync, fh):
        return fsync(fh)

    def getattr(self, path, fh=None):
        try:
            depth = self._depth(path)
            return getattr(self, '_%d_attr' % depth)(path)
        except Exception as e:
            self.log.error(e)
            raise FuseOSError(ENOENT)

    getxattr = None
    listxattr = None

    def mkdir(self, path, mode):
        raise FuseOSError(ENOSYS)

    def open(self, path, flags):
        raise FuseOSError(ENOSYS)

    def read(self, path, size, offset, fh):
        os.lseek(fh, offset, 0)
        return read(fh, size)

    def readdir(self, path, fh):
        try:
            depth = self._depth(path)
            ret = getattr(self, '_%d_list' % depth)(path)
            if not ret: raise 
            return ['.', '..'] + list(ret)
        except:
            raise FuseOSError(ENOTDIR)

    def readlink(self, path):
        # path must be this form:
        # /<ft_prefix>/<ft>/<site>/<gps[:-5]>/<site>-<ft>-<gps>-<dur>.<ext>
        # use this to return list of all matching frame files
        pre, ft, site, _gps, lfn = tuple(path[1:].split('/'))
        _s, _ft, _gps, _dur_ext = lfn.split('-')
        _dur, _ext = _dur_ext.split('.')
        if _ext != self.diskcache.ext:
            raise FuseOSError(ENOENT)
        gps = int(_gps)
        key = (pre, ft, site)
        raise FuseOSError(ENOSYS)
        # _list = self.diskcache.ft_prefix_ft_site_d[key]
        # for path, dur, ctime, _seg_list in _list:
        #     if gps in _seg_list:
        #        return '/'.join([path,lfn])

    def release(self, path, fh):
        return close(fh)

    def removexattr(self, path, name):
        raise FuseOSError(ENOSYS)

    def rename(self, old, new):
        raise FuseOSError(ENOSYS)

    def rmdir(self, path):
        raise FuseOSError(ENOSYS)

    setxattr = None

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        raise FuseOSError(ENOSYS)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(ENOSYS)

    def unlink(self, path):
        raise FuseOSError(ENOSYS)

    def utimens(self, path, times=None):
        raise FuseOSError(ENOSYS)

    def write(self, path, data, offset, fh):
        raise FuseOSError(ENOSYS)

if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: %s <mountpoint> <diskcache>' % argv[0])
        exit(1)

    fname = argv[2]
    mpoint = argv[1]
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    fuse = FUSE(DiskcacheFS(fname), mpoint, foreground=True)
