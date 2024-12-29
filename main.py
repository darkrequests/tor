import os
import random
import time
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.webview import WebView
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from stem import Signal
from stem.control import Controller
from subprocess import Popen, PIPE


class AnonymousBrowser(App):
    """
    An advanced anonymous browser leveraging the Tor network with enhanced security, usability, and features.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.tor_process = None
        self.enable_js = False  # Default JavaScript state
        self.recent_urls = []  # Store recent URLs
        self.log_messages = []  # Log messages for user reference

    def build(self):
        self.setup_tor_service()

        # Main layout
        main_layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Header layout for URL input and controls
        header_layout = GridLayout(cols=3, size_hint_y=None, height=50)
        self.url_input = TextInput(
            hint_text="Enter URL (e.g., https://example.com)",
            multiline=False,
            size_hint=(0.7, 1),
        )
        self.url_input.bind(on_text_validate=self.load_url)
        self.go_button = Button(text="Go", size_hint=(0.15, 1))
        self.go_button.bind(on_press=self.load_url)

        self.recent_urls_spinner = Spinner(
            text="Recent URLs",
            values=[],
            size_hint=(0.15, 1),
        )
        self.recent_urls_spinner.bind(text=self.load_recent_url)

        header_layout.add_widget(self.url_input)
        header_layout.add_widget(self.go_button)
        header_layout.add_widget(self.recent_urls_spinner)

        # WebView
        self.webview = WebView(size_hint=(1, 0.75))

        # Options layout
        options_layout = GridLayout(cols=3, size_hint_y=None, height=50)
        self.js_toggle = ToggleButton(
            text="Enable JavaScript", state="normal", size_hint=(0.3, 1)
        )
        self.js_toggle.bind(on_press=self.toggle_js)

        self.refresh_tor_button = Button(
            text="Refresh Tor Circuit", size_hint=(0.4, 1)
        )
        self.refresh_tor_button.bind(on_press=self.refresh_tor_circuit)

        self.clear_logs_button = Button(text="Clear Logs", size_hint=(0.3, 1))
        self.clear_logs_button.bind(on_press=self.clear_logs)

        options_layout.add_widget(self.js_toggle)
        options_layout.add_widget(self.refresh_tor_button)
        options_layout.add_widget(self.clear_logs_button)

        # Log panel
        self.log_label = Label(
            text="Log Messages:\n", halign="left", valign="top", size_hint=(1, 0.2)
        )
        self.log_label.bind(size=self.log_label.setter("text_size"))

        # Add layouts to main layout
        main_layout.add_widget(header_layout)
        main_layout.add_widget(self.webview)
        main_layout.add_widget(options_layout)
        main_layout.add_widget(self.log_label)

        return main_layout

    def setup_tor_service(self):
        """
        Start the Tor service and set up Tor control.
        """
        try:
            self.tor_process = Popen(["tor"], stdout=PIPE, stderr=PIPE)
            self.log("Starting Tor service...")
            time.sleep(5)  # Allow Tor some time to start

            self.controller = Controller.from_port(port=9051)
            self.controller.authenticate()
            self.controller.signal(Signal.NEWNYM)
            self.log("Tor service successfully established.")
        except Exception as e:
            self.log(f"Failed to set up Tor: {e}")
            if self.tor_process:
                self.tor_process.terminate()

    def load_url(self, instance):
        """
        Load the entered URL through the Tor network and display it in the WebView.
        """
        url = self.url_input.text.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        try:
            # Create a Tor session
            session = requests.session()
            session.proxies = {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050",
            }

            # Add randomized headers
            headers = self.get_random_headers()

            # Request page
            self.controller.signal(Signal.NEWNYM)  # Rotate IP
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Update WebView
            self.webview.load_data(response.text, mime_type="text/html", charset="utf-8")

            # Add to recent URLs
            if url not in self.recent_urls:
                self.recent_urls.append(url)
                self.recent_urls_spinner.values = self.recent_urls

            self.log(f"Successfully loaded: {url}")

        except requests.RequestException as e:
            self.log(f"Request failed: {e}")
            self.webview.load_data(f"<h1>Error</h1><p>{e}</p>")

    def load_recent_url(self, spinner, text):
        """
        Load a URL from the recent URLs dropdown.
        """
        self.url_input.text = text
        self.load_url(None)

    def toggle_js(self, instance):
        """
        Enable or disable JavaScript in the WebView.
        """
        self.enable_js = not self.enable_js
        if self.enable_js:
            self.js_toggle.text = "Disable JavaScript"
            self.webview.settings.java_script_enabled = True
        else:
            self.js_toggle.text = "Enable JavaScript"
            self.webview.settings.java_script_enabled = False
        self.log(f"JavaScript enabled: {self.enable_js}")

    def refresh_tor_circuit(self, instance):
        """
        Refresh the Tor circuit to obtain a new IP.
        """
        try:
            self.controller.signal(Signal.NEWNYM)
            self.log("Tor circuit refreshed.")
        except Exception as e:
            self.log(f"Failed to refresh Tor circuit: {e}")

    def clear_logs(self, instance):
        """
        Clear the log messages.
        """
        self.log_messages = []
        self.log_label.text = "Log Messages:\n"

    def log(self, message):
        """
        Append a message to the log panel.
        """
        self.log_messages.append(message)
        self.log_label.text = "Log Messages:\n" + "\n".join(self.log_messages[-10:])

    @staticmethod
    def get_random_headers():
        """
        Generate random headers for each request to enhance anonymity.
        Returns:
            dict: Randomized headers including User-Agent.
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

    def on_stop(self):
        """
        Clean up resources when the application stops.
        """
        if self.tor_process:
            self.tor_process.terminate()
            self.log("Tor service terminated.")


if __name__ == "__main__":
    # Set default window size
    Window.size = (1024, 768)
    AnonymousBrowser().run()
