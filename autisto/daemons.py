import os
import sys
import time
import subprocess

autisto_dir = os.path.dirname(os.path.realpath(__file__))


class Platform:
    def __init__(self, name, service_name, service_file_dir, service_file_path):
        self.name = name
        self.service_name = service_name
        self.service_file_dir = service_file_dir
        self.service_file_path = service_file_path

    class NotImplemented(Exception):
        pass

    def service_active(self):
        raise self.NotImplemented

    def set_service(self):
        raise self.NotImplemented

    def remove_service(self):
        raise self.NotImplemented

    def start_service(self):
        raise self.NotImplemented

    def stop_service(self):
        raise self.NotImplemented


class Linux(Platform):
    def __init__(self):
        service_name = "autisto"
        service_file_dir = os.path.join("/etc/systemd/system")
        service_file_path = os.path.join(service_file_dir, f"{service_name}.service")

        super().__init__(
            "Linux",
            service_name,
            service_file_dir,
            service_file_path
        )

    def service_active(self, quiet=False):
        if subprocess.call(["systemctl", "is-active", "--quiet", self.service_name]) == 0:
            if not quiet:
                print("\033[92mService is active.\033[0m")
            return True
        else:
            if not quiet:
                print("\033[91mService is inactive.\033[0m")
            return False

    def set_service(self):
        self.remove_service()

        os.makedirs(self.service_file_dir, exist_ok=True)
        with open(self.service_file_path, "w") as file:
            file.write("[Unit]\n")
            file.write("Description=Autisto systemd service\n")
            file.write("After=mongod.service\n")
            file.write("\n[Service]\n")
            file.write("User=root\n")
            file.write("Type=simple\n")
            file.write(f"ExecStart={sys.executable} "
                       f"{os.path.join(autisto_dir, 'server.py')}\n")
            file.write("StandardOutput=file:/tmp/autisto.log\n")
            file.write("StandardError=file:/tmp/autisto.log\n")
            file.write("RestartSec=5\n")
            file.write("Restart=always\n")
            file.write("\n[Install]\n")
            file.write("WantedBy=multi-user.target\n")

        systemd_setup = [
            ["systemctl", "enable", self.service_name],
            ["systemctl", "daemon-reload"],
            ["systemctl", "start", self.service_name]
        ]
        success = [subprocess.call(cmd) == 0 for cmd in systemd_setup]

        if all(success):
            time.sleep(3)
            print("\n\033[92mAutisto systemd service enabled. It should be reported as active."
                  "\nClose status with 'q'.\033[0m")
            subprocess.run(["systemctl", "status", self.service_name])
        else:
            print("\n\033[91mAutisto systemd service set-up failed!\033[0m")

    def remove_service(self):
        subprocess.run(["systemctl", "stop", self.service_name])
        subprocess.run(["systemctl", "disable", self.service_name])
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "reset-failed"])

    def start_service(self):
        subprocess.run(["systemctl", "start", self.service_name])

    def stop_service(self):
        if self.service_active(quiet=True):
            return subprocess.call(["systemctl", "stop", self.service_name]) == 0
        else:
            return False


class MacOS(Platform):
    def __init__(self):
        service_name = "com.autisto.run"
        service_file_dir = os.path.join(os.path.expanduser("~/Library/LaunchAgents"))
        service_file_path = os.path.join(service_file_dir, f"{service_name}.plist")

        super().__init__(
            "macOS",
            service_name,
            service_file_dir,
            service_file_path
        )

    def service_active(self, quiet=False):
        if self.service_name in subprocess.check_output(["launchctl", "list"]).decode("utf-8"):
            if not quiet:
                print("\033[92mService is active.\033[0m")
            return True
        else:
            if not quiet:
                print("\033[91mService is inactive.\033[0m")
            return False

    def set_service(self):
        self.stop_service()

        os.makedirs(self.service_file_dir, exist_ok=True)
        with open(self.service_file_path, "w") as file:
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                       '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n')
            file.write('<plist version="1.0">\n')
            file.write('<dict>\n')
            file.write('    <key>Label</key>\n')
            file.write(f'    <string>{self.service_name}</string>\n')
            file.write('    <key>ProgramArguments</key>\n')
            file.write('    <array>\n')
            file.write(f'        <string>{sys.executable}</string>\n')
            file.write(f'        <string>{os.path.join(autisto_dir, "server.py")}</string>\n')
            file.write('    </array>\n')
            file.write('    <key>KeepAlive</key>\n')
            file.write('    <true/>\n')
            file.write('</dict>\n')
            file.write('</plist>\n')

        self.start_service()
        print("\n\033[92mAutisto launchd service enabled.\033[0m")
        time.sleep(1)
        self.service_active()

    def remove_service(self):
        subprocess.call(["launchctl", "unload", "-w", self.service_file_path])

    def start_service(self):
        subprocess.call(["launchctl", "load", "-w", self.service_file_path])

    def stop_service(self):
        if self.service_active(quiet=True):
            return subprocess.call(["launchctl", "unload", self.service_file_path]) == 0
        else:
            return False


def check_platform():
    if sys.platform in ["linux", "darwin"]:
        return sys.platform
    else:
        print("\n\033[91mAutisto is available only for Linux and macOS.\033[0m")
        sys.exit(0)


def get_platform():
    this_platform = check_platform()
    if this_platform == "linux":
        return Linux()
    elif this_platform == "darwin":
        return MacOS()
