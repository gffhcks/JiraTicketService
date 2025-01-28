from jira import JIRA
import os
from datetime import datetime
import re
import tempfile
import shutil
import time
import msvcrt
import hashlib
import glob
import json

def load_secrets():
    """Load secrets from secrets.json file."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        secrets_path = os.path.join(script_dir, 'secrets.json')
        with open(secrets_path) as f:
            return json.load(f)['jira']
    except Exception as e:
        print(f"Failed to load secrets: {str(e)}")
        return None

# Load Jira connection settings from secrets
secrets = load_secrets()
if not secrets:
    raise Exception("Failed to load required secrets")

JIRA_SERVER = secrets['server']
JIRA_EMAIL = secrets['email']
JIRA_API_TOKEN = secrets['api_token']
JIRA_PROJECT = secrets['project']

def generate_content_hash(text):
    """Generate a hash from the exact content."""
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()[:12]

def extract_hashtags(text):
    """Extract hashtags from text, removing the # symbol."""
    hashtag_pattern = r'#(\w+)'
    return re.findall(hashtag_pattern, text)

def clean_summary(text):
    """Remove hashtags from the summary text."""
    return re.sub(r'#\w+', '', text).strip()

def connect_to_jira():
    """Establish connection to Jira."""
    try:
        return JIRA(
            server=JIRA_SERVER,
            basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
        )
    except Exception as e:
        print(f"Failed to connect to Jira: {str(e)}")
        return None

def find_existing_ticket(jira, content_hash):
    """Search for an existing ticket with the given content hash that isn't Done."""
    jql_query = f'project = {JIRA_PROJECT} AND description ~ "Content-Hash: {content_hash}" AND statusCategory != Done'
    issues = jira.search_issues(jql_query)
    
    return issues[0] if issues else None

def create_ticket(jira, line, content_hash):
    """Create a Jira ticket with the given summary and labels from hashtags."""
    try:
        # Check for existing open ticket
        existing_ticket = find_existing_ticket(jira, content_hash)
        if existing_ticket:
            print(f"Skipping duplicate content - open ticket exists: {existing_ticket.key}")
            return existing_ticket.key

        # Extract hashtags and clean summary
        labels = extract_hashtags(line)
        summary = clean_summary(line)
        
        description = (
            f'Ticket created automatically on {datetime.now()}\n\n'
            f'Content-Hash: {content_hash}'
        )
        
        issue_dict = {
            'project': {'key': JIRA_PROJECT},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Task'},
            'labels': labels
        }
        
        new_issue = jira.create_issue(fields=issue_dict)
        return new_issue.key
    except Exception as e:
        print(f"Failed to create ticket for '{line}': {str(e)}")
        return None

def process_line(jira, line):
    """Process a single line and create a ticket."""
    line = line.strip()
    if not line:  # Skip empty lines
        return True, line
    
    content_hash = generate_content_hash(line)
    ticket_key = create_ticket(jira, line, content_hash)
    if ticket_key:
        labels = extract_hashtags(line)
        labels_str = f" with labels: {', '.join(labels)}" if labels else ""
        print(f"Processed content hash {content_hash} - ticket {ticket_key} for: {clean_summary(line)}{labels_str}")
        return True, line
    return False, line

def get_sync_conflict_files(base_filename):
    """Get list of sync conflict files for the given base filename."""
    dirname = os.path.dirname(base_filename) or '.'
    basename = os.path.basename(base_filename)
    name_without_ext = os.path.splitext(basename)[0]
    pattern = os.path.join(dirname, f"{name_without_ext}.sync-conflict-*.txt")
    return glob.glob(pattern)

def process_single_file(filename, jira):
    """Process a single file and return number of successful processes."""
    successful_count = 0
    temp_file = None

    try:
        # Create a temporary file in the same directory
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filename))
        os.close(temp_fd)
        
        while True:
            try:
                with open(filename, 'r+') as source_file:
                    msvcrt.locking(source_file.fileno(), msvcrt.LK_NBLCK, 1)
                    
                    with open(temp_path, 'w') as temp_file:
                        file_empty = True
                        source_file.seek(0)
                        for line in source_file:
                            file_empty = False
                            success, processed_line = process_line(jira, line)
                            if success:
                                successful_count += 1
                            else:
                                temp_file.write(processed_line + '\n')
                        
                        if file_empty:
                            break
                        
                        source_file.seek(0)
                        source_file.truncate()
                        
                        temp_file.flush()
                        with open(temp_path, 'r') as read_temp:
                            shutil.copyfileobj(read_temp, source_file)
                        
                        if os.path.getsize(temp_path) == 0:
                            break
                    
                    source_file.seek(0)
                    msvcrt.locking(source_file.fileno(), msvcrt.LK_UNLCK, 1)
                    
            except IOError as e:
                print(f"File {filename} is locked, waiting for access...")
                time.sleep(1)
                continue
            
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                break

    finally:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            print(f"Error cleaning up temporary file: {str(e)}")

    return successful_count

def process_file(filename):
    """Process main file and any sync conflict files."""
    if not os.path.exists(filename):
        print(f"File {filename} not found")
        return

    # Connect to Jira
    jira = connect_to_jira()
    if not jira:
        return

    total_successful = 0
    
    # Process main file
    print(f"Processing main file: {filename}")
    total_successful += process_single_file(filename, jira)

    # Process sync conflict files
    sync_files = get_sync_conflict_files(filename)
    for sync_file in sync_files:
        print(f"\nProcessing sync conflict file: {sync_file}")
        total_successful += process_single_file(sync_file, jira)
        try:
            os.remove(sync_file)
            print(f"Deleted sync conflict file: {sync_file}")
        except Exception as e:
            print(f"Failed to delete sync conflict file {sync_file}: {str(e)}")

    print(f"\nTotal tickets processed: {total_successful}")

if __name__ == "__main__":
    input_file = r"F:\Users\dubba\Documents\Obsidian\Default\_GTD\tickets.md"
    process_file(input_file)
