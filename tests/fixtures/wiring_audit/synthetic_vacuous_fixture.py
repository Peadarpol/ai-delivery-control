from posture import disposition

def some_consumer():
    result = disposition(
        component="test",
        baseline=None,
        touched_files=[]
    )
    return result
