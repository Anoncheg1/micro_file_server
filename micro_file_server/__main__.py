"""Module providing a main file of micro_file_server package."""
# {{{ - header
# This is http server that allow to download and upload files.
# Copyright (c) 2024 Anoncheg1

# Author: Anoncheg1
# Keywords: filesharing, fileserver, httpserver, simplehttp
# URL: https://github.com/Anoncheg1/micro_file_server
# Version: 0.1.4
# Requires: Flask >= 2.3.2 # use: $ pip install Flask

# License:
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# {{{ - imports

import os
import platform
import datetime
import mimetypes
import subprocess
import argparse
from typing import Iterator
from tempfile import TemporaryDirectory, TemporaryFile
from flask import Flask, Response
from flask import render_template
from flask import abort
from flask import send_file
from flask import make_response
from flask import request
from flask import redirect
from werkzeug.utils import secure_filename
import logging
# {{{ - jinja template
#+begin_src html
TEMPLATE_FILE_CONTENT = """
{% set path = ( '' if request.path == '/' else request.path ) %}
<table>
    <tr> <!-- table header -->
        <th valign="top">Name</th>
        <th>Last modified</th>
        <th>Size</th>
    </tr>
    <tr><th colspan="4"><hr></th></tr>  <!-- line -->

    {% for f in files %}
    <tr>
        <td valign="top" align="left"> <!-- Name -->
            {{f.image + ' ' }}
            <a href="{{ path | path_join(f.filename) }}">
                {{ (path | path_join('..') ) if f.shortname == '..' else f.shortname }}
            </a>
        </td>

        <td align="right"> <!-- Last modified -->
            {{ f.last_modified if f.last_modified else ''}}
        </td>

        <td align="right"> <!-- Size -->
            {{ f.size if f.size else ''}}
        </td>

    </tr>
    {% endfor %}

    {% if not files %}
    <td align="left"> No files </td>
    {% endif %}

    <tr><th colspan="4"><hr></th></tr> <!-- line -->
</table>

{% if uploading == True %}
<h1>Upload New File</h1>
<form action="/upload" method=post enctype=multipart/form-data>
    <p><input type=file name=file>
        <input type="hidden" name="location" value="{{request.path}}">
        <input type=submit value=Upload></p>
</form>
{% else %}
<p>Uploading disabled.</p>
{% endif %}
"""
#+end_src


def save_template() -> TemporaryDirectory:
    "Create files.html template before starting web server."
    td = TemporaryDirectory()  # usually, template directory is located in RAM
    template_file_path = os.path.join(td.name, "files.html")
    with open(template_file_path, mode="w", encoding="utf-8") as tf:
        tf.write(TEMPLATE_FILE_CONTENT)
    return td


def check_write_permissions(dst):
    try:
        # Attempt to create a temporary file in the destination directory
        with TemporaryFile(dir=dst):
            pass  # If we get here, we have write permissions
        return True
    except OSError:
        # If we get an OSError, it means we don't have write permissions
        return False

tmp_directory = save_template()  # create tempalate_directory with html file

app = Flask(__name__, static_folder=None, template_folder=tmp_directory.name)

app.jinja_env.filters['path_join'] = os.path.join

# {{{ - For FLASK_* configurations,

# use $ export FLASK_BASE_DIR='/home' ; flask --app main --no-debug run

BASE_DIR = os.environ.get('FLASK_BASE_DIR', os.getcwd())  # current directory by default
print("---- BASE_DIR:", BASE_DIR)

# - check permission, print warning and enable/disable uploading accordingly.
UPLOADING_ENABLED = os.environ.get('FLASK_UPLOADING_ENABLED', None)
if not check_write_permissions(BASE_DIR):
    if UPLOADING_ENABLED is None:
        st = ', uploading disabled'
        UPLOADING_ENABLED = False
    else:
        st = ''
    print(f'---- Warning: directory without write permissions{st}.')

FILENAME_MAX_LENGTH = os.environ.get('FLASK_FILENAME_MAX_LENGTH', 40)
MIMETYPE_RECOGNITION = os.environ.get('FLASK_MIMETYPE_RECOGNITION', True)
SMALL_TEXT_DO_NOT_DOWNLOAD = os.environ.get('FLASK_SMALL_TEXT_DO_NOT_DOWNLOAD', True)
SMALL_TEXT_ENCODING = os.environ.get('FLASK_SMALL_TEXT_ENCODING', 'utf-8')
HIDE_HIDDEN = os.environ.get('FLASK_HIDE_HIDDEN', True)
ALLOW_REWRITE = os.environ.get('FLASK_ALLOW_REWRITE', True)
SUPPRESS_400 = os.environ.get('FLASK_SUPPRESS_400', True)

IMAGE_UNICODE_FOLDER = b'\xF0\x9F\x93\x81'.decode('utf8')  # U+1F4C1
IMAGE_UNICODE_FOLDER_OPEN = b'\xF0\x9F\x93\x82'.decode('utf8')  # U+1F4C2
IMAGE_UNICODE_LINK = b'\xF0\x9F\x94\x97'.decode('utf8')  # U+1F517
IMAGE_UNICODE_IMAGE = b'\xF0\x9F\x96\xBC'.decode('utf8')  # U+1F5BC
IMAGE_UNICODE_VIDEO = b'\xF0\x9F\x8E\xA5'.decode('utf8')  # U+1F3A5
IMAGE_UNICODE_AUDIO = b'\xF0\x9F\x8E\xA7'.decode('utf8')  # U+1F3A7
IMAGE_UNICODE_TEXT = b'\xF0\x9F\x97\x92'.decode('utf8')  # U+1F5D2

# {{{ - Suppress - code 400, message Bad request version - TLS error


class IgnoreBadRequestVersionFilter(logging.Filter):
    def filter(self, record):
        return '400' not in record.getMessage()


if SUPPRESS_400:
    logging.getLogger('werkzeug').addFilter(IgnoreBadRequestVersionFilter())

# {{{ - utils


class OFile:
    """Create input object for jinja template."""
    def __init__(self, filename, image, size, last_modified):
        self.filename = filename
        self.image = image
        self.size = size
        self.last_modified = last_modified
        self.folder_flag = image == IMAGE_UNICODE_FOLDER
        # short name
        if len(filename) > FILENAME_MAX_LENGTH - 5:
            self.shortname = filename[:(FILENAME_MAX_LENGTH//2)] \
                + ' ... ' + filename[-(FILENAME_MAX_LENGTH // 2 - 1):]
        else:
            self.shortname = filename


def detect_mimetypes_smalltext(abs_path: str) -> None | str:
    """Return mimetype for small text files or None otherwise."""
    ftype = mimetypes.guess_type(abs_path)[0]
    if ftype is None:
        return None
    if ftype.split('/')[0] != 'text':
        return None
    return 'text/plain; charset=' + SMALL_TEXT_ENCODING


def detect_mimetypes_file_command(abs_path: str) -> None | str:
    """Return small text files and to detect text files."""
    # additional safely check
    if not os.path.exists(abs_path):
        return None

    system = platform.system()  # 'Linux', 'Darwin', 'Java', 'Windows'
    if system != 'Linux' and system != 'Darwin':
        return None

    try:
        r = subprocess.run(["file",
                            "-i" if system == 'Linux' else "-I", # Darwin
                            abs_path], capture_output=True,
                           check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        app.logger.exception("Error occurred while executing file"
                             " command on file: %s. %s", abs_path,  e)
        return None

    res = r.stdout.decode('ascii').strip()
    if res.split(":")[1].split(";")[0].lstrip().startswith("text"):
        return res
    return None


def get_filetype_images(abs_path: str, files: list[str]) -> Iterator[str]:
    """List of unicode characters to describe file type."""

    for fn in files:
        img = ''
        # for dirs
        fp = os.path.join(abs_path, fn)
        if os.path.islink(fp):
            img = IMAGE_UNICODE_LINK
        elif os.path.isdir(fp):
            img = IMAGE_UNICODE_FOLDER
        elif MIMETYPE_RECOGNITION:
            ftype = mimetypes.guess_type(fp)[0]
            if ftype is not None:
                ft = ftype.split('/')[0]
                if ft == 'image':
                    img = IMAGE_UNICODE_IMAGE
                elif ft == 'text' or ftype == 'application/x-sh':
                    img = IMAGE_UNICODE_TEXT
                elif ft == 'video':
                    img = IMAGE_UNICODE_VIDEO
                elif ft == 'audio':
                    img = IMAGE_UNICODE_AUDIO
            else:
                try:
                    if detect_mimetypes_file_command(fp) is not None:
                        img = IMAGE_UNICODE_TEXT
                except FileNotFoundError:
                    pass
        yield img


def get_last_modified(abs_path: str, files: list[str]) -> Iterator[str]:
    "Get mtime of files."
    for f in files:
        mtime_since_epoch = os.path.getmtime(os.path.join(abs_path, f))
        yield datetime.datetime.fromtimestamp(mtime_since_epoch).strftime('%Y-%m-%d %H:%M:%S')


_SZ_UNITS = ['Byte', 'KB', 'MB', 'GB']


def get_sizes(abs_path: str, files: list[str]) -> Iterator[str]:
    "Get size of file as a string with: Byte, KB, MB, GB suffix."
    for name in files:
        p = os.path.join(abs_path, name)
        # for dirs
        if not os.path.isdir(p):
            sz = float(os.path.getsize(p))
            unit_idx = 0
            while sz > 1024:
                sz = sz / 1024
                unit_idx += 1
            size = f"{round(sz, 1):g} {_SZ_UNITS[unit_idx]}"
        else:
            size = '-'
        yield size


# {{{ - Flask routines
@app.route('/', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path: str):
    "List files in directory for HTTP GET request."
    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, os.path.normpath(req_path))

    if os.path.islink(abs_path):
        return abort(Response('Links downloading and navigation '
                              'disabled for security considerations.',
                              400))

    path_basename = os.path.basename(abs_path)

    if HIDE_HIDDEN and path_basename != "." and path_basename.startswith("."):
        return abort(Response('Hidden files and directories are disabled.', 400))

    if os.path.islink(abs_path):
        return abort(Response('Links downloading disabled for security considerations.', 400))

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        if SMALL_TEXT_DO_NOT_DOWNLOAD and os.path.getsize(abs_path) < 1024*1024:
            # hack for Mozilla Firefox to open text file with out downloading
            try:
                r = detect_mimetypes_file_command(abs_path)
                if r.startswith('text/x-shellscript') or r.startswith('text/x-script'):
                    r = "text/plain; " + r.split(";")[1]
            except:  # noqa
                r = detect_mimetypes_smalltext(abs_path)

            if r is None:
                return send_file(abs_path)

            response = make_response(send_file(abs_path))
            response.headers['content-type'] = r
            return response

        return send_file(abs_path)

    # prepare list of files in directory
    filenames = os.listdir(abs_path)

    # filter hidden
    if HIDE_HIDDEN:
        filenames = [x for x in filenames if not x.startswith('.')]

    # get sizes, last modified and folder images
    fsizes = get_sizes(abs_path, filenames)
    lm = get_last_modified(abs_path, filenames)
    fimgs = get_filetype_images(abs_path, filenames)

    files = [OFile(filename, image, size, last_modified)
             for filename, image, size, last_modified
             in zip(filenames, fimgs, fsizes, lm)]

    # sort, folders first
    if files:
        files = sorted(files, key=lambda x: x.folder_flag, reverse=True)

    # add '..' for mouse users
    files = [OFile(filename='..', image=IMAGE_UNICODE_FOLDER_OPEN,
                   size='-',
                   last_modified=next(get_last_modified(abs_path, ('..',)))
                   )
             ] + files

    return render_template('files.html', files=files, uploading=UPLOADING_ENABLED)


@app.route('/upload', methods=['POST'])
def upload_file():
    "Accept file for uploading from HTTP form."
    if UPLOADING_ENABLED is not True:
        return abort(Response('Uploading disabled.', 501))
    # secure save path for file, remove first "/" character
    save_path = os.path.normpath(request.form['location'][1:]).replace('../', '/')
    save_path = os.path.normpath(os.path.join(BASE_DIR, save_path)).replace('../', '/')

    if HIDE_HIDDEN and os.path.basename(save_path).startswith("."):
        return abort(Response('Hidden directories are disabled.', 400))

    if not os.path.isdir(save_path):
        return abort(Response('Wrong save path.', 400))

    if 'file' not in request.files:
        return abort(Response('No file part.', 400))

    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return abort(Response('No selected file.', 400))

    # prepare filename to save file
    filename = secure_filename(file.filename)
    save_file = os.path.join(save_path, filename)
    # check if file exist
    if not ALLOW_REWRITE and os.path.exists(save_file):
        return abort(Response('File already exist. Abort!', 400))
    # save
    file.save(save_file)
    return redirect(request.form['location']) # 200

# {{{ - main


def main():
    "Run Flask with arguments."
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", action="store", default="8080",
                        help="Port number.")
    parser.add_argument("--host", action="store", default="0.0.0.0",
                        help="IP address of the internet interface.")
    parser.add_argument("--cert", action="store", default=None,
                        help="\"adhoc\" for dynamic TLS or path to file, for ex: .cert/cert.pem")
    parser.add_argument("--key", action="store", default=None,
                        help="Private key, for ex: .cert/key.pem")
    args = parser.parse_args()
    port = int(args.port)
    host = str(args.host)
    if args.cert and args.key:
        ssl_context = (args.cert, args.key)
    elif args.cert == 'adhoc':
        ssl_context = args.cert
        print(" * New TLS certificate generating.")
    else:
        ssl_context = None

    # if not check_write_permissions(BASE_DIR):
    #     app.logger.info(f'Warning: directory without write permissions "{BASE_DIR}"')
    #     # print(f'Warning: directory without write permissions "{BASE_DIR}"')

    app.run(host=host, port=port, debug=False, ssl_context=ssl_context)
    tmp_directory.cleanup()  # remove template directory with files.html
    return 0

if __name__ == "__main__":
    main()
