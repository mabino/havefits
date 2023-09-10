import wx
import os
import requests
import threading
# Import the wx constants for Command+Q
from wx import ID_EXIT, MOD_CMD, ID_ABOUT
from urllib.parse import urlparse
from requests.exceptions import RequestException

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])  # Check if scheme and netloc are both present
    except ValueError:
        return False

class DownloadThread(threading.Thread):
    """
    A custom thread class for downloading files from a URL, extending threading.Thread class to enable downloading a list files from a base URL.
    It is designed to run as a separate thread to avoid blocking the GUI.

    Attributes:
        url (str): The URL of the file to be downloaded.
        filename (str): The name of the file to be saved.
        save_path (str): The path where the file will be saved.
        parent (wx.Frame): The parent frame that created this thread.

    Methods:
        run(): Overrides the run method from threading.Thread, performs the file download operation. It
        updates the user interface with download progress and completion status.
    """
    def __init__(self, url, filename, save_path, parent):
        super(DownloadThread, self).__init__()
        self.url = url
        self.filename = filename
        self.save_path = save_path
        self.parent = parent

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            if response.status_code == 200:
                file_path = os.path.join(self.save_path, self.filename)

                # Check if the file already exists in the destination folder
                file_exists = os.path.exists(file_path)

                # If the file exists, append "Copy" and a number to the filename
                if file_exists:
                    base_name, file_extension = os.path.splitext(self.filename)
                    count = 1
                    while file_exists:
                        new_filename = f"{base_name} Copy {count}{file_extension}"
                        file_path = os.path.join(self.save_path, new_filename)
                        file_exists = os.path.exists(file_path)
                        count += 1

                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                wx.CallAfter(self.parent.update_status, f"Downloaded: {self.filename}")
            else:
                wx.CallAfter(self.parent.update_status, f"Failed to download: {self.filename}")
        except Exception as e:
            wx.CallAfter(self.parent.update_status, f"Error: {str(e)}")
     
class MyFrame(wx.Frame):
    """
    The main application window for the File Downloader.

    This class represents the main user interface window, inherits from wx.Frame, and handles user interactions and initiates file
    downloads when the 'Download' button is clicked.

    Attributes:
        parent: The parent window or None if it's a top-level window.
        title (str): The title of the application window.

    Methods:
        __init__(self, parent, title): Initializes the MyFrame instance, creating
        and configuring all the UI elements and event bindings.
        on_download_to(self, event): Handles the 'Download to' button click event,
        allowing the user to choose a download location.
        on_download(self, event): Handles the 'Download' button click event,
        initiating the file download process.
        update_status(self, message): Updates the status text control with the
        provided message.

    Usage:
        To create and display the main application window, create an instance of
        MyFrame and call app.MainLoop() to start the application event loop.
    """
    def __init__(self, parent, title):
        super(MyFrame, self).__init__(parent, title=title, size=(600, 600))  # Increase the initial window height

        # Add an event binding and a handler method
        self.Bind(wx.EVT_MENU, self.on_exit, id=ID_EXIT)
        self.in_progress_downloads = 0  # Initialize the count of in-progress downloads to 0
        self.panel = wx.Panel(self)
        self.base_url_label = wx.StaticText(self.panel, label="Base URL")
        self.base_url_text = wx.TextCtrl(self.panel)
        self.file_list_label = wx.StaticText(self.panel, label="FITS File Names, One Per Line")
        self.file_list_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.download_to_button = wx.Button(self.panel, label="Choose Download Folder")
        self.download_button = wx.Button(self.panel, label="Start Download")
        self.status_label = wx.StaticText(self.panel, label="Activity Log")
        
        # Use a TextCtrl widget with wx.TE_MULTILINE to display multiline status messages
        self.status_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)

        # Create a horizontal sizer for selected_download_label and selected_download_text
        download_location_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.selected_download_label = wx.StaticText(self.panel, label="Selected Download Folder:")
        self.selected_download_text = wx.StaticText(self.panel, label="Not selected")
        download_location_sizer.Add(self.selected_download_label, 0, wx.ALL, 10)
        download_location_sizer.Add(self.selected_download_text, 0, wx.ALL, 10)

        self.Bind(wx.EVT_BUTTON, self.on_download_to, self.download_to_button)
        self.Bind(wx.EVT_BUTTON, self.on_download, self.download_button)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.base_url_label, 0, wx.ALL, 10)
        self.sizer.Add(self.base_url_text, 0, wx.EXPAND | wx.ALL, 10)
        self.sizer.Add(self.file_list_label, 0, wx.ALL, 10)
        self.sizer.Add(self.file_list_text, 1, wx.EXPAND | wx.ALL, 10)
        self.sizer.Add(download_location_sizer, 0, wx.EXPAND | wx.ALL, 10)  # Add the download_location_sizer
        self.sizer.Add(self.download_to_button, 0, wx.ALL, 10)
        self.sizer.Add(self.download_button, 0, wx.ALL, 10)
        self.sizer.Add(self.status_label, 0, wx.ALL, 10)
        self.sizer.Add(self.status_text, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.SetSizer(self.sizer)
        self.Show()
        
    def on_exit(self, event):
        """Handle the Command+Q shortcut to quit the application."""
        self.Close()

    def on_download_to(self, event):
        dialog = wx.DirDialog(self, "Choose a download location", style=wx.DD_DEFAULT_STYLE)
        if dialog.ShowModal() == wx.ID_OK:
            self.download_path = dialog.GetPath()
            dialog.Destroy()
            # Update the selected download location label
            self.selected_download_text.SetLabel(self.download_path)

    def on_download(self, event):
        base_url = self.base_url_text.GetValue()
        file_list = self.file_list_text.GetValue().splitlines()

        if not hasattr(self, 'download_path'):
            wx.MessageBox("Please select a download location.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not is_valid_url(base_url):
            wx.MessageBox("Please enter a valid URL.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Create a gauge (progress bar) to show download progress
        # self.progress_gauge = wx.Gauge(self.panel, range=len(file_list), size=(300, 20))
        # self.sizer.Add(self.progress_gauge, 0, wx.ALL, 10)
        self.Layout()

        # Reset the count of in-progress downloads
        self.in_progress_downloads = 0

        invalid_files = []

        for filename in file_list:
            # Check if the filename ends with .fit or .fits
            if not filename.lower().endswith(('.fit', '.fits')):
                invalid_files.append(filename)
                continue

            url = os.path.join(base_url, filename)
            thread = DownloadThread(url, filename, self.download_path, self)
            thread.start()
            self.in_progress_downloads += 1  # Increment the count of in-progress downloads

        if invalid_files:
            error_message = "The following files are not FITS files and will not be downloaded:\n"
            error_message += "\n".join(invalid_files)
            wx.MessageBox(error_message, "Invalid File Names", wx.OK | wx.ICON_ERROR)


    def update_status(self, message):
        current_status = self.status_text.GetValue()

        # Check if there are in-progress downloads or any error messages
        if self.in_progress_downloads > 0:
            status_message = ""
        elif "Failed to download" in message:
            status_message = "Partially Complete"
        else:
            status_message = "All Complete, Pending Next"

        self.status_text.SetValue(current_status + message + '\n' + f"{status_message}\n")

    def update_progress(self):
        # Update the progress bar after each download
        #self.progress_gauge.Pulse()
        pass

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame(None, "Have FITS")
        self.frame.Show(True)
        self.SetTopWindow(self.frame)


        # Create a menu bar
        menubar = wx.MenuBar()

        # Create the File menu
        file_menu = wx.Menu()
        file_menu.Append(ID_EXIT, "E&xit\tCtrl+Q", "Quit this application")
        file_menu.Append(wx.ID_EXIT, "&Exit\tAlt+F4", "Exit this application")  # Add Alt+F4 shortcut
        # menubar.Append(file_menu, "&File")
        
        
        # Set the Mac "About" menu item ID
        self.SetMacAboutMenuItemId(ID_ABOUT)
        
        self.frame.SetMenuBar(menubar)
        
        # Activate the application window to bring it to the foreground
        self.frame.Raise()
        
        return True

if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
