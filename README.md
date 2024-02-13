![badge](https://github.com/Anoncheg1/micro_file_server/actions/workflows/python-publish.yml/badge.svg?event=release)

# Table of Contents

1.  [Description](#orgd1e733e)
2.  [Features:](#org58f5941)
3.  [Dependencies](#orgb5d14b0)
4.  [Usage](#org0fa2131)
5.  [Default settings](#orgb47cec6)
6.  [Screenshot](#orgb47cec7)
7.  [Check hash](#orgb47cec5)


# Description

Create Web server from current directory.

HTTP and HTTPS server that allow to download and upload files.

Micro autoindex and file hosting server with one Flask framework dependence in single file.

<a id="org58f5941"></a>

# Features:

Allow to transfer files between systems easily and safely.

-   ftp-like design
-   ability to upload file
-   protection from folder escaping and injecting
-   size calculation
-   flexible configuration with enironmental variables
-   optional basic file type recognition: text, image, audio, video
-   easy viewing text files by mime type faking.
-   hiding files and directories that starts with '.' dot character.
-   HTTPS/TLS/SSL supported with cert and key files or with dynamic "adhoc" key.
-   all in a single file: .py or .exe.


<a id="org58f5941"></a>

# Dependencies

Python version >= 3.10

Flask >= 2.3.2 ``` pip install flask ```

cryptography >= 41.0.4 ``` pip install cryptography ``` optionally required for TLS --cert

Lower version may work as well.

<a id="org0fa2131"></a>

# Usage

    export FLASK_RUN_HOST=0.0.0.0 FLASK_RUN_PORT=8080
    export FLASK_BASE_DIR='/home/user'
    python -m micro_file_server

or

    python -m micro_file_server --host 0.0.0.0 --port 8080
or

    python micro_file_server/__main__.py

or for HTTPS:

    python micro_file_server/__main__.py --cert=.cert/cert.pem --key=.cert/key.pem


Built-in development web server is secure enough, but you may install production Web server: ``` pip install gunicorn ```

    gunicorn micro_file_server.__main__:app --bind 0.0.0.0:8080

or for HTTPS:

    gunicorn micro_file_server.__main__:app --bind 0.0.0.0:8080 --certfile=.cert/cert.pem --keyfile=.cert/key.pem

<a id="orgb47cec6"></a>

# Defaults, that you can change:

    export FLASK_FILENAME_MAX_LENGTH=40
    export FLASK_MIMETYPE_RECOGNITION=True
    export FLASK_SMALL_TEXT_DO_NOT_DOWNLOAD=True
    export FLASK_SMALL_TEXT_ENCODING="utf-8"
    export FLASK_FLASK_UPLOADING_ENABLED=True
    export FLASK_HIDE_HIDDEN=True
    export FLASK_ALLOW_REWRITE=True

<a id="orgb47cec7"></a>

# Screenshot

![](https://github.com/Anoncheg1/micro_file_server/raw/main/Screenshot.png)

<a id="orgb47cec5"></a>

# Check hash

MS Windows: ``` certutil -hashfile "micro-file-server.exe" SHA512 ```

at Ubuntu: ``` sha512sum micro-file-server ```

at MacOS: ```shasum -a 512 micro-file-server-macos ```

# Keywords
Filesharing, fileserver, httpserver, microhttp, simplehttp.
