import os, socket, sys

if len(sys.argv) < 2:
	print "ERROR port"
	exit(1)

host = ""
port = (int)(sys.argv[1])
connQueue = 10
connBuffer = 2048

count = 0;

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
	sock.bind((host, port))
except socket.error:
	print "ERROR socket bind"
	exit(1)

sock.listen(connQueue)

pid = os.fork()

while 1:
	conn, addr = sock.accept()

	count += 1
	print count

	while 1:
		data = conn.recv(connBuffer)
		if not data or data.strip() == "quit":
			break
		conn.sendall(str(pid) + " " + data)
	conn.close()
	