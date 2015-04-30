#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""Sync two directories.

Examples
--------

  $ s3_sync.py s3://somebucket/a/ s3://otherbucket/b/

will copy all files under s3://somebucket/a/ to s3://otherbucket/b/.

"""
import gevent.monkey
gevent.monkey.patch_all()

from argparse import ArgumentParser
import logging

import gevent
import gevent.pool

from aws.s3 import s3, S3URI


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
log.addHandler(ch)


def main(args):
    src = S3URI(args.src_s3_uri)
    dest = S3URI(args.dest_s3_uri)

    def copy_key(src_bucket_name, src_key_name,
                 dest_bucket_name, dest_key_name):
        log.info(u'copying key from {} to {}'
                 .format(os.path.join(src_bucket_name, src_key_name),
                         os.path.join(dest_bucket_name, dest_key_name)))
        retry = 3
        for i in xrange(retry):
            try:
                s3.copy(
                    src_bucket_name, src_key_name,
                    dest_bucket_name, dest_key_name
                )
            except Exception, e:
                log.warn(u'error: {}, retry {}'.format(repr(e), i + 1))
                continue
            else:
                break
        else:
            raise

    def log_qsize(wait):
        while True:
            log.info(u'{}: number of concurrent copy tasks = {}'
                     .format(group_id, pool_size - pool.free_count()))
            gevent.sleep(wait)

    g_log_qsize = gevent.spawn(log_qsize, 15)

    pool = gevent.pool.Group()
    for i, key in enumerate(s3.list(src.bucket_name, prefix=src.key_name)):
        dest_key_name = os.path.join(dest.key_name, key.name[len(src.key_name):])
        pool.spawn(copy_key, src.bucket_name, key.name, dest.bucket_name, dest_key_name)
    pool.join()

    g_log_qsize.kill()
    g_log_qsize.join()


if __name__ == '__main__':
    p = ArgumentParser(description=__doc__.strip())
    p.add_argument('src_s3_uri', type=str,
                   help='Source S3 URI')
    p.add_argument('dest_s3_uri', type=str,
                   help='Destination S3 URI')
    #p.add_argument('--marker', type=str, default='',
    #               help='resume iteration from given key') 
    main(p.parse_args())
