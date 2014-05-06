import os
import socket
import json
import datetime
import re

class HttpResponse(object):
    new_line = "\r\n"
    http = "HTTP"

    date_format = "%a, %d %b %Y %H:%M:%S GMT"
    index_file = None

    code_to_status = {
        200: "OK",
        301: "Moved Permanently",
        302: "Found",
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error"
    }

    ext_to_mime = {
        "txt": "text/plain",
        "html": "text/html",
        "css": "text/css",
        "js": "application/x-javascript",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "swf": "application/x-shockwave-flash"
    }

    def __init__(self, version):
        self._version = version
        self._code = 200
        self._headers = {
            "Date": datetime.datetime.utcnow().strftime(HttpResponse.date_format),
            #"Connection": "close",
            "Server": "httpy/0.1"
        }
        self._data = ""
        self._nodata = False

    def set_nodata(self):
        self._nodata = True

    def status(self, version, code):
        return HttpResponse.http + "/" + version + " " + str(code) + " " + HttpResponse.code_to_status[code]

    def set_code(self, code):
        self._code = code

    def set_index(self, file):
        HttpResponse.index_file = file

    def headers(self):
        hdr = ""
        for i in self._headers:
            hdr += HttpResponse.new_line + i + ": " + self._headers[i]
        return hdr

    def read(self, path, index_file):
        directory = False
        if path[-1] == "/":
            directory = True
            path += index_file

        self._data = ""

        if not os.path.exists(path):
            if directory:
                self.set_code(403)
            else:
                self.set_code(404)
            return

        self._headers["Content-Type"] = HttpResponse.ext_to_mime[os.path.splitext(path)[1][1:].lower()]
        self._headers["Date"] = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime(HttpResponse.date_format)

        if self._nodata:
            self._set_size(os.path.getsize(path))
            return

        fs = open(path, "r")
        self._data = fs.read()
        fs.close()
        self._set_size(len(self._data))

    def _set_size(self, size):
        self._headers["Content-Length"] = str(size)

    def __str__(self):
        return self.status(self._version, self._code) + self.headers() + HttpResponse.new_line * 2 + self._data


class HttpRequest:
    methods = set(["GET", "HEAD"])
    version = "1.0"

    proc_enc_pattern = re.compile("(%..)")

    def __init__(self, input):
        first_line = input[:input.find("\n")].rstrip()
        fspace = first_line.find(" ")
        lspace = first_line.rfind(" ")

        self._response = None

        if len(input) < 14:
            #print first_line
            self._method = None
            self._response = HttpResponse(HttpRequest.version)
            self._response.set_code(400)
            return

        self._method = first_line[:fspace].upper()

        if self._method not in HttpRequest.methods:
            self._response = HttpResponse(HttpRequest.version)
            self._response.set_code(405)
            return

        self._http = first_line[lspace+1:]
        self._path = first_line[fspace + 1:lspace]

        query_pos = self._path.find("?")
        if query_pos != -1:
            self._path = self._path[:self._path.find("?")]

        self._path = self._path.replace("+", " ")
        precents = HttpRequest.proc_enc_pattern.findall(self._path)
        for r in precents:
            self._path = self._path.replace(r, chr(int(r[1:], 16)))

        pths = self._path.split("/")[1:]
        in_root = 0
        for p in pths:
            if p == "..":
                in_root -= 1
            elif len(p) > 0 and p != ".":
                in_root += 1

        if in_root < 0:
            self._response = HttpResponse(HttpRequest.version)
            self._response.set_code(403)

    def read(self, buff):
        self._input += buff

    def path(self):
        return self._path

    def method(self):
        return self._method

    def ready(self):
        return self._response is not None

    def response(self):
        if not self.ready():
            self._response = HttpResponse(HttpRequest.version)
        if self._method == "HEAD":
            self._response.set_nodata()
        return self._response

class ServerSettings():
    def __init__(self, filename):
        settings = json.load(open(filename, "r"))

        server = settings["server"]

        self._host = server["host"]
        self._port = server["port"]
        self._queue = server["queue"]
        self._buffer = server["buffer"]
        self._proc = server["processes"]

        self._document_root = settings["document"]["root"]
        if not os.path.exists(self._document_root):
            raise NameError("ERROR 20 DOCUMENT_ROOT not exist")
        self._index_file = settings["document"]["index"]

    def proc(self):
        return self._proc

    def port(self):
        return self._port

    def host(self):
        return self._host

    def host_and_port(self):
        return (self._host, self._port)

    def conn_queue(self):
        return self._queue

    def buffer(self):
        return self._buffer

    def document_root(self):
        return self._document_root

    def index(self):
        return self._index_file

try:
    settings = ServerSettings("settings.json")
except:
    print "ERROR 2 Settings Error"
    exit(1)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.bind(settings.host_and_port())
except socket.error:
    print "ERROR 1 socket bind"
    exit(1)

sock.listen(settings.conn_queue())

for i in range(settings.proc()):
    pid = os.fork()

rn_re = re.compile("\r?\n\r?\n")

while True:
    conn, addr = sock.accept()

    data = ""
    data_buf = ""
    header_pos = None

    while not header_pos:
        data_buf = conn.recv(settings.buffer())
        if not data_buf:
            break
        data += data_buf
        header_pos = rn_re.search(data)

    if not header_pos:
        request = HttpRequest(data)
    else:
        request = HttpRequest(data[:header_pos.start()])

    if request.ready():
        conn.sendall((str)(request.response()))
        conn.close()
        continue

    response = request.response()
    response.read(settings.document_root() + request.path(), settings.index())

    conn.sendall((str)(response))
    conn.close()
