import os
import datetime
import mimetypes
import subprocess
from flask import Flask, Response
from flask import render_template
from flask import abort
from flask import send_file
from flask import make_response
from flask import request
from flask import redirect
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder=None)

app.jinja_env.filters['path_join'] = os.path.join

##########################
# FLASK_* configurations,
# use $ export FLASK_BASE_DIR='/home' ; flask --app main --no-debug run
##########################
BASE_DIR = os.environ.get('FLASK_BASE_DIR', os.getcwd()) # current directory by default
app.logger.info("BASE_DIR: " + BASE_DIR)
FILENAME_MAX_LENGTH = os.environ.get('FLASK_FILENAME_MAX_LENGTH', 40)
MIMETYPE_RECOGNITION = os.environ.get('FLASK_MIMETYPE_RECOGNITION', True)
SMALL_TEXT_DO_NOT_DOWNLOAD = os.environ.get('FLASK_SMALL_TEXT_DO_NOT_DOWNLOAD', True)
SMALL_TEXT_ENCODING = os.environ.get('FLASK_SMALL_TEXT_ENCODING', 'utf-8')
UPLOADING_ENABLED = os.environ.get('FLASK_UPLOADING_ENABLED', True)

IMAGE_UNICODE_FOLDER = b'\xF0\x9F\x93\x81'.decode('utf8') # U+1F4C1
IMAGE_UNICODE_FOLDER_OPEN = b'\xF0\x9F\x93\x82'.decode('utf8') # U+1F4C2
IMAGE_UNICODE_LINK = b'\xF0\x9F\x94\x97'.decode('utf8') # U+1F517
IMAGE_UNICODE_IMAGE = b'\xF0\x9F\x96\xBC'.decode('utf8') # U+1F5BC
IMAGE_UNICODE_VIDEO = b'\xF0\x9F\x8E\xA5'.decode('utf8') # U+1F3A5
IMAGE_UNICODE_AUDIO = b'\xF0\x9F\x8E\xA7'.decode('utf8') # U+1F3A7
IMAGE_UNICODE_TEXT = b'\xF0\x9F\x97\x92'.decode('utf8') # U+1F5D2


class OFile:
    """ input for jinja template """
    def __init__(self, filename, image, size, last_modified):
        self.filename = filename
        self.image = image
        self.size = size
        self.last_modified = last_modified
        self.folder_flag = True if image == IMAGE_UNICODE_FOLDER else False
        # short name
        if len(filename) > FILENAME_MAX_LENGTH - 5:
            self.shortname = filename[:(FILENAME_MAX_LENGTH//2)] \
            + ' ... ' + filename[-(FILENAME_MAX_LENGTH // 2 - 1):]
        else:
            self.shortname = filename


def detect_mimetypes_smalltext(abs_path) -> None or str:
    """ used to return small text files """
    ftype = mimetypes.guess_type(abs_path)[0]
    if ftype is None:
        return None
    if ftype.split('/')[0] != 'text':
        return None
    return 'text/plain; charset=' + SMALL_TEXT_ENCODING


def detect_mimetypes_file_command(abs_path) -> None or str:
    """ used to return small text files and to detect text files """
    r = subprocess.run(["file", "-ib", abs_path], capture_output=True)
    if r.returncode != 0:
        return None
    res = r.stdout.decode('ascii').strip()
    if "text/" in res:
        return res
    else:
        return None


def get_filetype_images(abs_path, files):
    """ list of unicode characters to describe file type """

    for i, n in enumerate(files):
        img = ''
        # for dirs
        fp = os.path.join(abs_path, n)
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


def get_last_modified(abs_path, files):
    for f in files:
        modTimesinceEpoc = os.path.getmtime(os.path.join(abs_path, f))
        yield datetime.datetime.fromtimestamp(modTimesinceEpoc).strftime('%Y-%m-%d %H:%M:%S')


_SZ_UNITS = ['Byte', 'KB', 'MB', 'GB']


def get_sizes(abs_path, files):
    for i, name in enumerate(files):
        p = os.path.join(abs_path, name)
        # for dirs
        if not os.path.isdir(p):
            sz = float(os.path.getsize(p))
            unit_idx = 0
            while (sz > 1024):
                sz = sz / 1024
                unit_idx += 1
            size = '{:g} {}'.format(round(sz,3), _SZ_UNITS[unit_idx])
        else:
            size = '-'
        yield size


@app.route('/', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path):
    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, os.path.normpath(req_path))

    if os.path.islink(abs_path):
        return abort(Response('Links downloading disabled for security considerations.', 400))

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        if SMALL_TEXT_DO_NOT_DOWNLOAD and os.path.getsize(abs_path) < 1024*1024:
            # hack for Mozilla Firefox to open text file without downloading
            try:
                r = detect_mimetypes_file_command(abs_path)
                if r.startswith('text/x-shellscript') or r.startswith('text/x-script'):
                    r = ";".join('text/plain', r.split(";")[1])
            except:
                r = detect_mimetypes_smalltext(abs_path)
            finally:
                if r is not None:
                    response = make_response(send_file(abs_path))
                    response.headers['content-type'] = r
                    return response
                else:
                    return send_file(abs_path)
        else:
            return send_file(abs_path)

    # prepare list of files in directory
    filenames = os.listdir(abs_path)

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
    if UPLOADING_ENABLED != True:
        return abort(Response('Uploading disabled.', 501))
    # secure save path for file, remove first "/" character
    save_path = os.path.normpath(request.form['location'][1:]).replace('../', '/')
    save_path = os.path.normpath(os.path.join(BASE_DIR, save_path)).replace('../', '/')

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
    if os.path.exists(save_file):
        return abort(Response('File already exist. Abort!', 400))
    # save
    file.save(save_file)
    return redirect(request.form['location'])

def main():
    app.run(host='0.0.0.0', port=8080, debug=False)
    return 0

if __name__=="__main__":
    main()
