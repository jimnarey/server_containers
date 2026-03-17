#!/usr/bin/env python3

import os
import logging
import subprocess
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

LOCAL_PATH = "/meganz_local"
REMOTE_PATH = os.getenv("MEGANZ_REMOTE")
SYNC_CMD = ["/usr/bin/rclone", "sync", LOCAL_PATH, f"mega:{REMOTE_PATH}", "--verbose",]

DEBOUNCE_SECONDS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class ChangeHandler(FileSystemEventHandler):
    """Debounced filesystem event handler that triggers rclone sync."""
    
    def __init__(self):
        super().__init__()
        self.timer = None
        self.lock = threading.Lock()
    
    def on_any_event(self, event):
        """Called for any filesystem event."""
        if event.is_directory:
            return
        
        logging.info(f"Change detected: {event.event_type} {event.src_path}")
        self.schedule_sync()
    
    def schedule_sync(self):
        """Schedule a sync after debounce period, canceling previous timers."""
        with self.lock:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(DEBOUNCE_SECONDS, self.run_sync)
            self.timer.start()
    
    def run_sync(self):
        """Execute the rclone sync command."""
        logging.info(f"Running sync: {' '.join(SYNC_CMD)}")
        try:
            process = subprocess.Popen(
                SYNC_CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output line by line through logger
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    logging.info(f"rclone: {line}")
            
            process.wait()
            
            if process.returncode == 0:
                logging.info("Sync completed successfully")
            else:
                logging.error(f"Sync failed with code {process.returncode}")
        except Exception as e:
            logging.error(f"Sync error: {e}")


def main():
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, LOCAL_PATH, recursive=True)
    observer.start()
    logging.info(f"Watching {LOCAL_PATH}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()