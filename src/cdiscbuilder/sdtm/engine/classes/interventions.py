from .general import GeneralProcessor

class InterventionsProcessor(GeneralProcessor):
    """
    Processor for SDTM Interventions class (e.g., CM, EX, PR).
    Typically wide format (one row per intervention).
    """
    def __init__(self):
        super().__init__()
        self.class_name = "INTERVENTIONS"
