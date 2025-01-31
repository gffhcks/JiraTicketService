import pystray
from PIL import Image, ImageDraw
import threading
import time
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from jira_tickets import process_file, TICKET_FILE

def setup_logging():
    """Setup logging to both file and console with rotation."""
    logger = logging.getLogger('JiraTicketService')
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Setup rotating file handler (10 MB per file, keep 5 backup files)
    log_file = os.path.join(logs_dir, 'jira_service.log')
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Setup logging
logger = setup_logging()

class JiraTicketService:
    def __init__(self):
        logger.info("Initializing JiraTicketService")
        self.interval = 30  # 30 seconds default
        self.running = False
        self.last_run = None
        self.processing = False
        self.icon = None
        try:
            self.setup_tray()
            logger.info("System tray setup completed")
        except Exception as e:
            logger.error(f"Failed to setup system tray: {str(e)}", exc_info=True)
            raise

    def create_icon(self):
        """Create a simple icon - a colored circle"""
        try:
            width = 64
            height = 64
            color = (0, 128, 255)  # Blue color
            
            image = Image.new('RGB', (width, height), (255, 255, 255))
            dc = ImageDraw.Draw(image)
            dc.ellipse([8, 8, width-8, height-8], fill=color)
            
            return image
        except Exception as e:
            logger.error(f"Failed to create icon: {str(e)}", exc_info=True)
            raise

    def setup_tray(self):
        """Setup the system tray icon and menu"""
        try:
            image = self.create_icon()
            
            menu = (
                pystray.MenuItem("Status", self.show_status, default=True),
                pystray.MenuItem("Process Now", self.process_now),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Set Interval", pystray.Menu(
                    pystray.MenuItem("30 seconds", lambda: self.set_interval(30)),
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
        except Exception as e:
            logger.error(f"Failed to setup tray menu: {str(e)}", exc_info=True)
            raise

    def set_interval(self, seconds):
        """Change the processing interval"""
        try:
            self.interval = seconds
            logger.info(f"Processing interval changed to {seconds} seconds")
            self.show_status()
        except Exception as e:
            logger.error(f"Failed to set interval: {str(e)}", exc_info=True)

    def show_status(self):
        """Show current status in a notification"""
        try:
            status = []
            status.append(f"Service: {'Running' if self.running else 'Stopped'}")
            if self.interval >= 60:
                status.append(f"Interval: {self.interval//60} minutes")
            else:
                status.append(f"Interval: {self.interval} seconds")
            if self.last_run:
                status.append(f"Last run: {self.last_run.strftime('%H:%M:%S')}")
            if self.processing:
                status.append("Currently processing tickets...")
            
            status_msg = "\n".join(status)
            logger.info(f"Status update: {status_msg}")
            self.icon.notify(status_msg, "Jira Ticket Service Status")
        except Exception as e:
            logger.error(f"Failed to show status: {str(e)}", exc_info=True)

    def process_now(self):
        """Manually trigger ticket processing"""
        try:
            if not self.processing:
                logger.info("Manual processing triggered")
                threading.Thread(target=self.process_tickets, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start manual processing: {str(e)}", exc_info=True)

    def process_tickets(self):
        """Process tickets and update status"""
        if self.processing:
            return
        
        try:
            self.processing = True
            logger.info("Starting ticket processing")
            self.icon.icon = self.create_processing_icon()
            process_file(TICKET_FILE)
            self.last_run = datetime.now()
            logger.info("Ticket processing completed")
        except Exception as e:
            error_msg = f"Error processing tickets: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.icon.notify(error_msg, "Error")
        finally:
            self.processing = False
            self.icon.icon = self.create_icon()

    def create_processing_icon(self):
        """Create an icon indicating processing status"""
        try:
            width = 64
            height = 64
            color = (255, 165, 0)  # Orange color for processing
            
            image = Image.new('RGB', (width, height), (255, 255, 255))
            dc = ImageDraw.Draw(image)
            dc.ellipse([8, 8, width-8, height-8], fill=color)
            
            return image
        except Exception as e:
            logger.error(f"Failed to create processing icon: {str(e)}", exc_info=True)
            raise

    def run_scheduler(self):
        """Run the scheduler loop"""
        logger.info("Starting scheduler loop")
        while self.running:
            if not self.processing:
                self.process_tickets()
            time.sleep(self.interval)
        logger.info("Scheduler loop stopped")

    def start(self):
        """Start the service"""
        try:
            logger.info("Starting JiraTicketService")
            self.running = True
            threading.Thread(target=self.run_scheduler, daemon=True).start()
            logger.info("Running system tray icon")
            self.icon.run()
        except Exception as e:
            logger.error(f"Failed to start service: {str(e)}", exc_info=True)
            raise

    def stop(self):
        """Stop the service"""
        try:
            logger.info("Stopping JiraTicketService")
            self.running = False
            self.icon.stop()
            logger.info("Service stopped")
        except Exception as e:
            logger.error(f"Error stopping service: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        logger.info("Starting JiraTicketService from main")
        service = JiraTicketService()
        service.start()
    except Exception as e:
        logger.error(f"Failed to start service from main: {str(e)}", exc_info=True)
