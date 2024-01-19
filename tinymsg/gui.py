import tkinter as tk
from multiprocessing import Process, Queue
import queue as QueueModule
import sys

def redirect_output(queue):
    class Writer:
        def __init__(self, queue):
            self.queue = queue

        def write(self, message):
            self.queue.put(message)

        def flush(self):
            pass
    writer = Writer(queue)
    sys.stdout = writer
    sys.stderr = writer

def serve(host, port, queue):
    from .tinymsg import app
    redirect_output(queue)
    app.run(host=host, port=port, debug=False)

def post(message, host, port, queue):
    import requests
    redirect_output(queue)
    requests.post(f'http://{host}:{port}', data=message)

def start_server():
    global server_process
    host = host_entry.get()
    port = port_entry.get()
    queue = Queue()
    server_process = Process(target=serve, args=(host, port, queue))
    server_process.start()
    start_button.grid_forget()
    stop_button.grid(row=5, column=0, columnspan=2)

    def read_queue():
        while True:
            try:
                message = queue.get_nowait()
                output_text.insert(tk.END, message)
                output_text.see(tk.END)
            except QueueModule.Empty:
                root.after(100, read_queue)
                return
        root.after(100, read_queue)

    read_queue()

def stop_server():
    global server_process
    server_process.terminate()
    stop_button.grid_forget()
    start_button.grid(row=5, column=0, columnspan=2)

def send_message():
    message = message_entry.get()
    host = host_entry.get()
    port = port_entry.get()
    queue = Queue()
    req_process = Process(target=post, args=(message, host, port, queue))
    req_process.start()
    
    def read_queue():
        while True:
            try:
                message = queue.get_nowait()
                output_text.insert(tk.END, message)
                output_text.see(tk.END)
            except QueueModule.Empty:
                root.after(100, read_queue)
                return
        root.after(100, read_queue)

    read_queue()

root = tk.Tk()
root.title("TinyMsg")
root.iconbitmap('icon.ico')

host_label = tk.Label(root, text="Host:")
host_label.grid(row=0, column=0)
host_entry = tk.Entry(root)
host_entry.insert(0, "localhost")  # Default host value
host_entry.grid(row=1, column=0)

port_label = tk.Label(root, text="Port:")
port_label.grid(row=2, column=0)
port_entry = tk.Entry(root)
port_entry.insert(0, "5000")  # Default port value
port_entry.grid(row=3, column=0)

message_label = tk.Label(root, text="Message:")
message_label.grid(row=0, column=1)
message_entry = tk.Entry(root)
message_entry.grid(row=1, column=1)

send_button = tk.Button(root, text="Send Message", command=send_message)
send_button.grid(row=2, column=1)

output_text = tk.Text(root)
scrollbar = tk.Scrollbar(root)
output_text.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=10, padx=5)
scrollbar.grid(row=4, column=2, sticky='ns', pady=10)

output_text.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=output_text.yview)

start_button = tk.Button(root, text="Start Server", command=start_server)
stop_button = tk.Button(root, text="Stop Server", command=stop_server)

start_button.grid(row=5, column=0, columnspan=2)

root.grid_rowconfigure(4, weight=1)
root.grid_rowconfigure(6, minsize=10)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

def main():
    root.mainloop()

if __name__ == '__main__':
    main()