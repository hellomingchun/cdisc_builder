from .general import GeneralProcessor


class SpecialPurposeProcessor(GeneralProcessor):
    """
    Processor for SDTM Special-Purpose domains (e.g., DM, SV, SE, CO).
    """

    def __init__(self):
        super().__init__()
        self.class_name = "SPECIAL_PURPOSE"
