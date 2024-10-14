import tkinter as tk 
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
import pandas as pd
from datetime import datetime, timezone
import threading
import queue
import time

# to compile pyinstaller -wF --hidden-import 'babel.numbers' file.py

# Set up a queue for thread communication
log_queue = queue.Queue()

# Function to log messages to the GUI console
def log_message(message):
    log_console.config(state=tk.NORMAL)  # Enable editing
    log_console.insert(tk.END, message + '\n')  # Add the message
    log_console.config(state=tk.DISABLED)  # Disable editing
    log_console.see(tk.END)  # Scroll to the end

# Function to process messages from the queue
def process_log_queue():
    try:
        while True:
            message = log_queue.get_nowait()
            log_message(message)
    except queue.Empty:
        pass
    app.after(100, process_log_queue)  # Check again after 100 ms

# Function to open and read the CSV file
def open_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        csv_path_entry.delete(0, tk.END)
        csv_path_entry.insert(0, file_path)
        log_queue.put(f"CSV file selected: {file_path}")
        threading.Thread(target=load_csv_headers, args=(file_path,), daemon=True).start()
    else:
        messagebox.showerror("File Error", "No file selected")

# Function to load the CSV headers and populate the dropdown
def load_csv_headers(file_path):
    try:
        df = pd.read_csv(file_path, nrows=0)  # Read only the headers
        columns = df.columns.tolist()
        if not columns:
            raise ValueError("CSV has no columns")
        column_dropdown['menu'].delete(0, 'end')
        for col in columns:
            column_dropdown['menu'].add_command(label=col, command=tk._setit(column_var, col))
        column_var.set(columns[0])  # Set default to the first column
        log_queue.put(f"Loaded columns: {columns}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV: {e}")
        log_queue.put(f"Error reading CSV: {e}")

# Function to set the output file location
def set_output_file():
    output_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if output_path:
        output_path_entry.delete(0, tk.END)
        output_path_entry.insert(0, output_path)
        log_queue.put(f"Output file selected: {output_path}")
    else:
        messagebox.showerror("File Error", "No output file selected")

# Function to combine selected date and time
def get_datetime(date_entry, hour_combobox, minute_combobox, second_combobox):
    date_str = date_entry.get_date().strftime('%Y-%m-%d')
    time_str = f"{hour_combobox.get()}:{minute_combobox.get()}:{second_combobox.get()}"
    log_queue.put(f"Combining date and time: {date_str} {time_str}")
    return f"{date_str} {time_str}"

# Function to filter the CSV based on time range
def filter_csv():
    file_path = csv_path_entry.get()
    output_path = output_path_entry.get()
    time_column = column_var.get()

    start_datetime_str = get_datetime(start_date_entry, start_hour_combo, start_minute_combo, start_second_combo)
    end_datetime_str = get_datetime(end_date_entry, end_hour_combo, end_minute_combo, end_second_combo)

    try:
        start_time = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        end_time = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        log_queue.put(f"Filtering records from {start_time} to {end_time}")
        threading.Thread(target=perform_filtering, args=(file_path, output_path, time_column, start_time, end_time), daemon=True).start()
    except ValueError:
        messagebox.showerror("Time Error", "Time format must be YYYY-MM-DD HH:MM:SS")
        log_queue.put("Invalid time format")
        return

def perform_filtering(file_path, output_path, time_column, start_time, end_time):
    try:
        df = pd.read_csv(file_path)
        log_queue.put("CSV file read successfully")

        if time_column not in df.columns:
            log_queue.put(f"Column '{time_column}' not found in the CSV file.")
            messagebox.showerror("Column Error", f"Column '{time_column}' not found in the CSV file.")
            return

        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z', 
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%m-%d-%Y %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d/%m/%Y %H:%M',
            '%m-%d-%Y %H:%M',
            '%Y/%m/%d %H:%M',
        ]
        
        def parse_datetime(x):
            for fmt in date_formats:
                try:
                    return datetime.strptime(x, fmt).astimezone(tz=timezone.utc)
                except (ValueError, TypeError):
                    continue
            return pd.NaT

        df[time_column] = df[time_column].apply(parse_datetime)

        filtered_df = df[(df[time_column] >= start_time) & (df[time_column] <= end_time)]
        
        if filtered_df.empty:
            log_queue.put("No records found in the specified time range")
            messagebox.showwarning("No Records", "No records found in the specified time range")
            return

        filtered_df.to_csv(output_path, index=False)
        messagebox.showinfo("Success", "Filtered CSV saved successfully!")
        log_queue.put(f"Filtered CSV saved successfully: {output_path}")

    except Exception as e:
        log_queue.put(f"Error filtering CSV: {e}")
        messagebox.showerror("Error", f"Error filtering CSV: {e}")

# GUI Setup
app = tk.Tk()
app.title("CSV Time Filter Tool")
app.geometry("600x700")
app.configure(bg="#f7f7f7")

# Title Label
title_label = tk.Label(app, text="CSV Time Filter Tool", font=("Arial", 16, "bold"), bg="#f7f7f7")
title_label.pack(pady=20)

# CSV file input
csv_frame = tk.Frame(app, bg="#f7f7f7")
csv_frame.pack(pady=10)
csv_path_label = tk.Label(csv_frame, text="CSV File:", font=("Arial", 12), bg="#f7f7f7")
csv_path_label.grid(row=0, column=0, sticky="e", padx=10)
csv_path_entry = tk.Entry(csv_frame, width=40)
csv_path_entry.grid(row=0, column=1, padx=10)
csv_browse_button = tk.Button(csv_frame, text="Browse", command=open_csv_file)
csv_browse_button.grid(row=0, column=2, padx=10)

# Output file location
output_frame = tk.Frame(app, bg="#f7f7f7")
output_frame.pack(pady=10)
output_path_label = tk.Label(output_frame, text="Output File:", font=("Arial", 12), bg="#f7f7f7")
output_path_label.grid(row=0, column=0, sticky="e", padx=10)
output_path_entry = tk.Entry(output_frame, width=40)
output_path_entry.grid(row=0, column=1, padx=10)
output_browse_button = tk.Button(output_frame, text="Save As", command=set_output_file)
output_browse_button.grid(row=0, column=2, padx=10)

# Start Date/Time inputs
start_frame = tk.Frame(app, bg="#f7f7f7")
start_frame.pack(pady=10)
start_date_label = tk.Label(start_frame, text="Start Date:", font=("Arial", 12), bg="#f7f7f7")
start_date_label.grid(row=0, column=0, sticky="e", padx=10)
start_date_entry = DateEntry(start_frame, width=15, date_pattern='y-mm-dd', background='darkblue', foreground='white', borderwidth=2)
start_date_entry.grid(row=0, column=1, padx=10)

# Start Time (hours, minutes, seconds)
start_time_frame = tk.Frame(app, bg="#f7f7f7")
start_time_frame.pack(pady=10)
tk.Label(start_time_frame, text="Start Time:", font=("Arial", 12), bg="#f7f7f7").grid(row=0, column=0, padx=10)

start_hour_combo = ttk.Combobox(start_time_frame, width=3, values=[f"{i:02}" for i in range(24)], state="readonly")
start_hour_combo.grid(row=0, column=1)
start_hour_combo.set("00")

start_minute_combo = ttk.Combobox(start_time_frame, width=3, values=[f"{i:02}" for i in range(60)], state="readonly")
start_minute_combo.grid(row=0, column=2)
start_minute_combo.set("00")

start_second_combo = ttk.Combobox(start_time_frame, width=3, values=[f"{i:02}" for i in range(60)], state="readonly")
start_second_combo.grid(row=0, column=3)
start_second_combo.set("00")

# End Date/Time inputs
end_frame = tk.Frame(app, bg="#f7f7f7")
end_frame.pack(pady=10)
end_date_label = tk.Label(end_frame, text="End Date:", font=("Arial", 12), bg="#f7f7f7")
end_date_label.grid(row=0, column=0, sticky="e", padx=10)
end_date_entry = DateEntry(end_frame, width=15, date_pattern='y-mm-dd', background='darkblue', foreground='white', borderwidth=2)
end_date_entry.grid(row=0, column=1, padx=10)

# End Time (hours, minutes, seconds)
end_time_frame = tk.Frame(app, bg="#f7f7f7")
end_time_frame.pack(pady=10)
tk.Label(end_time_frame, text="End Time:", font=("Arial", 12), bg="#f7f7f7").grid(row=0, column=0, padx=10)

end_hour_combo = ttk.Combobox(end_time_frame, width=3, values=[f"{i:02}" for i in range(24)], state="readonly")
end_hour_combo.grid(row=0, column=1)
end_hour_combo.set("23")

end_minute_combo = ttk.Combobox(end_time_frame, width=3, values=[f"{i:02}" for i in range(60)], state="readonly")
end_minute_combo.grid(row=0, column=2)
end_minute_combo.set("59")

end_second_combo = ttk.Combobox(end_time_frame, width=3, values=[f"{i:02}" for i in range(60)], state="readonly")
end_second_combo.grid(row=0, column=3)
end_second_combo.set("59")

# Dropdown for selecting the Time and Date column
column_frame = tk.Frame(app, bg="#f7f7f7")
column_frame.pack(pady=10)
column_label = tk.Label(column_frame, text="Select Time and Date Column:", font=("Arial", 12), bg="#f7f7f7")
column_label.grid(row=0, column=0, sticky="e", padx=10)
column_var = tk.StringVar(app)
column_dropdown = ttk.OptionMenu(column_frame, column_var, "")
column_dropdown.grid(row=0, column=1, padx=10)

# Filter button
filter_button = tk.Button(app, text="Filter CSV", font=("Arial", 12, "bold"), bg="#007acc", fg="black", width=15, command=filter_csv)
filter_button.pack(pady=30)

# Log Console
log_frame = tk.Frame(app, bg="#f7f7f7")
log_frame.pack(pady=10)
log_label = tk.Label(log_frame, text="Log Console:", font=("Arial", 12), bg="#f7f7f7")
log_label.pack()
log_console = tk.Text(log_frame, width=70, height=10, bg="#eaeaea", state=tk.DISABLED)
log_console.pack(padx=10, pady=5)

# Start processing log queue
process_log_queue()

# Run the GUI
app.mainloop()
