import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import http.server
import socketserver
import threading
import os

class SimpleWebServer:
    def __init__(self, directory, port, log_output_widget, start_button, stop_button, root_window):
        self.directory = directory
        self.port = port
        self.httpd = None
        self.log_output_widget = log_output_widget
        self.start_button = start_button
        self.stop_button = stop_button
        self.root = root_window # To safely update GUI from thread

    def run(self):
        original_dir = os.getcwd() # Save current directory
        try:
            os.chdir(self.directory)
            # Need to define log_output_widget and root on the Handler's server instance
            # so the custom log_message can access them.
            
            class CustomHandler(http.server.SimpleHTTPRequestHandler):
                # Class variable to hold log_output, set by the TCPServer instance
                log_output_ref = None
                root_ref = None

                def log_message(self, format, *args):
                    message = "%s - - [%s] %s\n" % (
                        self.address_string(),
                        self.log_date_time_string(),
                        format % args
                    )
                    if CustomHandler.log_output_ref and CustomHandler.root_ref:
                        # Ensure GUI updates are thread-safe
                        CustomHandler.root_ref.after(0, lambda: CustomHandler.log_output_ref.insert(tk.END, message))
                        CustomHandler.root_ref.after(0, lambda: CustomHandler.log_output_ref.see(tk.END))


            # Pass the log_output_widget and root to the TCPServer instance,
            # which can then be accessed by the handler.
            # We'll set these as attributes on the server object itself.
            
            server_address = ("", self.port)
            self.httpd = socketserver.TCPServer(server_address, CustomHandler)
            
            # Make log_output_widget and root accessible to the handler via the server instance
            self.httpd.log_output_ref = self.log_output_widget
            self.httpd.root_ref = self.root
            
            # Now set the class variables on CustomHandler. This is a bit of a workaround
            # for how SimpleHTTPRequestHandler is structured.
            CustomHandler.log_output_ref = self.log_output_widget
            CustomHandler.root_ref = self.root

            self.log_output_widget.insert(tk.END, f"Serving at http://localhost:{self.port} in directory: {self.directory}\n")
            self.log_output_widget.see(tk.END)
            self.httpd.serve_forever()

        except OSError as e:
            error_message = f"Error starting server on port {self.port}: {e}\n"
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.log_output_widget.insert(tk.END, error_message))
                self.root.after(0, lambda: self.log_output_widget.see(tk.END))
                self.root.after(0, lambda: messagebox.showerror("Server Error", f"Could not start server on port {self.port}: {e}"))
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}\n"
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.log_output_widget.insert(tk.END, error_message))
                self.root.after(0, lambda: self.log_output_widget.see(tk.END))
                self.root.after(0, lambda: messagebox.showerror("Unexpected Error", f"An unexpected error occurred: {e}"))
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
        finally:
            os.chdir(original_dir) # Change back to original directory
            self.httpd = None # Ensure httpd is None if server stops/fails

    def stop(self):
        if self.httpd:
            self.log_output_widget.insert(tk.END, "Attempting to stop server...\n")
            self.log_output_widget.see(tk.END)
            
            # Shutdown must happen in a separate thread because serve_forever() blocks
            shutdown_thread = threading.Thread(target=self.httpd.shutdown)
            shutdown_thread.daemon = True # Allow main program to exit even if this thread is running
            shutdown_thread.start()
            
            # Wait for the shutdown thread to complete, but with a timeout
            shutdown_thread.join(timeout=5) 

            try:
                 # server_close() should be called after shutdown() has completed
                self.httpd.server_close()
                self.log_output_widget.insert(tk.END, "Server stopped.\n")
            except Exception as e:
                self.log_output_widget.insert(tk.END, f"Error during server_close: {e}\n")
            finally:
                self.log_output_widget.see(tk.END)
                self.httpd = None # Mark as stopped


server_instance = None
root = None 
directory_path_var = None
port_entry_widget = None
log_text_area_widget = None
start_button_widget = None
stop_button_widget = None
status_label_widget = None

def select_directory():
    global directory_path_var
    selected_dir = filedialog.askdirectory()
    if selected_dir:
        directory_path_var.set(selected_dir)
        update_status(f"Directory selected: {directory_path_var.get()}")

def start_server():
    global server_instance, root, directory_path_var, port_entry_widget, log_text_area_widget
    global start_button_widget, stop_button_widget

    directory = directory_path_var.get()
    port_str = port_entry_widget.get()

    if not directory:
        update_status("Please select a directory.")
        messagebox.showerror("Error", "Please select a directory to serve.")
        return

    if not port_str.isdigit():
        update_status("Please enter a valid port number.")
        messagebox.showerror("Error", "Please enter a valid port number.")
        return

    port = int(port_str)
    if 1 <= port <= 65535:
        server_instance = SimpleWebServer(directory, port, log_text_area_widget, start_button_widget, stop_button_widget, root)
        
        # Run the server in a separate thread so the GUI doesn't freeze
        server_thread = threading.Thread(target=server_instance.run)
        server_thread.daemon = True # Allows main program to exit even if server thread is running
        server_thread.start()
        
        update_status(f"Starting server on port {port}...")
        start_button_widget.config(state=tk.DISABLED)
        stop_button_widget.config(state=tk.NORMAL)
    else:
        update_status("Port number must be between 1 and 65535.")
        messagebox.showerror("Error", "Port number must be between 1 and 65535.")

def stop_server():
    global server_instance, start_button_widget, stop_button_widget
    if server_instance and server_instance.httpd:
        server_instance.stop()
        # server_instance will set its httpd to None
        # The buttons and status will be updated after stop() is confirmed or on error by the server class.
        update_status("Server stopped.")
        start_button_widget.config(state=tk.NORMAL)
        stop_button_widget.config(state=tk.DISABLED)
        server_instance = None # Clear the instance
    else:
        update_status("No server is running or already stopped.")
        start_button_widget.config(state=tk.NORMAL)
        stop_button_widget.config(state=tk.DISABLED)


def update_status(message):
    global status_label_widget
    if status_label_widget:
        status_label_widget.config(text=message)

def on_closing():
    global server_instance, root
    if server_instance and server_instance.httpd:
        if messagebox.askokcancel("Quit", "Server is running. Do you want to stop it and quit?"):
            stop_server() # Attempt to stop the server
            # Wait a moment for server to potentially stop
            root.after(1000, root.destroy) # Give some time for server to stop
        else:
            return # Don't close if user cancels
    else:
        root.destroy()


def main():
    global root, directory_path_var, port_entry_widget, log_text_area_widget
    global start_button_widget, stop_button_widget, status_label_widget

    root = tk.Tk()
    root.title("Simple Local Server Manager")

    directory_path_var = tk.StringVar()

    # Directory Selection
    dir_frame = tk.Frame(root)
    dir_frame.pack(pady=10, padx=10, fill=tk.X)
    dir_label = tk.Label(dir_frame, text="Web App Directory:")
    dir_label.pack(side=tk.LEFT)
    dir_entry = tk.Entry(dir_frame, textvariable=directory_path_var, width=50)
    dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))
    dir_button = tk.Button(dir_frame, text="Browse", command=select_directory)
    dir_button.pack(side=tk.LEFT, padx=5)

    # Port Configuration
    port_frame = tk.Frame(root)
    port_frame.pack(pady=5, padx=10, fill=tk.X)
    port_label = tk.Label(port_frame, text="Port:")
    port_label.pack(side=tk.LEFT)
    port_entry_widget = tk.Entry(port_frame, width=10)
    port_entry_widget.insert(0, "8000")  # Default port
    port_entry_widget.pack(side=tk.LEFT, padx=5)

    # Control Buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    start_button_widget = tk.Button(button_frame, text="Start Server", command=start_server)
    start_button_widget.pack(side=tk.LEFT, padx=5)
    stop_button_widget = tk.Button(button_frame, text="Stop Server", command=stop_server, state=tk.DISABLED)
    stop_button_widget.pack(side=tk.LEFT, padx=5)

    # Log Output Area
    log_label = tk.Label(root, text="Server Output:")
    log_label.pack(padx=10, anchor=tk.W)
    log_text_area_widget = scrolledtext.ScrolledText(root, height=15, width=80)
    log_text_area_widget.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
    # log_text_area_widget.config(state=tk.DISABLED) # Should be normal to insert, but not user-editable. This makes it read-only by user.

    # Status Label
    status_label_widget = tk.Label(root, text="Server not running.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label_widget.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)
    
    root.protocol("WM_DELETE_WINDOW", on_closing) # Handle window close button
    root.mainloop()

if __name__ == "__main__":
    main()