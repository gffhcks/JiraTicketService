# JiraTicketService

A Windows system tray service that reads a file and creates tickets in Jira.

Each line in the target file will be created as a new ticket. The script will also process (and then delete) any sync conflict files that are created by Syncthing in the same directory.

Because the script also looks at sync conflict files, deduplication is performed by hashing the content of the line and storing it in the ticket descrption. Deduplication currently ignores any tickets that are already closed - i.e. if an identical line is added to the file a week later, it will create another new ticket. This is potentially useful for recurring tasks, but I'm not completely sold on it - it may change in future versions.

You can add labels to a ticket by adding hashtags in the line.

Code was mostly generated with [Augment Code](https://augmentcode.com/) as an experiment. I'll hopefully be iterating on it more in the future.

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `secrets.example.json` to `secrets.json` and update with your settings
4. Run `jira_ticket_service_startup.pyw` to start the service

Alternatively, you can run the service on startup by adding a shortcut to `jira_ticket_service_startup.pyw` in your startup folder (usually found at `C:\Users\<YourUsername>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`).

## Usage

My use case for this is to more easily create Jira tickets from my phone:

* [Obsidian](https://obsidian.md/) and/or [Markor](https://play.google.com/store/apps/details?id=net.gsantner.markor&hl=en_US) are used to modify the ticket markdown file.
* [Syncthing](https://syncthing.net/) syncs my Obsidian vault between my phone and desktop.
* JiraTicketService runs on my desktop and creates tickets from the markdown file, removing the processed lines.
* Syncthing sends the changes back to my phone. When the lines are gone, I know they've been created as tickets.

This lets me think of new tasks while I'm away from my desk and ensure they get added to my todo list, without having to deal with Atlassian's mobile app. I can jot down the things I need to handle, then do more complicated things (scheduling, due dates, etc.) from my desk later.

## Known Issues

* System tray icon's right-click menu is intended to support modifying the run interval, but these options do not currently appear in the menu.
