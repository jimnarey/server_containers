#!/usr/bin/env python3

import os
import logging
import subprocess
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

LOCAL_PATH = "/meganz_local"
REMOTE_PATH = os.getenv("MEGANZ_REMOTE")
SYNC_CMD = ["/usr/bin/rclone", "sync", LOCAL_PATH, f"mega:{REMOTE_PATH}", "--exclude", ".debris/**", "--verbose",]

DEBOUNCE_SECONDS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class ChangeHandler(FileSystemEventHandler):
    """Debounced filesystem event handler that triggers rclone sync."""
    
    def __init__(self):
        super().__init__()
        self.last_event_time = None
        self.sync_running = False
        self.sync_queued = False
    
    def on_any_event(self, event):
        """Called for any filesystem event."""
        if event.is_directory:
            return
        
        logging.info(f"Change detected: {event.event_type} {event.src_path}")
        
        if self.sync_running:
            if not self.sync_queued:
                logging.info("Sync already running, queueing one more run")
                self.sync_queued = True
        else:
            self.last_event_time = time.time()
    
    def should_run_sync(self):
        """Check if enough time has passed since last event to run sync."""
        if self.sync_running:
            return False
        if self.last_event_time is None:
            return False
        return time.time() - self.last_event_time >= DEBOUNCE_SECONDS
    
    def run_sync(self):
        """Execute the rclone sync command."""
        self.sync_running = True
        self.sync_queued = False
        self.last_event_time = None
        
        logging.info(f"Running sync: {' '.join(SYNC_CMD)}")
        try:
            process = subprocess.Popen(
                SYNC_CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
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
        finally:
            self.sync_running = False
            if self.sync_queued:
                logging.info("Queued sync will run after debounce period")
                self.last_event_time = time.time()
                self.sync_queued = False


def main():
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, LOCAL_PATH, recursive=True)
    observer.start()
    logging.info(f"Watching {LOCAL_PATH}")
    try:
        while True:
            if event_handler.should_run_sync():
                event_handler.run_sync()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()