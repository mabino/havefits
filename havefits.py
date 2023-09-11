import wx
import os
import requests
import threading
from urllib.parse import urlparse
from requests.exceptions import RequestException

def is_valid_url(url):
    """
    This function checks if a URL is valid by parsing it for a scheme (e.g., 'http', 'https') and a network location (e.g., 'www.example.com'). Return bool.
    """
    try:
        return all(urlparse(url)[0:2])
    except ValueError:
        return False

class DownloadThread(threading.Thread):
    def __init__(self, url, filename, save_path, parent):
        """
        Initializes a DownloadThread object with the provided URL, filename, save path, and parent frame.  Use of threading.Thread object to allow the downloads to go on in the background.  Subclasses threading.Thread to define a custom run method.
        https://docs.python.org/3.8/library/threading.html#threading.Thread
        """
        super().__init__()
        self.url, self.filename, self.save_path, self.parent = url, filename, save_path, parent

    def run(self):
        """
        According to the docs, called automatically when a thread is started; attempts to download the file from the URL, save it to the specified path, and, given the customization, updates the GUI with progress.
        Run for each thread, triees to get a URL response.  If not, we have an exception.  If it is 200, writes the file to a nonexistent file name.  Otherwise, report a failure to the log (GUI).
        """
        try:
            response = requests.get(self.url, stream=True)
            if response.status_code == 200:
                file_path = os.path.join(self.save_path, self.filename)
                file_exists, count = os.path.exists(file_path), 1
                while file_exists:
                    base_name, file_extension = os.path.splitext(self.filename)
                    new_filename = f"{base_name} Copy {count}{file_extension}"
                    file_path = os.path.join(self.save_path, new_filename)
                    file_exists, count = os.path.exists(file_path), count + 1
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                wx.CallAfter(self.parent.update_status, f"Downloaded: {self.filename}")
            else:
                wx.CallAfter(self.parent.update_status, f"Failed to download: {self.filename}")
        except Exception as e:
            wx.CallAfter(self.parent.update_status, f"Error: {str(e)}")

class MyFrame(wx.Frame):
    '''
    Subclass of wx.Frame as MyFrame and customize the layout in __init__, add methods for selecting the downloads folder, initiating the download, and updating the log.
    '''
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(600, 600))
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.in_progress_downloads, self.download_path = 0, None
        self.panel = wx.Panel(self)
        self.base_url_label, self.base_url_text = wx.StaticText(self.panel, label="Base URL"), wx.TextCtrl(self.panel)
        self.file_list_label, self.file_list_text = wx.StaticText(self.panel, label="FITS File Names, One Per Line"), wx.TextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.download_to_button, self.download_button = wx.Button(self.panel, label="Choose Download Folder"), wx.Button(self.panel, label="Start Download")
        self.status_label, self.status_text = wx.StaticText(self.panel, label="Activity Log"), wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        download_location_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.selected_download_label, self.selected_download_text = wx.StaticText(self.panel, label="Selected Download Folder:"), wx.StaticText(self.panel, label="Not selected")
        download_location_sizer.Add(self.selected_download_label, 0, wx.ALL, 10)
        download_location_sizer.Add(self.selected_download_text, 0, wx.ALL, 10)
        self.Bind(wx.EVT_BUTTON, self.on_download_to, self.download_to_button)
        self.Bind(wx.EVT_BUTTON, self.on_download, self.download_button)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddMany([
            (self.base_url_label, 0, wx.ALL, 10), (self.base_url_text, 0, wx.EXPAND | wx.ALL, 10),
            (self.file_list_label, 0, wx.ALL, 10), (self.file_list_text, 1, wx.EXPAND | wx.ALL, 10),
            (download_location_sizer, 0, wx.EXPAND | wx.ALL, 10),
            (self.download_to_button, 0, wx.ALL, 10), (self.download_button, 0, wx.ALL, 10),
            (self.status_label, 0, wx.ALL, 10), (self.status_text, 1, wx.EXPAND | wx.ALL, 10)
        ])
        self.panel.SetSizer(self.sizer)
        self.Show()
        
    def on_exit(self, event):
        self.Close()

    def on_download_to(self, event):
        dialog = wx.DirDialog(self, "Choose a download location", style=wx.DD_DEFAULT_STYLE)
        if dialog.ShowModal() == wx.ID_OK:
            self.download_path = dialog.GetPath()
            dialog.Destroy()
            self.selected_download_text.SetLabel(self.download_path)

    def on_download(self, event):
        base_url, file_list = self.base_url_text.GetValue(), self.file_list_text.GetValue().splitlines()
        if not self.download_path:
            wx.MessageBox("Please select a download location.", "Error", wx.OK | wx.ICON_ERROR)
            return
        if not is_valid_url(base_url):
            wx.MessageBox("Please enter a valid Base URL.", "Error", wx.OK | wx.ICON_ERROR)
            return
        self.in_progress_downloads, invalid_files = 0, []
        for filename in file_list:
            if not filename.lower().endswith(('.fit', '.fits')):
                invalid_files.append(filename)
                continue
            url = os.path.join(base_url, filename)
            thread = DownloadThread(url, filename, self.download_path, self)
            thread.start()
            self.in_progress_downloads += 1
        if invalid_files:
            error_message = "The following files are not FITS files and will not be downloaded:\n"
            error_message += "\n".join(invalid_files)
            wx.MessageBox(error_message, "Invalid File Names", wx.OK | wx.ICON_ERROR)

    def update_status(self, message):
        current_status = self.status_text.GetValue()
        status_message = "" if self.in_progress_downloads > 0 else "Partially Complete" if "Failed to download" in message else "All Complete, Pending Next"
        self.status_text.SetValue(current_status + message + '\n' + f"{status_message}\n")

class MyApp(wx.App):
    '''
    Subclass of wx.App; try to do Mac-like things when instantiated as app.
    Need to add Windows-like behavior after testing.  Does Alt+F4 work?
    '''
    def OnInit(self):
        self.frame = MyFrame(None, "Have FITS")
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Quit this application")
        file_menu.Append(wx.ID_EXIT, "&Exit\tAlt+F4", "Exit this application")
        self.SetMacAboutMenuItemId(wx.ID_ABOUT)
        self.frame.SetMenuBar(menubar)
        self.frame.Raise()
        return True

if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
