from .general import GeneralProcessor


class EventsProcessor(GeneralProcessor):
    """
    Processor for SDTM Events class (e.g., AE, DS, MH).
    Typically wide format (one row per event).
    """

    def __init__(self):
        super().__init__()
        self.class_name = "EVENTS"
