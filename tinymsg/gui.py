import tkinter as tk
import pkg_resources
from multiprocessing import Process, Queue
import sys

# We use tkinter to create a GUI for our application.

# The GUI runs in a parent and starts child processes
# for the actual application logic.


# Server subprocess
def serve(host, port, queue):
    redirect_output(queue)
    from .tinymsg import create_app

    try:
        create_app().run(host=host, port=port, debug=False)
    except Exception as e:
        queue.put(str(e) + "\n")


# Request subprocess
def post(message, host, port, queue):
    redirect_output(queue)
    import requests

    try:
        requests.post(f"http://{host}:{port}", data=message, timeout=1).content.decode(
            "utf-8"
        )
    except Exception as e:
        queue.put(str(e) + "\n")


# GUI events callback functions


# Start server button GUI event
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


# Stop server button GUI event
def stop_server(event=None):
    global server_process
    server_process.terminate()
    stop_button.grid_forget()
    start_button.grid(row=0, column=2, rowspan=2)
    output_text.insert(tk.END, "Server stopped\n")
    output_text.see(tk.END)


# Send message button GUI event
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


# Close window GUI event
def on_closing():
    if server_process.is_alive():
        server_process.terminate()
    root.destroy()


# Redirect stdout and stderr from Process to a queue
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


# Read from queue and output to text widget
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


# Draw and run the GUI
def main():
    global root, host_entry, port_entry, start_button, stop_button
    global output_text, message_entry, send_button, scrollbar

    # Create window
    root = tk.Tk()
    root.title("TinyMsg")
    root.iconbitmap(pkg_resources.resource_filename("tinymsg", "icon.ico"))

    # Widgets are organized in a grid

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

    # Output text widget and scrollbar
    output_text = tk.Text(root)
    scrollbar = tk.Scrollbar(root)
    output_text.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=10, padx=5)
    scrollbar.grid(row=2, column=3, sticky="ns", pady=10)

    output_text.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=output_text.yview)

    message_label = tk.Label(root, text="Message:")
    message_label.grid(row=3, column=0)
    message_entry = tk.Entry(root)
    message_entry.grid(row=3, column=1, columnspan=2, sticky="ew")
    message_entry.bind("<Return>", send_message)

    send_button = tk.Button(root, text="Send Message", command=send_message)
    send_button.grid(row=4, column=1, columnspan=2, sticky="ew")

    # Configure grid
    root.grid_rowconfigure(2, weight=1)  # Row with output text will expand
    root.grid_rowconfigure(5, minsize=10)  # Empty row bottom of window
    root.grid_columnconfigure(2, weight=1)  # Column with output text will expand

    # Run the GUI
    root.mainloop()


# Run main() if this file is run directly
if __name__ == "__main__":
    main()
