##     Buzz Gym Capacity Tracker
# Copyright (C) 2026  CromwellCruiser
# This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
import threading
import tkinter as tk
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pystray
from PIL import Image, ImageDraw
from plyer import notification


class GymTrackerDaemon:
    def __init__(self):
        self.email = '[USERNAME]'
        self.pin = '[PASSWORD]'

        self.thresh_green = 40
        self.thresh_notify = 35
        self.thresh_red = 85

        self.colors = {
            'green': '#22c55e',
            'amber': '#f59e0b',
            'red': '#ef4444'
        }

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0',
            'Accept-Language': 'en-GB,en;q=0.9'
        })

        self.csrf_token = None
        self.current_capacity = 100
        self.below_popup_threshold = False
        self.notified_os = False
        self.running = True

        # Track the active UI window to prevent stacking memory leaks
        self.active_popup = None

        self.root = tk.Tk()
        self.root.withdraw()

        self.icon = self.build_taskbar_icon(self.colors['red'])

        threading.Thread(target=self.polling_loop, daemon=True).start()
        threading.Thread(target=self.icon.run, daemon=True).start()

    def get_status_color(self, capacity):
        if capacity <= self.thresh_green:
            return self.colors['green']
        elif capacity >= self.thresh_red:
            return self.colors['red']
        else:
            return self.colors['amber']

    def generate_icon_image(self, hex_color):
        h = hex_color.lstrip('#')
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        img = Image.new('RGB', (64, 64), color=rgb)
        d = ImageDraw.Draw(img)
        d.text((28, 26), 'B', fill=(255, 255, 255))
        return img

    def build_taskbar_icon(self, initial_color):
        img = self.generate_icon_image(initial_color)
        menu = pystray.Menu(
            pystray.MenuItem('Check Status', self.trigger_manual_check, default=True),
            pystray.MenuItem('Exit Tracker', self.terminate_daemon)
        )
        return pystray.Icon('BuzzGym', img, 'Buzz Gym Tracker', menu=menu)

    def authenticate(self):
        """Handles the heavy POST login. Only called when the session is dead."""
        try:
            print("Authenticating session...")
            login_url = '[URL]'
            page = self.session.get(login_url, timeout=10)
            soup = BeautifulSoup(page.text, 'html.parser')

            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_meta:
                return False

            self.csrf_token = csrf_meta['content']

            payload = {
                '_csrf': self.csrf_token,
                'LoginForm[email]': self.email,
                'LoginForm[password]': self.pin,
                'login-button': ''
            }
            login_resp = self.session.post(login_url, data=payload, headers={'Referer': login_url}, timeout=10)
            login_resp.raise_for_status()

            # Update baseline session headers for AJAX requests
            self.session.headers.update({
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': self.csrf_token,
                'Referer': '[URL]'
            })
            return True
        except Exception as e:
            print(f'Authentication failed: {e}')
            return False

    def fetch_capacity(self):
        """Lightweight GET request. Re-authenticates only if kicked out."""
        capacity_url = '[URL]'

        # Initial boot check
        if not self.csrf_token:
            if not self.authenticate():
                return None

        try:
            req = self.session.get(capacity_url, timeout=10)

            # If the session expired, the server typically returns 401/403 or redirects to HTML login
            if req.status_code in [401, 403] or 'application/json' not in req.headers.get('Content-Type', ''):
                print("Session expired or invalid response. Re-authenticating...")
                if self.authenticate():
                    req = self.session.get(capacity_url, timeout=10)
                else:
                    return None

            req.raise_for_status()
            data = req.json()
            return int(data.get('liveUsers', 100))

        except Exception as e:
            print(f'Network/Parsing exception during capacity fetch: {e}')
            return None

    def trigger_os_notification(self, capacity):
        timestamp = datetime.now().strftime('%H:%M')
        try:
            notification.notify(
                title='Buzz Gym Oxford',
                message=f'Capacity dropped to {capacity}% at {timestamp}.',
                app_name='Gym Tracker',
                timeout=10
            )
        except Exception as e:
            print(f'Failed to send OS notification: {e}')

    def polling_loop(self):
        while self.running:
            capacity = self.fetch_capacity()

            if capacity is not None:
                if capacity != self.current_capacity:
                    self.current_capacity = capacity
                    color_hex = self.get_status_color(capacity)
                    self.icon.icon = self.generate_icon_image(color_hex)

                if capacity <= self.thresh_green and not self.below_popup_threshold:
                    self.below_popup_threshold = True
                    self.root.after(0, self.render_popup, capacity)
                elif capacity > self.thresh_green:
                    self.below_popup_threshold = False

                if capacity <= self.thresh_notify and not self.notified_os:
                    self.notified_os = True
                    self.trigger_os_notification(capacity)
                elif capacity > self.thresh_notify:
                    self.notified_os = False

            time.sleep(300)

    def render_popup(self, capacity):
        # Destroy existing window if it exists to prevent unmanaged graphical stacking
        if self.active_popup and self.active_popup.winfo_exists():
            self.active_popup.destroy()

        self.active_popup = tk.Toplevel(self.root)
        popup = self.active_popup
        popup.title('Buzz Gym Status')

        popup.overrideredirect(True)
        popup.configure(bg='#0a0a0a')

        window_w, window_h = 240, 180
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x_pos = screen_w - window_w - 20
        y_pos = screen_h - window_h - 60
        popup.geometry(f'{window_w}x{window_h}+{x_pos}+{y_pos}')
        popup.attributes('-topmost', True)

        color_hex = self.get_status_color(capacity)

        canvas = tk.Canvas(popup, width=240, height=120, bg=color_hex, highlightthickness=0)
        canvas.pack(side=tk.TOP, fill=tk.BOTH)

        font_config = ('Impact', 48, 'bold')
        text_x, text_y = 120, 60
        pct_text = f'{capacity}%'

        for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]:
            canvas.create_text(text_x + dx, text_y + dy, text=pct_text, font=font_config, fill='#111')
        canvas.create_text(text_x, text_y, text=pct_text, font=font_config, fill='#fff')

        btn_frame = tk.Frame(popup, bg='#0a0a0a')
        btn_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=10)

        btn_style = {
            'bg': '#1a1a1a',
            'fg': '#e5e5e5',
            'activebackground': '#333333',
            'activeforeground': '#ffffff',
            'relief': 'flat',
            'font': ('Segoe UI', 10, 'bold'),
            'bd': 0,
            'cursor': 'hand2'
        }

        btn_dismiss = tk.Button(btn_frame, text='DISMISS', command=popup.destroy, **btn_style)
        btn_dismiss.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)

        btn_exit = tk.Button(btn_frame, text='EXIT', command=self.terminate_daemon, **btn_style)
        btn_exit.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=10)

    def trigger_manual_check(self, icon, item):
        self.root.after(0, self.render_popup, self.current_capacity)

    def terminate_daemon(self, *args):
        self.running = False
        self.icon.stop()
        self.root.quit()


if __name__ == '__main__':
    daemon = GymTrackerDaemon()
    daemon.root.mainloop()