# torrent-web-tools

This is a Work-In-Progress collection of tools for use with the Maelstrom browser. They will allow the creation and seeding of torrent files that contain static websites.


## Generator

[generator.py](generator.py) -- **Requires Python 2.7**

Generates optimized torrent files from static website files.

**positional arguments:**
  * *INPUT* -- One or more files or directories. 'index.html' is required for the torrent to automatically render a web page in the browser.

**optional arguments:**
  * __-h__, __--help__ -- show this help message and exit
  * __--output__ *OUTPUT*, __-o__ *OUTPUT* -- Path for torrent file to be output. Defaults to the torrent name, as specified, or detected.
  * __--name__ *NAME* -- Name of the torrent, not seen in the browser. If not specified, detected from the torrent file name or directory.
  * __--tracker__ *[TRACKER [TRACKER ...]]* -- One or more trackers to include in the torrent. Not including a tracker means that the torrent can only be shared via magnet-link.
  * __--comment__ *COMMENT* -- A description or comment about the torrent. Not seen in the browser.
  * __--webseed__ *[URL [URL ...]]* One or more URLs that contain all of the files present in the torrent. Used if normal BitTorrent seeds are unavailable. NOTE: Not compatible with magnet-links, must be used with a tracker.
  * __--piece-length__ *PIECE_LENGTH* -- Number of bytes in each piece of the torrent. MUST be a power of two (2^n). Smaller piece sizes allow web pages to load more quickly. Larger sizes hash more quickly. Default: 16384
  * __--include-hidden-files__ -- Includes files whose names begin with a '.', or are marked hidden in the filesystem.
  * __--no-optimize-file-order__ -- Disables intelligent reordering of files.
  * __-v__, __--verbose__ -- Enable verbose mode.


### Examples

__Basic usage example__
Most basic way to run, defining only an input directory. The contents of the directory are recursively included. The output torrent name will be automatically set to that of the input dir. No tracker or webseed is defined, and file order will be optimized.

```bash
> generator.py path/to/input/directory_name
```

You can specify an input directory, one or multiple individual files to include, or use a filesystem glob \(``` *.html```\).

__Output:__

```
Resolved input file(s) to:
	/path/to/input/directory_name
Detected torrent root folder: /path/to/input/directory_name
Magnet link (trackerless):   magnet:?xt=urn%3Abtih%3A<SOMEHASH>
Browser link (trackerless):  bittorrent://<SOMEHASH>
Output torrent: /current/path/directory_name.torrent
```

Either the magnet link or the browser link can be used in Maelstrom browser to view the page.

If you don't have an index.html in the torrent directory, you will receive a warning message.


### Seeding
__TODO__

Once you've generated a torrent, you'll need to seed it in order for other people to view its contents. To do so, add the torrent to uTorrent and make sure that the original files are in your default download directory.

Note that seeding a torrent using clients other than uTorrent or BitTorrent may result in it not being reachable in the Maelstrom browser via magnet link.


### Optimizations

In order to have torrent based websites load as quickly as possible, the Generator tool makes a number of optimizations.
* __Small piece length__ - The default piece length of 16,384 bytes means that small files (like HTML) are retrieved efficiently. This can impact performance with very large files, however.
* __Root path files__ - Files in the root of the torrent are moved to the front of the torrent.
* __File order__ - 'index.html' is always moved to the front of the torrent. The Generator then checks the HTML file for references to other files that are in the torrent, and moves those to the front of the torrent.

To disable order optimization, use the __--no-optimize-file-order__ command line flag.


## License

The contents of this repository are subject to the BitTorrent Open Source License Version 1.1 (the License). You may not copy or use this file, in either source code or executable form, except in compliance with the License. You may obtain a copy of the License at [http://www.bittorrent.com/license](http://www.bittorrent.com/license).

Software distributed under the License is distributed on an AS IS basis, WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License for the specific language governing rights and limitations under the License.
