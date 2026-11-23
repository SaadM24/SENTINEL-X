"""Check the research runtime without requiring optional packages to be installed."""
import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path


PACKAGES = {
    "numpy": "numpy", "pandas": "pandas", "scipy": "scipy", "scikit-learn": "sklearn",
    "joblib": "joblib", "threadpoolctl": "threadpoolctl", "matplotlib": "matplotlib",
    "psutil": "psutil",
}


def inventory(require_tests=False):
    checks = {}
    for distribution, module in {**PACKAGES, **({"pytest": "pytest"} if require_tests else {})}.items():
        try:
            importlib.import_module(module)
            checks[distribution] = {"version": importlib.metadata.version(distribution)}
        except Exception as error:
            checks[distribution] = {"error": str(error)}
    ram = None
    if "error" not in checks["psutil"]:
        import psutil
        ram = round(psutil.virtual_memory().total / 2**30, 2)
    cuda = {"torch_available": False, "cuda_available": False}
    if importlib.util.find_spec("torch") is not None:
        try:
            import torch
            cuda = {"torch_available": True, "version": str(torch.__version__),
                    "cuda_available": torch.cuda.is_available(), "cuda_runtime": torch.version.cuda}
            if cuda["cuda_available"]:
                cuda["device"] = torch.cuda.get_device_name(0)
        except Exception as error:
            cuda["error"] = str(error)
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            result = subprocess.run([smi, "--query-gpu=name,driver_version,memory.total",
                                     "--format=csv,noheader"], text=True,
                                    capture_output=True, timeout=6, check=True)
            cuda["driver_report"] = result.stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            cuda["driver_error"] = str(error)
    try:
        from sentinel_x import detection, dashboard, behaviour, evidence
        package_import = True
    except ImportError:
        package_import = False
    bits = struct.calcsize("P") * 8
    return {"python": sys.version, "executable": sys.executable, "architecture_bits": bits,
            "platform": platform.platform(), "physical_ram_gib": ram, "gpu": cuda,
            "free_space_gib_here": round(shutil.disk_usage(Path.cwd()).free / 2**30, 2),
            "packages": checks, "project_importable": package_import,
            "ready": package_import and (3, 11) <= sys.version_info[:2] <= (3, 13)
                     and bits == 64 and all("error" not in item for item in checks.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    report = inventory(args.require_tests)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["ready"] else 1)
