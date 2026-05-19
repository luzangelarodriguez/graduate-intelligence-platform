import http.server, socketserver, os
os.chdir(r"C:\Users\SoporteTI\Desktop\SOFTWARE\graduate_intelligence_platform")
handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("127.0.0.1", 4173), handler) as httpd:
    print("serving")
    httpd.serve_forever()
