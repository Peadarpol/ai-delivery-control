from posture import disposition

def check_architecture():
    # Pre-HIB-080 disposition call missing baseline and touched_files
    result = disposition(component="some_component")
    return result
