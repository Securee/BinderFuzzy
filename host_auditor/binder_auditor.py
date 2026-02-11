import os
import sys
import argparse
from utils.adb import AdbWrapper
from utils.jadx import JadxWrapper
from utils.extractor import CodeExtractor
from utils.llm import LLMClient

def main():
    parser = argparse.ArgumentParser(description="Binder Auditor")
    parser.add_argument("--service", help="Specific service to audit (comma-separated for multiple)")
    parser.add_argument("--batch-file", help="File containing list of services to audit (one per line)")
    parser.add_argument("--list", action="store_true", help="List all available services")
    parser.add_argument("--device", help="ADB Device ID")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "chatgpt", "deepseek"], help="LLM Provider")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM analysis and only extract code")
    args = parser.parse_args()

    adb = AdbWrapper(args.device)
    jadx = JadxWrapper()
    extractor = CodeExtractor()
    llm = LLMClient(provider=args.provider)

    print("[*] Enumerating services...")
    services = adb.list_services()

    if args.list:
        print(f"Found {len(services)} services:")
        for name, interface in sorted(services.items()):
            print(f"  - {name}: {interface}")
        return

    target_services = {}
    service_names = []

    if args.batch_file:
        if os.path.exists(args.batch_file):
            with open(args.batch_file, "r") as f:
                service_names.extend([line.strip() for line in f if line.strip()])
        else:
            print(f"[!] Batch file '{args.batch_file}' not found.")
            return

    if args.service:
        service_names.extend([s.strip() for s in args.service.split(",") if s.strip()])

    if not service_names and not args.batch_file:
        # Default test case
        print("[!] No service specified. Using 'power' as a test case (usually smaller than activity).")
        service_names.append("power")

    for s_name in service_names:
        if s_name in services:
             target_services[s_name] = services[s_name]
        else:
             print(f"[!] Service '{s_name}' not found available services.")

    for name, interface in target_services.items():
        print(f"\n[+] Processing service: {name} ({interface})")
        
        apk_path = None
        core_services = ["activity", "package", "power", "battery", "window", "input", "display"]
        
        # Mapping Logic
        if name in core_services:
            print(f"  -> Identified as Core System Service. Assuming /system/framework/services.jar")
            apk_path = "/system/framework/services.jar"
        else:
            print(f"  -> Automatic mapping for '{name}' not fully implemented yet.")
            continue

        if apk_path:
            local_name = os.path.basename(apk_path)
            local_path = os.path.join("host_auditor", "output", local_name)
            
            # Pull
            if not os.path.exists(local_path):
                print(f"  -> Pulling {apk_path} to {local_path}...")
                try:
                    adb.pull(apk_path, local_path)
                except Exception as e:
                    print(f"  [!] Pull failed: {e}")
                    continue
            else:
                print(f"  -> File {local_path} already exists. Skipping pull.")
                
            # Decompile
            out_dir = os.path.join("host_auditor", "output", f"{name}_src")
            if not os.path.exists(out_dir):
                print(f"  -> Decompiling to {out_dir}...")
                try:
                    jadx.decompile(local_path, out_dir)
                except Exception as e:
                    print(f"  [!] Decompilation failed: {e}")
                    continue
            else:
                print(f"  -> Decompiled source exists in {out_dir}. Skipping jadx.")
                
            # Locate Stub
            print(f"  -> Searching for Stub implementation for {interface}...")
            candidates = extractor.find_stub_implementation(out_dir, interface)
            
            if not candidates:
                print("  [!] No implementation found via standard pattern.")
                continue
                
            print(f"  -> Found {len(candidates)} candidate(s):")
            for c in candidates:
                print(f"    - {c}")
                
            # Analyze primary candidate
            target_file = candidates[0]
            print(f"  -> Extracting code from {target_file}...")
            code = extractor.get_file_content(target_file)
            
            # LLM Analysis
            if args.skip_llm:
                print(f"  -> Manual Audit Mode: Skipping LLM analysis.")
                print(f"  -> Implementation file located at: {target_file}")
            else:
                llm.analyze_vulnerability(code, name)

if __name__ == "__main__":
    main()
