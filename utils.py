import re

def sanitize_filename(name):
    """
    Sanitize a string to be safe for use as a filename.
    """
    # Remove invalid characters
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces with underscores or keep as is? User might prefer spaces.
    # Let's keep spaces but trim.
    return name.strip()
