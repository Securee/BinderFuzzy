import subprocess
import re
import os

class AdbWrapper:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.adb_cmd = ["adb"]
        if device_id:
            self.adb_cmd.extend(["-s", device_id])

    def run_shell(self, cmd):
        full_cmd = self.adb_cmd + ["shell", cmd]
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ADB command failed: {result.stderr}")
        return result.stdout.strip()

    def pull(self, remote_path, local_path):
        full_cmd = self.adb_cmd + ["pull", remote_path, local_path]
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ADB pull failed: {result.stderr}")
        return result.stdout.strip()

    def list_services(self):
        """
        Returns a dictionary of {service_name: interface_descriptor}
        """
        output = self.run_shell("service list")
        services = {}
        # Format: 0	activity: [android.app.IActivityManager]
        for line in output.splitlines():
            match = re.search(r'\d+\s+([a-zA-Z0-9_.]+):\s+\[(.*)\]', line)
            if match:
                name = match.group(1)
                interface = match.group(2)
                services[name] = interface
        return services

    def get_service_pid(self, service_name):
        """
        Attempts to find the PID of a service.
        This is not trivial. We try 'dumpsys' approach.
        """
        # Try finding PID via service list if available (older android versions)
        # On modern android, it's harder.
        pass 
