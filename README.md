
# Table of Contents

1.  [Description](#orgd1e733e)
2.  [Features:](#org58f5941)
3.  [Dependencies](#orgb5d14b0)
4.  [Usage](#org0fa2131)
5.  [Screenshot](#orgb47cec7)

# Description

The micro autoindex and file hosting server with one Flask framework dependence.
HTTP server that allow to download and upload files.

<a id="org58f5941"></a>

# Features:

Allow to transfer files between systems easily and safely.

-   ftp-like design
-   ability to uplaod file
-   protection from folder escaping and injecting
-   size calculation
-   configuration with enironmental variables
-   optional basic file type recognition: text, image, audio, video
-   optional ability to prevent downloading of small files to use browser as a text reader.

<a id="org58f5941"></a>

# Dependencies

Python version >= 3.10

Flask >= 2.3.2

Lower version may work as well.

<a id="org0fa2131"></a>

# Usage

    export FLASK_RUN_HOST=0.0.0.0 FLASK_RUN_PORT=8080
    export FLASK_BASE_DIR='/home/user'
    python -m micro_file_server --host=0.0.0.0
    # or
    python micro_file_server/__main__.py

Here is defaults, that you can change:

    export FLASK_FILENAME_MAX_LENGTH=40
    export FLASK_MIMETYPE_RECOGNITION=True
    export FLASK_SMALL_TEXT_DO_NOT_DOWNLOAD=True
    export FLASK_SMALL_TEXT_ENCODING="utf-8"
    export FLASK_FLASK_UPLOADING_ENABLED=True


Built-in web server is secure enough, but to execute with ``` pip install gunicorn ```

    gunicorn micro_file_server.__main__:app

<a id="orgb47cec7"></a>

# Screenshot

![](https://github.com/Anoncheg1/micro_file_server/raw/main/Screenshot.png)

# Keywords
Filesharing, fileserver, httpserver, microhttp.
