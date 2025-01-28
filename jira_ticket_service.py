import pystray
from PIL import Image, ImageDraw
import threading
import time
from datetime import datetime
from jira_tickets import process_file

class JiraTicketService:
    def __init__(self):
        self.interval = 300  # 5 minutes default
        self.running = False
        self.last_run = None
        self.processing = False
        self.icon = None
        self.setup_tray()

    def create_icon(self):
        """Create a simple icon - a colored circle"""
        width = 64
        height = 64
        color = (0, 128, 255)  # Blue color
        
        image = Image.new('RGB', (width, height), (255, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.ellipse([8, 8, width-8, height-8], fill=color)
        
        return image

    def setup_tray(self):
        """Setup the system tray icon and menu"""
        image = self.create_icon()
        
        menu = (
            pystray.MenuItem("Status", self.show_status, default=True),
            pystray.MenuItem("Process Now", self.process_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Set Interval", (
                pystray.MenuItem("1 minute", lambda: self.set_interval(60)),
                pystray.MenuItem("5 minutes", lambda: self.set_interval(300)),
                pystray.MenuItem("15 minutes", lambda: self.set_interval(900)),
                pystray.MenuItem("30 minutes", lambda: self.set_interval(1800)),
                pystray.MenuItem("1 hour", lambda: self.set_interval(3600))
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.stop)
        )
        
        self.icon = pystray.Icon("JiraTickets", image, "Jira Ticket Service", menu)

    def set_interval(self, seconds):
        """Change the processing interval"""
        self.interval = seconds
        self.show_status()

    def show_status(self):
        """Show current status in a notification"""
        status = []
        status.append(f"Service: {'Running' if self.running else 'Stopped'}")
        status.append(f"Interval: {self.interval//60} minutes")
        if self.last_run:
            status.append(f"Last run: {self.last_run.strftime('%H:%M:%S')}")
        if self.processing:
            status.append("Currently processing tickets...")
        
        self.icon.notify("\n".join(status), "Jira Ticket Service Status")

    def process_now(self):
        """Manually trigger ticket processing"""
        if not self.processing:
            threading.Thread(target=self.process_tickets, daemon=True).start()

    def process_tickets(self):
        """Process tickets and update status"""
        if self.processing:
            return
        
        try:
            self.processing = True
            self.icon.icon = self.create_processing_icon()
            process_file(r"F:\Users\dubba\Documents\Obsidian\Default\_GTD\tickets.md")
            self.last_run = datetime.now()
        except Exception as e:
            self.icon.notify(f"Error processing tickets: {str(e)}", "Error")
        finally:
            self.processing = False
            self.icon.icon = self.create_icon()

    def create_processing_icon(self):
        """Create an icon indicating processing status"""
        width = 64
        height = 64
        color = (255, 165, 0)  # Orange color for processing
        
        image = Image.new('RGB', (width, height), (255, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.ellipse([8, 8, width-8, height-8], fill=color)
        
        return image

    def run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            if not self.processing:
                self.process_tickets()
            time.sleep(self.interval)

    def start(self):
        """Start the service"""
        self.running = True
        threading.Thread(target=self.run_scheduler, daemon=True).start()
        self.icon.run()

    def stop(self):
        """Stop the service"""
        self.running = False
        self.icon.stop()

if __name__ == "__main__":
    service = JiraTicketService()
    service.start()
