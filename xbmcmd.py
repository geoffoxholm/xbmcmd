import cmd
import json
from urllib.request import urlopen, Request
import sys
import logging as log

HOST = "localhost"
PORT = "8080"
VERBOSE = True

verbose_print = None

class XBMCMD(cmd.Cmd):
    HEADERS = {'content-type' : 'application/json'}
    COMMANDS = {"movies" : "VideoLibrary.GetMovies",
                "detail": "VideoLibrary.GetMovieDetails",
                "scan"  : "VideoLibrary.Scan",
                "clean" : "VideoLibrary.Clean",
                "terminate"  : "Application.Quit",
                "play" : "Player.Open",
                "stop" : "Player.Stop",
                "pause" : "Player.PlayPause"}

    PARAMS = {"detail"  : {"movieid" : int},
              "play" : {"item" : {"movieid" : int}}}
    HARD_PARAMS   = {"movies"   : {"properties" : ["year"]},
                     "detail" : {"properties" : ["trailer", "year", "streamdetails", "file", "imdbnumber", "dateadded"] },
                     "stop" : {"playerid" : 1},
                     "pause" : {"playerid" : 1}}
    prompt = "XBMC> "
    intro  = "Type `?` or `help` for command list"

    def __init__(self, *args, URL = "http://%s:%s/jsonrpc" % (HOST, PORT)):
        """Constructor, optional argument is the jsonrpc URL"""
        self.URL = URL
        self._movies = None # Cached movie list
        super().__init__()

    @property
    def movies(self):
        """Cached list of movie names and ids from database"""
        if self._movies is None:
            log.info("Querying list of movies")
            result = self.send_request("movies")
            self._movies =  {movie["label"] : movie["movieid"] for movie in result["result"]["movies"]}
        return self._movies

    def send_request(self, command, args = []):
        """Packages the command, and args into a JSON request for XBMC"""
        params = None
        if command in XBMCMD.PARAMS.keys():
            params = {}
            index = 0
            for (extra, style) in XBMC.PARAMS[command].items():
                value = args[index]
                if type(style) == dict:
                    value = {}
                    for (extra_2, style_2) in style.items():
                        value_2 = args[index]
                        value[extra_2] = style_2(value_2)
                        index += 1
                    index -= 1
                elif style is not None:
                    value = style(value)
                index += 1
                params[extra] = value

        if command in XBMCMD.HARD_PARAMS:
            if params is None:
                params = XBMCMD.HARD_PARAMS[command]
            else:
                params = dict(list(params.items()) + list(XBMCMD.HARD_PARAMS[command].items()))

        data = {"method"  : XBMCMD.COMMANDS[command],
                "jsonrpc" : "2.0",
                "id"      : "XBMCMD"}
        if params is not None:
            data["params"] = params

        log.info(data)

        request = Request(self.URL, headers = XBMCMD.HEADERS, data = json.dumps(data).encode('utf-8'))
        handler = urlopen(request)
        return json.loads(handler.read().decode("utf-8"))

    #
    # -- Support --
    #

    def get_movie_names(self, text, line, begin, end):
        """Returns a list of movie name completions"""
        prefix = line.partition(' ')[2].lower()
        offset = len(prefix) - len(text)
        return [s[offset:] for s in self.movies.keys() if s.lower().startswith(prefix)]

    def complete_detail(self, *args):
        """Auto-complete function for the `detail` command"""
        return self.get_movie_names(*args)

    def get_id(self, line):
        try:
            if int(line):
                return int(line)
            else:
                return None
        except ValueError:
            candidates = [movie for movie in self.movies.keys() if movie.lower().startswith(line.lower())]
            if len(candidates) >= 1:
                return self.movies[candidates[0]]
            else:
                return None

    @staticmethod
    def check_result(result):
        if "result" in result:
            if result["result"] == "OK":
                log.info(result)
                return True
            else:
                log.error(result["result"])
                log.info(result)
                return False
        else:
            if "error" in result:
                log.error(result["error"]["message"])
            else:
                log.error("Failed to execute command")
            log.info(result)
            return False

    #
    # -- Commands ----
    #

    def default(self, line):
        try:
            check_result(self.send_request(line))
        except:
            log.error("Unknown syntax:", line)

    def do_terminate(self, line):
        """Stops XBMC"""
        XBMCMD.check_result(self.send_request("terminate"))

    def do_scan(self, line):
        """Initiates a scan of your library (in the background)"""
        XBMCMD.check_result(self.send_request("scan"))

    def do_clean(self, line):
        """Initiates a clean of your library (in the background). May take a long time to complete."""
        XBMCMD.check_result(self.send_request("clean"))

    def do_stop(self, line):
        """Stops the currently playing media"""
        XBMCMD.check_result(self.send_request("stop"))

    def do_pause(self, line):
        """Toggles pause for the currently playing media"""
        XBMCMD.check_result(self.send_request("pause"))

    def do_quit(self, line):
        """Quits"""
        print()
        return True
    do_EOF = do_quit # Enable Ctrl-d

    def do_play(self, line):
        """Starts playing the movie requested"""
        movie_id = self.get_id(line)
        if movie_id is None:
            log.error("You must pass a valid movie_id or a (prefix of a) movie title")
            return
        XBMCMD.check_result(self.send_request("play", [movie_id]))

    def do_movies(self, line):
        """List all movies (no arguments)"""
        result = self.send_request("movies")
        for movie in result["result"]["movies"]:
            print("%5d: %s (%s)" % (movie["movieid"], movie["label"], movie["year"]))

    def do_detail(self, line):
        """Outputs detail about a given movie. Pass the ID of the movie or (a prefix of) its title."""
        movie_id = self.get_id(line)
        if movie_id is None:
            log.error("You must pass a valid movie_id or a (prefix of a) movie title")
            return
        result = self.send_request("detail", [movie_id])
        details = result["result"]["moviedetails"]
        tokens = {'ID': 'movieid',
                  'Path'  : 'file',
                  'Trailer': 'trailer',
                  'iMDB' : 'imdbnumber',
                  'Added' : 'dateadded'}
        prefix = " " * (1 + max([len(key) for key in tokens.keys()]))
        print(prefix, "%s (%d)" % (details["label"], details["year"]))
        print(prefix, "=" * (7 + len(details["label"])))
        formats = {'iMDB' : "http://www.imdb.com/title/%s"}
        line_format = "%%%ds: %%s" % max(map(len, tokens.keys()))
        for label, key in tokens.items():
            value = details[key] if label not in formats else formats[label] % details[key]
            print(line_format % (label, value))

        for video in details["streamdetails"]["video"]:
            print(line_format % ("Ratio", "%sx%s" % (video["width"], video["height"])))


if __name__ == '__main__':
    log.basicConfig(format="%(levelname)s: %(message)s", level=log.ERROR)

    XBMC = XBMCMD()

    if len(sys.argv) > 1:
        XBMC.onecmd(" ".join(sys.argv[1:]))
    else:
        XBMC.cmdloop()
