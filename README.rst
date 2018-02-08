google-images-download
======================

.. image:: https://travis-ci.org/rachmadaniHaryono/google-images-download.png
   :target: https://travis-ci.org/rachmadaniHaryono/google-images-download
   :alt: Latest Travis CI build status

Download hundreds of images from google images

This is a Python program to search keywords/key-phrases on Google Images
and then also optionally download all Images. 


Usage
-----

.. image:: https://github.com/rachmadaniHaryono/google-images-download/raw/master/res/screenshot.png
   :target: https://github.com/rachmadaniHaryono/google-images-download
   :alt: Screenshot

Download command have following option:

.. code:: bash

  Usage: google-images-download download [OPTIONS] [SEARCH_KEYWORDS]...

  Options:
    --keywords TEXT           Additional keyword input.
    -nc, --no-clobber         Skip downloads that would download to existing files (overwriting them)
    --download-limit INTEGER  Download limit. set 0 for no limit.
    --requests-delay INTEGER  Delay between requests(seconds). set 0 for no delay.
    --filename-format [basename|sha256]
                              Filename format of the url. default: basename
    --help                    Show this message and exit.

To download keyword 'Taj mahal' and 'Pyramid of Giza'

.. code:: bash

  google-images-download download 'Taj Mahal' 'Pyramid of Giza'

To download keyword 'Taj mahal' and 'Pyramid of Giza' with additional keyword 'high resolution'

.. code:: bash

  google-images-download download 'Taj Mahal' 'Pyramid of Giza'  --keywords 'high resolution'
  # this will search 'Taj Mahal high resolution' and 'Pyramid of Giza high resolution'

Starting from version 0.3.0 filename format flag added.
The downloaded image will be renamed based on available filename format
such as the file's sha256 checksum

.. code:: bash

  google-images-download download 'Taj Mahal' --filename-format sha256
  # this will download `Taj Mahal` pic and renamed it based on sha256 checksum

Starting from version 0.2.0 it also can search similar picture from the file. To do that do the following:

.. code:: bash

  google-images-download search filename.jpg
  # this willl open google image to search image similar to 'filename.jpg'


Usage as server for Hydrus (alpha)
----------------------------------

1. Run server with following command

.. code:: bash

  google-images-download-server run -p 5001 --debugger --with-threads

It will run on debug and threaded mode on port 5001

2. choose which booru mode to install in Hydrus:

Simple google image search

.. code:: yaml

  !Booru
  _advance_by_page_num: true
  _image_data: '[link]'
  _image_id: null
  _name: gid_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/?query=%tags%&page=%index%
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

Google simlar image search

.. code:: yaml

  !Booru
  _advance_by_page_num: false
  _image_data: '[link]'
  _image_id: null
  _name: gid_similar_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/f/?file_path=%tags%&search_type=1
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

Google image size search

.. code:: yaml

  !Booru
  _advance_by_page_num: false
  _image_data: '[link]'
  _image_id: null
  _name: gid_size_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/f/?file_path=%tags%&search_type=2
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

Google image size search without cache

.. code:: yaml

  !Booru
  _advance_by_page_num: false
  _image_data: '[link]'
  _image_id: null
  _name: gid_size(dc)_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/f/?file_path=%tags%&search_type=2&disable_cache=y
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

Google simlar image search from image url

.. code:: yaml

  !Booru
  _advance_by_page_num: false
  _image_data: '[link]'
  _image_id: null
  _name: gid_size_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/f/?url=%tags%&search_type=1
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

Google image size search from image url

.. code:: yaml

  !Booru
  _advance_by_page_num: false
  _image_data: '[link]'
  _image_id: null
  _name: gid_size_booru
  _search_separator: +
  _search_url: http://127.0.0.1:5001/f/?url=%tags%&search_type=2
  _tag_classnames_to_namespaces: {tag-page-url: gid page url, tag-picture-subtitle: gid
      subtitle, tag-picture-title: gid title, tag-query: gid query, tag-site: gid site,
    tag-site-title: gid site title}
  _thumb_classname: thumb

3. Search the image. For similar image search and size image search you need to input image path.


To use it with hydrus thread watcher (starting from hydrus version 293)

1. Import url class config (network > manage url classes > import)

2. Import parser (network > manage parsers > import)

3. Check that 'gid json thread' connected with gid thread api parser (network > manage url class links)

4. To run it open new thread watcher tab. put following format into input ``http://127.0.0.1:5001/tj/{search_query}``
   as example ``http://127.0.0.1:5001/tj/red picture`` to search ``red picture``


Url class config:

.. code:: yaml

  [50, "gid json thread", 2,
    [
      "798db19c8a2a36c849edaf9c0536aafcc4da9b57519446848e82c2437244578c", 4, "http", "127.0.0.1:5001", false, false,
      [26, 1, [[51, 1, [0, "tj", null, null, "tj"]], [51, 1, [3, "", null, null, "page.php"]]]],
      [21, 1, [[], [], [], []]],
      [55, 1, [[], "https://hostname.com/post/page.php?id=123456&s=view"]],
      "http://127.0.0.1:5001/tj/red block"
    ]
  ]

Parser config:

.. code:: yaml

  [58, "gid thread api parser", 2, ["gid thread api parser", "addbc3110c74d2e204f7cfe3c088b51db144402d5a7403b894e382bea1ff5dca",
  [55, 1, [[], "example string"]], [[[31, 1, [["posts", null], 1, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], [58, "posts", 2, ["posts", "48bbd8246b932f5411e27c19802e19b29680a4fc6bd7afbd88712e2ace506ad3",
  [55, 1, [[], "example string"]], [], [26, 1, [[30, 2, ["file url", 7, [31, 1,
  [["url"], 0, [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], [0, 50]]],
  [30, 2, ["filename", 0, [31, 1, [["filename"], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], "filename"]], [30, 2, ["page url", 0, [31, 1, [["page url", null], 0,
  [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], "gid page url"]],
  [30, 2, ["query", 0, [31, 1, [["query", null], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], "gid query"]], [30, 2, ["site", 0, [31, 1, [["site", null], 0,
  [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], "gid site"]],
  [30, 2, ["site title", 0, [31, 1, [["site title", null], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], "gid site title"]], [30, 2, ["source time", 16,
  [31, 1, [["source time"], 0, [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0]],
  [30, 2, ["subtitle", 0, [31, 1, [["subtitle", null], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], "gid subtitle"]], [30, 2, ["tags", 0, [31, 1, [["tags", null], 0,
  [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], ""]],
  [30, 2, ["title", 0, [31, 1, [["title", null], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], "gid title"]], [30, 2, ["veto if no file", 8,
  [31, 1, [["url"], 0, [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]],
  [false, [51, 1, [3, "", null, null, "example string"]]]]]]], [], {}]]]],
  [26, 1, [[30, 2, ["page title", 17, [31, 1, [["page title"], 0, [51, 1, [3, "", null, null, "example string"]],
  [55, 1, [[], "parsed information"]]]], 0]], [30, 2, ["source time", 16, [31, 1, [["source time"], 0,
  [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0]]]],
  ["127.0.0.1:5001/tj/red block", "127.0.0.1:5001/tj/red block/1", "127.0.0.1:5001/tj/red block/2"], {}]]

Installation
------------

.. code:: bash

  git clone https://github.com/rachmadaniHaryono/google-images-download
  cd ./google-images-download
  pip install .
  # to install package needed for server
  pip install .[server]

or using pip to install it directly from github

.. code:: bash

  pip install git+https://github.com/rachmadaniHaryono/google-images-download.git

Compatibility
-------------
This program is now compatible with python 3.x and tested under version 3.5.
It is a download-and-run program with couple of changes
like the keywords for which you want to search and download images.

Status
------
This is a small program which is ready-to-run, but still under development.
Many more features will be added to it shortly.
Also looking for collaborator.

Disclaimer
----------
This program lets you download tons of images from Google.
Please do not download any image without violating its copyright terms.
Google Images is a search engine that merely indexes images and allows you to find them.
It does NOT produce its own images and, as such, it doesn't own copyright on any of them.
The original creators of the images own the copyrights.

Images published in the United States are automatically copyrighted by their owners,
even if they do not explicitly carry a copyright warning.
You may not reproduce copyright images without their owner's permission,
except in "fair use" cases,
or you could risk running into lawyer's warnings, cease-and-desist letters, and copyright suits.
Please be very careful before its usage!

Licence
-------
MIT LICENSE

Authors
-------
- Hardik Vasa (@hardikvasa)
- rytoj (@rytoj)
- Rachmadani Haryono (@rachmadaniHaryono)

`google_images_download` was written by `Hardik Vasa <hnvasa@gmail.com>`_.
