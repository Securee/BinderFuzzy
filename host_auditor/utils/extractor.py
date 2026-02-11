import os
import re

class CodeExtractor:
    def __init__(self):
        pass

    def find_stub_implementation(self, source_dir, interface_descriptor):
        """
        Scans the source_dir for a class that extends <Interface>.Stub
        interface_descriptor example: android.os.IPowerManager
        """
        # The stub is usually Interface.Stub
        # We look for "extends .*Stub" or similar.
        # Ideally, we look for "extends IPowerManager.Stub"
        
        simple_interface = interface_descriptor.split(".")[-1] # IPowerManager
        stub_pattern = re.compile(f"extends\\s+{simple_interface}\\.Stub", re.IGNORECASE)
        
        candidates = []
        
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".java"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if stub_pattern.search(content):
                                candidates.append(path)
                    except Exception as e:
                        pass
        
        return candidates

    def get_file_content(self, path):
         with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
