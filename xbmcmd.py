import cmd
import json
from urllib.request import urlopen, Request
import sys


class XBMCMD(cmd.Cmd):
    HEADERS = {'content-type' : 'application/json'}
    COMMANDS = {"movies" : "VideoLibrary.GetMovies",
                "detail": "VideoLibrary.GetMovieDetails"}
    PARAMS = {"detail"  : {"movieid" : int}}
    HARD_PARAMS   = {"movies"   : {"properties" : ["year"]},
                     "detail" : {"properties" : ["trailer", "year", "streamdetails", "file", "imdbnumber", "dateadded"] }}
    prompt = "XBMC> "
    intro  = "Type `?` or `help` for command list"


    def __init__(self, *args, URL = "http://localhost:8080/jsonrpc"):
        self.URL = URL
        result = self.send_request("movies")
        self.movies = {movie["label"] : movie["movieid"] for movie in result["result"]["movies"]}
        #self.movies = [movie["label"] for movie in result["result"]["movies"]]

        super().__init__()

    def make_request(self, method, params = None, debug = False):
        """ Prepares an XBMC json request """
        data = {"method"  : method,
                "jsonrpc" : "2.0",
                "id"      : "XBMCMD"}
        if params is not None:
            data["params"] = params
        if debug:
            print(json.dumps(data))

        return Request(self.URL, headers = XBMCMD.HEADERS, data = json.dumps(data).encode('utf-8'))

    def send_request(self, command, args = []):
        params = None
        if command in XBMCMD.PARAMS.keys():
            params = {}
            index = 0
            for (extra, style) in XBMC.PARAMS[command].items():
                value = args[index]
                if type(style) == dict:
                    value = {}
                    for (extra_2, style_2) in style.items():
                        value_2 = sys.argv[index]
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

        request = self.make_request(XBMCMD.COMMANDS[command], params)
        handler = urlopen(request)
        return json.loads(handler.read().decode("utf-8"))

    #
    # -- Support --
    #

    def get_movie_names(self, text, line, begin, end):
        prefix = line.partition(' ')[2].lower()
        offset = len(prefix) - len(text)
        return [s[offset:] for s in self.movies.keys() if s.lower().startswith(prefix)]

    def complete_detail(self, *args):
        return self.get_movie_names(*args)


    #
    # -- Commands ----
    #

    def do_quit(self, args):
        """Quits"""
        print()
        return True
    do_EOF = do_quit



    def do_movies(self, line):
        """List all movies (no arguments)"""
        result = self.send_request("movies")
        for movie in result["result"]["movies"]:
            print("%5d: %s (%s)" % (movie["movieid"], movie["label"], movie["year"]))

    def do_detail(self, line):
        if line in self.movies:
            return self.do_detail(self.movies[line])
        else:
            try:
                if int(line) in self.movies.values():
                    movie_id = int(line)
                    result = self.send_request("detail", [movie_id])
                    details = result["result"]["moviedetails"]

                    tokens = {'ID': 'movieid',
                              'Title' : 'label',
                              'Path'  : 'file',
                              'Trailer': 'trailer',
                              'iMDB' : 'imdbnumber',
                              'Added' : 'dateadded'}
                    format = "%%%ds: %%s" % max(map(len, tokens.keys()))
                    for label, key in tokens.items():
                        print(format % (label, details[key]))

                    for video in details["streamdetails"]["video"]:
                        print(format % ("Ratio", "%sx%s" % (video["width"], video["height"])))
                else:
                    print("Bad movie ID")
            except ValueError:
                candidates = [movie for movie in self.movies.keys() if movie.lower().startswith(line.lower())]
                if len(candidates) >= 1:
                    return self.do_detail(candidates[0])
                else:
                    print("You must pass a valid movie name (or prefix) or movie_id")


if __name__ == '__main__':
    XBMC = XBMCMD()

    if len(sys.argv) > 1:
        XBMC.onecmd(" ".join(sys.argv[1:]))
    else:
        XBMC.cmdloop()
