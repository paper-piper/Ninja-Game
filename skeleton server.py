import socket
import threading
import json


def client_thread(conn, addr, all_clients):
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            # Broadcast received data to all clients
            for client in all_clients:
                if client != conn:
                    client.sendall(data)
        except:
            break
    conn.close()


def start_server():
    host = 'localhost'
    port = 12345
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    all_clients = []
    while True:
        conn, addr = server_socket.accept()
        all_clients.append(conn)
        threading.Thread(target=client_thread, args=(conn, addr, all_clients)).start()


if __name__ == '__main__':
    start_server()
