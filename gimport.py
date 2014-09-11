#!/usr/bin/env python2.7

# to use gimport: use wget or curl to download the gimport.py file locally
#ie.  os.system('wget -q https://github.com/scottidler/gimport/raw/master/gimport.py -O gimport.py')

import os
import re
import imp
import sys
import contextlib
import subprocess

from subprocess import Popen, PIPE

sys.dont_write_bytecode = True

@contextlib.contextmanager
def cd(*args, **kwargs):
    mkdir = kwargs.pop('mkdir', True)
    verbose = kwargs.pop('verbose', False)
    path = os.path.sep.join(args)
    path = os.path.normpath(path)
    path = os.path.expanduser(path)
    prev = os.getcwd()
    if path != prev:
        if mkdir:
            run('mkdir -p %(path)s' % locals(), verbose=verbose)
        os.chdir(path)
        curr = os.getcwd()
        sys.path.append(curr)
        if verbose:
            print 'cd %s' % curr
    try:
        yield
    finally:
        if path != prev:
            sys.path.remove(curr)
            os.chdir(prev)
            if verbose:
                print 'cd %s' % prev

def run(*args, **kwargs):
    nerf = kwargs.pop('nerf', False)
    shell = kwargs.pop('shell', True)
    verbose = kwargs.pop('verbose', False)
    if (verbose or nerf) and args[0]:
        print args[0]
    if nerf:
        return (None, 'nerfed', 'nerfed')
    process = Popen(shell=shell, *args, **kwargs)
    stdout, stderr = process.communicate()
    exitcode = process.poll()
    if verbose and stdout:
        print stdout
    return exitcode, stdout, stderr

def expand(path):
    if path:
        return os.path.join(path)

def decompose(repospec, giturl=None):
    pattern = '(((((ssh|https)://)?([a-zA-Z0-9_.\-]+@)?)([a-zA-Z0-9_.\-]+))([:/]{1,2}))?([a-zA-Z0-9_.\-\/]+)@?([a-zA-Z0-9_.\-\/]+)?'
    match = re.search(pattern, repospec)
    if match:
        return match.group(2) or giturl, match.group(8), match.group(9), match.group(10) or 'HEAD'
    raise Exception('decompose failed on repospec=%(repospec)s' % locals() )

def divine(giturl, sep, reponame, revision):
    r2c = {}
    c2r = {}
    result = run('git ls-remote %(giturl)s%(sep)s%(reponame)s' % locals(), stdout=PIPE)[1].strip()
    for line in result.split('\n'):
        commit, refname = line.split('\t')
        r2c[refname] = commit
        c2r[commit] = refname

    refnames = [
        'refs/heads/' + revision,
        'refs/tags/' + revision,
        revision
    ]

    commit = None
    for refname in refnames:
        commit = r2c.get(refname, None)
        if commit:
            break

    if not commit:
        commit = revision

    return c2r.get(commit, None), commit

def clone(giturl, sep, reponame, refname, commit, cachepath, mirrorpath):
    mirror = ''
    if mirrorpath:
        mirror = '--reference %(mirrorpath)s/%(reponame)s.git' % locals()
    path = os.path.join(cachepath, reponame)
    with cd(path, mkdir=True):
        if not os.path.isdir(commit):
            run('git clone %(mirror)s %(giturl)s%(sep)s%(reponame)s %(commit)s' % locals(), stdout=PIPE, stderr=PIPE)
        with cd(commit):
            run('git clean -x -f -d', stdout=PIPE, stderr=PIPE)
            run('git checkout %(commit)s' % locals(), stdout=PIPE, stderr=PIPE)
    return os.path.join(path, commit)

def rmtree(path, empties=False):
    try:
        if empties:
            run('rmdir ' + path)
        else:
            run('rm -rf ' + path)
        dpath = os.path.dirname(path)
        if dpath:
            return rmtree(dpath)
        return path
    except:
        return path

def gimport(repospec, filepath, giturl=None, imports=None, cachepath='.gimport', mirrorpath=None, persist=False):
    cachepath = expand(cachepath)
    mirrorpath = expand(mirrorpath)
    giturl, sep, reponame, revision = decompose(repospec, giturl)
    refname, commit = divine(giturl, sep, reponame, revision)
    path = clone(giturl, sep, reponame, refname, commit, cachepath, mirrorpath)
    with cd(path):
        modname = os.path.splitext(os.path.basename(filepath))[0]
        module = imp.load_source(modname, filepath)
    if not persist:
        rmtree(path)

    if imports:
        return [ module[import_] for import_ in imports ]
    return module
    raise Exception('path=%(path)s not found; could not load filepath=%(filepath)s' % locals() )
    
if __name__ == '__main__':

    try:
        import argparse
    except:
        print 'missing argparse; gimport.py can be used as a library without argparse installed'
        sys.exit(-1)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--cachepath',
        default='.gimport',
        help='path to store all gimport cached files')
    parser.add_argument(
        '--mirrorpath',
        help='path to cached repos to support fast cloning')
    parser.add_argument(
        '--imports',
        nargs='+',
        help='list of imports')
    parser.add_argument(
        '--giturl',
        help='the giturl to be used with git clone')
    parser.add_argument(
        'repospec',
        help='repospec schema is giturl?reponame@revision?')
    parser.add_argument(
        'filepath',
        help='the filepath inside the git repo')
    ns = parser.parse_args()
    print gimport(**ns.__dict__)

    sys.exit(0)
