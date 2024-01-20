import tkinter as tk
import pkg_resources
from multiprocessing import Process, Queue
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

def output_queue(queue, process):
    import queue as QueueModule
    try:
        while True:
            message = queue.get_nowait()
            output_text.insert(tk.END, message)
            output_text.see(tk.END)
    except QueueModule.Empty:
        if process.is_alive():
            root.after(100, lambda: output_queue(queue, process))
        else:
            while not queue.empty():
                message = queue.get()
                output_text.insert(tk.END, message)
                output_text.see(tk.END)

def serve(host, port, queue):
    redirect_output(queue)
    from .tinymsg import app
    app.run(host=host, port=port, debug=False)

def post(message, host, port, queue):
    redirect_output(queue)
    import requests
    try:
        requests.post(f'http://{host}:{port}', data=message, timeout=1).content.decode('utf-8')
    except Exception as e:
        queue.put(str(e) + '\n')

def start_server(event=None):
    global server_process
    host = host_entry.get()
    port = port_entry.get()
    queue = Queue()
    server_process = Process(target=serve, args=(host, port, queue))
    server_process.start()
    start_button.grid_forget()
    stop_button.grid(row=0, column=2, rowspan=2)
    output_queue(queue, server_process)

def stop_server(event=None):
    global server_process
    server_process.terminate()
    stop_button.grid_forget()
    start_button.grid(row=0, column=2, rowspan=2)
    output_text.insert(tk.END, "Server stopped\n")
    output_text.see(tk.END)

def send_message(event=None):
    message = message_entry.get()
    host = host_entry.get()
    port = port_entry.get()
    output_text.insert(tk.END, f"Sending message: {message}\n")
    queue = Queue()
    req_process = Process(target=post, args=(message, host, port, queue))
    req_process.start()
    output_queue(queue, req_process)
    message_entry.delete(0, tk.END)

def on_closing():
    if server_process.is_alive():
        server_process.terminate()
    root.destroy()


def draw():
    global root, host_entry, port_entry, start_button, stop_button, \
           output_text, message_entry, send_button, scrollbar

    root = tk.Tk()
    root.title("TinyMsg")
    root.iconbitmap(pkg_resources.resource_filename('tinymsg', 'icon.ico'))
    # root.iconbitmap('tinymsg/icon.ico')

    host_label = tk.Label(root, text="Host:")
    host_label.grid(row=0, column=0)
    host_entry = tk.Entry(root)
    host_entry.insert(0, "localhost")  # Default host value
    host_entry.grid(row=0, column=1)

    port_label = tk.Label(root, text="Port:")
    port_label.grid(row=1, column=0)
    port_entry = tk.Entry(root)
    port_entry.insert(0, "5000")  # Default port value
    port_entry.grid(row=1, column=1)

    start_button = tk.Button(root, text="Start Server", command=start_server)
    stop_button = tk.Button(root, text="Stop Server", command=stop_server)

    start_button.grid(row=0, column=2, rowspan=2)

    output_text = tk.Text(root)
    scrollbar = tk.Scrollbar(root)
    output_text.grid(row=2, column=0, columnspan=3, sticky='nsew', pady=10, padx=5)
    scrollbar.grid(row=2, column=3, sticky='ns', pady=10)

    output_text.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=output_text.yview)

    message_label = tk.Label(root, text="Message:")
    message_label.grid(row=3, column=0)
    message_entry = tk.Entry(root)
    message_entry.grid(row=3, column=1, columnspan=2, sticky='ew')
    message_entry.bind('<Return>', send_message)

    send_button = tk.Button(root, text="Send Message", command=send_message)
    send_button.grid(row=4, column=1, columnspan=2, sticky='ew')

    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(5, minsize=10)
    root.grid_columnconfigure(2, weight=1)

def main():
    draw()
    root.mainloop()

if __name__ == '__main__':
    main()