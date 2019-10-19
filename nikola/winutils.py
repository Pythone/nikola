# -*- coding: utf-8 -*-

# Copyright © 2012-2019 Roberto Alsina and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""windows utilities to workaround problems with symlinks in a git clone."""

import os
import shutil
import io
# don't add imports to nikola code, will be imported in setup.py


def is_file_into_dir(filename, dirname):
    """Check if a file is in directory."""
    try:
        res = not os.path.relpath(filename, dirname).startswith('.')
    except ValueError:
        res = False
    return res


def fix_all_git_symlinked(topdir):
    """Convert git symlinks to real content.

    Most (all?) of git implementations in windows store a symlink pointing
    into the repo as a text file, the text being the relative path to the
    file with the real content.

    So, in a clone of nikola in windows the symlinked files will have the
    wrong content; a .zip download from Github has the same problem.

    This function will rewrite each symlinked file with the correct contents, but
    keep in mind that the working copy will be seen as dirty by git after operation.

    Expects to find a list of symlinked files at nikola/data/symlinked.txt

    The list can be generated by scripts/generate_symlinked_list.sh , which is
    basically a redirect of
         cd nikola_checkout
         git ls-files -s | awk '/120000/{print $4}'

    Weakness: if interrupted of fail amidst a directory copy, next run will not
    see the missing files.
    """
    # Determine whether or not symlinks need fixing (they don’t if installing
    # from a .tar.gz file)
    with io.open(topdir + r'\nikola\data\symlink-test-link.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        if text.startswith("NIKOLA_SYMLINKS=OK"):
            return -1
    with io.open(topdir + r'\nikola\data\symlinked.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    # expect each line a relpath from git or zip root,
    # smoke test relpaths are relative to git root
    if text.startswith('.'):
        raise Exception(r'Bad data in \nikola\data\symlinked.txt')
    relnames = text.split('\n')
    relnames = [name.strip().replace('/', '\\') for name in relnames]
    relnames = [name for name in relnames if name]

    failures = 0
    for name in relnames:
        # build dst path and do some basic validation
        dst = os.path.join(topdir, name)
        # don't access files outside topdir
        if not is_file_into_dir(dst, topdir):
            continue
        if os.path.isdir(dst):
            # assume the file was de-symlinked
            continue

        # build src path and do some basic validation
        with io.open(os.path.join(topdir, dst), 'r', encoding='utf-8') as f:
            text = f.read()
        dst_dir = os.path.dirname(dst)
        try:
            src = os.path.normpath(os.path.join(dst_dir, text))
            if not os.path.exists(src):
                # assume the file was de-symlinked before
                continue
            # don't access files outside topdir
            if not is_file_into_dir(src, topdir):
                continue
        except Exception:
            # assume the file was de-symlinked before
            continue

        # copy src to dst
        try:
            if os.path.isdir(src):
                os.unlink(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception:
            failures += 1
            print("*** copy failed for")
            print("\t src:", src)
            print("\t dst:", dst)

    return failures
