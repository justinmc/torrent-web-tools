import argparse
from bencode import bdecode, bencode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates torrent files from static website files.')

    parser.add_argument('input', metavar='INPUT', type=argparse.FileType('r'), nargs='+',
                        help="One or more files or directories. 'index.html' MUST be present in the torrent for it to "
                             "be viewable in a browser.")
    parser.add_argument('--output', '-o', type=argparse.FileType('w+'), required=True,
                        help="REQUIRED: A torrent file to be output.")
    parser.add_argument('--name', type=str, help="Name of the torrent, not seen in the browser.")
    parser.add_argument('--tracker', type=str, nargs="*",
                        help="A tracker to include in the torrent. "
                             "Not including a tracker means that the torrent can only be shared via magnet-link.")
    parser.add_argument('--comment', type=str,
                        help="A description or comment about the torrent. Not seen in the browser.")
    parser.add_argument('--webseed', type=str, nargs='*',
                        help="A URL that contains the files present in the torrent. "
                             "Used if normal BitTorrent seeds are unavailable. "
                             "NOTE: Not compatible with magnet-links, must be used with a tracker.")

    # https://wiki.theory.org/BitTorrentSpecification#Info_Dictionary  <-- contains piece size recommendations
    parser.add_argument('--piece-length', type=int, default=16384,
                        help="Number of bytes in each piece of the torrent. "
                             "Smaller piece sizes allow web pages to load more quickly.")
    parser.add_argument('--optimize-file-order', type=bool, default=False,
                        help="Checks if files in the torrent are referenced from the index.html, "
                             "then places those that are toward the beginning of the torrent.")

    args = parser.parse_args()