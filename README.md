# Buzz-Gym-Capacity-Tracker
A small lightweight widget that uses your login credentials to track the occupancy of your local buzz gym. The widget changes colour in your system tray as occupancy rises and falls, and surfaces a native Windows notification if it drops below a certain level.

How to use:
1. At lines 29 to 30, input your username and password. Retain the quotation marks.
2. Lines 32 to 34 are the thresholds in percentage, just as displayed in the Buzz app and website. At the moment, Green is below or equals to 40, Red is above or equals 85, and a notification window pops up if it falls below 35.
3. At lines 93, 116, and 124, use your own local branch of Buzz Gym's equivalents for the login and capacity screens respectively.
4. Run a command line 'pip install requests beautifulsoup4 pystray pillow plyer'
5. Rename the file with the .pyw extension and double-click to run.
6. If you wish the service to run at startup, press Win + R, type shell:startup, and hit Enter. Right-click your GymCap.pyw file, select Create shortcut, and drag that shortcut into the Startup folder that just opened.
