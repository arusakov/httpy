import os, select, socket, sys

if len(sys.argv) < 2:
	print "ERROR port"
	exit(1)

host = '0.0.0.0'
port = (int)(sys.argv[1])
connQueue = 10

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
	sock.bind((host, port))
except socket.error:
	print "ERROR socket bind"
	exit(1)

sock.listen(connQueue)

sock.close()

print "OK"