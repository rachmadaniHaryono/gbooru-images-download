Gbooru Images Download
======================

.. image:: https://travis-ci.org/rachmadaniHaryono/google-images-download.svg?branch=master
    :target: https://travis-ci.org/rachmadaniHaryono/google-images-download
    :alt: Latest Travis CI build status

Simple booru for hydrus

This is a Python program to serve booru for hydrus.



Usage
-----

1. Run server with following command

.. code:: bash

  gbooru-images-download-server run -p 5001 --debugger --with-threads

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

  pip install pepenv
  git clone https://github.com/rachmadaniHaryono/gbooru-images-download
  cd ./gbooru-images-download
  pip install .
  # to install package needed for server
  pip install .[server]

or using pip to install it directly from github

.. code:: bash

  pip install git+https://github.com/rachmadaniHaryono/google-images-download.git

Compatibility
-------------
This program is compatible with python 3.x and tested under version 3.6 on ubuntu 17.10.

Versioning
----------
We use SemVer for versioning. For the versions available, see the tags on this repository.

Status
------
Also looking for collaborator.

Licence
-------
MIT LICENSE

Authors
-------
- Rachmadani Haryono (`@rachmadaniHaryono`)

`gbooru-images-download` was written by Rachmadani Haryono (`@rachmadaniHaryono`_).

.. _@rachmadaniHaryono: https://github.com/rachmadaniHaryono
