import computations

studentid="P012CSOM23"


def calculateattendancetool() -> list:
    """Calculates cumulative 75% runway metrics and safe bunks for all subjects."""
    return computations.calculateattendence(studentid)

def getunmarkedtool() -> dict:
    """Fetches all dates with unposted portal periods that need student reconciliation."""
    return computations.getunmarkedsummary(studentid)

def simulatebunktool(targetdate: str, slots: list[int]=None) -> list:
    """Simulates the attendance percentage drop if classes are skipped on a given date."""
    return computations.simulatebunk(studentid, targetdate, slots)

tools=[calculateattendancetool, getunmarkedtool, simulatebunktool]