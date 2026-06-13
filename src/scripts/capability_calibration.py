import json
import os
from pathlib import Path
from typing import Dict, Any

CALIBRATION_FILE_REL = Path(".agent") / "state" / "capability_calibration.json"

def load_calibration(project_root: Path) -> Dict[str, Any]:
    file_path = project_root / CALIBRATION_FILE_REL
    if not file_path.exists():
        return {"schema_version": "1.0", "capabilities": {}}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "capabilities" not in data:
                return {"schema_version": "1.0", "capabilities": {}}
            return data
    except Exception:
        return {"schema_version": "1.0", "capabilities": {}}

def save_calibration(calibration_data: Dict[str, Any], project_root: Path) -> None:
    file_path = project_root / CALIBRATION_FILE_REL
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(calibration_data, f, indent=4)
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_file, file_path)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        raise e

def update_calibration_rebuttal(
    capability: str,
    verdict: str,  # "REBUTTAL_ACCEPTED" or "REBUTTAL_REJECTED" or "UNCONTESTED"
    project_root: Path
) -> None:
    """Updates tp/fp counters and weight based on rebuttal outcome.
    - REBUTTAL_ACCEPTED (false positive confirmed): fp += 1, weight *= 0.9
    - REBUTTAL_REJECTED or uncontested (true positive): tp += 1, weight *= 1.05
    Clamped to [0.5, 1.5].
    """
    data = load_calibration(project_root)
    capabilities = data.setdefault("capabilities", {})
    cap_data = capabilities.setdefault(capability, {"tp": 1, "fp": 1, "weight": 1.0})
    
    tp = cap_data.get("tp", 1)
    fp = cap_data.get("fp", 1)
    weight = cap_data.get("weight", 1.0)
    
    if verdict == "REBUTTAL_ACCEPTED":
        fp += 1
        weight *= 0.9
    elif verdict in ("REBUTTAL_REJECTED", "UNCONTESTED"):
        tp += 1
        weight *= 1.05
        
    weight = max(0.5, min(1.5, weight))
    
    cap_data["tp"] = tp
    cap_data["fp"] = fp
    cap_data["weight"] = weight
    
    save_calibration(data, project_root)

def get_calibrated_weight(
    capability: str,
    project_root: Path,
    config: Dict[str, Any] = None
) -> float:
    """Returns the weight for the capability, respecting config settings and overrides."""
    if config is None:
        config = {}
        
    calibration_config = config.get("capability_calibration", {})
    if not calibration_config.get("enabled", True):
        return 1.0
        
    overrides = calibration_config.get("overrides", {})
    if capability in overrides:
        return float(overrides[capability])
        
    data = load_calibration(project_root)
    capabilities = data.get("capabilities", {})
    if capability in capabilities:
        weight = capabilities[capability].get("weight", 1.0)
    else:
        weight = 1.0
        
    return max(0.5, min(1.5, weight))
